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

from src.display_controller import DisplayController
from src.states import DISPLAY_MODE

display = DisplayController()
display.mode = DISPLAY_MODE.DEV


display.display_image("./resources/lowres/conversation_320.jpg")
time.sleep(2)
display.display_image("resources/lowres/story_320.jpg")
time.sleep(2)
display.display_image("resources/lowres/listening_320.jpg")
time.sleep(2)
display.display_image("resources/lowres/validate_320.jpg")


display.update_dev()
display.display_text("test1", 1)
time.sleep(5)
display.push_log_to_display_queue("test2")


display.push_log_to_display_queue("test3")
time.sleep(1)
display.push_log_to_display_queue("test4")
time.sleep(1)

display.push_log_to_display_queue("test5")

display.push_log_to_display_queue("test6")

display.push_log_to_display_queue("test7")
time.sleep(1)
display.push_log_to_display_queue("test81")

display.push_log_to_display_queue(
    "test1& hello my name is log and i want to crah out something afafa "
)
display.push_log_to_display_queue("test1é")
display.push_log_to_display_queue("test1e")
display.push_log_to_display_queue("test1r")
time.sleep(5)
