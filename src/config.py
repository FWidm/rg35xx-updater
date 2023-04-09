from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from src import ROOT_DIR


@dataclass
class Config:
    conf_override_path: Optional[Path]
    skin_conf_override_path: Optional[Path]
    skin_systems_override_path: Optional[Path]
    boot_partition: Optional[Path]
    rarch_partition: Optional[Path]
    boot_logo_path: Optional[Path]
    output_path: Path = ROOT_DIR / "out"

    def __str__(self) -> str:
        return f"boot partition: {self.boot_partition}\n" \
               f"retroarch partition: {self.rarch_partition}\n" \
               f"rarch config override: {self.conf_override_path}\n" \
               f"skin config override: {self.skin_conf_override_path}\n" \
               f"skin system override: {self.skin_systems_override_path}\n" \
               f"boot logo path: {self.boot_logo_path}"
