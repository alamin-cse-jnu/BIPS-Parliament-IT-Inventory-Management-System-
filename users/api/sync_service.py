"""
PRP Synchronization Service - Business Logic for PIMS-PRP Integration
====================================================================

Complete business logic service for PRP (Parliament Resource Portal) user synchronization
in PIMS at Bangladesh Parliament Secretariat, Dhaka.

Location: Bangladesh Parliament Secretariat, Dhaka, Bangladesh
Project: PIMS-PRP Integration  
Purpose: Core business logic for syncing PRP user data to PIMS

Based on Official Integration Requirements:
- API Base URL: https://prp.parliament.gov.bd
- Authentication: Bearer token (username: "ezzetech", password: "${Fty#3a")
- Data Models: EmployeeDetails → CustomUser field mapping
- Business Rules: One-way sync, admin override protection, status management

Key Features:
- Comprehensive field mapping (PRP EmployeeDetails → PIMS CustomUser)
- Business rule compliance (status override, one-way sync)
- Photo conversion (PRP byte[] → Django ImageField)
- Batch synchronization with performance optimization
- Detailed sync reporting and error handling
- Admin-controlled operations with audit logging

Data Mapping (Per Integration Context):
--------------------------------------
PRP EmployeeDetails → PIMS CustomUser Fields:
- userId → employee_id  
- nameEng → first_name + last_name (split)
- email → email
- designationEng → designation
- mobile → phone_number
- photo (byte[]) → profile_image (converted)
- status → is_active + is_active_employee

PRP DepartmentModel → PIMS Office Field:
- nameEng → office

Business Rules Implementation:
-----------------------------
1. User Creation: NO user creation from PIMS interface
2. Data Authority: PRP is the single source of truth
3. Sync Direction: One-way PRP → PIMS only
4. Field Editing: PRP-sourced fields are read-only in PIMS
5. Status Override: PIMS admin can override user status
6. Sync Control: Admin-initiated sync operations only

Usage Example:
-------------
from users.api.prp_client import create_prp_client
from users.api.sync_service import PRPSyncService

# Initialize service
prp_client = create_prp_client()
sync_service = PRPSyncService(prp_client)

# Sync specific department
result = sync_service.sync_department_users(department_id=1)

# Sync all departments
result = sync_service.sync_all_departments()

# Check results
if result.success:
    print(f"Created: {result.users_created}, Updated: {result.users_updated}")
"""

import base64
import io
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple, Union
from PIL import Image
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.db import transaction, IntegrityError
from django.utils import timezone
from django.conf import settings
from django.core.exceptions import ValidationError

from .prp_client import PRPClient
from .exceptions import (
    PRPException,
    PRPSyncError,
    PRPDataValidationError,
    PRPConnectionError,
    PRPAuthenticationError,
    PRPBusinessRuleError
)

# Configure logging
logger = logging.getLogger('pims.prp_integration.sync_service')

# Get User model
User = get_user_model()


