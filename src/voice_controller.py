import logging
import threading
import time
from enum import Enum
from pathlib import Path
from queue import Queue

import httpx
import requests  # type: ignore
from faster_whisper import WhisperModel
from just_playback import Playback
from PyQt6.QtCore import QObject
from PyQt6.QtCore import pyqtSignal as Signal

from src.alltalk_controller import AllTalkController

SOUND_FORMAT = "wav"  # or "wav" or "mp3"


class SpeachesModel:
    model: str
    voice: str
    language: str

    def __init__(self, model: str, voice: str, language: str = "multilingual"):
        self.model = model
        self.voice = voice
        self.language = language


class kokoro_models:
    kokoro_base = SpeachesModel(
        model="speaches-ai/Kokoro-82M-v1.0-ONNX", voice="ff_siwis"
    )
    kokoro_base_int8 = SpeachesModel(
        model="speaches-ai/Kokoro-82M-v1.0-ONNX-int8", voice="ff_siwis"
    )
    kokoro_base_fp16 = SpeachesModel(
        model="speaches-ai/Kokoro-82M-v1.0-ONNX-fp16", voice="ff_siwis"
    )
    kokoro_suronek = SpeachesModel(
        model="suronek/Kokoro-82M-v1.1-zh-ONNX", voice="ff_siwis"
    )
    piper_upmc = SpeachesModel(
        model="speaches-ai/piper-fr_FR-upmc-medium", voice="upmc", language="fr"
    )
    # really bad
    piper_mls = SpeachesModel(
        model="speaches-ai/piper-fr_FR-mls-medium", voice="upmc", language="fr"
    )
    piper_siwis = SpeachesModel(
        model="speaches-ai/piper-fr_FR-siwis-medium", voice="siwis", language="fr"
    )
    # best?
    piper_tom = SpeachesModel(
        model="speaches-ai/piper-fr_FR-tom-medium", voice="tom", language="fr"
    )


class TTS_IMPL(Enum):
    ALLTALK = 0
    COQUI = 1
    SPEACHES = 3


class STT_IMPL(Enum):
    FAST_WHISPER = 0
    REMOTE_FASTER_WHISPER = 1
    SPEACHES = 3


