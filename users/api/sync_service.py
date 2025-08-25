"""
PRP Synchronization Service
===========================

Business logic service for PRP (Parliament Resource Portal) user synchronization
in PIMS at Bangladesh Parliament Secretariat, Dhaka.

Location: Bangladesh Parliament Secretariat, Dhaka, Bangladesh
Project: PIMS-PRP Integration  
Purpose: Core business logic for syncing PRP user data to PIMS

Key Classes:
- PRPSyncService: Main service for user synchronization
- PRPSyncResult: Result container for sync operations

Business Rules Implementation:
- One-way sync: PRP → PIMS (PRP is authoritative)
- Status override: PIMS admin inactive status takes precedence  
- Field mapping: Reuse existing CustomUser fields for PRP data
- No user creation from PIMS: All users originate from PRP

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

from __future__ import annotations
from typing import TYPE_CHECKING

import io
import logging
import base64
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from PIL import Image
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.db import transaction
from django.utils import timezone
from django.conf import settings

if TYPE_CHECKING:
    from django.contrib.auth.models import AbstractUser

from .prp_client import PRPClient
from .exceptions import (
    PRPSyncError,
    PRPDataValidationError,
    PRPConnectionError,
    PRPAuthenticationError
)

# Configure logging
logger = logging.getLogger('pims.prp_integration.sync_service')

User = get_user_model()


class PRPSyncResult:
    """
    Container for PRP synchronization operation results.
    
    Tracks statistics and outcomes for sync operations including
    user creation, updates, errors, and departmental processing.
    """
    
    def __init__(self):
        """Initialize empty sync result."""
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
        self.sync_details: Dict[str, Any] = {}
    
    def add_created_user(self, user_id: str, details: Optional[str] = None):
        """Record a user creation."""
        self.users_created += 1
        if details:
            self.sync_details[f'created_{user_id}'] = details
    
    def add_updated_user(self, user_id: str, details: Optional[str] = None):
        """Record a user update."""
        self.users_updated += 1
        if details:
            self.sync_details[f'updated_{user_id}'] = details
    
    def add_skipped_user(self, user_id: str, reason: str):
        """Record a skipped user."""
        self.users_skipped += 1
        self.sync_details[f'skipped_{user_id}'] = reason
    
    def add_error(self, error: str, user_id: Optional[str] = None):
        """Record an error."""
        self.users_errors += 1
        self.errors.append(error)
        self.success = False
        if user_id:
            self.sync_details[f'error_{user_id}'] = error
    
    def add_warning(self, warning: str):
        """Record a warning."""
        self.warnings.append(warning)
    
    def add_department_result(self, dept_result: PRPSyncResult):
        """Add results from a department sync operation."""
        self.users_created += dept_result.users_created
        self.users_updated += dept_result.users_updated
        self.users_skipped += dept_result.users_skipped
        self.users_errors += dept_result.users_errors
        self.departments_processed += 1
        self.errors.extend(dept_result.errors)
        self.warnings.extend(dept_result.warnings)
        self.sync_details.update(dept_result.sync_details)
        if not dept_result.success:
            self.success = False
    
    def finalize(self):
        """Finalize the sync result."""
        self.end_time = timezone.now()
    
    def get_duration(self) -> timedelta:
        """Get sync operation duration."""
        end = self.end_time or timezone.now()
        return end - self.start_time
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary."""
        return {
            'users_created': self.users_created,
            'users_updated': self.users_updated,
            'users_skipped': self.users_skipped,
            'users_errors': self.users_errors,
            'departments_processed': self.departments_processed,
            'errors': self.errors,
            'warnings': self.warnings,
            'success': self.success,
            'duration_seconds': self.get_duration().total_seconds(),
            'sync_details': self.sync_details
        }


