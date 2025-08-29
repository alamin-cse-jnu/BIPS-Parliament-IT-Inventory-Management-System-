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
DEBUG = os.environ.get('DEBUG', 'False').lower() == 'true'

ALLOWED_HOSTS = [
    'localhost',
    '127.0.0.1',
    '0.0.0.0',
    '*.parliament.gov.bd',  # Bangladesh Parliament domain
    '*.ezzetech.com',       # Development domain
]

# Security settings for Bangladesh Parliament Secretariat
if not DEBUG:
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
    'django.middleware.locale.LocaleMiddleware',          # i18n support
]

ROOT_URLCONF = 'pims.urls'

# ============================================================================
# TEMPLATE CONFIGURATION
# ============================================================================

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            BASE_DIR / 'templates',
            BASE_DIR / 'users' / 'templates',
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                #'core.context_processors.site_context',         # PIMS site context
                #'users.context_processors.prp_context',         # PRP integration context
            ],
        },
    },
]

WSGI_APPLICATION = 'pims.wsgi.application'

# ============================================================================
# DATABASE CONFIGURATION
# ============================================================================

# Database configuration for Bangladesh Parliament Secretariat
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': os.environ.get('DB_NAME', 'pims_db'),
        'USER': os.environ.get('DB_USER', 'root'),
        'PASSWORD': os.environ.get('DB_PASSWORD', ''),
        'HOST': os.environ.get('DB_HOST', 'localhost'),
        'PORT': os.environ.get('DB_PORT', '3306'),
        'OPTIONS': {
            'sql_mode': 'STRICT_TRANS_TABLES',
            'charset': 'utf8mb4',
            'collation': 'utf8mb4_unicode_ci',
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
        },
    }
}

# Database connection pooling for high-traffic scenarios
DATABASE_CONNECTION_POOLING = os.environ.get('DB_CONNECTION_POOLING', 'False').lower() == 'true'

# ============================================================================
# PASSWORD VALIDATION
# ============================================================================

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

# ============================================================================
# INTERNATIONALIZATION & LOCALIZATION
# ============================================================================

# Bangladesh Parliament Secretariat localization settings
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Dhaka'              # Bangladesh timezone
USE_I18N = True
USE_L10N = True
USE_TZ = True

# Additional language support for Bangladesh
LANGUAGES = [
    ('en', 'English'),
    ('bn', 'Bengali (বাংলা)'),
]

LOCALE_PATHS = [
    BASE_DIR / 'locale',
]

# Date and time formatting for Bangladesh
DATE_FORMAT = 'd/m/Y'                 # DD/MM/YYYY format
TIME_FORMAT = 'H:i'                   # 24-hour format
DATETIME_FORMAT = 'd/m/Y H:i'         # DD/MM/YYYY HH:MM
SHORT_DATE_FORMAT = 'd/m/y'
SHORT_DATETIME_FORMAT = 'd/m/y H:i'

# ============================================================================
# STATIC FILES & MEDIA CONFIGURATION
# ============================================================================

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

STATICFILES_DIRS = [
    BASE_DIR / 'static',
]

# Media files (User uploads, PRP profile images)
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# File upload settings for PRP profile images
FILE_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024  # 5MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10MB

# Profile image settings for PRP integration
PROFILE_IMAGE_SETTINGS = {
    'MAX_SIZE': 2 * 1024 * 1024,      # 2MB max size
    'ALLOWED_FORMATS': ['JPEG', 'PNG', 'WEBP'],
    'THUMBNAIL_SIZE': (150, 150),      # Thumbnail dimensions
    'QUALITY': 85,                     # JPEG quality
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
        'User-Agent': 'PIMS-Parliament/1.0 (+https://parliament.gov.bd)',
    },
    
    # Data Validation
    'VALIDATE_SSL': True,              # SSL certificate validation
    'VERIFY_DATA_INTEGRITY': True,     # Verify data integrity from PRP
    'LOG_API_CALLS': True,            # Log all API calls for audit
}

