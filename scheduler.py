# scheduler.py — Run the pipeline daily at 11:55 PM

from apscheduler.schedulers.blocking import BlockingScheduler

from config import SCHEDULE_HOUR, SCHEDULE_MINUTE
from main import run

scheduler = BlockingScheduler(timezone="Asia/Singapore")

scheduler.add_job(
    run,
    trigger="cron",
    hour=SCHEDULE_HOUR,
    minute=SCHEDULE_MINUTE,
)

print(f"[scheduler] Tech News Agent scheduled at {SCHEDULE_HOUR:02d}:{SCHEDULE_MINUTE:02d} SGT daily.")
print("[scheduler] Running... press Ctrl+C to stop.")

try:
    scheduler.start()
except KeyboardInterrupt:
    print("[scheduler] Stopped.")
