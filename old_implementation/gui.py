"""
Clean GUI for MVR File Analyzer
Pure UI logic using controller architecture.
"""

import sys
import os
from pathlib import Path
from typing import List, Optional, Dict, Any

# PyQt6 imports
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QFileDialog, QTextEdit, QCheckBox,
    QGroupBox, QScrollArea, QComboBox, QProgressBar, QMessageBox,
    QFrame, QGridLayout, QDialog, QMenuBar, QMenu, QRadioButton,
    QButtonGroup, QTableWidget, QTableWidgetItem, QHeaderView,
    QTreeWidget, QTreeWidgetItem, QTabWidget, QTableView, QAbstractItemView,
    QStyledItemDelegate, QStyle, QStyleOptionViewItem, QProxyStyle,
    QSplitter
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QSettings, QMimeData, QAbstractItemModel, QModelIndex
from PyQt6.QtGui import QFont, QAction, QColor, QDrag, QPixmap, QStandardItemModel, QStandardItem

# Import our clean architecture
from config import Config
from controllers.main_controller import MVRController
from views.gdtf_matching_dialog import GDTFMatchingDialog
from views.fixture_attribute_dialog import FixtureAttributeDialog
from views.ma3_xml_dialog import MA3XMLDialog
from views.csv_import_dialog import CSVImportDialog
from views.mvr_import_dialog import MVRImportDialog
from views.settings_dialog import SettingsDialog


class DragDropIndicator(QWidget):
    """Visual indicator for drag and drop operations."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(2)
        self.setStyleSheet("background-color: #0078d4; border-radius: 1px;")
        self.hide()

class DragDropItemModel(QStandardItemModel):
    """Custom model that handles drag and drop properly."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setColumnCount(6)  # ID, Name, Type, Mode, Address, Routing
        self.setHorizontalHeaderLabels([
            "Fixture ID", "Name", "Type", "Mode", "Base Address", "Routing"
        ])
    
    def supportedDropActions(self):
        return Qt.DropAction.MoveAction
    
    def flags(self, index):
        default_flags = super().flags(index)
        if index.isValid():
            # Make routing column (column 5) read-only but still draggable
            if index.column() == 5:
                return default_flags & ~Qt.ItemFlag.ItemIsEditable
            return default_flags | Qt.ItemFlag.ItemIsDragEnabled | Qt.ItemFlag.ItemIsDropEnabled
        return default_flags | Qt.ItemFlag.ItemIsDropEnabled
    
    def dropMimeData(self, data, action, row, column, parent):
        """Handle drop operations - always drop entire rows."""
        if action == Qt.DropAction.IgnoreAction:
            return True
        
        # Always insert rows, never replace cells
        return super().dropMimeData(data, action, row, 0, parent)
    
    def mimeTypes(self):
        return ["application/x-qabstractitemmodeldatalist"]

