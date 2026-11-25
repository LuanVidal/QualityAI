"""Aplicação desktop do protótipo QualityAI."""

from __future__ import annotations

import os
import sys
from dataclasses import replace
from datetime import datetime
from pathlib import Path
from threading import Event

import cv2
from PySide6.QtCore import QObject, QThread, QTimer, Qt, Signal, Slot
from PySide6.QtGui import QCloseEvent, QIcon, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSlider,
    QStackedWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from qualityai.camera import CameraController, CameraError, mirror_frame
from qualityai.config import DEFAULT_CONFIDENCE_THRESHOLD, MIN_IMAGES_PER_CLASS, projects_dir
from qualityai.ml import (
    QualityPredictor,
    TrainingCancelled,
    TrainingError,
    TrainingReport,
    train_lightweight_model,
)
from qualityai.preprocessing import PreprocessingConfig, visual_similarity
from qualityai.resources import install_brand_fonts, resource_path
from qualityai.storage import DatasetStore, RecipeCatalog
from qualityai.styles import APP_STYLESHEET
from qualityai.widgets import StatCard, VideoView


class TrainingWorker(QObject):
    progress = Signal(int, str)
    finished = Signal(object)
    failed = Signal(str)
    cancelled = Signal(str)

    def __init__(self, store: DatasetStore, config: PreprocessingConfig) -> None:
        super().__init__()
        self.store = store
        self.config = config
        self.cancel_event = Event()

    @Slot()
    def run(self) -> None:
        try:
            report = train_lightweight_model(
                self.store.all_labeled_images(),
                self.store.paths.model,
                preprocessing=self.config,
                progress=lambda value, message: self.progress.emit(value, message),
                cancel_event=self.cancel_event,
            )
        except TrainingCancelled as exc:
            self.cancelled.emit(str(exc))
        except Exception as exc:  # noqa: BLE001 - a mensagem precisa chegar à interface
            self.failed.emit(str(exc))
        else:
            self.finished.emit(report)

    @Slot()
    def cancel(self) -> None:
        self.cancel_event.set()


class RecipeDialog(QDialog):
    """Cadastro compacto de uma receita de inspeção."""

    def __init__(
        self,
        parent: QWidget,
        *,
        name: str = "",
        part_type: str = "",
        description: str = "",
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Receita de inspeção")
        self.setModal(True)
        self.setMinimumWidth(520)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 22)
        layout.setSpacing(16)
        title = QLabel("Configurar receita")
        title.setObjectName("DialogTitle")
        hint = QLabel(
            "Cada receita mantém seu próprio dataset, ROI, filtros e modelo de classificação."
        )
        hint.setObjectName("SectionHint")
        hint.setWordWrap(True)
        layout.addWidget(title)
        layout.addWidget(hint)

        form = QFormLayout()
        form.setSpacing(12)
        self.name_input = QLineEdit(name)
        self.name_input.setPlaceholderText("Ex.: Tampa do motor — Linha A")
        self.part_type_input = QLineEdit(part_type)
        self.part_type_input.setPlaceholderText("Ex.: Tampa plástica injetada")
        self.description_input = QTextEdit(description)
        self.description_input.setPlaceholderText(
            "Descreva a peça, o defeito esperado, iluminação e objetivo desta receita."
        )
        self.description_input.setFixedHeight(105)
        form.addRow("Nome da receita", self.name_input)
        form.addRow("Tipo de peça", self.part_type_input)
        form.addRow("Descrição do modelo", self.description_input)
        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        save_button = buttons.button(QDialogButtonBox.StandardButton.Save)
        save_button.setText("Salvar receita")
        save_button.setObjectName("PrimaryButton")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Cancelar")
        buttons.accepted.connect(self._accept_if_valid)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _accept_if_valid(self) -> None:
        if not self.name_input.text().strip():
            QMessageBox.information(self, "Nome obrigatório", "Informe o nome da receita.")
            self.name_input.setFocus()
            return
        self.accept()

    def values(self) -> tuple[str, str, str]:
        return (
            self.name_input.text().strip(),
            self.part_type_input.text().strip(),
            self.description_input.toPlainText().strip(),
        )


