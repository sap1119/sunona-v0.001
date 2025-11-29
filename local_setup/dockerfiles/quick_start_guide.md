# Deep Core Setup & Usage Guide

This document provides a comprehensive, step-by-step guide to running the sunona AI project using bash commands. It covers setup, building, running, and using the system.

## 1. Prerequisites

Ensure you have the following installed:
- **Docker Desktop** (with Docker Compose V2)
- **Git**
- **Curl** (for making API requests)

Ensure you have a `.env` file in `local_setup/` with the following credentials:
- `TWILIO_ACCOUNT_SID`
- `TWILIO_AUTH_TOKEN`
- `TWILIO_PHONE_NUMBER`
- `OPENAI_API_KEY` (or OpenRouter key if using OpenRouter)
- `DEEPGRAM_AUTH_TOKEN`
- `AWS_ACCESS_KEY_ID` (for Polly)
- `AWS_SECRET_ACCESS_KEY` (for Polly)
- `AWS_REGION` (for Polly)

## 2. Docker Environment Setup

Navigate to the setup directory:
```bash
cd local_setup
```

### Build Images
Enable BuildKit for faster builds and build the services:
```bash
export DOCKER_BUILDKIT=1
export COMPOSE_DOCKER_CLI_BUILD=1
docker compose build
```

### Start Services
Start all containers in detached mode:
```bash
docker compose up -d
```

### Verify Status
Check if all containers are running (sunona-app, twilio-app, plivo-app, redis, ngrok):
```bash
docker compose ps
```

View logs for specific services if needed:
```bash
docker compose logs -f sunona-app
docker compose logs -f twilio-app
```

## 3. Agent Management

### Create Customer Service Agent
We have provided a script `create_test_agent.py` to create a pre-configured Customer Service Agent using OpenRouter.

Run the script:
```bash
python create_test_agent.py
```
This will:
1. Create an agent with the role "Customer Service Representative".
2. Configure it to use `mistralai/mistral-7b-instruct` via OpenRouter.
3. Save the Agent ID to `agent_id.txt`.
4. Print the curl command to initiate a call.

### List All Agents
To see all created agents:
```bash
curl http://localhost:5001/all
```

## 4. Initiating Calls

To initiate a call, use the `curl` command. 

**Using the Customer Service Agent:**
```bash
# Replace with your actual Agent ID if different
AGENT_ID=$(cat agent_id.txt)
RECIPIENT="+917075488154"

curl -X POST http://localhost:8001/call \
  -H "Content-Type: application/json" \
  -d "{\"agent_id\": \"$AGENT_ID\", \"recipient_phone_number\": \"$RECIPIENT\"}"
```

## 5. Troubleshooting

### Common Issues

**1. Build Failures**
- **Issue**: Dependency conflicts or network errors during build.
- **Fix**: Ensure `requirements_minimal.txt` is up to date and try building without cache:
  ```bash
  docker compose build --no-cache
  ```

**2. Call Not Initiated**
- **Issue**: Curl command returns success but no call is received.
- **Fix**: Check `twilio-app` logs for errors:
  ```bash
  docker compose logs twilio-app
  ```
  Ensure your Twilio credentials in `.env` are correct and the account has funds/credits.

**3. Agent Not Responding**
- **Issue**: Call connects but agent is silent.
- **Fix**: Check `sunona-app` logs:
  ```bash
  docker compose logs sunona-app
  ```
  Verify your LLM (OpenAI/OpenRouter) and Transcriber (Deepgram) API keys are valid.

## 6. Cleanup

To stop all services:
```bash
docker compose down
```

To stop and remove volumes (warning: deletes agent data):
```bash
docker compose down -v
```