class DraggableTableView(QTableView):
    """Custom QTableView with enhanced drag and drop functionality including multi-row selection.
    
    Features:
    - Multi-row selection using Ctrl+Click, Shift+Click, or click-and-drag
    - Drag and drop multiple selected rows while maintaining their relative order
    - Keyboard shortcuts: Ctrl+A (select all), Delete (delete selected rows)
    - Context menu with operations for single or multiple rows
    - Visual feedback during drag operations showing number of rows being moved
    - Backward compatibility with single-row operations
    
    Signals:
    - rowMoved(int, int): Emitted for single row moves (backward compatibility)
    - rowsMoved(list, int): Emitted for multi-row moves with selected_rows and target_row
    - rowInserted(int): Emitted when a row is inserted
    - rowDeleted(int): Emitted when a row is deleted
    """
    
    rowMoved = pyqtSignal(int, int)  # from_row, to_row (for single row - backward compatibility)
    rowsMoved = pyqtSignal(list, int)  # selected_rows, target_row (for multi-row moves)
    rowInserted = pyqtSignal(int)    # row_index
    rowDeleted = pyqtSignal(int)     # row_index
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_drag_drop()
        self.setup_context_menu()
        
        # Visual feedback for drag operations
        self.drag_indicator = DragDropIndicator(self)
        self.drag_start_rows = []  # List of selected rows being dragged
        
    def setup_drag_drop(self):
        """Configure drag and drop settings."""
        self.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.setDragDropOverwriteMode(False)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)  # Enable multi-selection
        
    def setup_context_menu(self):
        """Setup context menu for row operations."""
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)
    
    def get_selected_rows(self):
        """Get a sorted list of currently selected row indices."""
        selected_rows = []
        for index in self.selectedIndexes():
            row = index.row()
            if row not in selected_rows:
                selected_rows.append(row)
        return sorted(selected_rows)
    
    def startDrag(self, supportedActions):
        """Start drag operation with visual feedback for single or multiple rows."""
        selected_indexes = self.selectedIndexes()
        if not selected_indexes:
            return
        
        # Get all selected rows
        self.drag_start_rows = self.get_selected_rows()
        if not self.drag_start_rows:
            return
            
        # Create drag object
        drag = QDrag(self)
        
        # Create mime data for all selected rows
        mime_data = self.model().mimeData(selected_indexes)
        drag.setMimeData(mime_data)
        
        # Create visual representation
        pixmap = self.create_drag_pixmap()
        drag.setPixmap(pixmap)
        
        # Execute drag
        result = drag.exec(Qt.DropAction.MoveAction)
        
        # Clean up
        self.drag_start_rows = []
        self.drag_indicator.hide()
    
    def create_drag_pixmap(self):
        """Create a visual representation of the dragged rows."""
        if not self.drag_start_rows:
            return QPixmap()
        
        from PyQt6.QtGui import QPainter, QColor, QFont
        
        try:
            # Calculate dimensions for multi-row pixmap
            if len(self.drag_start_rows) == 1:
                # Single row - use original height
                first_index = self.model().index(self.drag_start_rows[0], 0)
                first_rect = self.visualRect(first_index)
                pixmap_height = first_rect.height()
            else:
                # Multiple rows - use condensed representation
                single_row_height = 20  # Condensed height per row
                pixmap_height = min(len(self.drag_start_rows) * single_row_height + 10, 120)  # Cap at 120px
            
            pixmap_width = min(self.width(), 300)  # Cap width at 300px
            
            # Create pixmap
            pixmap = QPixmap(pixmap_width, pixmap_height)
            pixmap.fill(QColor(100, 100, 100, 180))  # Semi-transparent gray
            
            # Create painter for styling
            painter = QPainter(pixmap)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            
            # Draw border
            painter.setPen(QColor(50, 50, 50))
            painter.drawRect(pixmap.rect().adjusted(0, 0, -1, -1))
            
            # Add text indicating number of rows
            if len(self.drag_start_rows) > 1:
                painter.setPen(QColor(255, 255, 255))
                font = QFont()
                font.setBold(True)
                painter.setFont(font)
                text = f"{len(self.drag_start_rows)} rows"
                painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, text)
            
            painter.end()
            
            # Set device pixel ratio for high-resolution screens
            pixmap.setDevicePixelRatio(self.devicePixelRatio())
            
            return pixmap
            
        except Exception as e:
            # Fallback: return a simple pixmap if rendering fails
            pixmap = QPixmap(100, 30)
            pixmap.fill(QColor(100, 100, 100, 180))
            return pixmap
    
    def dragEnterEvent(self, event):
        """Handle drag enter events."""
        if event.source() == self:
            event.acceptProposedAction()
            self.drag_indicator.show()
        else:
            event.ignore()
    
    def dragMoveEvent(self, event):
        """Handle drag move events with visual feedback."""
        if event.source() != self:
            event.ignore()
            return
            
        # Calculate drop position
        pos = event.position().toPoint()
        index = self.indexAt(pos)
        
        if index.isValid():
            row = index.row()
            rect = self.visualRect(index)
            
            # Determine if we're in the top or bottom half
            if pos.y() < rect.center().y():
                # Insert above this row
                insert_row = row
            else:
                # Insert below this row
                insert_row = row + 1
        else:
            # Drop at the end
            insert_row = self.model().rowCount()
        
        # Position the drop indicator
        self.position_drop_indicator(insert_row)
        
        event.acceptProposedAction()
    
    def dragLeaveEvent(self, event):
        """Handle drag leave events."""
        self.drag_indicator.hide()
        event.accept()
    
    def dropEvent(self, event):
        """Handle drop events for single or multiple rows."""
        if event.source() != self:
            event.ignore()
            return
            
        # Hide the indicator
        self.drag_indicator.hide()
        
        # Get drop position
        pos = event.position().toPoint()
        target_index = self.indexAt(pos)
        
        if target_index.isValid():
            target_row = target_index.row()
            rect = self.visualRect(target_index)
            
            # Determine insertion point
            if pos.y() >= rect.center().y():
                target_row += 1
        else:
            target_row = self.model().rowCount()
        
        # Handle multiple row selection
        if len(self.drag_start_rows) > 1:
            # Don't drop on any of the selected rows or immediately after the last one
            if target_row in self.drag_start_rows or target_row == max(self.drag_start_rows) + 1:
                event.ignore()
                return
                
            # Perform multi-row move
            if self.perform_multi_row_move(self.drag_start_rows, target_row):
                event.acceptProposedAction()
                self.rowsMoved.emit(self.drag_start_rows, target_row)
            else:
                event.ignore()
        else:
            # Single row handling (backward compatibility)
            single_row = self.drag_start_rows[0] if self.drag_start_rows else -1
            
            # Don't drop on the same position
            if target_row == single_row or target_row == single_row + 1:
                event.ignore()
                return
                
            # Perform single row move
            if self.perform_row_move(single_row, target_row):
                event.acceptProposedAction()
                self.rowMoved.emit(single_row, target_row)  # Emit old signal for compatibility
                self.rowsMoved.emit([single_row], target_row)  # Also emit new signal
            else:
                event.ignore()
    
    def position_drop_indicator(self, row):
        """Position the visual drop indicator."""
        if row >= self.model().rowCount():
            # Position at the end
            if self.model().rowCount() > 0:
                last_index = self.model().index(self.model().rowCount() - 1, 0)
                last_rect = self.visualRect(last_index)
                y = last_rect.bottom()
            else:
                y = 0
        else:
            # Position above the target row
            index = self.model().index(row, 0)
            rect = self.visualRect(index)
            y = rect.top()
        
        # Set indicator position
        self.drag_indicator.setGeometry(0, y, self.width(), 2)
        self.drag_indicator.show()
    
    def perform_multi_row_move(self, source_rows, target_row):
        """Perform the actual multi-row move operation while maintaining relative order."""
        if not source_rows or target_row in source_rows:
            return False
        
        model = self.model()
        
        # Store all row data first
        rows_data = []
        for row in sorted(source_rows, reverse=True):  # Process in reverse order to maintain indices
            row_items = []
            for col in range(model.columnCount()):
                item = model.takeItem(row, col)
                row_items.append(item)
            rows_data.append(row_items)
            model.removeRow(row)
        
        # Reverse the data to maintain original order
        rows_data.reverse()
        
        # Adjust target position based on how many rows were removed before it
        adjusted_target = target_row
        for row in source_rows:
            if row < target_row:
                adjusted_target -= 1
        
        # Insert all rows at the target position
        for i, row_items in enumerate(rows_data):
            insert_position = adjusted_target + i
            model.insertRow(insert_position)
            
            # Place items in the new row
            for col, item in enumerate(row_items):
                if item is not None:
                    # Special handling for routing column (column 5 or 8 depending on table)
                    if col in [5, 8]:  # Both possible routing columns
                        item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                    model.setItem(insert_position, col, item)
                else:
                    # Create empty item if none existed
                    new_item = QStandardItem("")
                    if col in [5, 8]:  # Routing columns
                        new_item.setFlags(new_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                    model.setItem(insert_position, col, new_item)
        
        # Select the moved rows at their new positions
        selection_model = self.selectionModel()
        selection_model.clearSelection()
        for i in range(len(rows_data)):
            new_row = adjusted_target + i
            selection_model.select(
                model.index(new_row, 0),
                selection_model.SelectionFlag.Select | selection_model.SelectionFlag.Rows
            )
        
        return True
    
    def show_context_menu(self, position):
        """Show context menu with row operations for single or multiple rows."""
        if not self.indexAt(position).isValid():
            return
        
        selected_rows = self.get_selected_rows()
        menu = QMenu(self)
        
        if len(selected_rows) <= 1:
            # Single row operations
            insert_above_action = menu.addAction("Insert Empty Row Above")
            insert_below_action = menu.addAction("Insert Empty Row Below")
            menu.addSeparator()
            delete_row_action = menu.addAction("Delete Row")
            
            # Connect actions
            insert_above_action.triggered.connect(self.insert_empty_row_above)
            insert_below_action.triggered.connect(self.insert_empty_row_below)
            delete_row_action.triggered.connect(self.delete_current_row)
        else:
            # Multi-row operations
            menu.addAction(f"Selected: {len(selected_rows)} rows").setEnabled(False)
            menu.addSeparator()
            
            insert_above_action = menu.addAction("Insert Empty Row Above Selection")
            insert_below_action = menu.addAction("Insert Empty Row Below Selection")
            menu.addSeparator()
            delete_rows_action = menu.addAction(f"Delete {len(selected_rows)} Selected Rows")
            
            # Connect actions for multi-row operations
            insert_above_action.triggered.connect(lambda: self.insert_empty_row_at(min(selected_rows)))
            insert_below_action.triggered.connect(lambda: self.insert_empty_row_at(max(selected_rows) + 1))
            delete_rows_action.triggered.connect(self.delete_selected_rows)
        
        # Show menu
        menu.exec(self.mapToGlobal(position))
    
    def delete_selected_rows(self):
        """Delete all currently selected rows."""
        selected_rows = self.get_selected_rows()
        if not selected_rows:
            return
        
        # Remove rows in reverse order to maintain correct indices
        for row in sorted(selected_rows, reverse=True):
            self.model().removeRow(row)
            self.rowDeleted.emit(row)
    
    def insert_empty_row_above(self):
        """Insert an empty row above the current selection."""
        current_row = self.currentIndex().row()
        if current_row >= 0:
            self.insert_empty_row_at(current_row)
            self.selectRow(current_row)
    
    def insert_empty_row_below(self):
        """Insert an empty row below the current selection."""
        current_row = self.currentIndex().row()
        if current_row >= 0:
            insert_row = current_row + 1
            self.insert_empty_row_at(insert_row)
            self.selectRow(insert_row)
    
    def insert_empty_row_at(self, row):
        """Insert an empty row at the specified position."""
        model = self.model()
        model.insertRow(row)
        
        # Initialize the row with empty items
        for col in range(model.columnCount()):
            item = QStandardItem("")
            if col == 5:  # Routing column
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            model.setItem(row, col, item)
        
        self.rowInserted.emit(row)
    
    def delete_current_row(self):
        """Delete the currently selected row."""
        current_row = self.currentIndex().row()
        if current_row >= 0:
            self.model().removeRow(current_row)
            self.rowDeleted.emit(current_row)
    
    def keyPressEvent(self, event):
        """Handle keyboard events for enhanced multi-selection."""
        if event.key() == Qt.Key.Key_A and event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            # Ctrl+A - select all rows
            self.selectAll()
            event.accept()
            return
        elif event.key() == Qt.Key.Key_Delete:
            # Delete key - delete selected rows
            selected_rows = self.get_selected_rows()
            if selected_rows:
                if len(selected_rows) == 1:
                    self.delete_current_row()
                else:
                    self.delete_selected_rows()
                event.accept()
                return
        
        # Call parent implementation for other keys
        super().keyPressEvent(event)
    
    def resizeEvent(self, event):
        """Handle resize events."""
        super().resizeEvent(event)
        # Update indicator width if it's visible
        if self.drag_indicator.isVisible():
            self.drag_indicator.setGeometry(
                self.drag_indicator.x(),
                self.drag_indicator.y(),
                self.width(),
                self.drag_indicator.height()
            )

# Keep the old DraggableTableWidget class name for backward compatibility
# but make it use the new implementation
class DraggableTableWidget(DraggableTableView):
    """Backward compatible alias for DraggableTableView."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Create and set the model
        self.item_model = DragDropItemModel(self)
        self.setModel(self.item_model)
        
        # Configure view
        self.horizontalHeader().setStretchLastSection(True)
        self.verticalHeader().setVisible(False)
        self.setAlternatingRowColors(True)
        
        # Connect signals to match the old interface
        self.rowMoved.connect(self.on_row_moved)
        self.rowsMoved.connect(self.on_rows_moved)  # New multi-row signal
        self.rowInserted.connect(self.on_row_inserted)
        self.rowDeleted.connect(self.on_row_deleted)
        
        # Create backward compatibility signal
        self.itemSelectionChanged = self.selectionModel().selectionChanged
    
    def on_row_moved(self, from_row, to_row):
        """Handle row moved events."""
        if hasattr(self.parent(), 'on_row_moved'):
            self.parent().on_row_moved(from_row, to_row)
    
    def on_rows_moved(self, selected_rows, target_row):
        """Handle multiple rows moved events."""
        if hasattr(self.parent(), 'on_rows_moved'):
            self.parent().on_rows_moved(selected_rows, target_row)
    
    def on_row_inserted(self, row):
        """Handle row inserted events."""
        if hasattr(self.parent(), 'on_row_inserted'):
            self.parent().on_row_inserted(row)
    
    def on_row_deleted(self, row):
        """Handle row deleted events."""
        if hasattr(self.parent(), 'on_row_deleted'):
            self.parent().on_row_deleted(row)
    
    # Legacy methods for backward compatibility
    def setRowCount(self, count):
        """Set the number of rows."""
        current_count = self.item_model.rowCount()
        if count > current_count:
            for _ in range(count - current_count):
                self.item_model.insertRow(current_count)
        elif count < current_count:
            for _ in range(current_count - count):
                self.item_model.removeRow(count)
    
    def rowCount(self):
        """Get the number of rows."""
        return self.item_model.rowCount()
    
    def columnCount(self):
        """Get the number of columns."""
        return self.item_model.columnCount()
    
    def setItem(self, row, column, item):
        """Set an item at the specified position."""
        if isinstance(item, QTableWidgetItem):
            # Convert QTableWidgetItem to QStandardItem
            std_item = QStandardItem(item.text())
            std_item.setData(item.data(Qt.ItemDataRole.UserRole), Qt.ItemDataRole.UserRole)
            if column == 5:  # Routing column
                std_item.setFlags(std_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.item_model.setItem(row, column, std_item)
        else:
            self.item_model.setItem(row, column, item)
    
    def item(self, row, column):
        """Get an item at the specified position."""
        return self.item_model.item(row, column)
    
    def removeRow(self, row):
        """Remove a row."""
        return self.item_model.removeRow(row)
    
    def insertRow(self, row):
        """Insert a row."""
        return self.item_model.insertRow(row)
    
    def selectRow(self, row):
        """Select a single row."""
        selection_model = self.selectionModel()
        selection_model.clearSelection()
        selection_model.select(
            self.item_model.index(row, 0),
            selection_model.SelectionFlag.SelectCurrent | selection_model.SelectionFlag.Rows
        )
    
    def selectRows(self, rows):
        """Select multiple rows."""
        if not rows:
            return
        
        selection_model = self.selectionModel()
        selection_model.clearSelection()
        
        for row in rows:
            selection_model.select(
                self.item_model.index(row, 0),
                selection_model.SelectionFlag.Select | selection_model.SelectionFlag.Rows
            )
    
    def getSelectedRows(self):
        """Get list of currently selected row indices (for backward compatibility)."""
        return self.get_selected_rows() if hasattr(self, 'get_selected_rows') else []
    
    def currentRow(self):
        """Get the current row."""
        return self.currentIndex().row()
    
    def resizeColumnsToContents(self):
        """Resize columns to fit content."""
        super().resizeColumnsToContents()
    
    def setColumnCount(self, count):
        """Set the number of columns."""
        self.item_model.setColumnCount(count)
    
    def setHorizontalHeaderLabels(self, labels):
        """Set the horizontal header labels."""
        self.item_model.setHorizontalHeaderLabels(labels)


class AnalysisWorker(QThread):
    """Background worker for running analysis without freezing the GUI."""
    
    progress_update = pyqtSignal(str)
    analysis_complete = pyqtSignal(dict)
    analysis_error = pyqtSignal(str)
    
    def __init__(self, controller: MVRController, fixture_type_attributes: Dict[str, List[str]], output_format: str, ma3_config: dict = None):
        super().__init__()
        self.controller = controller
        self.fixture_type_attributes = fixture_type_attributes
        self.output_format = output_format
        self.ma3_config = ma3_config
    
    def run(self):
        """Run the analysis in background thread."""
        try:
            self.progress_update.emit("Starting analysis...")
            result = self.controller.analyze_fixtures_by_type(self.fixture_type_attributes, self.output_format, self.ma3_config)
            
            if result["success"]:
                self.analysis_complete.emit(result)
            else:
                self.analysis_error.emit(result["error"])
                
        except Exception as e:
            self.analysis_error.emit(str(e))


class MasterAnalysisWorker(QThread):
    """Background worker for running master fixture analysis."""
    
    progress_update = pyqtSignal(str)
    analysis_complete = pyqtSignal(dict)
    analysis_error = pyqtSignal(str)
    
    def __init__(self, controller: MVRController, fixture_type_attributes: Dict[str, List[str]], output_format: str, ma3_config: dict = None, sequence_start: int = 1):
        super().__init__()
        self.controller = controller
        self.fixture_type_attributes = fixture_type_attributes
        self.output_format = output_format
        self.ma3_config = ma3_config
        self.sequence_start = sequence_start
    
    def run(self):
        """Run the master analysis in background thread."""
        try:
            self.progress_update.emit("Analyzing master fixtures...")
            result = self.controller.analyze_master_fixtures(self.fixture_type_attributes, self.output_format, self.ma3_config, self.sequence_start)
            
            if result["success"]:
                self.analysis_complete.emit(result)
            else:
                self.analysis_error.emit(result["error"])
                
        except Exception as e:
            self.analysis_error.emit(str(e))


class RemoteAnalysisWorker(QThread):
    """Background worker for running remote fixture analysis."""
    
    progress_update = pyqtSignal(str)
    analysis_complete = pyqtSignal(dict)
    analysis_error = pyqtSignal(str)
    
    def __init__(self, controller: MVRController, fixture_type_attributes: Dict[str, List[str]], output_format: str, ma3_config: dict = None, sequence_start: int = 1):
        super().__init__()
        self.controller = controller
        self.fixture_type_attributes = fixture_type_attributes
        self.output_format = output_format
        self.ma3_config = ma3_config
        self.sequence_start = sequence_start
    
    def run(self):
        """Run the remote analysis in background thread."""
        try:
            self.progress_update.emit("Analyzing remote fixtures...")
            result = self.controller.analyze_remote_fixtures(self.fixture_type_attributes, self.output_format, self.ma3_config, self.sequence_start)
            
            if result["success"]:
                self.analysis_complete.emit(result)
            else:
                self.analysis_error.emit(result["error"])
                
        except Exception as e:
            self.analysis_error.emit(str(e))


class MVRApp(QMainWindow):
    """Main application window - Clean UI only."""
    
    def __init__(self):
        super().__init__()
        
        # Initialize controller
        self.controller = MVRController()
        self.config = Config()
        
        # Analysis workers
        self.worker = None
        self.master_worker = None
        self.remote_worker = None
        
        # MA3 XML configuration
        self.ma3_config = None
        
        # Results storage
        self.current_results = None
        self.master_results = None
        self.remote_results = None
        
        # Project management
        self.current_project_path = None
        self.project_dirty = False
        
        # Fixture type attributes per dataset
        self.fixture_type_attributes = {}  # Legacy
        self.master_fixture_type_attributes = {}
        self.remote_fixture_type_attributes = {}
        
        # Table ordering state - preserves user's custom row order
        self.master_table_order = []  # List of (fixture_id, attribute_name) tuples in display order
        self.remote_table_order = []  # List of (fixture_id, attribute_name) tuples in display order
        self.table_population_in_progress = False  # Flag to prevent recursive updates
        
        self.setup_ui()
        self.update_ui_state()
    
    def setup_ui(self):
        """Create the main user interface with tabbed Master/Remote workflow."""
        self.setWindowTitle("AttributeAddresser - Master & Remote Alignment")
        self.setGeometry(100, 100, 1400, 900)  # Slightly larger for tabbed interface
        
        # Additional window properties for better branding
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowTitleHint)
        
        # Create menu bar
        self.create_menu_bar()
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QVBoxLayout(central_widget)
        
        # Create tab widget
        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)
        
        # Create tabs
        self.create_master_tab()
        self.create_remote_tab()
        self.create_alignment_tab()
        
        # Add shared export section at the bottom
        export_section = self.create_export_section()
        main_layout.addWidget(export_section)
        
        # Status bar
        self.status_bar = self.statusBar()
        self.status_bar.showMessage("Ready - Start with Master fixtures")
        
        # Set minimum window size
        self.setMinimumWidth(1000)
        
        # Initialize MA3 config button visibility based on current format
        current_format = self.format_combo.currentText()
        self.ma3_config_btn.setVisible(current_format == "ma3_xml")
        
        # Load MA3 config if format is ma3_xml and config is None
        if current_format == "ma3_xml" and self.ma3_config is None:
            self.ma3_config = self.config.get_ma3_xml_config()
    
    def create_master_tab(self):
        """Create the Master fixtures tab."""
        master_widget = QWidget()
        master_layout = QVBoxLayout(master_widget)
        
        # Create horizontal layout for the first three steps
        steps_horizontal_layout = QHBoxLayout()
        
        # Add master control sections to horizontal layout with equal stretch
        master_control_sections = self.create_master_control_sections()
        for section in master_control_sections:
            steps_horizontal_layout.addWidget(section, 1)
        
        # Add the horizontal layout to master layout
        master_layout.addLayout(steps_horizontal_layout)
        
        # Add master results section in the middle
        master_results_section = self.create_master_results_section()
        master_layout.addWidget(master_results_section, 1)
        
        # Add tab to widget
        self.tab_widget.addTab(master_widget, "📋 Master Fixtures")
    
    def create_remote_tab(self):
        """Create the Remote fixtures tab."""
        remote_widget = QWidget()
        remote_layout = QVBoxLayout(remote_widget)
        
        # Create horizontal layout for the first three steps
        steps_horizontal_layout = QHBoxLayout()
        
        # Add remote control sections to horizontal layout with equal stretch
        remote_control_sections = self.create_remote_control_sections()
        for section in remote_control_sections:
            steps_horizontal_layout.addWidget(section, 1)
        
        # Add the horizontal layout to remote layout
        remote_layout.addLayout(steps_horizontal_layout)
        
        # Add remote results section in the middle
        remote_results_section = self.create_remote_results_section()
        remote_layout.addWidget(remote_results_section, 1)
        
        # Add tab to widget
        self.tab_widget.addTab(remote_widget, "📡 Remote Fixtures")
    
    def create_alignment_tab(self):
        """Create the Alignment results tab."""
        alignment_widget = QWidget()
        alignment_layout = QVBoxLayout(alignment_widget)
        
        # Add alignment status and controls
        alignment_control_section = self.create_alignment_control_section()
        alignment_layout.addWidget(alignment_control_section)
        
        # Add alignment results section
        alignment_results_section = self.create_alignment_results_section()
        alignment_layout.addWidget(alignment_results_section, 1)
        
        # Add tab to widget
        self.tab_widget.addTab(alignment_widget, "🔀 Routing")
    
    def create_menu_bar(self):
        """Create the application menu bar."""
        menubar = self.menuBar()
        
        # On macOS, add an application menu
        if sys.platform == "darwin":
            app_menu = menubar.addMenu('AttributeAddresser')
            
            # About action
            about_action = QAction('About AttributeAddresser', self)
            about_action.triggered.connect(self.show_about)
            app_menu.addAction(about_action)
            
            app_menu.addSeparator()
            
            # Quit action (macOS style)
            quit_action = QAction('Quit AttributeAddresser', self)
            quit_action.setShortcut('Cmd+Q')
            quit_action.triggered.connect(self.close)
            app_menu.addAction(quit_action)
        
        # File menu
        file_menu = menubar.addMenu('File')
        
        # New Project
        new_action = QAction('New Project', self)
        new_action.setShortcut('Ctrl+N')
        new_action.triggered.connect(self.new_project)
        file_menu.addAction(new_action)
        
        file_menu.addSeparator()
        
        # Load Project
        load_action = QAction('Load Project...', self)
        load_action.setShortcut('Ctrl+O')
        load_action.triggered.connect(self.load_project)
        file_menu.addAction(load_action)
        
        # Recent Projects submenu
        self.recent_menu = file_menu.addMenu('Recent Projects')
        self.update_recent_projects_menu()
        
        file_menu.addSeparator()
        
        # Save Project
        self.save_action = QAction('Save Project', self)
        self.save_action.setShortcut('Ctrl+S')
        self.save_action.triggered.connect(self.save_project)
        self.save_action.setEnabled(False)
        file_menu.addAction(self.save_action)
        
        # Save Project As
        save_as_action = QAction('Save Project As...', self)
        save_as_action.setShortcut('Ctrl+Shift+S')
        save_as_action.triggered.connect(self.save_project_as)
        file_menu.addAction(save_as_action)
        
        file_menu.addSeparator()
        
        # Exit
        exit_action = QAction('Exit', self)
        exit_action.setShortcut('Ctrl+Q')
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Tools menu
        tools_menu = menubar.addMenu('Tools')
        
        # Settings
        settings_action = QAction('Settings...', self)
        settings_action.triggered.connect(self.show_settings)
        tools_menu.addAction(settings_action)
    
    def create_control_sections(self) -> List[QWidget]:
        """Create all control sections as separate group boxes."""
        sections = []
        
        # File selection group
        file_group = QGroupBox("1. File Selection")
        file_layout = QVBoxLayout(file_group)
        
        # Import type selection
        import_type_layout = QHBoxLayout()
        import_type_layout.addWidget(QLabel("Import Type:"))
        
        self.import_type_group = QButtonGroup()
        self.mvr_radio = QRadioButton("MVR File")
        self.csv_radio = QRadioButton("CSV File")
        self.mvr_radio.setChecked(True)  # Default to MVR
        
        self.import_type_group.addButton(self.mvr_radio)
        self.import_type_group.addButton(self.csv_radio)
        
        import_type_layout.addWidget(self.mvr_radio)
        import_type_layout.addWidget(self.csv_radio)
        import_type_layout.addStretch()
        
        file_layout.addLayout(import_type_layout)
        
        # File status label
        self.file_label = QLabel("No file selected")
        self.file_label.setWordWrap(True)
        self.file_label.setStyleSheet("padding: 10px; border: 1px solid #ccc; border-radius: 4px;")
        file_layout.addWidget(self.file_label)
        
        # Browse button
        self.browse_btn = QPushButton("Browse MVR File...")
        self.browse_btn.clicked.connect(self.browse_file)
        file_layout.addWidget(self.browse_btn)
        
        # Connect radio buttons to update browse button text
        self.mvr_radio.toggled.connect(self.update_browse_button)
        self.csv_radio.toggled.connect(self.update_browse_button)
        
        sections.append(file_group)
        
        # GDTF Matching group
        gdtf_group = QGroupBox("2. GDTF Profile Matching")
        gdtf_layout = QVBoxLayout(gdtf_group)
        
        self.gdtf_status_label = QLabel("Load a file first")
        self.gdtf_status_label.setWordWrap(True)
        self.gdtf_status_label.setStyleSheet("color: gray; font-style: italic; padding: 5px;")
        gdtf_layout.addWidget(self.gdtf_status_label)
        
        # Manual matching button
        self.match_gdtf_btn = QPushButton("Match GDTF Profiles")
        self.match_gdtf_btn.clicked.connect(self.match_gdtf_profiles)
        self.match_gdtf_btn.setEnabled(False)
        self.match_gdtf_btn.setToolTip("Match fixture types to GDTF profiles")
        gdtf_layout.addWidget(self.match_gdtf_btn)
        
        sections.append(gdtf_group)
        
        # Attribute Selection group
        attribute_group = QGroupBox("3. Attribute Selection")
        attribute_layout = QVBoxLayout(attribute_group)
        
        self.attribute_status_label = QLabel("Complete steps 1-2 first")
        self.attribute_status_label.setWordWrap(True)
        self.attribute_status_label.setStyleSheet("color: gray; font-style: italic; padding: 5px;")
        attribute_layout.addWidget(self.attribute_status_label)
        
        # Select Attributes button
        self.select_attrs_btn = QPushButton("Select Attributes")
        self.select_attrs_btn.clicked.connect(self.select_attributes)
        self.select_attrs_btn.setEnabled(False)
        attribute_layout.addWidget(self.select_attrs_btn)
        
        sections.append(attribute_group)
        
        return sections
    
    def create_master_control_sections(self) -> List[QWidget]:
        """Create master control sections as separate group boxes."""
        sections = []
        
        # File selection group
        file_group = QGroupBox("1. Master File Selection")
        file_layout = QVBoxLayout(file_group)
        
        # Import type selection
        import_type_layout = QHBoxLayout()
        import_type_layout.addWidget(QLabel("Import Type:"))
        
        self.master_import_type_group = QButtonGroup()
        self.master_mvr_radio = QRadioButton("MVR File")
        self.master_csv_radio = QRadioButton("CSV File")
        self.master_mvr_radio.setChecked(True)  # Default to MVR
        
        self.master_import_type_group.addButton(self.master_mvr_radio)
        self.master_import_type_group.addButton(self.master_csv_radio)
        
        import_type_layout.addWidget(self.master_mvr_radio)
        import_type_layout.addWidget(self.master_csv_radio)
        import_type_layout.addStretch()
        
        file_layout.addLayout(import_type_layout)
        
        # File status label
        self.master_file_label = QLabel("No master file selected")
        self.master_file_label.setWordWrap(True)
        self.master_file_label.setStyleSheet("padding: 10px; border: 1px solid #ccc; border-radius: 4px;")
        file_layout.addWidget(self.master_file_label)
        
        # Browse button
        self.master_browse_btn = QPushButton("Browse Master MVR File...")
        self.master_browse_btn.clicked.connect(self.browse_master_file)
        file_layout.addWidget(self.master_browse_btn)
        
        # Connect radio buttons to update browse button text
        self.master_mvr_radio.toggled.connect(self.update_master_browse_button)
        self.master_csv_radio.toggled.connect(self.update_master_browse_button)
        
        sections.append(file_group)
        
        # GDTF Matching group
        gdtf_group = QGroupBox("2. Master GDTF Profile Matching")
        gdtf_layout = QVBoxLayout(gdtf_group)
        
        self.master_gdtf_status_label = QLabel("Load a master file first")
        self.master_gdtf_status_label.setWordWrap(True)
        self.master_gdtf_status_label.setStyleSheet("color: gray; font-style: italic; padding: 5px;")
        gdtf_layout.addWidget(self.master_gdtf_status_label)
        
        # Manual matching button
        self.master_match_gdtf_btn = QPushButton("Match Master GDTF Profiles")
        self.master_match_gdtf_btn.clicked.connect(self.match_master_gdtf_profiles)
        self.master_match_gdtf_btn.setEnabled(False)
        self.master_match_gdtf_btn.setToolTip("Match master fixture types to GDTF profiles")
        gdtf_layout.addWidget(self.master_match_gdtf_btn)
        
        sections.append(gdtf_group)
        
        # Attribute Selection group
        attribute_group = QGroupBox("3. Master Attribute Selection")
        attribute_layout = QVBoxLayout(attribute_group)
        
        self.master_attribute_status_label = QLabel("Complete steps 1-2 first")
        self.master_attribute_status_label.setWordWrap(True)
        self.master_attribute_status_label.setStyleSheet("color: gray; font-style: italic; padding: 5px;")
        attribute_layout.addWidget(self.master_attribute_status_label)
        
        # Select Attributes button
        self.master_select_attrs_btn = QPushButton("Select Master Attributes")
        self.master_select_attrs_btn.clicked.connect(self.select_master_attributes)
        self.master_select_attrs_btn.setEnabled(False)
        attribute_layout.addWidget(self.master_select_attrs_btn)
        
        sections.append(attribute_group)
        
        return sections
    
    def create_remote_control_sections(self) -> List[QWidget]:
        """Create remote control sections as separate group boxes."""
        sections = []
        
        # File selection group
        file_group = QGroupBox("1. Remote File Selection")
        file_layout = QVBoxLayout(file_group)
        
        # Import type selection
        import_type_layout = QHBoxLayout()
        import_type_layout.addWidget(QLabel("Import Type:"))
        
        self.remote_import_type_group = QButtonGroup()
        self.remote_mvr_radio = QRadioButton("MVR File")
        self.remote_csv_radio = QRadioButton("CSV File")
        self.remote_mvr_radio.setChecked(True)  # Default to MVR
        
        self.remote_import_type_group.addButton(self.remote_mvr_radio)
        self.remote_import_type_group.addButton(self.remote_csv_radio)
        
        import_type_layout.addWidget(self.remote_mvr_radio)
        import_type_layout.addWidget(self.remote_csv_radio)
        import_type_layout.addStretch()
        
        file_layout.addLayout(import_type_layout)
        
        # File status label
        self.remote_file_label = QLabel("No remote file selected")
        self.remote_file_label.setWordWrap(True)
        self.remote_file_label.setStyleSheet("padding: 10px; border: 1px solid #ccc; border-radius: 4px;")
        file_layout.addWidget(self.remote_file_label)
        
        # Browse button
        self.remote_browse_btn = QPushButton("Browse Remote MVR File...")
        self.remote_browse_btn.clicked.connect(self.browse_remote_file)
        file_layout.addWidget(self.remote_browse_btn)
        
        # Connect radio buttons to update browse button text
        self.remote_mvr_radio.toggled.connect(self.update_remote_browse_button)
        self.remote_csv_radio.toggled.connect(self.update_remote_browse_button)
        
        sections.append(file_group)
        
        # GDTF Matching group
        gdtf_group = QGroupBox("2. Remote GDTF Profile Matching")
        gdtf_layout = QVBoxLayout(gdtf_group)
        
        self.remote_gdtf_status_label = QLabel("Load a remote file first")
        self.remote_gdtf_status_label.setWordWrap(True)
        self.remote_gdtf_status_label.setStyleSheet("color: gray; font-style: italic; padding: 5px;")
        gdtf_layout.addWidget(self.remote_gdtf_status_label)
        
        # Manual matching button
        self.remote_match_gdtf_btn = QPushButton("Match Remote GDTF Profiles")
        self.remote_match_gdtf_btn.clicked.connect(self.match_remote_gdtf_profiles)
        self.remote_match_gdtf_btn.setEnabled(False)
        self.remote_match_gdtf_btn.setToolTip("Match remote fixture types to GDTF profiles")
        gdtf_layout.addWidget(self.remote_match_gdtf_btn)
        
        sections.append(gdtf_group)
        
        # Attribute Selection group
        attribute_group = QGroupBox("3. Remote Attribute Selection")
        attribute_layout = QVBoxLayout(attribute_group)
        
        self.remote_attribute_status_label = QLabel("Complete steps 1-2 first")
        self.remote_attribute_status_label.setWordWrap(True)
        self.remote_attribute_status_label.setStyleSheet("color: gray; font-style: italic; padding: 5px;")
        attribute_layout.addWidget(self.remote_attribute_status_label)
        
        # Select Attributes button
        self.remote_select_attrs_btn = QPushButton("Select Remote Attributes")
        self.remote_select_attrs_btn.clicked.connect(self.select_remote_attributes)
        self.remote_select_attrs_btn.setEnabled(False)
        attribute_layout.addWidget(self.remote_select_attrs_btn)
        
        sections.append(attribute_group)
        
        return sections
    
    def update_browse_button(self):
        """Update the browse button text based on selected import type."""
        if self.mvr_radio.isChecked():
            self.browse_btn.setText("Browse MVR File...")
        else:
            self.browse_btn.setText("Browse CSV File...")
    
    def update_master_browse_button(self):
        """Update the master browse button text based on selected import type."""
        if self.master_mvr_radio.isChecked():
            self.master_browse_btn.setText("Browse Master MVR File...")
        else:
            self.master_browse_btn.setText("Browse Master CSV File...")
    
    def update_remote_browse_button(self):
        """Update the remote browse button text based on selected import type."""
        if self.remote_mvr_radio.isChecked():
            self.remote_browse_btn.setText("Browse Remote MVR File...")
        else:
            self.remote_browse_btn.setText("Browse Remote CSV File...")
    
    def browse_file(self):
        """Open file dialog to select MVR or CSV file based on selection."""
        if self.mvr_radio.isChecked():
            self.browse_mvr_file()
        else:
            self.browse_csv_file()
    
    def browse_mvr_file(self):
        """Open MVR import dialog."""
        try:
            dialog = MVRImportDialog(self, self.config)
            
            # Connect the import successful signal
            dialog.import_successful.connect(self.load_csv_fixtures)
            
            dialog.exec()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error opening MVR import dialog:\n{str(e)}")
    
    def browse_csv_file(self):
        """Open CSV import dialog."""
        try:
            dialog = CSVImportDialog(self, self.config)
            
            # Connect the import successful signal
            dialog.import_successful.connect(self.load_csv_fixtures)
            
            dialog.exec()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error opening CSV import dialog:\n{str(e)}")
    
    def load_csv_fixtures(self, fixture_matches: List):
        """Load fixtures from CSV import."""
        try:
            result = self.controller.load_csv_fixtures(fixture_matches)
            
            if result["success"]:
                # Update UI
                self.file_label.setText(f"✓ CSV Import ({result['total_fixtures']} fixtures)")
                self.file_label.setStyleSheet("padding: 10px; border: 1px solid #4CAF50; border-radius: 4px; background-color: #E8F5E8; color: #2E7D32; font-weight: bold;")
                
                # Update GDTF status
                self._update_gdtf_status(result["matched_fixtures"], result["total_fixtures"])
                
                # Update UI state
                self.update_ui_state()
                self.mark_project_dirty()
                
                # Trigger automatic analysis
                self._trigger_automatic_analysis()
                
                self.status_bar.showMessage(f"Loaded {result['total_fixtures']} fixtures from CSV import")
                
            else:
                QMessageBox.critical(self, "Error", f"Failed to load CSV fixtures:\n{result['error']}")
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error loading CSV fixtures:\n{str(e)}")
    
    def load_mvr_file(self, file_path: str):
        """Load an MVR file using the controller."""
        self.status_bar.showMessage("Loading MVR file...")
        
        try:
            result = self.controller.load_mvr_file(file_path)
            
            if result["success"]:
                # Update UI
                self.file_label.setText(f"✓ {Path(file_path).name}")
                self.file_label.setStyleSheet("padding: 10px; border: 1px solid #4CAF50; border-radius: 4px; background-color: #E8F5E8; color: #2E7D32; font-weight: bold;")
                
                # Update GDTF status
                self._update_gdtf_status(result["matched_fixtures"], result["total_fixtures"])
                
                # Update UI state
                self.update_ui_state()
                self.mark_project_dirty()
                
                # Trigger automatic analysis
                self._trigger_automatic_analysis()
                
                self.status_bar.showMessage(f"Loaded {result['total_fixtures']} fixtures from {Path(file_path).name}")
                
            else:
                QMessageBox.critical(self, "Error", f"Failed to load MVR file:\n{result['error']}")
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error loading file:\n{str(e)}")
    
    def match_gdtf_profiles(self):
        """Open GDTF matching dialog."""
        try:
            # Check if we have fixtures loaded
            if not self.controller.matched_fixtures:
                QMessageBox.warning(self, "No Fixtures", "Please load fixtures first (MVR or CSV).")
                return
            
            dialog = GDTFMatchingDialog(self, self.controller, self.config)
            
            if dialog.exec() == QDialog.DialogCode.Accepted:
                # Get the fixture type matches from the dialog
                fixture_type_matches = dialog.get_fixture_type_matches()
                
                # Update matches in controller
                result = self.controller.update_fixture_matches(fixture_type_matches)
                
                if result["success"]:
                    matched_count = result["matched_fixtures"]
                    total_count = result["total_fixtures"]
                    
                    # Update GDTF status
                    self._update_gdtf_status(matched_count, total_count)
                    
                    # Update UI state
                    self.update_ui_state()
                    self.mark_project_dirty()
                    
                    # Trigger automatic analysis
                    self._trigger_automatic_analysis()
                    
                    self.status_bar.showMessage(f"Updated fixture matches: {matched_count}/{total_count} matched")
                else:
                    QMessageBox.critical(self, "Error", f"Failed to update matches:\n{result['error']}")
                    
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error in GDTF matching:\n{str(e)}")
    
    def load_external_gdtf_profiles(self):
        """Load external GDTF profiles for CSV matching."""
        try:
            # Get the last used directory
            last_dir = self.config.get_external_gdtf_folder() if self.config else ""
            
            folder_path = QFileDialog.getExistingDirectory(
                self, 
                "Select GDTF Profiles Folder", 
                last_dir
            )
            
            if not folder_path:
                return
            
            # Load profiles
            result = self.controller.load_external_gdtf_profiles(folder_path)
            
            if result["success"]:
                profile_count = result["profiles_loaded"]
                
                # Save folder path
                if self.config:
                    self.config.set_external_gdtf_folder(folder_path)
                
                # Update UI state
                self.update_ui_state()
                self.mark_project_dirty()
                
                # Trigger automatic analysis since new GDTF profiles might affect matching
                self._trigger_automatic_analysis()
                
                QMessageBox.information(
                    self, 
                    "External GDTF Profiles Loaded", 
                    f"Successfully loaded {profile_count} GDTF profiles from:\n{folder_path}\n\n"
                    f"Use 'Match GDTF Profiles' to match these profiles to your fixtures."
                )
                
                self.status_bar.showMessage(f"Loaded {profile_count} external GDTF profiles")
                
            else:
                QMessageBox.critical(self, "Error", f"Failed to load external GDTF profiles:\n{result['error']}")
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error loading external GDTF profiles:\n{str(e)}")
    

    
    def load_master_csv_fixtures(self, fixture_matches: List):
        """Load master fixtures from CSV import."""
        try:
            result = self.controller.load_master_csv_fixtures(fixture_matches)
            
            if result["success"]:
                # Update UI
                self.master_file_label.setText(f"✓ Master CSV Import ({result['total_fixtures']} fixtures)")
                self.master_file_label.setStyleSheet("padding: 10px; border: 1px solid #4CAF50; border-radius: 4px; background-color: #E8F5E8; color: #2E7D32; font-weight: bold;")
                
                # Store master results
                self.master_results = result
                
                # Update UI state
                self.update_ui_state()
                self.mark_project_dirty()
                
            else:
                QMessageBox.critical(self, "Error", f"Error loading master CSV: {result['error']}")
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error loading master CSV:\n{str(e)}")
    
    def browse_master_file(self):
        """Open file dialog to select master MVR or CSV file based on selection."""
        if self.master_mvr_radio.isChecked():
            self.browse_master_mvr_file()
        else:
            self.browse_master_csv_file()
    
    def browse_master_mvr_file(self):
        """Open MVR import dialog for master fixtures."""
        try:
            dialog = MVRImportDialog(self, self.config)
            dialog.setWindowTitle("Master MVR Import - Select Fixtures")
            
            # Connect the import successful signal
            dialog.import_successful.connect(self.load_master_csv_fixtures)
            
            dialog.exec()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error opening master MVR import dialog:\n{str(e)}")
    
    def browse_master_csv_file(self):
        """Open CSV import dialog for master fixtures."""
        try:
            dialog = CSVImportDialog(self, self.config)
            
            # Connect the import successful signal
            dialog.import_successful.connect(self.load_master_csv_fixtures)
            
            dialog.exec()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error opening master CSV import dialog:\n{str(e)}")
    
    def _setup_empty_results_tree(self):
        """Legacy method - no longer used in tabbed interface."""
        pass

    def _populate_results_tree(self, analysis_results: dict):
        """Legacy method - no longer used in tabbed interface."""
        pass

    def _show_error_in_tree(self, error_message: str):
        """Legacy method - no longer used in tabbed interface."""
        pass
        
    def _clear_results_tree(self):
        """Legacy method - no longer used in tabbed interface."""
        pass

    def _should_trigger_analysis(self) -> bool:
        """Check if automatic analysis should be triggered."""
        # Check if we have everything needed for analysis
        status = self.controller.get_current_status()
        
        # Step 1: File loaded
        if not status["file_loaded"]:
            return False
            
        # Step 2: GDTF matching (at least some fixtures matched)
        if status["matched_fixtures"] <= 0:
            return False
            
        # Step 3: Attributes selected
        if not self.fixture_type_attributes:
            return False
            
        # Check if any attributes are actually selected
        total_attributes = sum(len(attrs) for attrs in self.fixture_type_attributes.values())
        if total_attributes <= 0:
            return False
            
        return True

    def _trigger_automatic_analysis(self):
        """Legacy method - automatic analysis is now handled per tab."""
        pass
    
    def _trigger_master_analysis(self):
        """Trigger automatic analysis for master fixtures."""
        if not self._should_trigger_master_analysis():
            return
            
        # Prevent multiple concurrent analyses
        if self.master_worker is not None:
            return
            
        self.status_bar.showMessage("Analyzing master fixtures...")
        
        # Get output format and MA3 config
        output_format = self.format_combo.currentText()
        ma3_config = self.ma3_config if output_format == "ma3_xml" else None
        sequence_start = self.config.get_sequence_start_number()
        
        # Start analysis worker
        self.master_worker = MasterAnalysisWorker(
            self.controller, 
            self.master_fixture_type_attributes, 
            output_format, 
            ma3_config,
            sequence_start
        )
        
        self.master_worker.progress_update.connect(self.update_progress)
        self.master_worker.analysis_complete.connect(self.master_analysis_complete)
        self.master_worker.analysis_error.connect(self.master_analysis_error)
        self.master_worker.start()
    
    def _trigger_remote_analysis(self):
        """Trigger automatic analysis for remote fixtures."""
        if not self._should_trigger_remote_analysis():
            return
            
        # Prevent multiple concurrent analyses
        if self.remote_worker is not None:
            return
            
        self.status_bar.showMessage("Analyzing remote fixtures...")
        
        # Get output format and MA3 config
        output_format = self.format_combo.currentText()
        ma3_config = self.ma3_config if output_format == "ma3_xml" else None
        sequence_start = self.config.get_sequence_start_number()
        
        # Start analysis worker
        self.remote_worker = RemoteAnalysisWorker(
            self.controller, 
            self.remote_fixture_type_attributes, 
            output_format, 
            ma3_config,
            sequence_start
        )
        
        self.remote_worker.progress_update.connect(self.update_progress)
        self.remote_worker.analysis_complete.connect(self.remote_analysis_complete)
        self.remote_worker.analysis_error.connect(self.remote_analysis_error)
        self.remote_worker.start()
    
    def _should_trigger_master_analysis(self) -> bool:
        """Check if automatic analysis should be triggered for master fixtures."""
        # Check if we have everything needed for master analysis
        status = self.controller.get_master_status()
        
        # Step 1: File loaded
        if not status["file_loaded"]:
            return False
            
        # Step 2: GDTF matching (at least some fixtures matched)
        if status["matched_fixtures"] <= 0:
            return False
            
        # Step 3: Attributes selected
        if not self.master_fixture_type_attributes:
            return False
            
        # Check if any attributes are actually selected
        total_attributes = sum(len(attrs) for attrs in self.master_fixture_type_attributes.values())
        if total_attributes <= 0:
            return False
            
        return True
    
    def _should_trigger_remote_analysis(self) -> bool:
        """Check if automatic analysis should be triggered for remote fixtures."""
        # Check if we have everything needed for remote analysis
        status = self.controller.get_remote_status()
        
        # Step 1: File loaded
        if not status["file_loaded"]:
            return False
            
        # Step 2: GDTF matching (at least some fixtures matched)
        if status["matched_fixtures"] <= 0:
            return False
            
        # Step 3: Attributes selected
        if not self.remote_fixture_type_attributes:
            return False
            
        # Check if any attributes are actually selected
        total_attributes = sum(len(attrs) for attrs in self.remote_fixture_type_attributes.values())
        if total_attributes <= 0:
            return False
            
        return True

    def _update_results_status(self):
        """Update the results status based on current state."""
        if self._should_trigger_analysis():
            if self.current_results:
                summary = self.current_results.get("summary", {})
                total_fixtures = summary.get("total_fixtures", 0)
                matched_fixtures = summary.get("matched_fixtures", 0)
                conflicts = len(summary.get("conflicts", []))
                
                status_msg = f"Analysis complete: {matched_fixtures}/{total_fixtures} fixtures"
                if conflicts > 0:
                    status_msg += f", {conflicts} conflicts"
                
                self.results_status.setText(status_msg)
                self.results_status.setStyleSheet("color: green; font-weight: bold; padding: 10px;")
            else:
                self.results_status.setText("Ready for automatic analysis")
                self.results_status.setStyleSheet("color: blue; font-weight: bold; padding: 10px;")
        else:
            self.results_status.setText("Complete steps 1-3 for automatic analysis")
            self.results_status.setStyleSheet("color: gray; font-style: italic; padding: 10px;")
    
    def browse_csv_file(self):
        """Open CSV import dialog."""
        try:
            dialog = CSVImportDialog(self, self.config)
            
            # Connect the import successful signal
            dialog.import_successful.connect(self.load_csv_fixtures)
            
            dialog.exec()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error opening CSV import dialog:\n{str(e)}")
    
    def load_csv_fixtures(self, fixture_matches: List):
        """Load fixtures from CSV import."""
        try:
            result = self.controller.load_csv_fixtures(fixture_matches)
            
            if result["success"]:
                # Update UI
                self.file_label.setText(f"✓ CSV Import ({result['total_fixtures']} fixtures)")
                self.file_label.setStyleSheet("padding: 10px; border: 1px solid #4CAF50; border-radius: 4px; background-color: #E8F5E8; color: #2E7D32; font-weight: bold;")
                
                # Update GDTF status
                self._update_gdtf_status(result["matched_fixtures"], result["total_fixtures"])
                
                # Update UI state
                self.update_ui_state()
                self.mark_project_dirty()
                
                # Trigger automatic analysis
                self._trigger_automatic_analysis()
                
                self.status_bar.showMessage(f"Loaded {result['total_fixtures']} fixtures from CSV import")
                
            else:
                QMessageBox.critical(self, "Error", f"Failed to load CSV fixtures:\n{result['error']}")
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error loading CSV fixtures:\n{str(e)}")
    
    def load_mvr_file(self, file_path: str):
        """Load an MVR file using the controller."""
        self.status_bar.showMessage("Loading MVR file...")
        
        try:
            result = self.controller.load_mvr_file(file_path)
            
            if result["success"]:
                # Update UI
                self.file_label.setText(f"✓ {Path(file_path).name}")
                self.file_label.setStyleSheet("padding: 10px; border: 1px solid #4CAF50; border-radius: 4px; background-color: #E8F5E8; color: #2E7D32; font-weight: bold;")
                
                # Update GDTF status
                self._update_gdtf_status(result["matched_fixtures"], result["total_fixtures"])
                
                # Update UI state
                self.update_ui_state()
                self.mark_project_dirty()
                
                # Trigger automatic analysis
                self._trigger_automatic_analysis()
                
                self.status_bar.showMessage(f"Loaded {result['total_fixtures']} fixtures from {Path(file_path).name}")
                
            else:
                QMessageBox.critical(self, "Error", f"Failed to load MVR file:\n{result['error']}")
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error loading file:\n{str(e)}")
    
    def match_gdtf_profiles(self):
        """Open GDTF matching dialog."""
        try:
            # Check if we have fixtures loaded
            if not self.controller.matched_fixtures:
                QMessageBox.warning(self, "No Fixtures", "Please load fixtures first (MVR or CSV).")
                return
            
            dialog = GDTFMatchingDialog(self, self.controller, self.config)
            
            if dialog.exec() == QDialog.DialogCode.Accepted:
                # Get the fixture type matches from the dialog
                fixture_type_matches = dialog.get_fixture_type_matches()
                
                # Update matches in controller
                result = self.controller.update_fixture_matches(fixture_type_matches)
                
                if result["success"]:
                    matched_count = result["matched_fixtures"]
                    total_count = result["total_fixtures"]
                    
                    # Update GDTF status
                    self._update_gdtf_status(matched_count, total_count)
                    
                    # Update UI state
                    self.update_ui_state()
                    self.mark_project_dirty()
                    
                    # Trigger automatic analysis
                    self._trigger_automatic_analysis()
                    
                    self.status_bar.showMessage(f"Updated fixture matches: {matched_count}/{total_count} matched")
                else:
                    QMessageBox.critical(self, "Error", f"Failed to update matches:\n{result['error']}")
                    
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error in GDTF matching:\n{str(e)}")
    
    def load_external_gdtf_profiles(self):
        """Load external GDTF profiles for CSV matching."""
        try:
            # Get the last used directory
            last_dir = self.config.get_external_gdtf_folder() if self.config else ""
            
            folder_path = QFileDialog.getExistingDirectory(
                self, 
                "Select GDTF Profiles Folder", 
                last_dir
            )
            
            if not folder_path:
                return
            
            # Load profiles
            result = self.controller.load_external_gdtf_profiles(folder_path)
            
            if result["success"]:
                profile_count = result["profiles_loaded"]
                
                # Save folder path
                if self.config:
                    self.config.set_external_gdtf_folder(folder_path)
                
                # Update UI state
                self.update_ui_state()
                self.mark_project_dirty()
                
                # Trigger automatic analysis since new GDTF profiles might affect matching
                self._trigger_automatic_analysis()
                
                QMessageBox.information(
                    self, 
                    "External GDTF Profiles Loaded", 
                    f"Successfully loaded {profile_count} GDTF profiles from:\n{folder_path}\n\n"
                    f"Use 'Match GDTF Profiles' to match these profiles to your fixtures."
                )
                
                self.status_bar.showMessage(f"Loaded {profile_count} external GDTF profiles")
                
            else:
                QMessageBox.critical(self, "Error", f"Failed to load external GDTF profiles:\n{result['error']}")
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error loading external GDTF profiles:\n{str(e)}")
    
    def select_attributes(self):
        """Open attribute selection dialog and save selections independently."""
        try:
            # Open the fixture attribute dialog with existing selections
            dialog = FixtureAttributeDialog(self, self.controller, self.config, self.fixture_type_attributes, data_source="current")
            
            if dialog.exec() == QDialog.DialogCode.Accepted:
                # Get selected attributes per fixture type
                self.fixture_type_attributes = dialog.get_fixture_type_attributes()
                
                # Validate that we have some attributes selected
                total_selected = sum(len(attrs) for attrs in self.fixture_type_attributes.values())
                if total_selected == 0:
                    QMessageBox.warning(self, "No Attributes", "No attributes were selected. You can modify your selection anytime.")
                    self.fixture_type_attributes = {}
                else:
                    # Store the attributes in config (for future reference)
                    self.config.set_fixture_type_attributes(self.fixture_type_attributes)
                    
                    # Mark project as dirty
                    self.mark_project_dirty()
                
                # Update UI state after any changes
                self.update_ui_state()
                
                # Trigger automatic analysis
                self._trigger_automatic_analysis()
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error in attribute selection:\n{str(e)}")
    
    def select_master_attributes(self):
        """Open attribute selection dialog and save selections independently."""
        try:
            # Open the fixture attribute dialog with existing selections
            dialog = FixtureAttributeDialog(self, self.controller, self.config, self.master_fixture_type_attributes, data_source="master")
            
            if dialog.exec() == QDialog.DialogCode.Accepted:
                # Get selected attributes per fixture type
                self.master_fixture_type_attributes = dialog.get_fixture_type_attributes()
                
                # Validate that we have some attributes selected
                total_selected = sum(len(attrs) for attrs in self.master_fixture_type_attributes.values())
                if total_selected == 0:
                    QMessageBox.warning(self, "No Attributes", "No attributes were selected for master fixtures. You can modify your selection anytime.")
                    self.master_fixture_type_attributes = {}
                else:
                    # Store the attributes in config (for future reference)
                    self.config.set_fixture_type_attributes(self.master_fixture_type_attributes)
                    
                    # Mark project as dirty
                    self.mark_project_dirty()
                
                # Update UI state after any changes
                self.update_ui_state()
                
                # Trigger automatic analysis for master fixtures
                self._trigger_master_analysis()
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error in master attribute selection:\n{str(e)}")
    
    def match_master_gdtf_profiles(self):
        """Open GDTF matching dialog for master fixtures."""
        try:
            # Check if we have master fixtures loaded
            if not self.controller.master_matched_fixtures:
                QMessageBox.warning(self, "No Master Fixtures", "Please load master fixtures first (MVR or CSV).")
                return
            
            # Use existing dialog but set it to work with master fixtures
            dialog = GDTFMatchingDialog(self, self.controller, self.config)
            dialog.set_fixture_data_source("master")  # We'll need to add this method
            
            if dialog.exec() == QDialog.DialogCode.Accepted:
                # Get the fixture type matches from the dialog
                fixture_type_matches = dialog.get_fixture_type_matches()
                
                # Update matches in controller
                result = self.controller.update_master_fixture_matches(fixture_type_matches)
                
                if result["success"]:
                    matched_count = result["matched_fixtures"]
                    total_count = result["total_fixtures"]
                    
                    # Update UI state
                    self.update_ui_state()
                    self.mark_project_dirty()
                    
                    self.status_bar.showMessage(f"Updated master fixture matches: {matched_count}/{total_count} matched")
                else:
                    QMessageBox.critical(self, "Error", f"Failed to update master matches:\n{result['error']}")
                    
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error in master GDTF matching:\n{str(e)}")
    
    def load_master_file(self, file_path: str):
        """Load an MVR file using the controller for master fixtures."""
        self.status_bar.showMessage("Loading Master MVR file...")
        
        try:
            result = self.controller.load_master_mvr_file(file_path)
            
            if result["success"]:
                # Update UI
                self.master_file_label.setText(f"✓ {Path(file_path).name}")
                self.master_file_label.setStyleSheet("padding: 10px; border: 1px solid #4CAF50; border-radius: 4px; background-color: #E8F5E8; color: #2E7D32; font-weight: bold;")
                
                # Store master results
                self.master_results = result
                
                # Update UI state
                self.update_ui_state()
                self.mark_project_dirty()
                
                self.status_bar.showMessage(f"Loaded {result['total_fixtures']} master fixtures from {Path(file_path).name}")
                
            else:
                QMessageBox.critical(self, "Error", f"Failed to load Master MVR file:\n{result['error']}")
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error loading Master file:\n{str(e)}")
    
    def browse_remote_file(self):
        """Open file dialog to select remote MVR or CSV file based on selection."""
        if self.remote_mvr_radio.isChecked():
            self.browse_remote_mvr_file()
        else:
            self.browse_remote_csv_file()
    
    def browse_remote_mvr_file(self):
        """Open MVR import dialog for remote fixtures."""
        try:
            dialog = MVRImportDialog(self, self.config)
            dialog.setWindowTitle("Remote MVR Import - Select Fixtures")
            
            # Connect the import successful signal
            dialog.import_successful.connect(self.load_remote_csv_fixtures)
            
            dialog.exec()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error opening remote MVR import dialog:\n{str(e)}")
    
    def browse_remote_csv_file(self):
        """Open CSV import dialog for remote fixtures."""
        try:
            dialog = CSVImportDialog(self, self.config)
            
            # Connect the import successful signal
            dialog.import_successful.connect(self.load_remote_csv_fixtures)
            
            dialog.exec()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error opening remote CSV import dialog:\n{str(e)}")
    
    def load_remote_file(self, file_path: str):
        """Load an MVR file using the controller for remote fixtures."""
        self.status_bar.showMessage("Loading Remote MVR file...")
        
        try:
            result = self.controller.load_remote_mvr_file(file_path)
            
            if result["success"]:
                # Update UI
                self.remote_file_label.setText(f"✓ {Path(file_path).name}")
                self.remote_file_label.setStyleSheet("padding: 10px; border: 1px solid #4CAF50; border-radius: 4px; background-color: #E8F5E8; color: #2E7D32; font-weight: bold;")
                
                # Store remote results
                self.remote_results = result
                
                # Update UI state
                self.update_ui_state()
                self.mark_project_dirty()
                
                self.status_bar.showMessage(f"Loaded {result['total_fixtures']} remote fixtures from {Path(file_path).name}")
                
            else:
                QMessageBox.critical(self, "Error", f"Failed to load Remote MVR file:\n{result['error']}")
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error loading Remote file:\n{str(e)}")
    
    def load_remote_csv_fixtures(self, fixture_matches: List):
        """Load remote fixtures from CSV import."""
        try:
            result = self.controller.load_remote_csv_fixtures(fixture_matches)
            
            if result["success"]:
                # Update UI
                self.remote_file_label.setText(f"✓ Remote CSV Import ({result['total_fixtures']} fixtures)")
                self.remote_file_label.setStyleSheet("padding: 10px; border: 1px solid #4CAF50; border-radius: 4px; background-color: #E8F5E8; color: #2E7D32; font-weight: bold;")
                
                # Store remote results
                self.remote_results = result
                
                # Update UI state
                self.update_ui_state()
                self.mark_project_dirty()
                
            else:
                QMessageBox.critical(self, "Error", f"Error loading remote CSV: {result['error']}")
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error loading remote CSV:\n{str(e)}")
    
    def match_remote_gdtf_profiles(self):
        """Open GDTF matching dialog for remote fixtures."""
        try:
            # Check if we have remote fixtures loaded
            if not self.controller.remote_matched_fixtures:
                QMessageBox.warning(self, "No Remote Fixtures", "Please load remote fixtures first (MVR or CSV).")
                return
            
            # Use existing dialog but set it to work with remote fixtures
            dialog = GDTFMatchingDialog(self, self.controller, self.config)
            dialog.set_fixture_data_source("remote")
            
            if dialog.exec() == QDialog.DialogCode.Accepted:
                # Get the fixture type matches from the dialog
                fixture_type_matches = dialog.get_fixture_type_matches()
                
                # Update matches in controller
                result = self.controller.update_remote_fixture_matches(fixture_type_matches)
                
                if result["success"]:
                    matched_count = result["matched_fixtures"]
                    total_count = result["total_fixtures"]
                    
                    # Update UI state
                    self.update_ui_state()
                    self.mark_project_dirty()
                    
                    self.status_bar.showMessage(f"Updated remote fixture matches: {matched_count}/{total_count} matched")
                else:
                    QMessageBox.critical(self, "Error", f"Failed to update remote matches:\n{result['error']}")
                    
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error in remote GDTF matching:\n{str(e)}")
    
    def select_remote_attributes(self):
        """Select remote attributes for analysis."""
        try:
            # Check if remote fixtures are loaded
            if not hasattr(self, 'remote_fixture_type_attributes'):
                self.remote_fixture_type_attributes = {}
                
            dialog = FixtureAttributeDialog(self, self.controller, self.config, self.remote_fixture_type_attributes, data_source="remote")
            
            if dialog.exec() == QDialog.DialogCode.Accepted:
                # Get selected attributes per fixture type
                self.remote_fixture_type_attributes = dialog.get_fixture_type_attributes()
                
                # Validate that we have some attributes selected
                total_selected = sum(len(attrs) for attrs in self.remote_fixture_type_attributes.values())
                if total_selected == 0:
                    QMessageBox.warning(self, "No Attributes", "No attributes were selected for remote fixtures. You can modify your selection anytime.")
                    self.remote_fixture_type_attributes = {}
                else:
                    # Store the attributes in config (for future reference)
                    self.config.set_fixture_type_attributes(self.remote_fixture_type_attributes)
                    
                    # Mark project as dirty
                    self.mark_project_dirty()
                
                # Update UI state after any changes
                self.update_ui_state()
                
                # Trigger automatic analysis for remote fixtures
                self._trigger_remote_analysis()
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error in remote attribute selection:\n{str(e)}")
    
    def create_export_section(self) -> QWidget:
        """Create the export section at the bottom."""
        export_group = QGroupBox("Export & Configuration")
        export_layout = QHBoxLayout(export_group)
        
        # Output format selection
        format_label = QLabel("Output Format:")
        export_layout.addWidget(format_label)
        
        self.format_combo = QComboBox()
        self.format_combo.addItems(["ma3_xml", "ma3_sequences", "csv", "json"])
        self.format_combo.setCurrentText("ma3_xml")
        self.format_combo.currentTextChanged.connect(self.on_format_changed)
        export_layout.addWidget(self.format_combo)
        
        # MA3 XML configuration button
        self.ma3_config_btn = QPushButton("Configure MA3 XML...")
        self.ma3_config_btn.clicked.connect(self.configure_ma3_xml)
        export_layout.addWidget(self.ma3_config_btn)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        export_layout.addWidget(self.progress_bar)
        
        # Export button
        self.export_btn = QPushButton("Export Results")
        self.export_btn.clicked.connect(self.export_results)
        self.export_btn.setEnabled(False)
        export_layout.addWidget(self.export_btn)
        
        export_layout.addStretch()
        
        return export_group
    
    def create_master_results_section(self) -> QWidget:
        """Create the master results section."""
        results_group = QGroupBox("Master Analysis Results")
        results_layout = QVBoxLayout(results_group)
        
        # Results status
        self.master_results_status = QLabel("Complete steps 1-3 for automatic analysis")
        self.master_results_status.setStyleSheet("color: gray; font-style: italic; padding: 10px;")
        results_layout.addWidget(self.master_results_status)
        
        # Results tree
        self.master_results_tree = QTreeWidget()
        self.master_results_tree.setHeaderLabels(["Fixture/Attribute", "Type", "GDTF Profile", "Base Address", "Mode", "ActivationGroup", "Sequence", "Universe", "Channel", "Absolute"])
        self.master_results_tree.setAlternatingRowColors(True)
        self.master_results_tree.setRootIsDecorated(True)
        results_layout.addWidget(self.master_results_tree)
        
        # Setup initial state
        self._setup_empty_master_results_tree()
        
        return results_group
    
    def create_remote_results_section(self) -> QWidget:
        """Create the remote results section."""
        results_group = QGroupBox("Remote Analysis Results")
        results_layout = QVBoxLayout(results_group)
        
        # Results status
        self.remote_results_status = QLabel("Complete steps 1-3 for automatic analysis")
        self.remote_results_status.setStyleSheet("color: gray; font-style: italic; padding: 10px;")
        results_layout.addWidget(self.remote_results_status)
        
        # Results tree
        self.remote_results_tree = QTreeWidget()
        self.remote_results_tree.setHeaderLabels(["Fixture/Attribute", "Type", "GDTF Profile", "Base Address", "Mode", "ActivationGroup", "Sequence", "Universe", "Channel", "Absolute"])
        self.remote_results_tree.setAlternatingRowColors(True)
        self.remote_results_tree.setRootIsDecorated(True)
        results_layout.addWidget(self.remote_results_tree)
        
        # Setup initial state
        self._setup_empty_remote_results_tree()
        
        return results_group
    
    def create_alignment_control_section(self) -> QWidget:
        """Create the routing control section."""
        control_group = QGroupBox("Routing Controls")
        control_layout = QVBoxLayout(control_group)
        
        # Status label
        self.alignment_status = QLabel("Load Master and Remote fixtures to begin routing")
        self.alignment_status.setStyleSheet("color: gray; font-style: italic; padding: 10px;")
        control_layout.addWidget(self.alignment_status)
        
        # Alignment buttons
        button_layout = QHBoxLayout()
        
        self.align_btn = QPushButton("Auto Route")
        self.align_btn.setEnabled(False)
        self.align_btn.setToolTip("Automatically route remote fixtures to master fixtures based on names")
        self.align_btn.clicked.connect(self.align_fixtures)
        button_layout.addWidget(self.align_btn)
        
        self.pair_btn = QPushButton("Link Selected")
        self.pair_btn.setEnabled(False)
        self.pair_btn.setToolTip("Manually link selected master and remote fixtures")
        self.pair_btn.clicked.connect(self.pair_selected_fixtures)
        button_layout.addWidget(self.pair_btn)
        
        self.unpair_btn = QPushButton("Unlink Selected")
        self.unpair_btn.setEnabled(False)
        self.unpair_btn.setToolTip("Remove manual link for selected master fixture")
        self.unpair_btn.clicked.connect(self.unpair_selected_fixture)
        button_layout.addWidget(self.unpair_btn)
        
        self.clear_alignment_btn = QPushButton("Clear All")
        self.clear_alignment_btn.setEnabled(False)
        self.clear_alignment_btn.clicked.connect(self.clear_alignment)
        button_layout.addWidget(self.clear_alignment_btn)
        
        # Add sequence assignment button
        self.assign_sequences_btn = QPushButton("Assign Sequences")
        self.assign_sequences_btn.setEnabled(False)
        self.assign_sequences_btn.setToolTip("Assign sequence numbers from master to remote fixtures based on row position")
        self.assign_sequences_btn.clicked.connect(self.assign_sequences_by_row)
        button_layout.addWidget(self.assign_sequences_btn)
        
        button_layout.addStretch()
        
        control_layout.addLayout(button_layout)
        
        return control_group
    
    def create_alignment_results_section(self) -> QWidget:
        """Create the routing section with side-by-side tables."""
        results_group = QGroupBox("Attribute Routing")
        results_layout = QVBoxLayout(results_group)
        
        # Results status
        self.alignment_results_status = QLabel("Load Master and Remote fixtures to begin attribute routing")
        self.alignment_results_status.setStyleSheet("color: gray; font-style: italic; padding: 10px;")
        results_layout.addWidget(self.alignment_results_status)
        
        # Create horizontal layout for side-by-side tables
        tables_layout = QHBoxLayout()
        
        # Master attributes table
        master_group = QGroupBox("Master Attributes")
        master_layout = QVBoxLayout(master_group)
        
        self.master_fixtures_table = DraggableTableWidget()
        self.master_fixtures_table.setColumnCount(9)
        self.master_fixtures_table.setHorizontalHeaderLabels([
            "Fixture ID", "Fixture Name", "Attribute", "Sequence", 
            "ActivationGroup", "Universe", "Channel", "Absolute", "Routing"
        ])
        self.master_fixtures_table.setAlternatingRowColors(True)
        self.master_fixtures_table.itemSelectionChanged.connect(self.on_master_selection_changed)
        master_layout.addWidget(self.master_fixtures_table)
        
        # Remote attributes table
        remote_group = QGroupBox("Remote Attributes")
        remote_layout = QVBoxLayout(remote_group)
        
        self.remote_fixtures_table = DraggableTableWidget()
        self.remote_fixtures_table.setColumnCount(9)
        self.remote_fixtures_table.setHorizontalHeaderLabels([
            "Fixture ID", "Fixture Name", "Attribute", "Sequence", 
            "ActivationGroup", "Universe", "Channel", "Absolute", "Routing"
        ])
        self.remote_fixtures_table.setAlternatingRowColors(True)
        self.remote_fixtures_table.itemSelectionChanged.connect(self.on_remote_selection_changed)
        remote_layout.addWidget(self.remote_fixtures_table)
        
        # Add equal stretch to both tables
        tables_layout.addWidget(master_group, 1)
        tables_layout.addWidget(remote_group, 1)
        
        results_layout.addLayout(tables_layout, 1)
        
        # Setup initial state
        self._setup_empty_alignment_tables()
        
        return results_group
    
    def _setup_empty_master_results_tree(self):
        """Set up the master results tree in empty state."""
        self.master_results_tree.clear()
        
        # Add a status item
        status_item = QTreeWidgetItem()
        status_item.setText(0, "Complete steps 1-3 for automatic analysis")
        status_item.setForeground(0, QColor("gray"))
        
        # Set italic font
        font = QFont()
        font.setItalic(True)
        status_item.setFont(0, font)
        
        self.master_results_tree.addTopLevelItem(status_item)
        
        # Resize to fit content
        self.master_results_tree.resizeColumnToContents(0)
    
    def _setup_empty_remote_results_tree(self):
        """Set up the remote results tree in empty state."""
        self.remote_results_tree.clear()
        
        # Add a status item
        status_item = QTreeWidgetItem()
        status_item.setText(0, "Complete steps 1-3 for automatic analysis")
        status_item.setForeground(0, QColor("gray"))
        
        # Set italic font
        font = QFont()
        font.setItalic(True)
        status_item.setFont(0, font)
        
        self.remote_results_tree.addTopLevelItem(status_item)
        
        # Resize to fit content
        self.remote_results_tree.resizeColumnToContents(0)
    
    def _setup_empty_alignment_tables(self):
        """Set up the alignment tables in empty state."""
        self.master_fixtures_table.setRowCount(0)
        self.remote_fixtures_table.setRowCount(0)
        
        # Resize columns to fit content
        self.master_fixtures_table.resizeColumnsToContents()
        self.remote_fixtures_table.resizeColumnsToContents()
    
    def align_fixtures(self):
        """Perform automatic fixture alignment between master and remote fixtures."""
        try:
            self.status_bar.showMessage("Auto-aligning fixtures...")
            
            # Show alignment configuration dialog or use defaults
            alignment_config = {
                "match_threshold": 0.8,
                "case_sensitive": False,
                "allow_partial_matches": True,
                "prioritize_exact_matches": True
            }
            
            result = self.controller.align_fixtures(alignment_config)
            
            if result["success"]:
                # Clear any existing manual alignments and set mode to automatic
                self.controller.manual_alignments = {}
                self.controller.alignment_mode = "automatic"
                
                # Update alignment tables
                self._populate_alignment_tables()
                
                # Update alignment status
                matched_count = result["matched_count"]
                total_master = len(self.controller.master_matched_fixtures)
                alignment_percentage = result["alignment_percentage"]
                sequence_assignments = result.get("sequence_assignments", 0)
                
                status_text = f"✓ Auto-alignment complete: {matched_count}/{total_master} fixtures matched ({alignment_percentage:.1f}%)"
                if sequence_assignments > 0:
                    status_text += f", {sequence_assignments} sequences assigned"
                
                self.alignment_status.setText(status_text)
                self.alignment_status.setStyleSheet("color: green; font-weight: bold; padding: 10px;")
                
                # Enable clear button
                self.clear_alignment_btn.setEnabled(True)
                
                # Mark project as dirty
                self.mark_project_dirty()
                
                status_msg = f"Auto-alignment complete: {matched_count} fixtures matched"
                if sequence_assignments > 0:
                    status_msg += f", {sequence_assignments} sequences assigned"
                self.status_bar.showMessage(status_msg)
                
            else:
                QMessageBox.critical(self, "Alignment Error", f"Failed to align fixtures:\n{result['error']}")
                self.status_bar.showMessage("Alignment failed")
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error during alignment:\n{str(e)}")
            self.status_bar.showMessage("Alignment error")
    
    def clear_alignment(self):
        """Clear current alignment results."""
        try:
            self.controller.clear_alignment_results()
            
            # Refresh the tables
            self._populate_alignment_tables()
            
            # Reset alignment status
            self.alignment_status.setText("Load Master and Remote fixtures to begin attribute alignment")
            self.alignment_status.setStyleSheet("color: gray; font-style: italic; padding: 10px;")
            
            # Disable clear button
            self.clear_alignment_btn.setEnabled(False)
            
            # Mark project as dirty
            self.mark_project_dirty()
            
            self.status_bar.showMessage("Alignment results cleared")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error clearing alignment:\n{str(e)}")
    
    def on_master_selection_changed(self):
        """Handle master table selection changes."""
        self._update_manual_alignment_buttons()
    
    def on_remote_selection_changed(self):
        """Handle remote table selection changes."""
        self._update_manual_alignment_buttons()
    
    def pair_selected_fixtures(self):
        """Pair selected master and remote fixtures."""
        try:
            # Get selected rows
            master_row = self._get_selected_master_row()
            remote_row = self._get_selected_remote_row()
            
            if master_row is None or remote_row is None:
                QMessageBox.warning(self, "Selection Required", "Please select both a master and remote fixture to pair.")
                return
            
            # Get fixture IDs
            master_id = self.master_fixtures_table.item(master_row, 0).text()
            remote_id = self.remote_fixtures_table.item(remote_row, 0).text()
            
            # Set manual alignment
            self.controller.set_manual_alignment(master_id, remote_id)
            
            # Refresh the tables
            self._populate_alignment_tables()
            
            # Update status
            self._update_alignment_status()
            
            # Mark project as dirty
            self.mark_project_dirty()
            
            self.status_bar.showMessage(f"Paired master fixture {master_id} with remote fixture {remote_id} (sequences assigned automatically)")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error pairing fixtures:\n{str(e)}")
            self.status_bar.showMessage("Error pairing fixtures")
    
    def unpair_selected_fixture(self):
        """Remove manual pairing for selected master fixture."""
        try:
            # Get selected master row
            master_row = self._get_selected_master_row()
            
            if master_row is None:
                QMessageBox.warning(self, "Selection Required", "Please select a master fixture to unpair.")
                return
            
            # Get fixture ID
            master_id = self.master_fixtures_table.item(master_row, 0).text()
            
            # Remove manual alignment
            self.controller.remove_manual_alignment(master_id)
            
            # Refresh the tables
            self._populate_alignment_tables()
            
            # Update status
            self._update_alignment_status()
            
            # Mark project as dirty
            self.mark_project_dirty()
            
            self.status_bar.showMessage(f"Unpaired master fixture {master_id}")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error unpairing fixture:\n{str(e)}")
            self.status_bar.showMessage("Error unpairing fixture")
    
    def _get_selected_master_row(self) -> Optional[int]:
        """Get the selected row in the master table."""
        selection = self.master_fixtures_table.selectionModel().selectedRows()
        if selection:
            return selection[0].row()
        return None
    
    def _get_selected_remote_row(self) -> Optional[int]:
        """Get the selected row in the remote table."""
        selection = self.remote_fixtures_table.selectionModel().selectedRows()
        if selection:
            return selection[0].row()
        return None
    
    def _update_manual_alignment_buttons(self):
        """Update the state of manual alignment buttons."""
        has_master = self._get_selected_master_row() is not None
        has_remote = self._get_selected_remote_row() is not None
        
        self.pair_btn.setEnabled(has_master and has_remote)
        self.unpair_btn.setEnabled(has_master)
    
    def assign_sequences_by_row(self):
        """Assign sequence numbers from master table rows to corresponding remote table rows."""
        try:
            if not hasattr(self, 'master_fixtures_table') or not hasattr(self, 'remote_fixtures_table'):
                QMessageBox.warning(self, "Tables Not Ready", "Master and remote tables are not available.")
                return
                
            # Check if we have both master and remote data
            if not hasattr(self, 'master_results') or self.master_results is None:
                QMessageBox.warning(self, "No Master Data", "Please load and analyze master fixtures first.")
                return
                
            if not hasattr(self, 'remote_results') or self.remote_results is None:
                QMessageBox.warning(self, "No Remote Data", "Please load and analyze remote fixtures first.")
                return
            
            master_row_count = self.master_fixtures_table.rowCount()
            remote_row_count = self.remote_fixtures_table.rowCount()
            
            if master_row_count == 0:
                QMessageBox.warning(self, "No Master Rows", "No master fixture attributes found.")
                return
                
            if remote_row_count == 0:
                QMessageBox.warning(self, "No Remote Rows", "No remote fixture attributes found.")
                return
            
            # Ask user for confirmation
            msg = f"This will assign sequence numbers from {master_row_count} master rows to {remote_row_count} remote rows.\n\n"
            msg += "Row 1 master sequence → Row 1 remote sequence\n"
            msg += "Row 2 master sequence → Row 2 remote sequence\n"
            msg += "etc.\n\n"
            if master_row_count != remote_row_count:
                msg += f"Note: Row counts differ ({master_row_count} master vs {remote_row_count} remote).\n"
                msg += "Only matching rows will be processed.\n\n"
            msg += "Continue?"
            
            reply = QMessageBox.question(self, "Assign Sequences", msg, 
                                       QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply != QMessageBox.StandardButton.Yes:
                return
            
            # Save current table order to preserve it
            self._save_current_table_order()
            
            # First, ensure backend data is in sync with current table order
            self._update_fixture_order_from_tables()
            
            # Transfer sequences row by row
            sequences_assigned = 0
            max_rows = min(master_row_count, remote_row_count)
            
            for row in range(max_rows):
                # Get sequence from master row
                master_seq_item = self.master_fixtures_table.item(row, 3)  # Sequence column is index 3
                if master_seq_item:
                    master_sequence = master_seq_item.text()
                    if master_sequence and master_sequence != "—" and master_sequence != "":
                        # Update remote row sequence
                        remote_seq_item = self.remote_fixtures_table.item(row, 3)
                        if remote_seq_item:
                            remote_seq_item.setText(master_sequence)
                            sequences_assigned += 1
                        
                        # Also update the underlying fixture data
                        remote_fixture_id_item = self.remote_fixtures_table.item(row, 0)
                        remote_attr_item = self.remote_fixtures_table.item(row, 2)
                        if remote_fixture_id_item and remote_attr_item:
                            fixture_id = int(remote_fixture_id_item.text())
                            attr_name = remote_attr_item.text()
                            
                            # Find the fixture in remote_matched_fixtures and update sequence
                            for fixture in self.controller.remote_matched_fixtures:
                                if fixture.fixture_id == fixture_id:
                                    if not hasattr(fixture, 'attribute_sequences') or fixture.attribute_sequences is None:
                                        fixture.attribute_sequences = {}
                                    fixture.attribute_sequences[attr_name] = int(master_sequence)
                                    break
            
            # Update sequence display in tables without rebuilding them
            self._update_sequences_in_place()
            
            # Update the status and mark project as dirty
            self.status_bar.showMessage(f"Assigned {sequences_assigned} sequence numbers from master to remote fixtures")
            self.mark_project_dirty()
            
            # Show completion message
            QMessageBox.information(self, "Sequences Assigned", 
                                  f"Successfully assigned {sequences_assigned} sequence numbers from master to remote fixtures.")
                                  
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error assigning sequences:\n{str(e)}")
            import traceback
            traceback.print_exc()
    
    def _populate_alignment_tables(self, preserve_order=True):
        """Populate the master and remote attribute tables."""
        try:
            # Prevent recursive calls during table population
            if self.table_population_in_progress:
                return
            self.table_population_in_progress = True
            
            # Save current table ordering if preserving order
            if preserve_order:
                self._save_current_table_order()
            
            # Clear existing data
            self.master_fixtures_table.setRowCount(0)
            self.remote_fixtures_table.setRowCount(0)
            
            # Get manual alignments
            manual_alignments = self.controller.get_manual_alignments()
            
            # Populate master attributes table
            master_fixtures = self.controller.master_matched_fixtures
            if master_fixtures:
                master_attribute_rows = []
                
                # Build list of all attribute rows for master fixtures
                for fixture in master_fixtures:
                    if not fixture.is_matched():
                        continue
                        
                    # Get fixture type to determine which attributes to show
                    fixture_type = fixture.gdtf_spec or "Unknown"
                    fixture_type_clean = fixture_type.replace('.gdtf', '') if fixture_type.endswith('.gdtf') else fixture_type
                    fixture_attributes = self.master_fixture_type_attributes.get(fixture_type_clean, [])
                    
                    # Add each attribute as a separate row
                    for attr_name in fixture_attributes:
                        if attr_name in fixture.attribute_offsets:
                            # Get attribute details
                            sequence_num = fixture.get_sequence_for_attribute(attr_name)
                            activation_group = fixture.get_activation_group_for_attribute(attr_name)
                            
                            # Get address info
                            addr_info = fixture.absolute_addresses.get(attr_name, {})
                            universe = addr_info.get("universe", "?")
                            channel = addr_info.get("channel", "?")
                            absolute_address = addr_info.get("absolute_address", "?")
                            
                            # Show routing status
                            routing_status = ""
                            if fixture.fixture_id in manual_alignments:
                                remote_id = manual_alignments[fixture.fixture_id]
                                routing_status = f"→ Fixture {remote_id}"
                            
                            master_attribute_rows.append({
                                'fixture_id': fixture.fixture_id,
                                'fixture_name': fixture.name,
                                'attribute': attr_name,
                                'sequence': sequence_num or "—",
                                'activation_group': activation_group or "—",
                                'universe': universe,
                                'channel': channel,
                                'absolute': absolute_address,
                                'routing': routing_status
                            })
                
                # Set table size and populate rows
                self.master_fixtures_table.setRowCount(len(master_attribute_rows))
                for row, attr_row in enumerate(master_attribute_rows):
                    # Create table items
                    id_item = QTableWidgetItem(str(attr_row['fixture_id']))
                    name_item = QTableWidgetItem(attr_row['fixture_name'])
                    attr_item = QTableWidgetItem(attr_row['attribute'])
                    seq_item = QTableWidgetItem(str(attr_row['sequence']))
                    group_item = QTableWidgetItem(attr_row['activation_group'])
                    universe_item = QTableWidgetItem(str(attr_row['universe']))
                    channel_item = QTableWidgetItem(str(attr_row['channel']))
                    absolute_item = QTableWidgetItem(str(attr_row['absolute']))
                    routing_item = QTableWidgetItem(attr_row['routing'])
                    
                    # Make routing column read-only
                    routing_item.setFlags(routing_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                    
                    # Set items in table
                    self.master_fixtures_table.setItem(row, 0, id_item)
                    self.master_fixtures_table.setItem(row, 1, name_item)
                    self.master_fixtures_table.setItem(row, 2, attr_item)
                    self.master_fixtures_table.setItem(row, 3, seq_item)
                    self.master_fixtures_table.setItem(row, 4, group_item)
                    self.master_fixtures_table.setItem(row, 5, universe_item)
                    self.master_fixtures_table.setItem(row, 6, channel_item)
                    self.master_fixtures_table.setItem(row, 7, absolute_item)
                    self.master_fixtures_table.setItem(row, 8, routing_item)
            
            # Populate remote attributes table
            remote_fixtures = self.controller.remote_matched_fixtures
            if remote_fixtures:
                remote_attribute_rows = []
                
                # Build list of all attribute rows for remote fixtures
                for fixture in remote_fixtures:
                    if not fixture.is_matched():
                        continue
                        
                    # Get fixture type to determine which attributes to show
                    fixture_type = fixture.gdtf_spec or "Unknown"
                    fixture_type_clean = fixture_type.replace('.gdtf', '') if fixture_type.endswith('.gdtf') else fixture_type
                    fixture_attributes = self.remote_fixture_type_attributes.get(fixture_type_clean, [])
                    
                    # Add each attribute as a separate row
                    for attr_name in fixture_attributes:
                        if attr_name in fixture.attribute_offsets:
                            # Get attribute details
                            sequence_num = fixture.get_sequence_for_attribute(attr_name)
                            activation_group = fixture.get_activation_group_for_attribute(attr_name)
                            
                            # Get address info
                            addr_info = fixture.absolute_addresses.get(attr_name, {})
                            universe = addr_info.get("universe", "?")
                            channel = addr_info.get("channel", "?")
                            absolute_address = addr_info.get("absolute_address", "?")
                            
                            # Show routing status
                            routing_status = ""
                            # Check if this remote fixture is linked with any master
                            for master_id, remote_id in manual_alignments.items():
                                if remote_id == fixture.fixture_id:
                                    routing_status = f"← Fixture {master_id}"
                                    break
                            
                            remote_attribute_rows.append({
                                'fixture_id': fixture.fixture_id,
                                'fixture_name': fixture.name,
                                'attribute': attr_name,
                                'sequence': sequence_num or "",  # Show blank sequence for remote fixtures initially
                                'activation_group': activation_group or "—",
                                'universe': universe,
                                'channel': channel,
                                'absolute': absolute_address,
                                'routing': routing_status
                            })
                
                # Set table size and populate rows
                self.remote_fixtures_table.setRowCount(len(remote_attribute_rows))
                for row, attr_row in enumerate(remote_attribute_rows):
                    # Create table items
                    id_item = QTableWidgetItem(str(attr_row['fixture_id']))
                    name_item = QTableWidgetItem(attr_row['fixture_name'])
                    attr_item = QTableWidgetItem(attr_row['attribute'])
                    seq_item = QTableWidgetItem(str(attr_row['sequence']))
                    group_item = QTableWidgetItem(attr_row['activation_group'])
                    universe_item = QTableWidgetItem(str(attr_row['universe']))
                    channel_item = QTableWidgetItem(str(attr_row['channel']))
                    absolute_item = QTableWidgetItem(str(attr_row['absolute']))
                    routing_item = QTableWidgetItem(attr_row['routing'])
                    
                    # Make routing column read-only
                    routing_item.setFlags(routing_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                    
                    # Set items in table
                    self.remote_fixtures_table.setItem(row, 0, id_item)
                    self.remote_fixtures_table.setItem(row, 1, name_item)
                    self.remote_fixtures_table.setItem(row, 2, attr_item)
                    self.remote_fixtures_table.setItem(row, 3, seq_item)
                    self.remote_fixtures_table.setItem(row, 4, group_item)
                    self.remote_fixtures_table.setItem(row, 5, universe_item)
                    self.remote_fixtures_table.setItem(row, 6, channel_item)
                    self.remote_fixtures_table.setItem(row, 7, absolute_item)
                    self.remote_fixtures_table.setItem(row, 8, routing_item)
            
            # Resize columns to fit content
            self.master_fixtures_table.resizeColumnsToContents()
            self.remote_fixtures_table.resizeColumnsToContents()
            
            # Restore table ordering if preserving order
            if preserve_order:
                self._restore_table_order()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error populating alignment tables:\n{str(e)}")
        finally:
            self.table_population_in_progress = False
    
    def _save_current_table_order(self):
        """Save the current table order to preserve user's custom ordering."""
        try:
            # Save master table order
            if hasattr(self, 'master_fixtures_table'):
                self.master_table_order = self._extract_fixture_order_from_table(self.master_fixtures_table)
            
            # Save remote table order
            if hasattr(self, 'remote_fixtures_table'):
                self.remote_table_order = self._extract_fixture_order_from_table(self.remote_fixtures_table)
                
        except Exception as e:
            print(f"Error saving table order: {e}")
    
    def _restore_table_order(self):
        """Restore the saved table order after table repopulation."""
        try:
            # Restore master table order
            if self.master_table_order and hasattr(self, 'master_fixtures_table'):
                self._reorder_table_by_saved_order(self.master_fixtures_table, self.master_table_order)
            
            # Restore remote table order  
            if self.remote_table_order and hasattr(self, 'remote_fixtures_table'):
                self._reorder_table_by_saved_order(self.remote_fixtures_table, self.remote_table_order)
                
        except Exception as e:
            print(f"Error restoring table order: {e}")
    
    def _reorder_table_by_saved_order(self, table, saved_order):
        """Reorder a table to match a saved order of (fixture_id, attribute_name) tuples."""
        if not saved_order:
            return
            
        # Create a mapping of current rows by (fixture_id, attribute)
        current_rows = {}
        for row in range(table.rowCount()):
            fixture_id_item = table.item(row, 0)  # Fixture ID column
            attr_item = table.item(row, 2)        # Attribute column
            
            if fixture_id_item and attr_item:
                try:
                    fixture_id = int(fixture_id_item.text())
                    attr_name = attr_item.text()
                    
                    # Store all items for this row
                    row_items = []
                    for col in range(table.columnCount()):
                        item = table.item(row, col)
                        row_items.append(item.text() if item else "")
                    
                    current_rows[(fixture_id, attr_name)] = row_items
                except (ValueError, AttributeError):
                    continue
        
        # Rebuild table in the saved order
        table.setRowCount(0)
        ordered_rows = []
        
        # Add rows in saved order
        for fixture_id, attr_name in saved_order:
            if (fixture_id, attr_name) in current_rows:
                ordered_rows.append(current_rows[(fixture_id, attr_name)])
        
        # Add any remaining rows that weren't in saved order
        for key, row_data in current_rows.items():
            if key not in saved_order:
                ordered_rows.append(row_data)
        
        # Populate the table with ordered rows
        table.setRowCount(len(ordered_rows))
        for row, row_data in enumerate(ordered_rows):
            for col, cell_text in enumerate(row_data):
                item = QTableWidgetItem(cell_text)
                if col == 8:  # Routing column should be read-only
                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                table.setItem(row, col, item)
    
    def _should_repopulate_tables(self):
        """Determine if tables need to be rebuilt or just updated."""
        try:
            # If tables are empty, we need to populate them
            if (not hasattr(self, 'master_fixtures_table') or 
                not hasattr(self, 'remote_fixtures_table') or
                self.master_fixtures_table.rowCount() == 0 or 
                self.remote_fixtures_table.rowCount() == 0):
                return True
            
            # Check if the number of rows matches expected data
            master_fixtures = self.controller.master_matched_fixtures
            remote_fixtures = self.controller.remote_matched_fixtures
            
            if master_fixtures:
                expected_master_rows = 0
                for fixture in master_fixtures:
                    if fixture.is_matched():
                        fixture_type = fixture.gdtf_spec or "Unknown"
                        fixture_type_clean = fixture_type.replace('.gdtf', '') if fixture_type.endswith('.gdtf') else fixture_type
                        fixture_attributes = self.master_fixture_type_attributes.get(fixture_type_clean, [])
                        expected_master_rows += len([attr for attr in fixture_attributes if attr in fixture.attribute_offsets])
                
                if self.master_fixtures_table.rowCount() != expected_master_rows:
                    return True
            
            if remote_fixtures:
                expected_remote_rows = 0
                for fixture in remote_fixtures:
                    if fixture.is_matched():
                        fixture_type = fixture.gdtf_spec or "Unknown"
                        fixture_type_clean = fixture_type.replace('.gdtf', '') if fixture_type.endswith('.gdtf') else fixture_type
                        fixture_attributes = self.remote_fixture_type_attributes.get(fixture_type_clean, [])
                        expected_remote_rows += len([attr for attr in fixture_attributes if attr in fixture.attribute_offsets])
                
                if self.remote_fixtures_table.rowCount() != expected_remote_rows:
                    return True
                
                # Additional check: Ensure remote fixtures have address data populated
                # If any remote fixture has attributes but no address data, repopulate
                for fixture in remote_fixtures:
                    if fixture.is_matched():
                        fixture_type_clean = (fixture.gdtf_spec or "Unknown").replace('.gdtf', '')
                        fixture_attributes = self.remote_fixture_type_attributes.get(fixture_type_clean, [])
                        for attr_name in fixture_attributes:
                            if attr_name in fixture.attribute_offsets:
                                # Check if this attribute has address data
                                if not fixture.absolute_addresses or attr_name not in fixture.absolute_addresses:
                                    return True
            
            # Tables seem to be in sync, no repopulation needed
            return False
            
        except Exception as e:
            print(f"Error checking if repopulation needed: {e}")
            # When in doubt, repopulate to be safe
            return True
    
    def _update_sequences_in_place(self):
        """Update sequence numbers in tables without rebuilding them."""
        try:
            # Update master table sequences
            for row in range(self.master_fixtures_table.rowCount()):
                fixture_id_item = self.master_fixtures_table.item(row, 0)
                attr_item = self.master_fixtures_table.item(row, 2)
                seq_item = self.master_fixtures_table.item(row, 3)
                
                if fixture_id_item and attr_item and seq_item:
                    fixture_id = int(fixture_id_item.text())
                    attr_name = attr_item.text()
                    
                    # Find the fixture and get current sequence
                    for fixture in self.controller.master_matched_fixtures:
                        if fixture.fixture_id == fixture_id:
                            current_seq = fixture.get_sequence_for_attribute(attr_name)
                            seq_item.setText(str(current_seq) if current_seq else "—")
                            break
            
            # Update remote table sequences
            for row in range(self.remote_fixtures_table.rowCount()):
                fixture_id_item = self.remote_fixtures_table.item(row, 0)
                attr_item = self.remote_fixtures_table.item(row, 2)
                seq_item = self.remote_fixtures_table.item(row, 3)
                
                if fixture_id_item and attr_item and seq_item:
                    fixture_id = int(fixture_id_item.text())
                    attr_name = attr_item.text()
                    
                    # Find the fixture and get current sequence
                    for fixture in self.controller.remote_matched_fixtures:
                        if fixture.fixture_id == fixture_id:
                            current_seq = fixture.get_sequence_for_attribute(attr_name)
                            seq_item.setText(str(current_seq) if current_seq else "")
                            break
                            
        except Exception as e:
            print(f"Error updating sequences in place: {e}")
    
    def _update_alignment_status(self):
        """Update the alignment status label."""
        try:
            manual_alignments = self.controller.get_manual_alignments()
            alignment_count = len(manual_alignments)
            
            if alignment_count > 0:
                self.alignment_status.setText(f"✓ {alignment_count} manual attribute routing(s) set")
                self.alignment_status.setStyleSheet("color: green; font-weight: bold; padding: 10px;")
                self.clear_alignment_btn.setEnabled(True)
            else:
                self.alignment_status.setText("Load Master and Remote fixtures to begin attribute routing")
                self.alignment_status.setStyleSheet("color: gray; font-style: italic; padding: 10px;")
                self.clear_alignment_btn.setEnabled(False)
                
        except Exception as e:
            self.alignment_status.setText(f"Error updating status: {str(e)}")
            self.alignment_status.setStyleSheet("color: red; padding: 10px;")
    
    def on_row_moved(self, from_index, to_index):
        """Handle when a row is moved via drag and drop."""
        # Save the new table order immediately
        self._save_current_table_order()
        
        # Update backend fixture data to match new table order
        self._update_fixture_order_from_tables()
        
        # Mark that the routing has been modified
        self.mark_project_dirty()
        self.status_bar.showMessage(f"Row moved from {from_index} to {to_index}")
    
    def on_rows_moved(self, selected_rows, target_row):
        """Handle when multiple rows are moved via drag and drop."""
        # Save the new table order immediately
        self._save_current_table_order()
        
        # Update backend fixture data to match new table order
        self._update_fixture_order_from_tables()
        
        # Mark that the routing has been modified
        self.mark_project_dirty()
        
        # Create informative status message
        if len(selected_rows) == 1:
            self.status_bar.showMessage(f"Row moved from {selected_rows[0]} to {target_row}")
        else:
            self.status_bar.showMessage(f"{len(selected_rows)} rows moved to position {target_row}")
    
    def _update_fixture_order_from_tables(self):
        """Update backend fixture data to match the current table order."""
        try:
            # Update master fixtures order
            if hasattr(self, 'master_fixtures_table') and self.controller.master_matched_fixtures:
                master_order = self._extract_fixture_order_from_table(self.master_fixtures_table)
                if master_order:
                    self.controller.master_matched_fixtures = self._reorder_fixtures_by_attributes(
                        self.controller.master_matched_fixtures, master_order
                    )
            
            # Update remote fixtures order  
            if hasattr(self, 'remote_fixtures_table') and self.controller.remote_matched_fixtures:
                remote_order = self._extract_fixture_order_from_table(self.remote_fixtures_table)
                if remote_order:
                    self.controller.remote_matched_fixtures = self._reorder_fixtures_by_attributes(
                        self.controller.remote_matched_fixtures, remote_order
                    )
                    
        except Exception as e:
            print(f"Error updating fixture order: {e}")
    
    def _extract_fixture_order_from_table(self, table):
        """Extract the current order of (fixture_id, attribute_name) from a table."""
        order = []
        for row in range(table.rowCount()):
            fixture_id_item = table.item(row, 0)  # Fixture ID column
            attr_item = table.item(row, 2)        # Attribute column
            
            if fixture_id_item and attr_item:
                try:
                    fixture_id = int(fixture_id_item.text())
                    attr_name = attr_item.text()
                    order.append((fixture_id, attr_name))
                except (ValueError, AttributeError):
                    continue
        
        return order
    
    def _reorder_fixtures_by_attributes(self, fixtures, attribute_order):
        """Reorder fixtures based on the order of their attributes in the table."""
        if not attribute_order:
            return fixtures
        
        # Create a map of fixtures by ID for quick lookup
        fixture_map = {fixture.fixture_id: fixture for fixture in fixtures}
        
        # Track which fixtures we've processed and in what order
        processed_fixtures = []
        processed_fixture_ids = set()
        
        # Go through the attribute order and add fixtures in the order they first appear
        for fixture_id, attr_name in attribute_order:
            if fixture_id in fixture_map and fixture_id not in processed_fixture_ids:
                processed_fixtures.append(fixture_map[fixture_id])
                processed_fixture_ids.add(fixture_id)
        
        # Add any remaining fixtures that weren't in the table (shouldn't happen, but just in case)
        for fixture in fixtures:
            if fixture.fixture_id not in processed_fixture_ids:
                processed_fixtures.append(fixture)
        
        return processed_fixtures
    
    def on_row_inserted(self, row_index):
        """Handle when an empty row is inserted."""
        # Save the new table order immediately
        self._save_current_table_order()
        
        # Update backend fixture data to match new table order
        self._update_fixture_order_from_tables()
        
        self.status_bar.showMessage(f"Empty row inserted at position {row_index}")
        # Mark that the routing has been modified
        self.mark_project_dirty()
    
    def on_row_deleted(self, row_index):
        """Handle when a row is deleted."""
        # Save the new table order immediately
        self._save_current_table_order()
        
        # Update backend fixture data to match new table order
        self._update_fixture_order_from_tables()
        
        self.status_bar.showMessage(f"Row deleted at position {row_index}")
        # Mark that the routing has been modified
        self.mark_project_dirty()
    
    def add_master_row(self):
        """Add an empty row to the master fixtures table."""
        row_count = self.master_fixtures_table.rowCount()
        self.master_fixtures_table.insertRow(row_count)
        
        # Set default values for empty row
        self.master_fixtures_table.setItem(row_count, 0, QTableWidgetItem(""))  # ID
        self.master_fixtures_table.setItem(row_count, 1, QTableWidgetItem(""))  # Name
        self.master_fixtures_table.setItem(row_count, 2, QTableWidgetItem(""))  # Type
        self.master_fixtures_table.setItem(row_count, 3, QTableWidgetItem(""))  # Mode
        self.master_fixtures_table.setItem(row_count, 4, QTableWidgetItem(""))  # Base Address
        
        # Set routing column as read-only
        routing_item = QTableWidgetItem("")
        routing_item.setFlags(routing_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        self.master_fixtures_table.setItem(row_count, 5, routing_item)
        
        # Select the new row
        self.master_fixtures_table.selectRow(row_count)
        
        self.status_bar.showMessage("Empty master row added")
        self.mark_project_dirty()
    
    def add_remote_row(self):
        """Add an empty row to the remote fixtures table."""
        row_count = self.remote_fixtures_table.rowCount()
        self.remote_fixtures_table.insertRow(row_count)
        
        # Set default values for empty row
        self.remote_fixtures_table.setItem(row_count, 0, QTableWidgetItem(""))  # ID
        self.remote_fixtures_table.setItem(row_count, 1, QTableWidgetItem(""))  # Name
        self.remote_fixtures_table.setItem(row_count, 2, QTableWidgetItem(""))  # Type
        self.remote_fixtures_table.setItem(row_count, 3, QTableWidgetItem(""))  # Mode
        self.remote_fixtures_table.setItem(row_count, 4, QTableWidgetItem(""))  # Base Address
        
        # Set routing column as read-only
        routing_item = QTableWidgetItem("")
        routing_item.setFlags(routing_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        self.remote_fixtures_table.setItem(row_count, 5, routing_item)
        
        # Select the new row
        self.remote_fixtures_table.selectRow(row_count)
        
        self.status_bar.showMessage("Empty remote row added")
        self.mark_project_dirty()
    
    def _populate_alignment_results_tree(self, alignment_result: dict):
        """Populate the alignment results tree with alignment data."""
        if not alignment_result or not alignment_result.get("success"):
            self._show_error_in_alignment_tree("Alignment failed")
            return
        
        alignment_results = alignment_result.get("alignment_results", [])
        if not alignment_results:
            self._show_error_in_alignment_tree("No alignment results to display")
            return
        
        # Clear the tree
        self.alignment_results_tree.clear()
        
        # Sort results by alignment status and confidence
        sorted_results = sorted(
            alignment_results, 
            key=lambda x: (
                0 if x["alignment_status"] == "matched" else 
                1 if x["alignment_status"] == "unmatched" else 2,
                -x["confidence"]
            )
        )
        
        for result in sorted_results:
            # Create alignment item
            alignment_item = QTreeWidgetItem()
            
            # Master fixture info
            if result["master_fixture"]:
                master_name = result["master_fixture"].name
                master_type = getattr(result["master_fixture"], 'gdtf_spec', 'Unknown') or 'Unknown'
            else:
                master_name = "—"
                master_type = "—"
            
            # Remote fixture info
            if result["remote_fixture"]:
                remote_name = result["remote_fixture"].name
                remote_type = getattr(result["remote_fixture"], 'gdtf_spec', 'Unknown') or 'Unknown'
            else:
                remote_name = "—"
                remote_type = "—"
            
            # Set alignment item data
            alignment_item.setText(0, master_name)
            alignment_item.setText(1, remote_name)
            alignment_item.setText(2, result["alignment_status"].replace("_", " ").title())
            alignment_item.setText(3, f"{result['confidence']:.2%}")
            alignment_item.setText(4, result["notes"])
            
            # Set styling based on alignment status
            if result["alignment_status"] == "matched":
                alignment_item.setForeground(0, QColor("darkgreen"))
                alignment_item.setForeground(1, QColor("darkgreen"))
                alignment_item.setForeground(2, QColor("darkgreen"))
            elif result["alignment_status"] == "unmatched":
                alignment_item.setForeground(0, QColor("orange"))
                alignment_item.setForeground(2, QColor("orange"))
            else:  # unmatched_remote
                alignment_item.setForeground(1, QColor("red"))
                alignment_item.setForeground(2, QColor("red"))
            
            # Add to tree
            self.alignment_results_tree.addTopLevelItem(alignment_item)
        
        # Resize columns to fit content
        for i in range(self.alignment_results_tree.columnCount()):
            self.alignment_results_tree.resizeColumnToContents(i)
    
    def _show_error_in_alignment_tree(self, error_message: str):
        """Show an error message in the alignment tree."""
        self.alignment_results_tree.clear()
        
        error_item = QTreeWidgetItem()
        error_item.setText(0, error_message)
        error_item.setForeground(0, QColor("red"))
        
        # Set bold font
        font = QFont()
        font.setBold(True)
        error_item.setFont(0, font)
        
        self.alignment_results_tree.addTopLevelItem(error_item)
        
        # Resize to fit content
        self.alignment_results_tree.resizeColumnToContents(0)
    
    def _populate_master_results_tree(self, analysis_results: dict):
        """Populate the master results tree with hierarchical analysis data."""
        if not analysis_results or not analysis_results.get("success"):
            self._show_error_in_master_tree("Master analysis failed")
            return
        
        results = analysis_results.get("analysis_results")
        if not results:
            self._show_error_in_master_tree("No master analysis results")
            return
        
        fixtures = results.fixtures
        if not fixtures:
            self._show_error_in_master_tree("No master fixtures to display")
            return
        
        # Clear the tree
        self.master_results_tree.clear()
        
        # Sort fixtures by fixture_id
        sorted_fixtures = sorted([f for f in fixtures if f.is_matched()], key=lambda x: x.fixture_id)
        
        for fixture in sorted_fixtures:
            # Create fixture parent item
            fixture_type = fixture.gdtf_spec or "Unknown"
            if fixture_type.endswith('.gdtf'):
                fixture_type = fixture_type[:-5]
            
            # Get fixture type to determine which attributes to show
            fixture_type_clean = fixture_type.replace('.gdtf', '') if fixture_type.endswith('.gdtf') else fixture_type
            fixture_attributes = self.master_fixture_type_attributes.get(fixture_type_clean, [])
            
            # Create fixture item with summary info
            fixture_item = QTreeWidgetItem()
            fixture_item.setText(0, f"Master Fixture {fixture.fixture_id}: {fixture.name}")
            fixture_item.setText(1, "FIXTURE")
            fixture_item.setText(2, fixture_type)
            fixture_item.setText(3, str(fixture.base_address))
            fixture_item.setText(4, fixture.gdtf_mode or "")
            fixture_item.setText(5, "—")  # No fixture-level ActivationGroup anymore
            
            # Set fixture item styling
            font = QFont()
            font.setBold(True)
            fixture_item.setFont(0, font)
            fixture_item.setForeground(0, QColor("darkblue"))
            
            # Add attribute child items
            if hasattr(fixture, 'absolute_addresses') and fixture.absolute_addresses:
                for attr_name in fixture_attributes:
                    if attr_name in fixture.absolute_addresses:
                        addr_info = fixture.absolute_addresses[attr_name]
                        universe = addr_info.get("universe", "?")
                        channel = addr_info.get("channel", "?")
                        absolute_address = addr_info.get("absolute_address", "?")
                        
                        attr_item = QTreeWidgetItem()
                        attr_item.setText(0, f"  └─ {attr_name}")
                        attr_item.setText(1, "ATTRIBUTE")
                        attr_item.setText(2, "—")
                        attr_item.setText(3, "—")
                        attr_item.setText(4, "—")
                        # Get ActivationGroup for this attribute
                        activation_group = fixture.get_activation_group_for_attribute(attr_name)
                        attr_item.setText(5, activation_group if activation_group else "—")
                        # Get sequence number for this attribute
                        sequence_num = fixture.get_sequence_for_attribute(attr_name)
                        attr_item.setText(6, str(sequence_num) if sequence_num else "—")
                        attr_item.setText(7, str(universe))
                        attr_item.setText(8, str(channel))
                        attr_item.setText(9, str(absolute_address))
                        
                        fixture_item.addChild(attr_item)
            
            # If no attributes, add a placeholder
            if fixture_item.childCount() == 0:
                no_attr_item = QTreeWidgetItem()
                no_attr_item.setText(0, "No attributes selected")
                no_attr_item.setForeground(0, QColor("gray"))
                
                font = QFont()
                font.setItalic(True)
                no_attr_item.setFont(0, font)
                
                fixture_item.addChild(no_attr_item)
            
            # Add fixture to tree
            self.master_results_tree.addTopLevelItem(fixture_item)
            
            # Expand the fixture to show attributes
            fixture_item.setExpanded(True)
        
        # Resize columns to fit content
        for i in range(self.master_results_tree.columnCount()):
            self.master_results_tree.resizeColumnToContents(i)
    
    def _populate_remote_results_tree(self, analysis_results: dict):
        """Populate the remote results tree with hierarchical analysis data."""
        if not analysis_results or not analysis_results.get("success"):
            self._show_error_in_remote_tree("Remote analysis failed")
            return
        
        results = analysis_results.get("analysis_results")
        if not results:
            self._show_error_in_remote_tree("No remote analysis results")
            return
        
        fixtures = results.fixtures
        if not fixtures:
            self._show_error_in_remote_tree("No remote fixtures to display")
            return
        
        # Clear the tree
        self.remote_results_tree.clear()
        
        # Sort fixtures by fixture_id
        sorted_fixtures = sorted([f for f in fixtures if f.is_matched()], key=lambda x: x.fixture_id)
        
        for fixture in sorted_fixtures:
            # Create fixture parent item
            fixture_type = fixture.gdtf_spec or "Unknown"
            if fixture_type.endswith('.gdtf'):
                fixture_type = fixture_type[:-5]
            
            # Get fixture type to determine which attributes to show
            fixture_type_clean = fixture_type.replace('.gdtf', '') if fixture_type.endswith('.gdtf') else fixture_type
            fixture_attributes = self.remote_fixture_type_attributes.get(fixture_type_clean, [])
            
            # Create fixture item with summary info
            fixture_item = QTreeWidgetItem()
            fixture_item.setText(0, f"Remote Fixture {fixture.fixture_id}: {fixture.name}")
            fixture_item.setText(1, "FIXTURE")
            fixture_item.setText(2, fixture_type)
            fixture_item.setText(3, str(fixture.base_address))
            fixture_item.setText(4, fixture.gdtf_mode or "")
            fixture_item.setText(5, "—")  # No fixture-level ActivationGroup anymore
            
            # Set fixture item styling
            font = QFont()
            font.setBold(True)
            fixture_item.setFont(0, font)
            fixture_item.setForeground(0, QColor("darkorange"))
            
            # Add attribute child items
            if hasattr(fixture, 'absolute_addresses') and fixture.absolute_addresses:
                for attr_name in fixture_attributes:
                    if attr_name in fixture.absolute_addresses:
                        addr_info = fixture.absolute_addresses[attr_name]
                        universe = addr_info.get("universe", "?")
                        channel = addr_info.get("channel", "?")
                        absolute_address = addr_info.get("absolute_address", "?")
                        
                        attr_item = QTreeWidgetItem()
                        attr_item.setText(0, f"  └─ {attr_name}")
                        attr_item.setText(1, "ATTRIBUTE")
                        attr_item.setText(2, "—")
                        attr_item.setText(3, "—")
                        attr_item.setText(4, "—")
                        # Get ActivationGroup for this attribute
                        activation_group = fixture.get_activation_group_for_attribute(attr_name)
                        attr_item.setText(5, activation_group if activation_group else "—")
                        # Get sequence number for this attribute
                        sequence_num = fixture.get_sequence_for_attribute(attr_name)
                        attr_item.setText(6, str(sequence_num) if sequence_num else "—")
                        attr_item.setText(7, str(universe))
                        attr_item.setText(8, str(channel))
                        attr_item.setText(9, str(absolute_address))
                        
                        fixture_item.addChild(attr_item)
            
            # If no attributes, add a placeholder
            if fixture_item.childCount() == 0:
                no_attr_item = QTreeWidgetItem()
                no_attr_item.setText(0, "No attributes selected")
                no_attr_item.setForeground(0, QColor("gray"))
                
                font = QFont()
                font.setItalic(True)
                no_attr_item.setFont(0, font)
                
                fixture_item.addChild(no_attr_item)
            
            # Add fixture to tree
            self.remote_results_tree.addTopLevelItem(fixture_item)
            
            # Expand the fixture to show attributes
            fixture_item.setExpanded(True)
        
        # Resize columns to fit content
        for i in range(self.remote_results_tree.columnCount()):
            self.remote_results_tree.resizeColumnToContents(i)
    
    def _show_error_in_master_tree(self, error_message: str):
        """Show an error message in the master results tree."""
        self.master_results_tree.clear()
        
        error_item = QTreeWidgetItem()
        error_item.setText(0, error_message)
        error_item.setForeground(0, QColor("red"))
        
        # Set bold font
        font = QFont()
        font.setBold(True)
        error_item.setFont(0, font)
        
        self.master_results_tree.addTopLevelItem(error_item)
        
        # Resize to fit content
        self.master_results_tree.resizeColumnToContents(0)
    
    def _show_error_in_remote_tree(self, error_message: str):
        """Show an error message in the remote results tree."""
        self.remote_results_tree.clear()
        
        error_item = QTreeWidgetItem()
        error_item.setText(0, error_message)
        error_item.setForeground(0, QColor("red"))
        
        # Set bold font
        font = QFont()
        font.setBold(True)
        error_item.setFont(0, font)
        
        self.remote_results_tree.addTopLevelItem(error_item)
        
        # Resize to fit content
        self.remote_results_tree.resizeColumnToContents(0)
    
    def update_progress(self, message: str):
        """Update progress message."""
        self.status_bar.showMessage(message)
    
    def analysis_complete(self, result: dict):
        """Legacy method - analysis is now handled per tab."""
        pass
    
    def analysis_error(self, error: str):
        """Legacy method - analysis is now handled per tab.""" 
        pass
    
    def master_analysis_complete(self, result: dict):
        """Handle successful master analysis completion."""
        self.master_worker = None
        
        # Store results
        self.master_results = result
        
        # Update UI
        self._populate_master_results_tree(result)
        
        # Show summary
        summary = result.get("summary", {})
        total_fixtures = summary.get("total_fixtures", 0)
        matched_fixtures = summary.get("matched_fixtures", 0)
        conflicts = len(summary.get("conflicts", []))
        
        status_msg = f"Master analysis complete: {matched_fixtures}/{total_fixtures} fixtures analyzed"
        if conflicts > 0:
            status_msg += f", {conflicts} conflicts"
        
        self.status_bar.showMessage(status_msg)
        
        # Force update of routing tables to reflect new address data
        if hasattr(self, 'remote_results') and self.remote_results is not None:
            # Force repopulation of alignment tables to ensure address data is current
            self._populate_alignment_tables(preserve_order=True)
        
        # Update UI state
        self.update_ui_state()
    
    def master_analysis_error(self, error: str):
        """Handle master analysis error."""
        self.master_worker = None
        
        # Clear results
        self.master_results = None
        
        # Show error in tree
        self._show_error_in_master_tree(f"Master analysis error: {error}")
        
        # Update status
        self.status_bar.showMessage("Master analysis failed")
        
        # Show error dialog
        QMessageBox.critical(self, "Master Analysis Error", f"Failed to analyze master fixtures:\n{error}")
        
        # Update UI state
        self.update_ui_state()
    
    def remote_analysis_complete(self, result: dict):
        """Handle successful remote analysis completion."""
        self.remote_worker = None
        
        # Store results
        self.remote_results = result
        
        # Update UI
        self._populate_remote_results_tree(result)
        
        # Show summary
        summary = result.get("summary", {})
        total_fixtures = summary.get("total_fixtures", 0)
        matched_fixtures = summary.get("matched_fixtures", 0)
        conflicts = len(summary.get("conflicts", []))
        
        status_msg = f"Remote analysis complete: {matched_fixtures}/{total_fixtures} fixtures analyzed"
        if conflicts > 0:
            status_msg += f", {conflicts} conflicts"
        
        self.status_bar.showMessage(status_msg)
        
        # Force update of routing tables to reflect new address data
        if hasattr(self, 'master_results') and self.master_results is not None:
            # Force repopulation of alignment tables to ensure address data is current
            self._populate_alignment_tables(preserve_order=True)
        
        # Update UI state
        self.update_ui_state()
    
    def remote_analysis_error(self, error: str):
        """Handle remote analysis error."""
        self.remote_worker = None
        
        # Clear results
        self.remote_results = None
        
        # Show error in tree
        self._show_error_in_remote_tree(f"Remote analysis error: {error}")
        
        # Update status
        self.status_bar.showMessage("Remote analysis failed")
        
        # Show error dialog
        QMessageBox.critical(self, "Remote Analysis Error", f"Failed to analyze remote fixtures:\n{error}")
        
        # Update UI state
        self.update_ui_state()
    
    def on_format_changed(self, format_name: str):
        """Handle output format change."""
        # Show/hide MA3 XML configuration button (only needed for DMX remotes, not sequences)
        self.ma3_config_btn.setVisible(format_name == "ma3_xml")
        
        # If switching to MA3 XML and no config exists, load from saved config
        # Only do this for user-initiated changes, not during project loading
        if format_name == "ma3_xml" and self.ma3_config is None:
            self.ma3_config = self.config.get_ma3_xml_config()
            
        # Update config file and mark project as dirty if this is a user-initiated change
        # (Don't update during loading when signals are blocked)
        if not self.format_combo.signalsBlocked():
            self.config.set_output_format(format_name)  # Save to config file
            self.mark_project_dirty()
            
            # Trigger re-analysis if format change affects analysis
            if self.current_results:
                self._trigger_automatic_analysis()
    
    def configure_ma3_xml(self):
        """Open MA3 XML configuration dialog."""
        dialog = MA3XMLDialog(self, self.config)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.ma3_config = dialog.get_config()
            self.mark_project_dirty()  # Mark project as dirty when MA3 config changes
            
            # Trigger re-analysis if MA3 config changes affect analysis
            if self.current_results and self.format_combo.currentText() == "ma3_xml":
                self._trigger_automatic_analysis()
            QMessageBox.information(
                self,
                "Configuration Saved",
                "MA3 XML settings have been configured and saved."
            )
    
    def mark_project_dirty(self):
        """Mark the project as having unsaved changes."""
        self.project_dirty = True
        self.update_window_title()
        self.update_ui_state()
    
    def update_window_title(self):
        """Update the window title to reflect current project state."""
        base_title = "AttributeAddresser"
        
        if self.current_project_path:
            project_name = Path(self.current_project_path).stem
            if self.project_dirty:
                base_title = f"{base_title} - {project_name} *"
            else:
                base_title = f"{base_title} - {project_name}"
        elif self.project_dirty:
            base_title = f"{base_title} *"
        
        self.setWindowTitle(base_title)
    
    def show_about(self):
        """Show the About dialog."""
        QMessageBox.about(
            self,
            "About AttributeAddresser",
            "AttributeAddresser v1.0\n\n"
            "A professional tool for analyzing MVR files and extracting fixture addresses.\n\n"
            "Features:\n"
            "• MVR file analysis\n"
            "• GDTF profile matching\n"
            "• DMX address calculation\n"
            "• Multiple export formats\n"
            "• MA3 XML remote generation\n"
            "• Global sequence numbering\n\n"
            "© 2025 AttributeAddresser"
        )
    
    def show_settings(self):
        """Show settings dialog."""
        try:
            dialog = SettingsDialog(self, self.config)
            dialog.exec()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error opening settings dialog:\n{str(e)}")
    
    def new_project(self):
        """Create a new project."""
        if self.project_dirty:
            reply = QMessageBox.question(
                self, "Unsaved Changes",
                "You have unsaved changes. Do you want to save the current project first?",
                QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel
            )
            
            if reply == QMessageBox.StandardButton.Save:
                if not self.save_project():
                    return  # Save was cancelled
            elif reply == QMessageBox.StandardButton.Cancel:
                return
        
        # Reset all state
        self.current_project_path = None
        self.project_dirty = False
        self.fixture_type_attributes = {}
        self.ma3_config = None
        self.current_results = None
        
        # Reset master/remote state
        self.master_fixture_type_attributes = {}
        self.remote_fixture_type_attributes = {}
        self.master_results = None
        self.remote_results = None
        
        # Reset project timestamps
        if hasattr(self, 'project_created_timestamp'):
            delattr(self, 'project_created_timestamp')
        
        # Reset controller state
        self.controller = MVRController()
        
        # Reset UI dropdowns and controls
        self.format_combo.blockSignals(True)
        self.format_combo.setCurrentText(self.config.get_output_format())  # Reset to default format
        self.format_combo.blockSignals(False)
        self.ma3_config_btn.setVisible(self.format_combo.currentText() == "ma3_xml")
        
        # Reset other UI elements
        self.file_label.setText("No file selected")
        self.file_label.setStyleSheet("padding: 10px; border: 1px solid #ccc; border-radius: 4px;")
        self.gdtf_status_label.setText("Load a file first")
        self.gdtf_status_label.setStyleSheet("color: gray; font-style: italic; padding: 5px;")
        self.attribute_status_label.setText("Complete steps 1-2 first")
        self.attribute_status_label.setStyleSheet("color: gray; font-style: italic; padding: 5px;")
        self._clear_results_tree()
        
        # Reset import type to MVR
        self.mvr_radio.setChecked(True)
        self.update_browse_button()
        
        self.update_ui_state()
        self.update_window_title()
        self.status_bar.showMessage("New project created")
    
    def load_project(self):
        """Load a project from file."""
        if self.project_dirty:
            reply = QMessageBox.question(
                self, "Unsaved Changes",
                "You have unsaved changes. Do you want to save the current project first?",
                QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel
            )
            
            if reply == QMessageBox.StandardButton.Save:
                if not self.save_project():
                    return  # Save was cancelled
            elif reply == QMessageBox.StandardButton.Cancel:
                return
        
        # Get project file path
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Load Project",
            "",
            "AttributeAddresser Project Files (*.aap);;All Files (*)"
        )
        
        if file_path:
            self.load_project_file(file_path)
    
    def save_project(self) -> bool:
        """Save the current project. Returns True if successful."""
        if self.current_project_path:
            return self.save_project_file(self.current_project_path)
        else:
            return self.save_project_as()
    
    def save_project_as(self) -> bool:
        """Save the project with a new name. Returns True if successful."""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Project As",
            "",
            "AttributeAddresser Project Files (*.aap);;All Files (*)"
        )
        
        if file_path:
            if not file_path.endswith('.aap'):
                file_path += '.aap'
            return self.save_project_file(file_path)
        
        return False
    
    def load_project_file(self, file_path: str):
        """Load project state from file."""
        try:
            import json
            with open(file_path, 'r') as f:
                project_data = json.load(f)
            
            # Validate project data version
            version = project_data.get('version', '1.0')
            if version not in ['1.0', '2.0']:
                QMessageBox.warning(self, "Invalid Project", f"This project file format (version {version}) is not supported.")
                return
            
            # Load external GDTF profiles first if specified
            external_gdtf_folder = project_data.get('external_gdtf_folder')
            if external_gdtf_folder:
                resolved_gdtf_folder = self._resolve_path_from_project(external_gdtf_folder, file_path)
                if resolved_gdtf_folder and os.path.exists(resolved_gdtf_folder):
                    self._load_external_gdtf_profiles(resolved_gdtf_folder)
                elif resolved_gdtf_folder:  # Path specified but folder doesn't exist
                    # For missing GDTF folder, just show a warning but continue loading
                    QMessageBox.warning(
                        self, "GDTF Folder Not Found",
                        f"The external GDTF folder was not found at:\n{resolved_gdtf_folder}\n\nYou can set it again in the GDTF settings."
                    )
            
            # Handle version 2.0 project files with master/remote data
            if version == '2.0':
                # Load master file if specified
                master_loaded = False
                if project_data.get('master_file_path'):
                    master_path = self._resolve_path_from_project(project_data['master_file_path'], file_path)
                    if master_path and os.path.exists(master_path):
                        self.load_master_file(master_path)
                        master_loaded = True
                    elif master_path:  # Path specified but file doesn't exist
                        file_types = "MVR Files (*.mvr);;CSV Files (*.csv);;All Files (*)"
                        new_master_path = self._prompt_for_missing_file("Master File", master_path, file_types)
                        if new_master_path:
                            self.load_master_file(new_master_path)
                            master_loaded = True
                            # Update controller path to new location
                            self.controller.master_file_path = new_master_path
                            self.mark_project_dirty()  # Mark as dirty since path changed
                
                # Apply master fixture type matches
                if master_loaded:
                    master_fixture_type_matches = project_data.get('master_fixture_type_matches')
                    if master_fixture_type_matches:
                        result = self.controller.update_master_fixture_matches(master_fixture_type_matches)
                        if not result["success"]:
                            self.status_bar.showMessage("Warning: Could not restore all master fixture matches")
                
                # Load remote file if specified
                remote_loaded = False
                if project_data.get('remote_file_path'):
                    remote_path = self._resolve_path_from_project(project_data['remote_file_path'], file_path)
                    if remote_path and os.path.exists(remote_path):
                        self.load_remote_file(remote_path)
                        remote_loaded = True
                    elif remote_path:  # Path specified but file doesn't exist
                        file_types = "MVR Files (*.mvr);;CSV Files (*.csv);;All Files (*)"
                        new_remote_path = self._prompt_for_missing_file("Remote File", remote_path, file_types)
                        if new_remote_path:
                            self.load_remote_file(new_remote_path)
                            remote_loaded = True
                            # Update controller path to new location
                            self.controller.remote_file_path = new_remote_path
                            self.mark_project_dirty()  # Mark as dirty since path changed
                
                # Apply remote fixture type matches
                if remote_loaded:
                    remote_fixture_type_matches = project_data.get('remote_fixture_type_matches')
                    if remote_fixture_type_matches:
                        result = self.controller.update_remote_fixture_matches(remote_fixture_type_matches)
                        if not result["success"]:
                            self.status_bar.showMessage("Warning: Could not restore all remote fixture matches")
                
                # Restore master and remote fixture type attributes
                self.master_fixture_type_attributes = project_data.get('master_fixture_type_attributes', {})
                self.remote_fixture_type_attributes = project_data.get('remote_fixture_type_attributes', {})
                
                # Restore alignment data
                self.controller.alignment_results = project_data.get('alignment_results')
                self.controller.manual_alignments = project_data.get('manual_alignments', {})
                self.controller.alignment_mode = project_data.get('alignment_mode', 'automatic')
                
                # Restore table ordering
                self.master_table_order = project_data.get('master_table_order', [])
                self.remote_table_order = project_data.get('remote_table_order', [])
                
                # Restore UI state
                if 'current_tab_index' in project_data:
                    self.tab_widget.setCurrentIndex(project_data['current_tab_index'])
                
                # Restore window geometry
                window_geometry = project_data.get('window_geometry')
                if window_geometry:
                    self.setGeometry(
                        window_geometry['x'],
                        window_geometry['y'],
                        window_geometry['width'],
                        window_geometry['height']
                    )
                
                # Restore project timestamps
                self.project_created_timestamp = project_data.get('created_timestamp')
                
            else:
                # Handle version 1.0 project files (backward compatibility)
                # Load MVR file if specified
                mvr_loaded = False
                if project_data.get('mvr_file_path'):
                    mvr_path = self._resolve_path_from_project(project_data['mvr_file_path'], file_path)
                    if mvr_path and os.path.exists(mvr_path):
                        self.load_mvr_file(mvr_path)
                        mvr_loaded = True
                    elif mvr_path:  # Path specified but file doesn't exist
                        file_types = "MVR Files (*.mvr);;All Files (*)"
                        new_mvr_path = self._prompt_for_missing_file("MVR File", mvr_path, file_types)
                        if new_mvr_path:
                            self.load_mvr_file(new_mvr_path)
                            mvr_loaded = True
                            # Update controller path to new location
                            self.controller.current_file_path = new_mvr_path
                            self.mark_project_dirty()  # Mark as dirty since path changed
                
                # Apply saved fixture type matches for version 1.0
                if mvr_loaded:
                    fixture_type_matches = project_data.get('fixture_type_matches')
                    if fixture_type_matches:
                        result = self.controller.update_fixture_matches(fixture_type_matches)
                        if result["success"]:
                            self._update_gdtf_status(result["matched_fixtures"], result["total_fixtures"])
                        else:
                            self.status_bar.showMessage("Warning: Could not restore all fixture matches")
            
            # Restore other project state (common to both versions)
            self.fixture_type_attributes = project_data.get('fixture_type_attributes', {})
            self.ma3_config = project_data.get('ma3_config')
            
            # Restore output format without triggering events during loading
            if 'output_format' in project_data:
                # Temporarily block signals to prevent format change events during loading
                self.format_combo.blockSignals(True)
                self.format_combo.setCurrentText(project_data['output_format'])
                self.format_combo.blockSignals(False)
                
                # Manually update the MA3 config button visibility after loading
                format_name = project_data['output_format']
                self.ma3_config_btn.setVisible(format_name == "ma3_xml")
            
            # Set project path and clear dirty flag
            self.current_project_path = file_path
            self.project_dirty = False
            
            # Add to recent projects
            self.add_to_recent_projects(file_path)
            
            # Update UI
            self.update_ui_state()
            self.update_window_title()
            
            # Show informative status message about project loading
            relocated_files = []
            resolved_relative_paths = False
            
            if version == '2.0':
                # Check if any files were relocated by user
                if project_data.get('master_file_path') and self.controller.master_file_path:
                    original_path = self._resolve_path_from_project(project_data['master_file_path'], file_path)
                    if original_path != project_data.get('master_file_path'):
                        resolved_relative_paths = True
                    if self.controller.master_file_path != original_path:
                        relocated_files.append("master")
                        
                if project_data.get('remote_file_path') and self.controller.remote_file_path:
                    original_path = self._resolve_path_from_project(project_data['remote_file_path'], file_path)
                    if original_path != project_data.get('remote_file_path'):
                        resolved_relative_paths = True
                    if self.controller.remote_file_path != original_path:
                        relocated_files.append("remote")
            else:
                # Version 1.0 legacy handling
                if project_data.get('mvr_file_path') and self.controller.current_file_path:
                    original_path = self._resolve_path_from_project(project_data['mvr_file_path'], file_path)
                    if original_path != project_data.get('mvr_file_path'):
                        resolved_relative_paths = True
                    if self.controller.current_file_path != original_path:
                        relocated_files.append("MVR")
            
            # Create appropriate status message
            if relocated_files:
                self.status_bar.showMessage(f"Project loaded: {Path(file_path).name} (relocated {', '.join(relocated_files)} files)")
            elif resolved_relative_paths:
                self.status_bar.showMessage(f"Project loaded: {Path(file_path).name} (resolved relative paths)")
            else:
                self.status_bar.showMessage(f"Project loaded: {Path(file_path).name}")
            
        except Exception as e:
            QMessageBox.critical(self, "Load Error", f"Failed to load project:\n{str(e)}")
    
    def _make_path_relative(self, absolute_path: str, project_file_path: str) -> str:
        """Convert absolute path to relative path from project file location."""
        try:
            if not absolute_path:
                return ""
            
            project_dir = Path(project_file_path).parent
            target_path = Path(absolute_path)
            
            # Try to make it relative, fall back to absolute if not possible
            try:
                relative_path = target_path.relative_to(project_dir)
                return str(relative_path)
            except ValueError:
                # Paths are on different drives or too far apart, keep absolute
                return absolute_path
                
        except Exception:
            # Any error, return original path
            return absolute_path
    
    def _resolve_path_from_project(self, stored_path: str, project_file_path: str) -> str:
        """Resolve a stored path (relative or absolute) to absolute path."""
        try:
            if not stored_path:
                return ""
            
            # If it's already absolute and exists, use it
            if Path(stored_path).is_absolute() and Path(stored_path).exists():
                return stored_path
            
            # Try to resolve as relative to project file
            project_dir = Path(project_file_path).parent
            resolved_path = project_dir / stored_path
            
            if resolved_path.exists():
                return str(resolved_path.resolve())
            
            # If relative path doesn't work, try the original path
            if Path(stored_path).exists():
                return str(Path(stored_path).resolve())
            
            # Path doesn't exist, return as-is for error handling
            return stored_path
            
        except Exception:
            # Any error, return original path
            return stored_path
    
    def _prompt_for_missing_file(self, file_description: str, original_path: str, file_types: str = "All Files (*)") -> str:
        """Prompt user to locate a missing file."""
        reply = QMessageBox.question(
            self, f"{file_description} Not Found",
            f"The {file_description.lower()} '{Path(original_path).name}' was not found at:\n{original_path}\n\nDo you want to locate it?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            new_path, _ = QFileDialog.getOpenFileName(
                self, f"Locate {file_description}", str(Path(original_path).name), file_types
            )
            return new_path if new_path else ""
        
        return ""

    def save_project_file(self, file_path: str) -> bool:
        """Save project state to file. Returns True if successful."""
        try:
            import json
            
            # Collect essential project data with relative paths for transferability
            project_data = {
                'version': '2.0',  # Updated version for expanded data structure
                
                # Legacy single-dataset support (for backward compatibility)
                'mvr_file_path': self._make_path_relative(self.controller.current_file_path, file_path),
                'fixture_type_attributes': self.fixture_type_attributes,
                'fixture_type_matches': self.controller.get_current_fixture_type_matches(),
                
                # Master dataset
                'master_file_path': self._make_path_relative(self.controller.master_file_path, file_path),
                'master_import_type': self.controller.master_import_type,
                'master_fixture_type_attributes': getattr(self, 'master_fixture_type_attributes', {}),
                'master_fixture_type_matches': self.controller.get_current_master_fixture_type_matches(),
                
                # Remote dataset  
                'remote_file_path': self._make_path_relative(self.controller.remote_file_path, file_path),
                'remote_import_type': self.controller.remote_import_type,
                'remote_fixture_type_attributes': getattr(self, 'remote_fixture_type_attributes', {}),
                'remote_fixture_type_matches': self.controller.get_current_remote_fixture_type_matches(),
                
                # Alignment data
                'alignment_results': self.controller.alignment_results,
                'manual_alignments': self.controller.manual_alignments,
                'alignment_mode': self.controller.alignment_mode,
                
                # Table ordering preservation
                'master_table_order': getattr(self, 'master_table_order', []),
                'remote_table_order': getattr(self, 'remote_table_order', []),
                
                # Configuration and settings
                'external_gdtf_folder': self._make_path_relative(self.config.get_external_gdtf_folder(), file_path),
                'ma3_config': self.ma3_config,
                'output_format': self.format_combo.currentText(),
                
                # UI state
                'current_tab_index': self.tab_widget.currentIndex(),
                'window_geometry': {
                    'x': self.geometry().x(),
                    'y': self.geometry().y(),
                    'width': self.geometry().width(),
                    'height': self.geometry().height()
                },
                
                # Analysis results cache (to avoid re-computation)
                'has_master_results': hasattr(self, 'master_results') and self.master_results is not None,
                'has_remote_results': hasattr(self, 'remote_results') and self.remote_results is not None,
                
                # Additional metadata
                'created_timestamp': getattr(self, 'project_created_timestamp', self._get_timestamp()),
                'last_modified_timestamp': self._get_timestamp(),
                'app_version': '2.0'
            }
            
            # Save to file
            with open(file_path, 'w') as f:
                json.dump(project_data, f, indent=2)
            
            # Update project state
            self.current_project_path = file_path
            self.project_dirty = False
            
            # Set created timestamp if this is a new project
            if not hasattr(self, 'project_created_timestamp'):
                self.project_created_timestamp = project_data['created_timestamp']
            
            # Add to recent projects
            self.add_to_recent_projects(file_path)
            
            # Update UI
            self.update_ui_state()
            self.update_window_title()
            self.status_bar.showMessage(f"Project saved: {Path(file_path).name}")
            
            return True
            
        except Exception as e:
            QMessageBox.critical(self, "Save Error", f"Failed to save project:\n{str(e)}")
            return False
    
    def add_to_recent_projects(self, file_path: str):
        """Add project to recent projects list."""
        settings = QSettings('AttributeAddresser', 'RecentProjects')
        recent_files = settings.value('recent_files', [])
        
        # Remove if already exists
        if file_path in recent_files:
            recent_files.remove(file_path)
        
        # Add to front
        recent_files.insert(0, file_path)
        
        # Keep only last 10
        recent_files = recent_files[:10]
        
        # Save
        settings.setValue('recent_files', recent_files)
        
        # Update menu
        self.update_recent_projects_menu()
    
    def update_recent_projects_menu(self):
        """Update the recent projects menu."""
        self.recent_menu.clear()
        
        settings = QSettings('AttributeAddresser', 'RecentProjects')
        recent_files = settings.value('recent_files', [])
        
        if recent_files:
            for file_path in recent_files:
                if os.path.exists(file_path):
                    action = QAction(Path(file_path).name, self)
                    action.setToolTip(file_path)
                    action.triggered.connect(lambda checked, path=file_path: self.load_project_file(path))
                    self.recent_menu.addAction(action)
        else:
            no_recent_action = QAction('No recent projects', self)
            no_recent_action.setEnabled(False)
            self.recent_menu.addAction(no_recent_action)
    
    def _get_timestamp(self) -> str:
        """Get current timestamp."""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    def _update_gdtf_status(self, matched_count: int, total_count: int):
        """Update GDTF status label and button state."""
        if matched_count == total_count:
            self.gdtf_status_label.setText(f"All {total_count} fixtures successfully matched!")
            self.gdtf_status_label.setStyleSheet("color: green; font-weight: bold; padding: 5px;")
            self.match_gdtf_btn.setText("Edit GDTF Matches")
            self.match_gdtf_btn.setEnabled(True)  # Keep enabled for editing
        else:
            unmatched = total_count - matched_count
            self.gdtf_status_label.setText(f"{matched_count}/{total_count} fixtures matched. {unmatched} need manual matching.")
            self.gdtf_status_label.setStyleSheet("color: orange; font-weight: bold; padding: 5px;")
            self.match_gdtf_btn.setText("Match GDTF Profiles")
            self.match_gdtf_btn.setEnabled(True)
    
    def _load_external_gdtf_profiles(self, gdtf_folder: str) -> bool:
        """Load external GDTF profiles from folder. Returns True if successful."""
        if not gdtf_folder or not os.path.exists(gdtf_folder):
            return False
        
        self.config.set_external_gdtf_folder(gdtf_folder)
        result = self.controller.load_external_gdtf_profiles(gdtf_folder)
        
        if result["success"]:
            self.status_bar.showMessage(f"Loaded {result['profiles_loaded']} external GDTF profiles")
            return True
        return False
    
    def export_results(self):
        """Export analysis results to file, supporting Master, Remote, and Alignment data."""
        try:
            # Check what data we have available for export
            has_master = hasattr(self, 'master_results') and self.master_results is not None and self.master_fixture_type_attributes
            has_remote = hasattr(self, 'remote_results') and self.remote_results is not None and self.remote_fixture_type_attributes
            has_alignment = self.controller.alignment_results is not None
            
            if not (has_master or has_remote or has_alignment):
                QMessageBox.information(self, "No Data", "Please load fixtures, select attributes, and optionally perform alignment before exporting.")
                return
            
            # Create export options dialog
            export_options = self._get_export_options(has_master, has_remote, has_alignment)
            if not export_options:
                return
            
            # Get output format
            output_format = self.format_combo.currentText()
            extensions = {
                "text": "txt",
                "csv": "csv", 
                "json": "json",
                "ma3_xml": "xml",
                "ma3_sequences": "xml"
            }
            ext = extensions.get(output_format, "txt")
            
            # Get last used directory
            last_dir = self.config.get_last_export_directory()
            start_dir = last_dir if last_dir and os.path.exists(last_dir) else ""
            
            # Show file dialog
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Export Analysis Results",
                f"{start_dir}/fixture_analysis.{ext}",
                f"{output_format.upper()} Files (*.{ext});;All Files (*)"
            )
            
            if file_path:
                # Save the directory for next time
                self.config.set_last_export_directory(str(Path(file_path).parent))
                
                # Perform export based on selected options
                self._perform_export(file_path, output_format, export_options)
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error during export:\n{str(e)}")
    
    def _get_export_options(self, has_master: bool, has_remote: bool, has_alignment: bool) -> dict:
        """Get export options from user via simple dialog."""
        from PyQt6.QtWidgets import QCheckBox, QVBoxLayout, QHBoxLayout, QPushButton, QDialog
        
        dialog = QDialog(self)
        dialog.setWindowTitle("Export Options")
        dialog.setFixedSize(350, 200)
        
        layout = QVBoxLayout(dialog)
        layout.addWidget(QLabel("Select data to export:"))
        
        options = {}
        
        if has_master:
            master_cb = QCheckBox("Master Fixtures Analysis")
            master_cb.setChecked(True)
            layout.addWidget(master_cb)
            options['master'] = master_cb
        
        if has_remote:
            remote_cb = QCheckBox("Remote Fixtures Analysis")
            remote_cb.setChecked(True)
            layout.addWidget(remote_cb)
            options['remote'] = remote_cb
        
        if has_alignment:
            alignment_cb = QCheckBox("Fixture Alignment Results")
            alignment_cb.setChecked(True)
            layout.addWidget(alignment_cb)
            options['alignment'] = alignment_cb
        
        if has_master and has_remote and has_alignment:
            combined_cb = QCheckBox("Combined Summary Report")
            combined_cb.setChecked(True)
            layout.addWidget(combined_cb)
            options['combined'] = combined_cb
        
        # Buttons
        button_layout = QHBoxLayout()
        ok_btn = QPushButton("Export")
        cancel_btn = QPushButton("Cancel")
        ok_btn.clicked.connect(dialog.accept)
        cancel_btn.clicked.connect(dialog.reject)
        button_layout.addWidget(ok_btn)
        button_layout.addWidget(cancel_btn)
        layout.addLayout(button_layout)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            return {key: cb.isChecked() for key, cb in options.items()}
        return None
    
    def _perform_export(self, file_path: str, output_format: str, export_options: dict):
        """Perform the actual export based on options."""
        try:
            exported_files = []
            
            # Get MA3 config if needed
            ma3_config = None
            if output_format == "ma3_xml":
                ma3_config = self.ma3_config
            
            # Export master data
            if export_options.get("master", False):
                master_file_path = self._get_export_file_path(file_path, "master")
                result = self._export_master_data(master_file_path, output_format, ma3_config)
                if result["success"]:
                    exported_files.append(f"Master: {Path(master_file_path).name}")
                else:
                    QMessageBox.warning(self, "Export Warning", f"Failed to export master data: {result['error']}")
            
            # Export remote data
            if export_options.get("remote", False):
                remote_file_path = self._get_export_file_path(file_path, "remote")
                result = self._export_remote_data(remote_file_path, output_format, ma3_config)
                if result["success"]:
                    exported_files.append(f"Remote: {Path(remote_file_path).name}")
                else:
                    QMessageBox.warning(self, "Export Warning", f"Failed to export remote data: {result['error']}")
            
            # Export alignment data
            if export_options.get("alignment", False):
                alignment_file_path = self._get_export_file_path(file_path, "alignment")
                result = self._export_alignment_data(alignment_file_path, output_format)
                if result["success"]:
                    exported_files.append(f"Alignment: {Path(alignment_file_path).name}")
                else:
                    QMessageBox.warning(self, "Export Warning", f"Failed to export alignment data: {result['error']}")
            
            # Export combined data
            if export_options.get("combined", False):
                combined_file_path = self._get_export_file_path(file_path, "combined")
                result = self._export_combined_data(combined_file_path, output_format, ma3_config)
                if result["success"]:
                    exported_files.append(f"Combined: {Path(combined_file_path).name}")
                else:
                    QMessageBox.warning(self, "Export Warning", f"Failed to export combined data: {result['error']}")
            
            if exported_files:
                files_text = "\n".join(exported_files)
                QMessageBox.information(
                    self, 
                    "Export Complete", 
                    f"Successfully exported:\n{files_text}"
                )
                self.status_bar.showMessage(f"Export complete: {len(exported_files)} files")
            else:
                QMessageBox.warning(self, "Export Failed", "No files were exported successfully.")
                
        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Error during export:\n{str(e)}")
    
    def _get_export_file_path(self, base_path: str, suffix: str) -> str:
        """Generate export file path with suffix."""
        path = Path(base_path)
        stem = path.stem
        extension = path.suffix
        return str(path.parent / f"{stem}_{suffix}{extension}")
    
    def _export_master_data(self, file_path: str, output_format: str, ma3_config: dict = None) -> dict:
        """Export master fixture data."""
        if not self.master_fixture_type_attributes:
            return {"success": False, "error": "No master attributes selected"}
        
        # Analyze master fixtures
        result = self.controller.analyze_master_fixtures(
            self.master_fixture_type_attributes, 
            output_format, 
            ma3_config
        )
        
        if result["success"]:
            # Export the results
            export_result = self.controller.export_results(result, output_format, file_path, ma3_config)
            return export_result
        
        return result
    
    def _export_remote_data(self, file_path: str, output_format: str, ma3_config: dict = None) -> dict:
        """Export remote fixture data."""
        if not self.remote_fixture_type_attributes:
            return {"success": False, "error": "No remote attributes selected"}
        
        # Export existing remote fixtures without re-analyzing (preserves assigned sequences)
        result = self.controller.export_remote_fixtures_direct(
            self.remote_fixture_type_attributes, 
            output_format, 
            file_path,
            ma3_config
        )
        
        return result
    
    def _export_alignment_data(self, file_path: str, output_format: str) -> dict:
        """Export alignment data."""
        if not self.controller.alignment_results:
            return {"success": False, "error": "No alignment data available"}
        
        try:
            # Convert alignment data to exportable format
            alignment_data = self._format_alignment_data_for_export()
            
            # Write to file
            if output_format == "csv":
                self._write_alignment_csv(file_path, alignment_data)
            elif output_format == "json":
                self._write_alignment_json(file_path, alignment_data)
            else:
                self._write_alignment_text(file_path, alignment_data)
            
            return {"success": True}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _export_combined_data(self, file_path: str, output_format: str, ma3_config: dict = None) -> dict:
        """Export combined master, remote, and alignment data."""
        try:
            combined_data = {
                "export_timestamp": self._get_timestamp(),
                "master_fixtures": [],
                "remote_fixtures": [],
                "alignment_results": []
            }
            
            # Add master data if available
            if self.master_fixture_type_attributes:
                master_result = self.controller.analyze_master_fixtures(
                    self.master_fixture_type_attributes, "json"
                )
                if master_result["success"]:
                    combined_data["master_fixtures"] = self._extract_fixture_data(master_result)
            
            # Add remote data if available (preserve sequences)
            if self.remote_fixture_type_attributes:
                combined_data["remote_fixtures"] = self._extract_fixture_data_direct(
                    self.controller.remote_matched_fixtures
                )
            
            # Add alignment data if available
            if self.controller.alignment_results:
                combined_data["alignment_results"] = self._format_alignment_data_for_export()
            
            # Write combined data
            if output_format == "json":
                import json
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(combined_data, f, indent=2, default=str)
            else:
                # For other formats, write a summary
                self._write_combined_summary(file_path, combined_data)
            
            return {"success": True}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _format_alignment_data_for_export(self):
        """Format alignment data for export."""
        formatted_data = []
        
        # Check if we have manual alignments, generate results if needed
        alignment_mode = self.controller.get_alignment_mode()
        if alignment_mode == "manual":
            # Generate alignment results from manual alignments
            result = self.controller.generate_alignment_results_from_manual()
            if result.get("success"):
                alignment_results = result["alignment_results"]
            else:
                alignment_results = []
        else:
            # Use existing alignment results
            alignment_results = self.controller.alignment_results or []
        
        for result in alignment_results:
            row = {
                "master_name": result["master_fixture"].name if result["master_fixture"] else "",
                "master_type": getattr(result["master_fixture"], 'gdtf_spec', '') if result["master_fixture"] else "",
                "remote_name": result["remote_fixture"].name if result["remote_fixture"] else "",
                "remote_type": getattr(result["remote_fixture"], 'gdtf_spec', '') if result["remote_fixture"] else "",
                "alignment_status": result["alignment_status"],
                "confidence": result["confidence"],
                "notes": result["notes"]
            }
            formatted_data.append(row)
        
        return formatted_data
    
    def _write_alignment_csv(self, file_path: str, data: list):
        """Write alignment data to CSV file."""
        import csv
        
        fieldnames = ["master_name", "master_type", "remote_name", "remote_type", 
                     "alignment_status", "confidence", "notes"]
        
        with open(file_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(data)
    
    def _write_alignment_json(self, file_path: str, data: list):
        """Write alignment data to JSON file."""
        import json
        
        export_data = {
            "export_timestamp": self._get_timestamp(),
            "alignment_results": data
        }
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, default=str)
    
    def _write_alignment_text(self, file_path: str, data: list):
        """Write alignment data to text file."""
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write("FIXTURE ALIGNMENT RESULTS\n")
            f.write("=" * 50 + "\n\n")
            f.write(f"Export Date: {self._get_timestamp()}\n")
            f.write(f"Total Alignments: {len(data)}\n\n")
            
            for i, row in enumerate(data, 1):
                f.write(f"{i}. Master: {row['master_name']} ({row['master_type']})\n")
                f.write(f"   Remote: {row['remote_name']} ({row['remote_type']})\n")
                f.write(f"   Status: {row['alignment_status']} ({row['confidence']:.2%})\n")
                f.write(f"   Notes: {row['notes']}\n\n")
    
    def _extract_fixture_data(self, analysis_result: dict):
        """Extract fixture data from analysis result."""
        fixtures_data = []
        
        if analysis_result.get("analysis_results") and hasattr(analysis_result["analysis_results"], 'fixtures'):
            for fixture in analysis_result["analysis_results"].fixtures:
                fixture_data = {
                    "id": fixture.fixture_id,
                    "name": fixture.name,
                    "type": fixture.gdtf_spec or "Unknown",
                    "mode": fixture.gdtf_mode or "",
                    "base_address": fixture.base_address,
                    "absolute_addresses": getattr(fixture, 'absolute_addresses', {})
                }
                fixtures_data.append(fixture_data)
        
        return fixtures_data
    
    def _write_combined_summary(self, file_path: str, combined_data: dict):
        """Write combined data summary to text file."""
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write("COMBINED FIXTURE ANALYSIS RESULTS\n")
            f.write("=" * 50 + "\n\n")
            f.write(f"Export Date: {combined_data['export_timestamp']}\n\n")
            
            f.write(f"Master Fixtures: {len(combined_data['master_fixtures'])}\n")
            f.write(f"Remote Fixtures: {len(combined_data['remote_fixtures'])}\n")
            f.write(f"Alignment Results: {len(combined_data['alignment_results'])}\n\n")
            
            # Write summary statistics
            if combined_data['alignment_results']:
                matched = sum(1 for r in combined_data['alignment_results'] 
                            if r['alignment_status'] == 'matched')
                total = len(combined_data['alignment_results'])
                f.write(f"Alignment Success Rate: {matched}/{total} ({matched/total*100:.1f}%)\n")
    
    def update_ui_state(self):
        """Update UI state based on current application state."""
        # Get status for each dataset
        main_status = self.controller.get_current_status()
        master_status = self.controller.get_master_status()
        remote_status = self.controller.get_remote_status()
        
        # Update master UI elements with master-specific status
        self._update_master_ui_state(master_status)
        
        # Update remote UI elements with remote-specific status
        self._update_remote_ui_state(remote_status)
        
        # Update alignment UI elements
        self._update_alignment_ui_state()
        
        # Update export button based on both master and remote
        has_results = (
            (hasattr(self, 'master_results') and self.master_results is not None and self.master_fixture_type_attributes) or
            (hasattr(self, 'remote_results') and self.remote_results is not None and self.remote_fixture_type_attributes)
        )
        
        if hasattr(self, 'export_btn'):
            self.export_btn.setEnabled(bool(has_results))
        
        # Update save action
        if hasattr(self, 'save_action'):
            self.save_action.setEnabled(self.project_dirty)
    
    def _update_master_ui_state(self, status):
        """Update master UI elements based on master dataset state."""
        # For master tab, we use the master-specific controller status
        file_loaded = status["file_loaded"]
        has_fixtures = status["matched_fixtures"] > 0 or status["unmatched_fixtures"] > 0
        
        # Manual matching button - enabled when fixtures loaded
        if hasattr(self, 'master_match_gdtf_btn'):
            self.master_match_gdtf_btn.setEnabled(bool(has_fixtures))
        
        # Update select attributes button
        can_select_attributes = (
            status["file_loaded"] and 
            status["matched_fixtures"] > 0
        )
        
        if hasattr(self, 'master_select_attrs_btn'):
            self.master_select_attrs_btn.setEnabled(bool(can_select_attributes))
        
        # Update attribute selection status label
        if hasattr(self, 'master_attribute_status_label'):
            if can_select_attributes:
                if self.master_fixture_type_attributes:
                    total_attrs = sum(len(attrs) for attrs in self.master_fixture_type_attributes.values())
                    if total_attrs > 0:
                        self.master_attribute_status_label.setText(f"Attributes saved ({total_attrs} total) - you can modify anytime")
                        self.master_attribute_status_label.setStyleSheet("color: green; font-weight: bold; padding: 5px;")
                    else:
                        self.master_attribute_status_label.setText("No attributes selected - click to modify")
                        self.master_attribute_status_label.setStyleSheet("color: orange; font-weight: bold; padding: 5px;")
                else:
                    self.master_attribute_status_label.setText("Ready for attribute selection!")
                    self.master_attribute_status_label.setStyleSheet("color: blue; font-weight: bold; padding: 5px;")
            else:
                self.master_attribute_status_label.setText("Complete steps 1-2 first")
                self.master_attribute_status_label.setStyleSheet("color: gray; font-style: italic; padding: 5px;")
    
    def _update_remote_ui_state(self, status):
        """Update remote UI elements based on current state."""
        # For remote tab, we check if remote results exist
        has_remote_results = hasattr(self, 'remote_results') and self.remote_results is not None
        has_remote_fixtures = has_remote_results and self.remote_results.get("total_fixtures", 0) > 0
        
        # Manual matching button - enabled when fixtures loaded
        if hasattr(self, 'remote_match_gdtf_btn'):
            self.remote_match_gdtf_btn.setEnabled(bool(has_remote_fixtures))
        
        # Update select attributes button
        can_select_attributes = has_remote_results and self.remote_results.get("success", False)
        
        if hasattr(self, 'remote_select_attrs_btn'):
            self.remote_select_attrs_btn.setEnabled(bool(can_select_attributes))
        
        # Update attribute selection status label
        if hasattr(self, 'remote_attribute_status_label'):
            if can_select_attributes:
                if self.remote_fixture_type_attributes:
                    total_attrs = sum(len(attrs) for attrs in self.remote_fixture_type_attributes.values())
                    if total_attrs > 0:
                        self.remote_attribute_status_label.setText(f"Attributes saved ({total_attrs} total) - you can modify anytime")
                        self.remote_attribute_status_label.setStyleSheet("color: green; font-weight: bold; padding: 5px;")
                    else:
                        self.remote_attribute_status_label.setText("No attributes selected - click to modify")
                        self.remote_attribute_status_label.setStyleSheet("color: orange; font-weight: bold; padding: 5px;")
                else:
                    self.remote_attribute_status_label.setText("Ready for attribute selection!")
                    self.remote_attribute_status_label.setStyleSheet("color: blue; font-weight: bold; padding: 5px;")
            else:
                self.remote_attribute_status_label.setText("Complete steps 1-2 first")
                self.remote_attribute_status_label.setStyleSheet("color: gray; font-style: italic; padding: 5px;")
    
    def _update_alignment_ui_state(self):
        """Update alignment UI elements based on current state."""
        # Check if we have both master and remote data
        has_master = hasattr(self, 'master_results') and self.master_results is not None
        has_remote = hasattr(self, 'remote_results') and self.remote_results is not None
        
        can_align = has_master and has_remote
        
        if hasattr(self, 'align_btn'):
            self.align_btn.setEnabled(bool(can_align))
        
        # Enable assign sequences button when both datasets are available
        if hasattr(self, 'assign_sequences_btn'):
            self.assign_sequences_btn.setEnabled(bool(can_align))
        
        # Populate alignment tables when both datasets are available
        if can_align:
            # Only repopulate if data structure has changed, not just sequence values
            if self._should_repopulate_tables():
                self._populate_alignment_tables(preserve_order=True)
            self._update_alignment_status()
        elif hasattr(self, 'alignment_status'):
            if has_master and not has_remote:
                self.alignment_status.setText("Load remote fixtures to begin attribute routing")
                self.alignment_status.setStyleSheet("color: orange; font-style: italic; padding: 10px;")
            elif has_remote and not has_master:
                self.alignment_status.setText("Load master fixtures to begin attribute routing")
                self.alignment_status.setStyleSheet("color: orange; font-style: italic; padding: 10px;")
            else:
                self.alignment_status.setText("Load Master and Remote fixtures to begin attribute routing")
                self.alignment_status.setStyleSheet("color: gray; font-style: italic; padding: 10px;")

    def _extract_fixture_data_direct(self, fixtures):
        """Extract fixture data directly from fixture objects (preserves sequences)."""
        fixtures_data = []
        
        for fixture in fixtures:
            if fixture.is_matched():
                fixture_data = {
                    "id": fixture.fixture_id,
                    "name": fixture.name,
                    "type": fixture.gdtf_spec or "Unknown",
                    "mode": fixture.gdtf_mode or "",
                    "base_address": fixture.base_address,
                    "absolute_addresses": getattr(fixture, 'absolute_addresses', {}),
                    "attribute_sequences": getattr(fixture, 'attribute_sequences', {})
                }
                fixtures_data.append(fixture_data)
        
        return fixtures_data

def main():
    """Main entry point for the application."""
    app = QApplication(sys.argv)
    
    # Set application properties for proper branding
    app.setApplicationName("AttributeAddresser")
    app.setApplicationDisplayName("AttributeAddresser")
    app.setOrganizationName("AttributeAddresser")
    app.setOrganizationDomain("attributeaddresser.com")
    app.setApplicationVersion("1.0")
    
    # Create and show the main window
    window = MVRApp()
    window.show()
    
    # Run the application
    sys.exit(app.exec())


if __name__ == "__main__":
    main() 