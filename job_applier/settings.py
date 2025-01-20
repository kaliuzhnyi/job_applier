from typing import Dict, Any

import yaml

DEFAULT_FILE_NAME = "settings.yaml"


class Settings:
    value: Dict[str, Any]

    _instance = None

    def __new__(cls, file_name=DEFAULT_FILE_NAME):
        if cls._instance is None:
            cls._instance = super(Settings, cls).__new__(cls)
            cls._file_name = file_name
            cls._instance._load_settings()
        return cls._instance

    def __getitem__(self, section):
        if section in self.values:
            return self.values[section]
        else:
            raise KeyError(f"Section {section} not found in settings.")

    def _load_settings(self):
        try:
            with open(self._file_name, "r") as file:
                self.values = yaml.safe_load(file)
        except FileNotFoundError:
            raise FileNotFoundError(f"Settings file '{self._file_name}' not found.")
        except yaml.YAMLError as e:
            raise ValueError(f"Error parsing YAML file '{self._file_name}': {e}")

    def reload(self):
        self._load_settings()


SETTINGS = Settings()
