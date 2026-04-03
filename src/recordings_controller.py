#!/bin/bash

import glob
import logging
import os
import random

from src.states import RANDOM_CATEGORIES


class RecordingsController:
    recordings_list: dict = {}

    def __init__(self):
        self.recordings_list[RANDOM_CATEGORIES.CASUAL] = self.initialize_recordings(
            "casual"
        )
        self.recordings_list[RANDOM_CATEGORIES.FRIENDLY] = self.initialize_recordings(
            "friendly"
        )
        self.recordings_list[RANDOM_CATEGORIES.FEARSOME] = self.initialize_recordings(
            "fearsome"
        )
        self.recordings_list[RANDOM_CATEGORIES.ALL] = self.initialize_recordings("**")
        logging.info("RecordingsController initialized.")
        logging.info(f"Found {len(self.recordings_list)} recordings.")

    def initialize_recordings(self, subfolder) -> list:
        logging.info("Initializing recordings.")
        # Get absolute path to project root (parent of src/)
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        recordings_path = os.path.join(
            project_root, "resources", "stories", subfolder, "*.mp3"
        )
        return glob.glob(recordings_path, recursive=True)

    def get_random_recording_by_category(self, category: RANDOM_CATEGORIES) -> str:
        logging.info("Fetching a random recording.")
        if len(self.recordings_list[category]) == 0:
            logging.warning("No recordings available.")
            raise Exception("No recordings available.")

        return random.choice(self.recordings_list[category])

    def get_recording_by_index(self, index):
        logging.info(f"Fetching recording at index: {index}")
        if index < 0 or index >= len(self.recordings_list):
            logging.error("Index out of bounds.")
            raise IndexError("Index out of bounds.")

        return self.recordings_list[index]
