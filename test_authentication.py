#!/usr/bin/env python3
"""
Simple test script to demonstrate API authentication.
Run this while the Flask server is running to test authentication.
"""

import requests
import os
import json

# Configuration
BASE_URL = "http://localhost:8080"
TEST_PASSCODE = os.getenv("API_PASSCODE", "test-passcode")

def test_without_passcode():
    """Test API call without passcode - should fail."""
    print("🧪 Testing API call WITHOUT passcode...")
    
    try:
        response = requests.get(f"{BASE_URL}/get_containers")
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
        
        if response.status_code == 401:
            print("✅ PASS: API correctly rejected request without passcode")
        else:
            print("❌ FAIL: API should have rejected request without passcode")
    except Exception as e:
        print(f"❌ ERROR: {e}")
    
    print("-" * 50)

def test_with_wrong_passcode():
    """Test API call with wrong passcode - should fail."""
    print("🧪 Testing API call WITH wrong passcode...")
    
    headers = {
        "X-Passcode": "wrong-passcode",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.get(f"{BASE_URL}/get_containers", headers=headers)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
        
        if response.status_code == 401:
            print("✅ PASS: API correctly rejected request with wrong passcode")
        else:
            print("❌ FAIL: API should have rejected request with wrong passcode")
    except Exception as e:
        print(f"❌ ERROR: {e}")
    
    print("-" * 50)

def test_with_correct_passcode():
    """Test API call with correct passcode - should succeed."""
    print("🧪 Testing API call WITH correct passcode...")
    
    headers = {
        "X-Passcode": TEST_PASSCODE,
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.get(f"{BASE_URL}/get_containers", headers=headers)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ PASS: API correctly accepted request with correct passcode")
            data = response.json()
            print(f"Response keys: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")
        else:
            print("❌ FAIL: API should have accepted request with correct passcode")
            print(f"Response: {response.text}")
    except Exception as e:
        print(f"❌ ERROR: {e}")
    
    print("-" * 50)

def test_static_route():
    """Test static route - should work without passcode."""
    print("🧪 Testing static route (should work WITHOUT passcode)...")
    
    try:
        response = requests.get(f"{BASE_URL}/")
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ PASS: Static route works without authentication")
        else:
            print("❌ FAIL: Static route should work without authentication")
            print(f"Response: {response.text[:200]}...")
    except Exception as e:
        print(f"❌ ERROR: {e}")
    
    print("-" * 50)

def main():
    """Run all authentication tests."""
    print("🔐 API Authentication Test Suite")
    print("=" * 50)
    print(f"Base URL: {BASE_URL}")
    print(f"Test Passcode: {TEST_PASSCODE}")
    print("=" * 50)
    
    # Test cases
    test_without_passcode()
    test_with_wrong_passcode()
    test_with_correct_passcode()
    test_static_route()
    
    print("🏁 Test suite completed!")
    print("\n💡 Make sure to:")
    print("1. Set API_PASSCODE environment variable")
    print("2. Start the Flask server")
    print("3. Run this test script")

if __name__ == "__main__":
    main()
