import sys
import os
import random
import string
from PyQt6.QtWidgets import QApplication, QWidget, QLabel, QPushButton, QVBoxLayout, QMessageBox
from PyQt6.QtGui import QPixmap, QImage, QDragEnterEvent, QDropEvent
from PyQt6.QtCore import Qt, QUrl
from PIL import Image, ImageOps
import AppKit
import io
import numpy as np

class ImageInverter(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.setAcceptDrops(True)
        self.setWindowTitle('Flump')
        self.setGeometry(100, 100, 300, 300)

        layout = QVBoxLayout()

        self.label = QLabel('Drag and drop an image here\nor paste from clipboard')
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.label)

        self.saveButton = QPushButton('Save to Downloads')
        self.saveButton.clicked.connect(self.saveImage)
        self.saveButton.setEnabled(False)
        layout.addWidget(self.saveButton)

        self.setLayout(layout)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasImage() or event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event: QDropEvent):
        if event.mimeData().hasImage():
            self.processImage(QImage(event.mimeData().imageData()))
        elif event.mimeData().hasUrls():
            file_path = event.mimeData().urls()[0].toLocalFile()
            self.processImageFromFile(file_path)

    def processImageFromFile(self, file_path):
        try:
            pil_image = Image.open(file_path)
            self.processImage(self.pilToQImage(pil_image))
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to load image: {str(e)}")

    def pilToQImage(self, pil_image):
        im2 = pil_image.convert("RGBA")
        data = im2.tobytes("raw", "RGBA")
        qim = QImage(data, im2.size[0], im2.size[1], QImage.Format.Format_RGBA8888)
        return qim

    def processImage(self, qimage):
        try:
            # Convert QImage to PIL Image
            buffer = qimage.convertToFormat(QImage.Format.Format_RGBA8888)
            width, height = buffer.width(), buffer.height()
            ptr = buffer.constBits()
            ptr.setsize(height * width * 4)
            arr = np.frombuffer(ptr, np.uint8).reshape((height, width, 4))
            pil_image = Image.fromarray(arr)

            # Convert to LAB color space
            lab_image = pil_image.convert('LAB')

            # Split into L, A, and B channels
            l, a, b = lab_image.split()

            # Invert the L channel (luminance)
            inverted_l = ImageOps.invert(l)

            # Merge the inverted L channel with original A and B channels
            inverted_lab = Image.merge('LAB', (inverted_l, a, b))

            # Convert back to RGB
            inverted_image = inverted_lab.convert('RGB')
            inverted_image.putalpha(pil_image.getchannel('A'))

            # Display inverted image
            qpixmap = QPixmap.fromImage(QImage(inverted_image.tobytes(), inverted_image.width, inverted_image.height, QImage.Format.Format_RGBA8888))
            self.label.setPixmap(qpixmap.scaled(self.label.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))

            # Copy to clipboard
            output = io.BytesIO()
            inverted_image.save(output, format='PNG')
            # jaraco_clipboard.copy_image(output.getvalue())
            ns_image = AppKit.NSImage.alloc().initWithData_(
                AppKit.NSData.dataWithBytes_length_(output.getvalue(), len(output.getvalue()))
            )

            pb = AppKit.NSPasteboard.generalPasteboard()
            pb.clearContents()
            pb.setData_forType_(ns_image.TIFFRepresentation(), AppKit.NSTIFFPboardType)

            self.saveButton.setEnabled(True)
            self.inverted_image = inverted_image
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to process image: {str(e)}")
            self.label.setText('Drag and drop an image here\nor paste from clipboard')
            self.saveButton.setEnabled(False)

    def saveImage(self):
        if hasattr(self, 'inverted_image'):
            while True:
                random_name = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10)) + '.png'
                path = os.path.expanduser(f'~/Downloads/{random_name}')
                if os.path.exists(path):
                    continue
                self.inverted_image.save(path)
                QMessageBox.information(self, "Saved", f'Image saved to {path}')
                break

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_V and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            clipboard = QApplication.clipboard()
            mimeData = clipboard.mimeData()

            if mimeData.hasUrls():
                print(mimeData.urls())
                file_path = mimeData.urls()[0].toLocalFile()
                self.processImageFromFile(file_path)
            elif mimeData.hasImage():
                self.processImage(clipboard.image())
            elif mimeData.hasText():
                text = mimeData.text()
                if os.path.isfile(text):
                    self.processImageFromFile(text)
                else:
                    QMessageBox.warning(self, "Error", "Clipboard content is not an image or valid file path")
            else:
                QMessageBox.warning(self, "Error", "No image or valid file path found in clipboard")

def main():
    app = QApplication(sys.argv)
    ex = ImageInverter()
    ex.show()
    sys.exit(app.exec())

if __name__ == '__main__':
	main()
