"""Server-only settings. Provider keys never fall back to another provider's key."""
import os
import re
from dataclasses import dataclass, field
from typing import Mapping

from .errors import LanguageError

DEFAULT_MODELS = {'groq': 'openai/gpt-oss-20b', 'openai': 'gpt-5.6-luna'}
KEY_VARIABLES = {'groq': 'GROQ_API_KEY', 'openai': 'OPENAI_API_KEY'}
# Reviewed free-tier + strict-schema models, checked 2026-10-17. This is routing
# policy, NOT verification of the account's billing tier; owner must stay Free.
FREE_MODELS = {'openai/gpt-oss-20b', 'openai/gpt-oss-120b', 'qwen/qwen3.8-27b'}


@dataclass(frozen=True)
class LLMConfig:
    enabled: bool = False
    provider: str = 'groq'
    model: str = 'openai/gpt-oss-20b'
    key: str = field(default='', repr=False)
    free_only: bool = True
    max_run: int = 4
    max_process: int = 20
    max_output_tokens: int = 2048
    timeout_seconds: int = 30
    configuration_error: str | None = None

    @property
    def key_variable(self):
        return KEY_VARIABLES.get(self.provider, 'unsupported_provider')

    def check(self):
        if self.configuration_error:
            raise LanguageError(self.configuration_error)
        if self.provider not in DEFAULT_MODELS:
            raise LanguageError('Unsupported LLM_PROVIDER. Supported: groq, openai. No request made.')
        if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._:/-]{0,119}', self.model):
            raise LanguageError('LLM_MODEL is invalid. No request made.')
        if self.free_only and (self.provider != 'groq' or self.model not in FREE_MODELS):
            raise LanguageError('LLM_FREE_ONLY blocks this provider/model. Select a reviewed Groq free-tier model; no paid fallback is allowed.')
        if not (0 <= self.max_run <= 10 and 0 <= self.max_process <= 100
                and 256 <= self.max_output_tokens <= 4096 and 5 <= self.timeout_seconds <= 60):
            raise LanguageError('LLM limits outside allowed POC bounds. No request made.')

    def error(self):
        try:
            self.check()
        except LanguageError as exc:
            return str(exc)
        return None

    @classmethod
    def from_env(cls, environment: Mapping[str, str] | None = None):
        env = os.environ if environment is None else environment
        provider = env.get('LLM_PROVIDER', 'groq').strip().lower()
        model = env.get('LLM_MODEL', '').strip() or DEFAULT_MODELS.get(provider, '')
        key = env.get(KEY_VARIABLES.get(provider, ''), '').strip()
        values = dict(provider=provider, model=model, key=key)
        try:
            def boolean(name, default):
                value = env.get(name, default).strip().lower()
                if value not in {'true', 'false'}:
                    raise ValueError
                return value == 'true'
            values.update(enabled=boolean('COLLECTIONS_LLM_ENABLED', 'false'),
                free_only=boolean('LLM_FREE_ONLY', 'true'),
                max_run=int(env.get('LLM_MAX_CALLS_PER_RUN', '4')),
                max_process=int(env.get('LLM_MAX_CALLS_PER_PROCESS', '20')),
                max_output_tokens=int(env.get('LLM_MAX_OUTPUT_TOKENS', '2048' if provider == 'groq' else '1024')),
                timeout_seconds=int(env.get('LLM_TIMEOUT_SECONDS', '30')))
        except (TypeError, ValueError):
            values.update(enabled=False, configuration_error='Invalid boolean/numeric LLM setting. API calls disabled; check .env.')
        return cls(**values)