class VoiceController(QObject):
    tts_ready = Signal(str)
    job_done = Signal()

    playback = Playback()

    tts_mode = TTS_IMPL.SPEACHES
    stt_mode = STT_IMPL.SPEACHES

    # Queue for TTS worker
    tts_queue: Queue = Queue(maxsize=1000)
    # Queue for playback worker
    playback_queue: Queue = Queue(maxsize=1000)

    def __init__(self, host: str):
        super().__init__()

        self.received_final_chunk = False
        self.received_final_chunk_to_play = False

        if self.stt_mode == STT_IMPL.FAST_WHISPER:
            model_size = "large-v3"
            model_size = "turbo"
            # Run on GPU with FP16
            self.model = WhisperModel(model_size, device="cpu", compute_type="float32")
            # or run on GPU with INT8
            # model = WhisperModel(model_size, device="cuda", compute_type="int8_float16")
            # or run on CPU with INT8
            # model = WhisperModel(model_size, device="cpu", compute_type="int8")

        if self.tts_mode == TTS_IMPL.SPEACHES or self.stt_mode == STT_IMPL.SPEACHES:
            self.speaches_url = "{}:8000/".format(host)
            logging.info("TTS server on {}".format(self.speaches_url))
            self.tts_client = httpx.Client(base_url=self.speaches_url)
            self.tts_model = kokoro_models.piper_tom
            self.stt_model = "Kelno/whisper-large-v3-french-distil-dec16-ct2"
        elif self.tts_mode != TTS_IMPL.SPEACHES:  ## these were just used during testing
            self.coqui_tts_server = "{}:5002/api/tts".format(host)
            self.alltalk_controller = AllTalkController()

        self.remote_fast_whisper_stt_server = "{}:9876/api/v0/transcribe".format(host)

        self.running = True
        self.tts_thread = threading.Thread(target=self.tts_worker, daemon=True)
        self.tts_thread.start()
        self.playback_thread = threading.Thread(
            target=self.playback_worker, daemon=True
        )
        self.playback_thread.start()
        logging.info("Hello VoiceController!")

    def __del__(self):
        self.stop()

    def reset(self):
        logging.info("VoiceController reset called.")
        self.received_final_chunk = False
        self.received_final_chunk_to_play = False
        self.stop_audio_playback()
        # self.stop()

        # self.running = True
        # self.tts_thread = threading.Thread(target=self.tts_worker, daemon=True)
        # self.tts_thread.start()
        # self.playback_thread = threading.Thread(
        #     target=self.playback_worker, daemon=True
        # )
        # self.playback_thread.start()

    def stop(self):
        logging.info("Stopping VoiceController...")
        self.stop_audio_playback()
        self.running = False
        if self.tts_thread and self.tts_thread.is_alive():
            self.tts_thread.join()
        if self.playback_thread and self.playback_thread.is_alive():
            self.playback_thread.join()
        logging.info(" done.")

    def signal_received_final_text_chunk(self):
        self.received_final_chunk = True

    def push_to_tts_queue(self, text: str):
        logging.info("> TTS queuing text: {}".format(text))
        self.tts_queue.put(text)
        logging.info("> TTS queue size: {}".format(self.tts_queue.qsize()))

    def push_to_playback_queue(self, audio_file_path: str):
        logging.info("> Playback queuing audio file: {}".format(audio_file_path))
        self.playback_queue.put(audio_file_path)
        logging.info("> Playback queue size: {}".format(self.playback_queue.qsize()))

    def tts_worker(self):
        id = 0
        while self.running:
            if self.tts_queue.empty():
                time.sleep(1)
                if self.received_final_chunk:
                    self.received_final_chunk_to_play = True
                continue

            text = self.tts_queue.get()
            id = id + 1
            logging.info("> TTS worker got text: {}".format(text))
            output_file = "user_prompt_{}.{}".format(id, SOUND_FORMAT)
            self.text_to_speech(text, output_file)
            self.tts_ready.emit(output_file)
            self.tts_queue.task_done()

    def playback_worker(self):
        while self.running:
            if self.playback_queue.empty():
                time.sleep(1)
                continue

            audio_file_path = self.playback_queue.get()
            logging.info("> Playback worker got audio file: {}".format(audio_file_path))
            self.play_audio_file(audio_file_path)
            self.playback_queue.task_done()

            # was this the very final thing to do for this whole stt => generation => tts?
            if self.playback_queue.empty():
                if self.received_final_chunk_to_play:
                    # this was the final thing to do.
                    self.job_done.emit()
                    self.reset()

    def text_to_speech(self, text: str, output_file: str):
        logging.info("> TTS starting TTS request")

        if self.tts_mode == TTS_IMPL.SPEACHES:
            res = self.tts_client.post(
                "v1/audio/speech",
                json={
                    "model": self.tts_model.model,
                    "voice": self.tts_model.voice,
                    "input": text,
                    "response_format": SOUND_FORMAT,  # or mp3
                    "speed": 1,
                },
            ).raise_for_status()
            with Path(output_file).open("wb") as f:
                f.write(res.read())

        elif self.tts_mode == TTS_IMPL.ALLTALK:
            _ = self.alltalk_controller.generate_tts(
                text,
                character_voice="female_06.wav",
                language="fr",
                output_file_name="test_output",
                output_file=output_file,
            )

        else:
            headers = {
                # "text": text,
                # "speaker-id": "0",
                "language-id": "fr",
                "style-wav": "",
            }
            params = {"text": text}
            response = requests.post(
                self.coqui_tts_server, headers=headers, params=params
            )
            with open(output_file, "wb") as f:
                f.write(response.content)

        logging.info(f" > TTS output saved to: {output_file}")

    def speech_to_text(self, audio_file_path) -> str:
        if self.stt_mode == STT_IMPL.FAST_WHISPER:
            segments, info = self.model.transcribe(
                audio_file_path, language="fr", beam_size=5
            )

            transcription = ""
            for segment in segments:
                logging.info(
                    "Whisper > [%.2fs -> %.2fs] %s"
                    % (segment.start, segment.end, segment.text)
                )
                transcription = segment.text + " "

            logging.info("Whisper > Transcription complete.")
            return transcription
        elif self.stt_mode == STT_IMPL.REMOTE_FASTER_WHISPER:
            files = {"audio_file": open(audio_file_path, "rb")}
            r = requests.post(self.remote_fast_whisper_stt_server, files=files)
            result = r.json()
            logging.info(f"{r.status_code}: {result}")
            return result["text"]
        elif self.stt_mode == STT_IMPL.SPEACHES:
            print("logging", audio_file_path)
            files = {"file": open(audio_file_path, "rb")}
            data = {"model": self.stt_model, "translation": False, "language": "fr"}
            response = httpx.post(
                "{}v1/audio/transcriptions".format(self.speaches_url),
                files=files,
                data=data,
                timeout=100,
            )
            logging.info("STT response: {}".format(response))
            return response.text
        return "NOT IMPLEMENTED"

    def resume_audio_playback(self):
        logging.info("Resuming audio playback")
        if self.playback.paused:
            self.playback.resume()

    def pause_audio_playback(self):
        logging.info("Pausing audio playback")
        if not self.playback.paused:
            self.playback.pause()

    def is_playback_paused(self) -> bool:
        return self.playback.paused

    def stop_audio_playback(self):
        logging.info("Stopping audio playback")
        if self.playback.paused:
            self.playback.resume()
        self.playback.stop()

    def play_audio_file(self, audio_file_path: str):
        logging.info(f"Playing audio file: {audio_file_path}")
        self.playback.load_file(audio_file_path)
        self.playback.play()
        self.playback.pause()
        self.playback.seek(0)
        self.playback.resume()

        while self.playback.active:
            time.sleep(0.2)

        time.sleep(1)  # small delay to ensure smooth playback

        logging.info("Finished playing audio file: {}".format(audio_file_path))
