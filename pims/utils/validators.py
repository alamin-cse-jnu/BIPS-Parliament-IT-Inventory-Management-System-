# pims/utils/validators.py

import os
from django.core.exceptions import ValidationError
from django.conf import settings
from PIL import Image


def validate_image_file(value):
    """
    Validate uploaded image files for PIMS.
    
    Checks:
    - File extension
    - File size
    - Image validity
    """
    if not value:
        return
    
    # Check file extension
    ext = os.path.splitext(value.name)[1].lower()
    allowed_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp']
    
    if ext not in allowed_extensions:
        raise ValidationError(
            f'Only image files are allowed. Supported formats: {", ".join(allowed_extensions)}'
        )
    
    # Check file size (2MB limit)
    max_size = 2 * 1024 * 1024  # 2MB
    if value.size > max_size:
        raise ValidationError(f'File size cannot exceed {max_size // (1024*1024)}MB.')
    
    # Validate that it's actually an image
    try:
        image = Image.open(value)
        image.verify()
    except Exception:
        raise ValidationError('Invalid image file.')


def validate_user_image(value):
    """Specific validation for user profile images."""
    validate_image_file(value)
    
    # Additional checks for user images
    if value:
        try:
            image = Image.open(value)
            width, height = image.size
            
            # Check minimum dimensions
            if width < 100 or height < 100:
                raise ValidationError('Profile image must be at least 100x100 pixels.')
            
            # Check maximum dimensions
            if width > 2000 or height > 2000:
                raise ValidationError('Profile image cannot exceed 2000x2000 pixels.')
                
        except Exception as e:
            if isinstance(e, ValidationError):
                raise
            raise ValidationError('Invalid image file.')


def validate_employee_id(value):
    """Validate employee ID format."""
    if not value.isdigit():
        raise ValidationError('Employee ID must contain only numbers.')
    
    if len(value) < 3:
        raise ValidationError('Employee ID must be at least 3 digits.')
    
    if len(value) > 20:
        raise ValidationError('Employee ID cannot exceed 20 digits.')


def validate_phone_number(value):
    """Validate Bangladesh phone number format."""
    import re
    
    # Bangladesh phone number patterns
    patterns = [
        r'^\+8801[3-9]\d{8}$',  # +8801XXXXXXXXX
        r'^01[3-9]\d{8}$',      # 01XXXXXXXXX
        r'^8801[3-9]\d{8}$',    # 8801XXXXXXXXX
    ]
    
    if not any(re.match(pattern, value) for pattern in patterns):
        raise ValidationError(
            'Please enter a valid Bangladesh phone number. '
            'Format: +8801XXXXXXXXX or 01XXXXXXXXX'
        )