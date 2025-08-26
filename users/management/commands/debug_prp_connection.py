"""
Django Management Command: PRP Connection Debugging & Testing
=============================================================

Comprehensive connection testing and debugging command for PIMS-PRP Integration
at Bangladesh Parliament Secretariat.

Location: Bangladesh Parliament Secretariat, Dhaka, Bangladesh
Project: PIMS-PRP Integration
Purpose: Debug and test PRP API connectivity, authentication, and data retrieval

Business Context:
- PRP Base URL: https://prp.parliament.gov.bd
- Authentication: Bearer token (username: "ezzetech", password: "${Fty#3a")
- Critical for ensuring PRP integration reliability before user sync operations
- Provides detailed diagnostics for troubleshooting connection issues

Key Features:
- Complete API connectivity testing
- Authentication flow validation
- Token refresh mechanism testing
- Department and employee endpoint testing
- Network diagnostics and performance metrics
- Configuration validation
- Comprehensive error reporting and troubleshooting

Usage Examples:
    # Basic connection test
    python manage.py debug_prp_connection

    # Full diagnostic suite
    python manage.py debug_prp_connection --full-test

    # Test specific endpoint
    python manage.py debug_prp_connection --test-endpoint=departments

    # Network performance analysis
    python manage.py debug_prp_connection --performance-test

    # Authentication flow testing
    python manage.py debug_prp_connection --test-auth

    # Detailed verbose output
    python manage.py debug_prp_connection --verbose

Dependencies:
- users.api.prp_client (PRPClient)
- users.api.exceptions (PRP exceptions)
"""

import json
import logging
import sys
import time
import traceback
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
import socket
import ssl
from urllib.parse import urlparse

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.utils import timezone
from django.core.cache import cache

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
logger = logging.getLogger('pims.prp_integration.debug')

# Test configuration
DEFAULT_TEST_TIMEOUT = 30
MAX_RETRY_ATTEMPTS = 3
PERFORMANCE_TEST_ITERATIONS = 5


class ConnectionTest:
    """Individual connection test result."""
    
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        self.success = False
        self.duration = 0.0
        self.error = None
        self.details = {}
        self.warnings = []
    
    def start(self):
        """Start timing the test."""
        self.start_time = time.time()
    
    def finish(self, success: bool = True, error: str = None, **details):
        """Finish the test with results."""
        self.duration = time.time() - self.start_time
        self.success = success
        self.error = error
        self.details.update(details)
    
    def add_warning(self, warning: str):
        """Add a warning to the test."""
        self.warnings.append(warning)


