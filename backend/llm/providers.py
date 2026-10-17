"""Adapters normalize different wire APIs into one checked structured result.

Only the selected adapter is instantiated. No provider failover, discovery call,
raw error bodies, arbitrary base URLs or model reasoning in returned evidence.
"""
import hashlib
import json
from dataclasses import dataclass
from time import perf_counter
from typing import Protocol

import httpx

from .config import LLMConfig
from .errors import LanguageError


@dataclass(frozen=True)
class StructuredRequest:
    task: str
    instructions: str
    data: dict
    schema: dict


@dataclass
class StructuredResult:
    value: dict
    audit: dict


class Provider(Protocol):
    async def generate(self, request: StructuredRequest) -> StructuredResult: ...
    async def close(self): ...


def portable_schema(value):
    """Portable provider subset; full length checks still run locally in Pydantic."""
    if isinstance(value, list):
        return [portable_schema(item) for item in value]
    if isinstance(value, dict):
        return {key: portable_schema(item) for key, item in value.items()
                if key not in {'title', 'minLength', 'maxLength'}}
    return value


class HTTPProvider:
    base_url = ''
    endpoint = ''
    adapter_version = ''

    def __init__(self, config: LLMConfig, transport=None):
        self.config, self.transport, self.client = config, transport, None

    def payload(self, request):
        raise NotImplementedError

    def parse(self, data):
        raise NotImplementedError

    async def generate(self, request):
        self.config.check()  # Guard again at adapter boundary, including direct callers.
        if not self.config.enabled or not self.config.key:
            raise LanguageError('Selected provider disabled or missing its own API key. No request made.')
        body = self.payload(request)
        name = self.config.provider
        audit = {'provider': name, 'requested_model': self.config.model,
            'adapter_version': self.adapter_version, 'api_attempted': False,
            'input_sha256': hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()}
        started = perf_counter()
        try:
            if self.client is None:
                self.client = httpx.AsyncClient(base_url=self.base_url,
                    headers={'Authorization': 'Bearer ' + self.config.key},
                    timeout=self.config.timeout_seconds, follow_redirects=False, transport=self.transport)
            audit['api_attempted'] = True
            response = await self.client.post(self.endpoint, json=body)
            audit['http_status'] = response.status_code
            if response.status_code == 429:
                raise LanguageError(f'{name} quota/rate limit reached (HTTP 429); template/manual-review fallback, no other provider called.')
            if response.status_code >= 400:
                raise LanguageError(f'{name} request failed (HTTP {response.status_code}); provider details withheld.')
            data = response.json()
            if not isinstance(data, dict):
                raise LanguageError(f'Unexpected {name} response envelope.')
            text, usage = self.parse(data)
            value = json.loads(text)
            if not isinstance(value, dict):
                raise LanguageError('Provider structured output must be an object.')
            audit.update({'returned_model': str(data.get('model', self.config.model))[:120],
                'response_id': str(data.get('id', ''))[:100],
                'output_sha256': hashlib.sha256(text.encode()).hexdigest(), 'usage': usage})
            return StructuredResult(value=value, audit=audit)
        except httpx.HTTPError:
            error = LanguageError(f'{name} connection/timeout failed; no automatic retry or provider switch.')
            error.audit = audit
            raise error from None
        except (ValueError, KeyError, TypeError, IndexError, AttributeError, ImportError) as exc:
            error = exc if isinstance(exc, LanguageError) else LanguageError(f'{name} returned invalid data or local transport setup failed; review required.')
            error.audit = audit
            raise error from None
        finally:
            audit['duration_ms'] = round((perf_counter() - started) * 1000, 2)

    async def close(self):
        if self.client is not None:
            await self.client.aclose()


class GroqChatProvider(HTTPProvider):
    base_url = 'https://api.groq.com/openai/v1/'
    endpoint = 'chat/completions'
    adapter_version = 'groq-chat-json-v1'

    def payload(self, request):
        body = {'model': self.config.model,
            'messages': [{'role': 'system', 'content': request.instructions},
                         {'role': 'user', 'content': json.dumps(request.data, ensure_ascii=False)}],
            'stream': False, 'max_completion_tokens': self.config.max_output_tokens,
            'response_format': {'type': 'json_schema', 'json_schema': {'name': request.task,
                'strict': True, 'schema': portable_schema(request.schema)}}}
        if self.config.model.startswith('openai/gpt-oss-'):
            body.update(reasoning_effort='low', include_reasoning=False)
        elif self.config.model.startswith('qwen/'):
            body.update(reasoning_effort='none', include_reasoning=False)
        return body

    def parse(self, data):
        choices = data.get('choices', [])
        if len(choices) != 1 or choices[0].get('finish_reason') != 'stop':
            raise LanguageError('Groq response incomplete/refused; review required.')
        message = choices[0]['message']
        if message.get('refusal') or message.get('tool_calls') or not isinstance(message.get('content'), str):
            raise LanguageError('Groq refused or returned unsupported content; review required.')
        # Deliberately ignore any reasoning/analysis field, even if provider includes it.
        usage = data.get('usage') or {}
        mapping = {'prompt_tokens': 'input_tokens', 'completion_tokens': 'output_tokens', 'total_tokens': 'total_tokens'}
        return message['content'], {new: usage[key] for key, new in mapping.items() if isinstance(usage.get(key), int)}


class OpenAIResponsesProvider(HTTPProvider):
    base_url = 'https://api.openai.com/v1/'
    endpoint = 'responses'
    adapter_version = 'openai-responses-json-v1'

    def payload(self, request):
        return {'model': self.config.model, 'store': False, 'instructions': request.instructions,
            'input': json.dumps(request.data, ensure_ascii=False), 'reasoning': {'effort': 'none'},
            'max_output_tokens': self.config.max_output_tokens,
            'text': {'format': {'type': 'json_schema', 'name': request.task, 'strict': True,
                               'schema': portable_schema(request.schema)}}}

    def parse(self, data):
        if data.get('status') != 'completed':
            raise LanguageError('OpenAI response incomplete/refused; review required.')
        parts = [part for item in data.get('output', []) if item.get('type') == 'message' for part in item.get('content', [])]
        outputs = [p['text'] for p in parts if p.get('type') == 'output_text']
        if any(p.get('type') == 'refusal' for p in parts) or len(outputs) != 1:
            raise LanguageError('OpenAI refused or returned unsupported content; review required.')
        return outputs[0], {k: v for k, v in (data.get('usage') or {}).items()
            if k in {'input_tokens', 'output_tokens', 'total_tokens'} and isinstance(v, int)}


PROVIDERS = {'groq': GroqChatProvider, 'openai': OpenAIResponsesProvider}


def create_provider(config, transport=None) -> Provider:
    config.check()
    return PROVIDERS[config.provider](config, transport=transport)
