import os
from celery import Celery
from kombu import Queue
from src.utils.config_loader import load_config

app = Celery('digestbot')

# Load YAML config
config = load_config('config/celery.yaml')
app.conf.update(config.get('celery', {}))

redis_url = os.getenv('REDIS_URL')
if redis_url:
    app.conf.broker_url = redis_url
    app.conf.result_backend = os.getenv('CELERY_RESULT_BACKEND', redis_url.replace('/0', '/1', 1))

# Queues
app.conf.task_queues = (
    Queue('collect', routing_key='collect.#'),
    Queue('extract', routing_key='extract.#'),
    Queue('analyze', routing_key='analyze.#'),
    Queue('summarize', routing_key='summarize.#'),
    Queue('score', routing_key='score.#'),
    Queue('dispatch', routing_key='dispatch.#'),
    Queue('failed', routing_key='failed.#'),
)

# Routing
app.conf.task_routes = {
    'src.orchestrator.trigger_all': {'queue': 'collect'},
    'src.collectors.*': {'queue': 'collect'},
    'src.processors.extractor.*': {'queue': 'extract'},
    'src.processors.analyzer.*': {'queue': 'analyze'},
    'src.processors.summarizer.*': {'queue': 'summarize'},
    'src.processors.scorer.*': {'queue': 'score'},
    'src.dispatchers.*': {'queue': 'dispatch'},
}

# Resilience
app.conf.task_acks_late = True
app.conf.task_reject_on_worker_lost = True
app.conf.worker_prefetch_multiplier = 1

# Import tasks to ensure discovery (MUST be after app is defined but before it is used by workers)
import src.orchestrator
import src.processors.extractor
import src.processors.analyzer
import src.processors.summarizer
import src.processors.scorer
import src.dispatchers.telegram

# Beat schedule
from celery.schedules import crontab
app.conf.beat_schedule = {
    'daily-digest': {
        'task': 'src.orchestrator.trigger_all',
        'schedule': crontab(hour=7, minute=0),
    },
}

if __name__ == '__main__':
    app.start()
