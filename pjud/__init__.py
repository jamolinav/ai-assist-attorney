from .celeryy import app
import logging
import threading
import time
#from api_app.models import ExtractorCeleryWorker
#from api_app.extractor.init import is_celery_running
import os

WEBSITE_SITE_NAME = '' if os.environ.get('WEBSITE_SITE_NAME') is None else os.environ.get('WEBSITE_SITE_NAME')

logger = logging.getLogger('general')

logger.info('Celery app started')

__all__ = ('app',)