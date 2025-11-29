import asyncio
import os
from dotenv import load_dotenv
from sunona.assistant import Assistant
from sunona.models import (
    Transcriber,
    Synthesizer,
    LlmAgent,
    SimpleLlmAgent,
)

load_dotenv("local_setup/.env.local")

async def main():
    assistant = Assistant(name="local_agent")

    # Configure Local ASR (Whisper)
    transcriber = Transcriber(
        provider="whisper", 
        model="tiny", 
        stream=True, 
        language="en"
    )

    # Configure LLM (OpenRouter for free models)
    llm_agent = LlmAgent(
        agent_type="simple_llm_agent",
        agent_flow_type="streaming",
        llm_config={
            "provider": "openrouter",
            "model": "mistralai/mistral-7b-instruct:free",
            "temperature": 0.3,
            "system_prompt": "You are a helpful assistant."
        }
    )

    # Configure Local TTS (System TTS - Lowest Latency)
    synthesizer = Synthesizer(
        provider="system",
        stream=True,
        audio_format="wav",
    )

    # Build pipeline
    assistant.add_task(
        task_type="conversation",
        llm_agent=llm_agent,
        transcriber=transcriber,
        synthesizer=synthesizer,
        enable_textual_input=False,
    )

    print("Starting Local Assistant (Whisper + XTTS)...")
    print("Speak into your microphone.")

    # Stream results
    async for chunk in assistant.execute(local=True):
        print(chunk)


if __name__ == "__main__":
    asyncio.run(main())
