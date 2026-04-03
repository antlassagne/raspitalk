#!/bin/env python3
import argparse
import logging
import os
import signal
import sys

from PyQt6.QtCore import QCoreApplication, QTimer

from src.lunii_controller import LuniiController

os.environ["QT_QPA_PLATFORM"] = "minimal"

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


if __name__ == "__main__":
    app = QCoreApplication(sys.argv)

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--remote_worker_ip",
        help="IP of the machine that will run the STT, LLM and TTS.",
    )
    parser.add_argument(
        "--allow_local_fallback",
        action="store_true",
        help="[dev only] faallback locally whenever remote is not reachable",
    )
    parser.add_argument(
        "--sync_mode",
        action="store_true",
        help="Wait the whole text generation before running the TTS and playback",
    )
    args = parser.parse_args()

    lunii = LuniiController(args)

    def signal_handler(signum, frame):
        print("\nSignal received, closing application...")
        lunii.stop_logger()
        lunii.input.stop()
        lunii.display.stop()
        # lunii.mic.stop()

        QCoreApplication.quit()

    # Handle Ctrl+C gracefully
    signal.signal(signal.SIGINT, signal_handler)

    # Create a timer to allow signal processing
    timer = QTimer()
    timer.timeout.connect(lambda: None)
    timer.start(100)
    sys.exit(app.exec())
