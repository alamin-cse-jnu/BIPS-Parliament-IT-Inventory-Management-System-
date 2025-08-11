"""
Centralized QR Code Generation Utilities for PIMS
Bangladesh Parliament Secretariat

This module provides unified QR code generation functions for all PIMS entities:
- Devices (with QRCode model storage)
- Locations (with LocationQRCode model storage)
- Assignments (with AssignmentQRCode model storage)
- Users (future implementation)

Key Features:
- Consistent QR code format and styling across all apps
- Unified QRCode model approach for all entities
- Centralized data structure for QR content
- Unified error handling and validation
- Configurable QR code parameters
"""

import qrcode
import json
import uuid
import io
import os
from PIL import Image
from django.core.files.base import ContentFile
from django.urls import reverse
from django.conf import settings
from django.utils import timezone


class QRCodeGenerator:
    """
    Centralized QR code generator with consistent settings and methods.
    """
    
    # Default QR Code Settings
    DEFAULT_SETTINGS = {
        'version': 1,
        'error_correction': qrcode.constants.ERROR_CORRECT_L,
        'box_size': 10,
        'border': 4,
        'fill_color': 'black',
        'back_color': 'white',
        'format': 'PNG',
        'size': 200
    }
    
    def __init__(self, **kwargs):
        """Initialize QR generator with custom settings."""
        self.settings = {**self.DEFAULT_SETTINGS, **kwargs}
    
    def create_qr_image(self, data):
        """
        Create QR code image from data.
        
        Args:
            data: String or dict to encode in QR code
            
        Returns:
            PIL Image object
        """
        # Convert data to JSON string if it's a dict
        if isinstance(data, dict):
            qr_data = json.dumps(data, ensure_ascii=False)
        else:
            qr_data = str(data)
        
        # Create QR code
        qr = qrcode.QRCode(
            version=self.settings['version'],
            error_correction=self.settings['error_correction'],
            box_size=self.settings['box_size'],
            border=self.settings['border'],
        )
        
        qr.add_data(qr_data)
        qr.make(fit=True)
        
        # Create image
        img = qr.make_image(
            fill_color=self.settings['fill_color'],
            back_color=self.settings['back_color']
        )
        
        return img
    
    def save_image_to_content_file(self, img, filename):
        """
        Convert PIL image to Django ContentFile.
        
        Args:
            img: PIL Image object
            filename: Desired filename
            
        Returns:
            ContentFile object
        """
        buffer = io.BytesIO()
        img.save(buffer, format=self.settings['format'])
        file_content = ContentFile(buffer.getvalue())
        return file_content


# ============================================================================
# DEVICE QR CODE FUNCTIONS
# ============================================================================

def generate_device_qr_data(device, request=None):
    """
    Generate standardized QR code data for a device.
    
    Args:
        device: Device model instance
        request: HTTP request object for building absolute URLs
        
    Returns:
        dict: QR code data structure
    """
    qr_data = {
        'type': 'device',
        'id': device.id,
        'device_id': device.device_id,
        'brand': device.brand,
        'model': device.model,
        'serial_number': device.serial_number,
        'category': device.subcategory.category.name if device.subcategory else None,
        'subcategory': device.subcategory.name if device.subcategory else None,
        'status': device.status,
        'condition': device.condition,
        'asset_tag': getattr(device, 'asset_tag', None),
        'created_at': device.created_at.isoformat() if device.created_at else None,
        'generated_at': timezone.now().isoformat(),
    }
    
    # Add URL if request is available
    if request:
        qr_data['url'] = request.build_absolute_uri(
            reverse('devices:detail', kwargs={'pk': device.pk})
        )
    
    return qr_data


def create_device_qr_code(device, request=None, **qr_settings):
    """
    Create and save QR code for a device using the Device QRCode model.
    
    Args:
        device: Device model instance
        request: HTTP request object
        **qr_settings: Custom QR code settings
        
    Returns:
        QRCode instance or None if error
    """
    try:
        # Import here to avoid circular imports
        from devices.models import QRCode
        
        # Generate QR data
        qr_data = generate_device_qr_data(device, request)
        
        # Create QR generator
        generator = QRCodeGenerator(**qr_settings)
        
        # Generate QR image
        qr_image = generator.create_qr_image(qr_data)
        
        # Deactivate existing QR codes for this device
        QRCode.objects.filter(device=device, is_active=True).update(is_active=False)
        
        # Create new QR code object
        qr_code_obj = QRCode.objects.create(
            device=device,
            qr_data=json.dumps(qr_data),
            size=generator.settings['size'],
            format=generator.settings['format']
        )
        
        # Save QR image
        file_content = generator.save_image_to_content_file(
            qr_image, 
            f'device_{device.device_id}_qr.png'
        )
        
        qr_code_obj.qr_code.save(
            f'device_{device.device_id}_qr.png',
            file_content
        )
        
        return qr_code_obj
        
    except Exception as e:
        print(f"Error creating device QR code: {e}")
        return None


