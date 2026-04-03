import logging
import threading

from ollama import Client
from PyQt6.QtCore import QObject
from PyQt6.QtCore import pyqtSignal as Signal

from src.states import WORKING_MODE
from src.types import ErrorCode

SENTENCES_SPLITTERS = [".", "!", "?"]
MINIMUM_SENTENCE_LENGTH = 20


class OllamaController(QObject):
    # Signal emitted when a new story chunk is ready in async mode
    # manually triggered un sync mode
    story_chunk_ready = Signal(str)
    generation_finished = Signal()

    # contains the story chunk that is ready to be published, or None
    story_to_publish = None

    # contains the current story being generated
    story = ""

    running = False

    def __init__(self, host: str):
        super().__init__()
        logging.info("Hello OllamaController!")

        self.client = Client(host="{}:11434".format(host))

        # fast, very ad quality
        # self.story_model = "wizardlm2:7b"
        # self.story_model = "deepseek-r1"

        self.story_model = "MathiasB/llama3fr"
        self.story_model = "jobautomation/OpenEuroLLM-French"
        self.story_preprompt = "Tu es un conteur d'histoires pour enfants de 3 ans. Crée une histoire captivante et imaginative. L'histoire doit durer 3 minutes. Évidemment tu tutoies l'enfant et tu parles un français correct, bien qu'adapté à cet âge. Pas d'introduction, pas de titre, tu commences l'histoire tout de suite, et n'ajoute rien non plus une fois l'histoire terminée. L'histoire sera lue telle quelle par une seule voix. Pas non plus de didascalies. Donne un titre, mais ne commence pas par 'il était une fois.'. Base toi sur le prompt suivant: "
        self.conversation_preprompt = ""

    def stop(self):
        logging.info("Stopping OllamaController...")
        # stop ollama generation if possible

    def text_to_seech(self, text):
        logging.info(f"Converting text to speech: {text}")

    def refine_and_publish_story_if_ready(self):
        if self.refine_story():
            logging.info("\nStory chunk ready: {}".format(self.story_to_publish))
            self.story_chunk_ready.emit(self.story_to_publish)
            self.story_to_publish = None

    def refine_story(self):
        if self.story_to_publish is not None:
            logging.info(
                "There is already a story chunk ready to publish: {}".format(
                    self.story_to_publish
                )
            )
            raise Exception(
                "There is already a story chunk ready to publish {}".format(
                    self.story_to_publish
                )
            )

        for splitter in SENTENCES_SPLITTERS:
            if splitter in self.story:
                split_index = self.story.rfind(splitter) + 1
                if len(self.story[:split_index].strip()) >= MINIMUM_SENTENCE_LENGTH:
                    self.story_to_publish = self.story[:split_index].strip()
                    self.story = self.story[split_index:].strip()
                    return True
        return False

    def generate_text_response(
        self, prompt, working_mode: WORKING_MODE, async_mode: bool = False
    ):
        logging.info("Generating story for prompt: {}".format(prompt))
        if self.running:
            logging.info("Story generation already in progress.")
            return "", ErrorCode.BUSY
        if async_mode:
            self.generation_thread = threading.Thread(
                target=self.generate_text_response_worker,
                args=(prompt, working_mode, True),
                daemon=True,
            )
            self.generation_thread.start()
            return "", ErrorCode.SUCCESS
        else:
            return self.generate_text_response_worker(prompt, working_mode)

    def generate_text_response_worker(
        self, prompt, working_mode, async_mode: bool = False
    ):
        self.running = True
        self.story = ""
        untouched_story = ""
        if working_mode == WORKING_MODE.CONVERSATION_MODE:
            preprompt = self.conversation_preprompt
            func = self.client.chat
        else:
            preprompt = self.story_preprompt
            func = self.client.generate

        for chunk in func(
            model=self.story_model,
            prompt=preprompt + prompt,
            stream=True,
        ):
            # logging.info(chunk)
            # logging.info(type(chunk))
            print("#", end="", flush=True)
            story_chunk = chunk["response"]
            self.story += story_chunk
            untouched_story += story_chunk
            if async_mode:
                self.refine_and_publish_story_if_ready()
        if async_mode:
            # don't emit this in non async mode, or it may be treated before the chunk is actually worked on
            self.generation_finished.emit()

        logging.info("Story generation complete: {}".format(untouched_story))
        self.running = False
        return self.story, ErrorCode.SUCCESS
