import logging
import os
import sys
import threading
import time
from enum import Enum
from typing import Callable

from gpiozero import Button

DEBUG_KEYBOARD_ENABLED = 0

try:
    from pynput.keyboard import Controller, KeyCode, Listener

    DEBUG_KEYBOARD_ENABLED = 1
except Exception as e:
    logging.info("Unable to use the debugging keyboard here: {}".format(e))


"""
Class that detects keyboard key presses and run callbacks accordingly.
"""

# I2S pins used by audio HATs such as the ReSpeaker 2-Mic HAT:
#   GPIO 18 = BCLK, GPIO 19 = LRCLK, GPIO 20 = DIN, GPIO 21 = DOUT
# Creating a gpiozero device on any of these overrides the kernel's ALT0
# (I2S) function and breaks audio.  Set a pin to 0 to disable that button.
LEFT_BUTTON_PIN = int(os.getenv("BUTTON_LEFT_PIN", "16")) or None
MIDDLE_BUTTON_PIN = int(os.getenv("BUTTON_MIDDLE_PIN", "26")) or None
RIGHT_BUTTON_PIN = int(os.getenv("BUTTON_RIGHT_PIN", "0")) or None


class InputController:
    keyboard_running = False

    if DEBUG_KEYBOARD_ENABLED:
        keyboard = Controller()

    def __init__(self, key_pressed_callback: Callable[[int], None]):
        logging.info("Hello InputController!")
        self.key_pressed = key_pressed_callback

        try:
            time.sleep(1)  # it seems that can improve stability.
            # launch is badly so for now anyway.

            self.left_button = None
            self.right_button = None
            self.middle_button = None

            if LEFT_BUTTON_PIN is not None:
                self.left_button = Button(LEFT_BUTTON_PIN, bounce_time=0.1, hold_time=2)
                self.left_button.when_released = self.on_left_button_released
                self.left_button.when_held = self.on_left_button_held

            if RIGHT_BUTTON_PIN is not None:
                self.right_button = Button(RIGHT_BUTTON_PIN, bounce_time=0.1, hold_time=2)
                self.right_button.when_released = self.on_right_button_released
                self.right_button.when_held = self.on_right_button_held

            if MIDDLE_BUTTON_PIN is not None:
                self.middle_button = Button(MIDDLE_BUTTON_PIN, bounce_time=0.1, hold_time=2)
                self.middle_button.when_released = self.on_middle_button_released
                self.middle_button.when_held = self.on_middle_button_held

        except Exception:
            logging.info(
                "Failed to initialize button, probably running on a dev machine without them."
            )
            logging.info("Falling back to keyboard.")
            self.keyboard_running = True
            self.listener_thread = threading.Thread(target=self.run, daemon=True)
            self.listener_thread.start()

            self.listener = Listener(on_press=self.on_press)
            self.listener.start()

    ## double click implementation
    # from datetime import datetime, timedelta

    # Button.pressed_time = None

    # def pressed(btn):
    #     if btn.pressed_time:
    #         if btn.pressed_time + timedelta(seconds=0.6) > datetime.now():
    #             print("pressed twice")
    #         else:
    #             print("too slow") # debug
    #         btn.pressed_time = None
    #     else:
    #         print("pressed once")  # debug
    #         btn.pressed_time = datetime.now()

    # btn = Button(3)
    # btn.when_pressed = pressed

    def on_left_button_released(self):
        logging.info("Left button released.")
        self.key_pressed(INPUT_CONTROLLER_ACTION.LEFT_BUTTON_TOGGLE.value)

    def on_right_button_released(self):
        logging.info("Right button released.")
        self.key_pressed(INPUT_CONTROLLER_ACTION.RIGHT_BUTTON_TOGGLE.value)
        # pick menu item or validate choice
        # start listening for prompt in both story and conversation mode.
        # stop listening when pressed again.
        # start story generation or listening whenever prompt is available.
        # pause/restart the story playback if any.

    def on_middle_button_released(self):
        logging.info("Middle button released.")
        self.key_pressed(INPUT_CONTROLLER_ACTION.MIDDLE_BUTTON_TOGGLE.value)
        # switch between logs and normal display mode

    def on_left_button_held(self):
        logging.info("Left button held.")
        self.key_pressed(INPUT_CONTROLLER_ACTION.LEFT_BUTTON_HELD.value)
        # Stop everything, cancel listened prompt.

    def on_right_button_held(self):
        logging.info("Right button held.")
        self.key_pressed(INPUT_CONTROLLER_ACTION.RIGHT_BUTTON_HELD.value)

    def on_middle_button_held(self):
        logging.info("Middle button held.")
        self.key_pressed(INPUT_CONTROLLER_ACTION.MIDDLE_BUTTON_HELD.value)
        sys.exit(212)
        # reboot the device

    def stop(self):
        logging.info("Stopping InputController...")
        if self.keyboard_running:
            self.keyboard_running = False
            self.listener_thread.join()
            self.listener.stop()

    def run(self):
        while self.keyboard_running:
            time.sleep(0.1)

    def on_press(self, key):
        # map_of_keys = {"s": 0, "d": 1, "f": 2}
        if isinstance(key, KeyCode):
            if key.char == "s":
                logging.info("left key pressed.")
                self.key_pressed(INPUT_CONTROLLER_ACTION.LEFT_BUTTON_TOGGLE.value)
            elif key.char == "d":
                logging.info("middle key pressed.")
                self.key_pressed(INPUT_CONTROLLER_ACTION.MIDDLE_BUTTON_TOGGLE.value)
            elif key.char == "f":
                logging.info("right key pressed.")
                self.key_pressed(INPUT_CONTROLLER_ACTION.RIGHT_BUTTON_TOGGLE.value)
            elif key.char == "x":
                logging.info("left key held.")
                self.key_pressed(INPUT_CONTROLLER_ACTION.LEFT_BUTTON_HELD.value)
            elif key.char == "c":
                logging.info("middle key held.")
                self.key_pressed(INPUT_CONTROLLER_ACTION.MIDDLE_BUTTON_HELD.value)
            elif key.char == "v":
                logging.info("right key held.")
                self.key_pressed(INPUT_CONTROLLER_ACTION.RIGHT_BUTTON_HELD.value)


class INPUT_CONTROLLER_ACTION(Enum):
    LEFT_BUTTON_TOGGLE = 0
    MIDDLE_BUTTON_TOGGLE = 1
    RIGHT_BUTTON_TOGGLE = 2
    LEFT_BUTTON_HELD = 3
    MIDDLE_BUTTON_HELD = 4
    RIGHT_BUTTON_HELD = 5
