"""
Draggable table widgets for AttributeAddresser.
Provides drag and drop functionality for fixture tables with grouping by attributes.
"""

from typing import List, Optional, Dict, Any
from PyQt6.QtWidgets import (
    QWidget, QTableView, QTableWidget, QTableWidgetItem, QHeaderView,
    QAbstractItemView, QStyledItemDelegate, QStyle, QStyleOptionViewItem,
    QMenu, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QMimeData, QModelIndex, QAbstractTableModel
from PyQt6.QtGui import QDrag, QPixmap, QPainter, QColor, QFont


class DragDropTableModel(QAbstractTableModel):
    """Custom table model that handles drag and drop properly."""
    
    def __init__(self, headers: List[str], parent=None):
        super().__init__(parent)
        self._headers = headers
        self._data = []  # List of dictionaries, each representing a row
    
    def rowCount(self, parent=None):
        """Return the number of rows."""
        return len(self._data)
    
    def columnCount(self, parent=None):
        """Return the number of columns."""
        return len(self._headers)
    
    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        """Return data for the given index and role."""
        if not index.isValid():
            return None
        
        if role == Qt.ItemDataRole.DisplayRole:
            row = index.row()
            col = index.column()
            if 0 <= row < len(self._data) and 0 <= col < len(self._headers):
                return str(self._data[row].get(self._headers[col], ''))
        
        return None
    
    def setData(self, index, value, role=Qt.ItemDataRole.EditRole):
        """Set data for the given index and role."""
        if not index.isValid():
            return False
        
        if role == Qt.ItemDataRole.EditRole or role == Qt.ItemDataRole.DisplayRole:
            row = index.row()
            col = index.column()
            if 0 <= row < len(self._data) and 0 <= col < len(self._headers):
                self._data[row][self._headers[col]] = str(value)
                self.dataChanged.emit(index, index)
                return True
        
        return False
    
    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        """Return header data."""
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            if 0 <= section < len(self._headers):
                return self._headers[section]
        return None
    
    def flags(self, index):
        """Return flags for the given index."""
        if not index.isValid():
            return Qt.ItemFlag.ItemIsDropEnabled
        
        # Use int values to avoid recursion issues with Qt flags
        base_flags = (Qt.ItemFlag.ItemIsEnabled.value | 
                     Qt.ItemFlag.ItemIsSelectable.value | 
                     Qt.ItemFlag.ItemIsDragEnabled.value | 
                     Qt.ItemFlag.ItemIsDropEnabled.value)
        
        # Make routing column (column 8) read-only but still draggable
        if index.column() == 8:  # Routing column
            return Qt.ItemFlag(base_flags)
        
        # Add editable flag for other columns
        return Qt.ItemFlag(base_flags | Qt.ItemFlag.ItemIsEditable.value)
    
    def supportedDropActions(self):
        """Return supported drop actions."""
        return Qt.DropAction.MoveAction
    
    def mimeTypes(self):
        """Return supported MIME types."""
        return ["application/x-qabstractitemmodeldatalist"]
    
    def mimeData(self, indexes):
        """Create MIME data for the given indexes."""
        mime_data = QMimeData()
        encoded_data = self.encodeData(indexes)
        mime_data.setData("application/x-qabstractitemmodeldatalist", encoded_data)
        return mime_data
    
    def dropMimeData(self, data, action, row, column, parent):
        """Handle drop operations."""
        if action == Qt.DropAction.IgnoreAction:
            return True
        
        if not data.hasFormat("application/x-qabstractitemmodeldatalist"):
            return False
        
        # Always insert rows, never replace cells
        return True
    
    def encodeData(self, indexes):
        """Encode data for MIME operations."""
        # Simple encoding - just store row indices
        rows = set()
        for index in indexes:
            if index.isValid():
                rows.add(index.row())
        
        # Convert to bytes
        return str(sorted(rows)).encode()
    
    def decodeData(self, data):
        """Decode data from MIME operations."""
        try:
            rows_str = data.data("application/x-qabstractitemmodeldatalist").data().decode()
            # Parse the string representation of the list
            rows_str = rows_str.strip('[]')
            if rows_str:
                return [int(x.strip()) for x in rows_str.split(',')]
            return []
        except:
            return []
    
    def insertRow(self, row, parent=None):
        """Insert a row at the specified position."""
        # Use QModelIndex() instead of None for parent
        from PyQt6.QtCore import QModelIndex
        parent_index = parent if parent is not None else QModelIndex()
        self.beginInsertRows(parent_index, row, row)
        self._data.insert(row, {header: '' for header in self._headers})
        self.endInsertRows()
        return True
    
    def removeRow(self, row, parent=None):
        """Remove a row at the specified position."""
        if 0 <= row < len(self._data):
            # Use QModelIndex() instead of None for parent
            from PyQt6.QtCore import QModelIndex
            parent_index = parent if parent is not None else QModelIndex()
            self.beginRemoveRows(parent_index, row, row)
            del self._data[row]
            self.endRemoveRows()
            return True
        return False
    
    def setRowData(self, row, data_dict):
        """Set data for a specific row."""
        if 0 <= row < len(self._data):
            self._data[row] = data_dict.copy()
            # Emit data changed for the entire row
            top_left = self.index(row, 0)
            bottom_right = self.index(row, len(self._headers) - 1)
            self.dataChanged.emit(top_left, bottom_right)
    
    def getRowData(self, row):
        """Get data for a specific row."""
        if 0 <= row < len(self._data):
            return self._data[row].copy()
        return {}
    
    def clear(self):
        """Clear all data."""
        self.beginResetModel()
        self._data.clear()
        self.endResetModel()
    
    def setDataFromList(self, data_list):
        """Set data from a list of dictionaries."""
        self.beginResetModel()
        self._data = [row.copy() for row in data_list]
        self.endResetModel()


class DragDropIndicator(QWidget):
    """Visual indicator for drag and drop operations."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(4)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.hide()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        # Draw shadow
        shadow_color = QColor(0, 120, 212, 80)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(shadow_color)
        painter.drawRect(0, 2, self.width(), 2)
        # Draw main line
        painter.setBrush(QColor("#0078d4"))
        painter.setPen(QColor("#0078d4"))
        painter.drawRect(0, 0, self.width(), 2)
        painter.end()


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
    
    def get_selection_info(self):
        """Get information about the current selection."""
        selected_rows = self.get_selected_rows()
        if not selected_rows:
            return "No rows selected"
        elif len(selected_rows) == 1:
            return f"Row {selected_rows[0]} selected"
        else:
            return f"{len(selected_rows)} rows selected (rows {selected_rows[0]}-{selected_rows[-1]})"
    
    def startDrag(self, supportedActions):
        """Start drag operation with visual feedback for single or multiple rows."""
        selected_indexes = self.selectedIndexes()
        if not selected_indexes:
            return
        
        # Get all selected rows
        self.drag_start_rows = self.get_selected_rows()
        if not self.drag_start_rows:
            return
        
        # Provide visual feedback that drag is starting
        self.setCursor(Qt.CursorShape.ClosedHandCursor)
            
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
        self.setCursor(Qt.CursorShape.ArrowCursor)
    
    def create_drag_pixmap(self):
        """Create a visual representation of the dragged rows."""
        if not self.drag_start_rows:
            return QPixmap()
        
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
                font.setPointSize(10)
                painter.setFont(font)
                text = f"{len(self.drag_start_rows)} rows"
                painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, text)
            else:
                # For single row, show a subtle indicator
                painter.setPen(QColor(255, 255, 255))
                font = QFont()
                font.setPointSize(8)
                painter.setFont(font)
                text = "1 row"
                painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, text)
            
            painter.end()
            return pixmap
            
        except Exception as e:
            print(f"Error creating drag pixmap: {e}")
            return QPixmap()
    
    def dragEnterEvent(self, event):
        """Handle drag enter events."""
        if event.mimeData().hasFormat("application/x-qabstractitemmodeldatalist"):
            event.acceptProposedAction()
            self.drag_indicator.show()
        else:
            event.ignore()
    
    def dragMoveEvent(self, event):
        """Handle drag move events with visual feedback."""
        if event.mimeData().hasFormat("application/x-qabstractitemmodeldatalist"):
            event.acceptProposedAction()
            
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
                # Drop at end of table
                insert_row = self.model().rowCount()
            
            # Position drop indicator
            self.position_drop_indicator(insert_row)
            
        else:
            event.ignore()
    
    def dragLeaveEvent(self, event):
        """Handle drag leave events."""
        self.drag_indicator.hide()
        super().dragLeaveEvent(event)
    
    def dropEvent(self, event):
        """Handle drop events."""
        if event.mimeData().hasFormat("application/x-qabstractitemmodeldatalist"):
            event.acceptProposedAction()
            
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
                # Drop at end of table
                insert_row = self.model().rowCount()
            
            # Hide drop indicator
            self.drag_indicator.hide()
            
            # Perform the move
            if self.drag_start_rows:
                # Check if we're dropping within the selected range
                if insert_row in self.drag_start_rows:
                    # Don't move if dropping within the selection
                    return
                
                self.perform_multi_row_move(self.drag_start_rows, insert_row)
            
        else:
            event.ignore()
    
    def position_drop_indicator(self, row):
        """Position the drop indicator at the target row where insertion will occur."""
        if row >= self.model().rowCount():
            # Position at the bottom of the table, just below the last row
            if self.model().rowCount() == 0:
                y = 0
            else:
                last_index = self.model().index(self.model().rowCount() - 1, 0)
                last_rect = self.visualRect(last_index)
                y = last_rect.bottom()
        else:
            # Position at the bottom of the target row (one row lower)
            index = self.model().index(row, 0)
            rect = self.visualRect(index)
            y = rect.bottom() - (self.drag_indicator.height() * 2)
        self.drag_indicator.setGeometry(0, y, self.viewport().width(), self.drag_indicator.height())
        self.drag_indicator.show()
    
    def perform_multi_row_move(self, source_rows, target_row):
        """Perform multi-row move operation and preserve selection by ID or row data."""
        if not source_rows:
            return

        # Get unique identifiers for selected rows (prefer 'ID', else use full row data)
        model = self.model()
        headers = getattr(model, '_headers', None)
        id_col = None
        if headers and 'ID' in headers:
            id_col = headers.index('ID')
        selected_ids = []
        for row in source_rows:
            row_data = model.getRowData(row)
            if id_col is not None:
                selected_ids.append(row_data.get('ID'))
            else:
                selected_ids.append(tuple(row_data.items()))

        # Store all row data first
        row_data_list = [model.getRowData(row) for row in source_rows]

        # Remove all source rows in reverse order to maintain indices
        for source_row in reversed(source_rows):
            model.removeRow(source_row)

        # Calculate the final target position after removing source rows
        final_target = target_row
        for source_row in source_rows:
            if source_row < target_row:
                final_target -= 1

        # Insert all rows at the target position in the correct order
        moved_rows = []
        for i, row_data in enumerate(row_data_list):
            insert_position = final_target + i
            model.insertRow(insert_position)
            model.setRowData(insert_position, row_data)
            moved_rows.append(insert_position)

        # Reselect the same logical rows by ID or row data
        self.clearSelection()
        for row in range(model.rowCount()):
            row_data = model.getRowData(row)
            if id_col is not None:
                if row_data.get('ID') in selected_ids:
                    super().selectRow(row)
            else:
                if tuple(row_data.items()) in selected_ids:
                    super().selectRow(row)

        # Emit signals
        if len(moved_rows) == 1:
            self.rowMoved.emit(source_rows[0], moved_rows[0])
        else:
            self.rowsMoved.emit(source_rows, final_target)
    
    def show_context_menu(self, position):
        """Show context menu for row operations."""
        menu = QMenu(self)
        
        # Get selected rows
        selected_rows = self.get_selected_rows()
        
        if selected_rows:
            # Show selection info
            selection_info = menu.addAction(self.get_selection_info())
            selection_info.setEnabled(False)
            menu.addSeparator()
            
            # Delete selected rows
            delete_action = menu.addAction("Delete Selected Row(s)")
            delete_action.triggered.connect(self.delete_selected_rows)
            
            menu.addSeparator()
            
            # Insert row options
            insert_above_action = menu.addAction("Insert Row Above")
            insert_above_action.triggered.connect(self.insert_empty_row_above)
            
            insert_below_action = menu.addAction("Insert Row Below")
            insert_below_action.triggered.connect(self.insert_empty_row_below)
        
        if menu.actions():
            menu.exec(self.mapToGlobal(position))
    
    def delete_selected_rows(self):
        """Delete all selected rows."""
        selected_rows = self.get_selected_rows()
        if not selected_rows:
            return
        
        # Confirm deletion
        if len(selected_rows) == 1:
            message = "Delete this row?"
        else:
            message = f"Delete {len(selected_rows)} selected rows?"
        
        reply = QMessageBox.question(self, "Confirm Deletion", message,
                                   QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if reply == QMessageBox.StandardButton.Yes:
            # Delete in reverse order to maintain indices
            for row in reversed(selected_rows):
                self.model().removeRow(row)
                self.rowDeleted.emit(row)
    
    def insert_empty_row_above(self):
        """Insert empty row above current selection."""
        selected_rows = self.get_selected_rows()
        if selected_rows:
            self.insert_empty_row_at(selected_rows[0])
    
    def insert_empty_row_below(self):
        """Insert empty row below current selection."""
        selected_rows = self.get_selected_rows()
        if selected_rows:
            self.insert_empty_row_at(selected_rows[-1] + 1)
    
    def insert_empty_row_at(self, row):
        """Insert empty row at specified position."""
        self.model().insertRow(row)
        self.rowInserted.emit(row)
    
    def delete_current_row(self):
        """Delete the currently selected row."""
        current_row = self.currentIndex().row()
        if current_row >= 0:
            self.model().removeRow(current_row)
            self.rowDeleted.emit(current_row)
    
    def keyPressEvent(self, event):
        """Handle keyboard shortcuts."""
        if event.key() == Qt.Key.Key_Delete:
            self.delete_selected_rows()
        elif event.key() == Qt.Key.Key_A and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            # Select all rows
            self.selectAll()
        elif event.key() == Qt.Key.Key_Up and event.modifiers() == Qt.KeyboardModifier.ShiftModifier:
            # Shift+Up: Extend selection upward
            current_row = self.currentIndex().row()
            if current_row > 0:
                self.selectRow(current_row - 1)
        elif event.key() == Qt.Key.Key_Down and event.modifiers() == Qt.KeyboardModifier.ShiftModifier:
            # Shift+Down: Extend selection downward
            current_row = self.currentIndex().row()
            if current_row < self.model().rowCount() - 1:
                self.selectRow(current_row + 1)
        else:
            super().keyPressEvent(event)
    
    def resizeEvent(self, event):
        """Handle resize events to reposition drop indicator."""
        super().resizeEvent(event)
        if self.drag_indicator.isVisible():
            # Reposition indicator if visible
            current_row = self.currentIndex().row()
            if current_row >= 0:
                self.position_drop_indicator(current_row)


class DraggableTableWidget(DraggableTableView):
    """Draggable table widget that extends QTableWidget functionality."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Connect signals to default handlers
        self.rowMoved.connect(self.on_row_moved)
        self.rowsMoved.connect(self.on_rows_moved)
        self.rowInserted.connect(self.on_row_inserted)
        self.rowDeleted.connect(self.on_row_deleted)
    
    def on_row_moved(self, from_row, to_row):
        """Default handler for single row moves."""
        pass
    
    def on_rows_moved(self, selected_rows, target_row):
        """Default handler for multi-row moves."""
        pass
    
    def on_row_inserted(self, row):
        """Default handler for row insertion."""
        pass
    
    def on_row_deleted(self, row):
        """Default handler for row deletion."""
        pass
    
    # QTableWidget compatibility methods
    def setRowCount(self, count):
        """Set the number of rows in the table."""
        current_count = self.model().rowCount()
        if count > current_count:
            for _ in range(count - current_count):
                self.model().insertRow(current_count)
        elif count < current_count:
            for _ in range(current_count - count):
                self.model().removeRow(current_count - 1)
    
    def rowCount(self):
        """Get the number of rows in the table."""
        return self.model().rowCount()
    
    def columnCount(self):
        """Get the number of columns in the table."""
        return self.model().columnCount()
    
    def setItem(self, row, column, item):
        """Set an item in the table."""
        if isinstance(item, QTableWidgetItem):
            index = self.model().index(row, column)
            self.model().setData(index, item.text())
            # Preserve item flags
            if not item.flags() & Qt.ItemFlag.ItemIsEditable:
                self.model().setData(index, item.text(), Qt.ItemDataRole.UserRole)
    
    def item(self, row, column):
        """Get an item from the table."""
        index = self.model().index(row, column)
        if index.isValid():
            item = QTableWidgetItem(self.model().data(index))
            # Restore item flags if needed
            user_data = self.model().data(index, Qt.ItemDataRole.UserRole)
            if user_data:
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            return item
        return None
    
    def removeRow(self, row):
        """Remove a row from the table."""
        self.model().removeRow(row)
    
    def insertRow(self, row):
        """Insert a row into the table."""
        self.model().insertRow(row)
    
    def selectRow(self, row):
        """Select a specific row."""
        if 0 <= row < self.model().rowCount():
            super().selectRow(row)
    
    def selectRows(self, rows):
        """Select multiple rows."""
        self.clearSelection()
        for row in rows:
            if 0 <= row < self.model().rowCount():
                super().selectRow(row)
    
    def getSelectedRows(self):
        """Get list of selected row indices."""
        return self.get_selected_rows()
    
    def currentRow(self):
        """Get the current row index."""
        return self.currentIndex().row()
    
    def resizeColumnsToContents(self):
        """Resize columns to fit their contents."""
        super().resizeColumnsToContents()
    
    def setColumnCount(self, count):
        """Set the number of columns in the table."""
        # Note: The model doesn't support dynamic column count changes
        # This is a compatibility method that does nothing
        pass
    
    def setHorizontalHeaderLabels(self, labels):
        """Set the horizontal header labels."""
        # Note: The model doesn't support dynamic header changes
        # This is a compatibility method that does nothing
        pass 