class PRPSyncService:
    """
    Service for synchronizing user data from PRP API to PIMS.
    
    Handles all business logic for user synchronization including:
    - Data mapping from PRP format to PIMS CustomUser model
    - Business rule enforcement (status override, read-only fields)
    - Error handling and validation
    - Transaction management for data integrity
    
    Location: Bangladesh Parliament Secretariat, Dhaka, Bangladesh
    """
    
    def __init__(self, prp_client: PRPClient):
        """
        Initialize sync service with PRP client.
        
        Args:
            prp_client: Configured PRP API client
        """
        self.prp_client = prp_client
        self.location = "Bangladesh Parliament Secretariat, Dhaka"
        
        logger.info(
            "PRPSyncService initialized",
            extra={'location': self.location}
        )
    
    def get_prp_departments(self) -> List[Dict[str, Any]]:
        """
        Get all departments from PRP API.
        
        Returns:
            List of department dictionaries with structure:
            {id: int, nameEng: str, nameBng: str, isWing: bool}
            
        Raises:
            PRPConnectionError: If API connection fails
            PRPDataValidationError: If department data is invalid
        """
        try:
            departments = self.prp_client.get_departments()
            
            # Validate department data structure
            for dept in departments:
                if not isinstance(dept, dict) or 'id' not in dept or 'nameEng' not in dept:
                    raise PRPDataValidationError(
                        f"Invalid department data structure: {dept}"
                    )
            
            logger.info(
                f"Retrieved {len(departments)} departments from PRP",
                extra={'department_count': len(departments), 'location': self.location}
            )
            
            return departments
            
        except Exception as e:
            logger.error(f"Failed to get PRP departments: {e}")
            if isinstance(e, (PRPConnectionError, PRPDataValidationError)):
                raise
            raise PRPSyncError(f"Failed to retrieve departments: {str(e)}")
    
    def sync_department_users(
        self, 
        department_id: int,
        dry_run: bool = False,
        force: bool = False,
        limit: Optional[int] = None,
        skip_inactive: bool = False
    ) -> PRPSyncResult:
        """
        Sync all users from a specific PRP department.
        
        Args:
            department_id: PRP department ID
            dry_run: If True, preview changes without applying
            force: If True, ignore timestamp checks
            limit: Maximum number of users to process
            skip_inactive: If True, skip inactive users
            
        Returns:
            PRPSyncResult with operation statistics
        """
        result = PRPSyncResult()
        
        try:
            logger.info(
                f"Starting department user sync for department {department_id}",
                extra={
                    'department_id': department_id,
                    'dry_run': dry_run,
                    'force': force,
                    'location': self.location
                }
            )
            
            # Get employee details from PRP
            employees = self.prp_client.get_employee_details(department_id)
            
            if not employees:
                result.add_warning(f"No employees found in department {department_id}")
                result.finalize()
                return result
            
            # Get department info for office field mapping
            departments = self.get_prp_departments()
            department_info = next(
                (dept for dept in departments if dept['id'] == department_id), 
                None
            )
            
            if not department_info:
                result.add_error(f"Department {department_id} not found in PRP")
                result.finalize()
                return result
            
            # Process employees with limit if specified
            employees_to_process = employees[:limit] if limit else employees
            
            with transaction.atomic():
                savepoint = transaction.savepoint() if not dry_run else None
                
                try:
                    for employee in employees_to_process:
                        # Skip inactive users if requested
                        if skip_inactive and not employee.get('status', True):
                            result.add_skipped_user(
                                employee.get('userId', 'unknown'),
                                'User is inactive in PRP'
                            )
                            continue
                        
                        # Sync individual user
                        user_result = self._sync_single_user(
                            employee, 
                            department_info, 
                            dry_run=dry_run,
                            force=force
                        )
                        
                        # Add to overall result
                        if user_result['action'] == 'created':
                            result.add_created_user(
                                user_result['user_id'], 
                                user_result.get('details')
                            )
                        elif user_result['action'] == 'updated':
                            result.add_updated_user(
                                user_result['user_id'], 
                                user_result.get('details')
                            )
                        elif user_result['action'] == 'skipped':
                            result.add_skipped_user(
                                user_result['user_id'], 
                                user_result.get('reason', 'Unknown')
                            )
                        elif user_result['action'] == 'error':
                            result.add_error(
                                user_result.get('error', 'Unknown error'),
                                user_result['user_id']
                            )
                    
                    if not dry_run and savepoint:
                        transaction.savepoint_commit(savepoint)
                        
                except Exception as e:
                    if not dry_run and savepoint:
                        transaction.savepoint_rollback(savepoint)
                    raise e
            
            result.departments_processed = 1
            result.finalize()
            
            logger.info(
                f"Department {department_id} sync completed",
                extra={
                    'department_id': department_id,
                    'users_created': result.users_created,
                    'users_updated': result.users_updated,
                    'errors': result.users_errors,
                    'location': self.location
                }
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Department {department_id} sync failed: {e}")
            result.add_error(f"Department sync failed: {str(e)}")
            result.finalize()
            return result
    
    def sync_all_departments(
        self,
        dry_run: bool = False,
        force: bool = False,
        limit: Optional[int] = None,
        skip_inactive: bool = False
    ) -> PRPSyncResult:
        """
        Sync users from all PRP departments.
        
        Args:
            dry_run: If True, preview changes without applying
            force: If True, ignore timestamp checks  
            limit: Maximum number of users per department
            skip_inactive: If True, skip inactive users
            
        Returns:
            PRPSyncResult with aggregated statistics
        """
        result = PRPSyncResult()
        
        try:
            logger.info(
                "Starting full sync of all PRP departments",
                extra={'location': self.location}
            )
            
            # Get all departments
            departments = self.get_prp_departments()
            
            if not departments:
                result.add_error("No departments found in PRP")
                result.finalize()
                return result
            
            # Process each department
            for department in departments:
                dept_id = department['id']
                dept_name = department.get('nameEng', f'Department {dept_id}')
                
                logger.info(f"Processing department: {dept_name}")
                
                # Sync department users
                dept_result = self.sync_department_users(
                    department_id=dept_id,
                    dry_run=dry_run,
                    force=force,
                    limit=limit,
                    skip_inactive=skip_inactive
                )
                
                # Add department result to overall result
                result.add_department_result(dept_result)
            
            result.finalize()
            
            logger.info(
                f"Full sync completed: {result.departments_processed} departments processed",
                extra={
                    'departments_processed': result.departments_processed,
                    'users_created': result.users_created,
                    'users_updated': result.users_updated,
                    'errors': result.users_errors,
                    'location': self.location
                }
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Full sync failed: {e}")
            result.add_error(f"Full sync failed: {str(e)}")
            result.finalize()
            return result
    
    def _sync_single_user(
        self,
        employee_data: Dict[str, Any],
        department_info: Dict[str, Any],
        dry_run: bool = False,
        force: bool = False
    ) -> Dict[str, Any]:
        """
        Sync a single user from PRP data.
        
        Args:
            employee_data: PRP employee data
            department_info: PRP department information
            dry_run: If True, preview changes without applying
            force: If True, ignore timestamp checks
            
        Returns:
            Dictionary with sync result details
        """
        user_id = employee_data.get('userId')
        
        if not user_id:
            return {
                'action': 'error',
                'user_id': 'unknown',
                'error': 'Missing userId in employee data'
            }
        
        try:
            # Map PRP data to PIMS fields
            mapped_data = self._map_prp_to_pims_data(employee_data, department_info)
            
            # Check if user already exists
            try:
                existing_user = User.objects.get(employee_id=user_id)
                
                # Apply business rules for updates
                if self._should_update_user(existing_user, mapped_data, force):
                    if not dry_run:
                        updated_user = self._update_existing_user(existing_user, mapped_data)
                        return {
                            'action': 'updated',
                            'user_id': user_id,
                            'details': f'Updated user {updated_user.username}'
                        }
                    else:
                        return {
                            'action': 'updated',
                            'user_id': user_id,
                            'details': 'Would update user (dry run)'
                        }
                else:
                    return {
                        'action': 'skipped',
                        'user_id': user_id,
                        'reason': 'No updates needed or admin override active'
                    }
                    
            except User.DoesNotExist:
                # Create new user
                if not dry_run:
                    new_user = self._create_new_user(mapped_data)
                    return {
                        'action': 'created',
                        'user_id': user_id,
                        'details': f'Created user {new_user.username}'
                    }
                else:
                    return {
                        'action': 'created',
                        'user_id': user_id,
                        'details': 'Would create new user (dry run)'
                    }
            
        except Exception as e:
            logger.error(f"Failed to sync user {user_id}: {e}")
            return {
                'action': 'error',
                'user_id': user_id,
                'error': str(e)
            }
    
    def _map_prp_to_pims_data(
        self, 
        employee_data: Dict[str, Any], 
        department_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Map PRP employee data to PIMS CustomUser fields.
        
        Args:
            employee_data: PRP employee data
            department_info: PRP department information
            
        Returns:
            Mapped data for PIMS CustomUser model
        """
        user_id = employee_data.get('userId', '')
        name_eng = employee_data.get('nameEng', '')
        
        # Split name into first and last name
        name_parts = name_eng.strip().split(' ', 1)
        first_name = name_parts[0] if name_parts else ''
        last_name = name_parts[1] if len(name_parts) > 1 else ''
        
        # Generate Django username
        username = f"prp_{user_id}"
        
        mapped_data = {
            'username': username,
            'employee_id': user_id,
            'first_name': first_name,
            'last_name': last_name,
            'email': employee_data.get('email', ''),
            'designation': employee_data.get('designationEng', ''),
            'office': department_info.get('nameEng', ''),
            'phone_number': employee_data.get('mobile', ''),
            'is_active': employee_data.get('status', True),
            'is_active_employee': employee_data.get('status', True),
            'is_prp_managed': True,
            'prp_last_sync': timezone.now()
        }
        
        # Handle profile image if present
        if employee_data.get('photo'):
            try:
                profile_image = self._process_prp_photo(
                    employee_data['photo'], 
                    user_id
                )
                if profile_image:
                    mapped_data['profile_image'] = profile_image
            except Exception as e:
                logger.warning(f"Failed to process photo for user {user_id}: {e}")
        
        return mapped_data
    
    def _process_prp_photo(self, photo_data: Any, user_id: str) -> Optional[ContentFile]:
        """
        Process PRP photo data to Django ImageField format.
        
        Args:
            photo_data: Photo data from PRP (base64 or bytes)
            user_id: User ID for filename
            
        Returns:
            ContentFile for Django ImageField or None if processing fails
        """
        try:
            # Handle different photo data formats
            if isinstance(photo_data, str):
                # Base64 encoded image
                image_data = base64.b64decode(photo_data)
            elif isinstance(photo_data, bytes):
                # Raw bytes
                image_data = photo_data
            else:
                logger.warning(f"Unsupported photo data type for user {user_id}")
                return None
            
            # Validate and resize image
            image = Image.open(io.BytesIO(image_data))
            
            # Convert to RGB if needed
            if image.mode in ('RGBA', 'LA', 'P'):
                image = image.convert('RGB')
            
            # Resize if too large (max 300x300)
            if image.size[0] > 300 or image.size[1] > 300:
                image.thumbnail((300, 300), Image.LANCZOS)
            
            # Save as JPEG
            output = io.BytesIO()
            image.save(output, format='JPEG', quality=85)
            output.seek(0)
            
            # Create ContentFile
            filename = f"prp_user_{user_id}.jpg"
            return ContentFile(output.getvalue(), filename)
            
        except Exception as e:
            logger.error(f"Error processing photo for user {user_id}: {e}")
            return None
    
    def _should_update_user(
        self, 
        existing_user: AbstractUser, 
        mapped_data: Dict[str, Any], 
        force: bool = False
    ) -> bool:
        """
        Determine if user should be updated based on business rules.
        
        Business Rule: If PIMS admin made user inactive but PRP user is active,
        user remains inactive (admin override).
        
        Args:
            existing_user: Existing PIMS user
            mapped_data: New data from PRP
            force: If True, ignore timestamp checks
            
        Returns:
            True if user should be updated
        """
        # Force update if requested
        if force:
            return True
        
        # Check if user was recently synced (within 1 hour)
        if existing_user.prp_last_sync:
            time_diff = timezone.now() - existing_user.prp_last_sync
            if time_diff < timedelta(hours=1):
                return False
        
        # Apply status business rule
        # If admin made user inactive but PRP shows active, keep inactive
        if (not existing_user.is_active and 
            mapped_data.get('is_active', True) and
            existing_user.is_prp_managed):
            
            logger.info(
                f"Preserving admin override for user {existing_user.employee_id}: "
                "User inactive in PIMS but active in PRP"
            )
            # Remove is_active from mapped_data to preserve admin setting
            mapped_data.pop('is_active', None)
            mapped_data.pop('is_active_employee', None)
        
        return True
    
    def _create_new_user(self, mapped_data: Dict[str, Any]) -> AbstractUser:
        """
        Create new PIMS user from PRP data.
        
        Args:
            mapped_data: Mapped user data
            
        Returns:
            Created User instance
        """
        # Set default password for PRP users
        user = User(**mapped_data)
        user.set_password('12345678')  # Default password as specified
        user.save()
        
        logger.info(
            f"Created new PRP user: {user.username} (Employee ID: {user.employee_id})",
            extra={'employee_id': user.employee_id, 'location': self.location}
        )
        
        return user
    
    def _update_existing_user(self, user: AbstractUser, mapped_data: Dict[str, Any]) -> AbstractUser:
        """
        Update existing PIMS user with PRP data.
        
        Args:
            user: Existing user instance
            mapped_data: New data from PRP
            
        Returns:
            Updated User instance
        """
        # Update fields
        for field, value in mapped_data.items():
            if field != 'username':  # Don't change username
                setattr(user, field, value)
        
        user.save()
        
        logger.info(
            f"Updated PRP user: {user.username} (Employee ID: {user.employee_id})",
            extra={'employee_id': user.employee_id, 'location': self.location}
        )
        
        return user
    
    def get_sync_status(self, employee_id: str) -> Dict[str, Any]:
        """
        Get synchronization status for a specific user.
        
        Args:
            employee_id: PRP employee ID
            
        Returns:
            Dictionary with sync status information
        """
        try:
            user = User.objects.get(employee_id=employee_id)
            
            return {
                'exists': True,
                'is_prp_managed': getattr(user, 'is_prp_managed', False),
                'last_sync': getattr(user, 'prp_last_sync', None),
                'username': user.username,
                'is_active': user.is_active,
                'sync_age_hours': (
                    (timezone.now() - user.prp_last_sync).total_seconds() / 3600
                    if user.prp_last_sync else None
                )
            }
            
        except User.DoesNotExist:
            return {
                'exists': False,
                'is_prp_managed': False,
                'last_sync': None,
                'username': None,
                'is_active': None,
                'sync_age_hours': None
            }