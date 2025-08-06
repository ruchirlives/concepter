#!/usr/bin/env python3
"""
Test script for the transition metadata API endpoints.
This script tests both save and load functionality.
"""

import requests
import json
import os

# Configuration
API_BASE_URL = "http://localhost:8080"
API_PASSCODE = os.getenv("API_PASSCODE", "your_passcode_here")

# Headers for authentication
headers = {"Content-Type": "application/json", "X-Passcode": API_PASSCODE}


def test_save_transition_metadata():
    """Test saving transition metadata."""
    print("Testing save_transition_metadata endpoint...")

    # Sample transition metadata
    test_metadata = {
        "transitions": [
            {
                "id": "transition_1",
                "name": "Project Planning",
                "from_state": "initial",
                "to_state": "planning",
                "timestamp": "2025-08-06T10:00:00Z",
                "description": "Initial project setup and planning phase",
            },
            {
                "id": "transition_2",
                "name": "Implementation",
                "from_state": "planning",
                "to_state": "development",
                "timestamp": "2025-08-06T11:00:00Z",
                "description": "Start development work",
            },
        ],
        "metadata": {
            "project_name": "ConcepterWeb",
            "version": "1.0.0",
            "created_by": "test_user",
            "last_updated": "2025-08-06T12:00:00Z",
        },
    }

    try:
        response = requests.post(
            f"{API_BASE_URL}/save_transition_metadata", headers=headers, json={"metadata": test_metadata}
        )

        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")

        if response.status_code == 200:
            print("✅ Save test passed!")
            return True
        else:
            print("❌ Save test failed!")
            return False

    except Exception as e:
        print(f"❌ Save test error: {e}")
        return False


def test_load_transition_metadata():
    """Test loading transition metadata."""
    print("\nTesting load_transition_metadata endpoint...")

    try:
        response = requests.get(f"{API_BASE_URL}/load_transition_metadata", headers=headers)

        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")

        if response.status_code == 200:
            print("✅ Load test passed!")
            return True
        else:
            print("❌ Load test failed!")
            return False

    except Exception as e:
        print(f"❌ Load test error: {e}")
        return False


def test_delete_transition_metadata():
    """Test deleting transition metadata."""
    print("\nTesting delete_transition_metadata endpoint...")

    try:
        response = requests.delete(f"{API_BASE_URL}/delete_transition_metadata", headers=headers)

        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")

        if response.status_code in [200, 404]:  # 404 is ok if no data exists
            print("✅ Delete test passed!")
            return True
        else:
            print("❌ Delete test failed!")
            return False

    except Exception as e:
        print(f"❌ Delete test error: {e}")
        return False


def main():
    """Run all tests."""
    print("Starting transition metadata API tests...\n")

    # Test save functionality
    save_success = test_save_transition_metadata()

    # Test load functionality
    load_success = test_load_transition_metadata()

    # Test delete functionality
    delete_success = test_delete_transition_metadata()

    print("\n=== Test Results ===")
    print(f"Save test: {'PASSED' if save_success else 'FAILED'}")
    print(f"Load test: {'PASSED' if load_success else 'FAILED'}")
    print(f"Delete test: {'PASSED' if delete_success else 'FAILED'}")

    if save_success and load_success and delete_success:
        print("🎉 All tests passed!")
    else:
        print("❌ Some tests failed!")


if __name__ == "__main__":
    main()
