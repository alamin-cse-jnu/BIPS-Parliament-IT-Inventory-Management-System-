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
- Department structure: {nameEng, id, isWing} (only required fields for PIMS)
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
    
    Location: Bangladesh Parliament Secretariat, Dhaka, Bangladesh
    """
    
    help = '''
    Synchronize department data from PRP (Parliament Resource Portal) for PIMS user sync support.
    
    Location: Bangladesh Parliament Secretariat, Dhaka, Bangladesh
    
    This command fetches and caches department information from PRP API to support
    accurate office field mapping during user synchronization operations.
    
    Examples:
        python manage.py sync_prp_departments                        # Sync departments
        python manage.py sync_prp_departments --force                # Force refresh
        python manage.py sync_prp_departments --dry-run              # Preview only
        python manage.py sync_prp_departments --verbose              # Detailed output
        python manage.py sync_prp_departments --export=depts.json    # Export to file
    '''
    
    def add_arguments(self, parser):
        """Add command line arguments."""
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force refresh ignoring cache and recent sync timestamps'
        )
        
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Preview departments without caching or applying changes'
        )
        
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Enable detailed output and logging'
        )
        
        parser.add_argument(
            '--export',
            type=str,
            help='Export departments to JSON file (provide file path)'
        )
        
        parser.add_argument(
            '--validate-only',
            action='store_true',
            help='Only validate cached department data without fetching new data'
        )
        
        parser.add_argument(
            '--clear-cache',
            action='store_true',
            help='Clear department cache and exit'
        )
        
        parser.add_argument(
            '--timeout',
            type=int,
            default=120,
            help='API timeout in seconds (default: 120)'
        )
    
    def handle(self, *args, **options):
        """Main command handler."""
        # Store options
        self.options = options
        self.verbosity = options.get('verbosity', 1)
        self.dry_run = options.get('dry_run', False)
        self.force = options.get('force', False)
        self.verbose = options.get('verbose', False)
        
        # Configure logging level
        if self.verbose:
            logging.getLogger('pims.prp_integration').setLevel(logging.DEBUG)
        
        # Bangladesh time context
        dhaka_time = timezone.now().astimezone(timezone.get_default_timezone())
        
        self.stdout.write("=" * 80)
        self.stdout.write(
            self.style.SUCCESS("🏢 PRP Department Sync - Bangladesh Parliament Secretariat")
        )
        self.stdout.write(f"📍 Location: Dhaka, Bangladesh")
        self.stdout.write(f"🕐 Started at: {dhaka_time.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        
        if self.dry_run:
            self.stdout.write(self.style.WARNING("🧪 DRY RUN MODE - No changes will be applied"))
        
        self.stdout.write("=" * 80)
        
        try:
            # Handle special operations first
            if options.get('clear_cache'):
                self._clear_cache()
                return 0
            
            if options.get('validate_only'):
                return self._validate_cached_departments()
            
            # Initialize PRP client
            self._initialize_client()
            
            # Sync departments
            departments = self._sync_departments()
            
            # Export if requested
            if options.get('export'):
                self._export_departments(departments, options['export'])
            
            # Display results
            self._display_results(departments)
            
            self.stdout.write(
                self.style.SUCCESS("✅ PRP department synchronization completed successfully")
            )
            return 0
            
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING("\n⏹️  Department sync cancelled by user"))
            return 130
        except Exception as e:
            self.stderr.write(
                self.style.ERROR(f"💥 Fatal error during department sync: {str(e)}")
            )
            if self.verbose:
                self.stderr.write(f"Traceback: {traceback.format_exc()}")
            return 1
    
    def _initialize_client(self):
        """Initialize PRP client."""
        try:
            self.stdout.write("🔌 Initializing PRP API connection...")
            
            # Create PRP client using factory function
            self.prp_client = create_prp_client()
            
            # Test connection
            self.prp_client.health_check()
            self.stdout.write(self.style.SUCCESS("✅ PRP API connection established"))
            
        except PRPConfigurationError as e:
            raise CommandError(f"PRP configuration error: {e}")
        except PRPConnectionError as e:
            raise CommandError(f"Cannot connect to PRP API: {e}")
        except Exception as e:
            raise CommandError(f"Failed to initialize PRP client: {e}")
    
    def _sync_departments(self) -> List[Dict[str, Any]]:
        """Sync departments from PRP API."""
        # Check if we need to sync
        if not self.force and not self.dry_run:
            last_sync = cache.get(DEPARTMENT_LAST_SYNC_KEY)
            if last_sync:
                time_since_sync = timezone.now() - last_sync
                if time_since_sync.total_seconds() < 3600:  # 1 hour
                    self.stdout.write("ℹ️  Using cached departments (synced recently)")
                    cached_departments = cache.get(DEPARTMENT_CACHE_KEY, [])
                    if cached_departments:
                        return cached_departments
        
        self.stdout.write("🔄 Fetching departments from PRP API...")
        
        try:
            # Fetch departments from PRP
            departments = self.prp_client.get_departments()
            
            if not departments:
                self.stdout.write(self.style.WARNING("⚠️  No departments found in PRP"))
                return []
            
            self.stdout.write(f"📦 Retrieved {len(departments)} departments from PRP")
            
            # Validate department data structure
            validated_departments = self._validate_departments(departments)
            
            # Cache departments if not dry run
            if not self.dry_run:
                cache.set(DEPARTMENT_CACHE_KEY, validated_departments, DEPARTMENT_CACHE_TIMEOUT)
                cache.set(DEPARTMENT_LAST_SYNC_KEY, timezone.now(), DEPARTMENT_CACHE_TIMEOUT)
                self.stdout.write("💾 Departments cached successfully")
            else:
                self.stdout.write("🧪 DRY RUN: Departments not cached")
            
            return validated_departments
            
        except PRPConnectionError as e:
            raise CommandError(f"Failed to fetch departments from PRP: {e}")
        except PRPDataValidationError as e:
            raise CommandError(f"Invalid department data from PRP: {e}")
        except Exception as e:
            raise CommandError(f"Unexpected error during department sync: {e}")
    
    def _validate_departments(self, departments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Validate and normalize department data structure."""
        validated = []
        invalid_count = 0
        
        for dept in departments:
            try:
                # Required fields for PIMS integration
                if not isinstance(dept, dict):
                    invalid_count += 1
                    continue
                
                # Validate essential fields
                dept_id = dept.get('id')
                name_eng = dept.get('nameEng', '').strip()
                
                if not dept_id or not name_eng:
                    invalid_count += 1
                    if self.verbose:
                        self.stdout.write(
                            self.style.WARNING(f"⚠️  Skipping invalid department: {dept}")
                        )
                    continue
                
                # Normalize department data (only required fields for PIMS)
                normalized_dept = {
                    'id': int(dept_id),
                    'nameEng': name_eng,
                    'isWing': bool(dept.get('isWing', False)),
                    'sync_timestamp': timezone.now().isoformat()
                }
                
                validated.append(normalized_dept)
                
                if self.verbose:
                    wing_indicator = " (Wing)" if normalized_dept['isWing'] else ""
                    self.stdout.write(f"  ✅ {normalized_dept['nameEng']}{wing_indicator}")
                
            except (ValueError, TypeError) as e:
                invalid_count += 1
                if self.verbose:
                    self.stdout.write(
                        self.style.WARNING(f"⚠️  Invalid department data: {dept} - {e}")
                    )
                continue
        
        if invalid_count > 0:
            self.stdout.write(
                self.style.WARNING(f"⚠️  Skipped {invalid_count} invalid departments")
            )
        
        self.stdout.write(f"✅ Validated {len(validated)} departments")
        return validated
    
    def _validate_cached_departments(self) -> int:
        """Validate cached department data."""
        self.stdout.write("🔍 Validating cached department data...")
        
        cached_departments = cache.get(DEPARTMENT_CACHE_KEY)
        last_sync = cache.get(DEPARTMENT_LAST_SYNC_KEY)
        
        if not cached_departments:
            self.stdout.write(self.style.WARNING("⚠️  No departments found in cache"))
            return 1
        
        if not last_sync:
            self.stdout.write(self.style.WARNING("⚠️  No sync timestamp found in cache"))
        else:
            age = timezone.now() - last_sync
            self.stdout.write(f"📅 Last sync: {last_sync.strftime('%Y-%m-%d %H:%M:%S %Z')}")
            self.stdout.write(f"⏰ Cache age: {age}")
        
        # Validate structure
        valid_count = 0
        for dept in cached_departments:
            if (isinstance(dept, dict) and 
                dept.get('id') and 
                dept.get('nameEng')):
                valid_count += 1
        
        self.stdout.write(f"✅ Found {valid_count} valid departments in cache")
        self.stdout.write(f"📦 Total departments in cache: {len(cached_departments)}")
        
        if valid_count == len(cached_departments):
            self.stdout.write(self.style.SUCCESS("✅ All cached departments are valid"))
            return 0
        else:
            invalid_count = len(cached_departments) - valid_count
            self.stdout.write(
                self.style.WARNING(f"⚠️  {invalid_count} invalid departments in cache")
            )
            return 1
    
    def _export_departments(self, departments: List[Dict[str, Any]], export_path: str):
        """Export departments to JSON file."""
        try:
            export_file = Path(export_path)
            export_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Prepare export data
            export_data = {
                'metadata': {
                    'export_timestamp': timezone.now().isoformat(),
                    'location': 'Bangladesh Parliament Secretariat, Dhaka',
                    'total_departments': len(departments),
                    'source': 'PRP API - https://prp.parliament.gov.bd'
                },
                'departments': departments
            }
            
            # Write to file
            with open(export_file, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
            
            self.stdout.write(
                self.style.SUCCESS(f"📁 Departments exported to: {export_file.absolute()}")
            )
            
        except Exception as e:
            self.stderr.write(
                self.style.ERROR(f"❌ Failed to export departments: {e}")
            )
    
    def _clear_cache(self):
        """Clear department cache."""
        cache.delete(DEPARTMENT_CACHE_KEY)
        cache.delete(DEPARTMENT_LAST_SYNC_KEY)
        self.stdout.write(self.style.SUCCESS("🗑️  Department cache cleared"))
    
    def _display_results(self, departments: List[Dict[str, Any]]):
        """Display sync operation results."""
        self.stdout.write("\n" + "=" * 80)
        self.stdout.write(self.style.SUCCESS("📊 DEPARTMENT SYNC RESULTS"))
        self.stdout.write("=" * 80)
        
        # Summary statistics
        total_depts = len(departments)
        wing_count = sum(1 for dept in departments if dept.get('isWing', False))
        regular_count = total_depts - wing_count
        
        self.stdout.write(f"📈 Department Statistics:")
        self.stdout.write(f"  • Total Departments: {self.style.SUCCESS(str(total_depts))}")
        self.stdout.write(f"  • Regular Departments: {regular_count}")
        self.stdout.write(f"  • Wings: {wing_count}")
        
        # Department listing (first 10)
        if departments and self.verbose:
            self.stdout.write(f"\n🏢 Department List (showing first 10):")
            for dept in departments[:10]:
                wing_indicator = " [Wing]" if dept.get('isWing') else ""
                name_display = dept.get('nameEng', 'Unknown')
                dept_id = dept.get('id', 'N/A')
                self.stdout.write(f"  • ID {dept_id}: {name_display}{wing_indicator}")
            
            if total_depts > 10:
                self.stdout.write(f"  • ... and {total_depts - 10} more departments")
        
        # Cache status
        if not self.dry_run:
            cache_expiry = DEPARTMENT_CACHE_TIMEOUT / 3600  # hours
            self.stdout.write(f"\n💾 Cache Status:")
            self.stdout.write(f"  • Cached: {self.style.SUCCESS('Yes')}")
            self.stdout.write(f"  • Expires in: {cache_expiry} hours")
        else:
            self.stdout.write(f"\n💾 Cache Status: {self.style.WARNING('Not cached (dry run)')}")
        
        # Usage information
        self.stdout.write(f"\n💡 Usage Information:")
        self.stdout.write("  • These departments support user.office field mapping")
        self.stdout.write("  • Used during PRP user synchronization operations")  
        self.stdout.write("  • Data Mapping: PRP department.nameEng → PIMS user.office")
        self.stdout.write("  • Only nameEng, id, isWing fields are used for PIMS integration")
        
        # Location and time context
        dhaka_time = timezone.now().astimezone(timezone.get_default_timezone())
        self.stdout.write(f"\n📍 Completed at: {dhaka_time.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        self.stdout.write("🇧🇩 Bangladesh Parliament Secretariat, Dhaka")
        
        self.stdout.write("=" * 80)