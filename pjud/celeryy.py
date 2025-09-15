#!/usr/bin/env python
# -*-coding:utf-8 -*-
'''
@File    :   celeryy.py
@Time    :   2024/06/17 23:45:00
@Author  :   Juan Molina 
@Version :   5.1
@Contact :   jmolina@e-contact.cl
@License :   (C)Copyright 2025, Juan Molina
'''

import os
from celery import Celery
from django.conf import settings

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "pjud.settings")

def create_celery_app(broker_url, backend_url, namespace):
    app = Celery('tasks_api', broker=broker_url, backend=backend_url)
    app.config_from_object("django.conf:settings", namespace=namespace)
    app.autodiscover_tasks()

    app.conf.update(
        result_expires=300,
        task_time_limit=300,
        broker_transport_options=settings.CELERY_BROKER_TRANSPORT_OPTIONS,
        result_backend_transport_options=settings.CELERY_RESULT_BACKEND_TRANSPORT_OPTIONS,
    )
    return app

app = create_celery_app(settings.CELERY_BROKER_URL, settings.CELERY_RESULT_BACKEND, 'CELERY')