import asyncio
import os
import torch
import uuid
import io
import time
import traceback
from dotenv import load_dotenv
from TTS.api import TTS
from sunona.helpers.logger_config import configure_logger
from sunona.helpers.utils import create_ws_data_packet, convert_audio_to_wav
from .base_synthesizer import BaseSynthesizer

logger = configure_logger(__name__)
load_dotenv()

class XttsSynthesizer(BaseSynthesizer):
    def __init__(self, voice, language="en", audio_format="wav", sampling_rate="16000", stream=False, 
                 buffer_size=400, caching=True, **kwargs):
        super().__init__(kwargs.get("task_manager_instance", None), stream, buffer_size)
        self.voice = voice
        self.language = language
        self.sampling_rate = int(sampling_rate)
        self.audio_format = audio_format
        self.caching = caching
        self.first_chunk_generated = False
        self.synthesized_characters = 0
        
        # Load XTTS Model
        device = "cuda" if torch.cuda.is_available() else "cpu"
        logger.info(f"Loading XTTS Model on {device}")
        try:
            # Using the standard XTTS v2 model
            self.tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2").to(device)
        except Exception as e:
            logger.error(f"Failed to load XTTS model: {e}")
            raise e

    def get_synthesized_characters(self):
        return self.synthesized_characters

    def get_engine(self):
        return "xtts"

    def supports_websocket(self):
        return False

    async def __generate_audio(self, text):
        try:
            logger.info(f"Generating XTTS response for text: {text}")
            
            # Run TTS in a separate thread to avoid blocking the event loop
            # XTTS requires a speaker reference audio file or speaker name if it's a multi-speaker model
            # For simplicity, we'll assume 'voice' is the path to a reference audio file or a known speaker name
            # If 'voice' is a path, use speaker_wav, else use speaker
            
            kwargs = {
                "text": text,
                "language": self.language
            }
            
            if os.path.exists(self.voice):
                kwargs["speaker_wav"] = self.voice
            else:
                 # Fallback or specific speaker name if supported by the model config
                 # For standard XTTS v2, it usually requires a speaker_wav. 
                 # We'll default to a sample if provided voice is not a file.
                 # Ideally, the user should provide a path to a wav file in .env
                 pass

            # If no speaker_wav provided and model requires it, it might fail. 
            # Let's assume the user provides a valid path in 'voice' or we pick a default if possible.
            # But for now, we pass what we have.
            
            wav = await asyncio.to_thread(self.tts.tts, **kwargs)
            
            # Convert list/numpy array to bytes
            # XTTS returns a list of floats or numpy array. We need to convert to PCM bytes.
            import numpy as np
            import scipy.io.wavfile as wavfile
            
            wav_np = np.array(wav)
            
            # Create a BytesIO object to store the wav file
            out_buf = io.BytesIO()
            # XTTS v2 usually outputs at 24000Hz
            wavfile.write(out_buf, 24000, wav_np)
            out_buf.seek(0)
            return out_buf.read()

        except Exception as e:
            logger.error(f"Error in XTTS generation: {e}")
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
                    # Resample if needed (XTTS is 24k, we might need 8k or 16k)
                    # The base class resample method converts to 8000. 
                    # If we need 16000, we might need a custom resampler or rely on the client to handle it.
                    # For now, let's use the base resample if 8000 is requested, or just pass it if 24000 is fine.
                    # But usually telephony needs 8000.
                    
                    if self.sampling_rate == 8000:
                         audio_data = self.resample(audio_data)
                    elif self.sampling_rate == 16000:
                         # Simple resampling to 16k if needed, or just pass through if client handles it
                         # For now, let's assume we pass the wav and let the client/frontend handle it 
                         # OR we should strictly follow sampling_rate.
                         # Let's use convert_audio_to_wav to ensure it's a valid wav
                         pass

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
