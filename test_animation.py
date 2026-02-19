#!/usr/bin/env python3
"""Test script to verify the QPropertyAnimation works with custom property"""

import sys
from PyQt6.QtWidgets import QApplication, QWidget, QLabel, QVBoxLayout
from PyQt6.QtCore import QPropertyAnimation, QEasingCurve, pyqtProperty
from PyQt6.QtGui import QTransform

class RotatableLabel(QLabel):
    """A QLabel that supports rotation animation"""
    
    def __init__(self, text: str = "", parent=None):
        super().__init__(text, parent)
        self._rotation = 0
    
    @pyqtProperty(int)
    def rotation(self):
        """Rotation property for animation"""
        return self._rotation
    
    @rotation.setter
    def rotation(self, value):
        """Setter for rotation property"""
        self._rotation = value % 360
        transform = QTransform().rotate(self._rotation)
        self.setTransform(transform)


class TestWindow(QWidget):
    """Test window to display the animated label"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Rotation Animation Test")
        self.setGeometry(100, 100, 400, 300)
        
        # Create layout
        layout = QVBoxLayout(self)
        
        # Create rotatable label
        self.label = RotatableLabel("◐")
        self.label.setStyleSheet("font-size: 48pt;")
        layout.addWidget(self.label)
        
        # Create animation
        self.animation = QPropertyAnimation(self.label, b"rotation")
        self.animation.setDuration(1000)  # 1 second per rotation
        self.animation.setStartValue(0)
        self.animation.setEndValue(360)
        self.animation.setEasingCurve(QEasingCurve.Type.Linear)
        self.animation.setLoopCount(-1)  # Infinite loop
        self.animation.start()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = TestWindow()
    window.show()
    print("Animation test window is showing. Close the window to exit.")
    sys.exit(app.exec())
