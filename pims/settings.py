
"""
Django Settings for PIMS (Parliament IT Inventory Management System)
=====================================================================

Location: Bangladesh Parliament Secretariat, Dhaka, Bangladesh
Project: PIMS-PRP Integration for Real Employee Data Collection
Version: Django 4.2.7, Python 3.12.7

PRP Integration Context:
- Base URL: https://prp.parliament.gov.bd
- Authentication: Bearer token (username: "ezzetech", password: "${Fty#3a")
- Purpose: Remove mock data, implement real PRP API integration
- Business Rules: One-way sync PRP → PIMS, admin-controlled sync, PRP fields read-only

Template Design: Flat design with high contrast (teal, orange, red color scheme)
Location Context: All timestamps in Asia/Dhaka timezone
"""

import os
from pathlib import Path
from django.core.management.utils import get_random_secret_key

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# ============================================================================
# SECURITY SETTINGS
# ============================================================================

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get('SECRET_KEY', get_random_secret_key())

# SECURITY WARNING: don't run with debug turned on in production!
# FIXED: Default to True for development when no .env file exists
DEBUG = os.environ.get('DEBUG', 'True').lower() == 'true'

ALLOWED_HOSTS = [
    'localhost',
    '127.0.0.1',
    '0.0.0.0',
    '*.parliament.gov.bd',  # Bangladesh Parliament domain
    '*.ezzetech.com',       # Development domain
]

# Security settings for Bangladesh Parliament Secretariat
# FIXED: Only apply SSL settings in production environment
if not DEBUG and os.environ.get('ENVIRONMENT') == 'production':
    SECURE_SSL_REDIRECT = True
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    USE_TZ = True
    
    # CSRF Protection
    CSRF_COOKIE_SECURE = True
    SESSION_COOKIE_SECURE = True
    
    # Content Security Policy for Bangladesh Parliament
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_BROWSER_XSS_FILTER = True
    X_FRAME_OPTIONS = 'DENY'

# ============================================================================
# APPLICATION DEFINITION
# ============================================================================

# Django built-in applications
DJANGO_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',  # For template formatting
]

# Third-party applications
THIRD_PARTY_APPS = [
    'rest_framework',           # Django REST Framework for API
    'corsheaders',             # CORS handling for API calls
    'django_extensions',       # Development utilities
]

# PIMS applications
LOCAL_APPS = [
    'users',
    'locations',
    'devices',
    'vendors',
    'assignments',
    'maintenance', 
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

# ============================================================================
# MIDDLEWARE CONFIGURATION
# ============================================================================

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',              # CORS for PRP API
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'pims.urls'

# ============================================================================
# TEMPLATE CONFIGURATION
# ============================================================================

# Template Design System (Flat Design - Bangladesh Parliament)
PIMS_TEMPLATE_SETTINGS = {
    'DESIGN_SYSTEM': 'flat',  # flat design (no glassmorphism)
    'COLOR_SCHEME': {
        'PRIMARY_TEAL': '#20B2AA',      # Light Sea Green
        'PRIMARY_ORANGE': '#FF8C00',    # Dark Orange  
        'PRIMARY_RED': '#DC143C',       # Crimson
        'SECONDARY_GRAY': '#6C757D',    # Bootstrap gray-600
        'SUCCESS_GREEN': '#28A745',     # Bootstrap success
        'WARNING_YELLOW': '#FFC107',    # Bootstrap warning
        'INFO_BLUE': '#17A2B8',        # Bootstrap info
        'LIGHT_BG': '#F8F9FA',         # Light background
        'DARK_TEXT': '#212529',        # Dark text
    },
    'HIGH_CONTRAST': True,              # For accessibility
    'RESPONSIVE_BREAKPOINTS': ['mobile', 'tablet', 'laptop', 'desktop', 'big_monitor'],
    'LOCATION_CONTEXT': 'Bangladesh Parliament Secretariat, Dhaka',
    'ORGANIZATION': 'Bangladesh Parliament Secretariat',
    'TIMEZONE_DISPLAY': 'Asia/Dhaka',
}

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'users.context_processors.user_permissions_context',  # User permissions
                'users.context_processors.system_info_context',       # System info
            ],
        },
    },
]

WSGI_APPLICATION = 'pims.wsgi.application'

# ============================================================================
# DATABASE CONFIGURATION
# ============================================================================