class MainWindow(QMainWindow):
    PAGE_TITLES = (
        "Visão geral",
        "Imagens e câmera",
        "Treinamento leve",
        "Inspeção",
    )

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("QualityAI — Inspeção Visual Industrial")
        self.setWindowIcon(QIcon(str(resource_path("qualityai-logo.png"))))
        self.resize(1440, 900)
        self.setMinimumSize(1180, 760)

        self.catalog = RecipeCatalog(projects_dir())
        self.store = self.catalog.active_store()
        self.paths = self.store.paths
        metadata = self.store.read_metadata()
        self.preprocessing = PreprocessingConfig.from_dict(metadata.get("preprocessing"))
        self.camera = CameraController()
        self.current_frame = None
        self.predictor: QualityPredictor | None = None
        self.training_thread: QThread | None = None
        self.training_worker: TrainingWorker | None = None
        self._close_after_training = False
        self._last_inspection_frame = None
        self._last_inspection_result = None
        self._last_inspection_id: str | None = None

        self.camera_timer = QTimer(self)
        self.camera_timer.setInterval(40)
        self.camera_timer.timeout.connect(self._update_camera_frame)

        self._build_ui()
        self._connect_filter_controls()
        self._load_model_if_available()
        self.refresh_state()

    def _build_ui(self) -> None:
        root = QWidget()
        root.setObjectName("AppRoot")
        self.setCentralWidget(root)
        root_layout = QHBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        root_layout.addWidget(self._build_sidebar())

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)
        content_layout.addWidget(self._build_topbar())

        self.pages = QStackedWidget()
        self.pages.addWidget(self._build_dashboard_page())
        self.pages.addWidget(self._build_dataset_page())
        self.pages.addWidget(self._build_training_page())
        self.pages.addWidget(self._build_inspection_page())
        content_layout.addWidget(self.pages, 1)
        root_layout.addWidget(content, 1)

    def _build_sidebar(self) -> QWidget:
        sidebar = QWidget()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(246)
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(18, 20, 18, 20)
        layout.setSpacing(8)

        logo = QLabel()
        logo.setObjectName("BrandLogo")
        logo.setFixedSize(210, 158)
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo.setAccessibleName("QualityAI")
        logo_pixmap = QPixmap(str(resource_path("qualityai-logo.png")))
        logo.setPixmap(
            logo_pixmap.scaled(
                194,
                146,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )
        layout.addWidget(logo)
        layout.addSpacing(8)

        section = QLabel("OPERAÇÃO")
        section.setObjectName("BrandCaption")
        layout.addWidget(section)

        self.nav_group = QButtonGroup(self)
        self.nav_group.setExclusive(True)
        labels = ("▦  Visão geral", "◉  Imagens e câmera", "◆  Treinamento", "◎  Inspeção")
        for index, label in enumerate(labels):
            button = QPushButton(label)
            button.setObjectName("NavButton")
            button.setCheckable(True)
            button.clicked.connect(lambda checked=False, page=index: self._set_page(page))
            self.nav_group.addButton(button, index)
            layout.addWidget(button)
            if index == 0:
                button.setChecked(True)

        layout.addStretch(1)
        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setStyleSheet("color: #174561;")
        layout.addWidget(divider)
        local = QLabel("●  PROCESSAMENTO LOCAL\n    Dados permanecem neste notebook")
        local.setObjectName("Muted")
        local.setWordWrap(True)
        layout.addWidget(local)
        return sidebar

    def _build_topbar(self) -> QWidget:
        topbar = QWidget()
        topbar.setObjectName("Topbar")
        topbar.setFixedHeight(72)
        layout = QHBoxLayout(topbar)
        layout.setContentsMargins(28, 0, 28, 0)
        self.page_title = QLabel(self.PAGE_TITLES[0])
        self.page_title.setObjectName("PageTitle")
        layout.addWidget(self.page_title)
        layout.addStretch(1)
        self.project_label = QLabel("RECEITA ATIVA")
        self.project_label.setObjectName("Muted")
        layout.addWidget(self.project_label)
        self.camera_status = QLabel("○  CÂMERA")
        self.camera_status.setObjectName("StatusOffline")
        self.camera_status.setFixedHeight(32)
        self.camera_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.camera_status)
        return topbar

    def _page_container(self) -> tuple[QScrollArea, QVBoxLayout]:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        body = QWidget()
        body.setObjectName("PageBody")
        layout = QVBoxLayout(body)
        layout.setContentsMargins(28, 24, 28, 28)
        layout.setSpacing(18)
        scroll.setWidget(body)
        return scroll, layout

    def _panel(self, title: str, hint: str = "") -> tuple[QFrame, QVBoxLayout]:
        frame = QFrame()
        frame.setObjectName("Panel")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(20, 18, 20, 20)
        layout.setSpacing(12)
        heading = QLabel(title)
        heading.setObjectName("SectionTitle")
        layout.addWidget(heading)
        if hint:
            description = QLabel(hint)
            description.setObjectName("SectionHint")
            description.setWordWrap(True)
            layout.addWidget(description)
        return frame, layout

    def _build_dashboard_page(self) -> QWidget:
        page, layout = self._page_container()
        hero = QFrame()
        hero.setObjectName("Hero")
        hero_layout = QVBoxLayout(hero)
        hero_layout.setContentsMargins(26, 23, 26, 23)
        eyebrow = QLabel("INSPEÇÃO VISUAL ASSISTIDA")
        eyebrow.setObjectName("HeroEyebrow")
        title = QLabel("Qualidade industrial com IA leve e supervisão humana")
        title.setObjectName("HeroTitle")
        title.setWordWrap(True)
        text = QLabel(
            "Capture exemplos OK e NOK pela câmera USB, treine um classificador local "
            "e inspecione novas peças sem enviar imagens para a nuvem."
        )
        text.setObjectName("HeroText")
        text.setWordWrap(True)
        hero_layout.addWidget(eyebrow)
        hero_layout.addWidget(title)
        hero_layout.addWidget(text)
        layout.addWidget(hero)

        cards = QHBoxLayout()
        cards.setSpacing(14)
        self.dashboard_dataset = StatCard("DATASET", "0 / 20", "mínimo para o protótipo")
        self.dashboard_model = StatCard("MODELO", "Não treinado", "aguardando dataset")
        self.dashboard_camera = StatCard("CÂMERA USB", "Offline", "conecte na área de dataset")
        for card in (self.dashboard_dataset, self.dashboard_model, self.dashboard_camera):
            cards.addWidget(card, 1)
        layout.addLayout(cards)

        workflow, workflow_layout = self._panel(
            "Fluxo operacional",
            "A decisão continua com o profissional de qualidade; a IA organiza evidências e aponta a classe provável.",
        )
        steps = QHBoxLayout()
        for number, step in enumerate(
            ("Delimitar ROI", "Coletar 10 + 10", "Treinar e validar", "Inspecionar", "Revisar"),
            start=1,
        ):
            label = QLabel(f"{number:02d}\n{step}")
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setMinimumHeight(78)
            label.setStyleSheet(
                "background:#0d151e;border:1px solid #293d4e;border-radius:9px;"
                "font-weight:600;color:#c8d3dc;padding:10px;"
            )
            steps.addWidget(label, 1)
        workflow_layout.addLayout(steps)
        layout.addWidget(workflow)

        method, method_layout = self._panel(
            "Por que o treinamento é leve?",
            "A MobileNetV3-Small já sabe extrair formas, bordas e texturas. Seus pesos ficam congelados; "
            "somente um classificador linear aprende a separar OK de NOK. Assim, o notebook processa "
            "poucos parâmetros e a validação cruzada mede o desempenho fora das amostras usadas em cada ajuste.",
        )
        layout.addWidget(method)
        layout.addStretch(1)
        return page

    def _build_dataset_page(self) -> QWidget:
        page, layout = self._page_container()

        recipe, recipe_layout = self._panel(
            "Receitas e conjuntos de imagens",
            "Cada receita guarda imagens, região de interesse, filtros e modelo próprios.",
        )
        recipe_toolbar = QHBoxLayout()
        self.recipe_selector = QComboBox()
        self.recipe_selector.setMinimumWidth(330)
        self.recipe_selector.currentIndexChanged.connect(self._switch_recipe)
        new_recipe = QPushButton("+  Nova receita")
        new_recipe.setObjectName("PrimaryButton")
        new_recipe.clicked.connect(self._create_recipe)
        edit_recipe = QPushButton("Editar descrição")
        edit_recipe.clicked.connect(self._edit_recipe)
        clear_dataset = QPushButton("Apagar todas")
        clear_dataset.setObjectName("DangerOutlineButton")
        clear_dataset.clicked.connect(self._clear_dataset)
        recipe_toolbar.addWidget(self.recipe_selector, 1)
        recipe_toolbar.addWidget(new_recipe)
        recipe_toolbar.addWidget(edit_recipe)
        recipe_toolbar.addWidget(clear_dataset)
        recipe_layout.addLayout(recipe_toolbar)

        recipe_details = QFrame()
        recipe_details.setObjectName("RecipeDetails")
        details_layout = QHBoxLayout(recipe_details)
        details_layout.setContentsMargins(16, 12, 16, 12)
        details_layout.setSpacing(16)
        self.recipe_type_label = QLabel("PEÇA · —")
        self.recipe_type_label.setObjectName("RecipeType")
        self.recipe_description_label = QLabel("Sem descrição.")
        self.recipe_description_label.setObjectName("RecipeDescription")
        self.recipe_description_label.setWordWrap(True)
        details_layout.addWidget(self.recipe_type_label)
        details_layout.addWidget(self.recipe_description_label, 1)
        recipe_layout.addWidget(recipe_details)
        layout.addWidget(recipe)

        columns = QHBoxLayout()
        columns.setSpacing(18)

        video_panel, video_layout = self._panel(
            "Câmera e região de interesse",
            "Arraste o mouse sobre a imagem para delimitar a ROI. Somente essa região será usada no treino e na inspeção.",
        )
        self.dataset_video = VideoView()
        self.dataset_video.roiChanged.connect(self._on_roi_changed)
        video_layout.addWidget(self.dataset_video, 1)

        capture_buttons = QHBoxLayout()
        self.capture_ok_button = QPushButton("CAPTURAR COMO OK")
        self.capture_ok_button.setObjectName("OkButton")
        self.capture_ok_button.clicked.connect(lambda: self._capture_sample("ok"))
        self.capture_nok_button = QPushButton("CAPTURAR COMO NOK")
        self.capture_nok_button.setObjectName("NokButton")
        self.capture_nok_button.clicked.connect(lambda: self._capture_sample("nok"))
        capture_buttons.addWidget(self.capture_ok_button)
        capture_buttons.addWidget(self.capture_nok_button)
        video_layout.addLayout(capture_buttons)
        columns.addWidget(video_panel, 3)

        controls, controls_layout = self._panel("Ajustes de captura")
        controls.setMinimumWidth(330)

        camera_row = QHBoxLayout()
        self.camera_index = QComboBox()
        for index in range(5):
            self.camera_index.addItem(f"Câmera {index}", index)
        self.connect_camera_button = QPushButton("Conectar")
        self.connect_camera_button.setObjectName("PrimaryButton")
        self.connect_camera_button.clicked.connect(self._toggle_camera)
        camera_row.addWidget(self.camera_index, 1)
        camera_row.addWidget(self.connect_camera_button)
        controls_layout.addLayout(camera_row)

        self.processed_preview = QCheckBox("Visualizar resultado dos filtros")
        self.grayscale = QCheckBox("Tons de cinza")
        self.clahe = QCheckBox("Normalização de contraste (CLAHE)")
        self.denoise = QCheckBox("Redução leve de ruído")
        self.sharpen = QCheckBox("Realce de nitidez")
        self.clahe.setChecked(self.preprocessing.clahe)
        self.grayscale.setChecked(self.preprocessing.grayscale)
        self.denoise.setChecked(self.preprocessing.denoise)
        self.sharpen.setChecked(self.preprocessing.sharpen)
        for checkbox in (
            self.processed_preview,
            self.grayscale,
            self.clahe,
            self.denoise,
            self.sharpen,
        ):
            controls_layout.addWidget(checkbox)

        controls_layout.addWidget(QLabel("Brilho"))
        self.brightness_slider = QSlider(Qt.Orientation.Horizontal)
        self.brightness_slider.setRange(-100, 100)
        self.brightness_slider.setValue(self.preprocessing.brightness)
        controls_layout.addWidget(self.brightness_slider)
        controls_layout.addWidget(QLabel("Contraste"))
        self.contrast_slider = QSlider(Qt.Orientation.Horizontal)
        self.contrast_slider.setRange(50, 200)
        self.contrast_slider.setValue(round(self.preprocessing.contrast * 100))
        controls_layout.addWidget(self.contrast_slider)

        roi_reset = QPushButton("Redefinir ROI central")
        roi_reset.clicked.connect(self._reset_roi)
        controls_layout.addWidget(roi_reset)

        import_row = QHBoxLayout()
        import_ok = QPushButton("Importar OK")
        import_nok = QPushButton("Importar NOK")
        import_ok.clicked.connect(lambda: self._import_samples("ok"))
        import_nok.clicked.connect(lambda: self._import_samples("nok"))
        import_row.addWidget(import_ok)
        import_row.addWidget(import_nok)
        controls_layout.addLayout(import_row)

        self.ok_progress = QProgressBar()
        self.ok_progress.setRange(0, MIN_IMAGES_PER_CLASS)
        self.ok_count = QLabel("OK  0 / 10")
        self.nok_progress = QProgressBar()
        self.nok_progress.setRange(0, MIN_IMAGES_PER_CLASS)
        self.nok_count = QLabel("NOK  0 / 10")
        controls_layout.addWidget(self.ok_count)
        controls_layout.addWidget(self.ok_progress)
        controls_layout.addWidget(self.nok_count)
        controls_layout.addWidget(self.nok_progress)
        controls_layout.addStretch(1)
        columns.addWidget(controls, 1)
        layout.addLayout(columns, 3)

        samples, sample_layout = self._panel("Amostras recentes", "Selecione uma imagem para removê-la do dataset.")
        self.sample_list = QListWidget()
        self.sample_list.setMaximumHeight(160)
        sample_layout.addWidget(self.sample_list)
        delete_button = QPushButton("Remover amostra selecionada")
        delete_button.clicked.connect(self._delete_selected_sample)
        sample_layout.addWidget(delete_button, alignment=Qt.AlignmentFlag.AlignRight)
        layout.addWidget(samples)
        return page

    def _build_training_page(self) -> QWidget:
        page, layout = self._page_container()
        cards = QHBoxLayout()
        self.training_dataset_card = StatCard("AMOSTRAS", "0 / 20", "10 OK + 10 NOK")
        self.training_metric_card = StatCard("VALIDAÇÃO", "—", "validação cruzada estratificada")
        self.training_model_card = StatCard("ARTEFATO", "—", "MobileNetV3-Small + classificador linear")
        for card in (self.training_dataset_card, self.training_metric_card, self.training_model_card):
            cards.addWidget(card, 1)
        layout.addLayout(cards)

        explanation, explanation_layout = self._panel(
            "Estratégia eficiente",
            "A rede visual permanece congelada. O sistema extrai uma assinatura compacta de cada imagem "
            "e treina somente um classificador linear balanceado. A validação em cinco divisões evita "
            "apresentar a precisão do próprio conjunto de ajuste como se fosse desempenho real.",
        )
        layout.addWidget(explanation)

        process, process_layout = self._panel("Treinar nova versão")
        self.training_progress = QProgressBar()
        self.training_progress.setRange(0, 100)
        self.training_status = QLabel("Aguardando dataset completo.")
        self.training_status.setObjectName("Muted")
        process_layout.addWidget(self.training_status)
        process_layout.addWidget(self.training_progress)

        actions = QHBoxLayout()
        self.train_button = QPushButton("TREINAR MODELO")
        self.train_button.setObjectName("PrimaryButton")
        self.train_button.clicked.connect(self._start_training)
        self.cancel_training_button = QPushButton("Cancelar")
        self.cancel_training_button.setEnabled(False)
        self.cancel_training_button.clicked.connect(self._cancel_training)
        actions.addWidget(self.train_button)
        actions.addWidget(self.cancel_training_button)
        actions.addStretch(1)
        process_layout.addLayout(actions)

        self.training_log = QTextEdit()
        self.training_log.setReadOnly(True)
        self.training_log.setMinimumHeight(220)
        self.training_log.setPlaceholderText("O andamento e as métricas aparecerão aqui.")
        process_layout.addWidget(self.training_log)
        layout.addWidget(process, 1)
        return page

    def _build_inspection_page(self) -> QWidget:
        page, layout = self._page_container()
        columns = QHBoxLayout()
        columns.setSpacing(18)

        video_panel, video_layout = self._panel(
            "Imagem de inspeção",
            "O modelo aplica automaticamente a mesma ROI e os mesmos filtros usados no treinamento.",
        )
        self.inspection_video = VideoView("Conecte a câmera ou importe uma imagem")
        video_layout.addWidget(self.inspection_video, 1)
        actions = QHBoxLayout()
        analyze = QPushButton("CAPTURAR E ANALISAR")
        analyze.setObjectName("PrimaryButton")
        analyze.clicked.connect(self._inspect_current_frame)
        import_image = QPushButton("Importar imagem")
        import_image.clicked.connect(self._inspect_imported_image)
        actions.addWidget(analyze)
        actions.addWidget(import_image)
        video_layout.addLayout(actions)
        columns.addWidget(video_panel, 3)

        result_panel, result_layout = self._panel("Resultado da análise")
        result_panel.setMinimumWidth(340)
        self.result_label = QLabel("AGUARDANDO")
        self.result_label.setObjectName("ResultReview")
        self.result_label.setMinimumHeight(150)
        self.result_confidence = QLabel("Confiança: —")
        self.result_confidence.setObjectName("CardValue")
        self.result_model = QLabel("Modelo: nenhum modelo carregado")
        self.result_model.setObjectName("Muted")
        self.result_model.setWordWrap(True)
        self.result_guidance = QLabel(
            "Resultados com confiança abaixo de 70% exigem revisão humana."
        )
        self.result_guidance.setObjectName("SectionHint")
        self.result_guidance.setWordWrap(True)
        review_actions = QVBoxLayout()
        self.confirm_result_button = QPushButton("Confirmar resultado")
        self.correct_ok_button = QPushButton("Corrigir para OK")
        self.correct_ok_button.setObjectName("OkButton")
        self.correct_nok_button = QPushButton("Corrigir para NOK")
        self.correct_nok_button.setObjectName("NokButton")
        self.confirm_result_button.clicked.connect(self._confirm_inspection)
        self.correct_ok_button.clicked.connect(lambda: self._correct_inspection("ok"))
        self.correct_nok_button.clicked.connect(lambda: self._correct_inspection("nok"))
        review_actions.addWidget(self.confirm_result_button)
        review_actions.addWidget(self.correct_ok_button)
        review_actions.addWidget(self.correct_nok_button)
        for button in (
            self.confirm_result_button,
            self.correct_ok_button,
            self.correct_nok_button,
        ):
            button.setEnabled(False)
        result_layout.addWidget(self.result_label)
        result_layout.addWidget(self.result_confidence)
        result_layout.addWidget(self.result_model)
        result_layout.addWidget(self.result_guidance)
        result_layout.addLayout(review_actions)
        result_layout.addStretch(1)
        columns.addWidget(result_panel, 1)
        layout.addLayout(columns, 1)
        return page

    def _connect_filter_controls(self) -> None:
        self.processed_preview.toggled.connect(self.dataset_video.set_processed_preview)
        for control in (self.grayscale, self.clahe, self.denoise, self.sharpen):
            control.toggled.connect(self._filters_changed)
        self.brightness_slider.valueChanged.connect(self._filters_changed)
        self.contrast_slider.valueChanged.connect(self._filters_changed)

    def _set_page(self, index: int) -> None:
        self.pages.setCurrentIndex(index)
        self.page_title.setText(self.PAGE_TITLES[index])
        button = self.nav_group.button(index)
        if button is not None:
            button.setChecked(True)

    def _toggle_camera(self) -> None:
        if self.camera.is_open:
            self._disconnect_camera()
            return
        try:
            self.camera.open(int(self.camera_index.currentData()))
        except CameraError as exc:
            QMessageBox.warning(self, "Câmera indisponível", str(exc))
            return
        self.camera_timer.start()
        self.connect_camera_button.setText("Desconectar")
        self.camera_status.setText(f"●  CÂMERA {self.camera.index}")
        self.camera_status.setObjectName("StatusOnline")
        self.camera_status.style().unpolish(self.camera_status)
        self.camera_status.style().polish(self.camera_status)
        self.dashboard_camera.set_data("Online", f"dispositivo {self.camera.index}")

    def _disconnect_camera(self) -> None:
        self.camera_timer.stop()
        self.camera.release()
        self.current_frame = None
        self.dataset_video.clear_source()
        self.inspection_video.clear_source("Conecte a câmera ou importe uma imagem")
        self.connect_camera_button.setText("Conectar")
        self.camera_status.setText("○  CÂMERA")
        self.camera_status.setObjectName("StatusOffline")
        self.camera_status.style().unpolish(self.camera_status)
        self.camera_status.style().polish(self.camera_status)
        self.dashboard_camera.set_data("Offline", "conecte na área de dataset")

    def _update_camera_frame(self) -> None:
        try:
            frame = mirror_frame(self.camera.read())
        except CameraError as exc:
            self._disconnect_camera()
            QMessageBox.warning(self, "Câmera desconectada", str(exc))
            return
        self.current_frame = frame
        self.dataset_video.set_source(frame, self.preprocessing)
        display_config = self.predictor.preprocessing if self.predictor else self.preprocessing
        self.inspection_video.set_source(frame, display_config)

    def _on_roi_changed(self, x: float, y: float, width: float, height: float) -> None:
        self.preprocessing = replace(
            self.preprocessing,
            roi_x=x,
            roi_y=y,
            roi_width=width,
            roi_height=height,
        ).normalized()
        self._persist_preprocessing()

    def _filters_changed(self, *_args) -> None:
        self.preprocessing = replace(
            self.preprocessing,
            grayscale=self.grayscale.isChecked(),
            clahe=self.clahe.isChecked(),
            denoise=self.denoise.isChecked(),
            sharpen=self.sharpen.isChecked(),
            brightness=self.brightness_slider.value(),
            contrast=self.contrast_slider.value() / 100.0,
        ).normalized()
        self._persist_preprocessing()
        if self.current_frame is not None:
            self.dataset_video.set_source(self.current_frame, self.preprocessing)

    def _reset_roi(self) -> None:
        self.preprocessing = replace(
            self.preprocessing, roi_x=0.10, roi_y=0.10, roi_width=0.80, roi_height=0.80
        )
        self._persist_preprocessing()
        if self.current_frame is not None:
            self.dataset_video.set_source(self.current_frame, self.preprocessing)

    def _refresh_recipe_selector(self) -> None:
        active_id = str(self.store.read_metadata().get("recipe_id", self.paths.root.name))
        self.recipe_selector.blockSignals(True)
        self.recipe_selector.clear()
        active_index = 0
        for index, recipe in enumerate(self.catalog.list_recipes()):
            self.recipe_selector.addItem(recipe.name, recipe.recipe_id)
            if recipe.recipe_id == active_id:
                active_index = index
        self.recipe_selector.setCurrentIndex(active_index)
        self.recipe_selector.blockSignals(False)

    def _sync_recipe_controls(self) -> None:
        metadata = self.store.read_metadata()
        recipe_name = str(metadata.get("name") or "Receita sem nome")
        part_type = str(metadata.get("part_type") or "Peça não informada")
        description = str(metadata.get("description") or "Sem descrição do modelo.")
        self.project_label.setText(recipe_name.upper())
        self.recipe_type_label.setText(f"PEÇA · {part_type.upper()}")
        self.recipe_description_label.setText(description)

    def _sync_filter_controls(self) -> None:
        controls = (
            self.clahe,
            self.grayscale,
            self.denoise,
            self.sharpen,
            self.brightness_slider,
            self.contrast_slider,
        )
        for control in controls:
            control.blockSignals(True)
        self.clahe.setChecked(self.preprocessing.clahe)
        self.grayscale.setChecked(self.preprocessing.grayscale)
        self.denoise.setChecked(self.preprocessing.denoise)
        self.sharpen.setChecked(self.preprocessing.sharpen)
        self.brightness_slider.setValue(self.preprocessing.brightness)
        self.contrast_slider.setValue(round(self.preprocessing.contrast * 100))
        for control in controls:
            control.blockSignals(False)
        if self.current_frame is not None:
            self.dataset_video.set_source(self.current_frame, self.preprocessing)
            display_config = self.predictor.preprocessing if self.predictor else self.preprocessing
            self.inspection_video.set_source(self.current_frame, display_config)

    def _activate_recipe(self, recipe_id: str) -> None:
        self.store = self.catalog.activate(recipe_id)
        self.paths = self.store.paths
        metadata = self.store.read_metadata()
        self.preprocessing = PreprocessingConfig.from_dict(metadata.get("preprocessing"))
        self._last_inspection_frame = None
        self._last_inspection_result = None
        self._last_inspection_id = None
        self._load_model_if_available()
        self._reset_inspection_panel()
        self._sync_filter_controls()
        self.refresh_state()

    def _switch_recipe(self, _index: int) -> None:
        recipe_id = self.recipe_selector.currentData()
        if not recipe_id:
            return
        current_id = str(self.store.read_metadata().get("recipe_id", self.paths.root.name))
        if recipe_id == current_id:
            return
        if self.training_thread is not None:
            QMessageBox.information(
                self,
                "Treinamento em andamento",
                "Aguarde ou cancele o treinamento antes de trocar de receita.",
            )
            self._refresh_recipe_selector()
            return
        self._activate_recipe(str(recipe_id))

    def _create_recipe(self) -> None:
        if self.training_thread is not None:
            QMessageBox.information(self, "Treinamento em andamento", "Finalize o treinamento primeiro.")
            return
        dialog = RecipeDialog(self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        name, part_type, description = dialog.values()
        store = self.catalog.create(name, part_type, description)
        recipe_id = str(store.read_metadata()["recipe_id"])
        self._activate_recipe(recipe_id)

    def _edit_recipe(self) -> None:
        metadata = self.store.read_metadata()
        recipe_id = str(metadata.get("recipe_id", self.paths.root.name))
        dialog = RecipeDialog(
            self,
            name=str(metadata.get("name", "")),
            part_type=str(metadata.get("part_type", "")),
            description=str(metadata.get("description", "")),
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        name, part_type, description = dialog.values()
        self.catalog.update(recipe_id, name, part_type, description)
        self.refresh_state()

    def _clear_dataset(self) -> None:
        if self.training_thread is not None:
            QMessageBox.information(self, "Treinamento em andamento", "Finalize ou cancele o treinamento antes de limpar as imagens.")
            return
        counts = self.store.counts()
        total = counts["ok"] + counts["nok"]
        if total == 0:
            QMessageBox.information(self, "Dataset vazio", "Esta receita ainda não possui imagens.")
            return
        metadata = self.store.read_metadata()
        recipe_name = str(metadata.get("name") or "receita atual")
        answer = QMessageBox.warning(
            self,
            "Apagar todas as imagens?",
            f"Você está prestes a apagar permanentemente {total} imagens da receita “{recipe_name}”.\n\n"
            "As inspeções registradas serão preservadas. O modelo atual será arquivado e desativado, "
            "pois deixará de representar o dataset. Esta ação não pode ser desfeita.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        removed, archived_model = self.store.clear_images()
        self.predictor = None
        self._last_inspection_frame = None
        self._last_inspection_result = None
        self._last_inspection_id = None
        self._reset_inspection_panel()
        self.refresh_state()
        archive_text = " O modelo anterior foi arquivado." if archived_model else ""
        QMessageBox.information(
            self,
            "Dataset limpo",
            f"{removed} imagens foram removidas com segurança.{archive_text}",
        )

    def _persist_preprocessing(self) -> None:
        self.store.update_metadata(preprocessing=self.preprocessing.to_dict())

    def _capture_sample(self, label: str) -> None:
        if self.current_frame is None:
            QMessageBox.information(self, "Sem imagem", "Conecte a câmera USB antes de capturar.")
            return
        for existing in self.store.list_images(label)[-8:]:
            previous = cv2.imread(str(existing), cv2.IMREAD_COLOR)
            if previous is None:
                continue
            similarity = visual_similarity(self.current_frame, previous, self.preprocessing)
            if similarity >= 0.985:
                answer = QMessageBox.question(
                    self,
                    "Imagem muito semelhante",
                    "Esta captura é quase igual a uma amostra já registrada "
                    f"({similarity:.1%} de similaridade).\n\n"
                    "Para um modelo melhor, varie posição, iluminação ou exemplar. "
                    "Deseja salvar mesmo assim?",
                )
                if answer != QMessageBox.StandardButton.Yes:
                    return
                break
        try:
            saved = self.store.save_frame(self.current_frame, label)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Falha ao salvar", str(exc))
            return
        self.store.log_event("sample_captured", label=label, file=saved.name)
        self.refresh_state()

    def _import_samples(self, label: str) -> None:
        files, _ = QFileDialog.getOpenFileNames(
            self,
            f"Importar imagens {label.upper()}",
            "",
            "Imagens (*.jpg *.jpeg *.png *.bmp *.webp)",
        )
        if not files:
            return
        imported = self.store.import_images((Path(path) for path in files), label)
        if imported:
            self.store.log_event("samples_imported", label=label, count=len(imported))
        if len(imported) != len(files):
            QMessageBox.warning(
                self,
                "Importação parcial",
                f"{len(imported)} de {len(files)} imagens foram importadas.",
            )
        self.refresh_state()

    def _delete_selected_sample(self) -> None:
        item = self.sample_list.currentItem()
        if item is None:
            return
        path = Path(item.data(Qt.ItemDataRole.UserRole))
        answer = QMessageBox.question(
            self,
            "Remover amostra",
            f"Remover {path.name} do dataset?",
        )
        if answer == QMessageBox.StandardButton.Yes:
            self.store.delete_image(path)
            self.refresh_state()

    def _start_training(self) -> None:
        if self.training_thread is not None:
            return
        try:
            from qualityai.ml import validate_labeled_images

            validate_labeled_images(self.store.all_labeled_images())
        except TrainingError as exc:
            QMessageBox.warning(self, "Dataset incompleto", str(exc))
            return

        self.training_progress.setValue(0)
        self.training_log.clear()
        self.train_button.setEnabled(False)
        self.cancel_training_button.setEnabled(True)
        self.training_status.setText("Inicializando treinamento local…")

        thread = QThread(self)
        worker = TrainingWorker(self.store, self.preprocessing)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.progress.connect(self._on_training_progress)
        worker.finished.connect(self._on_training_finished)
        worker.failed.connect(self._on_training_failed)
        worker.cancelled.connect(self._on_training_cancelled)
        for signal in (worker.finished, worker.failed, worker.cancelled):
            signal.connect(thread.quit)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(self._clear_training_thread)
        self.training_thread = thread
        self.training_worker = worker
        thread.start()

    def _cancel_training(self) -> None:
        if self.training_worker is not None:
            self.training_status.setText("Cancelando após a etapa atual…")
            self.training_worker.cancel()

    @Slot(int, str)
    def _on_training_progress(self, value: int, message: str) -> None:
        self.training_progress.setValue(value)
        self.training_status.setText(message)
        self.training_log.append(f"[{value:3d}%] {message}")

    @Slot(object)
    def _on_training_finished(self, report: TrainingReport) -> None:
        self.training_progress.setValue(100)
        self.training_status.setText("Modelo treinado e validado.")
        self.training_log.append("")
        self.training_log.append(f"Acurácia balanceada: {report.balanced_accuracy:.1%}")
        self.training_log.append(f"F1: {report.f1:.1%}")
        self.training_log.append(f"ROC AUC: {report.roc_auc:.1%}")
        self.training_log.append(f"Matriz de confusão [NOK, OK]: {report.confusion_matrix}")
        self.store.log_event(
            "model_trained",
            version=report.model_version,
            images=report.total_images,
            balanced_accuracy=report.balanced_accuracy,
            f1=report.f1,
        )
        if self.store.database is not None and self.store.recipe_id:
            self.store.database.record_training_and_model(
                self.store.recipe_id,
                version=report.model_version,
                model_path=report.model_path,
                total_images=report.total_images,
                folds=report.folds,
                metrics={
                    "accuracy": report.accuracy,
                    "balanced_accuracy": report.balanced_accuracy,
                    "precision": report.precision,
                    "recall": report.recall,
                    "f1": report.f1,
                    "roc_auc": report.roc_auc,
                    "confusion_matrix": report.confusion_matrix,
                },
                confidence_threshold=DEFAULT_CONFIDENCE_THRESHOLD,
            )
        self._load_model_if_available()
        self.refresh_state()

    @Slot(str)
    def _on_training_failed(self, message: str) -> None:
        self.training_status.setText("Falha no treinamento.")
        self.training_log.append(f"ERRO: {message}")
        QMessageBox.critical(self, "Treinamento interrompido", message)

    @Slot(str)
    def _on_training_cancelled(self, message: str) -> None:
        self.training_status.setText(message)
        self.training_log.append(message)

    @Slot()
    def _clear_training_thread(self) -> None:
        self.training_thread = None
        self.training_worker = None
        self.train_button.setEnabled(True)
        self.cancel_training_button.setEnabled(False)
        if self._close_after_training:
            QTimer.singleShot(0, self.close)

    def _load_model_if_available(self) -> None:
        if not self.paths.model.is_file():
            self.predictor = None
            return
        try:
            self.predictor = QualityPredictor(self.paths.model)
        except Exception as exc:  # noqa: BLE001
            self.predictor = None
            QMessageBox.warning(self, "Modelo incompatível", str(exc))

    def _inspect_current_frame(self) -> None:
        if self.current_frame is None:
            QMessageBox.information(self, "Sem imagem", "Conecte a câmera antes de inspecionar.")
            return
        self._inspect_frame(self.current_frame)

    def _inspect_imported_image(self) -> None:
        file, _ = QFileDialog.getOpenFileName(
            self,
            "Selecionar imagem para inspeção",
            "",
            "Imagens (*.jpg *.jpeg *.png *.bmp *.webp)",
        )
        if not file:
            return
        frame = cv2.imread(file, cv2.IMREAD_COLOR)
        if frame is None:
            QMessageBox.warning(self, "Imagem inválida", "Não foi possível abrir a imagem.")
            return
        self.inspection_video.set_source(
            frame, self.predictor.preprocessing if self.predictor else self.preprocessing
        )
        self._inspect_frame(frame)

    def _inspect_frame(self, frame) -> None:
        if self.predictor is None:
            QMessageBox.information(
                self,
                "Modelo não treinado",
                "Complete o dataset e treine uma versão antes de inspecionar.",
            )
            return
        try:
            result = self.predictor.predict(frame)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Falha na inferência", str(exc))
            return

        if result.requires_review:
            display = "REVISÃO"
            style = "ResultReview"
            guidance = "Confiança abaixo do limite. Um inspetor deve revisar esta peça."
        elif result.label == "OK":
            display = "OK"
            style = "ResultOk"
            guidance = "A IA indica conformidade. Confirme conforme o procedimento de qualidade."
        else:
            display = "NOK"
            style = "ResultNok"
            guidance = "A IA indica não conformidade. Separe a peça para avaliação humana."
        self.result_label.setText(display)
        self.result_label.setObjectName(style)
        self.result_label.style().unpolish(self.result_label)
        self.result_label.style().polish(self.result_label)
        self.result_confidence.setText(f"Confiança: {result.confidence:.1%}")
        self.result_model.setText(f"Modelo: {result.model_version}")
        self.result_guidance.setText(guidance)
        self._last_inspection_frame = frame.copy()
        self._last_inspection_result = result
        for button in (
            self.confirm_result_button,
            self.correct_ok_button,
            self.correct_nok_button,
        ):
            button.setEnabled(True)

        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        destination = self.paths.inspections / f"{timestamp}_{display.lower()}_{result.confidence:.0%}.jpg"
        cv2.imwrite(str(destination), frame, [cv2.IMWRITE_JPEG_QUALITY, 92])
        if self.store.database is not None and self.store.recipe_id:
            self._last_inspection_id = self.store.database.record_inspection(
                self.store.recipe_id,
                model_id=result.model_version,
                file_path=destination,
                predicted_label=result.label.lower(),
                confidence=result.confidence,
                requires_review=result.requires_review,
            )
        self.store.log_event(
            "inspection_created",
            prediction=result.label.lower(),
            confidence=result.confidence,
            requires_review=result.requires_review,
            model_version=result.model_version,
            file=destination.name,
        )

    def _confirm_inspection(self) -> None:
        if self._last_inspection_result is None:
            return
        result = self._last_inspection_result
        self.store.log_event(
            "inspection_reviewed",
            prediction=result.label.lower(),
            human_label=result.label.lower(),
            corrected=False,
            model_version=result.model_version,
        )
        if self.store.database is not None and self._last_inspection_id:
            self.store.database.record_review(
                self._last_inspection_id,
                result.label.lower(),
                corrected=False,
            )
        self.result_guidance.setText("Resultado confirmado e registrado pelo inspetor.")
        self._finish_review()

    def _correct_inspection(self, human_label: str) -> None:
        if self._last_inspection_result is None or self._last_inspection_frame is None:
            return
        result = self._last_inspection_result
        saved = self.store.save_frame(
            self._last_inspection_frame, human_label, source="human_review"
        )
        self.store.log_event(
            "inspection_reviewed",
            prediction=result.label.lower(),
            human_label=human_label,
            corrected=True,
            model_version=result.model_version,
            dataset_file=saved.name,
        )
        if self.store.database is not None and self._last_inspection_id:
            self.store.database.record_review(
                self._last_inspection_id,
                human_label,
                corrected=True,
                dataset_image_id=self.store.database.image_id_for_path(saved),
            )
        self.result_guidance.setText(
            f"Correção salva como {human_label.upper()} e adicionada ao próximo treinamento."
        )
        self.refresh_state()
        self._finish_review()

    def _finish_review(self) -> None:
        for button in (
            self.confirm_result_button,
            self.correct_ok_button,
            self.correct_nok_button,
        ):
            button.setEnabled(False)

    def _reset_inspection_panel(self) -> None:
        self._last_inspection_id = None
        self.result_label.setText("AGUARDANDO")
        self.result_label.setObjectName("ResultReview")
        self.result_label.style().unpolish(self.result_label)
        self.result_label.style().polish(self.result_label)
        self.result_confidence.setText("Confiança: —")
        self.result_guidance.setText(
            "Capture uma imagem usando o modelo da receita ativa. Baixa confiança exige revisão humana."
        )
        self._finish_review()

    def refresh_state(self) -> None:
        self._refresh_recipe_selector()
        self._sync_recipe_controls()
        counts = self.store.counts()
        total = counts["ok"] + counts["nok"]
        ready = counts["ok"] >= MIN_IMAGES_PER_CLASS and counts["nok"] >= MIN_IMAGES_PER_CLASS
        self.ok_count.setText(f"OK  {counts['ok']} / {MIN_IMAGES_PER_CLASS}")
        self.nok_count.setText(f"NOK  {counts['nok']} / {MIN_IMAGES_PER_CLASS}")
        self.ok_progress.setValue(min(counts["ok"], MIN_IMAGES_PER_CLASS))
        self.nok_progress.setValue(min(counts["nok"], MIN_IMAGES_PER_CLASS))
        self.dashboard_dataset.set_data(
            f"{total} imagens",
            f"{counts['ok']} OK · {counts['nok']} NOK",
        )
        self.training_dataset_card.set_data(
            f"{counts['ok']} + {counts['nok']}",
            "dataset pronto" if ready else "mínimo 10 por classe",
        )
        self.train_button.setEnabled(ready and self.training_thread is None)
        if not ready:
            self.training_status.setText("Complete 10 imagens OK e 10 imagens NOK.")

        self.sample_list.clear()
        recent = sorted(self.store.all_labeled_images(), key=lambda item: item[0].stat().st_mtime, reverse=True)
        for path, label in recent[:30]:
            item = QListWidgetItem(f"{label.upper():3s}   {path.name}")
            item.setData(Qt.ItemDataRole.UserRole, str(path))
            self.sample_list.addItem(item)

        if self.predictor is None:
            self.dashboard_model.set_data("Não treinado", "complete o dataset")
            self.training_metric_card.set_data("—", "nenhum modelo validado")
            self.training_model_card.set_data("—", "aguardando treinamento")
            self.result_model.setText("Modelo: nenhum modelo carregado")
        else:
            balanced = float(self.predictor.metrics.get("balanced_accuracy", 0.0))
            self.dashboard_model.set_data("Pronto", f"versão {self.predictor.version}")
            self.training_metric_card.set_data(f"{balanced:.1%}", "acurácia balanceada")
            size_mb = self.paths.model.stat().st_size / (1024 * 1024)
            self.training_model_card.set_data(f"{size_mb:.1f} MB", "artefato local")
            self.result_model.setText(f"Modelo: {self.predictor.version}")

    def closeEvent(self, event: QCloseEvent) -> None:
        if self.training_thread is not None and self.training_thread.isRunning():
            if not self._close_after_training:
                answer = QMessageBox.question(
                    self,
                    "Treinamento em andamento",
                    "Deseja cancelar o treinamento e fechar quando a etapa atual terminar?",
                )
                if answer != QMessageBox.StandardButton.Yes:
                    event.ignore()
                    return
                self._close_after_training = True
                if self.training_worker is not None:
                    self.training_worker.cancel()
                self.training_status.setText("Cancelando com segurança antes de fechar…")
            event.ignore()
            return
        self.camera_timer.stop()
        self.camera.release()
        event.accept()


def main() -> int:
    os.environ.setdefault("QT_ENABLE_HIGHDPI_SCALING", "1")
    app = QApplication(sys.argv)
    app.setApplicationName("QualityAI")
    app.setOrganizationName("QualityAI")
    app.setStyle("Fusion")
    install_brand_fonts(app)
    app.setStyleSheet(APP_STYLESHEET)
    window = MainWindow()
    window.show()
    return app.exec()
