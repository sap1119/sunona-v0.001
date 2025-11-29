# Provider Configuration

Sunona supports a wide range of AI and telephony providers. This guide explains how to configure each one.

## 🔑 Environment Variables

All provider keys should be added to your `.env` file.

```bash
# LLM Providers
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GROQ_API_KEY=gsk_...
DEEPSEEK_API_KEY=...

# Speech-to-Text (STT)
DEEPGRAM_AUTH_TOKEN=...
ASSEMBLYAI_API_KEY=...

# Text-to-Speech (TTS)
ELEVENLABS_API_KEY=...
CARTESIA_API_KEY=...
OPENAI_API_KEY=... # Reused for TTS

# Telephony
TWILIO_ACCOUNT_SID=...
TWILIO_AUTH_TOKEN=...
PLIVO_AUTH_ID=...
PLIVO_AUTH_TOKEN=...
```

---

## 🗣️ Speech-to-Text (STT)

### Deepgram (Recommended)
Deepgram is the default and recommended STT provider due to its speed (<300ms latency).

- **Website**: [console.deepgram.com](https://console.deepgram.com)
- **Models**: `nova-2` (best balance), `nova-2-phonecall` (optimized for telephony)
- **Config**:
  ```json
  "transcriber": {
    "provider": "deepgram",
    "model": "nova-2",
    "language": "en",
    "stream": true
  }
  ```

### Whisper (OpenAI)
High accuracy but higher latency than Deepgram.

- **Config**:
  ```json
  "transcriber": {
    "provider": "openai",
    "model": "whisper-1"
  }
  ```

---

## 🧠 LLM Providers

### OpenAI
Standard choice for reasoning and conversation.

- **Models**: `gpt-4o`, `gpt-4o-mini` (faster/cheaper)
- **Config**:
  ```json
  "llm_agent": {
    "llm_config": {
      "provider": "openai",
      "model": "gpt-4o-mini"
    }
  }
  ```

### Anthropic
Great for complex instructions and natural tone.

- **Models**: `claude-3-5-sonnet-20240620`, `claude-3-haiku-20240307`
- **Config**:
  ```json
  "llm_agent": {
    "llm_config": {
      "provider": "anthropic",
      "model": "claude-3-5-sonnet-20240620"
    }
  }
  ```

### Groq
Extremely fast inference, great for low-latency voice agents.

- **Models**: `llama3-70b-8192`, `mixtral-8x7b-32768`
- **Config**:
  ```json
  "llm_agent": {
    "llm_config": {
      "provider": "groq",
      "model": "llama3-70b-8192"
    }
  }
  ```

---

## 🔊 Text-to-Speech (TTS)

### ElevenLabs
Industry standard for natural, emotional voices.

- **Website**: [elevenlabs.io](https://elevenlabs.io)
- **Config**:
  ```json
  "synthesizer": {
    "provider": "elevenlabs",
    "provider_config": {
      "voice_id": "JBFqnCBsd6RMkjVDRZzb", // George
      "model": "eleven_turbo_v2_5" // Low latency model
    }
  }
  ```

### Cartesia (Sonic)
Ultra-low latency (<100ms) TTS.

- **Config**:
  ```json
  "synthesizer": {
    "provider": "cartesia",
    "provider_config": {
      "voice_id": "..."
    }
  }
  ```

---

## 📞 Telephony

### Twilio
1. Buy a phone number in Twilio Console.
2. Configure the **Voice Webhook** for that number to point to your Sunona instance:
   - URL: `https://your-domain.com/api/v1/telephony/twilio/voice`
   - Method: `POST`
3. Set `TWILIO_ACCOUNT_SID` and `TWILIO_AUTH_TOKEN` in `.env`.

### Plivo
1. Buy a number in Plivo Console.
2. Create an Application in Plivo.
3. Set the **Answer URL** to:
   - URL: `https://your-domain.com/api/v1/telephony/plivo/voice`
   - Method: `POST`
4. Link the application to your number.
