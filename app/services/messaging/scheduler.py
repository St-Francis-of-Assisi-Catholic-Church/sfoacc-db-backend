"""
Scheduled-message dispatcher.

Polls the `scheduled_messages` table every minute and dispatches any
messages whose `send_at` has passed and whose `status` is PENDING.

Usage (in lifespan):
    from app.services.messaging.scheduler import message_scheduler
    message_scheduler.start()
    ...
    message_scheduler.stop()
"""

import logging
from datetime import datetime, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.core.database import db

logger = logging.getLogger(__name__)

_scheduler = AsyncIOScheduler(timezone="UTC")


async def _dispatch_due_messages():
    """Find and dispatch all due scheduled messages."""
    from app.models.messaging import ScheduledMessage, ScheduledMessageStatus
    from app.models.parishioner import Parishioner
    from app.services.sms.service import sms_service
    from app.services.email.service import email_service
    from app.core.config import settings

    now = datetime.now(timezone.utc)

    with db.session() as session:
        pending = (
            session.query(ScheduledMessage)
            .filter(
                ScheduledMessage.status == ScheduledMessageStatus.PENDING,
                ScheduledMessage.send_at <= now,
            )
            .all()
        )

        if not pending:
            return

        logger.info(f"Dispatching {len(pending)} scheduled message(s)")

        for job in pending:
            job.status = ScheduledMessageStatus.PROCESSING
            session.commit()

            try:
                parishioner_ids = job.parishioner_ids or []
                parishioners = (
                    session.query(Parishioner)
                    .filter(Parishioner.id.in_(parishioner_ids))
                    .all()
                )

                sent = 0
                for p in parishioners:
                    full_name = f"{p.first_name} {p.last_name}"
                    context = {
                        "parishioner_name": full_name,
                        "church_name": settings.CHURCH_NAME,
                        "church_contact": settings.CHURCH_CONTACT,
                        "new_church_id": p.new_church_id or "N/A",
                        "event_name": job.event_name or "Parish Event",
                        "event_date": job.event_date or "Sunday",
                        "event_time": job.event_time or "10:00 AM",
                    }

                    dispatched = False

                    if job.channel in ("sms", "both") and p.mobile_number:
                        if job.template == "custom_message" and job.custom_message:
                            try:
                                msg = job.custom_message.format(**context)
                            except KeyError:
                                msg = job.custom_message
                            sms_service.send_sms(phone_numbers=[p.mobile_number], message=msg)
                        else:
                            sms_service.send_from_template(
                                template_name=job.template,
                                phone_numbers=[p.mobile_number],
                                context=context,
                            )
                        dispatched = True

                    if job.channel in ("email", "both") and getattr(p, "email_address", None):
                        if job.template == "custom_message" and job.custom_message:
                            await email_service.send_custom_message(
                                to_email=p.email_address,
                                parishioner_name=full_name,
                                custom_message=job.custom_message,
                                subject=job.subject or "Message from Your Parish",
                                **context,
                            )
                        else:
                            await email_service.send_from_template(
                                template_name=job.template,
                                to_emails=[p.email_address],
                                context=context,
                            )
                        dispatched = True

                    if dispatched:
                        sent += 1

                job.sent_count = sent
                job.status = ScheduledMessageStatus.SENT
                logger.info(f"Scheduled message {job.id} sent to {sent} recipients")

            except Exception as exc:
                logger.error(f"Scheduled message {job.id} failed: {exc}", exc_info=True)
                job.status = ScheduledMessageStatus.FAILED
                job.error_message = str(exc)

            session.commit()


def start():
    """Start the background scheduler (call once at app startup)."""
    if not _scheduler.running:
        _scheduler.add_job(
            _dispatch_due_messages,
            trigger="interval",
            minutes=1,
            id="dispatch_scheduled_messages",
            replace_existing=True,
            misfire_grace_time=30,
        )
        _scheduler.start()
        logger.info("Message scheduler started (interval: 1 min)")


def stop():
    """Stop the scheduler (call at app shutdown)."""
    if _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("Message scheduler stopped")
