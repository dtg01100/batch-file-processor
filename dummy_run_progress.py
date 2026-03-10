#!/usr/bin/env python3
"""
dummy_run_progress.py - Comprehensive demonstration of QtProgressService features.

This script demonstrates all progress tracking capabilities:
- Percentage-based progress (0-100%)
- Indeterminate progress (throbber mode)
- Detailed progress tracking with folders/files
- Message updates
- Show/hide functionality
- Error handling

Run independently to test the progress overlay.
"""

import sys
from typing import Optional

from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QWidget,
    QLabel,
    QTextEdit,
)

from interface.qt.services.qt_services import QtProgressService
from interface.qt.theme import Theme


class ProgressDemoWindow(QMainWindow):
    """Main window for demonstrating progress tracking features."""
    
    def __init__(self) -> None:
        super().__init__()
        self.progress_service: Optional[QtProgressService] = None
        self.demo_timer: Optional[QTimer] = None
        self.current_demo_step = 0
        self.init_ui()
        
    def init_ui(self) -> None:
        """Initialize the user interface."""
        self.setWindowTitle("QtProgressService Demo")
        self.setGeometry(100, 100, 600, 500)
        
        # Apply theme stylesheet
        Theme.apply_theme(self)
        
        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Title label
        title = QLabel("Progress Overlay Demonstration")
        title.setProperty("heading", True)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # Description
        desc = QLabel(
            "Click the button below to start a comprehensive demo\n"
            "showing all progress tracking features."
        )
        desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc.setWordWrap(True)
        layout.addWidget(desc)
        
        # Start demo button
        self.demo_button = QPushButton("Start Demo")
        self.demo_button.setProperty("class", "primary")
        self.demo_button.clicked.connect(self.start_demo)
        layout.addWidget(self.demo_button)
        
        # Status log
        self.log = QTextEdit()
        self.log.setReadOnly(True)
        layout.addWidget(QLabel("Demo Log:"))
        layout.addWidget(self.log)
        
        # Spacer
        layout.addStretch()
        
    def log_message(self, message: str) -> None:
        """Add a message to the log."""
        self.log.append(f"[{QTimer.singleShot(0, lambda: None) or '--:--:--'}] {message}")
        # Actually we need to use time module for timestamp
        from datetime import datetime
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log.append(f"[{timestamp}] {message}")
        
    def start_demo(self) -> None:
        """Start the demonstration sequence."""
        self.demo_button.setEnabled(False)
        self.log.clear()
        self.current_demo_step = 0
        
        # Initialize progress service
        try:
            self.progress_service = QtProgressService(self)
            self.log_message("✓ QtProgressService initialized")
        except Exception as e:
            self.log_message(f"✗ Failed to initialize: {e}")
            self.demo_button.setEnabled(True)
            return
            
        # Start the demo sequence with a timer
        if not self.demo_timer:
            self.demo_timer = QTimer()
            self.demo_timer.timeout.connect(self.next_demo_step)
        self.demo_timer.start(1500)  # 1.5 seconds between steps
        
    def next_demo_step(self) -> None:
        """Execute the next step in the demonstration."""
        if self.progress_service is None:
            return
            
        step_handlers = [
            self.demo_show_overlay,
            self.demo_percentage_progress,
            self.demo_message_updates,
            self.demo_detailed_progress,
            self.demo_indeterminate_mode,
            self.demo_combined_features,
            self.demo_hide_overlay,
            self.demo_show_hide_toggle,
            self.demo_cleanup,
        ]
        
        if self.current_demo_step < len(step_handlers):
            step_handlers[self.current_demo_step]()
            self.current_demo_step += 1
        else:
            if self.demo_timer:
                self.demo_timer.stop()
            self.demo_button.setEnabled(True)
            self.log_message("✓ Demo completed successfully")
            
    def demo_show_overlay(self) -> None:
        """Demonstrate: Show the progress overlay."""
        try:
            if self.progress_service:
                # Update the theme styling to make the overlay more visible
                # First, try to access the overlay's styling
                self.progress_service.show("Initializing...")
                
                # Apply more visible styling to make the overlay clearly visible
                if hasattr(self.progress_service, 'progress_dialog'):
                    # Increase visibility with stronger colors and borders
                    style_override = """
                        QFrame#qt_progress_overlay {
                            background-color: rgba(0, 0, 0, 200); /* Darker background */
                            border: 3px solid #FF5722; /* Bright orange border */
                            border-radius: 15px;
                        }
                        QLabel {
                            color: white;
                            font-size: 18px;
                            font-weight: bold;
                        }
                        QProgressBar {
                            border: 3px solid #FF5722; /* Bright orange border */
                            border-radius: 8px;
                            text-align: center;
                            color: white;
                            font-weight: bold;
                            background-color: rgba(0, 0, 0, 100);
                        }
                        QProgressBar::chunk {
                            background-color: #FF5722; /* Bright orange progress */
                            width: 20px;
                            border-radius: 5px;
                        }
                        QLabel[objectName="throbber_label"] {
                            color: #FF5722;
                            font-size: 40pt;
                        }
                    """
                    self.progress_service.progress_dialog.setStyleSheet(style_override)
                
                self.log_message("✓ Progress overlay shown with message: 'Initializing...'")
                self.log_message("✓ Overlay styling updated for better visibility")
        except Exception as e:
            self.log_message(f"✗ Failed to show overlay: {e}")
            
    def demo_percentage_progress(self) -> None:
        """Demonstrate: Percentage-based progress (0-100%)."""
        try:
            if self.progress_service:
                # Start with throbber then switch to percentage
                self.progress_service.set_indeterminate()
                QApplication.processEvents()
                QTimer.singleShot(300, lambda: None)  # Small delay
                
                self.progress_service.update_progress(0)
                self.log_message("✓ Switched to percentage mode (0%)")
                
                # Animate from 0 to 100%
                for i in range(0, 101, 20):
                    if self.progress_service:
                        self.progress_service.update_progress(i)
                        self.log_message(f"  Progress: {i}%")
                        QTimer.singleShot(400, lambda: None)  # Small delay
                        QApplication.processEvents()
                        
                self.log_message("✓ Percentage progress complete (100%)")
        except Exception as e:
            self.log_message(f"✗ Percentage progress failed: {e}")
            
    def demo_message_updates(self) -> None:
        """Demonstrate: Dynamic message updates."""
        try:
            if self.progress_service:
                messages = [
                    "Processing batch files...",
                    "Validating data integrity...",
                    "Transforming records...",
                    "Finalizing output..."
                ]
                
                for msg in messages:
                    self.progress_service.update_message(msg)
                    self.log_message(f"✓ Message updated: '{msg}'")
                    QTimer.singleShot(800, lambda: None)
                    QApplication.processEvents()
                    
                self.log_message("✓ Message updates demonstrated")
        except Exception as e:
            self.log_message(f"✗ Message updates failed: {e}")
            
    def demo_detailed_progress(self) -> None:
        """Demonstrate: Detailed progress tracking with folders/files."""
        try:
            if self.progress_service:
                self.progress_service.update_progress(30)
                self.progress_service.update_detailed_progress(
                    folder_num=1,
                    folder_total=3,
                    file_num=5,
                    file_total=25,
                    footer="Batch processing in progress"
                )
                self.log_message("✓ Detailed progress: Folder 1/3, File 5/25")
                QTimer.singleShot(1000, lambda: None)
                QApplication.processEvents()
                
                self.progress_service.update_detailed_progress(
                    folder_num=2,
                    folder_total=3,
                    file_num=12,
                    file_total=25,
                    footer="Validating data..."
                )
                self.log_message("✓ Detailed progress: Folder 2/3, File 12/25")
                QTimer.singleShot(1000, lambda: None)
                QApplication.processEvents()
                
                self.progress_service.update_detailed_progress(
                    folder_num=3,
                    folder_total=3,
                    file_num=25,
                    file_total=25,
                    footer="Completing final checks"
                )
                self.log_message("✓ Detailed progress: Folder 3/3, File 25/25")
                QTimer.singleShot(1000, lambda: None)
                QApplication.processEvents()
                
        except Exception as e:
            self.log_message(f"✗ Detailed progress failed: {e}")
            
    def demo_indeterminate_mode(self) -> None:
        """Demonstrate: Indeterminate progress (throbber mode)."""
        try:
            if self.progress_service:
                self.progress_service.set_indeterminate()
                self.progress_service.update_message("Processing (unknown duration) - NOTICE THE THROBBER!")
                
                # Update styling to make throbber more visible
                if hasattr(self.progress_service, 'progress_dialog'):
                    style_override = """
                        QFrame#qt_progress_overlay {
                            background-color: rgba(0, 0, 0, 200); /* Darker background */
                            border: 3px solid #FF5722; /* Bright orange border */
                            border-radius: 15px;
                        }
                        QLabel {
                            color: white;
                            font-size: 18px;
                            font-weight: bold;
                        }
                        QProgressBar {
                            border: 3px solid #FF5722; /* Bright orange border */
                            border-radius: 8px;
                            text-align: center;
                            color: white;
                            font-weight: bold;
                            background-color: rgba(0, 0, 0, 100);
                        }
                        QProgressBar::chunk {
                            background-color: #FF5722; /* Bright orange progress */
                            width: 20px;
                            border-radius: 5px;
                        }
                        QLabel {
                            color: #FF5722;
                            font-size: 40pt;
                            font-weight: bold;
                        }
                    """
                    self.progress_service.progress_dialog.setStyleSheet(style_override)
                
                self.log_message("✓ Switched to indeterminate mode (throbber visible)")
                
                # Simulate work with unknown duration
                QTimer.singleShot(2000, lambda: None)
                QApplication.processEvents()
                
                self.log_message("✓ Indeterminate mode complete")
        except Exception as e:
            self.log_message(f"✗ Indeterminate mode failed: {e}")
            
    def demo_combined_features(self) -> None:
        """Demonstrate: Combining multiple features together."""
        try:
            if self.progress_service:
                # Show overlay with message (auto-shows if not visible)
                self.progress_service.update_message("FINAL BATCH PROCESSING - NOTICE THE VISIBILITY!")
                
                # Update styling to ensure visibility
                if hasattr(self.progress_service, 'progress_dialog'):
                    style_override = """
                        QFrame#qt_progress_overlay {
                            background-color: rgba(0, 0, 0, 220); /* Even darker background */
                            border: 4px solid #9C27B0; /* Purple border */
                            border-radius: 20px;
                        }
                        QLabel {
                            color: white;
                            font-size: 20px;
                            font-weight: bold;
                        }
                        QProgressBar {
                            border: 4px solid #9C27B0; /* Purple border */
                            border-radius: 10px;
                            text-align: center;
                            color: white;
                            font-weight: bold;
                            font-size: 14px;
                            background-color: rgba(0, 0, 0, 120);
                        }
                        QProgressBar::chunk {
                            background-color: #9C27B0; /* Purple progress */
                            width: 20px;
                            border-radius: 7px;
                        }
                    """
                    self.progress_service.progress_dialog.setStyleSheet(style_override)
                
                self.log_message("✓ Combined: message + progress")
                
                # Update progress and details together
                self.progress_service.update_progress(75)
                self.progress_service.update_detailed_progress(
                    folder_num=5,
                    folder_total=6,
                    file_num=45,
                    file_total=50,
                    footer="Final demo step - VISIBLY CLEAR!"
                )
                self.log_message("✓ Combined: progress + detailed info")
                QTimer.singleShot(1500, lambda: None)
                QApplication.processEvents()
                
        except Exception as e:
            self.log_message(f"✗ Combined features failed: {e}")
            
    def demo_hide_overlay(self) -> None:
        """Demonstrate: Hide the progress overlay."""
        try:
            if self.progress_service:
                self.progress_service.hide()
                self.log_message("✓ Progress overlay hidden")
                QTimer.singleShot(800, lambda: None)
                QApplication.processEvents()
        except Exception as e:
            self.log_message(f"✗ Hide failed: {e}")
            
    def demo_show_hide_toggle(self) -> None:
        """Demonstrate: Show/hide toggle functionality."""
        try:
            self.log_message("Demonstrating show/hide toggle (3 iterations)...")
            
            for i in range(3):
                if self.progress_service:
                    self.progress_service.show(f"Toggle iteration {i+1}/3")
                    self.log_message(f"  Shown (iteration {i+1})")
                    QTimer.singleShot(800, lambda: None)
                    QApplication.processEvents()
                    
                    self.progress_service.hide()
                    self.log_message(f"  Hidden (iteration {i+1})")
                    QTimer.singleShot(600, lambda: None)
                    QApplication.processEvents()
                    
            self.log_message("✓ Show/hide toggle complete")
        except Exception as e:
            self.log_message(f"✗ Toggle failed: {e}")
            
    def demo_cleanup(self) -> None:
        """Clean up after demo completion."""
        try:
            if self.progress_service:
                # Final hide to ensure overlay is closed
                self.progress_service.hide()
                self.log_message("✓ Cleanup: overlay hidden")
        except Exception as e:
            self.log_message(f"✗ Cleanup failed: {e}")


def main() -> int:
    """Main entry point with proper error handling."""
    try:
        # Create QApplication
        app = QApplication(sys.argv)
        
        # Apply theme
        app.setStyleSheet(Theme.get_stylesheet())
        
        # Create and show main window
        window = ProgressDemoWindow()
        window.show()
        
        # Run application event loop
        return app.exec()
        
    except ImportError as e:
        print(f"ERROR: Missing required PyQt6 modules: {e}")
        print("Install with: pip install PyQt6")
        return 1
        
    except Exception as e:
        print(f"ERROR: Unexpected error during startup: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
