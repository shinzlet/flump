import sys
import os
import random
import string
from PyQt6.QtWidgets import QApplication, QWidget, QLabel, QPushButton, QVBoxLayout, QMessageBox, QComboBox, QScrollArea, QFrame, QSlider, QCheckBox, QLineEdit, QColorDialog
from PyQt6.QtGui import QPixmap, QImage, QDragEnterEvent, QDropEvent, QKeyEvent, QFocusEvent, QColor
from PyQt6.QtCore import Qt
from PIL import Image, UnidentifiedImageError
import random
import datetime
import numpy as np
from .filter import Filter
from typing import Type, Optional, Any
from .copy_image import copy_image

from .filters.invert_luminance import InvertLuminance  # noqa: F401
from .filters.adjust_hsv import AdjustHSV # noqa: F401
from .filters.adjust_rgb import AdjustRGB # noqa: F401
from .filters.chromakey import ChromaKey # noqa: F401

class Flump(QWidget):
    _BUILTIN_FILTERS: list[Type[Filter]] = Filter.__subclasses__()
    _USER_FILTER_PATH: str = os.path.expanduser("~/.config/flump/filters")

    _filter_selector: QComboBox
    _image_area: QLabel
    _save_button: QPushButton
    _filter: Filter
    _user_filters: list[Type[Filter]] = []
    _input_image: Optional[Image.Image]
    _full_output_image: Optional[Image.Image]
    _copy_synced: bool
    _param_map: dict[str, QWidget]
    _color_dialogs: dict[str, QColorDialog]

    def __init__(self):
        super().__init__()
        self._user_filters = Flump._load_user_filters()
        self._initialize_ui()
        self._input_image = None
        self._full_output_image = None
        self._set_filter(Flump._BUILTIN_FILTERS[0])
        self._param_map = {}
        self._copy_synced = False
        self._color_dialogs = {}

    def _load_user_filters() -> list[Type[Filter]]:
        if not os.path.exists(Flump._USER_FILTER_PATH):
            os.makedirs(Flump._USER_FILTER_PATH)
            return []
        
        for file in os.listdir(Flump._USER_FILTER_PATH):
            if file.endswith(".py"):
                with open(os.path.join(Flump._USER_FILTER_PATH, file)) as f:
                    code = f.read()
                    exec(code)
        
        return [filter for filter in Filter.__subclasses__() if filter not in Flump._BUILTIN_FILTERS]

    def _all_filters(self) -> list[Type[Filter]]:
        return Flump._BUILTIN_FILTERS + self._user_filters

    def _get_filter_by_index(self, index: int) -> Type[Filter]:
        return self._all_filters()[index]
    
    def _initialize_ui(self):
        self.setAcceptDrops(True)
        self.setWindowTitle("Flump")
        w, h = 300, 500
        self.setGeometry(100, 100, w, h)
        self.setFixedSize(w, h)
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint)

        layout = QVBoxLayout()
        self.setLayout(layout)

        self._filter_selector = QComboBox()
        for filter in self._all_filters():
            self._filter_selector.addItem(filter.name())
        self._filter_selector.currentIndexChanged.connect(self._on_filter_index_changed)
        layout.addWidget(self._filter_selector)

        self._image_preview_area = QLabel("Drag and drop an image here\nor paste from clipboard")
        self._image_preview_area.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._image_preview_area.setMinimumHeight(200)
        layout.addWidget(self._image_preview_area)

        self._save_button = QPushButton("Save to Downloads")
        self._save_button.clicked.connect(self._save_image)
        self._save_button.setEnabled(False)
        layout.addWidget(self._save_button)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setMinimumHeight(50)
        self._filter_control_layout = QVBoxLayout()
        frame = QFrame(scroll)
        frame.setLayout(self._filter_control_layout)
        scroll.setWidget(frame)
        layout.addWidget(scroll)

        motd = "flump • https:// github.com/shinzlet/flump"

        if random.uniform(0, 1) < 0.3:
            motd = random.choice([
                "Happy flumping!",
                "Flump it up!",
                "It's always flump o'clock somewhere.",
                f"Bug-free since {datetime.datetime.now().strftime('%B %d, %Y')}!",
                "Flump Lets U Modify Pixels",
                "The only app that isn't not Flump.",
                "I'm sorry, but as a language model deve-"
            ])
        
        if random.uniform(0, 1) < 1e-7:
            motd = "Please purchase Flump premium."
        
        self._copied_label = QLabel(motd)
        self._copied_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._copied_label)

        # I do this instead of overloading methods to keep code camel_cased
        self.dragEnterEvent = self._drag_enter_event
        self.dropEvent = self._drop_event
        self.keyPressEvent = self._on_key_pressed

        # window focus loss detector
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.focusOutEvent = self._focus_out_event
    
    def _focus_out_event(self, event: QFocusEvent):
        self._ensure_copy_synced()
    
    def _map_slider_to_float_spec(slider_val: int, spec: dict[str, Any]) -> float:
        min, max = spec['min'], spec['max']
        return min + (max - min) * slider_val / 1000

    def _default_slider_value(spec: dict[str, Any]) -> int:
        min, max, default = spec['min'], spec['max'], spec['default']
        return int((default - min) / (max - min) * 1000)

    def _set_input_image(self, image_source: str | QImage):
        if isinstance(image_source, str):
            try:
                if os.path.isfile(image_source):
                    # NOTE: We have to convert to RGBA and copy at the point of entry - the loaded image
                    # a format specific subclass which seems buggy and leads to inexcplicable mutation if
                    # you convert and copy from it repeatedly!
                    self._input_image = Image.open(image_source).convert("RGBA").copy()
                else:
                    return
            except (FileNotFoundError, UnidentifiedImageError) as e:
                QMessageBox.warning(self, "Error", f"Failed to load image: {str(e)}")
                return
        else:
            # See NOTE above
            self._input_image = self._q_image_to_pil(image_source).convert("RGBA").copy()
        
        self._update_output_preview()
    
    def _set_filter(self, filter: Type[Filter]):
        self._filter = filter

        layout = self._filter_control_layout
        
        self._param_map = {}
        for child in layout.parentWidget().children():
            if child != layout:
                child.deleteLater()
        
        for param_name, param_spec in self._filter.default_params().items():
            layout.addWidget(QLabel(param_name))

            type = param_spec['type']
            widget = None
            if type == "float":
                widget = QSlider(Qt.Orientation.Horizontal)
                widget.setMinimum(0)
                widget.setMaximum(1000)
                widget.setValue(Flump._default_slider_value(param_spec))
                widget.valueChanged.connect(self._update_output_preview)
                widget.sliderReleased.connect(self._ensure_copy_synced)
            elif type == "bool":
                widget = QCheckBox()
                widget.setChecked(param_spec["default"])
                def _on_check_state_changed(checked: bool):
                    self._update_output_preview()
                    self._ensure_copy_synced()
                widget.checkStateChanged.connect(_on_check_state_changed)
            elif type == "str":
                widget = QLineEdit()
                widget.setText(param_spec["default"])
                widget.textChanged.connect(self._update_output_preview)
                widget.editingFinished.connect(self._ensure_copy_synced)
            elif type == "color":
                # implement qt color picker:
                # https://doc.qt.io/qtforpython/PySide6/QtWidgets/QColorDialog.html
                # Create a button that opens a persistent qColorDialog
                color = QColor(*param_spec["default"], 255)
                self._color_dialogs[param_name] = QColorDialog(color)
                widget = QPushButton("Choose Color")
                def _on_button_clicked(*, name = param_name):
                    self._color_dialogs[name].show()
                widget.clicked.connect(_on_button_clicked)
                def _on_color_changed(color: QColor):
                    self._update_output_preview()
                    self._ensure_copy_synced()
                self._color_dialogs[param_name].colorSelected.connect(_on_color_changed)
            else:
                raise ValueError(f"Invalid parameter specification: {param_spec}")

            self._param_map[param_name] = widget
            layout.addWidget(widget)
        
        layout.addStretch()
        self._update_output_preview()
    
    def _process_image(self, image: Image.Image):
        output = self._filter.apply(image, self._get_filter_params())
        
        if output.mode != 'RGBA':
            output = output.convert('RGBA')
        
        return output
    
    # Returns the output image at full resolution, using caching to avoid recomputing
    # as much as possible. This can be slow if you are changing parameters - try to only use
    # this when you absolutely need the full size image. Returns None if no input image is set.
    def _get_full_output(self) -> Optional[Image.Image]:
        if self._input_image is None:
            return None

        if self._full_output_image is None:
            self._full_output_image = self._process_image(self._input_image)
        
        return self._full_output_image

    def _ensure_copy_synced(self):
        if not self._copy_synced:
            output = self._get_full_output()
            if output is not None:
                copy_image(output)
                self._copy_synced = True
                self._copied_label.setText("Copied to clipboard")
    
    def _get_filter_params(self) -> dict[str, float | str | bool]:
        default_params = self._filter.default_params()
        params = {}
        for param_name, param_widget in self._param_map.items():
            if isinstance(param_widget, QSlider):
                params[param_name] = Flump._map_slider_to_float_spec(param_widget.value(), default_params[param_name])
            elif isinstance(param_widget, QCheckBox):
                params[param_name] = param_widget.isChecked()
            elif isinstance(param_widget, QLineEdit):
                params[param_name] = param_widget.text()
            elif param_name in self._color_dialogs:
                params[param_name] = self._color_dialogs[param_name].currentColor().getRgb()[0:3]
            else:
                raise ValueError(f"Invalid parameter widget: {param_widget}")
        return params
        
    def _on_filter_index_changed(self, index: int):
        self._set_filter(self._get_filter_by_index(index))
    
    def _drag_enter_event(self, event: QDragEnterEvent):
        if event.mimeData().hasImage() or event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()
    
    def _q_image_to_pil(self, q_image: QImage) -> Image.Image:
        q_image.convertTo(QImage.Format.Format_RGBA8888)
        width, height = q_image.width(), q_image.height()
        buffer = q_image.constBits()
        buffer.setsize(height * width * 4)
        arr = np.frombuffer(buffer, np.uint8).reshape((height, width, 4))
        return Image.fromarray(arr)
    
    def _update_output_preview(self):
        if self._input_image is None:
            return

        try:
            downscaled_input = self._input_image
            # 256x256 images are usually very quick to compute, so this is kind of our heuristic for "is this a lot of pixels"
            pixel_threshold = 256 ** 2
            oversize_factor = downscaled_input.width * downscaled_input.height / pixel_threshold
            if oversize_factor > 1:
                skip = int(oversize_factor ** 0.5)
                downscaled_input = downscaled_input.resize(
                    (downscaled_input.width // skip, downscaled_input.height // skip),
                    Image.Resampling.NEAREST)
                
            output_preview = self._process_image(downscaled_input)
            self._copy_synced = False
            self._full_output_image = None
            self._copied_label.setText("")

            # Display transformed image
            qpixmap = QPixmap.fromImage(QImage(
                output_preview.tobytes(),
                output_preview.width,
                output_preview.height,
                QImage.Format.Format_RGBA8888))
            self._image_preview_area.setPixmap(qpixmap.scaled(
                self._image_preview_area.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation))

            self._save_button.setEnabled(True)
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to process image: {str(e)}")
            self._image_preview_area.setText('Drag and drop an image here\nor paste from clipboard')
            self._save_button.setEnabled(False)

    def _save_image(self):
        output = self._get_full_output()
        if output is not None:
            while True:
                random_name = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10)) + '.png'
                path = os.path.expanduser(f'~/Downloads/{random_name}')
                if os.path.exists(path):
                    continue
                output.save(path)
                QMessageBox.information(self, "Saved", f'Image saved to {path}')
                break
    
    def _drop_event(self, event: QDropEvent):
        if event.mimeData().hasImage():
            q_image = QImage(event.mimeData().imageData())
            self._set_input_image(q_image)
        elif event.mimeData().hasUrls():
            file_path = event.mimeData().urls()[0].toLocalFile()
            self._set_input_image(file_path)

    def _on_key_pressed(self, event: QKeyEvent | None):
        if event.key() == Qt.Key.Key_V and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            clipboard = QApplication.clipboard()
            mimeData = clipboard.mimeData()

            if mimeData.hasUrls():
                file_path = mimeData.urls()[0].toLocalFile()
                self._set_input_image(file_path)
            elif mimeData.hasImage():
                self._set_input_image(clipboard.image())
            elif mimeData.hasText():
                file_path = mimeData.text()
                self._set_input_image(file_path)
            else:
                QMessageBox.warning(self, "Error", "No image or valid file path found in clipboard")

def main():
    app = QApplication(sys.argv)
    ex = Flump()
    ex.show()
    sys.exit(app.exec())

if __name__ == '__main__':
	main()
