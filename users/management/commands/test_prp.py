"""
Django Management Command: Test PRP Connection
==============================================
Simple debug tool to test PRP API connectivity

Usage: python manage.py test_prp
"""

import requests
import json
from django.core.management.base import BaseCommand
from django.conf import settings


class Command(BaseCommand):
    help = 'Test PRP API connection and authentication'
    
    def handle(self, *args, **options):
        self.stdout.write('🔍 Testing PRP Connection...')
        self.stdout.write(f'📍 Location: Bangladesh Parliament Secretariat, Dhaka')
        self.stdout.write('-' * 60)
        
        # Test 1: Basic connectivity
        self.test_basic_connectivity()
        
        # Test 2: Authentication
        self.test_authentication()
        
        # Test 3: Department endpoint
        self.test_department_endpoint()
        
    def test_basic_connectivity(self):
        """Test basic network connectivity to PRP server."""
        self.stdout.write('1️⃣ Testing basic connectivity...')
        
        try:
            base_url = getattr(settings, 'PRP_API_SETTINGS', {}).get('BASE_URL', 'https://prp.parliament.gov.bd')
            response = requests.get(base_url, timeout=10)
            
            self.stdout.write(f'   URL: {base_url}')
            self.stdout.write(f'   Status: {response.status_code}')
            self.stdout.write(f'   ✅ Basic connectivity: OK')
            
        except requests.exceptions.ConnectionError:
            self.stdout.write(f'   ❌ Connection failed: Cannot reach PRP server')
            self.stdout.write(f'   💡 Check: Network connection, VPN, or firewall')
        except requests.exceptions.Timeout:
            self.stdout.write(f'   ❌ Timeout: Server took too long to respond')
        except Exception as e:
            self.stdout.write(f'   ❌ Error: {str(e)}')
    
    def test_authentication(self):
        """Test PRP authentication endpoint."""
        self.stdout.write('\n2️⃣ Testing authentication...')
        
        try:
            prp_settings = getattr(settings, 'PRP_API_SETTINGS', {})
            base_url = prp_settings.get('BASE_URL', 'https://prp.parliament.gov.bd')
            username = prp_settings.get('AUTH_USERNAME', 'ezzetech')
            password = prp_settings.get('AUTH_PASSWORD', '${Fty#3a')
            
            auth_url = f"{base_url}/api/authentication/external"
            auth_payload = {
                "username": username,
                "password": password
            }
            params = {"action": "token"}
            
            self.stdout.write(f'   Auth URL: {auth_url}')
            self.stdout.write(f'   Username: {username}')
            self.stdout.write(f'   Password: {"*" * len(password)}')
            
            response = requests.post(
                auth_url,
                params=params,
                json=auth_payload,
                timeout=30
            )
            
            self.stdout.write(f'   Status: {response.status_code}')
            
            if response.status_code == 200:
                data = response.json()
                self.stdout.write(f'   Response: {json.dumps(data, indent=2)}')
                
                if data.get('responseCode') == 200:
                    token = data.get('payload', '')
                    self.stdout.write(f'   ✅ Authentication: SUCCESS')
                    self.stdout.write(f'   🔑 Token received: {len(token)} characters')
                    return token
                else:
                    self.stdout.write(f'   ❌ Authentication failed: {data.get("msg", "Unknown error")}')
            else:
                self.stdout.write(f'   ❌ HTTP Error: {response.status_code}')
                self.stdout.write(f'   Response: {response.text}')
                
        except Exception as e:
            self.stdout.write(f'   ❌ Authentication error: {str(e)}')
        
        return None
    
    def test_department_endpoint(self):
        """Test department endpoint with authentication."""
        self.stdout.write('\n3️⃣ Testing department endpoint...')
        
        # First get token
        token = self.test_authentication()
        if not token:
            self.stdout.write('   ⚠️  Skipping department test - no valid token')
            return
        
        try:
            prp_settings = getattr(settings, 'PRP_API_SETTINGS', {})
            base_url = prp_settings.get('BASE_URL', 'https://prp.parliament.gov.bd')
            
            dept_url = f"{base_url}/api/secure/external"
            params = {"action": "departments"}
            headers = {"Authorization": f"Bearer {token}"}
            
            self.stdout.write(f'   Dept URL: {dept_url}')
            self.stdout.write(f'   Token: {token[:20]}...')
            
            response = requests.get(
                dept_url,
                params=params,
                headers=headers,
                timeout=30
            )
            
            self.stdout.write(f'   Status: {response.status_code}')
            
            if response.status_code == 200:
                data = response.json()
                departments = data.get('payload', [])
                self.stdout.write(f'   ✅ Departments: Found {len(departments)} departments')
                
                # Show first few departments
                for i, dept in enumerate(departments[:3]):
                    name = dept.get('nameEng', dept.get('name', 'No name'))
                    self.stdout.write(f'      {i+1}. {name}')
                
            else:
                self.stdout.write(f'   ❌ HTTP Error: {response.status_code}')
                self.stdout.write(f'   Response: {response.text}')
                
        except Exception as e:
            self.stdout.write(f'   ❌ Department test error: {str(e)}')
