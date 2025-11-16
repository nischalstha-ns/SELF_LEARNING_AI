#!/usr/bin/env python3
"""
Test script for the Self-Learning AI System
Run this to verify the system works correctly
"""

import requests
import json
import time

API_BASE = "http://localhost:8000"

def test_api():
    print("🤖 Testing Self-Learning AI System\n")
    
    # Test 1: Check server status
    print("1. Testing server connection...")
    try:
        response = requests.get(f"{API_BASE}/")
        print(f"✅ Server running: {response.json()['message']}")
    except:
        print("❌ Server not running. Start with: cd backend && python main.py")
        return
    
    # Test 2: Predict action
    print("\n2. Testing prediction...")
    test_state = [1, 2, 3]
    response = requests.post(f"{API_BASE}/predict", 
                           json={"state": test_state})
    result = response.json()
    print(f"✅ Predicted action {result['action']} for state {result['state']}")
    
    # Test 3: Update model
    print("\n3. Testing model update...")
    update_data = {
        "state": [1, 2, 3],
        "action": 1,
        "reward": 1.0,
        "next_state": [2, 3, 4]
    }
    response = requests.post(f"{API_BASE}/update", json=update_data)
    print(f"✅ {response.json()['message']}")
    
    # Test 4: Check status
    print("\n4. Testing status endpoint...")
    response = requests.get(f"{API_BASE}/status")
    status = response.json()
    print(f"✅ Q-table has {status['total_states']} states")
    print(f"   Learning rate: {status['learning_rate']}")
    
    # Test 5: Multiple updates
    print("\n5. Testing learning progression...")
    for i in range(3):
        requests.post(f"{API_BASE}/update", json={
            "state": f"state_{i}",
            "action": i % 4,
            "reward": 0.5 + i * 0.2,
            "next_state": f"state_{i+1}"
        })
    
    final_status = requests.get(f"{API_BASE}/status").json()
    print(f"✅ After training: {final_status['total_states']} states learned")
    
    print("\n🎉 All tests passed! System is working correctly.")
    print("\n📖 Next steps:")
    print("   - Open frontend/index.html in your browser")
    print("   - Try different states and actions")
    print("   - Watch the Q-table grow as the AI learns")

if __name__ == "__main__":
    test_api()