from rq import Queue
from .metrics_worker import MetricsWorker
from redis import Redis
from ..config import settings
from ..utilities.icd10_lookup import set_icd10_file
from ..utilities.cpt_lookup import set_cpt_file
import logging, signal

redis_conn = Redis.from_url(settings.redis_url)

# Load local code files for ICD-10 / CPT validation
if settings.icd10_file:
    set_icd10_file(settings.icd10_file)
if settings.cpt_file:
    set_cpt_file(settings.cpt_file)

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
