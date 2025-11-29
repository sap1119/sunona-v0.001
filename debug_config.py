import os
from dotenv import load_dotenv
from bolna.models import Transcriber, Synthesizer, LlmAgent, SimpleLlmAgent

load_dotenv("local_setup/.env.local")

print("Testing Transcriber...")
try:
    transcriber = Transcriber(
        provider="whisper", 
        model="tiny", 
        stream=True, 
        language="en"
    )
    print("Transcriber OK")
except Exception as e:
    print(f"Transcriber FAILED: {e}")

print("\nTesting Synthesizer...")
try:
    synthesizer = Synthesizer(
        provider="system",
        provider_config={
            "voice": "default", 
            "language": "en"
        },
        stream=True,
        audio_format="wav",
    )
    print("Synthesizer OK")
except Exception as e:
    print(f"Synthesizer FAILED: {e}")

print("\nTesting LlmAgent...")
try:
    llm_agent = LlmAgent(
        agent_type="simple_llm_agent",
        agent_flow_type="streaming",
        llm_config=SimpleLlmAgent(
            provider="openrouter",
            model="mistralai/mistral-7b-instruct:free",
            temperature=0.3,
        ),
    )
    print("LlmAgent OK")
except Exception as e:
    print(f"LlmAgent FAILED: {e}")
