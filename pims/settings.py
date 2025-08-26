"""
Django Settings Configuration for PIMS (Parliament IT Inventory Management System)
Bangladesh Parliament Secretariat, Dhaka, Bangladesh

This settings file includes PRP (Parliament Resource Portal) API integration configuration
for user synchronization between PRP and PIMS systems.

Location: Bangladesh Parliament Secretariat, Dhaka
Project: PIMS-PRP Integration
API Provider: https://prp.parliament.gov.bd
"""

import os
import json
from pathlib import Path
from django.core.exceptions import ImproperlyConfigured
from cryptography.fernet import Fernet

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'your-secret-key-here')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get('DJANGO_DEBUG', 'False').lower() == 'true'

ALLOWED_HOSTS = os.environ.get('DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # PIMS Apps
    'users',
    'devices',
    'locations',
    'vendors',
    'assignments',
    'maintenance',
    
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

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'pims' / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'pims.wsgi.application'

# Database Configuration
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': os.environ.get('DB_NAME', 'pims_db'),
        'USER': os.environ.get('DB_USER', 'root'),
        'PASSWORD': os.environ.get('DB_PASSWORD', ''),
        'HOST': os.environ.get('DB_HOST', 'localhost'),
        'PORT': os.environ.get('DB_PORT', '3306'),
        'OPTIONS': {
            'sql_mode': 'traditional',
            'charset': 'utf8mb4',
            'use_unicode': True,
        },
    }
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Custom User Model
AUTH_USER_MODEL = 'users.CustomUser'

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Dhaka'  # Bangladesh Parliament Secretariat timezone
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [
    BASE_DIR / 'pims' / 'static',
]

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Cache Configuration
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': os.environ.get('REDIS_URL', 'redis://127.0.0.1:6379/1'),
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        },
        'KEY_PREFIX': 'pims',
        'TIMEOUT': 3600,  # 1 hour default timeout
    }
}

# Session Configuration
SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS = 'default'
SESSION_COOKIE_AGE = 3600 * 8  # 8 hours
SESSION_SAVE_EVERY_REQUEST = True

# Logging Configuration
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
            'format': '[PRP-API] {levelname} {asctime} - {name} - {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'logs' / 'pims.log',
            'formatter': 'verbose',
        },
        'prp_file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR / 'logs' / 'prp_integration.log',
            'maxBytes': 1024*1024*10,  # 10MB
            'backupCount': 5,
            'formatter': 'prp_format',
        },
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': True,
        },
        'pims.prp_integration': {
            'handlers': ['prp_file', 'console'],
            'level': 'INFO',
            'propagate': False,
        },
        'users.api': {
            'handlers': ['prp_file', 'console'],
            'level': 'DEBUG' if DEBUG else 'INFO',
            'propagate': False,
        },
    },
}

# ============================================================================
# PRP (Parliament Resource Portal) API Configuration
# ============================================================================
"""
PRP API Integration Settings for PIMS User Synchronization
Location: Bangladesh Parliament Secretariat, Dhaka, Bangladesh
API Provider: https://prp.parliament.gov.bd
Integration Type: One-way sync (PRP → PIMS)
Authentication: Token-based with auto-refresh
"""

# PRP API Base Configuration
PRP_API_BASE_URL = os.environ.get(
    'PRP_API_BASE_URL', 
    'https://prp.parliament.gov.bd'
)

# PRP API Timeout Settings (seconds)
PRP_API_TIMEOUT = int(os.environ.get('PRP_API_TIMEOUT', '30'))
PRP_API_CONNECT_TIMEOUT = int(os.environ.get('PRP_API_CONNECT_TIMEOUT', '10'))
PRP_API_READ_TIMEOUT = int(os.environ.get('PRP_API_READ_TIMEOUT', '20'))

# PRP API Retry Configuration
PRP_API_MAX_RETRIES = int(os.environ.get('PRP_API_MAX_RETRIES', '3'))
PRP_API_RETRY_DELAY = float(os.environ.get('PRP_API_RETRY_DELAY', '1.0'))
PRP_API_BACKOFF_FACTOR = float(os.environ.get('PRP_API_BACKOFF_FACTOR', '2.0'))

# PRP API Rate Limiting
PRP_API_RATE_LIMIT_CALLS = int(os.environ.get('PRP_API_RATE_LIMIT_CALLS', '100'))
PRP_API_RATE_LIMIT_PERIOD = int(os.environ.get('PRP_API_RATE_LIMIT_PERIOD', '3600'))  # 1 hour
PRP_API_RATE_LIMIT_DELAY = float(os.environ.get('PRP_API_RATE_LIMIT_DELAY', '0.5'))

