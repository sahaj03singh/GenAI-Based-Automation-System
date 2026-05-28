import json
import os
from selenium.webdriver.common.by import By

VALID_LOCATORS = ["id", "xpath", "css", "name"]


class LocatorAgent:
    def __init__(self, file_path="locators_memory.json"):
        self.file_path = file_path

        if not os.path.exists(file_path):
            with open(file_path, "w") as f:
                json.dump({}, f)

        with open(file_path) as f:
            self.memory = json.load(f)

    def normalize(self, description):
        return description.lower().strip()

    def save_locator(self, description, by, value):
        key = self.normalize(description)

        if by not in VALID_LOCATORS:
            return

        self.memory[key] = {
            "primary": {"by": by, "value": value},
            "fallback": []
        }

        self._save()

    def get_all_locators(self, description):
        key = self.normalize(description)

        if key not in self.memory:
            return []

        locators = []
        locators.append(self.memory[key]["primary"])
        locators.extend(self.memory[key]["fallback"])

        return locators

    def convert(self, locator):
        try:
            by = locator["by"].lower()
            value = locator["value"]

            if by not in VALID_LOCATORS:
                return None, None

            return getattr(By, by.upper()), value
        except:
            return None, None

    def _save(self):
        with open(self.file_path, "w") as f:
            json.dump(self.memory, f, indent=2)