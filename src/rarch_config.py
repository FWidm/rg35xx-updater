from dataclasses import dataclass
from pathlib import Path


@dataclass
class RarchConfig:
    path: Path
    entries: {}

    def __init__(self, path: Path) -> None:
        self.path = path
        self.entries = {}

        self.update_entries(path)

    def update_entries(self, path: Path):
        with open(path, 'r') as f:
            for l in f.readlines():
                if '=' in l:
                    key, val = l.split("=", 1)
                    if val:
                        self.entries[key.strip()] = val.strip()

    def get(self, key):
        return self.entries.get(key, None)

    def write_entries(self, path: Path = None):
        if not path:
            path = self.path

        with open(path, 'w') as f:
            f.writelines([f"{key} = {val}\n" for key, val in self.entries.items()])