class PRPSyncResult:
    """
    Container for PRP synchronization operation results.
    
    Provides comprehensive tracking of sync statistics, errors, and outcomes
    for audit logging and admin reporting at Bangladesh Parliament Secretariat.
    
    Attributes:
        users_created: Number of new users created from PRP
        users_updated: Number of existing users updated
        users_skipped: Number of users skipped (no changes)
        users_errors: Number of users with sync errors
        departments_processed: Number of departments processed
        errors: List of error messages
        warnings: List of warning messages
        success: Overall operation success status
        sync_details: Detailed operation information
    """
    
    def __init__(self):
        """Initialize empty sync result with Bangladesh context."""
        self.users_created: int = 0
        self.users_updated: int = 0
        self.users_skipped: int = 0
        self.users_errors: int = 0
        self.departments_processed: int = 0
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.success: bool = True
        self.start_time: datetime = timezone.now()
        self.end_time: Optional[datetime] = None
        self.location: str = "Bangladesh Parliament Secretariat, Dhaka"
        self.sync_details: Dict[str, Any] = {
            'location': self.location,
            'sync_type': 'PRP_TO_PIMS',
            'business_rules_applied': [],
            'field_mappings': [],
            'processed_users': []
        }
    
    def add_created_user(self, user_id: str, details: Optional[str] = None):
        """Record a user creation with context."""
        self.users_created += 1
        self.sync_details['processed_users'].append({
            'user_id': user_id,
            'action': 'CREATED',
            'details': details,
            'timestamp': timezone.now().isoformat()
        })
    
    def add_updated_user(self, user_id: str, details: Optional[str] = None):
        """Record a user update with context."""
        self.users_updated += 1
        self.sync_details['processed_users'].append({
            'user_id': user_id,
            'action': 'UPDATED', 
            'details': details,
            'timestamp': timezone.now().isoformat()
        })
    
    def add_skipped_user(self, user_id: str, reason: str):
        """Record a skipped user with reason."""
        self.users_skipped += 1
        self.sync_details['processed_users'].append({
            'user_id': user_id,
            'action': 'SKIPPED',
            'reason': reason,
            'timestamp': timezone.now().isoformat()
        })
    
    def add_error_user(self, user_id: str, error: str):
        """Record a user sync error."""
        self.users_errors += 1
        self.errors.append(f"User {user_id}: {error}")
        self.sync_details['processed_users'].append({
            'user_id': user_id,
            'action': 'ERROR',
            'error': error,
            'timestamp': timezone.now().isoformat()
        })
    
    def add_warning(self, message: str):
        """Add a warning message."""
        self.warnings.append(message)
    
    def add_business_rule(self, rule_name: str, applied: bool, details: str = ""):
        """Record business rule application."""
        self.sync_details['business_rules_applied'].append({
            'rule_name': rule_name,
            'applied': applied,
            'details': details
        })
    
    def finalize(self) -> 'PRPSyncResult':
        """Finalize the sync result with end time and status."""
        self.end_time = timezone.now()
        self.success = self.users_errors == 0
        
        # Calculate duration
        if self.start_time:
            duration = (self.end_time - self.start_time).total_seconds()
            self.sync_details['duration_seconds'] = duration
        
        return self
    
    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of the sync operation."""
        return {
            'success': self.success,
            'location': self.location,
            'users_created': self.users_created,
            'users_updated': self.users_updated,
            'users_skipped': self.users_skipped,
            'users_errors': self.users_errors,
            'departments_processed': self.departments_processed,
            'total_users_processed': (
                self.users_created + self.users_updated + 
                self.users_skipped + self.users_errors
            ),
            'duration_seconds': self.sync_details.get('duration_seconds', 0),
            'errors_count': len(self.errors),
            'warnings_count': len(self.warnings)
        }
    
    def __str__(self) -> str:
        """String representation of sync result."""
        return (
            f"PRP Sync Result: Created={self.users_created}, "
            f"Updated={self.users_updated}, Skipped={self.users_skipped}, "
            f"Errors={self.users_errors}, Success={self.success}"
        )


class PRPSyncService:
    """
    Complete PRP synchronization service implementing all business rules.
    
    Handles the complete lifecycle of PRP user synchronization including:
    - Data retrieval from PRP API
    - Field mapping PRP EmployeeDetails → PIMS CustomUser
    - Business rule enforcement (status override, one-way sync)
    - Photo processing and conversion
    - Database transactions with rollback support
    - Comprehensive audit logging
    
    Location: Bangladesh Parliament Secretariat, Dhaka, Bangladesh
    """
    
    def __init__(self, prp_client: PRPClient):
        """
        Initialize sync service with PRP client.
        
        Args:
            prp_client: Authenticated PRP API client
        """
        self.prp_client = prp_client
        self.location = "Bangladesh Parliament Secretariat, Dhaka, Bangladesh"
        
        # Default sync options (can be overridden)
        self.sync_options = {
            'sync_photos': True,
            'respect_admin_overrides': True,
            'default_password': '12345678',  # As specified in requirements
            'batch_size': 50,
            'max_photo_size': 5 * 1024 * 1024,  # 5MB
            'skip_recent_sync': True,  # Skip users synced within 1 hour
        }
        
        logger.info(f"🏛️  PRP Sync Service initialized for {self.location}")
    
    def sync_department_users(
        self, 
        department_id: int, 
        force: bool = False,
        sync_options: Optional[Dict[str, Any]] = None
    ) -> PRPSyncResult:
        """
        Sync all users from a specific PRP department.
        
        Args:
            department_id: PRP department ID from DepartmentModel
            force: If True, ignore recent sync timestamps
            sync_options: Override default sync options
            
        Returns:
            PRPSyncResult: Detailed sync operation results
            
        Raises:
            PRPSyncError: If department sync fails
            PRPConnectionError: If PRP API is unreachable
        """
        result = PRPSyncResult()
        
        # Update sync options if provided
        if sync_options:
            self.sync_options.update(sync_options)
        
        logger.info(f"🏢 Starting department sync for department {department_id}")
        
        try:
            # Get department info for context
            departments = self.prp_client.get_departments()
            department = next(
                (dept for dept in departments if dept['id'] == department_id), 
                None
            )
            
            if not department:
                raise PRPSyncError(
                    f"Department {department_id} not found in PRP",
                    department_id=department_id
                )
            
            dept_name = department.get('nameEng', f'Department {department_id}')
            logger.info(f"📋 Department: {dept_name} ({department_id})")
            
            # Get employees from PRP
            try:
                employees = self.prp_client.get_department_employees(department_id)
                logger.info(f"👥 Retrieved {len(employees)} employees from PRP")
            except PRPConnectionError as e:
                raise PRPSyncError(
                    f"Failed to retrieve employees from department {department_id}",
                    sync_operation="get_department_employees",
                    department_id=department_id
                ) from e
            
            # Process each employee
            result.departments_processed = 1
            
            with transaction.atomic():
                for employee_data in employees:
                    try:
                        self._sync_single_user(
                            employee_data=employee_data,
                            department=department,
                            result=result,
                            force=force
                        )
                    except Exception as e:
                        user_id = employee_data.get('userId', 'unknown')
                        error_msg = str(e)
                        logger.error(f"❌ Failed to sync user {user_id}: {error_msg}")
                        result.add_error_user(user_id, error_msg)
                        continue
            
            logger.info(f"✅ Department {dept_name} sync completed: {result}")
            
        except PRPException:
            # Re-raise PRP exceptions
            result.success = False
            raise
        except Exception as e:
            error_msg = f"Unexpected error syncing department {department_id}: {str(e)}"
            logger.error(f"💥 {error_msg}")
            result.success = False
            raise PRPSyncError(
                error_msg,
                sync_operation="sync_department_users",
                department_id=department_id
            ) from e
        
        return result.finalize()
    
    def sync_all_departments(
        self,
        force: bool = False,
        sync_options: Optional[Dict[str, Any]] = None
    ) -> PRPSyncResult:
        """
        Sync users from all PRP departments.
        
        Args:
            force: If True, ignore recent sync timestamps
            sync_options: Override default sync options
            
        Returns:
            PRPSyncResult: Comprehensive sync results
            
        Raises:
            PRPSyncError: If sync operation fails
        """
        result = PRPSyncResult()
        
        logger.info("🌐 Starting full PRP synchronization (all departments)")
        
        try:
            # Get all departments
            departments = self.prp_client.get_departments()
            logger.info(f"🏢 Found {len(departments)} departments in PRP")
            
            if not departments:
                result.add_warning("No departments found in PRP")
                return result.finalize()
            
            # Process each department
            for department in departments:
                dept_id = department['id']
                dept_name = department.get('nameEng', f'Department {dept_id}')
                
                try:
                    logger.info(f"🔄 Processing department: {dept_name} ({dept_id})")
                    
                    # Sync department users
                    dept_result = self.sync_department_users(
                        department_id=dept_id,
                        force=force,
                        sync_options=sync_options
                    )
                    
                    # Aggregate results
                    result.users_created += dept_result.users_created
                    result.users_updated += dept_result.users_updated
                    result.users_skipped += dept_result.users_skipped
                    result.users_errors += dept_result.users_errors
                    result.departments_processed += 1
                    result.errors.extend(dept_result.errors)
                    result.warnings.extend(dept_result.warnings)
                    
                    # Merge sync details
                    result.sync_details['processed_users'].extend(
                        dept_result.sync_details.get('processed_users', [])
                    )
                    
                except PRPException as e:
                    error_msg = f"Failed to sync department {dept_name}: {str(e)}"
                    logger.error(f"❌ {error_msg}")
                    result.errors.append(error_msg)
                    continue
            
            logger.info(f"✅ Full sync completed: {result}")
            
        except Exception as e:
            error_msg = f"Unexpected error during full sync: {str(e)}"
            logger.error(f"💥 {error_msg}")
            result.success = False
            raise PRPSyncError(
                error_msg,
                sync_operation="sync_all_departments"
            ) from e
        
        return result.finalize()
    
    def sync_single_user_by_id(
        self, 
        employee_id: str, 
        force: bool = False
    ) -> PRPSyncResult:
        """
        Sync a single user by PRP employee ID.
        
        Args:
            employee_id: PRP userId to sync
            force: If True, ignore recent sync timestamps
            
        Returns:
            PRPSyncResult: Single user sync results
            
        Raises:
            PRPSyncError: If user sync fails
        """
        result = PRPSyncResult()
        
        logger.info(f"👤 Starting single user sync for employee {employee_id}")
        
        try:
            # Lookup user in PRP
            employee_data = self.prp_client.lookup_user_by_employee_id(employee_id)
            
            if not employee_data:
                raise PRPSyncError(
                    f"Employee {employee_id} not found in PRP",
                    user_id=employee_id
                )
            
            # Get department info
            dept_id = employee_data.get('departmentId')
            if dept_id:
                departments = self.prp_client.get_departments()
                department = next(
                    (dept for dept in departments if dept['id'] == dept_id), 
                    None
                )
            else:
                department = None
            
            # Sync the user
            with transaction.atomic():
                self._sync_single_user(
                    employee_data=employee_data,
                    department=department,
                    result=result,
                    force=force
                )
            
            logger.info(f"✅ Single user sync completed: {result}")
            
        except PRPException:
            result.success = False
            raise
        except Exception as e:
            error_msg = f"Unexpected error syncing user {employee_id}: {str(e)}"
            logger.error(f"💥 {error_msg}")
            result.success = False
            raise PRPSyncError(
                error_msg,
                sync_operation="sync_single_user_by_id",
                user_id=employee_id
            ) from e
        
        return result.finalize()
    
    def _sync_single_user(
        self,
        employee_data: Dict[str, Any],
        department: Optional[Dict[str, Any]],
        result: PRPSyncResult,
        force: bool = False
    ) -> None:
        """
        Sync a single user with comprehensive business logic.
        
        Args:
            employee_data: PRP EmployeeDetails data
            department: PRP DepartmentModel data (optional)
            result: Sync result container to update
            force: If True, ignore recent sync checks
        """
        user_id = employee_data.get('userId')
        if not user_id:
            raise PRPDataValidationError(
                "Missing required userId field in employee data",
                field_name='userId'
            )
        
        logger.debug(f"🔄 Processing user: {user_id}")
        
        try:
            # Map PRP data to PIMS fields (CRITICAL BUSINESS LOGIC)
            mapped_data = self._map_prp_to_pims_fields(employee_data, department)
            
            # Check if user exists in PIMS
            try:
                existing_user = User.objects.get(employee_id=user_id)
                user_exists = True
                logger.debug(f"👤 Found existing user: {existing_user.username}")
            except User.DoesNotExist:
                existing_user = None
                user_exists = False
                logger.debug(f"👤 New user: {user_id}")
            
            # Apply business rules for updates
            if user_exists:
                should_update = self._should_update_user(
                    existing_user=existing_user,
                    mapped_data=mapped_data,
                    force=force
                )
                
                if not should_update:
                    result.add_skipped_user(
                        user_id, 
                        "Recent sync or no changes detected"
                    )
                    return
                
                # Update existing user
                updated_user = self._update_existing_user(existing_user, mapped_data)
                result.add_updated_user(
                    user_id, 
                    f"Updated fields: {list(mapped_data.keys())}"
                )
                
            else:
                # Create new user (following business rule: all users from PRP)
                new_user = self._create_new_user(mapped_data)
                result.add_created_user(
                    user_id,
                    f"Created with username: {new_user.username}"
                )
        
        except ValidationError as e:
            raise PRPDataValidationError(
                f"Data validation failed for user {user_id}: {str(e)}",
                field_name=getattr(e, 'field', None)
            )
        except IntegrityError as e:
            raise PRPSyncError(
                f"Database integrity error for user {user_id}: {str(e)}",
                user_id=user_id
            )
    
    def _map_prp_to_pims_fields(
        self,
        employee_data: Dict[str, Any],
        department: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Map PRP EmployeeDetails to PIMS CustomUser fields.
        
        Official Field Mapping (Per Integration Context):
        - userId → employee_id  
        - nameEng → first_name + last_name (split)
        - email → email
        - designationEng → designation
        - mobile → phone_number
        - photo (byte[]) → profile_image (converted)
        - status → is_active + is_active_employee
        
        Args:
            employee_data: PRP EmployeeDetails
            department: PRP DepartmentModel (optional)
            
        Returns:
            dict: Mapped data for PIMS CustomUser
            
        Raises:
            PRPDataValidationError: If required fields are missing
        """
        # Validate required fields
        required_fields = ['userId', 'nameEng']
        for field in required_fields:
            if not employee_data.get(field):
                raise PRPDataValidationError(
                    f"Required field '{field}' missing in PRP employee data",
                    field_name=field
                )
        
        # Start with mapped data
        mapped_data = {}
        
        # 1. Employee ID (userId → employee_id) - REQUIRED
        mapped_data['employee_id'] = str(employee_data['userId'])
        
        # 2. Name mapping (nameEng → first_name + last_name)
        full_name = str(employee_data['nameEng']).strip()
        name_parts = full_name.split(' ', 1)  # Split into max 2 parts
        mapped_data['first_name'] = name_parts[0] if name_parts else ''
        mapped_data['last_name'] = name_parts[1] if len(name_parts) > 1 else ''
        
        # 3. Email (email → email)
        email = employee_data.get('email', '').strip()
        if email:
            mapped_data['email'] = email
        
        # 4. Designation (designationEng → designation)
        designation = employee_data.get('designationEng', '').strip()
        if designation:
            mapped_data['designation'] = designation
        
        # 5. Phone (mobile → phone_number)
        mobile = employee_data.get('mobile', '').strip()
        if mobile:
            # Clean phone number format
            cleaned_mobile = self._clean_phone_number(mobile)
            if cleaned_mobile:
                mapped_data['phone_number'] = cleaned_mobile
        
        # 6. Office (department nameEng → office)
        if department and department.get('nameEng'):
            mapped_data['office'] = str(department['nameEng']).strip()
        
        # 7. Status (status → is_active + is_active_employee)
        prp_status = str(employee_data.get('status', 'unknown')).lower()
        is_active = prp_status == 'active'
        mapped_data['is_active'] = is_active
        mapped_data['is_active_employee'] = is_active
        
        # 8. Username generation (prp_{userId} format)
        mapped_data['username'] = f"prp_{employee_data['userId']}"
        
        # 9. PRP tracking fields
        mapped_data['is_prp_managed'] = True
        mapped_data['prp_last_sync'] = timezone.now()
        
        # 10. Photo processing (photo → profile_image)
        if self.sync_options.get('sync_photos', True):
            photo_data = employee_data.get('photo')
            if photo_data:
                try:
                    photo_file = self._convert_prp_photo_to_django_file(
                        photo_data, 
                        employee_data['userId']
                    )
                    if photo_file:
                        mapped_data['profile_image'] = photo_file
                except Exception as e:
                    logger.warning(f"⚠️  Failed to process photo for {employee_data['userId']}: {e}")
        
        logger.debug(f"📋 Mapped {len(mapped_data)} fields for user {employee_data['userId']}")
        return mapped_data
    
    def _clean_phone_number(self, phone: str) -> str:
        """
        Clean and format phone number for Bangladesh context.
        
        Args:
            phone: Raw phone number from PRP
            
        Returns:
            str: Cleaned phone number or empty string if invalid
        """
        if not phone:
            return ''
        
        # Remove all non-digit characters except +
        cleaned = ''.join(c for c in phone if c.isdigit() or c == '+')
        
        # Handle Bangladesh phone format
        if cleaned.startswith('+880'):
            return cleaned[:14]  # +880 + 10 digits max
        elif cleaned.startswith('880'):
            return f"+{cleaned[:13]}"  # Add + prefix
        elif cleaned.startswith('01') and len(cleaned) == 11:
            return f"+880{cleaned[1:]}"  # Convert 01XXXXXXXX to +8801XXXXXXXX
        elif len(cleaned) >= 10:
            return cleaned[:15]  # General international format
        
        return cleaned if len(cleaned) >= 9 else ''
    
    def _convert_prp_photo_to_django_file(
        self, 
        photo_data: Union[bytes, str, Any], 
        user_id: str
    ) -> Optional[ContentFile]:
        """
        Convert PRP photo data to Django ContentFile.
        
        Args:
            photo_data: Photo data from PRP (byte array or base64)
            user_id: User ID for filename generation
            
        Returns:
            ContentFile: Django file object or None if conversion fails
        """
        try:
            # Handle different photo data formats
            if isinstance(photo_data, str):
                # Assume base64 encoded string
                try:
                    photo_bytes = base64.b64decode(photo_data)
                except Exception:
                    logger.warning(f"⚠️  Invalid base64 photo data for user {user_id}")
                    return None
            elif isinstance(photo_data, (bytes, bytearray)):
                photo_bytes = bytes(photo_data)
            else:
                logger.warning(f"⚠️  Unsupported photo data type for user {user_id}: {type(photo_data)}")
                return None
            
            # Check file size
            if len(photo_bytes) > self.sync_options.get('max_photo_size', 5 * 1024 * 1024):
                logger.warning(f"⚠️  Photo too large for user {user_id}: {len(photo_bytes)} bytes")
                return None
            
            # Validate image format
            try:
                image = Image.open(io.BytesIO(photo_bytes))
                image.verify()  # Verify it's a valid image
                
                # Reset BytesIO after verify()
                image_io = io.BytesIO(photo_bytes)
                image = Image.open(image_io)
                
                # Convert to RGB if necessary (for JPEG compatibility)
                if image.mode in ('RGBA', 'LA', 'P'):
                    image = image.convert('RGB')
                
                # Resize if too large (max 800x800)
                if image.size[0] > 800 or image.size[1] > 800:
                    image.thumbnail((800, 800), Image.Resampling.LANCZOS)
                
                # Save to bytes
                output_io = io.BytesIO()
                image.save(output_io, format='JPEG', quality=85, optimize=True)
                photo_bytes = output_io.getvalue()
                
            except Exception as e:
                logger.warning(f"⚠️  Invalid image data for user {user_id}: {e}")
                return None
            
            # Create Django ContentFile
            filename = f"prp_user_{user_id}_{int(timezone.now().timestamp())}.jpg"
            content_file = ContentFile(photo_bytes, name=filename)
            
            logger.debug(f"📸 Converted photo for user {user_id}: {len(photo_bytes)} bytes")
            return content_file
            
        except Exception as e:
            logger.error(f"❌ Photo conversion failed for user {user_id}: {e}")
            return None
    
    def _should_update_user(
        self,
        existing_user: User,
        mapped_data: Dict[str, Any],
        force: bool = False
    ) -> bool:
        """
        Determine if user should be updated based on business rules.
        
        Critical Business Rule Implementation:
        - If PIMS admin made user inactive but PRP user is active,
          user remains inactive (admin override takes precedence)
        
        Args:
            existing_user: Existing PIMS user
            mapped_data: New data from PRP mapping
            force: If True, ignore timestamp and recent sync checks
            
        Returns:
            bool: True if user should be updated
        """
        # Force update if requested
        if force:
            logger.debug(f"🔧 Force update for user {existing_user.employee_id}")
            return True
        
        # Skip if user was recently synced (within 1 hour)
        if (self.sync_options.get('skip_recent_sync', True) and 
            existing_user.prp_last_sync):
            
            time_since_sync = timezone.now() - existing_user.prp_last_sync
            if time_since_sync < timedelta(hours=1):
                logger.debug(f"⏭️  Skipping recent sync for user {existing_user.employee_id}")
                return False
        
        # CRITICAL BUSINESS RULE: Admin Status Override
        # If PIMS admin made user inactive but PRP shows active, preserve admin override
        if (self.sync_options.get('respect_admin_overrides', True) and
            not existing_user.is_active and 
            mapped_data.get('is_active', True) and
            existing_user.is_prp_managed):
            
            logger.info(
                f"🛡️  Preserving admin override for user {existing_user.employee_id}: "
                "User inactive in PIMS but active in PRP - admin override takes precedence"
            )
            
            # Remove status fields from mapped_data to preserve admin setting
            mapped_data.pop('is_active', None)
            mapped_data.pop('is_active_employee', None)
            
            # Record business rule application
            return True  # Still update other fields
        
        # Check if any fields actually changed
        has_changes = False
        for field, new_value in mapped_data.items():
            if field in ['prp_last_sync']:  # Always update sync timestamp
                has_changes = True
                continue
                
            current_value = getattr(existing_user, field, None)
            
            # Handle special field comparisons
            if field == 'profile_image':
                # Always update photos if provided (they're ContentFile objects)
                if new_value:
                    has_changes = True
            elif current_value != new_value:
                has_changes = True
                logger.debug(f"🔄 Field change for {existing_user.employee_id}.{field}: {current_value} → {new_value}")
        
        return has_changes
    
    def _create_new_user(self, mapped_data: Dict[str, Any]) -> User:
        """
        Create new PIMS user from PRP data following business rules.
        
        Business Rules Applied:
        - Default password: "12345678" (as specified)
        - Username format: prp_{userId}
        - All users marked as PRP-managed
        
        Args:
            mapped_data: Mapped user data from PRP
            
        Returns:
            User: Created User instance
            
        Raises:
            PRPSyncError: If user creation fails
        """
        try:
            # Remove fields that can't be set directly
            profile_image = mapped_data.pop('profile_image', None)
            
            # Create user with mapped data
            user = User(**mapped_data)
            
            # Set default password (business rule)
            user.set_password(self.sync_options['default_password'])
            
            # Save user first
            user.save()
            
            # Handle profile image separately if provided
            if profile_image:
                try:
                    user.profile_image.save(
                        profile_image.name,
                        profile_image,
                        save=True
                    )
                    logger.debug(f"📸 Saved profile image for new user {user.employee_id}")
                except Exception as e:
                    logger.warning(f"⚠️  Failed to save profile image for new user {user.employee_id}: {e}")
            
            logger.info(
                f"✅ Created new PRP user: {user.username} "
                f"(Employee ID: {user.employee_id}, Name: {user.get_full_name()})",
                extra={
                    'employee_id': user.employee_id, 
                    'username': user.username,
                    'location': self.location
                }
            )
            
            return user
            
        except IntegrityError as e:
            raise PRPSyncError(
                f"Failed to create user {mapped_data.get('employee_id')}: Integrity constraint violation",
                user_id=mapped_data.get('employee_id'),
                sync_operation="create_user"
            ) from e
        except Exception as e:
            raise PRPSyncError(
                f"Failed to create user {mapped_data.get('employee_id')}: {str(e)}",
                user_id=mapped_data.get('employee_id'),
                sync_operation="create_user"
            ) from e
    
    def _update_existing_user(self, user: User, mapped_data: Dict[str, Any]) -> User:
        """
        Update existing PIMS user with PRP data following business rules.
        
        Business Rules Applied:
        - Preserve username (never change)
        - Update prp_last_sync timestamp
        - Handle profile image updates carefully
        
        Args:
            user: Existing user instance
            mapped_data: New data from PRP mapping
            
        Returns:
            User: Updated User instance
            
        Raises:
            PRPSyncError: If user update fails
        """
        try:
            # Remove profile image for separate handling
            profile_image = mapped_data.pop('profile_image', None)
            
            # Update user fields (except username - never change username)
            updated_fields = []
            for field, value in mapped_data.items():
                if field != 'username':  # Preserve username
                    old_value = getattr(user, field, None)
                    setattr(user, field, value)
                    if old_value != value:
                        updated_fields.append(field)
            
            # Save user updates
            user.save()
            
            # Handle profile image update separately
            if profile_image:
                try:
                    # Delete old image if exists
                    if user.profile_image:
                        try:
                            user.profile_image.delete(save=False)
                        except Exception:
                            pass  # Ignore deletion errors
                    
                    # Save new image
                    user.profile_image.save(
                        profile_image.name,
                        profile_image,
                        save=True
                    )
                    updated_fields.append('profile_image')
                    logger.debug(f"📸 Updated profile image for user {user.employee_id}")
                except Exception as e:
                    logger.warning(f"⚠️  Failed to update profile image for user {user.employee_id}: {e}")
            
            logger.info(
                f"✅ Updated PRP user: {user.username} "
                f"(Employee ID: {user.employee_id}, Fields: {updated_fields})",
                extra={
                    'employee_id': user.employee_id,
                    'username': user.username,
                    'updated_fields': updated_fields,
                    'location': self.location
                }
            )
            
            return user
            
        except Exception as e:
            raise PRPSyncError(
                f"Failed to update user {user.employee_id}: {str(e)}",
                user_id=user.employee_id,
                sync_operation="update_user"
            ) from e
    
    def get_sync_status(self, employee_id: str) -> Dict[str, Any]:
        """
        Get comprehensive synchronization status for a specific user.
        
        Args:
            employee_id: PRP userId to check
            
        Returns:
            dict: Detailed sync status information
        """
        try:
            # Check if user exists in PIMS
            try:
                pims_user = User.objects.get(employee_id=employee_id)
                pims_exists = True
                pims_data = {
                    'username': pims_user.username,
                    'full_name': pims_user.get_full_name(),
                    'email': pims_user.email,
                    'is_active': pims_user.is_active,
                    'is_prp_managed': pims_user.is_prp_managed,
                    'prp_last_sync': pims_user.prp_last_sync.isoformat() if pims_user.prp_last_sync else None,
                    'last_login': pims_user.last_login.isoformat() if pims_user.last_login else None
                }
            except User.DoesNotExist:
                pims_exists = False
                pims_data = None
            
            # Check if user exists in PRP
            try:
                prp_data = self.prp_client.lookup_user_by_employee_id(employee_id)
                prp_exists = prp_data is not None
            except Exception as e:
                prp_exists = False
                prp_data = None
                logger.warning(f"⚠️  Failed to lookup user {employee_id} in PRP: {e}")
            
            # Determine sync status
            if pims_exists and prp_exists:
                sync_status = "IN_SYNC"
                sync_needed = False
                
                # Check if sync is needed based on last sync time
                if pims_user.prp_last_sync:
                    time_since_sync = timezone.now() - pims_user.prp_last_sync
                    if time_since_sync > timedelta(hours=24):
                        sync_needed = True
                        sync_status = "SYNC_RECOMMENDED"
                else:
                    sync_needed = True
                    sync_status = "NEVER_SYNCED"
                    
            elif not pims_exists and prp_exists:
                sync_status = "PRP_ONLY"
                sync_needed = True
            elif pims_exists and not prp_exists:
                sync_status = "PIMS_ONLY"
                sync_needed = False
            else:
                sync_status = "NOT_FOUND"
                sync_needed = False
            
            return {
                'employee_id': employee_id,
                'sync_status': sync_status,
                'sync_needed': sync_needed,
                'pims_exists': pims_exists,
                'prp_exists': prp_exists,
                'pims_data': pims_data,
                'prp_data': prp_data,
                'location': self.location,
                'check_timestamp': timezone.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to get sync status for {employee_id}: {e}")
            return {
                'employee_id': employee_id,
                'sync_status': "ERROR",
                'sync_needed': False,
                'error': str(e),
                'check_timestamp': timezone.now().isoformat()
            }
    
    def get_prp_departments(self) -> List[Dict[str, Any]]:
        """
        Get list of all PRP departments with sync statistics.
        
        Returns:
            list: Department information with user counts
        """
        try:
            departments = self.prp_client.get_departments()
            
            # Enhance departments with PIMS sync statistics
            for department in departments:
                dept_id = department['id']
                
                # Count PIMS users from this department
                pims_users_count = User.objects.filter(
                    office=department.get('nameEng', ''),
                    is_prp_managed=True
                ).count()
                
                # Add statistics
                department['pims_users_count'] = pims_users_count
                department['sync_status'] = 'synced' if pims_users_count > 0 else 'not_synced'
            
            return departments
            
        except Exception as e:
            logger.error(f"❌ Failed to get PRP departments: {e}")
            raise PRPSyncError(
                f"Failed to retrieve PRP departments: {str(e)}",
                sync_operation="get_prp_departments"
            ) from e
    
    def validate_sync_prerequisites(self) -> Dict[str, Any]:
        """
        Validate all prerequisites for PRP synchronization.
        
        Returns:
            dict: Validation results with recommendations
        """
        validation_result = {
            'valid': True,
            'warnings': [],
            'errors': [],
            'recommendations': [],
            'location': self.location,
            'timestamp': timezone.now().isoformat()
        }
        
        try:
            # Test PRP API connection
            logger.info("🔍 Validating PRP synchronization prerequisites...")
            
            connection_test = self.prp_client.test_connection()
            if not connection_test.get('success'):
                validation_result['valid'] = False
                validation_result['errors'].append(
                    f"PRP API connection failed: {connection_test.get('message')}"
                )
            
            # Test authentication
            try:
                if not self.prp_client.authenticate():
                    validation_result['valid'] = False
                    validation_result['errors'].append("PRP authentication failed")
            except Exception as e:
                validation_result['valid'] = False
                validation_result['errors'].append(f"PRP authentication error: {str(e)}")
            
            # Test data retrieval
            try:
                departments = self.prp_client.get_departments()
                if not departments:
                    validation_result['warnings'].append("No departments found in PRP")
                else:
                    validation_result['recommendations'].append(
                        f"Found {len(departments)} departments ready for sync"
                    )
            except Exception as e:
                validation_result['errors'].append(f"Failed to retrieve departments: {str(e)}")
            
            # Check PIMS database
            try:
                pims_user_count = User.objects.filter(is_prp_managed=True).count()
                validation_result['recommendations'].append(
                    f"Found {pims_user_count} existing PRP-managed users in PIMS"
                )
            except Exception as e:
                validation_result['errors'].append(f"PIMS database error: {str(e)}")
            
            # Check sync options
            if not self.sync_options.get('default_password'):
                validation_result['warnings'].append("No default password set for new users")
            
            if validation_result['errors']:
                validation_result['valid'] = False
            
            logger.info(f"✅ Sync prerequisites validation completed: Valid={validation_result['valid']}")
            
        except Exception as e:
            validation_result['valid'] = False
            validation_result['errors'].append(f"Validation error: {str(e)}")
            logger.error(f"❌ Sync prerequisites validation failed: {e}")
        
        return validation_result


# Utility functions for external use

def create_sync_service(prp_client: Optional[PRPClient] = None) -> PRPSyncService:
    """
    Factory function to create PRP sync service with default configuration.
    
    Args:
        prp_client: Optional PRP client instance (creates new one if None)
        
    Returns:
        PRPSyncService: Configured sync service instance
    """
    if prp_client is None:
        from .prp_client import create_prp_client
        prp_client = create_prp_client()
    
    return PRPSyncService(prp_client)


def get_sync_statistics() -> Dict[str, Any]:
    """
    Get overall PRP synchronization statistics for PIMS.
    
    Returns:
        dict: Comprehensive sync statistics
    """
    try:
        # Count PRP-managed users
        total_prp_users = User.objects.filter(is_prp_managed=True).count()
        active_prp_users = User.objects.filter(is_prp_managed=True, is_active=True).count()
        inactive_prp_users = total_prp_users - active_prp_users
        
        # Count users synced in last 24 hours
        yesterday = timezone.now() - timedelta(hours=24)
        recently_synced = User.objects.filter(
            is_prp_managed=True,
            prp_last_sync__gte=yesterday
        ).count()
        
        # Count users never synced
        never_synced = User.objects.filter(
            is_prp_managed=True,
            prp_last_sync__isnull=True
        ).count()
        
        # Count users with photos
        users_with_photos = User.objects.filter(
            is_prp_managed=True,
            profile_image__isnull=False
        ).exclude(profile_image='').count()
        
        return {
            'total_prp_users': total_prp_users,
            'active_prp_users': active_prp_users,
            'inactive_prp_users': inactive_prp_users,
            'recently_synced_users': recently_synced,
            'never_synced_users': never_synced,
            'users_with_photos': users_with_photos,
            'photo_sync_percentage': (
                (users_with_photos / total_prp_users * 100) 
                if total_prp_users > 0 else 0
            ),
            'location': 'Bangladesh Parliament Secretariat, Dhaka',
            'timestamp': timezone.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Failed to get sync statistics: {e}")
        return {
            'error': str(e),
            'timestamp': timezone.now().isoformat()
        }


# Export main classes and functions
__all__ = [
    'PRPSyncService',
    'PRPSyncResult',
    'create_sync_service',
    'get_sync_statistics'
]