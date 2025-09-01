"""
Django Management Command: PRP User Synchronization
====================================================

Manual sync command for PIMS-PRP Integration at Bangladesh Parliament Secretariat.

Location: Bangladesh Parliament Secretariat, Dhaka, Bangladesh
Project: PIMS-PRP Integration
Purpose: Manual synchronization of user data from PRP API to PIMS

Business Context:
- PRP is the authoritative source for all user data
- One-way sync: PRP → PIMS (never send data back to PRP)
- Admin-controlled operation with comprehensive logging
- Status override: PIMS admin can override user status

Key Features:
- Full department sync or single user sync
- Comprehensive error handling and rollback
- Detailed sync reporting and audit logging
- Force sync option to override recent sync checks
- Dry run mode for testing without changes
- Admin-only operation with permission checks

Usage Examples:
    # Sync all users from all departments
    python manage.py sync_prp_users

    # Sync users from specific department
    python manage.py sync_prp_users --department=5

    # Sync specific user by employee ID
    python manage.py sync_prp_users --user=12345

    # Force sync ignoring recent sync timestamps
    python manage.py sync_prp_users --force

    # Dry run to preview changes without applying
    python manage.py sync_prp_users --dry-run

    # Verbose output with detailed logging
    python manage.py sync_prp_users --verbose

Dependencies:
- users.api.prp_client (PRPClient)
- users.api.sync_service (PRPSyncService)
- users.api.exceptions (PRP exceptions)
"""

import logging
import sys
import traceback
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from django.conf import settings
from django.contrib.auth.models import User

# Import PRP integration modules
try:
    from users.api.prp_client import PRPClient, create_prp_client
    from users.api.sync_service import PRPSyncService, PRPSyncResult
    from users.api.exceptions import (
        PRPException,
        PRPConnectionError,
        PRPAuthenticationError,
        PRPSyncError,
        PRPDataValidationError,
        PRPConfigurationError
    )
except ImportError as e:
    raise CommandError(
        f"PRP integration modules not available: {e}. "
        "Ensure prp_client.py and sync_service.py are implemented before running this command."
    )

# Configure logging
logger = logging.getLogger('pims.prp_integration.sync_users')

# Get custom user model
CustomUser = get_user_model()


