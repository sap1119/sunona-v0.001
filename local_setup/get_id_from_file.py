import json
import codecs

def get_id_from_file():
    try:
        # Try reading as utf-16 (powershell default for >)
        with codecs.open("agents.json", "r", "utf-16") as f:
            content = f.read()
    except:
        # Fallback to utf-8
        with open("agents.json", "r") as f:
            content = f.read()
            
    try:
        data = json.loads(content)
        agents = data.get("agents", [])
        for agent in agents:
            agent_data = agent.get("data", {})
            if agent_data.get("agent_config", {}).get("agent_name") == "Customer Service Agent":
                print(agent.get("agent_id"))
                return
    except Exception as e:
        print(f"Error parsing json: {e}")

if __name__ == "__main__":
    get_id_from_file()
