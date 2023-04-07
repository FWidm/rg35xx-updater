from dataclasses import dataclass
from pathlib import Path


@dataclass
class Config:
    conf_override_path: Path
    skin_conf_override_path: Path
    skin_systems_override_path: Path
    boot_partition: Path
    rarch_partition: Path
    boot_logo_path: Path