# PRP Business Rules (Critical for Bangladesh Parliament Operations)
PRP_BUSINESS_RULES = {
    # Core Business Logic
    'ONE_WAY_SYNC_ONLY': True,                    # PRP → PIMS only (never send data back)
    'ADMIN_CONTROLLED_SYNC': True,                # Only admins can trigger sync
    'STATUS_OVERRIDE_BY_PIMS_ADMIN': True,        # PIMS admin can override PRP user status
    'PRP_FIELDS_READ_ONLY': True,                 # PRP fields cannot be edited in PIMS
    'AUTO_CREATE_MISSING_USERS': True,            # Auto-create users from PRP if not in PIMS
    'SYNC_USER_STATUS_CHANGES': True,             # Sync active/inactive status changes
    'PRESERVE_LOCAL_PERMISSIONS': True,           # Keep PIMS-assigned roles/permissions
    
    # User Management Rules
    'DEFAULT_PASSWORD_FOR_PRP_USERS': '12345678', # Default password for PRP users
    'USE_PRP_USER_ID_AS_USERNAME': True,          # Format: prp_{userId}
    'SYNC_PROFILE_IMAGES': True,                  # Download and sync profile images
    'UPDATE_EXISTING_PRP_USERS': True,            # Update existing PRP users on sync
    
    # Data Integrity Rules
    'VALIDATE_REQUIRED_FIELDS': True,             # Validate required PRP fields
    'SKIP_INVALID_RECORDS': True,                 # Skip records with invalid data
    'LOG_SKIPPED_RECORDS': True,                  # Log all skipped records
    'BACKUP_BEFORE_SYNC': True,                   # Backup user data before sync
    
    # Sync Operation Rules
    'MAX_SYNC_DURATION': 3600,                   # 1 hour max sync duration
    'CONCURRENT_SYNC_PREVENTION': True,           # Prevent multiple simultaneous syncs
    'POST_SYNC_VALIDATION': True,                 # Validate data after sync
    'SYNC_OPERATION_LOGGING': True,               # Comprehensive sync logging
}

def get_prp_business_rule(rule_name, default=None):
    """
    Helper function to get PRP business rule values.
    
    Args:
        rule_name (str): Rule name from PRP_BUSINESS_RULES
        default: Default value if rule not found
        
    Returns:
        Any: Business rule value or default
        
    Example:
        password = get_prp_business_rule('DEFAULT_PASSWORD_FOR_PRP_USERS', '12345678')
    """
    return PRP_BUSINESS_RULES.get(rule_name, default)

# PRP Data Mapping Configuration (Official Field Mapping)
PRP_DATA_MAPPING = {
    # PRP EmployeeDetails → PIMS CustomUser Field Mapping
    'EMPLOYEE_FIELDS': {
        'userId': 'employee_id',                  # PRP userId → PIMS employee_id
        'nameEng': ('first_name', 'last_name'),  # Split nameEng → first_name + last_name
        'email': 'email',                        # PRP email → PIMS email
        'designationEng': 'designation',         # PRP designationEng → PIMS designation
        'mobile': 'phone_number',                # PRP mobile → PIMS phone_number
        'photo': 'profile_image',                # PRP photo (byte[]) → PIMS profile_image
        'status': ('is_active', 'is_active_employee'),  # PRP status → PIMS active flags
    },
    
    # PRP DepartmentModel → PIMS Office Field
    'DEPARTMENT_FIELDS': {
        'nameEng': 'office',                     # PRP department.nameEng → PIMS office
    },
    
    # Status Mapping (PRP Status → PIMS Boolean)
    'STATUS_MAPPING': {
        'active': True,
        'inactive': False,
        'suspended': False,
        'terminated': False,
        'retired': False,
        'unknown': False,
    },
    
    # Name Processing Rules
    'NAME_PROCESSING': {
        'SPLIT_DELIMITER': ' ',                  # Split nameEng by space
        'DEFAULT_FIRST_NAME': 'Unknown',         # Default if nameEng empty
        'DEFAULT_LAST_NAME': 'User',             # Default last name
        'MAX_NAME_LENGTH': 150,                  # Max length per name field
    }
}

# PRP Cache Configuration
PRP_CACHE_SETTINGS = {
    'DEPARTMENT_CACHE_KEY': 'prp_departments',
    'DEPARTMENT_CACHE_TIMEOUT': 86400,           # 24 hours
    'USER_CACHE_TIMEOUT': 3600,                  # 1 hour
    'API_RESPONSE_CACHE_TIMEOUT': 300,           # 5 minutes
    'SYNC_STATUS_CACHE_TIMEOUT': 1800,           # 30 minutes
}

# ============================================================================
# Template Design Pattern Settings (Bangladesh Parliament UI)
# ============================================================================

