#!/usr/bin/env python3
"""
Demo script for Meeting Notes Agent.
Tests core functionality without running full test suite.
"""

import os
import sys
import time
import subprocess
import requests
import json
from dotenv import load_dotenv

load_dotenv()

# Check configuration
mock_mode = os.getenv("MOCK_MODE", "false").lower() == "true"
ai_provider = os.getenv("AI_PROVIDER", "anthropic")

if not mock_mode:
    # Check for API key based on provider
    api_key_env = {
        "anthropic": "ANTHROPIC_API_KEY",
        "openai": "OPENAI_API_KEY",
        "gemini": "GEMINI_API_KEY"
    }.get(ai_provider)
    
    if api_key_env and not os.getenv(api_key_env):
        print(f"⚠️  {api_key_env} not set. Running in MOCK_MODE instead...")
        os.environ["MOCK_MODE"] = "true"
        mock_mode = True

if mock_mode:
    print("🎭 Running in MOCK_MODE (regex-based extraction, no API calls)")
else:
    print(f"🤖 Using AI provider: {ai_provider}")

print("🚀 Starting Meeting Notes Agent Demo...\n")

# Start server
print("📡 Starting FastAPI server...")
server_process = subprocess.Popen(
    ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"],
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE
)

# Wait for server to start
time.sleep(3)

try:
    # Health check
    print("🏥 Health check...")
    response = requests.get("http://localhost:8000/health")
    if response.status_code == 200:
        print("✅ Server is healthy\n")
    else:
        print(f"❌ Health check failed: {response.status_code}")
        sys.exit(1)

    # Test 1: Create a meeting
    print("📝 Test 1: Creating a meeting with transcript...")
    meeting_data = {
        "title": "Sprint Planning - Week 22",
        "transcript": """
        John: Alright team, let's discuss this week's priorities.
        Sarah: I'll handle the database migration, deadline is Friday.
        Mike: I can take the API authentication bug, should be done by Wednesday.
        John: Great. Sarah, can you also update the documentation after the migration?
        Sarah: Sure, I'll add that to my list. Deadline end of week.
        Mike: We're blocked on the frontend until John finishes the API design.
        John: I'll have the API spec ready by tomorrow.
        Lisa: Should we schedule a follow-up on the performance issues?
        John: Yes, let's do that next Monday. Lisa, can you prepare a report?
        Lisa: Will do. I'll analyze the metrics by Friday.
        """
    }
    
    response = requests.post("http://localhost:8000/meetings", json=meeting_data)
    if response.status_code == 200:
        meeting = response.json()
        print(f"✅ Meeting created (ID: {meeting['id']})")
        print(f"   Title: {meeting['title']}")
        print(f"   Action items extracted: {len(meeting['action_items'])}\n")
        
        # Display action items
        print("   Action Items:")
        for item in meeting['action_items']:
            print(f"   - [{item['id']}] {item['task']}")
            print(f"     Owner: {item['owner']}, Deadline: {item['deadline']}, Priority: {item['priority']}")
    else:
        print(f"❌ Failed to create meeting: {response.status_code}")
        print(response.text)
        sys.exit(1)

    # Test 2: List all meetings
    print("\n📋 Test 2: Listing all meetings...")
    response = requests.get("http://localhost:8000/meetings")
    if response.status_code == 200:
        meetings = response.json()
        print(f"✅ Found {len(meetings)} meeting(s)\n")
    else:
        print(f"❌ Failed to list meetings: {response.status_code}")

    # Test 3: Get pending action items
    print("⏳ Test 3: Getting pending action items...")
    response = requests.get("http://localhost:8000/action-items/pending")
    if response.status_code == 200:
        items = response.json()
        print(f"✅ Found {len(items)} pending item(s)\n")
        for item in items[:3]:  # Show first 3
            print(f"   - {item['task']} (Owner: {item['owner']})")
    else:
        print(f"❌ Failed to get pending items: {response.status_code}")

    # Test 4: Update an action item
    if meeting['action_items']:
        print("\n✏️  Test 4: Updating an action item...")
        item_id = meeting['action_items'][0]['id']
        update_data = {"status": "in_progress"}
        response = requests.patch(f"http://localhost:8000/action-items/{item_id}", json=update_data)
        if response.status_code == 200:
            updated_item = response.json()
            print(f"✅ Updated item {item_id}")
            print(f"   New status: {updated_item['status']}\n")
        else:
            print(f"❌ Failed to update item: {response.status_code}")

    # Test 5: Create another meeting to test cross-meeting linking
    print("🔗 Test 5: Creating second meeting (testing cross-meeting linking)...")
    meeting_data_2 = {
        "title": "Mid-week Sync - Week 22",
        "transcript": """
        John: Quick update on progress.
        Sarah: Database migration is done! Moving to documentation now.
        Mike: API auth bug is almost finished, should be ready tomorrow.
        John: Excellent. The API spec is ready for review.
        Lisa: Performance analysis is underway, will have preliminary results by Friday.
        """
    }
    
    response = requests.post("http://localhost:8000/meetings", json=meeting_data_2)
    if response.status_code == 200:
        meeting_2 = response.json()
        print(f"✅ Second meeting created (ID: {meeting_2['id']})")
        print(f"   Action items: {len(meeting_2['action_items'])}")
        print(f"   (Note: Items may be linked to previous meeting items)\n")
    else:
        print(f"❌ Failed to create second meeting: {response.status_code}")

    print("=" * 60)
    print("✅ Demo completed successfully!")
    print("=" * 60)
    print("\nAPI Endpoints:")
    print("  POST   /meetings                    - Create meeting")
    print("  GET    /meetings                    - List meetings")
    print("  GET    /meetings/{id}               - Get meeting details")
    print("  GET    /action-items                - List all action items")
    print("  GET    /action-items/{id}           - Get action item")
    print("  PATCH  /action-items/{id}           - Update action item")
    print("  GET    /action-items/owner/{owner}  - Get items by owner")
    print("  GET    /action-items/pending        - Get pending items")
    print("\nServer running at: http://localhost:8000")
    print("API docs at: http://localhost:8000/docs")

except Exception as e:
    print(f"❌ Error during demo: {e}")
    sys.exit(1)

finally:
    # Cleanup
    print("\n🛑 Stopping server...")
    server_process.terminate()
    server_process.wait(timeout=5)
    print("✅ Server stopped")
