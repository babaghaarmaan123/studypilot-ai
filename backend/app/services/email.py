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
from dataclasses import dataclass, field
from datetime import date
from email.message import EmailMessage
from email.utils import formataddr, make_msgid, parseaddr

from app.core.config import settings

logger = logging.getLogger(__name__)

#: Header names whose values must never reach a log or a diagnostic response.
_SECRET_HEADERS = {"api-key", "authorization"}


@dataclass
class ProviderResult:
    """The outcome of one HTTP call to an email provider.

    Carries the status and body rather than collapsing them to a boolean, so a
    diagnostic can report exactly what the provider said. A rejected message is
    recorded nowhere in the provider's own dashboard, so this is the only place
    the reason exists.
    """

    ok: bool
    status: int | None = None
    body: str = ""
    error: str | None = None

    def as_dict(self) -> dict:
        return {
            "ok": self.ok,
            "http_status": self.status,
            "response_body": self.body,
            "error": self.error,
        }


def _redact_headers(headers: dict) -> dict:
    return {
        key: ("<redacted>" if key.lower() in _SECRET_HEADERS else value)
        for key, value in headers.items()
    }


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
    # Logged before the attempt, not only after it. Without this line the logs
    # cannot distinguish "the provider refused" from "nothing ever called this",
    # and those have completely different causes: one is a credential or sender
    # problem, the other is a missing call site.
    logger.info(
        "Email attempt: provider=%s from=%s to=%s subject=%r",
        provider,
        settings.email_from_address,
        to,
        subject,
    )

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
def _post_json(
    url: str, payload: dict, headers: dict, provider: str
) -> ProviderResult:
    """POST JSON and treat any 2xx as accepted.

    Every outcome is logged, including success, so a Render log can answer three
    separate questions on its own: was a request made at all, did the provider
    accept it, and if not, what did it say. A provider that rejects a message
    never records it in its own dashboard, so these lines are the only trace.
    """
    body_bytes = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body_bytes,
        headers={"Content-Type": "application/json", **headers},
        method="POST",
    )
    logger.info("%s request: POST %s (%d bytes)", provider, url, len(body_bytes))
    if settings.EMAIL_LOG_PAYLOAD:
        # Off by default: the payload contains the whole message, which for a
        # reset email means the code itself, and nobody wants that in a log by
        # default. Turn it on to debug a provider rejection, then turn it off.
        logger.info(
            "%s payload: headers=%s body=%s",
            provider,
            json.dumps(_redact_headers(dict(request.header_items()))),
            json.dumps(payload)[:4000],
        )
    try:
        with urllib.request.urlopen(
            request, timeout=settings.EMAIL_API_TIMEOUT_SECONDS
        ) as response:
            body = response.read()[:800].decode("utf-8", "replace")
            if 200 <= response.status < 300:
                # The body carries the provider's message id, which is what to
                # search for in their dashboard when a message is accepted but
                # never arrives.
                logger.info(
                    "%s accepted the message: HTTP %s %s", provider, response.status, body
                )
                return ProviderResult(True, response.status, body)
            logger.error(
                "%s rejected the message: HTTP %s %s", provider, response.status, body
            )
            return ProviderResult(False, response.status, body)
    except urllib.error.HTTPError as error:
        # The body carries the real reason: an unverified sender, a bad key, a
        # quota. Worth logging verbatim, it is the difference between a
        # five minute fix and an afternoon.
        detail = error.read()[:800].decode("utf-8", "replace")
        logger.error("%s rejected the message: HTTP %s %s", provider, error.code, detail)
        return ProviderResult(False, error.code, detail)
    except Exception as error:
        logger.exception("Could not reach %s (POST %s)", provider, url)
        return ProviderResult(False, None, "", f"{type(error).__name__}: {error}")


def _warn_on_odd_brevo_key(key: str) -> None:
    if not key.startswith("xkeysib-"):
        # Brevo shows the key once, in a box that wraps, and it is easy to copy
        # only the part after the prefix. The API then answers 401, which reads
        # as a revoked or wrong key rather than a truncated one.
        logger.warning(
            "EMAIL_API_KEY does not begin with 'xkeysib-'. Brevo v3 keys do; if "
            "this send fails with a 401, the prefix is probably missing from the "
            "copied value. An SMTP key ('xsmtpsib-') will not work here either, "
            "it needs an API key."
        )


