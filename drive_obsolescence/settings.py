from __future__ import annotations
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict
import yaml

@dataclass
class Contact:
    person: str
    person_zh: str
    phone: str
    sales_abbr: str

@dataclass
class Settings:
    paths: Dict[str, str]
    rules: Dict[str, Any]
    contacts: Dict[str, Contact]
    schedule: Dict[str, Any]

    @property
    def output_root(self) -> Path:
        p = Path(self.paths["output_root"])
        p.mkdir(parents=True, exist_ok=True)
        return p

def load_settings(path: str | os.PathLike) -> Settings:
    with open(path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    contacts = {k: Contact(**v) for k, v in cfg["contacts"].items()}
    return Settings(
        paths=cfg["paths"],
        rules=cfg["rules"],
        contacts=contacts,
        schedule=cfg["schedule"],
    )
