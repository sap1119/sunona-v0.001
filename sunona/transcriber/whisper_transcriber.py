import asyncio
import numpy as np
import os
import time
import traceback
import webrtcvad
from dotenv import load_dotenv
from faster_whisper import WhisperModel

from .base_transcriber import BaseTranscriber
from sunona.helpers.logger_config import configure_logger
from sunona.helpers.utils import create_ws_data_packet

logger = configure_logger(__name__)
load_dotenv()

class WhisperTranscriber(BaseTranscriber):
    def __init__(self, telephony_provider, input_queue=None, model='tiny', stream=True, language="en", endpointing="400",
                 sampling_rate="16000", encoding="linear16", output_queue=None, keywords=None,
                 process_interim_results="true", **kwargs):
        super().__init__(input_queue)
        self.language = language
        self.stream = stream
        self.provider = telephony_provider
        self.model_size = model if model in ["tiny", "base", "small", "medium", "large-v2", "large-v3"] else "base"
        self.sampling_rate = int(sampling_rate)
        self.encoding = encoding
        self.transcriber_output_queue = output_queue
        self.transcription_task = None
        self.keywords = keywords
        
        # Initialize Whisper Model
        device = "cuda" if os.getenv("CUDA_VISIBLE_DEVICES") else "cpu"
        compute_type = "float16" if device == "cuda" else "int8"
        
        logger.info(f"Loading Whisper Model: {self.model_size} on {device} ({compute_type})")
        try:
            self.model = WhisperModel(self.model_size, device=device, compute_type=compute_type)
        except Exception as e:
            logger.error(f"Failed to load Whisper model on {device}, falling back to CPU: {e}")
            self.model = WhisperModel(self.model_size, device="cpu", compute_type="int8")

        self.audio_buffer = np.array([], dtype=np.float32)
        self.buffer_threshold_seconds = 1.0 
        self.last_transcription_time = time.time()
        
        # VAD Setup
        self.vad = webrtcvad.Vad(3) # Aggressiveness mode 3
        self.vad_frame_ms = 30
        self.vad_sample_rate = 16000 # webrtcvad supports 8000, 16000, 32000, 48000
        self.speech_detected = False

    async def transcribe(self):

            # Placeholder removed
        logger.info("Started Whisper Transcription")
        try:
            while True:
                ws_data_packet = await self.input_queue.get()
                
                if 'eos' in ws_data_packet.get('meta_info', {}) and ws_data_packet['meta_info']['eos'] is True:
                    logger.info("End of stream received")
                    await self.process_buffer(final=True)
                    break

                audio_data = ws_data_packet.get('data')
                self.meta_info = ws_data_packet.get('meta_info')

                # Convert audio to float32 numpy array for Whisper
                if isinstance(audio_data, bytes):
                    # Check VAD on raw bytes before conversion if possible, or convert to 16-bit PCM for VAD
                    # webrtcvad expects 16-bit PCM mono
                    
                    # Process VAD
                    is_speech = self.process_vad(audio_data)
                    if is_speech and not self.speech_detected:
                        logger.info("Speech detected (VAD)")
                        self.speech_detected = True
                        yield create_ws_data_packet("speech_started", self.meta_info)
                    
                    audio_np = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32) / 32768.0
                else:
                    audio_np = audio_data

                self.audio_buffer = np.concatenate((self.audio_buffer, audio_np))

                # Process if buffer is large enough
                current_audio_duration = len(self.audio_buffer) / self.sampling_rate
                if current_audio_duration >= self.buffer_threshold_seconds:
                    await self.process_buffer()

        except Exception as e:
            logger.error(f"Error in transcription: {e}")
            traceback.print_exc()
        finally:
            await self.push_to_transcriber_queue(create_ws_data_packet("transcriber_connection_closed", self.meta_info))

    def process_vad(self, audio_bytes):
        # webrtcvad needs frames of 10, 20, or 30 ms
        # Assuming 16000 Hz, 16-bit PCM
        # 30ms = 0.03 * 16000 * 2 bytes = 960 bytes
        
        frame_size = int(self.vad_sample_rate * self.vad_frame_ms / 1000) * 2
        
        # If chunk is smaller than frame size, skip (or buffer, but for simplicity skip)
        if len(audio_bytes) < frame_size:
            return False
            
        # Check the first frame of the chunk
        try:
            return self.vad.is_speech(audio_bytes[:frame_size], self.vad_sample_rate)
        except Exception:
            return False

    async def process_buffer(self, final=False):
        if len(self.audio_buffer) == 0:
            return

        start_time = time.time()
        
        segments, info = await asyncio.to_thread(
            self.model.transcribe,
            self.audio_buffer, 
            beam_size=5, 
            language=self.language,
            vad_filter=True
        )

        transcript = " ".join([segment.text for segment in segments]).strip()
        
        if transcript:
            logger.info(f"Whisper Transcript: {transcript}")
            
            data = {
                "type": "transcript",
                "content": transcript,
                "is_final": True 
            }
            
            # Track STT usage
            try:
                from sunona.helpers.call_tracker import get_current_tracker
                tracker = get_current_tracker()
                if tracker:
                    duration = len(self.audio_buffer) / self.sampling_rate
                    tracker.track_stt_usage(duration)
            except Exception as e:
                logger.warning(f"Failed to track STT usage: {e}")
            
            self.meta_info["transcriber_latency"] = time.time() - start_time
            await self.push_to_transcriber_queue(create_ws_data_packet(data, self.meta_info))
            
            # Reset speech detected flag after a transcript is produced (turn end logic simplified)
            self.speech_detected = False

        self.audio_buffer = np.array([], dtype=np.float32)

    async def push_to_transcriber_queue(self, data_packet):
        await self.transcriber_output_queue.put(data_packet)

    async def run(self):
        self.transcription_task = asyncio.create_task(self.transcribe())