def brevo_payload(to: str, subject: str, text_body: str, html_body: str | None) -> dict:
    """The exact JSON body sent to Brevo. Shared with the diagnostics endpoint,
    so what a diagnostic reports is what a real send transmits."""
    _, address = parseaddr(settings.email_from_address or "")
    payload: dict = {
        "sender": {"email": address, "name": settings.EMAIL_FROM_NAME},
        "to": [{"email": to}],
        "subject": subject,
        "textContent": text_body,
    }
    if html_body:
        payload["htmlContent"] = html_body
    return payload


BREVO_ENDPOINT = "https://api.brevo.com/v3/smtp/email"


def _brevo_headers() -> dict:
    return {"api-key": settings.EMAIL_API_KEY or "", "accept": "application/json"}


def _send_via_brevo(
    to: str, subject: str, text_body: str, html_body: str | None
) -> bool:
    _warn_on_odd_brevo_key(settings.EMAIL_API_KEY or "")
    result = _post_json(
        BREVO_ENDPOINT,
        brevo_payload(to, subject, text_body, html_body),
        _brevo_headers(),
        "Brevo",
    )
    if result.ok:
        logger.info("Sent %r to %s via Brevo", subject, to)
    return result.ok


RESEND_ENDPOINT = "https://api.resend.com/emails"


def resend_payload(to: str, subject: str, text_body: str, html_body: str | None) -> dict:
    payload: dict = {
        "from": formataddr((settings.EMAIL_FROM_NAME, settings.email_from_address)),
        "to": [to],
        "subject": subject,
        "text": text_body,
    }
    if html_body:
        payload["html"] = html_body
    return payload


def _send_via_resend(
    to: str, subject: str, text_body: str, html_body: str | None
) -> bool:
    result = _post_json(
        RESEND_ENDPOINT,
        resend_payload(to, subject, text_body, html_body),
        {"Authorization": f"Bearer {settings.EMAIL_API_KEY or ''}"},
        "Resend",
    )
    if result.ok:
        logger.info("Sent %r to %s via Resend", subject, to)
    return result.ok


# ---------------------------------------------------------------------------
# Diagnostics
# ---------------------------------------------------------------------------
def runtime_config() -> dict:
    """The email settings actually in effect in this process.

    Read from the live `settings` object rather than inferred from a file, so it
    reflects what the running container was given. Never includes the API key:
    its presence, length and prefix are enough to tell a missing key from a
    truncated one or an SMTP key pasted by mistake, which are the three ways it
    goes wrong.
    """
    key = settings.EMAIL_API_KEY or ""
    return {
        "environment": settings.ENVIRONMENT,
        "email_enabled": settings.email_enabled,
        "EMAIL_PROVIDER": settings.EMAIL_PROVIDER,
        "email_provider_normalised": settings.email_provider,
        "EMAIL_FROM": settings.EMAIL_FROM,
        "EMAIL_FROM_NAME": settings.EMAIL_FROM_NAME,
        "email_from_address_used": settings.email_from_address,
        "EMAIL_API_KEY_present": bool(key),
        "EMAIL_API_KEY_length": len(key),
        "EMAIL_API_KEY_prefix": key.split("-")[0] + "-" if "-" in key else key[:4],
        "EMAIL_API_KEY_looks_like_brevo_api_key": key.startswith("xkeysib-"),
        "SMTP_HOST": settings.SMTP_HOST,
        "SMTP_PORT": settings.SMTP_PORT,
        "EMAIL_LOG_PAYLOAD": settings.EMAIL_LOG_PAYLOAD,
    }


def probe(to: str) -> dict:
    """Send a real test message and report the request and the provider's reply.

    Returns the exact payload transmitted and the verbatim response, which is
    the only way to see a rejection: providers do not record refused messages in
    their dashboards, so there is nothing to look up afterwards.
    """
    provider = settings.email_provider
    report: dict = {"config": runtime_config(), "provider": provider, "to": to}

    if not settings.email_enabled:
        report["attempted"] = False
        report["reason"] = (
            "Email is not configured: email_enabled is false, so no request was "
            "made. Check EMAIL_PROVIDER, EMAIL_API_KEY and EMAIL_FROM."
        )
        return report

    subject = "StudyPilot email delivery test"
    text_body = (
        "This is a test message from StudyPilot's diagnostics endpoint.\n\n"
        "If you are reading it, transactional email works: the provider "
        "accepted the message and delivered it.\n"
    )
    html_body = (
        "<p>This is a test message from StudyPilot's diagnostics endpoint.</p>"
        "<p>If you are reading it, transactional email works.</p>"
    )

    if provider == "brevo":
        _warn_on_odd_brevo_key(settings.EMAIL_API_KEY or "")
        payload = brevo_payload(to, subject, text_body, html_body)
        endpoint, headers = BREVO_ENDPOINT, _brevo_headers()
    elif provider == "resend":
        payload = resend_payload(to, subject, text_body, html_body)
        endpoint = RESEND_ENDPOINT
        headers = {"Authorization": f"Bearer {settings.EMAIL_API_KEY or ''}"}
    else:
        report["attempted"] = bool(_send_via_smtp(to, subject, text_body, html_body))
        report["note"] = (
            "The smtp provider has no HTTP response to report; see the Render "
            "log for the SMTP conversation."
        )
        return report

    result = _post_json(endpoint, payload, headers, provider.title())
    report["attempted"] = True
    report["endpoint"] = endpoint
    report["request_headers"] = _redact_headers(
        {"Content-Type": "application/json", **headers}
    )
    # Bodies trimmed: the point is to see the sender, recipient and subject the
    # provider was given, not to re-read the template.
    report["request_payload"] = {
        **payload,
        **{
            key: f"<{len(value)} chars>"
            for key, value in payload.items()
            if key in {"textContent", "htmlContent", "text", "html"}
        },
    }
    report.update(result.as_dict())
    return report


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


