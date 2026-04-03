import os
import sys

# Ensure project root is on sys.path so `from src...` works when running this script
# directly (e.g. `python tools/display_tool.py`). This keeps the change local to
# this tool script and does not affect package layout elsewhere.
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import logging
import time

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

from src.voice_controller import SOUND_FORMAT, VoiceController

voice_controller = VoiceController("http://192.168.1.100")
text = "Bonjour je m'appelle Kévin et j'aime faire des chatouilles partout partout."
voice_controller.text_to_speech(text=text, output_file="test.{}".format(SOUND_FORMAT))
