"""
Industrial-Level Debugging Script for Pydantic Validation Error
Captures full traceback with verbose logging
"""
import sys
import traceback
import os
from dotenv import load_dotenv

# Enable verbose Pydantic validation errors
os.environ['PYDANTIC_USE_STRICT_VALIDATION'] = '1'

load_dotenv("local_setup/.env.local")

print("="*80)
print("INDUSTRIAL-LEVEL DEBUGGING SESSION")
print("="*80)
print("\n[STEP 1] Testing imports...")

try:
    from sunona.assistant import Assistant
    from sunona.models import Transcriber, Synthesizer, LlmAgent, SimpleLlmAgent
    print("✓ All imports successful\n")
except Exception as e:
    print(f"✗ Import failed:")
    traceback.print_exc()
    sys.exit(1)

print("[STEP 2] Testing Transcriber instantiation...")
try:
    transcriber = Transcriber(
        provider="whisper", 
        model="tiny", 
        stream=True, 
        language="en"
    )
    print(f"✓ Transcriber created: {transcriber}")
    print(f"  - Provider: {transcriber.provider}")
    print(f"  - Model: {transcriber.model}\n")
except Exception as e:
    print(f"✗ Transcriber failed:")
    traceback.print_exc()
    sys.exit(1)

print("[STEP 3] Testing Synthesizer instantiation (CRITICAL)...")
print("  Attempting with NO provider_config...")
try:
    synthesizer = Synthesizer(
        provider="system",
        stream=True,
        audio_format="wav"
    )
    print(f"✓ Synthesizer created: {synthesizer}")
    print(f"  - Provider: {synthesizer.provider}")
    print(f"  - Config: {synthesizer.provider_config}")
    print(f"  - Stream: {synthesizer.stream}\n")
except Exception as e:
    print(f"✗ Synthesizer failed:")
    print(f"  Error type: {type(e).__name__}")
    print(f"  Error message: {str(e)}")
    print("\n  Full traceback:")
    traceback.print_exc()
    print("\n  Attempting to extract Pydantic validation details...")
    if hasattr(e, 'errors'):
        print(f"\n  Pydantic validation errors:")
        for error in e.errors():
            print(f"    - Field: {error.get('loc')}")
            print(f"      Type: {error.get('type')}")
            print(f"      Message: {error.get('msg')}")
            print(f"      Input: {error.get('input')}")
    sys.exit(1)

print("[STEP 4] Testing LLM configuration...")
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
    print(f"✓ LlmAgent created: {llm_agent}")
    print(f"  - Type: {llm_agent.agent_type}\n")
except Exception as e:
    print(f"✗ LlmAgent failed:")
    traceback.print_exc()
    sys.exit(1)

print("[STEP 5] Testing Assistant instantiation...")
try:
    assistant = Assistant(name="debug_agent")
    print(f"✓ Assistant created: {assistant}\n")
except Exception as e:
    print(f"✗ Assistant failed:")
    traceback.print_exc()
    sys.exit(1)

print("="*80)
print("ALL TESTS PASSED - NO VALIDATION ERRORS DETECTED")
print("="*80)
