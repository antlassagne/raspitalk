import logging

import requests  # type: ignore

from src.display_controller import DisplayController
from src.input_controller import INPUT_CONTROLLER_ACTION, InputController
from src.logging_handler import CallbackHandler
from src.mic_controller import MicController
from src.ollama_controller import OllamaController
from src.recordings_controller import RecordingsController
from src.states import (
    DISPLAY_MODE,
    MENU_STATE,
    WORKING_LANGUAGE,
    WORKING_MODE,
    InputControllerStateMachine,
)
from src.types import ErrorCode
from src.voice_controller import VoiceController


class LuniiController:
    def __init__(self, args):
        self.display = DisplayController()

        # send every log to the display
        hook_handler = CallbackHandler(callback=self.display.push_log_to_display_queue)
        logger = logging.getLogger()
        logger.addHandler(hook_handler)
        self.ai_available = True

        host = args.remote_worker_ip
        self.async_mode = not args.sync_mode
        if host and host.startswith("http") is False:
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

        self.ollama = OllamaController(host=host)
        self.voice = VoiceController(host=host)
        self.mic = MicController()
        self.input = InputController()
        self.state_machine = InputControllerStateMachine(self.ai_available)
        self.recordings = RecordingsController()

        # Input signal (now onl from the keyboard during development)
        self.input.key_pressed.connect(self.handle_input)

        # connect ollama signals to warn us whenever a written sntence is ready
        self.ollama.story_chunk_ready.connect(self.on_story_chunk_available)
        self.ollama.generation_finished.connect(self.on_story_generation_finished)

        # connect voice signals to warn us whenever tts .wav file is ready
        self.voice.tts_ready.connect(self.on_story_tts_available)

        # all the commands that are following are handy for debugging so I keep them here commented
        # input_text = self.voice.speech_to_text(self.mic.temp_file)
        # test = "Il était une fois, dans un royaume lointain, une petite sirène nommée Marisol. Chaque soir, elle allumait sa lanterne magique qui scintillait d'un éclat vif, envoyant des bulles de lumière pleines de rêves émerger dans l'océan stellaire. Un petit poisson nommé Finley, curieux et brave, remarqua ces bulles un soir et en tenta de suivre une. Dans sa bulle de lumière, Finley se retrouva transporté dans un monde aux étoiles qui dança au rythme de la musique des sirènes. Il y rencontra Marisol, qui lui expliqua que chaque bulle était un voyage à travers l'histoire et le rêve. Avec un sourire, Marisol invita Finley à sauter ensemble dans la prochaine bulle, promettant une aventure incroyable. Ensemble, ils se retrouvèrent au cœur d'une ancienne légende, où ils devaient aider le grand dragon de l'or est détenu à jouer un concert pour sauver leur royaume des ténèbres. Finley, avec sa petite taille et son grand courage, fit vibrer les cornes du dragon avec une mélodie si charmante que la magie revint dans le royaume. Les ténèbres s'évanouirent et paix et beauté furent restaurées grâce à leur musique partagée. Alors que le premier rayon de soleil éclaire le royaume, Marisol et Finley se promettèrent de toujours partager leurs rêves et aventures. Et chaque soir, dans la lanterne magique, Finley pouvait encore entendre l'harmonie de leur concert sous-marin, rappelant que même les plus petits peuvent accomplir les actes les plus grands. Et c'est ainsi que le petit poisson et la sirène se sont unis dans une amitié éternelle, entre l'eau et la lumière, vivant ensemble la magie de l'histoire qui durait... juste assez pour tester leur imagination. Fin!"
        # test = "bonjour je m'appelle Antoine"
        # test = "Le Bal des Étoiles Filantes  Regarde, mon petit !"
        # self.voice.push_to_tts_queue(test)
        # text = "je voudrais une histoire sur les étoiles avec des chiens et des chats, en 5 phrases."
        # story = self.ollama.generate_text_response(text, WORKING_MODE.STORY_MODE, True)
        self.display.update(self.state_machine.working_mode)
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
        logging.debug("Handling input")
        state = self.state_machine.next_state(INPUT_CONTROLLER_ACTION(key_code))
        logging.info("State change: {}".format(state))
        self.on_state_changed(state)

    def on_state_changed(
        self, state: WORKING_LANGUAGE | WORKING_MODE | DISPLAY_MODE | MENU_STATE
    ):
        # first, in any case, update the display
        self.display.update(state)

        # then, handle the other controllers
        if isinstance(state, WORKING_MODE):
            # we are in the very begging. Making sure nothing is started.
            self.mic.stop()
            self.voice.reset()

        if isinstance(state, MENU_STATE):
            if state == MENU_STATE.LISTENING_PROMPT:
                self.mic.start_listening()

            if state == MENU_STATE.PAUSED:
                self.voice.pause_audio_playback()

            if state == MENU_STATE.LISTENING_PROMPT_FINISHED:
                self.mic.stop()
                logging.info(
                    "Waiting for the validation / cancellation of the prompt..."
                )

            if state == MENU_STATE.GENERATING_PROMPT:
                if self.voice.is_playback_paused():
                    self.voice.resume_audio_playback()
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
                        self.voice.push_to_playback_queue(recording_file)
                        self.voice.received_final_chunk_to_play = True
                    else:
                        logging.info("No recordings available.")
                else:
                    self.new_story_from_mic(self.async_mode)

            if state == MENU_STATE.MODE_CHOICE:
                self.mic.stop()
                self.voice.reset()
                self.ollama.stop()

    def on_story_tts_available(self, story_tts_filepath):
        logging.info("Story TTS available: {}".format(story_tts_filepath))
        self.voice.push_to_playback_queue(story_tts_filepath)

    def on_story_generation_finished(self):
        self.voice.signal_received_final_text_chunk()

    def on_story_chunk_available(self, story_chunk):
        logging.info("New story chunk available: {}".format(story_chunk))
        # remove the \n characters
        story_chunk = story_chunk.replace("\n", " ")
        self.voice.push_to_tts_queue(story_chunk)

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
            # the connected signal will handle the rest
