"""
Django Management Command: PRP Department Synchronization
=========================================================

Department sync command for PIMS-PRP Integration at Bangladesh Parliament Secretariat.

Location: Bangladesh Parliament Secretariat, Dhaka, Bangladesh
Project: PIMS-PRP Integration
Purpose: Sync department information from PRP API for accurate office field mapping

Business Context:
- PRP departments are used to populate the 'office' field in PIMS CustomUser model
- Department data comes from PRP API: /api/secure/external?action=departments
- Department structure: {nameEng, nameBng, id, isWing}
- Used during user sync to map department.nameEng → user.office

Key Features:
- Retrieves and caches department list from PRP API
- Validates department data structure
- Provides department lookup for user sync operations
- Comprehensive error handling and logging
- Admin-only operation with detailed reporting

Usage Examples:
    # Sync departments from PRP
    python manage.py sync_prp_departments

    # Sync with detailed output
    python manage.py sync_prp_departments --verbose

    # Dry run to preview departments
    python manage.py sync_prp_departments --dry-run

    # Force refresh ignoring cache
    python manage.py sync_prp_departments --force

    # Export departments to file for backup
    python manage.py sync_prp_departments --export=/path/to/departments.json

Dependencies:
- users.api.prp_client (PRPClient)
- users.api.exceptions (PRP exceptions)
"""

import json
import logging
import sys
import traceback
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
from django.core.management.base import BaseCommand, CommandError
from django.core.cache import cache
from django.conf import settings
from django.utils import timezone
from django.db import connection

# Import PRP integration modules
try:
    from users.api.prp_client import PRPClient, create_prp_client
    from users.api.exceptions import (
        PRPException,
        PRPConnectionError,
        PRPAuthenticationError,
        PRPDataValidationError,
        PRPConfigurationError
    )
except ImportError as e:
    raise CommandError(
        f"PRP integration modules not available: {e}. "
        "Ensure prp_client.py is implemented before running this command."
    )

# Configure logging
logger = logging.getLogger('pims.prp_integration.departments')

# Cache configuration for department data
DEPARTMENT_CACHE_KEY = 'prp_departments'
DEPARTMENT_CACHE_TIMEOUT = 3600 * 24  # 24 hours
DEPARTMENT_LAST_SYNC_KEY = 'prp_departments_last_sync'


