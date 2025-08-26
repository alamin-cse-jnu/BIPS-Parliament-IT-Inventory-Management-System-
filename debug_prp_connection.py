#!/usr/bin/env python
"""
Debug PRP Client Connection
Location: Bangladesh Parliament Secretariat, Dhaka
Purpose: Test PRP API connectivity and authentication

Run this script to debug PRP connection issues:
python manage.py shell < debug_prp_connection.py
"""

import os
import django
import sys
from pathlib import Path

# Setup Django
sys.path.append(str(Path(__file__).resolve().parent))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pims.settings')
django.setup()

from django.conf import settings
import requests
import json

def debug_prp_connection():
    """Debug PRP API connection step by step."""
    
    print("🏛️  PRP Connection Debug - Bangladesh Parliament Secretariat, Dhaka")
    print("=" * 70)
    
    # Step 1: Check environment variables
    print("1️⃣  Environment Variables Check:")
    prp_vars = {
        'PRP_INTEGRATION_AVAILABLE': os.environ.get('PRP_INTEGRATION_AVAILABLE', 'Not Set'),
        'PRP_API_ENABLED': os.environ.get('PRP_API_ENABLED', 'Not Set'),
        'PRP_API_BASE_URL': os.environ.get('PRP_API_BASE_URL', 'Not Set'),
        'PRP_API_USERNAME': os.environ.get('PRP_API_USERNAME', 'Not Set'),
        'PRP_API_PASSWORD': '***HIDDEN***' if os.environ.get('PRP_API_PASSWORD') else 'Not Set',
    }
    
    for key, value in prp_vars.items():
        status = "✅" if value != 'Not Set' else "❌"
        print(f"   {status} {key}: {value}")
    
    # Step 2: Test basic network connectivity
    print(f"\n2️⃣  Network Connectivity Test:")
    base_url = os.environ.get('PRP_API_BASE_URL', 'https://prp.parliament.gov.bd')
    
    try:
        response = requests.get(base_url, timeout=10)
        print(f"   ✅ Base URL accessible: {base_url}")
        print(f"   📊 Status Code: {response.status_code}")
        print(f"   📏 Response Size: {len(response.content)} bytes")
    except requests.exceptions.Timeout:
        print(f"   ❌ Timeout connecting to: {base_url}")
        print(f"   💡 This might be a network issue or the server is slow")
    except requests.exceptions.ConnectionError:
        print(f"   ❌ Connection error to: {base_url}")
        print(f"   💡 Check your internet connection or VPN settings")
    except Exception as e:
        print(f"   ❌ Network error: {e}")
    
    # Step 3: Test PRP authentication endpoint
    print(f"\n3️⃣  PRP Authentication Test:")
    
    auth_url = f"{base_url}/api/authentication/external"
    username = os.environ.get('PRP_API_USERNAME', 'ezzetech')
    password = os.environ.get('PRP_API_PASSWORD', '${Fty#3a')
    
    print(f"   🔗 Auth URL: {auth_url}")
    print(f"   👤 Username: {username}")
    print(f"   🔒 Password: {'*' * len(password) if password else 'Not Set'}")
    
    try:
        auth_payload = {
            "action": "token",
            "username": username,
            "password": password
        }
        
        print(f"   📤 Sending authentication request...")
        
        response = requests.post(
            auth_url,
            json=auth_payload,
            headers={
                'Content-Type': 'application/json',
                'User-Agent': 'PIMS-PRP-Integration/1.0 (Bangladesh Parliament)'
            },
            timeout=30
        )
        
        print(f"   📊 Auth Response Status: {response.status_code}")
        print(f"   📏 Response Size: {len(response.content)} bytes")
        
        if response.status_code == 200:
            try:
                data = response.json()
                print(f"   📋 Response Structure: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")
                
                if data.get('responseCode') == 200:
                    print(f"   ✅ Authentication successful!")
                    token = data.get('payload', {}).get('token') if isinstance(data.get('payload'), dict) else None
                    if token:
                        print(f"   🎫 Token received: {token[:20]}...{token[-10:] if len(token) > 30 else token}")
                    else:
                        print(f"   ⚠️  No token in response payload")
                else:
                    print(f"   ❌ Authentication failed: {data.get('msg', 'Unknown error')}")
                    print(f"   📋 Full response: {json.dumps(data, indent=2)}")
                    
            except json.JSONDecodeError:
                print(f"   ❌ Invalid JSON response")
                print(f"   📄 Raw response: {response.text[:200]}...")
                
        else:
            print(f"   ❌ HTTP Error: {response.status_code}")
            print(f"   📄 Response: {response.text[:200]}...")
            
    except requests.exceptions.Timeout:
        print(f"   ❌ Authentication timeout (30s)")
        print(f"   💡 PRP API might be slow or overloaded")
    except requests.exceptions.ConnectionError:
        print(f"   ❌ Connection error during authentication")
        print(f"   💡 Network issue or PRP server down")
    except Exception as e:
        print(f"   ❌ Authentication error: {e}")
    
    # Step 4: Test Django PRP client creation
    print(f"\n4️⃣  Django PRP Client Test:")
    
    try:
        from users.api.prp_client import create_prp_client, PRPClient
        print(f"   ✅ PRP client modules imported")
        
        try:
            client = create_prp_client()
            print(f"   ✅ PRP client created successfully")
            print(f"   🔗 Client base URL: {client.base_url}")
            print(f"   👤 Client username: {client.username}")
            
            # Test authentication
            try:
                auth_result = client.authenticate()
                print(f"   {'✅' if auth_result else '❌'} Client authentication: {auth_result}")
                
                if auth_result:
                    print(f"   🎫 Client token: {client.token[:20] if client.token else 'None'}...")
                    
                    # Test a simple API call
                    try:
                        test_result = client.test_connection()
                        print(f"   {'✅' if test_result.get('success') else '❌'} Connection test: {test_result}")
                    except Exception as e:
                        print(f"   ❌ Connection test failed: {e}")
                        
            except Exception as e:
                print(f"   ❌ Client authentication failed: {e}")
                
        except Exception as e:
            print(f"   ❌ Client creation failed: {e}")
            import traceback
            print(f"   🔍 Traceback:")
            traceback.print_exc()
            
    except ImportError as e:
        print(f"   ❌ Import error: {e}")
        print(f"   💡 Check if users/api/prp_client.py exists and is properly implemented")
    
    # Step 5: Check Django settings integration
    print(f"\n5️⃣  Django Settings Integration:")
    
    try:
        prp_available = getattr(settings, 'PRP_INTEGRATION_AVAILABLE', False)
        print(f"   {'✅' if prp_available else '❌'} settings.PRP_INTEGRATION_AVAILABLE: {prp_available}")
        
        prp_settings = getattr(settings, 'PRP_API_SETTINGS', {})
        if prp_settings:
            print(f"   ✅ settings.PRP_API_SETTINGS found:")
            for key, value in prp_settings.items():
                if 'PASSWORD' in key or 'SECRET' in key:
                    value = f"{'*' * len(str(value))} chars" if value else 'Empty'
                print(f"      {key}: {value}")
        else:
            print(f"   ⚠️  settings.PRP_API_SETTINGS not found or empty")
            
    except Exception as e:
        print(f"   ❌ Settings check failed: {e}")
    
    print(f"\n" + "=" * 70)
    print(f"🔍 Debug Summary:")
    print(f"📍 Location: Bangladesh Parliament Secretariat, Dhaka")
    
    # Provide specific recommendations
    if os.environ.get('PRP_INTEGRATION_AVAILABLE', '').lower() != 'true':
        print(f"❌ PRP Integration is disabled - enable it in .env file")
    elif not os.environ.get('PRP_API_BASE_URL'):
        print(f"❌ PRP_API_BASE_URL not set in environment")
    elif not os.environ.get('PRP_API_USERNAME') or not os.environ.get('PRP_API_PASSWORD'):
        print(f"❌ PRP credentials not set in environment")
    else:
        print(f"✅ Configuration looks good - check network connectivity")
    
    print(f"=" * 70)

if __name__ == "__main__":
    debug_prp_connection()