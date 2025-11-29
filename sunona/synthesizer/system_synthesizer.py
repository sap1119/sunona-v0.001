import asyncio
import pyttsx3
import uuid
import io
import time
import traceback
import wave
from sunona.helpers.logger_config import configure_logger
from sunona.helpers.utils import create_ws_data_packet
from .base_synthesizer import BaseSynthesizer

logger = configure_logger(__name__)

class SystemSynthesizer(BaseSynthesizer):
    def __init__(self, voice=None, language="en", audio_format="wav", sampling_rate="16000", stream=False, 
                 buffer_size=400, caching=True, **kwargs):
        super().__init__(kwargs.get("task_manager_instance", None), stream, buffer_size)
        
        # voice and language come as direct kwargs when instantiated by TaskManager
        # (provider_config is unpacked as **provider_config)
        self.voice = voice
        self.language = language
        self.sampling_rate = int(sampling_rate)
        self.audio_format = audio_format
        self.caching = caching
        self.first_chunk_generated = False
        self.synthesized_characters = 0
        
        # Initialize pyttsx3
        try:
            self.engine = pyttsx3.init()
            # Set properties if needed (rate, volume, voice)
            self.engine.setProperty('rate', 150) 
            
            # Try to set voice if provided, else default
            if self.voice:
                voices = self.engine.getProperty('voices')
                for v in voices:
                    if self.voice.lower() in v.name.lower() or self.voice in v.id:
                        self.engine.setProperty('voice', v.id)
                        break
        except Exception as e:
            logger.error(f"Failed to initialize pyttsx3: {e}")
            raise e

    def get_synthesized_characters(self):
        return self.synthesized_characters

    def get_engine(self):
        return "system"

    def supports_websocket(self):
        return False

    async def __generate_audio(self, text):
        try:
            logger.info(f"Generating System TTS response for text: {text}")
            
            # pyttsx3 save_to_file is blocking, run in thread
            # Also it saves to a file, so we need a temp file
            import tempfile
            import os
            
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as fp:
                temp_filename = fp.name
                
            # We need to run the loop in a way that doesn't conflict with the main loop
            # pyttsx3 engine loop is tricky. 
            # Ideally we should initialize a new engine instance per thread or use a lock.
            # For simplicity in this async context, we'll try to run it in a thread with a new init if possible
            # or just use the existing one if it's thread safe (it's usually not).
            # A safer way for pyttsx3 in async is to use a separate process or very careful locking.
            # Let's try a simple approach first: Re-init in the thread to be safe? No, COM objects are thread bound.
            # We must run the engine in the same thread it was created, OR create it in the worker thread.
            
            def _synthesize_worker(text, filename):
                # Initialize a new engine instance for this thread to avoid COM issues
                engine = pyttsx3.init()
                engine.save_to_file(text, filename)
                engine.runAndWait()
                # engine.stop() # runAndWait blocks until done
                
            await asyncio.to_thread(_synthesize_worker, text, temp_filename)
            
            # Read the file back
            if os.path.exists(temp_filename):
                with open(temp_filename, "rb") as f:
                    wav_data = f.read()
                os.remove(temp_filename)
                return wav_data
            return None

        except Exception as e:
            logger.error(f"Error in System TTS generation: {e}")
            traceback.print_exc()
            return None

    async def generate(self):
        while True:
            try:
                message = await self.internal_queue.get()
                logger.info(f"Generating TTS response for message: {message}")
                meta_info, text = message.get("meta_info"), message.get("data")

                if not self.should_synthesize_response(meta_info.get('sequence_id')):
                    logger.info(f"Skipping synthesis for sequence_id {meta_info.get('sequence_id')}")
                    continue

                self.synthesized_characters += len(text)

            # Track TTS usage for cost calculation
            try:
                from sunona.helpers.call_tracker import get_current_tracker
                tracker = get_current_tracker()
                if tracker and text:
                    tracker.track_tts_usage(len(text))
            except Exception as track_error:
                logger.warning(f"Failed to track TTS usage: {track_error}")
                
                audio_data = await self.__generate_audio(text)
                
                if audio_data:
                    # Resample if needed. pyttsx3 usually outputs 22050 or system default.
                    # We might need to resample to self.sampling_rate (e.g. 8000 or 16000)
                    # Using base class resample (which goes to 8000) or custom.
                    # Let's assume we use the base resample if 8000 is needed.
                    
                    if self.sampling_rate == 8000:
                         audio_data = self.resample(audio_data)
                    
                    if not self.first_chunk_generated:
                        meta_info["is_first_chunk"] = True
                        self.first_chunk_generated = True
                    else:
                        meta_info["is_first_chunk"] = False

                    if "end_of_llm_stream" in meta_info and meta_info["end_of_llm_stream"]:
                        meta_info["end_of_synthesizer_stream"] = True
                        self.first_chunk_generated = False

                    meta_info['text'] = text
                    meta_info['format'] = 'wav'
                    meta_info["text_synthesized"] = text
                    meta_info["mark_id"] = str(uuid.uuid4())
                    
                    yield create_ws_data_packet(audio_data, meta_info)
            except Exception as e:
                logger.error(f"Error in generate loop: {e}")
                traceback.print_exc()

    async def push(self, message):
        logger.info("Pushed message to internal queue")
        self.internal_queue.put_nowait(message)
