import json
from dataclasses import dataclass
from pathlib import Path


@dataclass
class SkinConfig:
    path: Path
    entries: {}

    def __init__(self, path: Path) -> None:
        self.path = path
        self.entries = {}

        self.update_entries(path)

    def update_entries(self, path: Path):
        with open(path, 'r') as f:
            entries = json.load(f)
            for k, v in entries.items():
                self.entries[k] = v

    def get(self, key):
        return self.entries.get(key, None)

    def write_entries(self, path: Path = None):
        if not path:
            path = self.path

        with open(path, 'w') as f:
            json.dump(self.entries, f,  indent=4)