# Database configuration for Bangladesh Parliament infrastructure
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': os.environ.get('DB_NAME', 'pims_db'),
        'USER': os.environ.get('DB_USER', 'root'),
        'PASSWORD': os.environ.get('DB_PASSWORD', ''),  # Required in production
        'HOST': os.environ.get('DB_HOST', 'localhost'),
        'PORT': os.environ.get('DB_PORT', '3306'),
        'OPTIONS': {
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
            'charset': 'utf8mb4',
            'autocommit': True,
        },
        'CONN_MAX_AGE': 60,  # Connection pooling for performance
    }
}

# ============================================================================
# PASSWORD VALIDATION
# ============================================================================

# Password validation for Parliament user accounts
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {
            'min_length': 8,  # Parliament security requirement
        }
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# ============================================================================
# INTERNATIONALIZATION
# ============================================================================

# Bangladesh Parliament localization settings
LANGUAGE_CODE = 'en-us'  # Primary language for Parliament operations
TIME_ZONE = 'Asia/Dhaka'  # Bangladesh Standard Time (GMT+6)
USE_I18N = True           # Enable internationalization
USE_TZ = True             # Enable timezone support

# ============================================================================
# STATIC FILES AND MEDIA CONFIGURATION
# ============================================================================

# Static files (CSS, JavaScript, Images) for Parliament templates
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Additional locations of static files
STATICFILES_DIRS = [
    BASE_DIR / 'static',
]

# Static files storage
STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.StaticFilesStorage'

# Media files (User uploads, PRP profile images, QR codes)
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# File upload settings for Parliament documentation
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10MB for document uploads
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10MB total
FILE_UPLOAD_PERMISSIONS = 0o644

# Image processing settings for PRP profile images
IMAGE_SETTINGS = {
    'MAX_SIZE': (800, 800),    # Maximum image dimensions
    'QUALITY': 85,             # JPEG quality
}

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Custom User Model
AUTH_USER_MODEL = 'users.CustomUser'

# Login URLs
LOGIN_URL = '/users/login/'
LOGIN_REDIRECT_URL = '/dashboard/'
LOGOUT_REDIRECT_URL = '/users/login/'

# ============================================================================
# PRP (Parliament Resource Portal) Integration Settings
# ============================================================================

# PRP Integration Availability Control
PRP_INTEGRATION_AVAILABLE = os.environ.get('PRP_INTEGRATION_AVAILABLE', 'True').lower() == 'true'
PRP_API_ENABLED = os.environ.get('PRP_API_ENABLED', 'True').lower() == 'true'

# PRP API Configuration (Official Bangladesh Parliament Resource Portal)
PRP_API_SETTINGS = {
    # Base API Configuration
    'BASE_URL': os.environ.get('PRP_API_BASE_URL', 'https://prp.parliament.gov.bd'),
    'API_VERSION': 'v1',
    'TIMEOUT': int(os.environ.get('PRP_API_TIMEOUT', '30')),          # 30 seconds timeout
    'RETRY_ATTEMPTS': int(os.environ.get('PRP_API_RETRY_ATTEMPTS', '3')),  # 3 retry attempts
    'RATE_LIMIT': int(os.environ.get('PRP_API_RATE_LIMIT', '100')),   # 100 calls per hour
    'BATCH_SIZE': int(os.environ.get('PRP_API_BATCH_SIZE', '50')),    # 50 users per batch
    
    # Authentication Configuration (Official Credentials)
    'AUTH_USERNAME': os.environ.get('PRP_AUTH_USERNAME', 'ezzetech'),
    'AUTH_PASSWORD': os.environ.get('PRP_AUTH_PASSWORD', '${Fty#3a'),
    'TOKEN_REFRESH_THRESHOLD': 300,    # Refresh token 5 minutes before expiry
    'AUTH_CACHE_TIMEOUT': 1800,        # Cache auth token for 30 minutes
    
    # API Endpoints
    'ENDPOINTS': {
        'TOKEN': '/api/authentication/external?action=token',
        'REFRESH_TOKEN': '/api/authentication/external?action=refresh-token',
        'DEPARTMENTS': '/api/secure/external?action=departments',
        'EMPLOYEE_DETAILS': '/api/secure/external?action=employee_details',
        'HEALTH_CHECK': '/api/secure/external?action=health',
    },
    
    # Request Configuration
    'HEADERS': {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'User-Agent': 'PIMS-PRP-Integration/1.0 (Bangladesh Parliament)',
    },
    
    # Data Validation Rules
    'REQUIRED_FIELDS': ['userId', 'nameEng', 'email', 'designationEng'],
    'OPTIONAL_FIELDS': ['mobile', 'photo', 'status'],
    'MAX_NAME_LENGTH': 100,
    'MAX_EMAIL_LENGTH': 150,
    'MAX_DESIGNATION_LENGTH': 100,
    
    # Sync Control
    'VALIDATE_SSL': True,      # Will be overridden in development
    'LOG_API_CALLS': False,    # Will be overridden in production
    'CACHE_RESPONSES': True,   # Cache API responses
    'CACHE_TIMEOUT': 900,      # 15 minutes cache for API responses
}

