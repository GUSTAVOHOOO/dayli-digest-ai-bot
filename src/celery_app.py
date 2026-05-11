from celery import Celery
from kombu import Queue
from src.utils.config_loader import load_config

app = Celery('digestbot')

# Load YAML config
config = load_config('config/celery.yaml')
app.conf.update(config.get('celery', {}))

# Queues
app.conf.task_queues = (
    Queue('collect', routing_key='collect.#'),
    Queue('extract', routing_key='extract.#'),
    Queue('summarize', routing_key='summarize.#'),
    Queue('score', routing_key='score.#'),
    Queue('dispatch', routing_key='dispatch.#'),
    Queue('failed', routing_key='failed.#'),
)

# Routing
app.conf.task_routes = {
    'src.collectors.*': {'queue': 'collect'},
    'src.processors.extractor.*': {'queue': 'extract'},
    'src.processors.summarizer.*': {'queue': 'summarize'},
    'src.processors.scorer.*': {'queue': 'score'},
    'src.orchestrator.process_dispatch_placeholder': {'queue': 'dispatch'},
    'src.dispatchers.*': {'queue': 'dispatch'},
}

# Resilience
app.conf.task_acks_late = True
app.conf.task_reject_on_worker_lost = True
app.conf.worker_prefetch_multiplier = 1

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
