"""Reminder Scheduler — fire reminders on time and send Feishu messages."""

import asyncio
import logging
import time

from feishu_kit.core.client import FeishuClient
from feishu_kit.modules.butler.store import Store

logger = logging.getLogger(__name__)

_CHECK_INTERVAL = 30  # seconds between checks


class ReminderScheduler:
    """Background task that fires pending reminders."""

    def __init__(self, store: Store, client: FeishuClient):
        self._store = store
        self._client = client
        self._task: asyncio.Task | None = None
        self._running = False
        self._scheduled: dict[int, asyncio.Task] = {}  # reminder_id -> timer task

    async def start(self) -> None:
        """Start the scheduler loop."""
        self._running = True
        self._task = asyncio.create_task(self._loop())
        # Recover pending reminders
        await self._recover()
        logger.info("Reminder scheduler started")

    async def stop(self) -> None:
        """Stop the scheduler."""
        self._running = False
        for t in self._scheduled.values():
            t.cancel()
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Reminder scheduler stopped")

    def schedule(self, reminder_id: int, fire_at: float) -> None:
        """Schedule a single reminder to fire at the given time."""
        if reminder_id in self._scheduled:
            return
        delay = max(0, fire_at - time.time())
        self._scheduled[reminder_id] = asyncio.create_task(
            self._fire_after(reminder_id, delay)
        )

    async def _fire_after(self, reminder_id: int, delay: float) -> None:
        """Wait for delay then fire the reminder."""
        try:
            await asyncio.sleep(delay)
            await self._fire(reminder_id)
        except asyncio.CancelledError:
            pass
        finally:
            self._scheduled.pop(reminder_id, None)

    async def _fire(self, reminder_id: int) -> None:
        """Fire a single reminder."""
        from feishu_kit.modules.messaging.service import MessagingService
        import json

        # Get reminder details
        reminders = self._store.get_pending_reminders()
        reminder = next((r for r in reminders if r["id"] == reminder_id), None)
        if not reminder:
            return

        try:
            svc = MessagingService(self._client)
            content = json.dumps({"text": f"提醒: {reminder['message']}"})
            await svc.send_message(
                reminder["open_id"], "text", content, "open_id"
            )
            self._store.mark_reminder_fired(reminder_id)
            self._store.audit(
                "reminder_fired", str(reminder_id),
                reminder["message"][:50], "AUTO_EXECUTE",
                reminder["chat_id"], reminder["open_id"],
            )
            logger.info("Reminder fired: id=%d msg=%s", reminder_id, reminder["message"][:30])

            # Handle recurring
            if reminder.get("recurring"):
                next_fire = self._next_occurrence(reminder["recurring"])
                if next_fire:
                    new_id = self._store.create_reminder(
                        reminder["chat_id"], reminder["open_id"],
                        reminder["message"], next_fire,
                        recurring=reminder["recurring"],
                        goal_id=reminder.get("goal_id"),
                    )
                    self.schedule(new_id, next_fire)

        except Exception as e:
            logger.error("Failed to fire reminder %d: %s", reminder_id, e, exc_info=True)

    async def _recover(self) -> None:
        """Recover and reschedule pending reminders after restart."""
        pending = self._store.get_pending_reminders()
        now = time.time()
        for r in pending:
            if r["fire_at"] <= now:
                # Already due — fire immediately
                await self._fire(r["id"])
            else:
                self.schedule(r["id"], r["fire_at"])
        if pending:
            logger.info("Recovered %d pending reminders", len(pending))

    async def _loop(self) -> None:
        """Periodic check for missed reminders (safety net)."""
        while self._running:
            try:
                await asyncio.sleep(_CHECK_INTERVAL)
                due = self._store.get_pending_reminders()
                for r in due:
                    if r["id"] not in self._scheduled:
                        await self._fire(r["id"])
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Reminder loop error: %s", e)

    def _next_occurrence(self, recurring: str) -> float | None:
        """Calculate next fire time for a recurring reminder.

        Supports: 'daily', 'weekly', 'hourly', 'Xm' (every X minutes), 'Xh' (every X hours)
        """
        now = time.time()
        recurring = recurring.lower().strip()

        if recurring == "daily":
            return now + 86400
        elif recurring == "weekly":
            return now + 604800
        elif recurring == "hourly":
            return now + 3600
        else:
            # Try "Xm" or "Xh" format
            import re
            m = re.match(r"(\d+)\s*(m|min|minutes?|h|hr|hours?)", recurring)
            if m:
                amount = int(m.group(1))
                unit = m.group(2)[0]  # 'm' or 'h'
                if unit == "m":
                    return now + amount * 60
                elif unit == "h":
                    return now + amount * 3600
        return None
