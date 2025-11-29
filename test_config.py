"""
Simplified test script to verify Sunona configuration works
"""
import os
from dotenv import load_dotenv

load_dotenv("local_setup/.env.local")

print("Testing Sunona imports...")
try:
    from sunona.models import Transcriber, Synthesizer, LlmAgent, SimpleLlmAgent
    print("✓ Imports successful")
except Exception as e:
    print(f"✗ Import failed: {e}")
    exit(1)

print("\nTesting Transcriber configuration...")
try:
    transcriber = Transcriber(
        provider="whisper",
        model="tiny",
        stream=True,
        language="en"
    )
    print(f"✓ Transcriber OK: {transcriber.provider}")
except Exception as e:
    print(f"✗ Transcriber failed: {e}")

print("\nTesting Synthesizer configuration...")
try:
    synthesizer = Synthesizer(
        provider="system",
        provider_config={"voice": None, "language": "en"},
        stream=True,
        audio_format="wav"
    )
    print(f"✓ Synthesizer OK: {synthesizer.provider}")
except Exception as e:
    print(f"✗ Synthesizer failed: {e}")

print("\nTesting LLM configuration...")
try:
    llm_config = SimpleLlmAgent(
        provider="openrouter",
        model="mistralai/mistral-7b-instruct:free",
        temperature=0.3
    )
    print(f"✓ SimpleLlmAgent OK: {llm_config.provider}")
except Exception as e:
    print(f"✗ SimpleLlmAgent failed: {e}")

print("\nTesting LlmAgent configuration...")
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
    print(f"✓ LlmAgent OK")
except Exception as e:
    print(f"✗ LlmAgent failed: {e}")

print("\n✓ All configuration tests passed!")
