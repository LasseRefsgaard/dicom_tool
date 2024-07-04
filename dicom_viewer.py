import os
import sys
import pydicom
import numpy as np
from PyQt6.QtWidgets import (
    QApplication,
    QLabel,
    QMainWindow,
    QSlider,
    QVBoxLayout,
    QHBoxLayout,
    QWidget,
    QSizePolicy,
    QPushButton,
    QLabel,
)
from PyQt6.QtCore import Qt, QPoint, QRect
from PyQt6.QtGui import QPixmap, QImage, QPainter, QPen, QColor


class ImageLabel(QLabel):
    def __init__(self):
        super().__init__()
        self.points = {}  # Store points as {z: [(x, y), (x, y), ...], ...}
        self.boxes = {}  # Store boxes as {z: [(x1, y1, x2, y2), ...], ...}
        self.current_z = 0  # Current slice index
        self.drawing_mode = "points"  # Default drawing mode
        self.box_start = None
        self.box_end = None  # Store the current end position of the box while drawing

    def set_z(self, z):
        self.current_z = z
        self.update()  # Update the display when the slice changes

    def set_drawing_mode(self, mode):
        self.drawing_mode = mode

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            if self.drawing_mode == "points":
                self.draw_point(event.position().toPoint())
            elif self.drawing_mode == "box":
                self.start_box(event.position().toPoint())
            self.update()

    def draw_point(self, pos):
        if self.current_z not in self.points:
            self.points[self.current_z] = []
        self.points[self.current_z].append((pos.x(), pos.y()))

    def start_box(self, pos):
        self.box_start = pos
        self.box_end = pos

    def mouseMoveEvent(self, event):
        if self.drawing_mode == "box" and self.box_start:
            self.box_end = event.position().toPoint()
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.drawing_mode == "box":
            self.finish_box(event.position().toPoint())
            self.box_start = None
            self.box_end = None
            self.update()

    def finish_box(self, pos):
        if self.current_z not in self.boxes:
            self.boxes[self.current_z] = []
        x1, y1 = self.box_start.x(), self.box_start.y()
        x2, y2 = pos.x(), pos.y()
        # Ensure x1 < x2 and y1 < y2 for the box coordinates
        x1, x2 = min(x1, x2), max(x1, x2)
        y1, y2 = min(y1, y2), max(y1, y2)
        self.boxes[self.current_z].append((x1, y1, x2, y2))

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        pen = QPen(QColor(255, 0, 0), 5)
        painter.setPen(pen)
        if self.current_z in self.points:
            for point in self.points[self.current_z]:
                painter.drawPoint(QPoint(point[0], point[1]))

        pen_box = QPen(QColor(0, 255, 0), 2)
        painter.setPen(pen_box)
        if self.current_z in self.boxes:
            for box in self.boxes[self.current_z]:
                x1, y1, x2, y2 = box
                painter.drawRect(QRect(QPoint(x1, y1), QPoint(x2, y2)))

        # Draw the box being dragged
        if self.drawing_mode == "box" and self.box_start and self.box_end:
            painter.drawRect(QRect(self.box_start, self.box_end))

    def save_points_and_boxes(self):
        with open("points_and_boxes.txt", "w") as f:
            for z, points in self.points.items():
                for point in points:
                    f.write(f"Point, {z}, {point[0]}, {point[1]}\n")
            for z, boxes in self.boxes.items():
                for box in boxes:
                    f.write(f"Box, {z}, {box[0]}, {box[1]}, {box[2]}, {box[3]}\n")


