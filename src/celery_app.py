import os
try:
    from celery import Celery
    from celery.schedules import crontab
    from kombu import Queue
except ImportError:
    Celery = None

    def Queue(*args, **kwargs):
        return {"args": args, "kwargs": kwargs}

    def crontab(*args, **kwargs):
        return {"args": args, "kwargs": kwargs}

from src.utils.config_loader import load_config


class _LocalTask:
    def __init__(self, func, bind=False, **options):
        self.func = func
        self.bind = bind
        self.name = options.get("name", func.__name__)
        self.max_retries = options.get("max_retries", 0)
        self.request = type("Request", (), {"retries": 0})()

    def __call__(self, *args, **kwargs):
        if self.bind:
            return self.func(self, *args, **kwargs)
        return self.func(*args, **kwargs)

    def run(self, *args, **kwargs):
        return self.__call__(*args, **kwargs)

    def delay(self, *args, **kwargs):
        return self.__call__(*args, **kwargs)

    def apply_async(self, args=None, kwargs=None, countdown=None):
        return self.__call__(*(args or ()), **(kwargs or {}))

    def retry(self, *args, **kwargs):
        raise RuntimeError("celery_unavailable_retry_requested")


class _LocalConf(dict):
    def __getattr__(self, key):
        return self.get(key)

    def __setattr__(self, key, value):
        self[key] = value


class _LocalCelery:
    def __init__(self, name):
        self.name = name
        self.conf = _LocalConf()

    def task(self, *decorator_args, **decorator_kwargs):
        def decorate(func):
            return _LocalTask(func, **decorator_kwargs)

        if decorator_args and callable(decorator_args[0]):
            return decorate(decorator_args[0])
        return decorate

    def start(self):
        return None


app = Celery('digestbot') if Celery is not None else _LocalCelery('digestbot')

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
if Celery is not None:
    import src.orchestrator
    import src.processors.extractor
    import src.processors.analyzer
    import src.processors.summarizer
    import src.processors.scorer
    import src.dispatchers.telegram

app.conf.beat_schedule = {
    'daily-digest': {
        'task': 'src.orchestrator.trigger_all',
        'schedule': crontab(hour=7, minute=0),
    },
}

if __name__ == '__main__':
    app.start()
