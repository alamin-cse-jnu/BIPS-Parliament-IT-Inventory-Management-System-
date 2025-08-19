"""
Complete Settings Configuration for PIMS
Bangladesh Parliament Secretariat IT Inventory Management System
Location: Dhaka, Bangladesh

Features:
- Enhanced MySQL/MariaDB configuration with PyMySQL support
- Bangladesh-specific localization
- Glass-morphism design system settings
- Performance optimizations
- Security configurations
- Modern template and static file management
"""

import os
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-%ppx4se)89yo@lrgb056*t$1^kr7qd@__)(x*@6#^$peycaho1'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = []

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',  # For better number formatting
    
    # PIMS Core Apps
    'users',
    'locations',
    'devices',
    'vendors',
    'assignments',
    'maintenance',
    
    # Third-party Apps
    'django_celery_beat',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'pims.urls'

# Template Configuration with Glass-morphism Design System
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            BASE_DIR / 'pims' / 'templates',  # Project-level templates
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'django.template.context_processors.media',
                'django.template.context_processors.static',
            ],
        },
    },
]

WSGI_APPLICATION = 'pims.wsgi.application'

# Enhanced Database Configuration for Bangladesh Parliament Secretariat
# MySQL/MariaDB with PyMySQL compatibility and performance optimizations
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'pims_db',
        'USER': 'root',
        'PASSWORD': '',
        'HOST': 'localhost',
        'PORT': '3306',
        'OPTIONS': {
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
            'charset': 'utf8mb4',
            'collation': 'utf8mb4_unicode_ci',
            'autocommit': True,
        },
        'CONN_MAX_AGE': 600,  # Connection pooling for better performance
        'ATOMIC_REQUESTS': True,  # Wrap each request in a transaction
    }
}

# Alternative production database configuration using environment variables
"""
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': os.environ.get('DB_NAME', 'pims_db'),
        'USER': os.environ.get('DB_USER', 'root'),
        'PASSWORD': os.environ.get('DB_PASSWORD', ''),
        'HOST': os.environ.get('DB_HOST', 'localhost'),
        'PORT': os.environ.get('DB_PORT', '3306'),
        'OPTIONS': {
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
            'charset': 'utf8mb4',
            'collation': 'utf8mb4_unicode_ci',
            'autocommit': True,
        },
        'CONN_MAX_AGE': 600,
        'ATOMIC_REQUESTS': True,
    }
}
"""

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {
            'min_length': 8,
        }
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization for Bangladesh Parliament Secretariat
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Dhaka'  # Bangladesh Standard Time (UTC+6)
USE_I18N = True
USE_TZ = True

# Static files configuration following template design patterns
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

STATICFILES_DIRS = [
    BASE_DIR / 'pims' / 'static',
]

STATICFILES_FINDERS = [
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
]

# Media files configuration for PIMS assets
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Custom User Model
AUTH_USER_MODEL = 'users.CustomUser'

# Authentication URLs
LOGIN_URL = 'users:login'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = 'users:login'

# Bangladesh Parliament Secretariat Configuration
PARLIAMENT_NAME = 'Bangladesh Parliament Secretariat'
SYSTEM_NAME = 'PIMS - Parliament IT Inventory Management System'
ORGANIZATION_LOCATION = 'Dhaka, Bangladesh'

# Glass-morphism Design System Settings (following template design patterns)
DESIGN_SYSTEM = {
    'THEME': 'glass-morphism',
    'BACKGROUND_GRADIENT': 'linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%)',
    'GLASS_CARD_OPACITY': 0.95,
    'BACKDROP_BLUR': '20px',
    'BORDER_OPACITY': 0.4,
    'BORDER_RADIUS': '16px',
    'SHADOW': '0 8px 32px rgba(0, 0, 0, 0.08)',
}

# Bootstrap and CSS Framework Settings
BOOTSTRAP_VERSION = '5.3'
USE_BOOTSTRAP_ICONS = True
USE_CUSTOM_CSS = True

# Report and Pagination Settings
REPORTS_PER_PAGE = 25
MAX_EXPORT_RECORDS = 10000
PAGINATION_ORPHANS = 3

# Session Configuration
SESSION_COOKIE_AGE = 28800  # 8 hours
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_SAVE_EVERY_REQUEST = True

# File Upload Configuration
FILE_UPLOAD_MAX_MEMORY_SIZE = 5242880  # 5MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 10485760  # 10MB
FILE_UPLOAD_TEMP_DIR = None
FILE_UPLOAD_PERMISSIONS = 0o644

# Image and Media Configuration
ALLOWED_IMAGE_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.gif', '.webp']
MAX_IMAGE_SIZE = 2 * 1024 * 1024  # 2MB
ALLOWED_DOCUMENT_EXTENSIONS = ['.pdf', '.doc', '.docx', '.xls', '.xlsx']
MAX_DOCUMENT_SIZE = 10 * 1024 * 1024  # 10MB