# PRP Sync Configuration
PRP_SYNC_BATCH_SIZE = int(os.environ.get('PRP_SYNC_BATCH_SIZE', '50'))
PRP_SYNC_MAX_CONCURRENT = int(os.environ.get('PRP_SYNC_MAX_CONCURRENT', '5'))
PRP_SYNC_ENABLE_AUTO = os.environ.get('PRP_SYNC_ENABLE_AUTO', 'False').lower() == 'true'
PRP_SYNC_AUTO_INTERVAL = int(os.environ.get('PRP_SYNC_AUTO_INTERVAL', '3600'))  # 1 hour

# PRP Cache Configuration
PRP_CACHE_TIMEOUT_TOKEN = int(os.environ.get('PRP_CACHE_TIMEOUT_TOKEN', '3600'))  # 1 hour
PRP_CACHE_TIMEOUT_DEPARTMENTS = int(os.environ.get('PRP_CACHE_TIMEOUT_DEPARTMENTS', '86400'))  # 24 hours
PRP_CACHE_TIMEOUT_USERS = int(os.environ.get('PRP_CACHE_TIMEOUT_USERS', '1800'))  # 30 minutes

# PRP Data Validation Settings
PRP_VALIDATE_USER_EMAIL = os.environ.get('PRP_VALIDATE_USER_EMAIL', 'True').lower() == 'true'
PRP_VALIDATE_USER_PHONE = os.environ.get('PRP_VALIDATE_USER_PHONE', 'True').lower() == 'true'
PRP_SKIP_INVALID_USERS = os.environ.get('PRP_SKIP_INVALID_USERS', 'True').lower() == 'true'

# PRP User Creation Settings (Business Rules)
PRP_USER_DEFAULT_PASSWORD = os.environ.get('PRP_USER_DEFAULT_PASSWORD', '12345678')
PRP_USER_USERNAME_PREFIX = os.environ.get('PRP_USER_USERNAME_PREFIX', 'prp_')
PRP_USER_AUTO_ACTIVATE = os.environ.get('PRP_USER_AUTO_ACTIVATE', 'True').lower() == 'true'

def get_encryption_key():
    """
    Get or generate encryption key for PRP credentials.
    
    Returns:
        bytes: Encryption key for Fernet encryption
    """
    key_file = BASE_DIR / '.prp_encryption_key'
    
    if key_file.exists():
        with open(key_file, 'rb') as f:
            return f.read()
    else:
        # Generate new key for first-time setup
        key = Fernet.generate_key()
        with open(key_file, 'wb') as f:
            f.write(key)
        # Set secure file permissions (owner read/write only)
        os.chmod(key_file, 0o600)
        return key

def encrypt_credential(credential: str) -> str:
    """
    Encrypt sensitive credential using Fernet encryption.
    
    Args:
        credential (str): Plain text credential to encrypt
        
    Returns:
        str: Base64 encoded encrypted credential
    """
    if not credential:
        return ''
    
    try:
        key = get_encryption_key()
        fernet = Fernet(key)
        encrypted = fernet.encrypt(credential.encode())
        return encrypted.decode()
    except Exception as e:
        raise ImproperlyConfigured(f"Failed to encrypt PRP credential: {e}")

def decrypt_credential(encrypted_credential: str) -> str:
    """
    Decrypt sensitive credential using Fernet encryption.
    
    Args:
        encrypted_credential (str): Base64 encoded encrypted credential
        
    Returns:
        str: Decrypted plain text credential
    """
    if not encrypted_credential:
        return ''
    
    try:
        key = get_encryption_key()
        fernet = Fernet(key)
        decrypted = fernet.decrypt(encrypted_credential.encode())
        return decrypted.decode()
    except Exception as e:
        raise ImproperlyConfigured(f"Failed to decrypt PRP credential: {e}")

# PRP API Credentials (Encrypted Storage)
# Official credentials from PRP Development Team (E-GOV)
_PRP_USERNAME_RAW = 'ezzetech'
_PRP_PASSWORD_RAW = '${Fty#3a'

# Encrypt credentials for secure storage
try:
    PRP_API_CREDENTIALS = {
        'username': encrypt_credential(_PRP_USERNAME_RAW),
        'password': encrypt_credential(_PRP_PASSWORD_RAW),
        'encrypted': True,
    }
