import requests
import json

def create_agent():
    url = "http://localhost:5001/agent"
    
    payload = {
        "agent_config": {
            "agent_name": "Customer Service Agent",
            "agent_type": "other",
            "tasks": [
                {
                    "task_type": "conversation",
                    "toolchain": {
                        "execution": "parallel",
                        "pipelines": [
                            ["transcriber", "llm_agent", "synthesizer"]
                        ]
                    },
                    "tools_config": {
                        "input": {
                            "provider": "twilio",
                            "format": "wav"
                        },
                        "output": {
                            "provider": "twilio",
                            "format": "wav"
                        },
                        "llm_agent": {
                            "agent_flow_type": "streaming",
                            "agent_type": "simple_llm_agent",
                            "llm_config": {
                                "provider": "openrouter",
                                "model": "mistralai/mistral-7b-instruct",
                                "max_tokens": 100,
                                "agent_type": "simple_llm_agent",
                                "agent_flow_type": "streaming"
                            }
                        },
                        "synthesizer": {
                            "provider": "polly",
                            "provider_config": {
                                "voice": "Joanna",
                                "engine": "neural",
                                "language": "en-US"
                            },
                            "stream": True,
                            "buffer_size": 40,
                            "audio_format": "pcm"
                        },
                        "transcriber": {
                            "provider": "deepgram",
                            "model": "nova-2",
                            "stream": True,
                            "language": "en",
                            "encoding": "linear16",
                            "sampling_rate": 8000
                        }
                    }
                }
            ],
            "agent_welcome_message": "Hello, thank you for calling customer service. How may I assist you today?"
        },
        "agent_prompts": {
            "task_1": {
                "system_prompt": "You are a helpful and polite customer service representative. Assist the user with their inquiries efficiently."
            }
        }
    }

    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        data = response.json()
        agent_id = data.get("agent_id")
        print(f"Agent created successfully! Agent ID: {agent_id}")
        
        with open("agent_id.txt", "w") as f:
            f.write(agent_id)

        print("\nTo initiate a call, run the following command:")
        print(f'curl -X POST http://localhost:8001/call -H "Content-Type: application/json" -d \'{{"agent_id": "{agent_id}", "recipient_phone_number": "+917075488154"}}\'')
        
        return agent_id
    except Exception as e:
        print(f"Error creating agent: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response content: {e.response.text}")
        return None

if __name__ == "__main__":
    create_agent()
