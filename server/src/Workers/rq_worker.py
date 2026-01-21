from rq import Queue
from src.Workers.metrics_worker import MetricsWorker
from redis import Redis
from src.config import settings
import logging, signal

redis_conn = Redis.from_url(settings.redis_url)

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


def run_worker():
    queue = Queue(connection=redis_conn)
    worker = MetricsWorker([queue])

    def _graceful(signum, frame):
        logger.info("Received signal %s, shutting down gracefully...", signum)
        worker.request_stop(signum, frame)

    signal.signal(signal.SIGTERM, _graceful)
    signal.signal(signal.SIGINT, _graceful)

    worker.work(with_scheduler=True)


if __name__ == "__main__":
    run_worker()
