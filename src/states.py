import logging
import sys
import time
from enum import Enum

from PyQt6.QtCore import QObject

from src.input_controller import INPUT_CONTROLLER_ACTION


class MENU_STATE(Enum):
    LOADING = 0
    MODE_CHOICE = 1
    LANGUAGE_CHOICE = 2
    PICKING_RECORDING_CATEGORY = 3
    LISTENING_PROMPT = 4
    LISTENING_PROMPT_FINISHED = 5
    GENERATING_PROMPT = 6
    PAUSED = 7


class WORKING_MODE(Enum):
    CONVERSATION_MODE = 0
    STORY_MODE = 1
    RANDOM_RECORDING_MODE = 2
    PICK_RECORDING_MODE = 3
    LAST = 4


class WORKING_LANGUAGE(Enum):
    FRENCH = 0
    ENGLISH = 1


class RANDOM_CATEGORIES(Enum):
    CASUAL = 0
    FEARSOME = 1
    FRIENDLY = 2
    ALL = 3
    LAST = 4


class DISPLAY_MODE(Enum):
    VISUAL = 0
    DEV = 1


class InputControllerStateMachine(QObject):
    menu_state = MENU_STATE.MODE_CHOICE
    working_mode = WORKING_MODE.CONVERSATION_MODE
    working_language = WORKING_LANGUAGE.FRENCH
    display_mode = DISPLAY_MODE.VISUAL
    recording_category = RANDOM_CATEGORIES(0)
    is_ai_available: bool = True

    def __init__(self, is_ai_available: bool):
        super().__init__()
        self.is_ai_available = is_ai_available
        if not self.is_ai_available:
            self.working_mode = WORKING_MODE.RANDOM_RECORDING_MODE
        logging.info("InputControllerStateMachine initialized.")

    def next_state(self, input_event: INPUT_CONTROLLER_ACTION):
        """
        next_state
        Params:
            input_event: the input that triggered a change in internal states

        Returns:
            the state that will visible to the user (will trigger an image modification)

        Raises:
            Exception: if it's a state whose transition is not implemented correctly.
        """
        if input_event == INPUT_CONTROLLER_ACTION.LEFT_BUTTON_TOGGLE:
            logging.info("Transitioning state on LEFT_BUTTON_TOGGLE")
            if self.menu_state == MENU_STATE.MODE_CHOICE:
                # switch working mode
                self.working_mode = WORKING_MODE(int(self.working_mode.value) + 1)
                if self.working_mode == WORKING_MODE.LAST:
                    if self.is_ai_available:
                        self.working_mode = WORKING_MODE.CONVERSATION_MODE
                    else:
                        self.working_mode = WORKING_MODE.RANDOM_RECORDING_MODE
                return self.working_mode

            # multilanguage is TODO
            # elif self.menu_state == MENU_STATE.LANGUAGE_CHOICE:
            #     # switch language
            #     self.working_language = WORKING_LANGUAGE(
            #         not bool(int(self.working_language.value))
            #     )
            #     return self.working_language

            # this button allows to restart the prompt listening
            elif self.menu_state == MENU_STATE.LISTENING_PROMPT_FINISHED:
                self.menu_state = MENU_STATE.MODE_CHOICE
                return self.working_mode

            # to restart the listening even faster
            elif self.menu_state == MENU_STATE.LISTENING_PROMPT:
                self.menu_state = MENU_STATE.MODE_CHOICE
                return self.working_mode

            # to cancel generation/playback
            elif self.menu_state == MENU_STATE.GENERATING_PROMPT:
                self.menu_state = MENU_STATE.MODE_CHOICE
                return self.working_mode

            # in the recording category picking, cycle categories
            elif self.menu_state == MENU_STATE.PICKING_RECORDING_CATEGORY:
                self.recording_category = RANDOM_CATEGORIES(
                    (int(self.recording_category.value) + 1)
                    % (RANDOM_CATEGORIES.LAST.value)
                )
                return self.recording_category

        elif input_event == INPUT_CONTROLLER_ACTION.MIDDLE_BUTTON_TOGGLE:
            # this will return the DISPLAY MODE
            logging.info("Transitioning state on MIDDLE_BUTTON_TOGGLE")
            # swich visual mode
            self.display_mode = DISPLAY_MODE(not bool(int(self.display_mode.value)))
            return self.display_mode

        elif input_event == INPUT_CONTROLLER_ACTION.RIGHT_BUTTON_TOGGLE:
            logging.info("Transitioning state on RIGHT_BUTTON_TOGGLE")
            # this will return the MENU_STATE
            if self.menu_state == MENU_STATE.MODE_CHOICE:
                if self.working_mode == WORKING_MODE.STORY_MODE:
                    self.menu_state = MENU_STATE.LISTENING_PROMPT
                elif self.working_mode == WORKING_MODE.CONVERSATION_MODE:
                    # not implemented RN
                    # self.menu_state = MENU_STATE.LANGUAGE_CHOICE
                    # fallback
                    self.menu_state = MENU_STATE.LISTENING_PROMPT
                elif self.working_mode == WORKING_MODE.RANDOM_RECORDING_MODE:
                    logging.info("Entering recording category picking")
                    self.menu_state = MENU_STATE.PICKING_RECORDING_CATEGORY
                    return self.recording_category

            elif self.menu_state == MENU_STATE.LANGUAGE_CHOICE:
                self.menu_state = MENU_STATE.LISTENING_PROMPT

            elif self.menu_state == MENU_STATE.PICKING_RECORDING_CATEGORY:
                self.menu_state = MENU_STATE.GENERATING_PROMPT

            elif self.menu_state == MENU_STATE.LISTENING_PROMPT:
                self.menu_state = MENU_STATE.LISTENING_PROMPT_FINISHED

            elif self.menu_state == MENU_STATE.LISTENING_PROMPT_FINISHED:
                self.menu_state = MENU_STATE.GENERATING_PROMPT

            elif self.menu_state == MENU_STATE.GENERATING_PROMPT:
                self.menu_state = MENU_STATE.PAUSED

            elif self.menu_state == MENU_STATE.PAUSED:
                self.menu_state = MENU_STATE.GENERATING_PROMPT

            logging.info(f"New menu state: {self.menu_state}")
            return self.menu_state

        elif input_event == INPUT_CONTROLLER_ACTION.LEFT_BUTTON_HELD:
            logging.info("Transitioning state on LEFT_BUTTON_HELD")
            self.menu_state = MENU_STATE.MODE_CHOICE
            return self.menu_state

        elif input_event == INPUT_CONTROLLER_ACTION.MIDDLE_BUTTON_HELD:
            logging.info("Transitioning state on MIDDLE_BUTTON_HELD")
            logging.info("EXITING")
            # exit the program gracefully
            self.visual_mode = DISPLAY_MODE.DEV
            time.sleep(2)

            sys.exit(1)

        raise Exception("Unhandled state.")
