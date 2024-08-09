import sys
import os
import random
import string
from PyQt6.QtWidgets import QApplication, QWidget, QLabel, QPushButton, QVBoxLayout, QMessageBox, QComboBox, QScrollArea, QFrame, QSlider, QCheckBox, QLineEdit
from PyQt6.QtGui import QPixmap, QImage, QDragEnterEvent, QDropEvent, QKeyEvent
from PyQt6.QtCore import Qt, QUrl
from PIL import Image, UnidentifiedImageError
import AppKit
import io
import numpy as np
from .filter import Filter
from typing import Type, Optional
from .filters.invert_luminance import InvertLuminance

class Flump(QWidget):
    _BUILTIN_FILTERS: list[Type[Filter]] = Filter.__subclasses__()
    _USER_FILTER_PATH: str = os.path.expanduser("~/.config/flump/filters")

    _filter_selector: QComboBox
    _image_area: QLabel
    _save_button: QPushButton
    _filter: Filter
    _user_filters: list[Type[Filter]] = []
    _input_image: Optional[Image.Image]
    _output_image: Optional[Image.Image]
    _param_map: dict[str, QWidget]

    def __init__(self):
        super().__init__()
        self._user_filters = Flump._load_user_filters()
        self._initialize_ui()
        self._input_image = None
        self._output_image = None
        self._set_filter(Flump._BUILTIN_FILTERS[0])
        self._param_map = {}

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

        self.label = QLabel("Drag and drop an image here\nor paste from clipboard")
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setMinimumHeight(200)
        layout.addWidget(self.label)

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

        # I do this instead of overloading methods to keep code camel_cased
        self.dragEnterEvent = self._drag_enter_event
        self.dropEvent = self._drop_event
        self.keyPressEvent = self._on_key_pressed
    
    def _map_slider_to_float_spec(slider_val: int, spec: tuple[float, float, float]) -> float:
        return spec[0] + (spec[1] - spec[0]) * slider_val / 1000

    def _default_slider_value(spec: tuple[float, float, float]) -> int:
        return int((spec[2] - spec[1]) / (spec[1] - spec[0]) * 1000)

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
        
        self._process_image()
    
    def _set_filter(self, filter: Type[Filter]):
        self._filter = filter

        layout = self._filter_control_layout
        
        self._param_map = {}
        for child in layout.parentWidget().children():
            if child != layout:
                child.deleteLater()
        
        for param_name, param_spec in self._filter.default_params().items():
            layout.addWidget(QLabel(param_name))
            widget = None
            if isinstance(param_spec, tuple):
                widget = QSlider(Qt.Orientation.Horizontal)
                widget.setMinimum(0)
                widget.setMaximum(1000)
                widget.setValue(Flump._default_slider_value(param_spec))
                widget.valueChanged.connect(self._process_image)
            elif isinstance(param_spec, bool):
                widget = QCheckBox()
                widget.setChecked(param_spec)
                widget.checkStateChanged.connect(self._process_image)
            elif isinstance(param_spec, str):
                widget = QLineEdit()
                widget.setText(param_spec)
                widget.textChanged.connect(self._process_image)
            else:
                raise ValueError(f"Invalid parameter specification: {param_spec}")

            self._param_map[param_name] = widget
            layout.addWidget(widget)
        
        layout.addStretch()
        self._process_image()
    
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
        q_image = q_image.convertToFormat(QImage.Format.Format_RGBA8888)
        width, height = q_image.width(), q_image.height()
        buffer = q_image.constBits()
        buffer.setsize(height * width * 4)
        arr = np.frombuffer(buffer, np.uint8).reshape((height, width, 4))
        return Image.fromarray(arr)
    
    def _process_image(self):
        if self._input_image is None:
            return

        try:
            self._output_image = self._filter.apply(self._input_image, self._get_filter_params()).convert('RGBA')

            # Display transformed image
            qpixmap = QPixmap.fromImage(QImage(
                self._output_image.tobytes(),
                self._output_image.width,
                self._output_image.height,
                QImage.Format.Format_RGBA8888))
            self.label.setPixmap(qpixmap.scaled(
                self.label.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation))

            # Copy to clipboard
            output = io.BytesIO()
            self._output_image.save(output, format='PNG')
            ns_image = AppKit.NSImage.alloc().initWithData_(
                AppKit.NSData.dataWithBytes_length_(output.getvalue(), len(output.getvalue()))
            )

            pb = AppKit.NSPasteboard.generalPasteboard()
            pb.clearContents()
            pb.setData_forType_(ns_image.TIFFRepresentation(), AppKit.NSTIFFPboardType)

            self._save_button.setEnabled(True)
        except Exception as e:
            print(e)
            QMessageBox.warning(self, "Error", f"Failed to process image: {str(e)}")
            self.label.setText('Drag and drop an image here\nor paste from clipboard')
            self._save_button.setEnabled(False)

    def _save_image(self):
        if self._output_image is not None:
            while True:
                random_name = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10)) + '.png'
                path = os.path.expanduser(f'~/Downloads/{random_name}')
                if os.path.exists(path):
                    continue
                self._output_image.save(path)
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
