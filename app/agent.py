import os
import json
from typing import List, Dict
from app.schemas import ActionItemBase
import re

_client = None
MOCK_MODE = os.getenv("MOCK_MODE", "false").lower() == "true"
AI_PROVIDER = os.getenv("AI_PROVIDER", "anthropic")  # anthropic, openai, gemini, ollama

def get_client():
    """Lazy initialization of AI client."""
    global _client
    if _client is None:
        if MOCK_MODE:
            return None  # Mock mode
        
        if AI_PROVIDER == "openai":
            import openai
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OPENAI_API_KEY not set in environment")
            _client = openai.OpenAI(api_key=api_key)
        elif AI_PROVIDER == "anthropic":
            import anthropic
            api_key = os.getenv("ANTHROPIC_API_KEY")
            if not api_key:
                raise ValueError("ANTHROPIC_API_KEY not set in environment")
            _client = anthropic.Anthropic(api_key=api_key)
        elif AI_PROVIDER == "gemini":
            import google.generativeai as genai
            api_key = os.getenv("GEMINI_API_KEY")
            if not api_key:
                raise ValueError("GEMINI_API_KEY not set in environment")
            genai.configure(api_key=api_key)
            _client = genai.GenerativeModel('gemini-pro')
        elif AI_PROVIDER == "ollama":
            # Ollama runs locally, no API key needed
            _client = "ollama"  # Placeholder
        else:
            raise ValueError(f"Unknown AI_PROVIDER: {AI_PROVIDER}")
    
    return _client


def extract_action_items(transcript: str) -> Dict:
    """Extract action items from meeting transcript using AI."""
    
    # Mock mode for demo without API key
    if MOCK_MODE:
        return _mock_extract_action_items(transcript)
    
    prompt = f"""Analyze this meeting transcript and extract all action items.

For each action item, identify:
- task: clear description of what needs to be done
- owner: person responsible (if mentioned)
- deadline: when it's due (if mentioned)
- priority: low, medium, or high (infer from context)

Also provide a brief summary of the meeting.

Transcript:
{transcript}

Return your response as JSON with this structure:
{{
    "summary": "brief meeting summary",
    "items": [
        {{
            "task": "task description",
            "owner": "person name or null",
            "deadline": "deadline or null",
            "priority": "low|medium|high"
        }}
    ]
}}

Be thorough but concise. If no action items found, return empty items array."""

    client = get_client()
    
    if AI_PROVIDER == "openai":
        message = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=2000
        )
        response_text = message.choices[0].message.content
    elif AI_PROVIDER == "anthropic":
        message = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}]
        )
        response_text = message.content[0].text
    elif AI_PROVIDER == "gemini":
        response = client.generate_content(prompt)
        response_text = response.text
    else:
        raise ValueError(f"Unsupported AI_PROVIDER: {AI_PROVIDER}")
    
    # Parse JSON response
    try:
        result = json.loads(response_text)
        return result
    except json.JSONDecodeError:
        # Fallback if AI doesn't return valid JSON
        return {
            "summary": "Failed to parse meeting",
            "items": []
        }


def _mock_extract_action_items(transcript: str) -> Dict:
    """Mock extraction for demo purposes."""
    items = []
    
    # Simple regex-based extraction
    lines = transcript.split('\n')
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # Look for patterns like "Name: task by deadline"
        match = re.match(r'(\w+):\s*(.+)', line)
        if match:
            owner = match.group(1)
            content = match.group(2)
            
            # Extract deadline
            deadline = None
            if 'by friday' in content.lower():
                deadline = "Friday"
            elif 'by monday' in content.lower():
                deadline = "Monday"
            elif 'by wednesday' in content.lower():
                deadline = "Wednesday"
            elif 'end of week' in content.lower():
                deadline = "End of week"
            elif 'tomorrow' in content.lower():
                deadline = "Tomorrow"
            
            # Infer priority
            priority = "medium"
            if 'urgent' in content.lower() or 'asap' in content.lower():
                priority = "high"
            elif 'when you can' in content.lower() or 'low priority' in content.lower():
                priority = "low"
            
            items.append({
                "task": content,
                "owner": owner,
                "deadline": deadline,
                "priority": priority
            })
    
    return {
        "summary": f"Meeting discussion with {len(items)} action items identified",
        "items": items
    }