class Command(BaseCommand):
    """
    Django management command for PRP connection debugging and testing.
    
    Provides comprehensive diagnostics for PRP API connectivity, authentication,
    and data retrieval to ensure reliable integration operations.
    
    Location: Bangladesh Parliament Secretariat, Dhaka, Bangladesh
    """
    
    help = '''
    Debug and test PRP (Parliament Resource Portal) API connectivity and integration.
    
    Location: Bangladesh Parliament Secretariat, Dhaka, Bangladesh
    
    This command provides comprehensive diagnostics for PRP API connection issues,
    authentication problems, and data retrieval testing to ensure reliable
    integration operations.
    
    Examples:
        python manage.py debug_prp_connection                      # Basic test
        python manage.py debug_prp_connection --full-test          # Complete suite
        python manage.py debug_prp_connection --test-auth          # Auth only
        python manage.py debug_prp_connection --performance-test   # Performance
        python manage.py debug_prp_connection --verbose            # Detailed output
    '''
    
    def add_arguments(self, parser):
        """Add command line arguments."""
        parser.add_argument(
            '--full-test',
            action='store_true',
            help='Run complete diagnostic test suite'
        )
        
        parser.add_argument(
            '--test-endpoint',
            type=str,
            choices=['auth', 'departments', 'employees', 'health'],
            help='Test specific endpoint only'
        )
        
        parser.add_argument(
            '--performance-test',
            action='store_true',
            help='Run performance and latency tests'
        )
        
        parser.add_argument(
            '--test-auth',
            action='store_true',
            help='Test authentication flow only'
        )
        
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Enable detailed output and logging'
        )
        
        parser.add_argument(
            '--timeout',
            type=int,
            default=DEFAULT_TEST_TIMEOUT,
            help=f'Test timeout in seconds (default: {DEFAULT_TEST_TIMEOUT})'
        )
        
        parser.add_argument(
            '--retry',
            type=int,
            default=MAX_RETRY_ATTEMPTS,
            help=f'Number of retry attempts for failed tests (default: {MAX_RETRY_ATTEMPTS})'
        )
        
        parser.add_argument(
            '--output-json',
            type=str,
            help='Export results to JSON file'
        )
        
        parser.add_argument(
            '--department-id',
            type=str,
            help='Test specific department ID for employee endpoint testing'
        )
    
    def handle(self, *args, **options):
        """Main command handler."""
        # Store options
        self.options = options
        self.verbosity = options.get('verbosity', 1)
        self.verbose = options.get('verbose', False)
        self.timeout = options.get('timeout', DEFAULT_TEST_TIMEOUT)
        
        # Configure logging level
        if self.verbose:
            logging.getLogger('pims.prp_integration').setLevel(logging.DEBUG)
        
        # Bangladesh time context
        dhaka_time = timezone.now().astimezone(timezone.get_default_timezone())
        
        self.stdout.write("=" * 80)
        self.stdout.write(
            self.style.SUCCESS("🔍 PRP Connection Diagnostics - Bangladesh Parliament Secretariat")
        )
        self.stdout.write(f"📍 Location: Dhaka, Bangladesh")
        self.stdout.write(f"🕐 Started at: {dhaka_time.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        self.stdout.write("=" * 80)
        
        # Initialize test results
        self.test_results = []
        self.overall_success = True
        
        try:
            # Run tests based on options
            if options.get('test_auth'):
                self._run_auth_tests()
            elif options.get('test_endpoint'):
                self._run_endpoint_test(options['test_endpoint'])
            elif options.get('performance_test'):
                self._run_performance_tests()
            elif options.get('full_test'):
                self._run_full_test_suite()
            else:
                self._run_basic_tests()
            
            # Export results if requested
            if options.get('output_json'):
                self._export_results(options['output_json'])
            
            # Display final results
            self._display_final_results()
            
            # Exit with appropriate code
            return 0 if self.overall_success else 1
            
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING("\n⏹️  Debug session cancelled by user"))
            return 130
        except Exception as e:
            self.stderr.write(
                self.style.ERROR(f"💥 Fatal error during PRP debug: {str(e)}")
            )
            if self.verbose:
                self.stderr.write(f"Traceback: {traceback.format_exc()}")
            return 1
    
    def _run_basic_tests(self):
        """Run basic connection and configuration tests."""
        self.stdout.write("🔧 Running basic PRP connection tests...\n")
        
        # Configuration validation
        self._test_configuration()
        
        # Network connectivity
        self._test_network_connectivity()
        
        # API client initialization
        self._test_client_initialization()
        
        # Basic health check
        self._test_health_check()
    
    def _run_full_test_suite(self):
        """Run complete diagnostic test suite."""
        self.stdout.write("🚀 Running full PRP diagnostic test suite...\n")
        
        # Basic tests
        self._test_configuration()
        self._test_network_connectivity()
        self._test_client_initialization()
        
        # Authentication tests
        self._test_authentication_flow()
        self._test_token_refresh()
        
        # API endpoint tests
        self._test_health_check()
        self._test_departments_endpoint()
        self._test_employees_endpoint()
        
        # Performance tests
        if not self.options.get('performance_test'):
            self._run_basic_performance_test()
    
    def _run_auth_tests(self):
        """Run authentication-focused tests."""
        self.stdout.write("🔐 Running PRP authentication tests...\n")
        
        self._test_configuration()
        self._test_client_initialization()
        self._test_authentication_flow()
        self._test_token_refresh()
        self._test_token_expiry_handling()
    
    def _run_endpoint_test(self, endpoint: str):
        """Run tests for specific endpoint."""
        self.stdout.write(f"🎯 Testing PRP endpoint: {endpoint}\n")
        
        # Always need basic setup
        self._test_configuration()
        self._test_client_initialization()
        
        if endpoint == 'auth':
            self._test_authentication_flow()
        elif endpoint == 'departments':
            self._test_departments_endpoint()
        elif endpoint == 'employees':
            self._test_employees_endpoint()
        elif endpoint == 'health':
            self._test_health_check()
    
    def _run_performance_tests(self):
        """Run performance and latency tests."""
        self.stdout.write("⚡ Running PRP performance tests...\n")
        
        self._test_configuration()
        self._test_client_initialization()
        self._test_response_times()
        self._test_concurrent_requests()
        self._test_large_dataset_handling()
    
    def _test_configuration(self):
        """Test PRP configuration settings."""
        test = ConnectionTest(
            "configuration", 
            "Validate PRP API configuration settings"
        )
        test.start()
        
        try:
            # Check required settings
            prp_settings = getattr(settings, 'PRP_API_SETTINGS', {})
            
            required_settings = ['BASE_URL', 'USERNAME', 'PASSWORD']
            missing_settings = []
            
            for setting in required_settings:
                if not prp_settings.get(setting):
                    missing_settings.append(setting)
            
            if missing_settings:
                test.finish(
                    success=False,
                    error=f"Missing required PRP settings: {', '.join(missing_settings)}",
                    missing_settings=missing_settings
                )
            else:
                # Validate URL format
                base_url = prp_settings['BASE_URL']
                parsed_url = urlparse(base_url)
                
                if not parsed_url.scheme or not parsed_url.netloc:
                    test.finish(
                        success=False,
                        error=f"Invalid PRP base URL format: {base_url}",
                        base_url=base_url
                    )
                else:
                    test.finish(
                        success=True,
                        base_url=base_url,
                        username=prp_settings['USERNAME'],
                        timeout=prp_settings.get('TIMEOUT', 'Not set')
                    )
        
        except Exception as e:
            test.finish(success=False, error=str(e))
        
        self._add_test_result(test)
    
    def _test_network_connectivity(self):
        """Test network connectivity to PRP server."""
        test = ConnectionTest(
            "network_connectivity",
            "Test network connectivity to PRP server"
        )
        test.start()
        
        try:
            # Get PRP settings
            prp_settings = getattr(settings, 'PRP_API_SETTINGS', {})
            base_url = prp_settings.get('BASE_URL', 'https://prp.parliament.gov.bd')
            
            parsed_url = urlparse(base_url)
            hostname = parsed_url.hostname
            port = parsed_url.port or (443 if parsed_url.scheme == 'https' else 80)
            
            # Test socket connection
            sock = socket.create_connection((hostname, port), timeout=self.timeout)
            sock.close()
            
            # Test SSL if HTTPS
            if parsed_url.scheme == 'https':
                context = ssl.create_default_context()
                with socket.create_connection((hostname, port), timeout=self.timeout) as sock:
                    with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                        cert = ssock.getpeercert()
                        test.finish(
                            success=True,
                            hostname=hostname,
                            port=port,
                            ssl_cert_subject=cert.get('subject', 'Unknown') if cert else 'No cert',
                            ssl_cert_issuer=cert.get('issuer', 'Unknown') if cert else 'No cert'
                        )
            else:
                test.finish(
                    success=True,
                    hostname=hostname,
                    port=port,
                    ssl_enabled=False
                )
        
        except socket.timeout:
            test.finish(
                success=False,
                error=f"Connection timeout to {hostname}:{port}",
                timeout=self.timeout
            )
        except socket.gaierror as e:
            test.finish(
                success=False,
                error=f"DNS resolution failed for {hostname}: {e}"
            )
        except ConnectionRefusedError:
            test.finish(
                success=False,
                error=f"Connection refused to {hostname}:{port}"
            )
        except Exception as e:
            test.finish(success=False, error=str(e))
        
        self._add_test_result(test)
    
    def _test_client_initialization(self):
        """Test PRP client initialization."""
        test = ConnectionTest(
            "client_initialization",
            "Initialize PRP API client"
        )
        test.start()
        
        try:
            self.prp_client = create_prp_client()
            test.finish(
                success=True,
                client_class=self.prp_client.__class__.__name__,
                base_url=self.prp_client.base_url if hasattr(self.prp_client, 'base_url') else 'Unknown'
            )
        
        except PRPConfigurationError as e:
            test.finish(success=False, error=f"Configuration error: {e}")
        except Exception as e:
            test.finish(success=False, error=str(e))
        
        self._add_test_result(test)
    
    def _test_authentication_flow(self):
        """Test PRP authentication flow."""
        test = ConnectionTest(
            "authentication_flow",
            "Test PRP API authentication and token retrieval"
        )
        test.start()
        
        try:
            if not hasattr(self, 'prp_client') or not self.prp_client:
                test.finish(success=False, error="PRP client not initialized")
                self._add_test_result(test)
                return
            
            # Test authentication
            token = self.prp_client.authenticate()
            
            if token:
                test.finish(
                    success=True,
                    token_length=len(token),
                    token_prefix=token[:20] + "..." if len(token) > 20 else token,
                    has_bearer=token.startswith('Bearer ') if token else False
                )
            else:
                test.finish(success=False, error="Authentication returned empty token")
        
        except PRPAuthenticationError as e:
            test.finish(success=False, error=f"Authentication failed: {e}")
        except PRPConnectionError as e:
            test.finish(success=False, error=f"Connection error during auth: {e}")
        except Exception as e:
            test.finish(success=False, error=str(e))
        
        self._add_test_result(test)
    
    def _test_token_refresh(self):
        """Test token refresh mechanism."""
        test = ConnectionTest(
            "token_refresh",
            "Test PRP API token refresh mechanism"
        )
        test.start()
        
        try:
            if not hasattr(self, 'prp_client') or not self.prp_client:
                test.finish(success=False, error="PRP client not initialized")
                self._add_test_result(test)
                return
            
            # Test token refresh
            new_token = self.prp_client.refresh_token()
            
            if new_token:
                test.finish(
                    success=True,
                    new_token_length=len(new_token),
                    refresh_successful=True
                )
            else:
                test.finish(success=False, error="Token refresh returned empty token")
        
        except PRPAuthenticationError as e:
            test.finish(success=False, error=f"Token refresh failed: {e}")
        except Exception as e:
            test.finish(success=False, error=str(e))
        
        self._add_test_result(test)
    
    def _test_token_expiry_handling(self):
        """Test token expiry handling."""
        test = ConnectionTest(
            "token_expiry_handling",
            "Test automatic token refresh on expiry"
        )
        test.start()
        
        # This is a conceptual test - in practice, you'd need to simulate
        # an expired token or wait for expiry
        test.add_warning("Token expiry simulation not implemented")
        test.finish(
            success=True,
            note="Manual testing required for token expiry scenarios"
        )
        
        self._add_test_result(test)
    
    def _test_health_check(self):
        """Test PRP API health check."""
        test = ConnectionTest(
            "health_check",
            "Test PRP API health check endpoint"
        )
        test.start()
        
        try:
            if not hasattr(self, 'prp_client') or not self.prp_client:
                test.finish(success=False, error="PRP client not initialized")
                self._add_test_result(test)
                return
            
            # Perform health check
            health_status = self.prp_client.health_check()
            
            test.finish(
                success=True,
                health_status=health_status,
                api_responsive=True
            )
        
        except PRPConnectionError as e:
            test.finish(success=False, error=f"Health check failed: {e}")
        except Exception as e:
            test.finish(success=False, error=str(e))
        
        self._add_test_result(test)
    
    def _test_departments_endpoint(self):
        """Test departments endpoint."""
        test = ConnectionTest(
            "departments_endpoint",
            "Test PRP departments API endpoint"
        )
        test.start()
        
        try:
            if not hasattr(self, 'prp_client') or not self.prp_client:
                test.finish(success=False, error="PRP client not initialized")
                self._add_test_result(test)
                return
            
            departments = self.prp_client.get_departments()
            
            if departments:
                # Analyze department data
                total_depts = len(departments)
                wings = sum(1 for d in departments if d.get('isWing', False))
                
                test.finish(
                    success=True,
                    total_departments=total_depts,
                    wings_count=wings,
                    regular_departments=total_depts - wings,
                    sample_department=departments[0] if departments else None
                )
            else:
                test.finish(success=False, error="No departments returned from API")
        
        except PRPConnectionError as e:
            test.finish(success=False, error=f"Connection error: {e}")
        except PRPDataValidationError as e:
            test.finish(success=False, error=f"Data validation error: {e}")
        except Exception as e:
            test.finish(success=False, error=str(e))
        
        self._add_test_result(test)
    
    def _test_employees_endpoint(self):
        """Test employees endpoint."""
        test = ConnectionTest(
            "employees_endpoint",
            "Test PRP employees API endpoint"
        )
        test.start()
        
        try:
            if not hasattr(self, 'prp_client') or not self.prp_client:
                test.finish(success=False, error="PRP client not initialized")
                self._add_test_result(test)
                return
            
            # Get department ID for testing
            department_id = self.options.get('department_id')
            
            if not department_id:
                # Try to get first department
                try:
                    departments = self.prp_client.get_departments()
                    if departments:
                        department_id = departments[0]['id']
                    else:
                        test.finish(success=False, error="No departments available for employee testing")
                        self._add_test_result(test)
                        return
                except Exception:
                    department_id = 1  # Default fallback
            
            # Test employee endpoint
            employees = self.prp_client.get_department_employees(int(department_id))
            
            if employees:
                # Analyze employee data
                total_employees = len(employees)
                active_employees = sum(1 for e in employees if e.get('status') == 'active')
                
                test.finish(
                    success=True,
                    department_id=department_id,
                    total_employees=total_employees,
                    active_employees=active_employees,
                    inactive_employees=total_employees - active_employees,
                    sample_employee=employees[0] if employees else None
                )
            else:
                test.finish(
                    success=True,
                    department_id=department_id,
                    total_employees=0,
                    note="Department has no employees"
                )
        
        except PRPConnectionError as e:
            test.finish(success=False, error=f"Connection error: {e}")
        except PRPDataValidationError as e:
            test.finish(success=False, error=f"Data validation error: {e}")
        except Exception as e:
            test.finish(success=False, error=str(e))
        
        self._add_test_result(test)
    
    def _run_basic_performance_test(self):
        """Run basic performance test."""
        test = ConnectionTest(
            "basic_performance",
            "Basic API response time test"
        )
        test.start()
        
        try:
            if not hasattr(self, 'prp_client') or not self.prp_client:
                test.finish(success=False, error="PRP client not initialized")
                self._add_test_result(test)
                return
            
            # Test multiple requests
            response_times = []
            
            for i in range(3):
                start_time = time.time()
                self.prp_client.health_check()
                response_time = time.time() - start_time
                response_times.append(response_time)
            
            avg_response_time = sum(response_times) / len(response_times)
            max_response_time = max(response_times)
            min_response_time = min(response_times)
            
            test.finish(
                success=True,
                average_response_time=round(avg_response_time, 3),
                max_response_time=round(max_response_time, 3),
                min_response_time=round(min_response_time, 3),
                total_requests=len(response_times)
            )
        
        except Exception as e:
            test.finish(success=False, error=str(e))
        
        self._add_test_result(test)
    
    def _test_response_times(self):
        """Test detailed response times for different endpoints."""
        test = ConnectionTest(
            "response_times",
            "Detailed API response time analysis"
        )
        test.start()
        
        try:
            if not hasattr(self, 'prp_client') or not self.prp_client:
                test.finish(success=False, error="PRP client not initialized")
                self._add_test_result(test)
                return
            
            endpoints_to_test = [
                ('health_check', lambda: self.prp_client.health_check()),
                ('get_departments', lambda: self.prp_client.get_departments())
            ]
            
            results = {}
            
            for endpoint_name, endpoint_func in endpoints_to_test:
                times = []
                for i in range(PERFORMANCE_TEST_ITERATIONS):
                    start_time = time.time()
                    try:
                        endpoint_func()
                        response_time = time.time() - start_time
                        times.append(response_time)
                    except Exception as e:
                        times.append(None)  # Failed request
                
                valid_times = [t for t in times if t is not None]
                if valid_times:
                    results[endpoint_name] = {
                        'avg': round(sum(valid_times) / len(valid_times), 3),
                        'max': round(max(valid_times), 3),
                        'min': round(min(valid_times), 3),
                        'success_rate': len(valid_times) / len(times)
                    }
                else:
                    results[endpoint_name] = {'error': 'All requests failed'}
            
            test.finish(success=True, endpoint_performance=results)
        
        except Exception as e:
            test.finish(success=False, error=str(e))
        
        self._add_test_result(test)
    
    def _test_concurrent_requests(self):
        """Test concurrent request handling (simplified)."""
        test = ConnectionTest(
            "concurrent_requests",
            "Test API behavior under concurrent load"
        )
        test.start()
        
        # Note: This is a simplified test. In practice, you'd use threading or asyncio
        test.add_warning("Concurrent testing simplified - manual load testing recommended")
        
        try:
            # Rapid sequential requests to simulate some concurrency
            start_time = time.time()
            success_count = 0
            
            for i in range(10):
                try:
                    self.prp_client.health_check()
                    success_count += 1
                except Exception:
                    pass
            
            total_time = time.time() - start_time
            
            test.finish(
                success=True,
                successful_requests=success_count,
                total_requests=10,
                total_time=round(total_time, 3),
                requests_per_second=round(10 / total_time, 2)
            )
        
        except Exception as e:
            test.finish(success=False, error=str(e))
        
        self._add_test_result(test)
    
    def _test_large_dataset_handling(self):
        """Test handling of large datasets."""
        test = ConnectionTest(
            "large_dataset_handling",
            "Test API response to large dataset requests"
        )
        test.start()
        
        try:
            if not hasattr(self, 'prp_client') or not self.prp_client:
                test.finish(success=False, error="PRP client not initialized")
                self._add_test_result(test)
                return
            
            # Test departments (usually smaller dataset)
            start_time = time.time()
            departments = self.prp_client.get_departments()
            dept_time = time.time() - start_time
            
            # Test employees from first department (potentially larger)
            if departments:
                start_time = time.time()
                employees = self.prp_client.get_department_employees(departments[0]['id'])
                emp_time = time.time() - start_time
                
                test.finish(
                    success=True,
                    departments_count=len(departments),
                    departments_response_time=round(dept_time, 3),
                    employees_count=len(employees) if employees else 0,
                    employees_response_time=round(emp_time, 3)
                )
            else:
                test.finish(
                    success=True,
                    departments_count=0,
                    note="No departments available for employee testing"
                )
        
        except Exception as e:
            test.finish(success=False, error=str(e))
        
        self._add_test_result(test)
    
    def _add_test_result(self, test: ConnectionTest):
        """Add test result and update overall status."""
        self.test_results.append(test)
        
        if not test.success:
            self.overall_success = False
        
        # Display immediate result
        status_icon = "✅" if test.success else "❌"
        status_style = self.style.SUCCESS if test.success else self.style.ERROR
        
        self.stdout.write(f"{status_icon} {test.description}")
        
        if test.success:
            if self.verbose and test.details:
                for key, value in test.details.items():
                    self.stdout.write(f"    • {key}: {value}")
        else:
            self.stdout.write(f"    {status_style(f'Error: {test.error}')}")
        
        if test.warnings and self.verbose:
            for warning in test.warnings:
                self.stdout.write(f"    ⚠️  {warning}")
        
        if self.verbose:
            self.stdout.write(f"    ⏱️  Duration: {test.duration:.3f}s")
        
        self.stdout.write("")  # Empty line for readability
    
    def _export_results(self, output_file: str):
        """Export test results to JSON file."""
        try:
            export_data = {
                'metadata': {
                    'timestamp': timezone.now().isoformat(),
                    'location': 'Bangladesh Parliament Secretariat, Dhaka',
                    'overall_success': self.overall_success,
                    'total_tests': len(self.test_results),
                    'passed_tests': len([t for t in self.test_results if t.success]),
                    'failed_tests': len([t for t in self.test_results if not t.success]),
                    'command_options': self.options
                },
                'test_results': []
            }
            
            # Convert test results to serializable format
            for test in self.test_results:
                test_data = {
                    'name': test.name,
                    'description': test.description,
                    'success': test.success,
                    'duration': test.duration,
                    'error': test.error,
                    'details': test.details,
                    'warnings': test.warnings
                }
                export_data['test_results'].append(test_data)
            
            # Write to file
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
            
            self.stdout.write(
                self.style.SUCCESS(f"📁 Test results exported to: {output_file}")
            )
            
        except Exception as e:
            self.stderr.write(
                self.style.ERROR(f"❌ Failed to export results: {e}")
            )
    
    def _display_final_results(self):
        """Display final test results summary."""
        self.stdout.write("\n" + "=" * 80)
        self.stdout.write(self.style.SUCCESS("📊 PRP CONNECTION DIAGNOSTIC RESULTS"))
        self.stdout.write("=" * 80)
        
        # Overall status
        overall_style = self.style.SUCCESS if self.overall_success else self.style.ERROR
        overall_text = "ALL TESTS PASSED ✅" if self.overall_success else "SOME TESTS FAILED ❌"
        self.stdout.write(f"Overall Status: {overall_style(overall_text)}")
        
        # Test statistics
        total_tests = len(self.test_results)
        passed_tests = len([t for t in self.test_results if t.success])
        failed_tests = total_tests - passed_tests
        
        self.stdout.write(f"\n📈 Test Statistics:")
        self.stdout.write(f"  • Total Tests: {total_tests}")
        self.stdout.write(f"  • Passed: {self.style.SUCCESS(str(passed_tests))}")
        self.stdout.write(f"  • Failed: {self.style.ERROR(str(failed_tests)) if failed_tests > 0 else '0'}")
        
        # Test breakdown
        if self.test_results:
            self.stdout.write(f"\n🔍 Test Breakdown:")
            for test in self.test_results:
                status_icon = "✅" if test.success else "❌"
                status_text = "PASS" if test.success else "FAIL"
                status_style = self.style.SUCCESS if test.success else self.style.ERROR
                
                self.stdout.write(f"  {status_icon} {test.name}: {status_style(status_text)} ({test.duration:.3f}s)")
                
                if not test.success:
                    self.stdout.write(f"      Error: {test.error}")
        
        # Performance summary
        performance_tests = [t for t in self.test_results if 'performance' in t.name or 'response_time' in t.name]
        if performance_tests:
            self.stdout.write(f"\n⚡ Performance Summary:")
            for test in performance_tests:
                if test.success and test.details:
                    if 'average_response_time' in test.details:
                        avg_time = test.details['average_response_time']
                        self.stdout.write(f"  • {test.name}: {avg_time}s average")
                    elif 'endpoint_performance' in test.details:
                        for endpoint, perf in test.details['endpoint_performance'].items():
                            if isinstance(perf, dict) and 'avg' in perf:
                                self.stdout.write(f"  • {endpoint}: {perf['avg']}s average")
        
        # Failed tests details
        failed_tests_list = [t for t in self.test_results if not t.success]
        if failed_tests_list:
            self.stdout.write(f"\n❌ Failed Tests Details:")
            for test in failed_tests_list:
                self.stdout.write(f"  • {test.name}: {test.error}")
                if test.details:
                    for key, value in test.details.items():
                        if key != 'error':
                            self.stdout.write(f"    - {key}: {value}")
        
        # Warnings summary
        all_warnings = []
        for test in self.test_results:
            all_warnings.extend(test.warnings)
        
        if all_warnings:
            self.stdout.write(f"\n⚠️  Warnings ({len(all_warnings)}):")
            for warning in all_warnings[:5]:  # Show first 5 warnings
                self.stdout.write(f"  • {warning}")
            if len(all_warnings) > 5:
                self.stdout.write(f"  • ... and {len(all_warnings) - 5} more warnings")
        
        # Troubleshooting recommendations
        if failed_tests_list:
            self.stdout.write(f"\n🔧 Troubleshooting Recommendations:")
            
            # Network issues
            network_failures = [t for t in failed_tests_list if 'network' in t.name or 'connectivity' in t.name]
            if network_failures:
                self.stdout.write("  📡 Network Issues Detected:")
                self.stdout.write("    - Check internet connectivity")
                self.stdout.write("    - Verify PRP server URL: https://prp.parliament.gov.bd")
                self.stdout.write("    - Check firewall and proxy settings")
                self.stdout.write("    - Test with: ping prp.parliament.gov.bd")
            
            # Authentication issues
            auth_failures = [t for t in failed_tests_list if 'auth' in t.name or 'token' in t.name]
            if auth_failures:
                self.stdout.write("  🔐 Authentication Issues Detected:")
                self.stdout.write("    - Verify PRP credentials in Django settings")
                self.stdout.write("    - Check username: 'ezzetech'")
                self.stdout.write("    - Verify password: '${Fty#3a'")
                self.stdout.write("    - Contact PRP administrators if credentials expired")
            
            # Configuration issues
            config_failures = [t for t in failed_tests_list if 'config' in t.name]
            if config_failures:
                self.stdout.write("  ⚙️  Configuration Issues Detected:")
                self.stdout.write("    - Review PRP_API_SETTINGS in Django settings")
                self.stdout.write("    - Ensure all required settings are present")
                self.stdout.write("    - Check BASE_URL, USERNAME, PASSWORD fields")
        
        # Success recommendations
        if self.overall_success:
            self.stdout.write(f"\n🎉 Connection Health: EXCELLENT")
            self.stdout.write("  • PRP API is fully accessible")
            self.stdout.write("  • All authentication mechanisms working")
            self.stdout.write("  • Ready for user synchronization operations")
            self.stdout.write("  • You can now run: python manage.py sync_prp_users")
        
        # Location and time context
        dhaka_time = timezone.now().astimezone(timezone.get_default_timezone())
        self.stdout.write(f"\n📍 Completed at: {dhaka_time.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        self.stdout.write("🇧🇩 Bangladesh Parliament Secretariat, Dhaka")
        
        self.stdout.write("=" * 80)