# Business Rules for PRP Integration
PRP_BUSINESS_RULES = {
    'ONE_WAY_SYNC': True,              # PRP → PIMS only
    'ADMIN_CONTROLLED_SYNC': True,     # Only admins can trigger sync
    'PRP_FIELDS_READONLY': True,       # PRP data cannot be edited in PIMS
    'PRESERVE_LOCAL_USERS': True,      # Don't overwrite non-PRP users
    'DEFAULT_PASSWORD': '12345678',    # Default password for PRP users
    'AUTO_ACTIVATE_PRP_USERS': True,   # Automatically activate synced users
    'SYNC_PROFILE_IMAGES': True,       # Download and sync profile images
    'DEPARTMENT_MAPPING': True,        # Map PRP departments to PIMS offices
}

# ============================================================================
# REST FRAMEWORK CONFIGURATION
# ============================================================================

# Django REST Framework settings for PRP API endpoints
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.TokenAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 25,
    'DEFAULT_FILTER_BACKENDS': [
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle'
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100/hour',
        'user': '1000/hour'
    }
}

# ============================================================================
# CORS CONFIGURATION
# ============================================================================

# CORS settings for PRP API integration
CORS_ALLOWED_ORIGINS = [
    "https://prp.parliament.gov.bd",
    "https://parliament.gov.bd",
]

# CORS headers for PRP communication
CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
]

# ============================================================================
# CACHING CONFIGURATION
# ============================================================================

# Cache configuration for PRP API responses and session data
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'pims-cache',
        'TIMEOUT': 300,  # 5 minutes default
        'OPTIONS': {
            'MAX_ENTRIES': 1000,
        }
    },
    # Redis cache for production (when available)
    'redis': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': os.environ.get('REDIS_URL', 'redis://localhost:6379/1'),
        'TIMEOUT': 900,  # 15 minutes for Redis
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }
    }
}

# Use Redis in production if available
if not DEBUG and os.environ.get('REDIS_URL'):
    CACHES['default'] = CACHES['redis']

# ============================================================================
# LOGGING CONFIGURATION
# ============================================================================

