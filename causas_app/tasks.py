#!/usr/bin/env python
# -*-coding:utf-8 -*-
'''
@File    :   tasks.py
@Time    :   2024/06/18 00:00:00
@Author  :   Juan Molina 
@Version :   5.1
@Contact :   jmolina@e-contact.cl
@License :   (C)Copyright 2025, Juan Molina
'''

from pjud.celeryy import app
import traceback
import json
import logging
from datetime import datetime, timedelta
from django.conf import settings
import os
from redis import Redis
from redis.exceptions import LockError
import redis

WEBSITE_SITE_NAME = '' if os.environ.get('WEBSITE_SITE_NAME') is None else os.environ.get('WEBSITE_SITE_NAME')

logger = logging.getLogger('causas_app')

@app.task
def get_causas(self, *args, **kwargs):
    try:
        from causas_app.views import get_causas_view
        logger.info(f"[{WEBSITE_SITE_NAME}] - Starting get_causas task with args: {args}, kwargs: {kwargs}")
        result = get_causas_view(*args, **kwargs)
        logger.info(f"[{WEBSITE_SITE_NAME}] - Completed get_causas task")
        return result
    except Exception as e:
        logger.error(f"[{WEBSITE_SITE_NAME}] - Error in get_causas task: {str(e)}")
        logger.error(traceback.format_exc())
        return {"error": str(e)}