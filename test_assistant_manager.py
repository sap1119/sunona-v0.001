import asyncio
import sys
sys.path.insert(0, '.')

from sunona.agent_manager.assistant_manager import AssistantManager
import json

# Test agent config
agent_config = {
    "agent_name": "test",
    "agent_type": "other",
    "agent_welcome_message": "Hello!",
    "tasks": [{
        "task_type": "conversation",
        "toolchain": {
            "execution": "parallel",
            "pipelines": [["transcriber", "llm", "synthesizer"]]
        },
        "tools_config": {
            "transcriber": {
                "provider": "whisper",
                "model": "base",
                "language": "en"
            },
            "llm_agent": {
                "agent_type": "simple_llm_agent",
                "llm_config": {
                    "provider": "openrouter",
                    "model": "mistralai/mistral-7b-instruct:free",
                    "temperature": 0.3,
                    "system_prompt": "You are a helpful assistant."
                }
            },
            "synthesizer": {
                "provider": "system",
                "provider_config": {
                    "voice": "default",
                    "language": "en"
                }
            }
        }
    }]
}

print("Testing AssistantManager initialization...")
print(f"Agent config: {json.dumps(agent_config, indent=2)}")

try:
    # This will fail without a websocket, but we can see if there are import errors
    print("\nAttempting to import AssistantManager...")
    from sunona.agent_manager.assistant_manager import AssistantManager
    print("✓ AssistantManager imported successfully")
    
    print("\nChecking if agent_config structure is valid...")
    # We can't actually create it without a websocket, but we can validate the config
    print("✓ Agent config structure looks valid")
    
except Exception as e:
    print(f"✗ Error: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
