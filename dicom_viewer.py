import os
import sys
import pydicom
import numpy as np
from PyQt5.QtWidgets import (
    QApplication,
    QLabel,
    QMainWindow,
    QSlider,
    QVBoxLayout,
    QHBoxLayout,
    QWidget,
    QSizePolicy,
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap, QImage


class DicomViewer(QMainWindow):
    def __init__(self, folder_path):
        super().__init__()

        self.images_axial = self.load_dicom_images_from_folder(folder_path)
        self.current_index_axial = 0

        # Transpose for sagittal view
        self.images_sagittal = np.transpose(self.images_axial, (1, 0, 2))
        self.current_index_sagittal = 0

        # Transpose for coronal view
        self.images_coronal = np.transpose(
            self.images_axial, (2, 1, 0)
        )  # Adjusted transposition
        self.current_index_coronal = 0

        self.initUI()

    def load_dicom_images_from_folder(self, folder_path):
        dicom_datasets = []
        for filename in os.listdir(folder_path):
            if filename.endswith(".dcm"):
                dicom_path = os.path.join(folder_path, filename)
                ds = pydicom.dcmread(dicom_path)
                dicom_datasets.append(ds)

        dicom_datasets.sort(
            key=lambda ds: ds.InstanceNumber
        )  # Ensure the datasets are sorted correctly
        images_axial = [self.dicom_to_image(ds) for ds in dicom_datasets]
        return images_axial

    def dicom_to_image(self, ds):
        # Normalize pixel data to 8-bit unsigned integer
        image = ds.pixel_array
        image = (
            (image - np.min(image)) / (np.max(image) - np.min(image)) * 255
        ).astype(np.uint8)
        return image

    def initUI(self):
        self.setWindowTitle("DICOM Viewer")

        # Axial view setup
        self.label_axial = QLabel(self)
        self.label_axial.setAlignment(Qt.AlignCenter)  # Center align the image
        self.label_axial.setScaledContents(True)  # Scale contents to fit label
        self.label_axial.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Expanding
        )  # Expanding size policy

        self.slider_axial = QSlider(Qt.Horizontal, self)
        self.slider_axial.setMinimum(0)
        self.slider_axial.setMaximum(len(self.images_axial) - 1)
        self.slider_axial.valueChanged.connect(self.slider_changed_axial)

        layout_axial = QVBoxLayout()
        layout_axial.addWidget(self.label_axial)
        layout_axial.addWidget(self.slider_axial)

        container_axial = QWidget()
        container_axial.setLayout(layout_axial)

        # Sagittal view setup
        self.label_sagittal = QLabel(self)
        self.label_sagittal.setAlignment(Qt.AlignCenter)  # Center align the image
        self.label_sagittal.setScaledContents(True)  # Scale contents to fit label
        self.label_sagittal.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Expanding
        )  # Expanding size policy

        self.slider_sagittal = QSlider(Qt.Horizontal, self)  # Horizontal scrollbar
        self.slider_sagittal.setMinimum(0)
        self.slider_sagittal.setMaximum(self.images_sagittal.shape[0] - 1)
        self.slider_sagittal.valueChanged.connect(self.slider_changed_sagittal)

        layout_sagittal = QVBoxLayout()  # Use QVBoxLayout for vertical layout
        layout_sagittal.addWidget(self.label_sagittal)
        layout_sagittal.addWidget(self.slider_sagittal)

        container_sagittal = QWidget()
        container_sagittal.setLayout(layout_sagittal)

        # Coronal view setup
        self.label_coronal = QLabel(self)
        self.label_coronal.setAlignment(Qt.AlignCenter)  # Center align the image
        self.label_coronal.setScaledContents(True)  # Scale contents to fit label
        self.label_coronal.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Expanding
        )  # Expanding size policy

        self.slider_coronal = QSlider(Qt.Horizontal, self)  # Horizontal scrollbar
        self.slider_coronal.setMinimum(0)
        self.slider_coronal.setMaximum(self.images_coronal.shape[0] - 1)
        self.slider_coronal.valueChanged.connect(self.slider_changed_coronal)

        layout_coronal = QVBoxLayout()  # Use QVBoxLayout for vertical layout
        layout_coronal.addWidget(self.label_coronal)
        layout_coronal.addWidget(self.slider_coronal)

        container_coronal = QWidget()
        container_coronal.setLayout(layout_coronal)

        # Main layout
        main_layout = QHBoxLayout()  # Use QHBoxLayout for horizontal layout
        main_layout.addWidget(container_axial)
        main_layout.addWidget(container_sagittal)
        main_layout.addWidget(container_coronal)

        main_widget = QWidget()
        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)

        # Initialize images
        self.update_image_axial()
        self.update_image_sagittal()
        self.update_image_coronal()

    def update_image_axial(self):
        image = self.images_axial[self.current_index_axial]
        height, width = image.shape[:2]  # Get height and width from image shape

        # Convert grayscale numpy array to QImage
        qimage = QImage(image.data.tobytes(), width, height, QImage.Format_Grayscale8)
        pixmap = QPixmap.fromImage(qimage)
        self.label_axial.setPixmap(pixmap)

    def update_image_sagittal(self):
        image = self.images_sagittal[self.current_index_sagittal]
        height, width = image.shape[:2]  # Get height and width from image shape

        # Convert grayscale numpy array to QImage
        qimage = QImage(image.data.tobytes(), width, height, QImage.Format_Grayscale8)
        pixmap = QPixmap.fromImage(qimage)
        self.label_sagittal.setPixmap(pixmap)

    def update_image_coronal(self):
        image = self.images_coronal[self.current_index_coronal]
        height, width = image.shape[:2]  # Get height and width from image shape

        # Convert grayscale numpy array to QImage
        qimage = QImage(image.data.tobytes(), width, height, QImage.Format_Grayscale8)
        pixmap = QPixmap.fromImage(qimage)
        self.label_coronal.setPixmap(pixmap)

    def slider_changed_axial(self, value):
        self.current_index_axial = value
        self.update_image_axial()

    def slider_changed_sagittal(self, value):
        self.current_index_sagittal = value
        self.update_image_sagittal()

    def slider_changed_coronal(self, value):
        self.current_index_coronal = value
        self.update_image_coronal()


if __name__ == "__main__":
    app = QApplication(sys.argv)

    folder_path = "C:/Users/LASREF/Downloads/ContouringWorkshopCase1/ContouringWorkshopCase1/"  # Update this path to your DICOM folder
    viewer = DicomViewer(folder_path)
    viewer.show()

    sys.exit(app.exec_())
