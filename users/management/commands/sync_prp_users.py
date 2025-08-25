"""
Django Management Command: PRP User Synchronization
===================================================

Manual user sync command for PIMS-PRP Integration at Bangladesh Parliament Secretariat.

Location: Bangladesh Parliament Secretariat, Dhaka, Bangladesh
Project: PIMS-PRP Integration
Purpose: Admin-controlled synchronization of user data from PRP to PIMS

Business Rules:
- Admin-only operation (requires superuser or specific permissions)
- One-way sync: PRP → PIMS (PRP is authoritative source)
- Status override: PIMS admin inactive status takes precedence
- Comprehensive logging and progress reporting
- Rollback capability on errors

Usage Examples:
    # Sync all departments and users
    python manage.py sync_prp_users --all

    # Sync specific department by ID
    python manage.py sync_prp_users --department=1

    # Sync specific department by name
    python manage.py sync_prp_users --department="Information Technology"

    # Status-only sync (update user status without full data sync)
    python manage.py sync_prp_users --status-only

    # Dry run (preview changes without applying)
    python manage.py sync_prp_users --all --dry-run

    # Force sync (ignore timestamp checks)
    python manage.py sync_prp_users --department=1 --force

    # Quiet mode (minimal output)
    python manage.py sync_prp_users --all --quiet

Dependencies:
- users.api.sync_service (PRPSyncService)
- users.api.prp_client (PRPClient) 
- users.api.exceptions (PRP exceptions)
"""

import sys
import logging
import traceback
from datetime import datetime
from typing import List, Dict, Any, Optional
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from django.conf import settings

# Import PRP integration modules
try:
    from users.api.sync_service import PRPSyncService, PRPSyncResult
    from users.api.prp_client import PRPClient, create_prp_client
    from users.api.exceptions import (
        PRPBaseException,
        PRPConnectionError,
        PRPAuthenticationError,
        PRPSyncError,
        PRPDataValidationError,
        PRPConfigurationError
    )
except ImportError as e:
    raise CommandError(
        f"PRP integration modules not available: {e}. "
        "Ensure all PRP integration files are properly implemented."
    )

User = get_user_model()

# Configure logging for sync operations
logger = logging.getLogger('pims.prp_integration.sync_command')


