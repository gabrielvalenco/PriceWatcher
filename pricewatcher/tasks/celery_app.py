"""
Celery configuration for PriceWatcher
"""
import os
from celery import Celery

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Redis configuration
redis_host = os.getenv('REDIS_HOST', 'localhost')
redis_port = os.getenv('REDIS_PORT', '6379')
redis_db = os.getenv('REDIS_DB', '0')

# Create Celery app
app = Celery(
    'pricewatcher',
    broker=f'redis://{redis_host}:{redis_port}/{redis_db}',
    backend=f'redis://{redis_host}:{redis_port}/{redis_db}',
    include=[
        'pricewatcher.tasks.price_tasks', 
        'pricewatcher.tasks.notification_tasks'
    ]
)

# Configure Celery
app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    worker_hijack_root_logger=False,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    result_expires=86400,  # 1 day
    # Task schedules
    beat_schedule={
        'update-prices-every-6-hours': {
            'task': 'pricewatcher.tasks.price_tasks.update_all_prices',
            'schedule': 21600.0,  # 6 hours
        },
        'check-alerts-hourly': {
            'task': 'pricewatcher.tasks.price_tasks.check_price_alerts',
            'schedule': 3600.0,  # 1 hour
        },
    },
)

if __name__ == '__main__':
    app.start()
