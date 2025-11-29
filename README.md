# Sunona - Voice AI Platform

<div align="center">

<img src="https://img.shields.io/badge/Python-3.8%2B-blue?style=flat-square&logo=python" alt="Python 3.8+">
<img src="https://img.shields.io/badge/FastAPI-0.108%2B-009688?style=flat-square&logo=fastapi" alt="FastAPI">
<img src="https://img.shields.io/badge/React-18%2B-61DAFB?style=flat-square&logo=react" alt="React">
<img src="https://img.shields.io/badge/License-MIT-green?style=flat-square" alt="MIT">

**Build voice AI agents in minutes. Deploy to production instantly.**

[🚀 Quick Start](#quick-start) • [📚 Docs](#documentation) • [💬 Discord](https://discord.gg/59kQWGgnm8) • [🐛 Issues](https://github.com/sunona-ai/sunona/issues)

</div>

---

## What is Sunona?

Sunona is a **production-ready platform** for building intelligent voice conversational agents. It handles everything from speech recognition to LLM processing to voice synthesis - all in real-time.

### Key Features

✅ **Real-time voice conversations** with <500ms latency  
✅ **50+ AI providers** - swap between OpenAI, Anthropic, Groq, etc without code changes  
✅ **7 STT + 10 TTS options** - Deepgram, ElevenLabs, Azure, and more  
✅ **Smart interruption handling** - detect when users speak over the agent  
✅ **Cost tracking per component** - see exactly what you spend on STT/LLM/TTS  
✅ **Graph-based conversations** - multi-branch dialogue flows  
✅ **RAG ready** - knowledge base integration (LanceDB, MongoDB, etc)  
✅ **Enterprise security** - RBAC, audit logs, encryption, self-hosted option  

---

## Quick Start

### 1️⃣ Prerequisites

```bash
# Required
- Python 3.8+
- Node.js 18+
- Docker & Docker Compose

# Get API keys (free tiers available)
- OPENAI_API_KEY (or use alternatives like Groq, Claude)
- DEEPGRAM_AUTH_TOKEN (speech-to-text)
- ELEVENLABS_API_KEY (text-to-speech)
```

### 2️⃣ Clone & Setup (2 minutes)

```bash
git clone https://github.com/sunona-ai/sunona.git
cd sunona/local_setup

# Copy environment file
cp .env.sample .env

# Edit .env with your API keys
nano .env
```

**Required in .env:**
```bash
OPENAI_API_KEY=sk-...
DEEPGRAM_AUTH_TOKEN=...
ELEVENLABS_API_KEY=...
JWT_SECRET_KEY=$(openssl rand -hex 32)
```

### 3️⃣ Run Everything (1 command)

```bash
# Start all services: backend, frontend, postgres, redis, twilio, plivo
docker-compose up --build

# ✅ Services ready:
# - Backend API: http://localhost:5001 (Swagger: /docs)
# - Frontend: http://localhost:5173
# - PostgreSQL: localhost:5432
# - Redis: localhost:6379
```

---

## Create Your First Agent (5 minutes)

### Step 1: Create Agent via API

```bash
curl -X POST http://localhost:5001/agent \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "agent_config": {
      "agent_name": "Support Bot",
      "agent_type": "simple",
      "tasks": [{
        "task_type": "conversation",
        "toolchain": {
          "execution": "parallel",
          "pipelines": [["transcriber", "llm", "synthesizer"]]
        },
        "tools_config": {
          "transcriber": {
            "provider": "deepgram",
            "model": "nova-2",
            "language": "en"
          },
          "llm_agent": {
            "agent_type": "simple_llm_agent",
            "llm_config": {
              "provider": "openai",
              "model": "gpt-4o-mini",
              "temperature": 0.7
            }
          },
          "synthesizer": {
            "provider": "elevenlabs",
            "provider_config": {
              "voice": "George",
              "voice_id": "JBFqnCBsd6RMkjVDRZzb"
            }
          }
        }
      }]
    },
    "agent_prompts": {
      "task_1": {
        "system_prompt": "You are a helpful customer support agent."
      }
    }
  }'
```

**Response:**
```json
{
  "agent_id": "550e8400-e29b-41d4-a716-446655440000",
  "state": "created"
}
```

### Step 2: Make a Call

```bash
curl -X POST http://localhost:5001/call/initiate \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "agent_id": "550e8400-e29b-41d4-a716-446655440000",
    "phone_number": "+1234567890",
    "provider": "twilio"
  }'
```

### Step 3: Monitor in Real-time

```bash
# Get analytics
curl http://localhost:5001/analytics/calls \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## Architecture (Simple Overview)

```
User (Phone/Browser)
       ↓
  [Twilio/Plivo/WebRTC]
       ↓
   FastAPI Backend (5001)
       ↓
  ┌────┴────┬────────┬──────────┐
  ↓         ↓        ↓          ↓
Deepgram  GPT-4o  ElevenLabs  Database
(STT)     (LLM)    (TTS)    (Postgres/Redis)
  ↓         ↓        ↓          ↓
  └────┬────┴────────┴──────────┘
       ↓
Real-time voice response
```

---

## Directory Structure

```
sunona/
├── ui/                    # React frontend (port 5173)
├── api/v1/               # FastAPI endpoints
├── sunona/               # Core orchestration engine
│   ├── llms/            # LLM integrations
│   ├── transcriber/     # Speech-to-text
│   ├── synthesizer/     # Text-to-speech
│   ├── agent_manager/   # Conversation logic
│   └── ...
├── services/            # Business logic (agents, calls, analytics)
├── database/            # PostgreSQL models
├── local_setup/         # Docker compose & setup
└── examples/            # Code samples
```

---

## Supported Providers

### Speech-to-Text (Pick one)
- **Deepgram** - ⚡ Fastest (300-400ms)
- Azure, Google Cloud, Whisper, Sarvam, AssemblyAI

### LLM (Pick one or more)
- **OpenAI** - GPT-4o, GPT-4o-mini
- Anthropic (Claude), Groq, DeepSeek, LiteLLM (100+ models)

### Text-to-Speech (Pick one)
- **ElevenLabs** - Most natural voices
- AWS Polly, Azure, Deepgram, Cartesia, Rime, OpenAI, Sarvam

### Telephony
- **Twilio** - PSTN calls
- **Plivo** - Alternative carrier
- **Exotel** - Regional coverage

---

## API Endpoints

### Authentication
```bash
POST /auth/login              # Get JWT token
```

### Agents
```bash
POST /agent                   # Create agent
GET /agent/{id}              # Get agent
PUT /agent/{id}              # Update agent
DELETE /agent/{id}           # Delete agent
GET /agents/all              # List all agents
```

### Calls
```bash
POST /call/initiate          # Start call
GET /call/{id}/status        # Get call status
POST /call/{id}/hangup       # End call
WS /ws/call/{id}             # Real-time streaming
```

### Analytics
```bash
GET /analytics/calls         # Call metrics
GET /analytics/costs         # Cost breakdown
GET /wallet/balance          # User balance
```

---

## Code Examples

### Python - Text-Only Agent

```python
import asyncio
from sunona.assistant import Assistant
from sunona.models import LlmAgent, SimpleLlmAgent

async def main():
    assistant = Assistant(name="support_bot")
    
    llm = LlmAgent(
        agent_type="simple_llm_agent",
        agent_flow_type="streaming",
        llm_config=SimpleLlmAgent(
            provider="openai",
            model="gpt-4o-mini",
            system_prompt="You are a helpful support agent."
        ),
    )
    
    assistant.add_task(
        task_type="conversation",
        llm_agent=llm,
        enable_textual_input=True,
    )
    
    async for chunk in assistant.execute():
        print(chunk)

asyncio.run(main())
```

### Python - Full Voice Agent

```python
import asyncio
from sunona.assistant import Assistant
from sunona.models import (
    Transcriber, Synthesizer, ElevenLabsConfig,
    LlmAgent, SimpleLlmAgent
)

async def main():
    assistant = Assistant(name="voice_bot")
    
    transcriber = Transcriber(
        provider="deepgram",
        model="nova-2",
        language="en",
        stream=True
    )
    
    llm = LlmAgent(
        agent_type="simple_llm_agent",
        agent_flow_type="streaming",
        llm_config=SimpleLlmAgent(
            provider="openai",
            model="gpt-4o-mini"
        ),
    )
    
    synthesizer = Synthesizer(
        provider="elevenlabs",
        provider_config=ElevenLabsConfig(
            voice="George",
            voice_id="JBFqnCBsd6RMkjVDRZzb"
        ),
        stream=True
    )
    
    assistant.add_task(
        task_type="conversation",
        llm_agent=llm,
        transcriber=transcriber,
        synthesizer=synthesizer
    )
    
    async for chunk in assistant.execute():
        print(chunk)

asyncio.run(main())
```

### Graph Agent - Multi-Branch Conversations

```python
from sunona.models import LlmAgent, GraphAgentConfig, GraphNode, GraphEdge

nodes = [
    GraphNode(
        id="welcome",
        prompt="Greet customer",
        edges=[
            GraphEdge(to_node_id="support", condition="has_issue"),
            GraphEdge(to_node_id="sales", condition="wants_product")
        ]
    ),
    GraphNode(id="support", prompt="Help resolve issue", edges=[]),
    GraphNode(id="sales", prompt="Sell product", edges=[]),
]

agent = LlmAgent(
    agent_type="graph_agent",
    llm_config=GraphAgentConfig(
        provider="openai",
        model="gpt-4o",
        nodes=nodes,
        current_node_id="welcome"
    ),
)
```

---

## Environment Variables

### Required
```bash
# LLM
OPENAI_API_KEY=sk-...
JWT_SECRET_KEY=your-secret-key

# STT
DEEPGRAM_AUTH_TOKEN=...

# TTS
ELEVENLABS_API_KEY=...

# Database
POSTGRES_URL=postgresql://user:pass@localhost:5432/sunona_db
REDIS_URL=redis://localhost:6379/0
```

### Optional (Telephony)
```bash
# Twilio
TWILIO_ACCOUNT_SID=AC...
TWILIO_AUTH_TOKEN=...
TWILIO_PHONE_NUMBER=+1...

# Or Plivo
PLIVO_AUTH_ID=...
PLIVO_AUTH_TOKEN=...
PLIVO_PHONE_NUMBER=...
```

---

## Performance (Typical Latencies)

| Component | Latency |
|-----------|---------|
| STT (Deepgram) | 300-400ms |
| LLM (GPT-4o-mini) | 400-800ms |
| TTS (ElevenLabs) | 200-300ms |
| Total End-to-End | 2.5-5s |

---

## Local Development (Alternative)

```bash
# Terminal 1: Backend
cd sunona
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows
pip install -r requirements.txt
python -m uvicorn local_setup.local_server:app --reload

# Terminal 2: Frontend
cd ui
npm install
npm run dev

# Terminal 3: Database (optional)
docker run -d -e POSTGRES_PASSWORD=password -p 5432:5432 postgres:15
```

---

## Webhooks

Configure webhooks in agent settings:

```json
{
  "webhooks": {
    "call.started": "https://your-app.com/hooks/call-started",
    "call.transcription": "https://your-app.com/hooks/transcription",
    "call.ended": "https://your-app.com/hooks/call-ended"
  }
}
```

**Webhook payload example:**
```json
{
  "event": "call.ended",
  "call_id": "call-123",
  "duration_seconds": 245,
  "transcript": "User: Hello... Agent: ...",
  "cost": {
    "stt": 0.026,
    "llm": 0.045,
    "tts": 0.052,
    "total": 0.123
  }
}
```

---

## Testing

```bash
# Backend tests
pytest tests/ -v

# Frontend tests
cd ui && npm run test

# Integration tests
pytest tests/integration/ -v
```

---

## Troubleshooting

### Services won't start?
```bash
# Check Docker
docker-compose logs -f

# Reset everything
docker-compose down -v
docker-compose up --build
```

### API errors?
```bash
# Check logs
docker-compose logs sunona-app

# Verify services
curl http://localhost:5001/docs
```

### Database issues?
```bash
# Connect to PostgreSQL
psql postgresql://sunona_user:sunona_password@localhost:5432/sunona_db

# Check agents
SELECT * FROM agents;
```

---

## Documentation

- **[Full Architecture Guide](./architecture.md)** - Deep dive into system design
- **[API Reference](./API.md)** - Complete endpoint documentation
- **[Provider Configuration](./providers.md)** - Setup each provider
- **[Deployment Guide](./deployment.md)** - Production setup

---

## Contributing

We welcome contributions! 

```bash
# 1. Fork repo
git clone https://github.com/your-username/sunona.git

# 2. Create feature branch
git checkout -b feature/amazing-feature

# 3. Make changes
# ... edit files ...

# 4. Test
pytest tests/ -v

# 5. Commit & push
git commit -m "Add amazing feature"
git push origin feature/amazing-feature

# 6. Open pull request
```

---

## Community & Support

- **GitHub Issues**: [Report bugs](https://github.com/sunona-ai/sunona/issues)
- **Discussions**: [Ask questions](https://github.com/sunona-ai/sunona/discussions)
- **Discord**: [Chat with us](https://discord.gg/59kQWGgnm8)
- **Email**: support@sunona.dev
- **Twitter**: [@sunonaai](https://twitter.com/sunonaai)

---

## License

MIT License - see [LICENSE](./LICENSE) for details

---

## Comparison

| Feature | Sunona | Pipecat | Vapi | AWS Connect |
|---------|--------|---------|------|-------------|
| Real-time Bi-directional | ✅ | ✅ | ⚠️ | ✅ |
| Multi-Provider Support | ✅ 50+ | ⚠️ Limited | ✅ 10+ | ❌ AWS only |
| Cost Per Component | ✅ Yes | ❌ No | ⚠️ Limited | ❌ No |
| Self-hosted | ✅ Docker | ❌ Cloud only | ❌ Cloud only | ✅ AWS |
| Open Source | ✅ MIT | ✅ MIT | ❌ Closed | ❌ Closed |
| Time to Deploy | ✅ 5 min | ⚠️ 30 min | ✅ 10 min | ⚠️ 1 hour |

---

<div align="center">

**⭐ Star this repo if Sunona helps you build amazing voice AI!**

Built with ❤️ for the voice AI community

</div>