# ---------------------------------------------------------------------------
# Daily plan
# ---------------------------------------------------------------------------
def send_daily_plan(to: str, name: str, day: date, sessions: list) -> bool:
    """Email one day's schedule to a student who asked for email reminders.

    `sessions` are StudySession rows for that day, already ordered. Callers only
    send when there is at least one, because "nothing scheduled today" is not
    worth an email.
    """
    first_name = (name or "there").split()[0]
    pretty_day = day.strftime("%A %d %B")
    total = sum(s.duration_minutes or 0 for s in sessions)
    hours, minutes = divmod(total, 60)
    total_text = f"{hours}h {minutes:02d}m" if hours else f"{minutes}m"
    count = len(sessions)
    subject = (
        f"Your StudyPilot plan for {day.strftime('%A')}: "
        f"{count} session{'s' if count != 1 else ''}, {total_text}"
    )

    def _ends(start: str, duration: int) -> str:
        try:
            hh, mm = (int(part) for part in start.split(":")[:2])
        except (ValueError, TypeError):
            return ""
        total_minutes = hh * 60 + mm + (duration or 0)
        return f"{(total_minutes // 60) % 24:02d}:{total_minutes % 60:02d}"

    lines = []
    rows = []
    for session in sessions:
        start = (session.start_time or "")[:5]
        finish = _ends(session.start_time or "", session.duration_minutes or 0)
        span = f"{start}-{finish}" if finish else start
        subject_name = session.subject.name if session.subject else ""
        label = f"{subject_name}: {session.title}" if subject_name else session.title
        lines.append(f"  {span}  {label}")
        rows.append(
            f'<tr>'
            f'<td style="padding:8px 12px 8px 0;white-space:nowrap;font-family:'
            f"'SFMono-Regular',Consolas,monospace;font-size:14px;color:#157976\">{span}</td>"
            f'<td style="padding:8px 0;font-size:14px;color:#151b28">{label}</td>'
            f"</tr>"
        )

    text_body = (
        f"Morning {first_name},\n\n"
        f"Here is your plan for {pretty_day} "
        f"({count} session{'s' if count != 1 else ''}, {total_text} in total):\n\n"
        + "\n".join(lines)
        + "\n\nOpen StudyPilot to start a session or move things around.\n\n"
        "You are getting this because email reminders are on. Turn them off in "
        "Settings if you would rather not.\n"
    )

    html_body = f"""\
<!doctype html>
<html>
  <body style="margin:0;padding:24px;background:#f6f7f9;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif;color:#151b28">
    <div style="max-width:520px;margin:0 auto;background:#ffffff;border:1px solid #e4e7ec;border-radius:14px;padding:32px">
      <p style="margin:0 0 4px;font-size:18px;font-weight:700">Your plan for {pretty_day}</p>
      <p style="margin:0 0 20px;font-size:14px;color:#5a6274">
        {count} session{'s' if count != 1 else ''} &middot; {total_text} in total
      </p>
      <table style="width:100%;border-collapse:collapse">{''.join(rows)}</table>
      <p style="margin:24px 0 0;font-size:13px;color:#5a6274">
        You are getting this because email reminders are on. You can turn them
        off in Settings.
      </p>
    </div>
    <p style="max-width:520px;margin:16px auto 0;font-size:12px;color:#8a91a0;text-align:center">
      {settings.EMAIL_FROM_NAME}
    </p>
  </body>
</html>
"""
    return send_email(to, subject, text_body, html_body)
