"""Outbound email, over SMTP or a provider's HTTPS API.

Deliberately stdlib only, no provider SDK and no new dependency: `smtplib` for
SMTP, `urllib.request` for the HTTP providers.

Two transports exist because SMTP does not work everywhere. Render blocks
outbound ports 25, 465 and 587 on free web services, so on a free instance every
SMTP send times out no matter how correct the credentials are. The HTTPS
providers go out over 443 and are unaffected, and Brevo in particular will verify
a single sender address without requiring a domain.

When nothing is configured the message is written to the log rather than sent.
That keeps local development working with no mail server, and in production
`Settings._guard_production` logs an error at start-up so the gap is visible
rather than silent.

Sending is blocking, and a slow or unreachable provider would otherwise hold an
HTTP worker for the whole timeout, so callers hand this to a background task.
"""

from __future__ import annotations

import json
import logging
import smtplib
import ssl
import urllib.error
import urllib.request
from email.message import EmailMessage
from email.utils import formataddr, make_msgid, parseaddr

from app.core.config import settings

logger = logging.getLogger(__name__)


def send_email(
    to: str, subject: str, text_body: str, html_body: str | None = None
) -> bool:
    """Send one message. Returns whether a provider accepted it.

    Never raises: a delivery failure must not turn into a 500 for the student,
    and the caller has already told them to check their inbox.
    """
    if not settings.email_enabled:
        logger.warning(
            "Email is not configured, so this message was not sent.\n"
            "  To: %s\n  Subject: %s\n%s",
            to,
            subject,
            text_body,
        )
        return False

    provider = settings.email_provider
    if provider == "brevo":
        return _send_via_brevo(to, subject, text_body, html_body)
    if provider == "resend":
        return _send_via_resend(to, subject, text_body, html_body)
    if provider != "smtp":
        logger.error(
            "Unknown EMAIL_PROVIDER %r; expected smtp, brevo or resend.", provider
        )
        return False
    return _send_via_smtp(to, subject, text_body, html_body)


# ---------------------------------------------------------------------------
# HTTPS providers
# ---------------------------------------------------------------------------
def _post_json(url: str, payload: dict, headers: dict, provider: str) -> bool:
    """POST JSON and treat any 2xx as accepted."""
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", **headers},
        method="POST",
    )
    try:
        with urllib.request.urlopen(
            request, timeout=settings.EMAIL_API_TIMEOUT_SECONDS
        ) as response:
            if 200 <= response.status < 300:
                return True
            logger.error(
                "%s rejected the message: HTTP %s %s",
                provider,
                response.status,
                response.read()[:400],
            )
            return False
    except urllib.error.HTTPError as error:
        # The body carries the real reason: an unverified sender, a bad key, a
        # quota. Worth logging verbatim, it is the difference between a
        # five minute fix and an afternoon.
        detail = error.read()[:400].decode("utf-8", "replace")
        logger.error("%s rejected the message: HTTP %s %s", provider, error.code, detail)
        return False
    except Exception:
        logger.exception("Could not reach %s", provider)
        return False


def _send_via_brevo(
    to: str, subject: str, text_body: str, html_body: str | None
) -> bool:
    name, address = parseaddr(settings.email_from_address or "")
    payload: dict = {
        "sender": {"email": address, "name": settings.EMAIL_FROM_NAME},
        "to": [{"email": to}],
        "subject": subject,
        "textContent": text_body,
    }
    if html_body:
        payload["htmlContent"] = html_body
    ok = _post_json(
        "https://api.brevo.com/v3/smtp/email",
        payload,
        {"api-key": settings.EMAIL_API_KEY or "", "accept": "application/json"},
        "Brevo",
    )
    if ok:
        logger.info("Sent %r to %s via Brevo", subject, to)
    return ok


def _send_via_resend(
    to: str, subject: str, text_body: str, html_body: str | None
) -> bool:
    payload: dict = {
        "from": formataddr((settings.EMAIL_FROM_NAME, settings.email_from_address)),
        "to": [to],
        "subject": subject,
        "text": text_body,
    }
    if html_body:
        payload["html"] = html_body
    ok = _post_json(
        "https://api.resend.com/emails",
        payload,
        {"Authorization": f"Bearer {settings.EMAIL_API_KEY or ''}"},
        "Resend",
    )
    if ok:
        logger.info("Sent %r to %s via Resend", subject, to)
    return ok