# Template settings for Bangladesh Parliament Secretariat (Flat Design)
PIMS_TEMPLATE_SETTINGS = {
    'DESIGN_SYSTEM': 'flat',                     # Flat design (NO glassmorphism)
    'LOCATION_CONTEXT': 'Bangladesh Parliament Secretariat, Dhaka',
    'TIMEZONE_DISPLAY': 'Asia/Dhaka',
    
    # Color Scheme (Teal, Orange, Red as per requirements)
    'COLOR_SCHEME': {
        'PRIMARY_TEAL': '#14b8a6',               # Primary teal
        'PRIMARY_TEAL_HOVER': '#0f9488',         # Teal hover state
        'PRIMARY_ORANGE': '#f97316',             # Primary orange
        'PRIMARY_ORANGE_HOVER': '#ea580c',       # Orange hover state
        'PRIMARY_RED': '#ef4444',                # Primary red
        'PRIMARY_RED_HOVER': '#dc2626',          # Red hover state
        'TEXT_PRIMARY': '#1e293b',               # Primary text
        'TEXT_SECONDARY': '#64748b',             # Secondary text
        'BACKGROUND_PRIMARY': '#ffffff',         # White background
        'BACKGROUND_SECONDARY': '#f8fafc',       # Light gray background
        'BORDER_LIGHT': '#e2e8f0',               # Light border
        'SUCCESS': '#10b981',                    # Success green
        'WARNING': '#f59e0b',                    # Warning amber
        'DANGER': '#ef4444',                     # Danger red
        'PRP_SYNC_BG': '#ecfdf5',                # PRP sync background
        'PRP_INDICATOR': '#14b8a6',              # PRP field indicator
        'PRP_READONLY_BG': '#f8f9fa',            # PRP read-only field background
    },
    
    # Responsive Design Breakpoints
    'RESPONSIVE_BREAKPOINTS': {
        'MOBILE': '320px',
        'TABLET': '768px',
        'LAPTOP': '1024px',
        'DESKTOP': '1280px',
        'BIG_MONITORS': '1920px',
    },
    
    # Design Principles
    'HIGH_CONTRAST': True,                       # High contrast for accessibility
    'CONSISTENT_SPACING': True,                  # Consistent spacing throughout
    'MODERN_TYPOGRAPHY': True,                   # Modern font choices
    'ACCESSIBILITY_FOCUSED': True,               # WCAG 2.1 compliance
}

# Static files configuration for template design
STATICFILES_FINDERS = [
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
]

# ============================================================================
# REST FRAMEWORK CONFIGURATION (For PRP API Integration)
# ============================================================================

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.BasicAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
        'rest_framework.renderers.BrowsableAPIRenderer',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 50,
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle'
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100/hour',
        'user': '1000/hour'
    }
}

# CORS Configuration for PRP API calls
CORS_ALLOWED_ORIGINS = [
    "https://prp.parliament.gov.bd",
]

CORS_ALLOW_CREDENTIALS = True

# ============================================================================
# CACHING CONFIGURATION
# ============================================================================

# Cache configuration for PRP data and general application cache
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache' if os.environ.get('REDIS_URL') else 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': os.environ.get('REDIS_URL', 'unique-snowflake'),
        'TIMEOUT': 300,                          # 5 minutes default timeout
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient' if os.environ.get('REDIS_URL') else None,
        },
        'KEY_PREFIX': 'pims_parliament',
    },
    
    # Dedicated cache for PRP data
    'prp_cache': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache' if os.environ.get('REDIS_URL') else 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': os.environ.get('REDIS_URL', 'prp-cache'),
        'TIMEOUT': 3600,                         # 1 hour for PRP data
        'KEY_PREFIX': 'prp_data',
    }
}

# ============================================================================
# LOGGING CONFIGURATION
# ============================================================================

# Ensure logs directory exists
LOGS_DIR = BASE_DIR / 'logs'
os.makedirs(LOGS_DIR, exist_ok=True)

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
            'format': '[PRP] {asctime} {levelname} {module} - {message}',
            'style': '{',
        },
    },
    
    'filters': {
        'require_debug_true': {
            '()': 'django.utils.log.RequireDebugTrue',
        },
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse',
        },
    },
    
    'handlers': {
        'console': {
            'level': 'INFO',
            'filters': ['require_debug_true'],
            'class': 'logging.StreamHandler',
            'formatter': 'simple'
        },
        'file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': LOGS_DIR / 'pims.log',
            'maxBytes': 1024*1024*10,           # 10 MB
            'backupCount': 10,
            'formatter': 'verbose',
        },
        'prp_file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': LOGS_DIR / 'prp_integration.log',
            'maxBytes': 1024*1024*10,           # 10 MB
            'backupCount': 20,                  # Keep more PRP logs
            'formatter': 'prp_format',
        },
        'sync_file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': LOGS_DIR / 'prp_sync.log',
            'maxBytes': 1024*1024*5,            # 5 MB
            'backupCount': 30,                  # Keep sync logs for longer
            'formatter': 'prp_format',
        },
        'error_file': {
            'level': 'ERROR',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': LOGS_DIR / 'errors.log',
            'maxBytes': 1024*1024*10,           # 10 MB
            'backupCount': 10,
            'formatter': 'verbose',
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
            'level': 'INFO',
            'propagate': False,
        },
        'pims.prp_integration': {
            'handlers': ['console', 'prp_file'],
            'level': 'INFO',
            'propagate': False,
        },
        'pims.prp_integration.sync': {
            'handlers': ['console', 'sync_file'],
            'level': 'INFO',
            'propagate': False,
        },
        'pims.prp_integration.api': {
            'handlers': ['console', 'prp_file'],
            'level': 'DEBUG' if DEBUG else 'INFO',
            'propagate': False,
        },
        'root': {
            'handlers': ['console', 'error_file'],
            'level': 'WARNING',
        },
    }
}

