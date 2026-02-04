"""
Folder Card Delegate module for PyQt6 interface.

This module contains the FolderCardDelegate class which handles the
custom drawing of folder cards in the list view with buttons for
editing, toggling active state, deleting, and sending.
"""

from typing import TYPE_CHECKING, Dict, Any, Optional

from PyQt6.QtWidgets import (
    QStyledItemDelegate,
    QStyle,
    QStyleOptionButton,
    QStyleOptionViewItem,
    QApplication,
    QStylePainter,
)
from PyQt6.QtGui import QPainter, QPalette, QFontMetrics, QPen, QBrush, QColor
from PyQt6.QtCore import pyqtSignal as Signal, Qt, QRect, QPoint, QEvent, QSize

if TYPE_CHECKING:
    from PyQt6.QtWidgets import QAbstractItemView


class FolderCardDelegate(QStyledItemDelegate):
    """Custom delegate for drawing folder cards in a list view."""
    
    # Signals for button clicks
    edit_clicked = Signal(int)  # folder_id
    toggle_active_clicked = Signal(int)  # folder_id
    delete_clicked = Signal(int)  # folder_id
    send_clicked = Signal(int)  # folder_id
    
    def __init__(self, parent=None):
        """Initialize the delegate."""
        super().__init__(parent)
        
        # Button dimensions
        self.button_height = 24
        self.button_width = 60
        self.button_spacing = 4
        self.card_padding = 8
        
        # Define button areas for hit detection
        self.button_areas = {}
        
    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index):
        """Paint the folder card with alias and action buttons."""
        # Get folder data from model
        folder_data = index.data(Qt.ItemDataRole.UserRole)
        if not folder_data:
            return
            
        # Extract folder properties
        alias = folder_data.get('alias', 'Unknown')
        folder_id = folder_data.get('id')
        is_active = folder_data.get('folder_is_active', False)
        
        # Draw background based on selection state
        painter.save()
        
        # Background
        if option.state & QStyle.StateFlag.State_Selected:
            painter.fillRect(option.rect, option.palette.highlight())
            painter.setPen(option.palette.color(QPalette.ColorRole.HighlightedText))
        else:
            painter.fillRect(option.rect, option.palette.base())
            painter.setPen(option.palette.color(QPalette.ColorRole.Text))
        
        # Draw border
        pen = QPen(QColor(136, 136, 136), 1)
        painter.setPen(pen)
        painter.drawRoundedRect(option.rect.adjusted(0, 0, -1, -1), 4, 4)
        
        # Calculate areas for content
        content_rect = option.rect.adjusted(
            self.card_padding, 
            self.card_padding, 
            -self.card_padding, 
            -self.card_padding
        )
        
        # Clear button areas for this row and prepare for new ones
        if index.row() not in self.button_areas:
            self.button_areas[index.row()] = {}
        else:
            self.button_areas[index.row()].clear()
        
        # Draw alias text at the top
        alias_rect = QRect(
            content_rect.left(),
            content_rect.top(),
            content_rect.width(),
            content_rect.height() - self.button_height - self.button_spacing
        )
        
        # Draw alias text
        painter.drawText(
            alias_rect,
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop,
            alias
        )
        
        # Calculate button positions (left-aligned at bottom)
        button_texts = []
        if is_active:
            button_texts = ['Send', '<-', 'Edit...']
        else:
            button_texts = ['Edit...', 'Delete']
        
        # Calculate total button area width needed
        button_count = len(button_texts)
        total_button_width = (self.button_width * button_count) + (self.button_spacing * (button_count - 1))
        
        # Start position for buttons (left-aligned)
        button_start_x = content_rect.left()
        button_y = content_rect.bottom() - self.button_height
        
        # Draw buttons
        current_x = button_start_x
        for i, text in enumerate(button_texts):
            button_rect = QRect(
                current_x,
                button_y,
                self.button_width,
                self.button_height
            )
            
            # Store button area for hit detection
            self.button_areas[index.row()][i] = {
                'rect': button_rect,
                'type': 'send' if is_active and i == 0 else
                        'toggle' if is_active and i == 1 else
                        'edit' if (is_active and i == 2) or (not is_active and i == 0) else
                        'delete'
            }
            
            # Draw button
            self._draw_button(painter, button_rect, text, option)
            
            current_x += self.button_width + self.button_spacing
        
        painter.restore()
    
    def _draw_button(self, painter: QPainter, rect: QRect, text: str, option: QStyleOptionViewItem):
        """Draw a button with standard styling."""
        # Create style option for button
        button_opt = QStyleOptionButton()
        button_opt.rect = rect
        button_opt.text = text
        button_opt.state = option.state | QStyle.StateFlag.State_Enabled
        
        # Use application style to draw the button
        app_style = QApplication.style()
        app_style.drawControl(QStyle.ControlElement.CE_PushButton, button_opt, painter)
    
    def sizeHint(self, option: QStyleOptionViewItem, index):
        """Return the size hint for the item."""
        # Calculate the required size based on content
        folder_data = index.data(Qt.ItemDataRole.UserRole)
        if not folder_data:
            return super().sizeHint(option, index)
        
        alias = folder_data.get('alias', 'Unknown')
        font_metrics = QFontMetrics(option.font)
        
        # Calculate text size
        text_size = font_metrics.boundingRect(alias).size()
        
        # Calculate total height: text height + button height + padding
        total_height = text_size.height() + self.button_height + (self.card_padding * 2)
        
        # Width: max of text width or button area width
        min_width = max(
            text_size.width(),
            (self.button_width * 3) + (self.button_spacing * 2) + (self.card_padding * 2)
        )
        
        return QSize(min_width, total_height)
    
    def editorEvent(self, event, model, option, index):
        """Handle mouse events for button clicks."""
        if event.type() == QEvent.Type.MouseButtonRelease:
            pos = event.pos()
            
            # Check if the click was inside any button area
            if index.row() in self.button_areas:
                for btn_idx, btn_info in self.button_areas[index.row()].items():
                    if btn_info['rect'].contains(pos):
                        folder_data = index.data(Qt.ItemDataRole.UserRole)
                        if folder_data:
                            folder_id = folder_data.get('id')
                            
                            # Emit appropriate signal based on button type
                            if btn_info['type'] == 'send':
                                self.send_clicked.emit(folder_id)
                            elif btn_info['type'] == 'toggle':
                                self.toggle_active_clicked.emit(folder_id)
                            elif btn_info['type'] == 'edit':
                                self.edit_clicked.emit(folder_id)
                            elif btn_info['type'] == 'delete':
                                self.delete_clicked.emit(folder_id)
                                
                        return True  # Event handled
        
        return super().editorEvent(event, model, option, index)
    