# ============================================================================
# LOCATION QR CODE FUNCTIONS
# ============================================================================

def generate_location_qr_data(location, request=None):
    """
    Generate standardized QR code data for a location.
    
    Args:
        location: Location model instance
        request: HTTP request object for building absolute URLs
        
    Returns:
        dict: QR code data structure
    """
    qr_data = {
        'type': 'location',
        'id': location.id,
        'location_code': getattr(location, 'location_code', None),
        'name': location.name,
        'building': location.building.name if location.building else None,
        'floor': location.floor.name if location.floor else None,
        'block': location.block.name if location.block else None,
        'room': location.room.name if location.room else None,
        'office': location.office.name if location.office else None,
        'coordinates': {
            'latitude': float(location.latitude) if location.latitude else None,
            'longitude': float(location.longitude) if location.longitude else None
        },
        'is_active': location.is_active,
        'created_at': location.created_at.isoformat() if location.created_at else None,
        'generated_at': timezone.now().isoformat(),
    }
    
    # Add URL if request is available
    if request:
        qr_data['url'] = request.build_absolute_uri(
            reverse('locations:detail', kwargs={'pk': location.pk})
        )
    
    return qr_data


def create_location_qr_code(location, request=None, **qr_settings):
    """
    Create and save QR code for a location using the LocationQRCode model.
    
    Args:
        location: Location model instance
        request: HTTP request object
        **qr_settings: Custom QR code settings
        
    Returns:
        LocationQRCode instance or None if error
    """
    try:
        # Import here to avoid circular imports
        from locations.models import LocationQRCode
        
        # Generate QR data
        qr_data = generate_location_qr_data(location, request)
        
        # Create QR generator
        generator = QRCodeGenerator(**qr_settings)
        
        # Generate QR image
        qr_image = generator.create_qr_image(qr_data)
        
        # Deactivate existing QR codes for this location
        LocationQRCode.objects.filter(location=location, is_active=True).update(is_active=False)
        
        # Create new QR code object
        qr_code_obj = LocationQRCode.objects.create(
            location=location,
            qr_data=json.dumps(qr_data),
            size=generator.settings['size'],
            format=generator.settings['format']
        )
        
        # Save QR image
        file_content = generator.save_image_to_content_file(
            qr_image, 
            f'location_{location.id}_qr.png'
        )
        
        qr_code_obj.qr_code.save(
            f'location_{location.id}_qr.png',
            file_content
        )
        
        return qr_code_obj
        
    except Exception as e:
        print(f"Error creating location QR code: {e}")
        return None


# ============================================================================
# ASSIGNMENT QR CODE FUNCTIONS
# ============================================================================

def generate_assignment_qr_data(assignment, request=None):
    """
    Generate standardized QR code data for an assignment.
    
    Args:
        assignment: Assignment model instance
        request: HTTP request object for building absolute URLs
        
    Returns:
        dict: QR code data structure
    """
    qr_data = {
        'type': 'assignment',
        'id': assignment.id,
        'assignment_id': assignment.assignment_id,
        'device': {
            'id': assignment.device.id,
            'device_id': assignment.device.device_id,
            'brand': assignment.device.brand,
            'model': assignment.device.model,
            'serial_number': assignment.device.serial_number,
        },
        'assigned_to': {
            'id': assignment.assigned_to.id,
            'name': assignment.assigned_to.get_full_name(),
            'username': assignment.assigned_to.username,
            'employee_id': getattr(assignment.assigned_to, 'employee_id', None),
        },
        'assignment_details': {
            'type': assignment.assignment_type,
            'status': assignment.status,
            'assigned_date': assignment.assigned_date.isoformat(),
            'expected_return_date': assignment.expected_return_date.isoformat() if assignment.expected_return_date else None,
            'purpose': assignment.purpose,
        },
        'location': {
            'id': assignment.assigned_location.id if assignment.assigned_location else None,
            'name': assignment.assigned_location.name if assignment.assigned_location else None,
        } if assignment.assigned_location else None,
        'created_at': assignment.created_at.isoformat() if assignment.created_at else None,
        'generated_at': timezone.now().isoformat(),
    }
    
    # Add URL if request is available
    if request:
        qr_data['url'] = request.build_absolute_uri(
            reverse('assignments:detail', kwargs={'pk': assignment.pk})
        )
    
    return qr_data


