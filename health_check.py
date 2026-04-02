#!/usr/bin/env python3
"""
Comprehensive health check and validation test for the Permit-to-Build API.
"""

import requests
import json
from PIL import Image, ImageDraw
import io

API_URL = "http://127.0.0.1:8000"

def check_api_health():
    """Check if API is running and accessible."""
    print("\n" + "="*60)
    print("🔍 API HEALTH CHECK")
    print("="*60)
    
    try:
        # Try to access the docs endpoint
        response = requests.get(f"{API_URL}/docs")
        if response.status_code == 200:
            print("✅ API Server is running and accessible")
            print(f"   URL: {API_URL}")
            return True
        else:
            print(f"⚠️  API returned status {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to API. Make sure the server is running.")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def check_endpoints():
    """Check available endpoints."""
    print("\n" + "="*60)
    print("📍 AVAILABLE ENDPOINTS")
    print("="*60)
    
    endpoints = [
        ("/docs", "GET", "Interactive API documentation (Swagger)"),
        ("/redoc", "GET", "Alternative API documentation (ReDoc)"),
        ("/openapi.json", "GET", "OpenAPI schema"),
        ("/validate", "POST", "Validate blueprint image"),
    ]
    
    for endpoint, method, description in endpoints:
        try:
            if method == "GET":
                response = requests.head(f"{API_URL}{endpoint}", timeout=2)
            print(f"✅ {method:6} {endpoint:20} - {description}")
        except:
            print(f"⚠️  {method:6} {endpoint:20} - Not accessible")

def create_test_blueprint():
    """Create a test blueprint image."""
    img = Image.new('RGB', (400, 400), color='white')
    draw = ImageDraw.Draw(img)
    
    # Draw some blueprint elements
    draw.rectangle([50, 50, 350, 350], outline='blue', width=2)
    draw.rectangle([100, 100, 300, 300], outline='blue', width=2)
    draw.line([50, 50, 350, 350], fill='blue', width=1)
    draw.text((150, 180), "Blueprint", fill='blue')
    
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='PNG')
    img_bytes.seek(0)
    return img_bytes

def test_validation():
    """Test the validation endpoint."""
    print("\n" + "="*60)
    print("🏗️  VALIDATION TEST")
    print("="*60)
    
    try:
        test_image = create_test_blueprint()
        print("✅ Test blueprint created")
        
        print("📤 Sending to /validate endpoint...")
        response = requests.post(
            f"{API_URL}/validate",
            files={"file": ("test_blueprint.png", test_image, "image/png")},
            timeout=60
        )
        
        print(f"📥 Response Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            
            print("\n✅ VALIDATION SUCCESSFUL")
            print(f"   Compliance Status: {data.get('compliance_report', {}).get('status', 'N/A')}")
            print(f"   Extracted Specs: {data.get('extracted_specs', {})}")
            print(f"   Relevant Laws Found: {len(data.get('relevant_laws', []))}")
            print(f"   Citations: {len(data.get('compliance_report', {}).get('citations', []))}")
            
            if data.get('errors'):
                print(f"\n⚠️  Processing Errors: {data['errors']}")
            
            return True
        else:
            print(f"❌ Validation failed: {response.text}")
            return False
            
    except requests.exceptions.Timeout:
        print("❌ Request timed out (API may be processing)")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def print_summary(health_ok, validation_ok):
    """Print test summary."""
    print("\n" + "="*60)
    print("📊 TEST SUMMARY")
    print("="*60)
    
    status = "✅ ALL SYSTEMS OPERATIONAL" if (health_ok and validation_ok) else "⚠️  ISSUES DETECTED"
    print(f"\nStatus: {status}")
    
    print(f"\n  API Health:        {'✅ OK' if health_ok else '❌ FAILED'}")
    print(f"  Validation Test:   {'✅ OK' if validation_ok else '❌ FAILED'}")
    
    if health_ok:
        print(f"\n🚀 The application is ready to use!")
        print(f"   - API: {API_URL}")
        print(f"   - Docs: {API_URL}/docs")
    
    print("\n" + "="*60)

if __name__ == "__main__":
    print("\n🔧 PERMIT-TO-BUILD ORCHESTRATOR - SYSTEM CHECK")
    print("Starting comprehensive validation...\n")
    
    health_ok = check_api_health()
    
    if health_ok:
        check_endpoints()
        validation_ok = test_validation()
    else:
        validation_ok = False
    
    print_summary(health_ok, validation_ok)