except Exception as e:
    # Fallback for development/testing environments
    if DEBUG:
        PRP_API_CREDENTIALS = {
            'username': _PRP_USERNAME_RAW,
            'password': _PRP_PASSWORD_RAW,
            'encrypted': False,
        }
    else:
        raise ImproperlyConfigured(f"PRP credential encryption failed in production: {e}")

# PRP API Endpoints Configuration
PRP_API_ENDPOINTS = {
    # Authentication endpoints
    'AUTH_TOKEN': '/api/authentication/external?action=token',
    'AUTH_REFRESH': '/api/authentication/external?action=refresh-token',
    
    # Data retrieval endpoints (PIMS integration scope)
    'EMPLOYEE_DETAILS': '/api/secure/external?action=employee_details&departmentId={department_id}',
    'DEPARTMENTS': '/api/secure/external?action=departments',
    
    # Health check endpoint
    'HEALTH_CHECK': '/api/health',
}

# PRP API Response Configuration
PRP_API_RESPONSE = {
    'SUCCESS_CODE': 200,
    'SUCCESS_MESSAGE': 'Success',
    'PAYLOAD_KEY': 'payload',
    'MESSAGE_KEY': 'msg',
    'RESPONSE_CODE_KEY': 'responseCode',
}

# PRP Field Mapping Configuration (PRP API → PIMS Model)
PRP_FIELD_MAPPING = {
    # Employee data mapping
    'EMPLOYEE': {
        'userId': 'employee_id',
        'nameEng': 'name_fields',  # Split into first_name + last_name
        'email': 'email',
        'designationEng': 'designation',
        'mobile': 'phone_number',
        'photo': 'profile_image',  # Convert byte array to image
        'status': 'status_fields',  # Maps to is_active + is_active_employee
    },
    
    # Department data mapping
    'DEPARTMENT': {
        'nameEng': 'office',
        'nameBng': 'office_bengali',  # Optional field
        'id': 'department_id',
        'isWing': 'is_wing',
    },
}

# PRP Integration Feature Flags
PRP_FEATURES = {
    'ENABLE_SYNC': os.environ.get('PRP_ENABLE_SYNC', 'True').lower() == 'true',
    'ENABLE_AUTO_SYNC': os.environ.get('PRP_ENABLE_AUTO_SYNC', 'False').lower() == 'true',
    'ENABLE_PHOTO_SYNC': os.environ.get('PRP_ENABLE_PHOTO_SYNC', 'True').lower() == 'true',
    'ENABLE_STATUS_OVERRIDE': os.environ.get('PRP_ENABLE_STATUS_OVERRIDE', 'True').lower() == 'true',
    'ENABLE_SYNC_LOGGING': os.environ.get('PRP_ENABLE_SYNC_LOGGING', 'True').lower() == 'true',
    'ENABLE_HEALTH_CHECK': os.environ.get('PRP_ENABLE_HEALTH_CHECK', 'True').lower() == 'true',
}

# PRP Business Rules Configuration
PRP_BUSINESS_RULES = {
    # User management rules
    'NO_LOCAL_USER_CREATION': True,  # Business rule: No user creation from PIMS
    'ONE_WAY_SYNC_ONLY': True,       # Business rule: PRP → PIMS only
    'ADMIN_STATUS_OVERRIDE': True,   # Business rule: Admin can override user status
    'PRP_FIELDS_READONLY': True,     # Business rule: PRP fields are read-only in PIMS
    'ADMIN_CONTROLLED_SYNC': True,   # Business rule: Only admin can trigger sync
    
    # Data authority rules
    'PRP_IS_AUTHORITATIVE': True,    # Business rule: PRP is single source of truth
    'PRESERVE_LOCAL_NOTES': True,    # Preserve PIMS-specific notes field
    'PRESERVE_LOCAL_PERMISSIONS': True,  # Preserve PIMS role/permission assignments
}

# PRP Monitoring and Alerting
PRP_MONITORING = {
    'ENABLE_ALERTS': os.environ.get('PRP_ENABLE_ALERTS', 'True').lower() == 'true',
    'ALERT_EMAIL': os.environ.get('PRP_ALERT_EMAIL', 'admin@parliament.gov.bd').split(','),
    'ALERT_ON_SYNC_FAILURE': True,
    'ALERT_ON_AUTH_FAILURE': True,
    'ALERT_ON_DATA_VALIDATION_ERROR': True,
    'HEALTH_CHECK_INTERVAL': int(os.environ.get('PRP_HEALTH_CHECK_INTERVAL', '300')),  # 5 minutes
}