def create_assignment_qr_code(assignment, request=None, **qr_settings):
    """
    Create and save QR code for an assignment using the AssignmentQRCode model.
    
    Args:
        assignment: Assignment model instance
        request: HTTP request object
        **qr_settings: Custom QR code settings
        
    Returns:
        AssignmentQRCode instance or None if error
    """
    try:
        # Import here to avoid circular imports
        from assignments.models import AssignmentQRCode
        
        # Generate QR data
        qr_data = generate_assignment_qr_data(assignment, request)
        
        # Create QR generator
        generator = QRCodeGenerator(**qr_settings)
        
        # Generate QR image
        qr_image = generator.create_qr_image(qr_data)
        
        # Deactivate existing QR codes for this assignment
        AssignmentQRCode.objects.filter(assignment=assignment, is_active=True).update(is_active=False)
        
        # Create new QR code object
        qr_code_obj = AssignmentQRCode.objects.create(
            assignment=assignment,
            qr_data=json.dumps(qr_data),
            size=generator.settings['size'],
            format=generator.settings['format']
        )
        
        # Save QR image
        file_content = generator.save_image_to_content_file(
            qr_image, 
            f'assignment_{assignment.assignment_id}_qr.png'
        )
        
        qr_code_obj.qr_code.save(
            f'assignment_{assignment.assignment_id}_qr.png',
            file_content
        )
        
        return qr_code_obj
        
    except Exception as e:
        print(f"Error creating assignment QR code: {e}")
        return None


# ============================================================================
# BULK OPERATIONS
# ============================================================================

def bulk_generate_device_qr_codes(devices, request=None, regenerate_existing=False):
    """
    Generate QR codes for multiple devices.
    
    Args:
        devices: Queryset or list of Device instances
        request: HTTP request object
        regenerate_existing: Whether to regenerate existing QR codes
        
    Returns:
        dict: Results summary
    """
    results = {
        'generated': 0,
        'updated': 0,
        'skipped': 0,
        'errors': 0,
        'error_devices': []
    }
    
    for device in devices:
        try:
            # Import here to avoid circular imports
            from devices.models import QRCode
            
            # Check if device already has QR code
            existing_qr = QRCode.objects.filter(device=device, is_active=True).first()
            
            if existing_qr and not regenerate_existing:
                results['skipped'] += 1
                continue
            
            # Generate QR code
            qr_code = create_device_qr_code(device, request)
            
            if qr_code:
                if existing_qr:
                    results['updated'] += 1
                else:
                    results['generated'] += 1
            else:
                results['errors'] += 1
                results['error_devices'].append(device.device_id)
                
        except Exception as e:
            results['errors'] += 1
            results['error_devices'].append(f"{device.device_id}: {str(e)}")
    
    return results


def bulk_generate_location_qr_codes(locations, request=None, regenerate_existing=False):
    """
    Generate QR codes for multiple locations.
    
    Args:
        locations: Queryset or list of Location instances
        request: HTTP request object
        regenerate_existing: Whether to regenerate existing QR codes
        
    Returns:
        dict: Results summary
    """
    results = {
        'generated': 0,
        'updated': 0,
        'skipped': 0,
        'errors': 0,
        'error_locations': []
    }
    
    for location in locations:
        try:
            # Import here to avoid circular imports
            from locations.models import LocationQRCode
            
            # Check if location already has QR code
            existing_qr = LocationQRCode.objects.filter(location=location, is_active=True).first()
            
            if existing_qr and not regenerate_existing:
                results['skipped'] += 1
                continue
            
            # Generate QR code
            qr_code = create_location_qr_code(location, request)
            
            if qr_code:
                if existing_qr:
                    results['updated'] += 1
                else:
                    results['generated'] += 1
            else:
                results['errors'] += 1
                results['error_locations'].append(str(location.id))
                
        except Exception as e:
            results['errors'] += 1
            results['error_locations'].append(f"{location.id}: {str(e)}")
    
    return results


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_qr_code_for_device(device):
    """
    Get active QR code for a device.
    
    Args:
        device: Device model instance
        
    Returns:
        QRCode instance or None
    """
    try:
        from devices.models import QRCode
        return QRCode.objects.filter(device=device, is_active=True).first()
    except:
        return None


def get_qr_code_for_location(location):
    """
    Get active QR code for a location.
    
    Args:
        location: Location model instance
        
    Returns:
        LocationQRCode instance or None
    """
    try:
        from locations.models import LocationQRCode
        return LocationQRCode.objects.filter(location=location, is_active=True).first()
    except:
        return None


def get_qr_code_for_assignment(assignment):
    """
    Get active QR code for an assignment.
    
    Args:
        assignment: Assignment model instance
        
    Returns:
        AssignmentQRCode instance or None
    """
    try:
        from assignments.models import AssignmentQRCode
        return AssignmentQRCode.objects.filter(assignment=assignment, is_active=True).first()
    except:
        return None