import logging
import os
import threading

import requests  # type: ignore

from src.input_controller import INPUT_CONTROLLER_ACTION, InputController
from src.logging_handler import CallbackHandler
from src.playback_controller import PlaybackController
from src.recordings_controller import RecordingsController
from src.states import (
    DISPLAY_MODE,
    MENU_STATE,
    RANDOM_CATEGORIES,
    WORKING_LANGUAGE,
    WORKING_MODE,
    InputControllerStateMachine,
)
from src.types import ErrorCode

USE_DISPLAY = os.getenv("USE_DISPLAY", "true").lower() == "true"
if USE_DISPLAY:
    from src.display_controller import DisplayController


def _thread_excepthook(args: threading.ExceptHookArgs):
    logging.exception(
        "Unhandled exception in thread '%s', exiting.",
        args.thread.name if args.thread else "unknown",
        exc_info=args.exc_value,
    )
    os._exit(1)


def get_startup_sound_file():
    # Get absolute path to project root (parent of src/)
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(project_root, "resources", "startup.mp3")


threading.excepthook = _thread_excepthook


class LuniiController:
    def __init__(self, args):
        self.display = None
        if USE_DISPLAY:
            self.display = DisplayController()

            # send every log to the display
            hook_handler = CallbackHandler(
                callback=self.display.push_log_to_display_queue
            )
            logger = logging.getLogger()
            logger.addHandler(hook_handler)

        self.ai_available = True
        self.async_mode = False

        host = args.remote_worker_ip
        if not host:
            logging.info("No remote worker IP provided. AI features disabled.")
            self.ai_available = False
        else:
            self.async_mode = not args.sync_mode
            if host.startswith("http") is False:
                host = "http://{}".format(host)
            logging.info("Remote worker IP: {}".format(host))
            logging.info("Async mode: {}".format(self.async_mode))

            # ping the default client and see if I need to fallback (dev only)
            try:
                r = requests.get("{}:11434".format(host))  # ollama
                r2 = requests.get("{}:8000/health".format(host))  # speaches
                if r.status_code == 200 and r2.status_code == 200:
                    logging.info("Running the remote backend.")
                else:
                    logging.info("Server not reachable.")
                    self.ai_available = False
            except Exception as e:
                logging.info("Server not reachable: {}".format(e))
                self.ai_available = False

        self.voice = None
        self.ollama = None
        self.mic = None

        if self.ai_available:
            from src.mic_controller import MicController
            from src.ollama_controller import OllamaController
            from src.voice_controller import VoiceController

            self.ollama = OllamaController(
                host=host,
                story_chunk_ready_callback=self.on_story_chunk_available,
                generation_finished_callback=self.on_story_generation_finished,
            )
            self.voice = VoiceController(
                host=host,
                on_tts_ready_callback=self.on_story_tts_available,
                on_final_tts_processed_callback=self.on_final_tts_processed,
            )
            self.mic = MicController()

        self.playback = PlaybackController()
        self.input = InputController(self.handle_input)
        self.state_machine = InputControllerStateMachine(self.ai_available)
        self.recordings = RecordingsController()

        # startup sound
        self.playback.push_to_playback_queue(get_startup_sound_file())
        self.playback.received_final_chunk_to_play = True

        # all the commands that are following are handy for debugging so I keep them here commented
        # input_text = self.voice.speech_to_text(self.mic.temp_file)
        # test = "Il était une fois, dans un royaume lointain, une petite sirène nommée Marisol. Chaque soir, elle allumait sa lanterne magique qui scintillait d'un éclat vif, envoyant des bulles de lumière pleines de rêves émerger dans l'océan stellaire. Un petit poisson nommé Finley, curieux et brave, remarqua ces bulles un soir et en tenta de suivre une. Dans sa bulle de lumière, Finley se retrouva transporté dans un monde aux étoiles qui dança au rythme de la musique des sirènes. Il y rencontra Marisol, qui lui expliqua que chaque bulle était un voyage à travers l'histoire et le rêve. Avec un sourire, Marisol invita Finley à sauter ensemble dans la prochaine bulle, promettant une aventure incroyable. Ensemble, ils se retrouvèrent au cœur d'une ancienne légende, où ils devaient aider le grand dragon de l'or est détenu à jouer un concert pour sauver leur royaume des ténèbres. Finley, avec sa petite taille et son grand courage, fit vibrer les cornes du dragon avec une mélodie si charmante que la magie revint dans le royaume. Les ténèbres s'évanouirent et paix et beauté furent restaurées grâce à leur musique partagée. Alors que le premier rayon de soleil éclaire le royaume, Marisol et Finley se promettèrent de toujours partager leurs rêves et aventures. Et chaque soir, dans la lanterne magique, Finley pouvait encore entendre l'harmonie de leur concert sous-marin, rappelant que même les plus petits peuvent accomplir les actes les plus grands. Et c'est ainsi que le petit poisson et la sirène se sont unis dans une amitié éternelle, entre l'eau et la lumière, vivant ensemble la magie de l'histoire qui durait... juste assez pour tester leur imagination. Fin!"
        # test = "bonjour je m'appelle Antoine"
        # test = "Le Bal des Étoiles Filantes  Regarde, mon petit !"
        # self.voice.push_to_tts_queue(test)
        # text = "je voudrais une histoire sur les étoiles avec des chiens et des chats, en 5 phrases."
        # story = self.ollama.generate_text_response(text, WORKING_MODE.STORY_MODE, True)
        if self.display:
            if self.ai_available:
                self.display.update(self.state_machine.working_mode)
            else:
                self.display.update(MENU_STATE.GENERATING_PROMPT)

        # in no-AI mode, auto-play a random story after the startup sound
        if not self.ai_available:
            self._play_next_random_story()

        logging.info("La Boite est prête!")

    def stop_logger(self):
        logger = logging.getLogger()
        for h in logger.handlers[:]:
            # Check if this handler is an instance of your custom class
            if isinstance(h, CallbackHandler):
                logger.removeHandler(h)
                h.close()  # Always close custom handlers
                logging.info("Custom handler removed.")

    def handle_input(self, key_code: int):
        try:
            logging.debug("Handling input")
            action = INPUT_CONTROLLER_ACTION(key_code)

            # in no-AI mode, buttons directly control playback
            if not self.ai_available:
                self._handle_no_ai_input(action)
                return

            state = self.state_machine.next_state(action)
            logging.info("State change: {}".format(state))
            self.on_state_changed(state)
        except Exception:
            logging.exception("Unhandled exception in handle_input, exiting.")
            os._exit(1)

    def _handle_no_ai_input(self, action: INPUT_CONTROLLER_ACTION):
        if action == INPUT_CONTROLLER_ACTION.LEFT_BUTTON_TOGGLE:
            self.playback.seek_relative(-15)
        elif action == INPUT_CONTROLLER_ACTION.RIGHT_BUTTON_TOGGLE:
            self.playback.seek_relative(30)
        elif action == INPUT_CONTROLLER_ACTION.MIDDLE_BUTTON_TOGGLE:
            if self.playback.is_playback_paused():
                self.playback.resume_audio_playback()
            else:
                self.playback.pause_audio_playback()
        elif action == INPUT_CONTROLLER_ACTION.MIDDLE_BUTTON_HELD:
            self._play_next_random_story()

    def on_state_changed(
        self, state: WORKING_LANGUAGE | WORKING_MODE | DISPLAY_MODE | MENU_STATE
    ):
        # first, in any case, update the display
        if self.display:
            self.display.update(state)

        # then, handle the other controllers
        if isinstance(state, WORKING_MODE):
            # we are in the very begging. Making sure nothing is started.
            self.playback.reset()
            if self.ai_available:
                self.mic.stop()
                self.voice.reset()

        if isinstance(state, RANDOM_CATEGORIES):
            # returning to category selection (e.g. after cancel), stop playback
            self.playback.reset()

        if isinstance(state, MENU_STATE):
            if state == MENU_STATE.LISTENING_PROMPT and self.mic:
                self.mic.start_listening()

            if state == MENU_STATE.PAUSED:
                self.playback.pause_audio_playback()

            if state == MENU_STATE.LISTENING_PROMPT_FINISHED and self.mic:
                self.mic.stop()
                logging.info(
                    "Waiting for the validation / cancellation of the prompt..."
                )

            if state == MENU_STATE.GENERATING_PROMPT:
                if self.playback.is_playback_paused():
                    self.playback.resume_audio_playback()
                    return

                if (
                    self.state_machine.working_mode
                    == WORKING_MODE.RANDOM_RECORDING_MODE
                ):
                    logging.info("Playing a random recording...")
                    recording_file = self.recordings.get_random_recording_by_category(
                        self.state_machine.recording_category
                    )
                    if recording_file:
                        self.playback.push_to_playback_queue(recording_file)
                        self.playback.received_final_chunk_to_play = True
                    else:
                        logging.info("No recordings available.")
                elif self.ai_available:
                    self.new_story_from_mic(self.async_mode)

            if state == MENU_STATE.MODE_CHOICE:
                self.playback.reset()
                if self.ai_available:
                    self.mic.stop()
                    self.voice.reset()
                    self.ollama.stop()

    def on_story_tts_available(self, story_tts_filepath):
        logging.info("Story TTS available: {}".format(story_tts_filepath))
        self.playback.push_to_playback_queue(story_tts_filepath)

    def on_final_tts_processed(self):
        self.playback.signal_received_final_chunk_to_play()

    def on_story_generation_finished(self):
        self.voice.signal_received_final_text_chunk()

    def on_story_chunk_available(self, story_chunk):
        logging.info("New story chunk available: {}".format(story_chunk))
        # remove the \n characters
        story_chunk = story_chunk.replace("\n", " ")
        self.voice.push_to_tts_queue(story_chunk)

    def _play_next_random_story(self):
        logging.info("Playing next random story...")
        self.playback.reset()
        recording_file = self.recordings.get_random_recording_by_category(
            RANDOM_CATEGORIES.ALL
        )
        if recording_file:
            self.playback.push_to_playback_queue(recording_file)
            self.playback.received_final_chunk_to_play = True
        else:
            logging.info("No recordings available.")

    def new_story_from_mic(self, async_mode: bool = False):
        logging.info("Creating a new story...")

        input_text = self.voice.speech_to_text(self.mic.temp_file)
        if len(input_text) <= 0:
            logging.info("Empty STT result.")
            return

        story, error = self.ollama.generate_text_response(
            input_text, self.state_machine.working_mode, async_mode
        )
        if error != ErrorCode.SUCCESS:
            logging.info("Failed to generate the image.")
            return
        if not async_mode:
            logging.info("Generated TTS all at once: {}".format(story))
            self.on_story_chunk_available(story)
            self.on_story_generation_finished()
        else:
            logging.info("Generating TTS asynchronously...")
            # the callbacks will handle the rest