# PRP Integration Status Tracking
PRP_STATUS = {
    'LAST_SUCCESSFUL_SYNC': None,  # Will be updated by sync operations
    'LAST_SYNC_ATTEMPT': None,     # Will be updated by sync operations
    'SYNC_ERROR_COUNT': 0,         # Will be updated by sync operations
    'API_HEALTH_STATUS': 'Unknown', # Will be updated by health checks
}

# Email Configuration for PRP Notifications
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = os.environ.get('EMAIL_HOST', 'smtp.parliament.gov.bd')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', '587'))
EMAIL_USE_TLS = os.environ.get('EMAIL_USE_TLS', 'True').lower() == 'true'
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', 'pims@parliament.gov.bd')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')
DEFAULT_FROM_EMAIL = EMAIL_HOST_USER
SERVER_EMAIL = EMAIL_HOST_USER

# ============================================================================
# Security Settings for PRP Integration
# ============================================================================

# CSRF Configuration
CSRF_TRUSTED_ORIGINS = [
    'https://prp.parliament.gov.bd',
    'https://pims.parliament.gov.bd',
]

# CORS Configuration (if needed)
CORS_ALLOWED_ORIGINS = [
    'https://prp.parliament.gov.bd',
]

# Security Headers
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

# Session Security
SESSION_COOKIE_SECURE = not DEBUG
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'

# CSRF Security
CSRF_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = 'Lax'

# ============================================================================
# Environment-Specific Overrides
# ============================================================================

# Production Environment Settings
if os.environ.get('DJANGO_ENV') == 'production':
    # Force HTTPS in production
    SECURE_SSL_REDIRECT = True
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    
    # Enhanced security for production
    SECURE_HSTS_SECONDS = 31536000  # 1 year
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    
    # Stricter PRP settings for production
    PRP_API_TIMEOUT = 20  # Shorter timeout in production
    PRP_SYNC_ENABLE_AUTO = False  # Disable auto-sync in production
    
    # Enhanced logging for production
    LOGGING['handlers']['file']['level'] = 'WARNING'
    LOGGING['handlers']['prp_file']['level'] = 'INFO'

# Development Environment Settings
elif DEBUG:
    # Development-specific PRP settings
    PRP_API_TIMEOUT = 60  # Longer timeout for development
    PRP_SYNC_ENABLE_AUTO = True  # Enable auto-sync in development
    
    # Enhanced logging for development
    LOGGING['handlers']['console']['level'] = 'DEBUG'
    LOGGING['loggers']['users.api']['level'] = 'DEBUG'
    
    # Development email backend
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# ============================================================================
# PRP Configuration Validation
# ============================================================================

def validate_prp_configuration():
    """
    Validate PRP configuration settings on startup.
    
    Raises:
        ImproperlyConfigured: If required PRP settings are missing or invalid
    """
    required_settings = [
        ('PRP_API_BASE_URL', PRP_API_BASE_URL),
        ('PRP_API_CREDENTIALS', PRP_API_CREDENTIALS),
        ('PRP_API_ENDPOINTS', PRP_API_ENDPOINTS),
    ]
    
    for setting_name, setting_value in required_settings:
        if not setting_value:
            raise ImproperlyConfigured(f"Required PRP setting {setting_name} is not configured")
    
    # Validate API base URL format
    if not PRP_API_BASE_URL.startswith(('http://', 'https://')):
        raise ImproperlyConfigured("PRP_API_BASE_URL must start with http:// or https://")
    
    # Validate credentials
    if not PRP_API_CREDENTIALS.get('username') or not PRP_API_CREDENTIALS.get('password'):
        raise ImproperlyConfigured("PRP API credentials (username/password) are required")
    
    # Validate timeout settings
    if PRP_API_TIMEOUT <= 0:
        raise ImproperlyConfigured("PRP_API_TIMEOUT must be a positive integer")
    
    # Validate batch size
    if PRP_SYNC_BATCH_SIZE <= 0 or PRP_SYNC_BATCH_SIZE > 1000:
        raise ImproperlyConfigured("PRP_SYNC_BATCH_SIZE must be between 1 and 1000")

# Run validation on startup (only in production)
if not DEBUG:
    validate_prp_configuration()

# ============================================================================
# Helper Functions for PRP Integration
# ============================================================================

