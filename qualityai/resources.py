"""Acesso aos recursos visuais empacotados com o QualityAI."""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtGui import QFont, QFontDatabase
from PySide6.QtWidgets import QApplication


def resource_path(*parts: str) -> Path:
    """Resolve recursos tanto no código-fonte quanto no executável PyInstaller."""

    bundle_root = getattr(sys, "_MEIPASS", None)
    if bundle_root:
        root = Path(bundle_root) / "qualityai" / "assets"
    else:
        root = Path(__file__).resolve().parent / "assets"
    return root.joinpath(*parts)


def install_brand_fonts(app: QApplication) -> str:
    """Carrega Poppins localmente e devolve a família efetivamente disponível."""

    loaded_families: list[str] = []
    for filename in ("Poppins-Regular.ttf", "Poppins-SemiBold.ttf", "Poppins-Bold.ttf"):
        font_id = QFontDatabase.addApplicationFont(str(resource_path("fonts", filename)))
        if font_id >= 0:
            loaded_families.extend(QFontDatabase.applicationFontFamilies(font_id))

    family = loaded_families[0] if loaded_families else "Segoe UI"
    app.setFont(QFont(family, 10))
    return family