# ============================================================================
# EMAIL CONFIGURATION
# ============================================================================

# Email configuration for notifications (Bangladesh Parliament)
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = os.environ.get('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', '587'))
EMAIL_USE_TLS = os.environ.get('EMAIL_USE_TLS', 'True').lower() == 'true'
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'noreply@parliament.gov.bd')

# Email notification settings for PRP sync operations
PRP_EMAIL_NOTIFICATIONS = {
    'SYNC_SUCCESS': True,                        # Email on successful sync
    'SYNC_FAILURE': True,                        # Email on sync failure  
    'SYNC_WARNINGS': True,                       # Email on sync warnings
    'ADMIN_RECIPIENTS': [
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

# Production-specific settings for Bangladesh Parliament
else:
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
    
    Raises:
        ImproperlyConfigured: If critical PRP settings are missing or invalid
    """
    from django.core.exceptions import ImproperlyConfigured
    
    if not PRP_INTEGRATION_AVAILABLE:
        return  # Skip validation if PRP integration is disabled
    
    # Validate required PRP settings
    required_settings = [
        ('PRP_API_SETTINGS', 'BASE_URL'),
        ('PRP_API_SETTINGS', 'AUTH_USERNAME'),
        ('PRP_API_SETTINGS', 'AUTH_PASSWORD'),
    ]
    
    for setting_group, setting_key in required_settings:
        setting_group_value = globals().get(setting_group, {})
        if not setting_group_value.get(setting_key):
            raise ImproperlyConfigured(
                f"PRP Integration Error: {setting_group}.{setting_key} is required "
                f"but not configured. Please check your environment variables or settings."
            )
    
    # Validate PRP API URL format
    base_url = PRP_API_SETTINGS.get('BASE_URL', '')
    if base_url and not base_url.startswith(('http://', 'https://')):
        raise ImproperlyConfigured(
            f"PRP Integration Error: BASE_URL must start with http:// or https://. "
            f"Got: {base_url}"
        )
    
    # Validate timeout values
    timeout = PRP_API_SETTINGS.get('TIMEOUT', 30)
    if not isinstance(timeout, int) or timeout <= 0:
        raise ImproperlyConfigured(
            f"PRP Integration Error: TIMEOUT must be a positive integer. Got: {timeout}"
        )

# Run validation on startup
try:
    validate_prp_settings()
except Exception as e:
    if DEBUG:
        print(f"⚠️  PRP Settings Validation Warning: {e}")
    else:
        raise

# ============================================================================
# PRP INTEGRATION STATUS & HEALTH CHECK
# ============================================================================

# PRP Integration Status Helper Functions
def get_prp_integration_status():
    """
    Get current PRP integration status.
    
    Returns:
        dict: Integration status information
    """
    return {
        'integration_available': PRP_INTEGRATION_AVAILABLE,
        'api_enabled': PRP_API_ENABLED,
        'base_url': PRP_API_SETTINGS.get('BASE_URL', ''),
        'configured': bool(PRP_API_SETTINGS.get('AUTH_USERNAME')) and bool(PRP_API_SETTINGS.get('AUTH_PASSWORD')),
        'location': 'Bangladesh Parliament Secretariat, Dhaka',
        'timezone': TIME_ZONE,
        'last_validation': None,  # Will be updated by health check
    }

def get_prp_api_endpoints():
    """
    Get all configured PRP API endpoints.
    
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
- DEBUG: Enable/disable debug mode (default: False)
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

Example .env file:
==================
DEBUG=False
SECRET_KEY=your-secret-key-here
DB_NAME=pims_parliament
DB_USER=pims_user
DB_PASSWORD=secure_password_here
DB_HOST=localhost
PRP_INTEGRATION_AVAILABLE=True
PRP_API_ENABLED=True
PRP_API_BASE_URL=https://prp.parliament.gov.bd
PRP_AUTH_USERNAME=ezzetech
PRP_AUTH_PASSWORD=${Fty#3a
EMAIL_HOST=smtp.parliament.gov.bd
EMAIL_HOST_USER=noreply@parliament.gov.bd
DEFAULT_FROM_EMAIL=noreply@parliament.gov.bd
"""