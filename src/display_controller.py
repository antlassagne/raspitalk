import logging
from collections import deque

from PIL import Image, ImageDraw, ImageFont

from src.states import (
    DISPLAY_MODE,
    MENU_STATE,
    RANDOM_CATEGORIES,
    WORKING_LANGUAGE,
    WORKING_MODE,
)

MAX_AMOUNT_OF_LINES = 15


class DisplayController:
    disp = None
    last_image_path: str = ""

    def __init__(self):
        logging.info("Hello DisplayController!")
        self.mode = DISPLAY_MODE.VISUAL

        logging.basicConfig(level=logging.INFO)

        self.states_map = {
            WORKING_LANGUAGE.ENGLISH: "english",
            WORKING_LANGUAGE.FRENCH: "french",
            WORKING_MODE.CONVERSATION_MODE: "./resources/lowres/conversation_320.jpg",
            WORKING_MODE.STORY_MODE: "./resources/lowres/story_320.jpg",
            WORKING_MODE.RANDOM_RECORDING_MODE: "./resources/lowres/random_320.jpg",
            WORKING_MODE.PICK_RECORDING_MODE: "./resources/lowres/pick_320.jpg",
            MENU_STATE.LISTENING_PROMPT: "./resources/lowres/listening_320.jpg",
            MENU_STATE.LISTENING_PROMPT_FINISHED: "./resources/lowres/validate_320.jpg",
            MENU_STATE.GENERATING_PROMPT: "./resources/lowres/listenup_320.jpg",
            RANDOM_CATEGORIES.CASUAL: "./resources/lowres/castle_320.jpg",
            RANDOM_CATEGORIES.FRIENDLY: "./resources/lowres/fox_320.jpg",
            RANDOM_CATEGORIES.FEARSOME: "./resources/lowres/monster_320.jpg",
            RANDOM_CATEGORIES.ALL: "./resources/lowres/random_320.jpg",
            DISPLAY_MODE.DEV: "",
            DISPLAY_MODE.VISUAL: "previous",  # special flag that will be reassigned to the last image displayed
            MENU_STATE.LOADING: "./resources/lowres/loading_320.jpg",
        }

        self.log_queue: deque = deque(maxlen=MAX_AMOUNT_OF_LINES)
        self.font = ImageFont.truetype("./resources/Roboto-Regular.ttf", 20)

        try:
            from src.external.LCD_2inch import LCD_2inch

            # disable the ReSpeaker LED because it collideds with the display
            # led_strip = APA102(num_led=3)
            # led_strip.clear_strip()
            # led_strip.cleanup()
            # display with hardware SPI:
            """
            Warning!!!Don't  creation of multiple displayer objects!!!
            """
            self.disp = LCD_2inch()
            # Initialize library.
            self.disp.Init()
            # Clear display.
            self.disp.clear()
            # Set the backlight to 100
            self.disp.bl_DutyCycle(50)

        except IOError as e:
            logging.info("DisplayController error: {}".format(e))
        except FileNotFoundError as e:
            logging.info("DisplayController error: {}".format(e))

        self.update(MENU_STATE.LOADING)

    def stop(self):
        if self.disp is not None:
            self.disp.module_exit()
            self.disp = None

        logging.info("DisplayController destructor called.")

    def change_mode(self, target_mode: DISPLAY_MODE):
        self.mode = DISPLAY_MODE(not bool(int(target_mode.value)))
        logging.info("Changing display mode to: {}".format(self.mode))

    def update_dev(self):
        if self.disp is not None:
            self.disp.clear()

            # Create blank image for drawing.
            image1 = Image.new("RGB", (self.disp.height, self.disp.width), "WHITE")
            self.draw = ImageDraw.Draw(image1)

            for i in range(0, len(self.log_queue)):
                self.display_text(self.log_queue[i], i)

            self.disp.ShowImage(image1)

    def update(
        self, state: WORKING_LANGUAGE | WORKING_MODE | DISPLAY_MODE | MENU_STATE
    ):
        if self.mode == DISPLAY_MODE.VISUAL:
            if state in self.states_map:
                self.display_image(self.states_map[state])
            else:
                raise Exception(
                    "This state is not supposed to call an image update: {}".format(
                        state
                    )
                )

    def display_text(self, text, line):
        self.draw.text((5, 5 + line * 20), text=text, fill="BLACK", font=self.font)

        # self.draw.text((5, 68), "Hello world", fill="BLACK", font=Font1)
        # self.draw.text((5, 118), "WaveShare", fill="WHITE", font=Font2)
        # self.draw.text((5, 160), "1234567890", fill="GREEN", font=Font3)

    def display_image(self, image_path):
        if image_path == "previous":
            image_path = self.last_image_path

        if image_path == "":
            logging.info("No image to display for this state.")
            return

        logging.info("Display image {}".format(image_path))
        image = Image.open(image_path)
        image = image.rotate(180)

        if self.disp is not None:
            self.disp.clear()
            self.disp.ShowImage(image)

        self.last_image_path = image_path

    def push_log_to_display_queue(self, text: str):
        self.log_queue.append(text)
        # print("Received log: {}".format(text))
        if self.mode == DISPLAY_MODE.DEV:
            self.update_dev()