def find_related_items(new_task: str, existing_items: List[Dict]) -> List[int]:
    """Find related action items using semantic similarity."""
    
    if not existing_items:
        return []
    
    # Mock mode
    if MOCK_MODE:
        return _mock_find_related_items(new_task, existing_items)
    
    # Build context of existing items
    existing_context = "\n".join([
        f"ID {item['id']}: {item['task']} (owner: {item.get('owner', 'none')}, status: {item['status']})"
        for item in existing_items
    ])
    
    prompt = f"""Given this new action item:
"{new_task}"

And these existing action items:
{existing_context}

Which existing items are related to the new one? Consider:
- Similar topics or dependencies
- Same owner or project
- Blocking relationships

Return ONLY a JSON array of related item IDs, e.g., [1, 5, 12]
If no related items, return []"""

    client = get_client()
    
    if AI_PROVIDER == "openai":
        message = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=200
        )
        response_text = message.choices[0].message.content.strip()
    elif AI_PROVIDER == "anthropic":
        message = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=200,
            messages=[{"role": "user", "content": prompt}]
        )
        response_text = message.content[0].text.strip()
    elif AI_PROVIDER == "gemini":
        response = client.generate_content(prompt)
        response_text = response.text.strip()
    else:
        raise ValueError(f"Unsupported AI_PROVIDER: {AI_PROVIDER}")
    
    try:
        related_ids = json.loads(response_text)
        return related_ids if isinstance(related_ids, list) else []
    except json.JSONDecodeError:
        return []


def _mock_find_related_items(new_task: str, existing_items: List[Dict]) -> List[int]:
    """Mock relationship detection."""
    related = []
    new_task_lower = new_task.lower()
    
    for item in existing_items:
        task_lower = item['task'].lower()
        # Simple keyword matching
        keywords = ['bug', 'api', 'database', 'migration', 'auth', 'login', 'frontend', 'backend']
        for keyword in keywords:
            if keyword in new_task_lower and keyword in task_lower:
                related.append(item['id'])
                break
    
    return related[:3]  # Max 3 related items


def detect_status_updates(transcript: str, existing_items: List[Dict]) -> List[Dict]:
    """Detect status updates for existing action items in the transcript."""
    
    if not existing_items:
        return []
    
    # Mock mode
    if MOCK_MODE:
        return _mock_detect_status_updates(transcript, existing_items)
    
    existing_context = "\n".join([
        f"ID {item['id']}: {item['task']} (current status: {item['status']})"
        for item in existing_items
    ])
    
    prompt = f"""Analyze this meeting transcript for status updates on existing action items.

Existing items:
{existing_context}

Transcript:
{transcript}

Identify any mentions of progress, completion, or blocking issues for these items.

Return JSON array of updates:
[
    {{
        "item_id": 123,
        "new_status": "completed|in_progress|blocked|pending",
        "reason": "brief explanation from transcript"
    }}
]

If no updates found, return []"""

    client = get_client()
    
    if AI_PROVIDER == "openai":
        message = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=1000
        )
        response_text = message.choices[0].message.content.strip()
    elif AI_PROVIDER == "anthropic":
        message = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}]
        )
        response_text = message.content[0].text.strip()
    elif AI_PROVIDER == "gemini":
        response = client.generate_content(prompt)
        response_text = response.text.strip()
    else:
        raise ValueError(f"Unsupported AI_PROVIDER: {AI_PROVIDER}")
    
    try:
        updates = json.loads(response_text)
        return updates if isinstance(updates, list) else []
    except json.JSONDecodeError:
        return []


def _mock_detect_status_updates(transcript: str, existing_items: List[Dict]) -> List[Dict]:
    """Mock status update detection."""
    updates = []
    transcript_lower = transcript.lower()
    
    for item in existing_items:
        task_lower = item['task'].lower()
        
        # Check for completion keywords
        if any(word in transcript_lower for word in ['done', 'finished', 'completed', 'ready']):
            if any(keyword in task_lower for keyword in ['bug', 'migration', 'api', 'spec']):
                updates.append({
                    "item_id": item['id'],
                    "new_status": "completed",
                    "reason": "Mentioned as done/finished in transcript"
                })
        
        # Check for in-progress keywords
        elif any(word in transcript_lower for word in ['working on', 'in progress', 'almost', 'underway']):
            if any(keyword in task_lower for keyword in ['bug', 'analysis', 'report']):
                updates.append({
                    "item_id": item['id'],
                    "new_status": "in_progress",
                    "reason": "Mentioned as in progress in transcript"
                })
        
        # Check for blocked keywords
        elif any(word in transcript_lower for word in ['blocked', 'waiting', 'stuck']):
            if any(keyword in task_lower for keyword in ['frontend', 'api', 'integration']):
                updates.append({
                    "item_id": item['id'],
                    "new_status": "blocked",
                    "reason": "Mentioned as blocked in transcript"
                })
    
    return updates
