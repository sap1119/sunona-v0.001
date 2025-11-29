
from sunona.models import Task, ToolsConfig, ToolsChainModel, ConversationConfig

try:
    t = Task(
        tools_config=ToolsConfig(),
        toolchain=ToolsChainModel(execution="parallel", pipelines=[])
    )
    print(f"Task dict: {t.dict()}")
    print(f"Task config type: {type(t.task_config)}")
    print(f"Task config value: {t.task_config}")
except Exception as e:
    print(f"Error: {e}")
