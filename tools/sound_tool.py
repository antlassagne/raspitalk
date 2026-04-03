import os
import sys
from threading import Thread

# Ensure project root is on sys.path so `from src...` works when running this script
# directly (e.g. `python tools/display_tool.py`). This keeps the change local to
# this tool script and does not affect package layout elsewhere.
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import logging

# from nava import play, stop_all, stop
import time

sound_id = 0


def run():
    i = 0
    while i < 3:
        time.sleep(1)
        i += 1
        print(i)
    # print(stop_all())
    voice_controller.stop_audio_playback()
    # print(stop(sound_id))
    print("ok")


# logging settings cleanup, because on some configuration I had problems
# 1. Check existing configuration
root_logger = logging.getLogger()

# 2. If handlers exist, clear them (use with caution, but necessary for diagnosis)
if root_logger.handlers:
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

# 3. Re-configure the logging
logging.basicConfig(
    level=logging.INFO, format="%(levelname)-5s - %(filename)-20s - %(message)s"
)

from src.mic_controller import MicController
from src.voice_controller import SOUND_FORMAT, VoiceController

# file = "resources/stories/grimoireauxhistoires/Au-secour-un-monstre-MP3.wav"
file = "resources/stories/pomme-d-api-trimmed/006 - Les Trésors de Pomme d'Api La verdiole de la peur (bonus).mp3"
# file = "user_prompt_1.wav"
voice_controller = VoiceController("http://localhost")

listener_thread = Thread(target=run, daemon=True)
listener_thread.start()

# mic_controller = MicController()
# mic_controller.start_recording(duration=5, output_file="input.{}".format(SOUND_FORMAT))
sound_id = voice_controller.play_audio_file(file)
# play(file, async_mode=False)
print("Done")

# sound_id = play(file, async_mode=False)
while 1:
    time.sleep(1)
    print("tick")
