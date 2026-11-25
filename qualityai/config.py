"""Configuração de caminhos e parâmetros do protótipo."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


APP_NAME = "QualityAI"
MIN_IMAGES_PER_CLASS = 10
IMAGE_SIZE = 224
DEFAULT_CONFIDENCE_THRESHOLD = 0.70
SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


def application_data_dir() -> Path:
    """Retorna a pasta gravável da aplicação no perfil do Windows."""

    base = os.environ.get("LOCALAPPDATA")
    if base:
        return Path(base) / APP_NAME
    return Path.home() / ".qualityai"


@dataclass(frozen=True)
class ProjectPaths:
    """Caminhos persistentes de um projeto local."""

    root: Path

    @property
    def dataset(self) -> Path:
        return self.root / "dataset"

    @property
    def ok(self) -> Path:
        return self.dataset / "ok"

    @property
    def nok(self) -> Path:
        return self.dataset / "nok"

    @property
    def models(self) -> Path:
        return self.root / "models"

    @property
    def model(self) -> Path:
        return self.models / "qualityai_model.pt"

    @property
    def inspections(self) -> Path:
        return self.root / "inspections"

    @property
    def metadata(self) -> Path:
        return self.root / "project.json"

    def ensure(self) -> "ProjectPaths":
        for directory in (self.ok, self.nok, self.models, self.inspections):
            directory.mkdir(parents=True, exist_ok=True)
        return self


def default_project_paths() -> ProjectPaths:
    return ProjectPaths(application_data_dir() / "projects" / "projeto-principal").ensure()


def projects_dir() -> Path:
    """Diretório que reúne as receitas locais de inspeção."""

    path = application_data_dir() / "projects"
    path.mkdir(parents=True, exist_ok=True)
    return path