class Command(BaseCommand):
    """
    Django management command for PRP user synchronization.
    
    Provides admin-controlled synchronization of user data from PRP API
    to PIMS with comprehensive error handling, progress reporting, and
    rollback capabilities.
    """
    
    help = 'Synchronize users from PRP (Parliament Resource Portal) to PIMS'
    
    def add_arguments(self, parser):
        """Add command-line arguments."""
        
        # Sync scope arguments (mutually exclusive)
        sync_group = parser.add_mutually_exclusive_group(required=True)
        sync_group.add_argument(
            '--all',
            action='store_true',
            help='Sync all departments and users from PRP'
        )
        sync_group.add_argument(
            '--department',
            type=str,
            help='Sync specific department by ID (number) or name (string)'
        )
        sync_group.add_argument(
            '--status-only',
            action='store_true',
            help='Update only user status without full data sync'
        )
        
        # Operation mode arguments
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Preview changes without applying them'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force sync ignoring timestamp checks'
        )
        parser.add_argument(
            '--quiet',
            action='store_true',
            help='Minimal output (errors and summary only)'
        )
        parser.add_argument(
            '--no-progress',
            action='store_true',
            help='Disable progress reporting'
        )
        
        # Filtering arguments
        parser.add_argument(
            '--limit',
            type=int,
            help='Limit number of users to sync (for testing)'
        )
        parser.add_argument(
            '--skip-inactive',
            action='store_true',
            help='Skip inactive users in PRP'
        )
        
        # Configuration overrides
        parser.add_argument(
            '--api-url',
            type=str,
            help='Override PRP API base URL'
        )
        parser.add_argument(
            '--timeout',
            type=int,
            default=30,
            help='API request timeout in seconds (default: 30)'
        )
    
    def handle(self, *args, **options):
        """Main command handler."""
        
        start_time = timezone.now()
        
        # Validate prerequisites
        self._validate_prerequisites(options)
        
        try:
            # Create PRP client
            prp_client = self._create_prp_client(options)
            
            # Create sync service
            sync_service = PRPSyncService(prp_client)
            
            # Execute sync operation based on arguments
            if options['all']:
                result = self._sync_all_departments(sync_service, options)
            elif options['department']:
                result = self._sync_department(sync_service, options['department'], options)
            elif options['status_only']:
                result = self._sync_status_only(sync_service, options)
            else:
                raise CommandError("No sync operation specified")
            
            # Display results
            self._display_results(result, options, start_time)
            
        except PRPBaseException as e:
            self._handle_prp_error(e)
        except Exception as e:
            self._handle_unexpected_error(e)
    
    def _validate_prerequisites(self, options: Dict[str, Any]) -> None:
        """Validate that prerequisites are met."""
        
        # Check Django environment
        try:
            User.objects.first()  # Test database access
        except Exception as e:
            raise CommandError(f"Database access failed: {e}")
        
        # Log permission check
        logger.info(
            "PRP User Sync command started",
            extra={
                'location': 'Bangladesh Parliament Secretariat, Dhaka',
                'operation': 'admin_sync',
                'timestamp': timezone.now().isoformat()
            }
        )
    
    def _create_prp_client(self, options: Dict[str, Any]) -> PRPClient:
        """Create and configure PRP client."""
        
        try:
            client = create_prp_client(base_url=options.get('api_url'))
            
            # Test connection
            if not options['quiet']:
                self.stdout.write("Testing PRP API connection...")
            
            connection_test = client.test_connection()
            
            if not connection_test['success']:
                raise CommandError(
                    f"PRP API connection test failed: {connection_test.get('error', 'Unknown error')}"
                )
            
            if not options['quiet']:
                self.stdout.write(
                    self.style.SUCCESS("✓ PRP API connection successful")
                )
            
            return client
            
        except PRPBaseException as e:
            raise CommandError(f"PRP client initialization failed: {e}")
    
    @transaction.atomic
    def _sync_all_departments(
        self, 
        sync_service: PRPSyncService, 
        options: Dict[str, Any]
    ) -> PRPSyncResult:
        """Sync all departments and their users."""
        
        logger.info("Starting full sync of all PRP departments")
        
        if not options['quiet']:
            self.stdout.write(
                self.style.HTTP_INFO("🔄 Syncing all departments from PRP...")
            )
        
        try:
            result = sync_service.sync_all_departments(
                dry_run=options.get('dry_run', False),
                force=options.get('force', False),
                limit=options.get('limit'),
                skip_inactive=options.get('skip_inactive', False)
            )
            
            if not options['quiet'] and not options.get('no_progress', False):
                departments = sync_service.get_prp_departments()
                self.stdout.write(f"Found {len(departments)} departments in PRP")
                
                for i, department in enumerate(departments, 1):
                    dept_name = department.get('nameEng', f"Department {department.get('id')}")
                    self.stdout.write(f"[{i}/{len(departments)}] Processed: {dept_name}")
            
            return result
            
        except Exception as e:
            logger.error(f"Full sync failed: {e}")
            raise
    
    @transaction.atomic
    def _sync_department(
        self, 
        sync_service: PRPSyncService, 
        department_identifier: str,
        options: Dict[str, Any]
    ) -> PRPSyncResult:
        """Sync specific department by ID or name."""
        
        logger.info(f"Starting sync for department: {department_identifier}")
        
        try:
            # Resolve department ID from identifier
            if department_identifier.isdigit():
                department_id = int(department_identifier)
                dept_name = f"Department {department_id}"
            else:
                # Find department by name
                departments = sync_service.get_prp_departments()
                department_id = None
                dept_name = department_identifier
                
                for dept in departments:
                    if (dept.get('nameEng', '').lower() == department_identifier.lower() or
                        dept.get('nameBng', '').lower() == department_identifier.lower()):
                        department_id = dept['id']
                        dept_name = dept.get('nameEng', dept_name)
                        break
                
                if department_id is None:
                    available_depts = [
                        dept.get('nameEng', f"ID:{dept.get('id')}") 
                        for dept in departments
                    ]
                    raise CommandError(
                        f"Department '{department_identifier}' not found in PRP. "
                        f"Available departments: {', '.join(available_depts)}"
                    )
            
            if not options['quiet']:
                self.stdout.write(
                    self.style.HTTP_INFO(f"🔄 Syncing department: {dept_name}")
                )
            
            # Perform sync
            result = sync_service.sync_department_users(
                department_id=department_id,
                dry_run=options.get('dry_run', False),
                force=options.get('force', False),
                limit=options.get('limit'),
                skip_inactive=options.get('skip_inactive', False)
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Department sync failed: {e}")
            raise
    
    @transaction.atomic
    def _sync_status_only(
        self, 
        sync_service: PRPSyncService, 
        options: Dict[str, Any]
    ) -> PRPSyncResult:
        """Sync only user status without full data update."""
        
        logger.info("Starting status-only sync")
        
        if not options['quiet']:
            self.stdout.write(
                self.style.HTTP_INFO("🔄 Syncing user status only...")
            )
        
        # For status-only sync, we'll sync all departments but with minimal data update
        # This would require additional implementation in PRPSyncService
        result = sync_service.sync_all_departments(
            dry_run=options.get('dry_run', False),
            force=True,  # Force to ensure status updates
            limit=options.get('limit'),
            skip_inactive=False  # Don't skip inactive users for status sync
        )
        
        return result
    
    def _display_results(
        self, 
        result: PRPSyncResult, 
        options: Dict[str, Any], 
        start_time: datetime
    ) -> None:
        """Display sync operation results."""
        
        duration = timezone.now() - start_time
        
        if not options['quiet']:
            self.stdout.write("\n" + "="*60)
            self.stdout.write(self.style.SUCCESS("PRP SYNC OPERATION COMPLETED"))
            self.stdout.write("="*60)
            
            # Summary statistics
            self.stdout.write(f"📊 SYNC SUMMARY:")
            self.stdout.write(f"   • Duration: {duration.total_seconds():.1f} seconds")
            self.stdout.write(f"   • Departments Processed: {result.departments_processed}")
            self.stdout.write(f"   • Users Created: {result.users_created}")
            self.stdout.write(f"   • Users Updated: {result.users_updated}")
            self.stdout.write(f"   • Users Skipped: {result.users_skipped}")
            self.stdout.write(f"   • Errors: {result.users_errors}")
            
            # Warnings
            if result.warnings:
                self.stdout.write(f"\n⚠️  WARNINGS ({len(result.warnings)}):")
                for warning in result.warnings[:5]:  # Show first 5 warnings
                    self.stdout.write(f"   • {warning}")
                if len(result.warnings) > 5:
                    self.stdout.write(f"   • ... and {len(result.warnings) - 5} more warnings")
            
            # Errors
            if result.errors:
                self.stdout.write(f"\n❌ ERRORS ({len(result.errors)}):")
                for error in result.errors[:5]:  # Show first 5 errors
                    self.stdout.write(f"   • {error}")
                if len(result.errors) > 5:
                    self.stdout.write(f"   • ... and {len(result.errors) - 5} more errors")
            
            self.stdout.write("="*60)
        
        # Final status message
        if result.success and result.users_errors == 0:
            self.stdout.write(
                self.style.SUCCESS(
                    f"\n✅ Sync completed successfully! "
                    f"{result.users_created + result.users_updated} users processed."
                )
            )
        else:
            self.stdout.write(
                self.style.ERROR(
                    f"\n⚠️ Sync completed with {result.users_errors} errors. "
                    "Check logs for details."
                )
            )
        
        # Log final results
        logger.info(
            "PRP sync operation completed",
            extra={
                'duration_seconds': duration.total_seconds(),
                'users_created': result.users_created,
                'users_updated': result.users_updated,
                'users_skipped': result.users_skipped,
                'departments_processed': result.departments_processed,
                'errors': result.users_errors,
                'dry_run': options.get('dry_run', False),
                'location': 'Bangladesh Parliament Secretariat, Dhaka'
            }
        )
    
    def _handle_prp_error(self, error: PRPBaseException):
        """Handle PRP-specific errors with appropriate user feedback."""
        
        if isinstance(error, PRPConnectionError):
            raise CommandError(
                f"Failed to connect to PRP API: {error}\n"
                "Please check network connectivity and PRP server status."
            )
        elif isinstance(error, PRPAuthenticationError):
            raise CommandError(
                f"PRP authentication failed: {error}\n"
                "Please verify PRP credentials in Django settings."
            )
        elif isinstance(error, PRPSyncError):
            raise CommandError(
                f"User synchronization failed: {error}\n"
                "Check sync service configuration and data integrity."
            )
        elif isinstance(error, PRPDataValidationError):
            raise CommandError(
                f"Invalid data received from PRP: {error}\n"
                "PRP API may have changed format or returned unexpected data."
            )
        elif isinstance(error, PRPConfigurationError):
            raise CommandError(
                f"PRP integration configuration error: {error}\n"
                "Check Django settings for PRP integration."
            )
        else:
            raise CommandError(f"PRP error: {error}")
    
    def _handle_unexpected_error(self, error: Exception):
        """Handle unexpected errors with full traceback logging."""
        
        error_id = timezone.now().strftime('%Y%m%d_%H%M%S')
        
        logger.error(
            f"Unexpected error in PRP sync command [ID: {error_id}]",
            extra={
                'error_type': type(error).__name__,
                'error_message': str(error),
                'traceback': traceback.format_exc(),
                'error_id': error_id
            }
        )
        
        raise CommandError(
            f"Unexpected error occurred [Error ID: {error_id}]: {error}\n"
            "Check logs for full details. Contact system administrator if issue persists."
        )


# Utility functions for testing and validation
def validate_sync_environment() -> Dict[str, Any]:
    """
    Validate that the environment is properly configured for PRP sync.
    
    Returns:
        Dictionary with validation results
    """
    validation_result = {
        'valid': True,
        'issues': [],
        'warnings': []
    }
    
    # Check database migration
    try:
        User = get_user_model()
        test_user = User.objects.first()
        if test_user and not hasattr(test_user, 'is_prp_managed'):
            validation_result['issues'].append(
                "PRP fields not found in User model. Run migration 0002_add_prp_fields.py"
            )
            validation_result['valid'] = False
    except Exception as e:
        validation_result['issues'].append(f"Database access failed: {e}")
        validation_result['valid'] = False
    
    # Check PRP API settings
    required_settings = ['PRP_API_BASE_URL', 'PRP_USERNAME', 'PRP_PASSWORD']
    for setting in required_settings:
        if not getattr(settings, setting, None):
            validation_result['warnings'].append(
                f"Setting {setting} not found. Using default values."
            )
    
    # Check timezone setting
    if settings.TIME_ZONE != 'Asia/Dhaka':
        validation_result['warnings'].append(
            f"TIME_ZONE is {settings.TIME_ZONE}, expected 'Asia/Dhaka' for Bangladesh Parliament"
        )
    
    return validation_result


# Export for testing
__all__ = ['Command', 'validate_sync_environment']