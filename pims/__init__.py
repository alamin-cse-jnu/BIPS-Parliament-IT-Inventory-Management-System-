"""
PIMS - Parliament IT Inventory Management System
Bangladesh Parliament Secretariat

Main package initialization.
"""

__version__ = '1.0.0'
__author__ = 'Bangladesh Parliament Secretariat IT Team'

# This will make sure the app is always imported when
# Django starts so that shared_task will use this app.
# Uncomment below lines if using Celery
# from .celery import app as celery_app
# __all__ = ('celery_app',)