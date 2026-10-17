import os
import re
from dataclasses import dataclass, field
from email.utils import parseaddr

from fastapi import HTTPException


def address(value):
    if not isinstance(value,str) or '\n' in value or '\r' in value:
        return ''
    parsed=parseaddr(value)[1].lower()
    return parsed if re.fullmatch(r'[a-z0-9.!#$%&\x27*+/=?^_`{|}~-]+@[a-z0-9.-]+\.[a-z]{2,}',parsed) else ''


@dataclass(frozen=True)
class MailConfig:
    enabled: bool = False
    key: str = field(default='',repr=False)
    owner_token: str = field(default='',repr=False)
    webhook_secret: str = field(default='',repr=False)
    sender: str = 'onboarding@resend.dev'
    recipient: str = ''
    receiving_domain: str = ''
    error: str | None = None

    @classmethod
    def from_env(cls):
        value=os.getenv('EMAIL_ENABLED','false').strip().lower()
        return cls(enabled=value=='true',key=os.getenv('RESEND_API_KEY','').strip(),
            owner_token=os.getenv('EMAIL_OWNER_TOKEN','').strip(),webhook_secret=os.getenv('RESEND_WEBHOOK_SECRET','').strip(),
            sender=os.getenv('EMAIL_FROM','onboarding@resend.dev').strip(),
            recipient=os.getenv('EMAIL_TEST_RECIPIENT','').strip().lower(),
            receiving_domain=os.getenv('EMAIL_RECEIVING_DOMAIN','').strip().lower(),
            error=None if value in {'true','false'} else 'EMAIL_ENABLED must be true or false.')

    def check(self):
        if self.error or not self.enabled:
            raise HTTPException(409,self.error or 'Live email is disabled. No email attempted.')
        if not self.key or len(self.owner_token)<32 or not self.webhook_secret.startswith('whsec_'):
            raise HTTPException(503,'Set private Resend key, webhook secret and owner token (at least32characters).')
        if not address(self.sender) or address(self.recipient)!=self.recipient:
            raise HTTPException(503,'Configure one valid EMAIL_TEST_RECIPIENT and EMAIL_FROM.')
        if not re.fullmatch(r'[a-z0-9](?:[a-z0-9.-]{0,180})\.resend\.app',self.receiving_domain):
            raise HTTPException(503,'Use your Resend-managed receiving subdomain in EMAIL_RECEIVING_DOMAIN.')

    def status(self):
        try:
            self.check(); ready=True; reason=None
        except HTTPException as exc:
            ready=False; reason=exc.detail
        # Recipient is disclosed only after owner authentication by a separate route.
        return {'enabled':self.enabled,'ready':ready,'provider':'resend',
                'mode':'controlled_test_inbox','daily_reservation_cap':10,'configuration_error':reason}
