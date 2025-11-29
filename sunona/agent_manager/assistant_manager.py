import copy
import time
import uuid

from .base_manager import BaseManager
from .task_manager import TaskManager
from sunona.helpers.logger_config import configure_logger
from sunona.models import AGENT_WELCOME_MESSAGE
from sunona.helpers.utils import update_prompt_with_context

logger = configure_logger(__name__)


class AssistantManager(BaseManager):
    def __init__(self, agent_config, ws=None, assistant_id=None, user_id=None, context_data=None, conversation_history=None,
                 turn_based_conversation=None, cache=None, input_queue=None, output_queue=None, **kwargs):
        super().__init__()
        self.run_id = str(uuid.uuid4())
        self.assistant_id = assistant_id
        self.user_id = user_id  # NEW: For database tracking
        self.call_tracker = None  # NEW: Call tracker instance
        self.tools = {}
        self.websocket = ws
        self.agent_config = agent_config
        self.context_data = context_data
        self.tasks = agent_config.get('tasks', [])
        self.task_states = [False] * len(self.tasks)
        self.turn_based_conversation = turn_based_conversation
        self.cache = cache
        self.input_queue = input_queue
        self.output_queue = output_queue
        self.kwargs = kwargs
        self.conversation_history = conversation_history
        if kwargs.get("is_web_based_call", False):
            self.kwargs['agent_welcome_message'] = agent_config.get('agent_welcome_message', AGENT_WELCOME_MESSAGE)
        else:
            self.kwargs['agent_welcome_message'] = update_prompt_with_context(
                agent_config.get('agent_welcome_message', AGENT_WELCOME_MESSAGE), context_data)

    async def run(self, local=False, run_id=None):
        """
        Run will start all tasks in sequential format
        """
        if run_id:
            self.run_id = run_id

        # Initialize call tracker if user_id is provided
        if self.user_id and self.assistant_id:
            try:
                from sunona.helpers.call_tracker import CallTracker, set_current_tracker
                self.call_tracker = CallTracker(
                    user_id=self.user_id,
                    agent_id=self.assistant_id,
                    phone_number=self.kwargs.get('phone_number'),
                    direction=self.kwargs.get('direction', 'outbound')
                )
                self.call_tracker.set_providers(self.agent_config)
                await self.call_tracker.start_call(self.kwargs.get('call_sid'))
                set_current_tracker(self.call_tracker)
                logger.info(f"✅ Call tracking started for user {self.user_id}")
            except Exception as e:
                logger.warning(f"Failed to initialize call tracker: {e}")
                self.call_tracker = None

        input_parameters = None
        for task_id, task in enumerate(self.tasks):
            logger.info(f"Running task {task_id}")
            task_manager = TaskManager(self.agent_config.get("agent_name", self.agent_config.get("assistant_name")),
                                       task_id, task, self.websocket,
                                       context_data=self.context_data, input_parameters=input_parameters,
                                       assistant_id=self.assistant_id, run_id=self.run_id,
                                       turn_based_conversation=self.turn_based_conversation,
                                       cache=self.cache, input_queue=self.input_queue, output_queue=self.output_queue,
                                       conversation_history=self.conversation_history, **self.kwargs)
            await task_manager.load_prompt(self.agent_config.get("agent_name", self.agent_config.get("assistant_name")),
                                           task_id, local=local, **self.kwargs)
            task_output = await task_manager.run()
            task_output['run_id'] = self.run_id
            yield task_id, copy.deepcopy(task_output)
            self.task_states[task_id] = True
            if task_id == 0:
                input_parameters = task_output
            if task["task_type"] == "extraction":
                input_parameters["extraction_details"] = task_output["extracted_data"]
        
        # End call tracking and calculate costs
        if self.call_tracker:
            try:
                from sunona.helpers.call_tracker import clear_current_tracker
                cost_data = await self.call_tracker.end_call(self.agent_config)
                clear_current_tracker()
                if cost_data:
                    logger.info(f"✅ Call ended. Total cost: ${cost_data['total_cost']:.4f}")
                    logger.info(f"   Breakdown: LLM=${cost_data['breakdown']['llm_cost']:.4f}, "
                              f"TTS=${cost_data['breakdown']['tts_cost']:.4f}, "
                              f"STT=${cost_data['breakdown']['stt_cost']:.4f}, "
                              f"Telephony=${cost_data['breakdown']['telephony_cost']:.4f}, "
                              f"Platform Fee=${cost_data['breakdown']['platform_fee']:.4f}")
            except Exception as e:
                logger.error(f"Failed to end call tracking: {e}")
        
        logger.info("Done with execution of the agent")
