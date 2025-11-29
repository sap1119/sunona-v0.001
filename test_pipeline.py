"""
Comprehensive test - Full Assistant Pipeline
"""
import sys
import traceback
from dotenv import load_dotenv

load_dotenv("local_setup/.env.local")

print("="*80)
print("COMPREHENSIVE PIPELINE TEST")
print("="*80)

# Test 1: Imports
print("\n[TEST 1] Importing all components...")
try:
    from sunona.assistant import Assistant
    from sunona.models import Transcriber, Synthesizer, LlmAgent, SimpleLlmAgent
    print("[OK] All imports successful")
except Exception as e:
    print("[FAIL] Import failed:")
    traceback.print_exc()
    sys.exit(1)

# Test 2: Transcriber
print("\n[TEST 2] Creating Transcriber...")
try:
    transcriber = Transcriber(
        provider="whisper", 
        model="tiny", 
        stream=True, 
        language="en"
    )
    print(f"[OK] Transcriber: {transcriber.provider}")
except Exception as e:
    print("[FAIL] Transcriber failed:")
    traceback.print_exc()
    sys.exit(1)

# Test 3: Synthesizer
print("\n[TEST 3] Creating Synthesizer...")
try:
    synthesizer = Synthesizer(
        provider="system",
        stream=True,
        audio_format="wav"
    )
    print(f"[OK] Synthesizer: {synthesizer.provider}")
except Exception as e:
    print("[FAIL] Synthesizer failed:")
    traceback.print_exc()
    sys.exit(1)

# Test 4: LLM Agent
print("\n[TEST 4] Creating LLM Agent...")
try:
    llm_agent = LlmAgent(
        agent_type="simple_llm_agent",
        agent_flow_type="streaming",
        llm_config={
            "provider": "openrouter",
            "model": "mistralai/mistral-7b-instruct:free",
            "temperature": 0.3
        }
    )
    print(f"[OK] LLM Agent: {llm_agent.agent_type}")
except Exception as e:
    print("[FAIL] LLM Agent failed:")
    traceback.print_exc()
    sys.exit(1)

# Test 5: Assistant
print("\n[TEST 5] Creating Assistant...")
try:
    assistant = Assistant(name="test_agent")
    print(f"[OK] Assistant created")
except Exception as e:
    print("[FAIL] Assistant failed:")
    traceback.print_exc()
    sys.exit(1)

# Test 6: Add Task (CRITICAL - This is where it likely fails)
print("\n[TEST 6] Adding task to Assistant...")
try:
    assistant.add_task(
        task_type="conversation",
        llm_agent=llm_agent,
        transcriber=transcriber,
        synthesizer=synthesizer,
        enable_textual_input=False
    )
    print(f"[OK] Task added successfully")
except Exception as e:
    print("[FAIL] add_task failed:")
    print(f"       Error: {type(e).__name__}: {str(e)}")
    if hasattr(e, 'errors'):
        print("\n[PYDANTIC ERRORS]")
        for err in e.errors():
            print(f"  - Location: {err.get('loc')}")
            print(f"    Type: {err.get('type')}")
            print(f"    Message: {err.get('msg')}")
    print("\n[TRACEBACK]")
    traceback.print_exc()
    sys.exit(1)

print("\n" + "="*80)
print("ALL TESTS PASSED - PIPELINE READY")
print("="*80)
