from rq import Queue, Worker
from rq.job import Job
import time


class MetricsWorker(Worker):
    def execute_job(self, job: Job, queue: Queue):
        try:
            result = super().execute_job(job, queue)
            return result
        except Exception as e:
            raise
        finally:
            pass
