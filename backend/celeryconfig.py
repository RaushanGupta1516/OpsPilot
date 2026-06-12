from celery.schedules import crontab

# run monitor task every 30 seconds
beat_schedule = {
    "monitor-all-apps": {
        "task": "app.workers.monitor_task.run_monitoring_cycle",
        "schedule": 30.0,  # every 30 seconds
    },
}

timezone = "UTC"