class DicomViewer(QMainWindow):
    def __init__(self, folder_path):
        super().__init__()

        self.images_axial = self.load_dicom_images_from_folder(folder_path)
        self.current_index_axial = 0

        # Transpose for sagittal view
        self.images_sagittal = np.transpose(self.images_axial, (1, 0, 2))
        self.current_index_sagittal = 0

        # Transpose for coronal view
        self.images_coronal = np.transpose(self.images_axial, (2, 1, 0))
        self.current_index_coronal = 0

        self.initUI()

    def load_dicom_images_from_folder(self, folder_path):
        dicom_datasets = []
        for filename in os.listdir(folder_path):
            if filename.endswith(".dcm"):
                dicom_path = os.path.join(folder_path, filename)
                ds = pydicom.dcmread(dicom_path)
                dicom_datasets.append(ds)

        dicom_datasets.sort(key=lambda ds: ds.InstanceNumber)
        images_axial = [self.dicom_to_image(ds) for ds in dicom_datasets]
        return images_axial

    def dicom_to_image(self, ds):
        image = ds.pixel_array
        image = (
            (image - np.min(image)) / (np.max(image) - np.min(image)) * 255
        ).astype(np.uint8)
        return image

    def initUI(self):
        self.setWindowTitle("DICOM Viewer")

        # Axial view setup
        self.label_axial = ImageLabel()
        self.label_axial.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label_axial.setScaledContents(True)
        self.label_axial.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )

        self.slider_axial = QSlider(Qt.Orientation.Horizontal, self)
        self.slider_axial.setMinimum(0)
        self.slider_axial.setMaximum(len(self.images_axial) - 1)
        self.slider_axial.valueChanged.connect(self.slider_changed_axial)

        layout_axial = QVBoxLayout()
        layout_axial.addWidget(self.label_axial)
        layout_axial.addWidget(self.slider_axial)

        container_axial = QWidget()
        container_axial.setLayout(layout_axial)

        # Coordinates label
        self.coordinates_label = QLabel(self)
        self.coordinates_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.coordinates_label.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )

        # Save points button
        self.save_points_button = QPushButton("Save Points and Boxes", self)
        self.save_points_button.clicked.connect(self.save_points_and_boxes)

        # Draw points button
        self.draw_points_button = QPushButton("Draw Points", self)
        self.draw_points_button.clicked.connect(
            lambda: self.label_axial.set_drawing_mode("points")
        )

        # Draw box button
        self.draw_box_button = QPushButton("Draw Box", self)
        self.draw_box_button.clicked.connect(
            lambda: self.label_axial.set_drawing_mode("box")
        )

        # Controls layout (buttons)
        layout_controls = QHBoxLayout()
        layout_controls.addWidget(self.save_points_button)
        layout_controls.addWidget(self.draw_points_button)
        layout_controls.addWidget(self.draw_box_button)

        controls_widget = QWidget()
        controls_widget.setLayout(layout_controls)

        # Sagittal view setup
        self.label_sagittal = QLabel(self)
        self.label_sagittal.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label_sagittal.setScaledContents(True)
        self.label_sagittal.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )

        self.slider_sagittal = QSlider(Qt.Orientation.Horizontal, self)
        self.slider_sagittal.setMinimum(0)
        self.slider_sagittal.setMaximum(self.images_sagittal.shape[0] - 1)
        self.slider_sagittal.valueChanged.connect(self.slider_changed_sagittal)

        layout_sagittal = QVBoxLayout()
        layout_sagittal.addWidget(self.label_sagittal)
        layout_sagittal.addWidget(self.slider_sagittal)

        container_sagittal = QWidget()
        container_sagittal.setLayout(layout_sagittal)

        # Coronal view setup
        self.label_coronal = QLabel(self)
        self.label_coronal.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label_coronal.setScaledContents(True)
        self.label_coronal.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )

        self.slider_coronal = QSlider(Qt.Orientation.Horizontal, self)
        self.slider_coronal.setMinimum(0)
        self.slider_coronal.setMaximum(self.images_coronal.shape[0] - 1)
        self.slider_coronal.valueChanged.connect(self.slider_changed_coronal)

        layout_coronal = QVBoxLayout()
        layout_coronal.addWidget(self.label_coronal)
        layout_coronal.addWidget(self.slider_coronal)

        container_coronal = QWidget()
        container_coronal.setLayout(layout_coronal)

        # Main layout
        main_layout = QHBoxLayout()
        main_layout.addWidget(container_axial)
        main_layout.addWidget(container_sagittal)
        main_layout.addWidget(container_coronal)

        # Create a layout for the controls below the main layout
        layout_main = QVBoxLayout()
        layout_main.addLayout(main_layout)
        layout_main.addWidget(controls_widget)
        layout_main.addWidget(self.coordinates_label)

        main_widget = QWidget()
        main_widget.setLayout(layout_main)
        self.setCentralWidget(main_widget)

        # Initialize images
        self.update_image_axial()
        self.update_image_sagittal()
        self.update_image_coronal()

    def update_image_axial(self):
        image = self.images_axial[self.current_index_axial]
        height, width = image.shape[:2]

        qimage = QImage(
            image.data.tobytes(), width, height, QImage.Format.Format_Grayscale8
        )
        pixmap = QPixmap.fromImage(qimage)
        self.label_axial.setPixmap(pixmap)
        self.label_axial.set_z(self.current_index_axial)  # Set the current slice index

    def update_image_sagittal(self):
        image = self.images_sagittal[self.current_index_sagittal]
        height, width = image.shape[:2]

        qimage = QImage(
            image.data.tobytes(), width, height, QImage.Format.Format_Grayscale8
        )
        pixmap = QPixmap.fromImage(qimage)
        self.label_sagittal.setPixmap(pixmap)

    def update_image_coronal(self):
        image = self.images_coronal[self.current_index_coronal]
        height, width = image.shape[:2]

        qimage = QImage(
            image.data.tobytes(), width, height, QImage.Format.Format_Grayscale8
        )
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

    def save_points_and_boxes(self):
        self.label_axial.save_points_and_boxes()
        self.update_coordinates_label()

    def update_coordinates_label(self):
        coordinates_text = ""
        for z, points in self.label_axial.points.items():
            for point in points:
                coordinates_text += f"Z: {z}, X: {point[0]}, Y: {point[1]}\n"

        for z, boxes in self.label_axial.boxes.items():
            for box in boxes:
                coordinates_text += (
                    f"Z: {z} X1,Y1: ({box[0]}, {box[1]}) X2,Y2: ({box[2]}, {box[3]})\n"
                )

        self.coordinates_label.setText(coordinates_text)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Up:
            if self.current_index_axial < len(self.images_axial) - 1:
                self.current_index_axial += 1
                self.slider_axial.setValue(self.current_index_axial)
        elif event.key() == Qt.Key.Key_Down:
            if self.current_index_axial > 0:
                self.current_index_axial -= 1
                self.slider_axial.setValue(self.current_index_axial)

    def wheelEvent(self, event):
        if event.angleDelta().y() > 0:  # Scroll up
            if self.current_index_axial < len(self.images_axial) - 1:
                self.current_index_axial += 1
                self.slider_axial.setValue(self.current_index_axial)
        else:  # Scroll down
            if self.current_index_axial > 0:
                self.current_index_axial -= 1
                self.slider_axial.setValue(self.current_index_axial)


if __name__ == "__main__":
    app = QApplication(sys.argv)

    folder_path = "dicom/"  # Update this path to your DICOM folder
    viewer = DicomViewer(folder_path)
    viewer.show()

    sys.exit(app.exec())
