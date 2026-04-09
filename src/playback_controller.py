import logging
import threading
import time
from queue import Queue

from just_playback import Playback


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

    def reset(self):
        logging.info("PlaybackController reset called.")
        self.received_final_chunk_to_play = False
        self.stop_audio_playback()

    def stop(self):
        logging.info("Stopping PlaybackController...")
        self.stop_audio_playback()
        self.running = False
        if self.playback_thread and self.playback_thread.is_alive():
            self.playback_thread.join()
        logging.info(" done.")

    def signal_received_final_chunk_to_play(self):
        self.received_final_chunk_to_play = True

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
            if self.playback_queue.empty():
                if self.received_final_chunk_to_play:
                    # this was the final thing to do.
                    self.reset()

    def seek_relative(self, offset_seconds: float):
        """Seek forward or backward by the given number of seconds."""
        if self.playback.active:
            new_pos = self.playback.curr_pos + offset_seconds
            new_pos = max(0, min(new_pos, self.playback.duration))
            self.playback.seek(new_pos)
            logging.info(
                "Seeked to {:.1f}s (offset {:.0f}s)".format(new_pos, offset_seconds)
            )

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