# PIMS-specific Media Dimensions and Settings
USER_IMAGE_SIZE = (300, 300)      # Profile image dimensions
QR_CODE_SIZE = (300, 300)         # QR code dimensions
DEVICE_IMAGE_SIZE = (800, 600)    # Device photo dimensions
THUMBNAIL_SIZE = (150, 150)       # Thumbnail dimensions

# QR Code Configuration
QR_CODE_SETTINGS = {
    'VERSION': 1,
    'ERROR_CORRECTION': 'M',
    'BOX_SIZE': 10,
    'BORDER': 4,
    'FILL_COLOR': '#1e293b',
    'BACK_COLOR': '#ffffff',
}

# Email Configuration (for notifications and reports)
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'localhost'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = ''
EMAIL_HOST_PASSWORD = ''
DEFAULT_FROM_EMAIL = 'noreply@parliament.gov.bd'

# Cache Configuration (for better performance)
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.db.DatabaseCache',
        'LOCATION': 'pims_cache_table',
    }
}

# Celery Configuration (for background tasks)
CELERY_BROKER_URL = 'redis://localhost:6379/0'
CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'Asia/Dhaka'

# Logging Configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '[{levelname}] {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '[{levelname}] {asctime} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR / 'logs' / 'pims.log',
            'maxBytes': 1024*1024*10,  # 10MB
            'backupCount': 5,
            'formatter': 'verbose',
        },
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
        'error_file': {
            'level': 'ERROR',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR / 'logs' / 'error.log',
            'maxBytes': 1024*1024*10,  # 10MB
            'backupCount': 5,
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console', 'file'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file', 'error_file'],
            'level': 'INFO',
            'propagate': False,
        },
        'pims': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'users': {
            'handlers': ['file'],
            'level': 'INFO',
            'propagate': True,
        },
        'devices': {
            'handlers': ['file'],
            'level': 'INFO',
            'propagate': True,
        },
        'maintenance': {
            'handlers': ['file'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}

# Security Settings (uncomment for production)
"""
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
X_FRAME_OPTIONS = 'DENY'
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_SECURE = True
SECURE_SSL_REDIRECT = True
"""

# Custom Settings for Bangladesh Parliament Secretariat
PARLIAMENT_SETTINGS = {
    'WORKING_HOURS': {
        'START': '09:00',
        'END': '17:00',
    },
    'WORKING_DAYS': [0, 1, 2, 3, 4],  # Monday to Friday
    'OFFICIAL_HOLIDAYS': [],  # Can be populated with Bangladesh public holidays
    'FISCAL_YEAR_START': 7,  # July (Bangladesh fiscal year)
    'DEFAULT_CURRENCY': 'BDT',
    'TIMEZONE_DISPLAY': 'Bangladesh Standard Time (BST)',
}

# API and Integration Settings
REST_FRAMEWORK = {
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 25,
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
}

# Data Validation Settings
DATA_VALIDATION = {
    'DEVICE_ID_PATTERN': r'^[A-Z]{2,4}\d{4,8}$',
    'USER_ID_PATTERN': r'^EMP\d{4,6}$',
    'QR_CODE_PREFIX': 'PIMS',
    'BARCODE_FORMAT': 'CODE128',
}

# Backup and Maintenance Settings
BACKUP_SETTINGS = {
    'AUTO_BACKUP': True,
    'BACKUP_INTERVAL_HOURS': 24,
    'MAX_BACKUP_FILES': 30,
    'BACKUP_LOCATION': BASE_DIR / 'backups',
}

# Performance Settings
PERFORMANCE_SETTINGS = {
    'ENABLE_QUERY_OPTIMIZATION': True,
    'MAX_CONCURRENT_REQUESTS': 100,
    'DATABASE_QUERY_TIMEOUT': 30,
    'CACHE_TIMEOUT': 3600,  # 1 hour
}

# Feature Flags
FEATURE_FLAGS = {
    'ENABLE_QR_CODES': True,
    'ENABLE_BARCODE_SCANNING': True,
    'ENABLE_EMAIL_NOTIFICATIONS': True,
    'ENABLE_SMS_NOTIFICATIONS': False,
    'ENABLE_API_ACCESS': True,
    'ENABLE_MOBILE_APP': False,
    'ENABLE_AUDIT_TRAIL': True,
    'ENABLE_ADVANCED_REPORTS': True,
}

# Maintenance and Monitoring
MAINTENANCE_MODE = False
SYSTEM_VERSION = '2.0.0'
BUILD_DATE = '2025-08-14'
LAST_UPDATE = '2025-08-14'

# Create logs directory if it doesn't exist
(BASE_DIR / 'logs').mkdir(exist_ok=True)