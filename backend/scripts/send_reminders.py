"""Email today's plan to everyone who turned email reminders on.

    python -m scripts.send_reminders                # today
    python -m scripts.send_reminders --dry-run      # who would get one
    python -m scripts.send_reminders --date 2026-08-03

Run from the `backend` directory so the relative DATABASE_URL resolves. Safe to
run repeatedly: each student is stamped with the day they were last emailed.

Use this when you have somewhere to run a cron. If you do not, the same work is
available as POST /api/v1/tasks/daily-reminders for an external scheduler.
"""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import date, datetime

from app.core.config import settings
from app.db.session import SessionLocal
from app.services import reminders


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--date",
        help="Day to send for, as YYYY-MM-DD. Defaults to today.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report who would be emailed without sending anything.",
    )
    parser.add_argument("--quiet", action="store_true", help="Only print the summary.")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.WARNING if args.quiet else logging.INFO,
        format="%(levelname)s  %(name)s  %(message)s",
    )

    for_date: date | None = None
    if args.date:
        try:
            for_date = datetime.strptime(args.date, "%Y-%m-%d").date()
        except ValueError:
            print(f"-> not a date: {args.date!r} (expected YYYY-MM-DD)")
            return 2

    if not settings.email_enabled:
        print(
            "-> email is not configured, so nothing can be sent.\n"
            "   Set EMAIL_PROVIDER with EMAIL_API_KEY (brevo/resend) or the "
            "SMTP_* variables."
        )
        return 1

    with SessionLocal() as db:
        run = reminders.send_daily_reminders(db, for_date=for_date, dry_run=args.dry_run)

    verb = "would email" if args.dry_run else "emailed"
    print(f"\n-> {run.day}: {run.opted_in} opted in, {verb} {run.sent}")
    print(f"   skipped: {run.no_sessions} with nothing scheduled, "
          f"{run.already_sent} already sent today")
    if run.failed:
        print(f"   FAILED: {run.failed} (see the log above for the provider error)")
    if run.recipients:
        print("   recipients: " + ", ".join(run.recipients))
    return 1 if run.failed else 0


if __name__ == "__main__":
    sys.exit(main())
