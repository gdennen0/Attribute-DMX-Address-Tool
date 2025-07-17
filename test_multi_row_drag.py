#!/usr/bin/env python3
"""
Test application to demonstrate multi-row selection and dragging functionality.
"""

import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QLabel
from PyQt6.QtCore import Qt

from views.draggable_tables import DraggableTableWidget


class TestWindow(QMainWindow):
    """Test window to demonstrate multi-row selection and dragging."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Multi-Row Selection & Dragging Test")
        self.setGeometry(100, 100, 800, 600)
        
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Create layout
        layout = QVBoxLayout(central_widget)
        
        # Add instructions
        instructions = QLabel("""
Multi-Row Selection & Dragging Test

Instructions:
1. Select multiple rows using:
   - Ctrl+Click to select individual rows
   - Shift+Click to select ranges
   - Click and drag to select multiple rows
   - Ctrl+A to select all rows

2. Drag multiple rows by:
   - Selecting multiple rows first
   - Clicking and dragging any selected row
   - All selected rows will move together

3. Keyboard shortcuts:
   - Ctrl+A: Select all rows
   - Delete: Delete selected rows
   - Shift+Up/Down: Extend selection

4. Right-click for context menu with additional options
        """)
        instructions.setStyleSheet("background-color: #f0f0f0; padding: 10px; border: 1px solid #ccc;")
        layout.addWidget(instructions)
        
        # Create test table with proper model
        from views.draggable_tables import DragDropTableModel
        
        # Create model with headers
        headers = ["ID", "Name", "Type", "Status"]
        model = DragDropTableModel(headers)
        self.table = DraggableTableWidget()
        self.table.setModel(model)
        
        # Add some test data
        test_data = [
            {"ID": "1", "Name": "Fixture A", "Type": "LED", "Status": "Active"},
            {"ID": "2", "Name": "Fixture B", "Type": "Moving", "Status": "Active"},
            {"ID": "3", "Name": "Fixture C", "Type": "LED", "Status": "Inactive"},
            {"ID": "4", "Name": "Fixture D", "Type": "Conventional", "Status": "Active"},
            {"ID": "5", "Name": "Fixture E", "Type": "LED", "Status": "Active"},
            {"ID": "6", "Name": "Fixture F", "Type": "Moving", "Status": "Inactive"},
            {"ID": "7", "Name": "Fixture G", "Type": "Conventional", "Status": "Active"},
            {"ID": "8", "Name": "Fixture H", "Type": "LED", "Status": "Active"},
            {"ID": "9", "Name": "Fixture I", "Type": "Moving", "Status": "Active"},
            {"ID": "10", "Name": "Fixture J", "Type": "LED", "Status": "Inactive"},
        ]
        
        # Set the data in the model
        model.setDataFromList(test_data)
        
        # Connect signals
        self.table.rowMoved.connect(self.on_row_moved)
        self.table.rowsMoved.connect(self.on_rows_moved)
        
        layout.addWidget(self.table)
        
        # Add status label
        self.status_label = QLabel("Ready - Select rows to test multi-row operations")
        self.status_label.setStyleSheet("color: blue; padding: 5px;")
        layout.addWidget(self.status_label)
    
    def on_row_moved(self, from_row, to_row):
        """Handle single row move."""
        self.status_label.setText(f"Row {from_row} moved to position {to_row}")
    
    def on_rows_moved(self, selected_rows, target_row):
        """Handle multi-row move."""
        self.status_label.setText(f"Rows {selected_rows} moved to position {target_row}")


def main():
    """Main function."""
    app = QApplication(sys.argv)
    
    window = TestWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main() 