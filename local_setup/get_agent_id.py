import requests
import json

def get_agent_id():
    try:
        response = requests.get("http://localhost:5001/all")
        data = response.json()
        agents = data.get("agents", [])
        for agent in agents:
            agent_data = agent.get("data", {})
            if agent_data.get("agent_config", {}).get("agent_name") == "Customer Service Agent":
                print(agent.get("agent_id"))
                return
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    get_agent_id()
