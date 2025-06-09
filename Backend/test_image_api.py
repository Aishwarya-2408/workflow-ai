"""
Test script for image workflow API endpoints
"""
import requests
import os
import json
from pprint import pprint

# Base URL for API
API_BASE_URL = "http://localhost:5000/api/v1/image"

def test_health():
    """Test health check endpoint"""
    print("\n=== Testing Health Check ===")
    response = requests.get(f"{API_BASE_URL}/health")
    print(f"Status Code: {response.status_code}")
    pprint(response.json())
    return response.status_code == 200

def test_current_file():
    """Test current file endpoint"""
    print("\n=== Testing Current File ===")
    response = requests.get(f"{API_BASE_URL}/current-file")
    print(f"Status Code: {response.status_code}")
    try:
        pprint(response.json())
    except:
        print("No JSON response")
    return response.status_code in [200, 404]  # 404 is okay for no current file

def test_list_outputs():
    """Test list outputs endpoint"""
    print("\n=== Testing List Outputs ===")
    response = requests.get(f"{API_BASE_URL}/outputs")
    print(f"Status Code: {response.status_code}")
    try:
        pprint(response.json())
    except:
        print("No JSON response")
    return response.status_code == 200

def test_upload_file(file_path=None):
    """Test file upload endpoint"""
    if not file_path:
        print("\n=== Skipping Upload Test (no file specified) ===")
        return True
    
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        return False
        
    print(f"\n=== Testing Upload File: {file_path} ===")
    with open(file_path, 'rb') as file:
        files = {'file': (os.path.basename(file_path), file)}
        response = requests.post(f"{API_BASE_URL}/upload", files=files)
    
    print(f"Status Code: {response.status_code}")
    try:
        pprint(response.json())
    except:
        print("No JSON response")
    
    return response.status_code == 200

def run_tests(test_image=None):
    """Run all tests"""
    results = {
        "Health Check": test_health(),
        "Current File": test_current_file(),
        "List Outputs": test_list_outputs()
    }
    
    if test_image:
        results["Upload File"] = test_upload_file(test_image)
    
    # Print summary
    print("\n=== Test Results ===")
    all_passed = True
    for test, result in results.items():
        status = "PASSED" if result else "FAILED"
        print(f"{test}: {status}")
        if not result:
            all_passed = False
    
    return all_passed

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Test Image API endpoints")
    parser.add_argument("--image", help="Path to image file for upload test")
    args = parser.parse_args()
    
    success = run_tests(args.image)
    print(f"\nOverall: {'PASSED' if success else 'FAILED'}")
    
    if not success:
        exit(1)  # Exit with error code for CI/CD pipelines 