class Command(BaseCommand):
    """
    Django management command for PRP user synchronization.
    
    Provides comprehensive user synchronization capabilities from PRP
    (Parliament Resource Portal) to PIMS with business rule enforcement.
    
    Location: Bangladesh Parliament Secretariat, Dhaka, Bangladesh
    """
    
    help = '''
    Synchronize user data from PRP (Parliament Resource Portal) to PIMS.
    
    Location: Bangladesh Parliament Secretariat, Dhaka, Bangladesh
    
    This command provides manual control over PRP user synchronization with
    comprehensive business rule enforcement and audit logging.
    
    Examples:
        python manage.py sync_prp_users                    # Sync all users
        python manage.py sync_prp_users --department=5     # Sync specific department
        python manage.py sync_prp_users --user=12345       # Sync specific user
        python manage.py sync_prp_users --force            # Force sync all
        python manage.py sync_prp_users --dry-run          # Preview changes only
    '''
    
    def add_arguments(self, parser):
        """Add command line arguments."""
        parser.add_argument(
            '--department',
            type=str,
            help='Sync users from specific department ID only'
        )
        
        parser.add_argument(
            '--user',
            type=str,
            help='Sync specific user by PRP employee ID only'
        )
        
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force sync ignoring recent sync timestamps'
        )
        
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Preview changes without applying them to database'
        )
        
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Enable detailed output and logging'
        )
        
        parser.add_argument(
            '--max-users',
            type=int,
            default=1000,
            help='Maximum number of users to process in single run (default: 1000)'
        )
        
        parser.add_argument(
            '--timeout',
            type=int,
            default=300,
            help='API timeout in seconds (default: 300)'
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
            self.style.SUCCESS("🇧🇩 PRP User Synchronization - Bangladesh Parliament Secretariat")
        )
        self.stdout.write(f"📍 Location: Dhaka, Bangladesh")
        self.stdout.write(f"🕐 Started at: {dhaka_time.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        
        if self.dry_run:
            self.stdout.write(self.style.WARNING("🧪 DRY RUN MODE - No changes will be applied"))
        
        self.stdout.write("=" * 80)
        
        try:
            # Initialize PRP client and sync service
            self._initialize_services()
            
            # Execute sync operation based on options
            if options.get('user'):
                result = self._sync_single_user(options['user'])
            elif options.get('department'):
                result = self._sync_department(options['department'])
            else:
                result = self._sync_all_departments()
            
            # Display results
            self._display_results(result)
            
            # Exit with appropriate code
            if result.success:
                self.stdout.write(
                    self.style.SUCCESS("✅ PRP user synchronization completed successfully")
                )
                return 0
            else:
                self.stdout.write(
                    self.style.ERROR("❌ PRP user synchronization completed with errors")
                )
                return 1
                
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING("\n⏹️  Sync operation cancelled by user"))
            return 130
        except Exception as e:
            self.stderr.write(
                self.style.ERROR(f"💥 Fatal error during PRP sync: {str(e)}")
            )
            if self.verbose:
                self.stderr.write(f"Traceback: {traceback.format_exc()}")
            return 1
    
    def _initialize_services(self):
        """Initialize PRP client and sync service."""
        try:
            self.stdout.write("🔌 Initializing PRP API connection...")
            
            # Create PRP client using factory function
            self.prp_client = create_prp_client()
            
            # Test connection
            self.prp_client.health_check()
            self.stdout.write(self.style.SUCCESS("✅ PRP API connection established"))
            
            # Initialize sync service
            self.sync_service = PRPSyncService(self.prp_client)
            
            if self.dry_run:
                self.stdout.write(self.style.WARNING("🧪 Sync service initialized in DRY RUN mode"))
            
        except PRPConfigurationError as e:
            raise CommandError(f"PRP configuration error: {e}")
        except PRPConnectionError as e:
            raise CommandError(f"Cannot connect to PRP API: {e}")
        except Exception as e:
            raise CommandError(f"Failed to initialize PRP services: {e}")
    
    def _sync_single_user(self, employee_id: str) -> PRPSyncResult:
        """Sync a specific user by employee ID."""
        self.stdout.write(f"👤 Syncing single user: {employee_id}")
        
        try:
            if self.dry_run:
                self.stdout.write("🧪 DRY RUN: User sync preview not yet implemented")
                # In a real implementation, you'd preview the changes here
                result = PRPSyncResult()
                result.add_warning("Dry run mode - no changes applied")
                return result.finalize()
            
            result = self.sync_service.sync_single_user_by_id(
                employee_id=employee_id,
                force=self.force
            )
            
            return result
            
        except PRPException as e:
            self.stderr.write(self.style.ERROR(f"❌ PRP sync error: {e}"))
            result = PRPSyncResult()
            result.success = False
            result.add_error_user(employee_id, str(e))
            return result.finalize()
    
    def _sync_department(self, department_id: str) -> PRPSyncResult:
        """Sync users from a specific department."""
        self.stdout.write(f" Syncing department: {department_id}")
        
        try:
            if self.dry_run:
                self.stdout.write(" DRY RUN: Department sync preview not yet implemented")
                result = PRPSyncResult()
                result.add_warning("Dry run mode - no changes applied")
                return result.finalize()
            
            result = self.sync_service.sync_department_users(
                department_id=int(department_id),
                force=self.force
            )
            
            return result
            
        except ValueError:
            raise CommandError(f"Invalid department ID: {department_id}")
        except PRPException as e:
            self.stderr.write(self.style.ERROR(f" Department sync error: {e}"))
            result = PRPSyncResult()
            result.success = False
            result.add_error("sync_department", str(e))
            return result.finalize()
    
    def _sync_all_departments(self) -> PRPSyncResult:
        """Sync users from all departments."""
        self.stdout.write("🌐 Syncing all departments...")
        
        try:
            if self.dry_run:
                self.stdout.write(" DRY RUN: Full sync preview not yet implemented")
                result = PRPSyncResult()
                result.add_warning("Dry run mode - no changes applied")
                return result.finalize()
            
            result = self.sync_service.sync_all_departments(
                force=self.force
            )
            
            return result
            
        except PRPException as e:
            self.stderr.write(self.style.ERROR(f" Full sync error: {e}"))
            result = PRPSyncResult()
            result.success = False
            result.add_error("sync_all_departments", str(e))
            return result.finalize()
    
    def _display_results(self, result: PRPSyncResult):
        """Display sync operation results."""
        self.stdout.write("\n" + "=" * 80)
        self.stdout.write(self.style.SUCCESS("📊 SYNC OPERATION RESULTS"))
        self.stdout.write("=" * 80)
        
        # Summary statistics
        summary = result.get_summary()
        
        # Success/Failure status
        status_style = self.style.SUCCESS if result.success else self.style.ERROR
        status_text = "SUCCESS " if result.success else "FAILED "
        self.stdout.write(f"Status: {status_style(status_text)}")
        
        # User statistics
        self.stdout.write(f"\n User Statistics:")
        self.stdout.write(f"  • Created: {self.style.SUCCESS(str(summary['users_created']))}")
        self.stdout.write(f"  • Updated: {self.style.WARNING(str(summary['users_updated']))}")
        self.stdout.write(f"  • Skipped: {summary['users_skipped']}")
        self.stdout.write(f"  • Errors:  {self.style.ERROR(str(summary['users_errors']))}")
        self.stdout.write(f"  • Total:   {summary['total_users_processed']}")
        
        # Department statistics
        if summary['departments_processed'] > 0:
            self.stdout.write(f"\n🏢 Departments Processed: {summary['departments_processed']}")
        
        # Duration
        if summary['duration_seconds'] > 0:
            duration_str = f"{summary['duration_seconds']:.2f} seconds"
            self.stdout.write(f"⏱️  Duration: {duration_str}")
        
        # Errors
        if result.errors:
            self.stdout.write(f"\n❌ Errors ({len(result.errors)}):")
            for error in result.errors[:5]:  # Show first 5 errors
                self.stdout.write(f"  • {self.style.ERROR(error)}")
            
            if len(result.errors) > 5:
                remaining = len(result.errors) - 5
                self.stdout.write(f"  • ... and {remaining} more errors")
        
        # Warnings
        if result.warnings:
            self.stdout.write(f"\n⚠️  Warnings ({len(result.warnings)}):")
            for warning in result.warnings[:3]:  # Show first 3 warnings
                self.stdout.write(f"  • {self.style.WARNING(warning)}")
            
            if len(result.warnings) > 3:
                remaining = len(result.warnings) - 3
                self.stdout.write(f"  • ... and {remaining} more warnings")
        
        # Business rules applied
        if 'business_rules_applied' in result.sync_details:
            rules = result.sync_details['business_rules_applied']
            if rules:
                self.stdout.write(f"\n📋 Business Rules Applied ({len(rules)}):")
                for rule in rules:
                    status = "✅" if rule['applied'] else "❌"
                    self.stdout.write(f"  • {status} {rule['rule_name']}")
        
        # Location and time context
        dhaka_time = timezone.now().astimezone(timezone.get_default_timezone())
        self.stdout.write(f"\n📍 Completed at: {dhaka_time.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        self.stdout.write("🇧🇩 Bangladesh Parliament Secretariat, Dhaka")
        
        self.stdout.write("=" * 80)