# Comprehensive logging for Parliament system monitoring
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
        'prp_format': {
            'format': '🏛️  PRP-API {asctime} [{levelname}] {module}: {message}',
            'style': '{',
        }
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
        'prp_file': {
            'level': 'DEBUG',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR / 'logs' / 'prp_integration.log',
            'maxBytes': 1024*1024*5,   # 5MB
            'backupCount': 3,
            'formatter': 'prp_format',
        },
        'console': {
            'level': 'DEBUG' if DEBUG else 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': True,
        },
        'pims': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG' if DEBUG else 'INFO',
            'propagate': True,
        },
        'pims.prp_integration': {
            'handlers': ['console', 'prp_file'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'pims.prp_integration.api': {
            'handlers': ['console', 'prp_file'],
            'level': 'INFO',  # Will be set to DEBUG in development
            'propagate': False,
        },
        'users.api.prp_client': {
            'handlers': ['console', 'prp_file'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

# Ensure logs directory exists
(BASE_DIR / 'logs').mkdir(exist_ok=True)

# ============================================================================
# EMAIL CONFIGURATION
# ============================================================================

# Email settings for Parliament notifications
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = os.environ.get('EMAIL_HOST', 'smtp.parliament.gov.bd')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', '587'))
EMAIL_USE_TLS = os.environ.get('EMAIL_USE_TLS', 'True').lower() == 'true'
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', 'noreply@parliament.gov.bd')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')

# Default email settings
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'noreply@parliament.gov.bd')
SERVER_EMAIL = DEFAULT_FROM_EMAIL

# Email templates configuration for PRP notifications
EMAIL_SETTINGS = {
    'PRP_SYNC_NOTIFICATIONS': True,
    'ADMIN_EMAIL_RECIPIENTS': [
        'admin@parliament.gov.bd',
        'it@parliament.gov.bd',
    ],
    'EMAIL_TEMPLATE_PREFIX': 'users/emails/prp_',
}

# ============================================================================
# CELERY CONFIGURATION (For Background Tasks)
# ============================================================================

# Celery configuration for PRP sync background tasks
CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL', 'redis://localhost:6379/0')
CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'Asia/Dhaka'
CELERY_ENABLE_UTC = True

# Celery task configuration for PRP operations
CELERY_TASK_ROUTES = {
    'users.tasks.sync_prp_users': {'queue': 'prp_sync'},
    'users.tasks.sync_prp_departments': {'queue': 'prp_sync'},
    'users.tasks.validate_prp_connection': {'queue': 'prp_health'},
}

# ============================================================================
# ENVIRONMENT-SPECIFIC OVERRIDES
# ============================================================================

# Development-specific settings
if DEBUG:
    # Development logging
    LOGGING['loggers']['pims.prp_integration.api']['level'] = 'DEBUG'
    
    # Allow all origins in development
    CORS_ALLOW_ALL_ORIGINS = True
    
    # Development PRP settings (can use test credentials)
    PRP_API_SETTINGS['VALIDATE_SSL'] = False  # For local testing
    
    # FIXED: Disable SSL redirects completely in development
    SECURE_SSL_REDIRECT = False

# Production-specific settings for Bangladesh Parliament
elif os.environ.get('ENVIRONMENT') == 'production':
    # Production security
    SECURE_SSL_REDIRECT = True
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    
    # Production PRP settings
    PRP_API_SETTINGS['VALIDATE_SSL'] = True
    PRP_API_SETTINGS['LOG_API_CALLS'] = True
    
    # Production error handling
    ADMINS = [
        ('PIMS Admin', 'admin@parliament.gov.bd'),
        ('IT Support', 'it@parliament.gov.bd'),
    ]
    MANAGERS = ADMINS

# ============================================================================
# CUSTOM SETTINGS VALIDATORS
# ============================================================================

def validate_prp_settings():
    """
    Validate PRP configuration settings on startup.
    Called during Django initialization to ensure proper configuration.
    
    Raises:
        ImproperlyConfigured: If required PRP settings are missing or invalid
    """
    from django.core.exceptions import ImproperlyConfigured
    
    if not PRP_INTEGRATION_AVAILABLE:
        return  # Skip validation if PRP integration is disabled
    
    # Check required PRP settings
    required_settings = ['BASE_URL', 'AUTH_USERNAME', 'AUTH_PASSWORD']
    missing_settings = []
    
    for setting in required_settings:
        if not PRP_API_SETTINGS.get(setting):
            missing_settings.append(setting)
    
    if missing_settings:
        raise ImproperlyConfigured(
            f"Missing required PRP settings: {', '.join(missing_settings)}. "
            f"Please configure these in your environment variables or settings.py"
        )
    
    # Validate URL format
    base_url = PRP_API_SETTINGS.get('BASE_URL', '')
    if not (base_url.startswith('http://') or base_url.startswith('https://')):
        raise ImproperlyConfigured(
            f"Invalid PRP_API_BASE_URL format: {base_url}. "
            f"Must start with http:// or https://"
        )

def get_prp_endpoint_urls():
    """
    Get complete URLs for PRP API endpoints.
    
    Returns:
        dict: Complete endpoint URLs
    """
    base_url = PRP_API_SETTINGS.get('BASE_URL', '').rstrip('/')
    endpoints = PRP_API_SETTINGS.get('ENDPOINTS', {})
    
    return {
        name: f"{base_url}{path}"
        for name, path in endpoints.items()
    }

# ============================================================================
# DEVELOPMENT & DEBUGGING HELPERS
# ============================================================================

if DEBUG:
    # Development helper functions
    def print_prp_config():
        """Print PRP configuration for debugging (development only)."""
        print("\n" + "="*80)
        print("🏛️  PIMS-PRP Integration Configuration")
        print("="*80)
        print(f"Location: {PIMS_TEMPLATE_SETTINGS['LOCATION_CONTEXT']}")
        print(f"Timezone: {TIME_ZONE}")
        print(f"Integration Available: {PRP_INTEGRATION_AVAILABLE}")
        print(f"API Enabled: {PRP_API_ENABLED}")
        print(f"Base URL: {PRP_API_SETTINGS.get('BASE_URL', 'Not configured')}")
        print(f"Auth Username: {PRP_API_SETTINGS.get('AUTH_USERNAME', 'Not configured')}")
        print(f"Auth Password: {'*' * len(PRP_API_SETTINGS.get('AUTH_PASSWORD', ''))}")
        print(f"Timeout: {PRP_API_SETTINGS.get('TIMEOUT')}s")
        print(f"Retry Attempts: {PRP_API_SETTINGS.get('RETRY_ATTEMPTS')}")
        print(f"Rate Limit: {PRP_API_SETTINGS.get('RATE_LIMIT')}/hour")
        print("="*80)
        
        # Business Rules Summary
        print("\n🔧 PRP Business Rules:")
        for rule, value in PRP_BUSINESS_RULES.items():
            print(f"  • {rule}: {value}")
        print("="*80)
        
        # Template Design Settings
        print("\n🎨 Template Design Settings:")
        colors = PIMS_TEMPLATE_SETTINGS['COLOR_SCHEME']
        print(f"  • Design System: {PIMS_TEMPLATE_SETTINGS['DESIGN_SYSTEM'].upper()}")
        print(f"  • Primary Colors: Teal({colors['PRIMARY_TEAL']}), Orange({colors['PRIMARY_ORANGE']}), Red({colors['PRIMARY_RED']})")
        print(f"  • High Contrast: {PIMS_TEMPLATE_SETTINGS['HIGH_CONTRAST']}")
        print("="*80 + "\n")
    
    # Auto-print config in development
    try:
        print_prp_config()
    except Exception as e:
        print(f"⚠️  Could not print PRP config: {e}")

# ============================================================================
# FINAL CONFIGURATION SUMMARY
# ============================================================================

# Configuration summary for logging
PIMS_CONFIG_SUMMARY = {
    'project_name': 'PIMS (Parliament IT Inventory Management System)',
    'location': 'Bangladesh Parliament Secretariat, Dhaka',
    'version': '1.0.0',
    'django_version': '4.2.7',
    'python_version': '3.12.7',
    'database': 'MariaDB/MySQL',
    'prp_integration': PRP_INTEGRATION_AVAILABLE,
    'prp_api_base': PRP_API_SETTINGS.get('BASE_URL', ''),
    'timezone': TIME_ZONE,
    'debug_mode': DEBUG,
    'template_design': PIMS_TEMPLATE_SETTINGS['DESIGN_SYSTEM'],
    'color_scheme': 'Teal, Orange, Red (Flat Design)',
}

# ============================================================================
# ENVIRONMENT VARIABLES DOCUMENTATION
# ============================================================================

"""
Required Environment Variables for PIMS-PRP Integration:
========================================================

Core Django Settings:
- SECRET_KEY: Django secret key (auto-generated if not provided)
- DEBUG: Enable/disable debug mode (default: True for development)
- ENVIRONMENT: Set to 'production' for production deployment
- ALLOWED_HOSTS: Comma-separated list of allowed hosts

Database Settings:
- DB_NAME: Database name (default: pims_parliament)
- DB_USER: Database username (default: pims_user)
- DB_PASSWORD: Database password (required in production)
- DB_HOST: Database host (default: localhost)
- DB_PORT: Database port (default: 3306)

PRP Integration Settings:
- PRP_INTEGRATION_AVAILABLE: Enable/disable PRP integration (default: True)
- PRP_API_ENABLED: Enable/disable PRP API calls (default: True)
- PRP_API_BASE_URL: PRP API base URL (default: https://prp.parliament.gov.bd)
- PRP_AUTH_USERNAME: PRP authentication username (default: ezzetech)
- PRP_AUTH_PASSWORD: PRP authentication password (default: ${Fty#3a)
- PRP_API_TIMEOUT: API request timeout in seconds (default: 30)
- PRP_API_RETRY_ATTEMPTS: Number of retry attempts (default: 3)
- PRP_API_RATE_LIMIT: API rate limit per hour (default: 100)
- PRP_API_BATCH_SIZE: Batch size for user sync (default: 50)

Optional Settings:
- REDIS_URL: Redis cache URL (for production caching)
- EMAIL_HOST: SMTP server host
- EMAIL_HOST_USER: SMTP username
- EMAIL_HOST_PASSWORD: SMTP password
- CELERY_BROKER_URL: Celery broker URL (for background tasks)

Example .env file for Production:
=================================
DEBUG=False
ENVIRONMENT=production
SECRET_KEY=your-secure-secret-key-here
DB_NAME=pims_parliament
DB_USER=pims_user
DB_PASSWORD=secure_password_here
DB_HOST=parliament-db-server
PRP_INTEGRATION_AVAILABLE=True
PRP_API_ENABLED=True
PRP_API_BASE_URL=https://prp.parliament.gov.bd
PRP_AUTH_USERNAME=ezzetech
PRP_AUTH_PASSWORD=${Fty#3a
EMAIL_HOST=smtp.parliament.gov.bd
EMAIL_HOST_USER=noreply@parliament.gov.bd
DEFAULT_FROM_EMAIL=noreply@parliament.gov.bd
REDIS_URL=redis://parliament-redis:6379/0
"""