# ---------------------------------------------------------------------------
# SMTP
# ---------------------------------------------------------------------------
def _send_via_smtp(
    to: str, subject: str, text_body: str, html_body: str | None = None
) -> bool:
    sender = settings.email_from_address
    message = EmailMessage()
    message["From"] = formataddr((settings.EMAIL_FROM_NAME, sender))
    message["To"] = to
    message["Subject"] = subject
    # An explicit Message-ID and a text part alongside the HTML both help with
    # spam scoring, which matters for transactional mail nobody has opted into.
    message["Message-ID"] = make_msgid(domain=sender.split("@")[-1])
    message.set_content(text_body)
    if html_body:
        message.add_alternative(html_body, subtype="html")

    try:
        if settings.SMTP_USE_SSL:
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL(
                settings.SMTP_HOST,
                settings.SMTP_PORT,
                timeout=settings.SMTP_TIMEOUT_SECONDS,
                context=context,
            ) as smtp:
                _authenticate(smtp)
                smtp.send_message(message)
        else:
            with smtplib.SMTP(
                settings.SMTP_HOST,
                settings.SMTP_PORT,
                timeout=settings.SMTP_TIMEOUT_SECONDS,
            ) as smtp:
                smtp.ehlo()
                if settings.SMTP_USE_TLS:
                    smtp.starttls(context=ssl.create_default_context())
                    smtp.ehlo()
                _authenticate(smtp)
                smtp.send_message(message)
    except (TimeoutError, OSError) as error:
        # A timeout here is almost always a blocked port rather than a bad
        # password, and on Render's free tier it always is. Say so, because the
        # symptom otherwise reads as an authentication problem.
        logger.error(
            "Could not reach the SMTP server at %s:%s (%s). If this is a free "
            "Render web service, outbound SMTP ports are blocked: set "
            "EMAIL_PROVIDER=brevo with an EMAIL_API_KEY instead, or move to a "
            "paid instance.",
            settings.SMTP_HOST,
            settings.SMTP_PORT,
            error,
        )
        return False
    except Exception:
        # Includes authentication failures and refused senders. Logged with a
        # traceback because this is the one thing that silently locks a student
        # out of their account.
        logger.exception("Could not send email to %s (subject: %s)", to, subject)
        return False

    logger.info("Sent %r to %s via SMTP", subject, to)
    return True


def _authenticate(smtp: smtplib.SMTP) -> None:
    if settings.SMTP_USERNAME and settings.SMTP_PASSWORD:
        smtp.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)


# ---------------------------------------------------------------------------
# Password reset
# ---------------------------------------------------------------------------
def send_password_reset_code(to: str, name: str, code: str) -> bool:
    """Email a password reset code.

    The code is spaced in the HTML for legibility but kept unspaced in the text
    part, so copying it out of either version and pasting it still works after
    the whitespace stripping the reset form does.
    """
    first_name = (name or "there").split()[0]
    minutes = settings.RESET_CODE_EXPIRE_MINUTES
    subject = f"Your StudyPilot password reset code: {code}"

    text_body = (
        f"Hi {first_name},\n\n"
        f"Use this code to reset your StudyPilot password:\n\n"
        f"    {code}\n\n"
        f"It expires in {minutes} minutes and can only be used once.\n\n"
        "If you did not ask to reset your password you can ignore this email. "
        "Your password has not been changed.\n\n"
        f"{settings.EMAIL_FROM_NAME}\n"
    )

    digits = "".join(f'<span style="padding:0 6px">{d}</span>' for d in code)
    html_body = f"""\
<!doctype html>
<html>
  <body style="margin:0;padding:24px;background:#f6f7f9;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif;color:#151b28">
    <div style="max-width:520px;margin:0 auto;background:#ffffff;border:1px solid #e4e7ec;border-radius:14px;padding:32px">
      <p style="margin:0 0 20px;font-size:18px;font-weight:700">Reset your password</p>
      <p style="margin:0 0 8px;font-size:15px;line-height:1.55">Hi {first_name},</p>
      <p style="margin:0 0 24px;font-size:15px;line-height:1.55">
        Enter this code on the password reset screen:
      </p>
      <div style="margin:0 0 24px;padding:18px;background:#f2fbfa;border:1px solid #a8e0dc;border-radius:12px;text-align:center;font-size:30px;font-weight:700;letter-spacing:3px;color:#157976;font-family:'SFMono-Regular',Consolas,monospace">
        {digits}
      </div>
      <p style="margin:0 0 20px;font-size:14px;line-height:1.55;color:#5a6274">
        The code expires in {minutes} minutes and can only be used once.
      </p>
      <p style="margin:0;font-size:14px;line-height:1.55;color:#5a6274">
        If you did not ask to reset your password you can ignore this email.
        Your password has not been changed.
      </p>
    </div>
    <p style="max-width:520px;margin:16px auto 0;font-size:12px;color:#8a91a0;text-align:center">
      {settings.EMAIL_FROM_NAME}
    </p>
  </body>
</html>
"""
    return send_email(to, subject, text_body, html_body)