class Command(BaseCommand):
    """
    Django management command for PRP department synchronization.
    
    Maintains updated department information from PRP API for accurate
    office field mapping during user synchronization operations.
    """
    
    help = 'Synchronize departments from PRP (Parliament Resource Portal) for office field mapping'
    
    def add_arguments(self, parser):
        """Add command-line arguments."""
        
        # Operation mode arguments
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Preview departments without caching them'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force refresh ignoring cached data'
        )
        parser.add_argument(
            '--quiet',
            action='store_true',
            help='Minimal output (errors and summary only)'
        )
        
        # Data export/import arguments
        parser.add_argument(
            '--export',
            type=str,
            help='Export departments to JSON file (e.g., --export=/path/to/departments.json)'
        )
        parser.add_argument(
            '--import',
            dest='import_file',
            type=str,
            help='Import departments from JSON file (for testing/backup restore)'
        )
        
        # Validation and reporting arguments
        parser.add_argument(
            '--validate-users',
            action='store_true',
            help='Validate existing users against current departments'
        )
        parser.add_argument(
            '--show-stats',
            action='store_true',
            help='Show department usage statistics'
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
        
        # Configure logging based on verbosity
        self._configure_logging(options)
        
        # Record operation start time
        sync_start_time = timezone.now()
        
        try:
            # Handle different operation modes
            if options.get('import_file'):
                self._import_departments(options['import_file'], options)
            elif options.get('validate_users'):
                self._validate_user_departments(options)
            elif options.get('show_stats'):
                self._show_department_statistics(options)
            else:
                # Main sync operation
                self._sync_departments(options)
            
            # Show completion message
            duration = timezone.now() - sync_start_time
            if not options['quiet']:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"✓ Department operation completed in {duration.total_seconds():.1f} seconds"
                    )
                )
                
        except PRPException as e:
            self._handle_prp_error(e)
        except Exception as e:
            self._handle_unexpected_error(e)
    
    def _configure_logging(self, options: Dict[str, Any]):
        """Configure logging based on command options."""
        
        if options['quiet']:
            log_level = logging.ERROR
        elif options['verbosity'] >= 2:
            log_level = logging.DEBUG
        else:
            log_level = logging.INFO
        
        # Configure logger
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            '%(asctime)s - PRP Departments - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S %Z'  # Bangladesh time format
        )
        handler.setFormatter(formatter)
        
        logger.handlers.clear()
        logger.addHandler(handler)
        logger.setLevel(log_level)
        
        # Set timezone for logging
        import pytz
        handler.formatter.converter = lambda *args: pytz.timezone(
            'Asia/Dhaka'
        ).localize(datetime.now()).timetuple()
    
    def _sync_departments(self, options: Dict[str, Any]):
        """Main department synchronization operation."""
        
        logger.info("Starting PRP department synchronization")
        
        if not options['quiet']:
            self.stdout.write(
                self.style.HTTP_INFO("🔄 Syncing departments from PRP...")
            )
        
        # Check cache if not forcing refresh
        if not options.get('force', False):
            cached_departments = self._get_cached_departments()
            if cached_departments:
                if not options['quiet']:
                    self.stdout.write(
                        self.style.WARNING(
                            f"Using cached departments ({len(cached_departments)} items). "
                            "Use --force to refresh from PRP."
                        )
                    )
                
                self._display_departments(cached_departments, options)
                return cached_departments
        
        # Create PRP client and fetch departments
        try:
            prp_client = self._create_prp_client(options)
            departments = prp_client.get_departments()
            
        except Exception as e:
            raise CommandError(f"Failed to retrieve departments from PRP: {e}")
        
        # Validate department data
        validated_departments = self._validate_departments(departments)
        
        # Cache departments if not dry run
        if not options.get('dry_run', False):
            self._cache_departments(validated_departments)
            
            if not options['quiet']:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"✓ Cached {len(validated_departments)} departments for office field mapping"
                    )
                )
        
        # Display departments
        self._display_departments(validated_departments, options)
        
        # Export if requested
        if options.get('export'):
            self._export_departments(validated_departments, options['export'], options)
        
        # Clean up resources
        if 'prp_client' in locals():
            prp_client.close()
        
        return validated_departments
    
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
            
        except PRPException as e:
            raise CommandError(f"PRP client initialization failed: {e}")
    
    def _validate_departments(self, departments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Validate department data structure and content."""
        
        logger.info(f"Validating {len(departments)} departments from PRP")
        
        validated_departments = []
        validation_errors = []
        
        required_fields = ['id', 'nameEng']
        optional_fields = ['nameBng', 'isWing']
        
        for i, dept in enumerate(departments):
            dept_errors = []
            
            # Check required fields
            for field in required_fields:
                if field not in dept:
                    dept_errors.append(f"Missing required field: {field}")
                elif not dept[field]:
                    dept_errors.append(f"Empty required field: {field}")
            
            # Validate field types
            if 'id' in dept and not isinstance(dept['id'], int):
                dept_errors.append(f"Department ID must be integer, got: {type(dept['id'])}")
            
            if 'nameEng' in dept and not isinstance(dept['nameEng'], str):
                dept_errors.append(f"nameEng must be string, got: {type(dept['nameEng'])}")
            
            if 'isWing' in dept and not isinstance(dept['isWing'], bool):
                dept_errors.append(f"isWing must be boolean, got: {type(dept['isWing'])}")
            
            # Log validation issues
            if dept_errors:
                dept_name = dept.get('nameEng', f"Department {i+1}")
                validation_errors.extend([f"{dept_name}: {error}" for error in dept_errors])
                logger.warning(
                    f"Department validation failed: {dept_name}",
                    extra={'errors': dept_errors, 'department_data': dept}
                )
            else:
                # Add validated department
                validated_departments.append({
                    'id': dept['id'],
                    'nameEng': dept['nameEng'].strip(),
                    'nameBng': dept.get('nameBng', '').strip() if dept.get('nameBng') else '',
                    'isWing': dept.get('isWing', False)
                })
        
        # Report validation results
        if validation_errors:
            logger.error(
                f"Department validation found {len(validation_errors)} errors",
                extra={'errors': validation_errors}
            )
            
            # Show first few errors to user
            self.stdout.write(
                self.style.ERROR(f"⚠ {len(validation_errors)} department validation errors:")
            )
            for error in validation_errors[:3]:
                self.stdout.write(f"  • {error}")
            if len(validation_errors) > 3:
                self.stdout.write(f"  ... and {len(validation_errors) - 3} more errors")
        
        logger.info(
            f"Department validation completed: {len(validated_departments)} valid, "
            f"{len(departments) - len(validated_departments)} invalid"
        )
        
        return validated_departments
    
    def _cache_departments(self, departments: List[Dict[str, Any]]):
        """Cache department data for user sync operations."""
        
        try:
            # Cache departments list
            cache.set(DEPARTMENT_CACHE_KEY, departments, DEPARTMENT_CACHE_TIMEOUT)
            
            # Cache last sync timestamp
            cache.set(DEPARTMENT_LAST_SYNC_KEY, timezone.now(), DEPARTMENT_CACHE_TIMEOUT)
            
            # Create department lookup by ID and name for quick access
            dept_by_id = {dept['id']: dept for dept in departments}
            dept_by_name = {dept['nameEng'].lower(): dept for dept in departments}
            
            cache.set('prp_departments_by_id', dept_by_id, DEPARTMENT_CACHE_TIMEOUT)
            cache.set('prp_departments_by_name', dept_by_name, DEPARTMENT_CACHE_TIMEOUT)
            
            logger.info(
                f"Cached {len(departments)} departments",
                extra={'cache_timeout': DEPARTMENT_CACHE_TIMEOUT}
            )
            
        except Exception as e:
            logger.error(f"Failed to cache departments: {e}")
            raise CommandError(f"Department caching failed: {e}")
    
    def _get_cached_departments(self) -> Optional[List[Dict[str, Any]]]:
        """Retrieve cached department data."""
        
        departments = cache.get(DEPARTMENT_CACHE_KEY)
        last_sync = cache.get(DEPARTMENT_LAST_SYNC_KEY)
        
        if departments and last_sync:
            logger.info(
                f"Retrieved {len(departments)} departments from cache",
                extra={'last_sync': last_sync.isoformat()}
            )
            return departments
        
        return None
    
    def _display_departments(self, departments: List[Dict[str, Any]], options: Dict[str, Any]):
        """Display department information to user."""
        
        if options['quiet']:
            return
        
        self.stdout.write("\n" + "="*60)
        self.stdout.write(
            self.style.HTTP_INFO("PRP Departments - Bangladesh Parliament Secretariat")
        )
        self.stdout.write("="*60)
        
        # Summary statistics
        total_depts = len(departments)
        wings = sum(1 for dept in departments if dept.get('isWing', False))
        regular_depts = total_depts - wings
        
        self.stdout.write(f"Total departments: {total_depts}")
        self.stdout.write(f"Wings: {wings}")
        self.stdout.write(f"Regular departments: {regular_depts}")
        
        # Department list
        if options['verbosity'] >= 2:
            self.stdout.write("\nDepartment Details:")
            self.stdout.write("-" * 40)
            
            for dept in sorted(departments, key=lambda x: x['nameEng']):
                dept_type = "Wing" if dept.get('isWing', False) else "Dept"
                bengali_name = f" ({dept['nameBng']})" if dept.get('nameBng') else ""
                
                self.stdout.write(
                    f"[{dept['id']:3d}] {dept['nameEng']}{bengali_name} ({dept_type})"
                )
        
        # Show sample for mapping reference
        else:
            self.stdout.write("\nSample departments for office field mapping:")
            self.stdout.write("-" * 40)
            
            for dept in sorted(departments, key=lambda x: x['nameEng'])[:5]:
                self.stdout.write(f"  • {dept['nameEng']}")
            
            if len(departments) > 5:
                self.stdout.write(f"  ... and {len(departments) - 5} more departments")
    
    def _export_departments(self, departments: List[Dict[str, Any]], export_path: str, options: Dict[str, Any]):
        """Export departments to JSON file."""
        
        try:
            export_file = Path(export_path)
            export_file.parent.mkdir(parents=True, exist_ok=True)
            
            export_data = {
                'metadata': {
                    'export_time': timezone.now().isoformat(),
                    'source': 'PRP API - Bangladesh Parliament Secretariat',
                    'total_departments': len(departments),
                    'api_base_url': getattr(settings, 'PRP_API_BASE_URL', 'https://prp.parliament.gov.bd')
                },
                'departments': departments
            }
            
            with open(export_file, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
            
            if not options['quiet']:
                self.stdout.write(
                    self.style.SUCCESS(f"✓ Exported {len(departments)} departments to {export_path}")
                )
            
            logger.info(f"Departments exported to {export_path}")
            
        except Exception as e:
            logger.error(f"Export failed: {e}")
            raise CommandError(f"Failed to export departments: {e}")
    
    def _import_departments(self, import_path: str, options: Dict[str, Any]):
        """Import departments from JSON file (for testing/backup restore)."""
        
        try:
            import_file = Path(import_path)
            
            if not import_file.exists():
                raise CommandError(f"Import file not found: {import_path}")
            
            with open(import_file, 'r', encoding='utf-8') as f:
                import_data = json.load(f)
            
            departments = import_data.get('departments', [])
            
            if not departments:
                raise CommandError("No departments found in import file")
            
            # Validate imported data
            validated_departments = self._validate_departments(departments)
            
            # Cache imported departments if not dry run
            if not options.get('dry_run', False):
                self._cache_departments(validated_departments)
            
            if not options['quiet']:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"✓ Imported {len(validated_departments)} departments from {import_path}"
                    )
                )
            
            # Display imported departments
            self._display_departments(validated_departments, options)
            
        except Exception as e:
            logger.error(f"Import failed: {e}")
            raise CommandError(f"Failed to import departments: {e}")
    
    def _validate_user_departments(self, options: Dict[str, Any]):
        """Validate existing users against current departments."""
        
        try:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            
            # Get current departments
            departments = self._get_cached_departments()
            if not departments:
                raise CommandError("No cached departments found. Run sync first.")
            
            # Create department lookup
            dept_names = {dept['nameEng'].lower() for dept in departments}
            
            # Check users with office assignments
            users_with_office = User.objects.filter(
                office__isnull=False
            ).exclude(office='').values_list('office', flat=True)
            
            # Find mismatched offices
            unique_offices = set(users_with_office)
            unmatched_offices = {
                office for office in unique_offices
                if office.lower() not in dept_names
            }
            
            # Report results
            total_offices = len(unique_offices)
            matched_offices = total_offices - len(unmatched_offices)
            
            self.stdout.write("\n" + "="*60)
            self.stdout.write("User-Department Validation Results")
            self.stdout.write("="*60)
            self.stdout.write(f"Total unique office assignments: {total_offices}")
            self.stdout.write(f"Matched with PRP departments: {matched_offices}")
            self.stdout.write(f"Unmatched offices: {len(unmatched_offices)}")
            
            if unmatched_offices and not options['quiet']:
                self.stdout.write("\nUnmatched office assignments:")
                for office in sorted(unmatched_offices):
                    user_count = list(users_with_office).count(office)
                    self.stdout.write(f"  • {office} ({user_count} users)")
            
        except Exception as e:
            raise CommandError(f"User validation failed: {e}")
    
    def _show_department_statistics(self, options: Dict[str, Any]):
        """Show department usage statistics."""
        
        try:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            
            # Get departments
            departments = self._get_cached_departments()
            if not departments:
                departments = self._sync_departments({'quiet': True, 'dry_run': True})
            
            # Get user office statistics
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT office, COUNT(*) as user_count
                    FROM users_customuser 
                    WHERE office IS NOT NULL AND office != ''
                    GROUP BY office
                    ORDER BY user_count DESC
                """)
                office_stats = cursor.fetchall()
            
            # Display statistics
            self.stdout.write("\n" + "="*60)
            self.stdout.write("Department Usage Statistics")
            self.stdout.write("="*60)
            
            self.stdout.write(f"Total PRP departments: {len(departments)}")
            self.stdout.write(f"Departments with users: {len(office_stats)}")
            
            if office_stats:
                self.stdout.write(f"Total users with office assignment: {sum(count for _, count in office_stats)}")
                
                if not options['quiet']:
                    self.stdout.write("\nTop departments by user count:")
                    for office, count in office_stats[:10]:
                        self.stdout.write(f"  {office}: {count} users")
                    
                    if len(office_stats) > 10:
                        self.stdout.write(f"  ... and {len(office_stats) - 10} more departments")
            
        except Exception as e:
            raise CommandError(f"Statistics generation failed: {e}")
    
    def _handle_prp_error(self, error: PRPException):
        """Handle PRP-specific errors with appropriate user feedback."""
        
        if isinstance(error, PRPConnectionError):
            raise CommandError(
                f"Failed to connect to PRP API: {error.message}\n"
                "Please check network connectivity and PRP server status."
            )
        elif isinstance(error, PRPAuthenticationError):
            raise CommandError(
                f"PRP authentication failed: {error.message}\n"
                "Please verify PRP credentials in Django settings."
            )
        elif isinstance(error, PRPDataValidationError):
            raise CommandError(
                f"Invalid department data from PRP: {error.message}\n"
                "PRP API may have changed format or returned unexpected data."
            )
        elif isinstance(error, PRPConfigurationError):
            raise CommandError(
                f"PRP integration configuration error: {error.message}\n"
                "Check Django settings for PRP integration."
            )
        else:
            raise CommandError(f"PRP error: {error.message}")
    
    def _handle_unexpected_error(self, error: Exception):
        """Handle unexpected errors with full traceback logging."""
        
        error_id = timezone.now().strftime('%Y%m%d_%H%M%S')
        
        logger.error(
            f"Unexpected error in PRP department sync [ID: {error_id}]",
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


# Utility functions for department management
def get_prp_departments() -> List[Dict[str, Any]]:
    """
    Get PRP departments from cache or API.
    
    Returns:
        List of department dictionaries
        
    Raises:
        CommandError: If departments cannot be retrieved
    """
    # Try cache first
    departments = cache.get(DEPARTMENT_CACHE_KEY)
    if departments:
        return departments
    
    # Fall back to API
    try:
        client = create_prp_client()
        departments = client.get_departments()
        
        # Cache for future use
        cache.set(DEPARTMENT_CACHE_KEY, departments, DEPARTMENT_CACHE_TIMEOUT)
        cache.set(DEPARTMENT_LAST_SYNC_KEY, timezone.now(), DEPARTMENT_CACHE_TIMEOUT)
        
        return departments
        
    except Exception as e:
        raise CommandError(f"Failed to retrieve departments: {e}")


def get_department_by_id(department_id: int) -> Optional[Dict[str, Any]]:
    """
    Get specific department by ID.
    
    Args:
        department_id: PRP department ID
        
    Returns:
        Department dictionary or None if not found
    """
    dept_lookup = cache.get('prp_departments_by_id')
    if not dept_lookup:
        departments = get_prp_departments()
        dept_lookup = {dept['id']: dept for dept in departments}
        cache.set('prp_departments_by_id', dept_lookup, DEPARTMENT_CACHE_TIMEOUT)
    
    return dept_lookup.get(department_id)


def get_department_by_name(department_name: str) -> Optional[Dict[str, Any]]:
    """
    Get specific department by name (case-insensitive).
    
    Args:
        department_name: Department name (English)
        
    Returns:
        Department dictionary or None if not found
    """
    dept_lookup = cache.get('prp_departments_by_name')
    if not dept_lookup:
        departments = get_prp_departments()
        dept_lookup = {dept['nameEng'].lower(): dept for dept in departments}
        cache.set('prp_departments_by_name', dept_lookup, DEPARTMENT_CACHE_TIMEOUT)
    
    return dept_lookup.get(department_name.lower())


# Export for testing and external use
__all__ = [
    'Command', 
    'get_prp_departments', 
    'get_department_by_id', 
    'get_department_by_name'
]