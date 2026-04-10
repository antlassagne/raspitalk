import logging
import os
import threading
import time
from queue import Queue

from just_playback import Playback

SOUND_FORMAT = "wav"  # or "wav" or "mp3"


def get_startup_sound_file():
    # Get absolute path to project root (parent of src/)
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(project_root, "resources", "startup.mp3")


class PlaybackController:
    def __init__(self):
        self.playback = Playback()
        self.playback_queue: Queue = Queue(maxsize=1000)

        self.received_final_chunk_to_play = False
        self.running = True

        self.playback_thread = threading.Thread(
            target=self.playback_worker, daemon=True
        )
        self.playback_thread.start()
        logging.info("Hello PlaybackController!")

    def __del__(self):
        self.stop()
        self.running = False
        if self.playback_thread and self.playback_thread.is_alive():
            self.playback_thread.join()

    def stop(self):
        logging.info("PlaybackController reset called.")
        self.received_final_chunk = False
        self.received_final_chunk_to_play = False
        self.stop_audio_playback()

    def signal_received_final_text_chunk(self):
        self.received_final_chunk = True

    def push_to_playback_queue(self, audio_file_path: str):
        logging.info("> Playback queuing audio file: {}".format(audio_file_path))
        self.playback_queue.put(audio_file_path)
        logging.info("> Playback queue size: {}".format(self.playback_queue.qsize()))

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
            # report that we are finished to the voice controller? that was done before the split
            # Maybe we should still do it, simply to update the UI
            # if self.playback_queue.empty():
            #     if self.received_final_chunk_to_play:
            #         # this was the final thing to do.
            #         self.stop()

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

        while self.playback.active:
            time.sleep(0.2)

        logging.info("Finished playing audio file: {}".format(audio_file_path))
