"""
Celery application for background tasks.
"""
from celery import Celery
from celery.schedules import crontab
from app.core.config import settings

# Create Celery app
celery_app = Celery(
    "marketeye",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.workers.market_data", "app.workers.alerts", "app.workers.portfolio"]
)

# Configure Celery
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
    # Store beat schedule in Redis instead of filesystem
    beat_scheduler="celery.beat:PersistentScheduler",
    beat_schedule_filename="/tmp/celerybeat-schedule",
)

# Periodic tasks schedule
celery_app.conf.beat_schedule = {
    # Update market prices every minute
    "update-market-prices": {
        "task": "app.workers.market_data.update_all_asset_prices",
        "schedule": 60.0,  # Every 60 seconds
    },
    # Evaluate alerts every minute
    "evaluate-alerts": {
        "task": "app.workers.alerts.evaluate_all_alerts",
        "schedule": 60.0,  # Every 60 seconds
    },
    # Update portfolio values every 5 minutes
    "update-portfolios": {
        "task": "app.workers.portfolio.update_all_portfolios",
        "schedule": 300.0,  # Every 5 minutes
    },
    # Clean up old notification logs daily
    "cleanup-notifications": {
        "task": "app.workers.alerts.cleanup_old_notifications",
        "schedule": crontab(hour=0, minute=0),  # Daily at midnight
    },
    # Backfill daily OHLCV after US market close (22:30 UTC / 6:30 PM ET)
    "backfill-daily-prices": {
        "task": "app.workers.market_data.backfill_daily_prices",
        "schedule": crontab(hour=22, minute=30),
    },
}

if __name__ == "__main__":
    celery_app.start()