def get_prp_credentials():
    """
    Get decrypted PRP API credentials.
    
    Returns:
        dict: Dictionary containing username and password
    """
    if PRP_API_CREDENTIALS.get('encrypted', False):
        return {
            'username': decrypt_credential(PRP_API_CREDENTIALS['username']),
            'password': decrypt_credential(PRP_API_CREDENTIALS['password']),
        }
    else:
        return {
            'username': PRP_API_CREDENTIALS['username'],
            'password': PRP_API_CREDENTIALS['password'],
        }

def get_prp_endpoint_url(endpoint_key: str, **kwargs) -> str:
    """
    Get full PRP API endpoint URL.
    
    Args:
        endpoint_key (str): Key from PRP_API_ENDPOINTS
        **kwargs: Format arguments for endpoint URL
        
    Returns:
        str: Full endpoint URL
        
    Raises:
        KeyError: If endpoint_key is not found
    """
    if endpoint_key not in PRP_API_ENDPOINTS:
        raise KeyError(f"PRP endpoint '{endpoint_key}' not found")
    
    endpoint_path = PRP_API_ENDPOINTS[endpoint_key]
    if kwargs:
        endpoint_path = endpoint_path.format(**kwargs)
    
    return f"{PRP_API_BASE_URL.rstrip('/')}{endpoint_path}"

def is_prp_feature_enabled(feature_name: str) -> bool:
    """
    Check if a PRP feature is enabled.
    
    Args:
        feature_name (str): Feature name from PRP_FEATURES
        
    Returns:
        bool: True if feature is enabled, False otherwise
    """
    return PRP_FEATURES.get(feature_name, False)

def get_prp_business_rule(rule_name: str) -> bool:
    """
    Get PRP business rule setting.
    
    Args:
        rule_name (str): Rule name from PRP_BUSINESS_RULES
        
    Returns:
        bool: Business rule value
    """
    return PRP_BUSINESS_RULES.get(rule_name, False)

# ============================================================================
# Template Design Pattern Settings (Flat Design with High Contrast)
# ============================================================================

# Template context processors for PRP integration
TEMPLATES[0]['OPTIONS']['context_processors'].extend([
    'users.context_processors.prp_integration_status',
])

# Template settings for Bangladesh Parliament Secretariat
PIMS_TEMPLATE_SETTINGS = {
    'DESIGN_SYSTEM': 'flat',  # Flat design (NO glassmorphism)
    'COLOR_SCHEME': {
        'PRIMARY_TEAL': '#14b8a6',
        'PRIMARY_ORANGE': '#f97316', 
        'PRIMARY_RED': '#ef4444',
        'TEXT_PRIMARY': '#1e293b',
        'TEXT_SECONDARY': '#64748b',
        'BACKGROUND_PRIMARY': '#ffffff',
        'BACKGROUND_SECONDARY': '#f8fafc',
    },
    'RESPONSIVE_BREAKPOINTS': ['mobile', 'tablet', 'laptop', 'desktop', 'big_monitors'],
    'HIGH_CONTRAST': True,
    'LOCATION_CONTEXT': 'Bangladesh Parliament Secretariat, Dhaka',
    'TIMEZONE_DISPLAY': 'Asia/Dhaka',
}

# Static files configuration for template design
STATICFILES_FINDERS = [
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
]

# Ensure logs directory exists
os.makedirs(BASE_DIR / 'logs', exist_ok=True)

# ============================================================================
# Final Configuration Summary
# ============================================================================
"""
PIMS-PRP Integration Configuration Summary:
==========================================

API Configuration:
- Base URL: https://prp.parliament.gov.bd
- Authentication: Token-based with auto-refresh
- Timeout: 30 seconds (configurable)
- Retry: 3 attempts with exponential backoff
- Rate Limiting: 100 calls/hour
- Batch Size: 50 users per sync operation

Security Features:
- Encrypted credential storage using Fernet
- Secure token management and refresh
- Comprehensive audit logging
- Rate limiting and retry mechanisms
- Input validation and sanitization

Business Rules Implementation:
- One-way sync: PRP → PIMS only
- Admin-controlled sync operations
- Status override by PIMS admin
- PRP fields are read-only in PIMS
- Default password: "12345678" for PRP users

Template Design:
- Flat design with high contrast
- Color scheme: Teal, Orange, Red
- Responsive design for all devices
- Bangladesh Parliament Secretariat branding
- Asia/Dhaka timezone consistency

Location: Bangladesh Parliament Secretariat, Dhaka, Bangladesh
Integration Type: User synchronization from PRP to PIMS
Project Status: Ready for implementation
"""