"""
MVR Import Dialog - Clean UI for importing MVR files with fixture selection.
Similar to CSV import but for MVR files.
"""

import os
from typing import Dict, List, Optional, Any
from pathlib import Path

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, 
    QPushButton, QGroupBox, QScrollArea, QWidget,
    QFileDialog, QMessageBox, QFrame, QTableWidget, QTableWidgetItem,
    QHeaderView, QCheckBox, QSplitter, QTextEdit
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

from services.mvr_service import MVRService
from services.fixture_processing_service import FixtureProcessingService


class SelectableMVRTableWidget(QTableWidget):
    """Custom table widget with checkbox selection for MVR fixtures."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.setSelectionMode(QTableWidget.SelectionMode.ExtendedSelection)
        
        # Enable selection highlighting
        self.setShowGrid(True)
        self.setAlternatingRowColors(True)
        
        # Connect selection changes
        self.selectionModel().selectionChanged.connect(self.on_selection_changed)
        
    def on_selection_changed(self):
        """Handle selection change events."""
        # Update parent selection status
        if hasattr(self.parent(), 'update_selection_status'):
            self.parent().update_selection_status()
    
    def get_selected_rows(self) -> List[int]:
        """Get list of currently selected row indices."""
        selected_rows = []
        for index in self.selectionModel().selectedRows():
            selected_rows.append(index.row())
        return sorted(selected_rows)
    
    def is_row_selected(self, row: int) -> bool:
        """Check if a row is selected."""
        return row in self.get_selected_rows()
    
    def setup_table_data(self, fixtures: List[Dict]):
        """Set up the table with fixture data."""
        if not fixtures:
            return
        
        # Set up columns
        headers = ["Select", "Name", "Type", "Mode", "Base Address", "Fixture ID", "UUID"]
        self.setColumnCount(len(headers))
        self.setHorizontalHeaderLabels(headers)
        
        # Set up rows
        self.setRowCount(len(fixtures))
        
        for row, fixture in enumerate(fixtures):
            # Checkbox column
            checkbox = QCheckBox()
            checkbox.setChecked(True)  # Default to selected
            checkbox.stateChanged.connect(lambda state, r=row: self.on_checkbox_changed(r, state))
            self.setCellWidget(row, 0, checkbox)
            
            # Fixture data columns
            self.setItem(row, 1, QTableWidgetItem(str(fixture.get('name', 'Unknown'))))
            self.setItem(row, 2, QTableWidgetItem(str(fixture.get('gdtf_spec', 'Unknown'))))
            self.setItem(row, 3, QTableWidgetItem(str(fixture.get('gdtf_mode', 'Unknown'))))
            self.setItem(row, 4, QTableWidgetItem(str(fixture.get('base_address', 1))))
            self.setItem(row, 5, QTableWidgetItem(str(fixture.get('fixture_id', 0))))
            self.setItem(row, 6, QTableWidgetItem(str(fixture.get('uuid', 'N/A'))))
        
        # Resize columns to fit content
        self.resizeColumnsToContents()
        
        # Make first column (checkbox) smaller
        self.setColumnWidth(0, 60)
        
    def on_checkbox_changed(self, row: int, state: int):
        """Handle checkbox state changes."""
        # Emit signal to parent to update import button state
        if hasattr(self.parent(), 'update_import_button_state'):
            self.parent().update_import_button_state()
    
    def get_checked_rows(self) -> List[int]:
        """Get list of checked row indices."""
        checked_rows = []
        for row in range(self.rowCount()):
            checkbox = self.cellWidget(row, 0)
            if checkbox and checkbox.isChecked():
                checked_rows.append(row)
        return checked_rows
    
    def set_row_checked(self, row: int, checked: bool):
        """Set the checked state of a specific row."""
        if 0 <= row < self.rowCount():
            checkbox = self.cellWidget(row, 0)
            if checkbox:
                checkbox.setChecked(checked)
    
    def check_selected_rows(self):
        """Check all selected rows."""
        for row in self.get_selected_rows():
            self.set_row_checked(row, True)
    
    def uncheck_selected_rows(self):
        """Uncheck all selected rows."""
        for row in self.get_selected_rows():
            self.set_row_checked(row, False)
    
    def check_all_rows(self):
        """Check all rows."""
        for row in range(self.rowCount()):
            self.set_row_checked(row, True)
    
    def uncheck_all_rows(self):
        """Uncheck all rows."""
        for row in range(self.rowCount()):
            self.set_row_checked(row, False)


class MVRImportDialog(QDialog):
    """
    Dialog for importing MVR files with fixture selection.
    """
    
    # Signal emitted when MVR import is successful
    import_successful = pyqtSignal(list)  # List of FixtureMatch objects
    
    def __init__(self, parent, config=None):
        super().__init__(parent)
        self.config = config
        self.mvr_service = MVRService()
        self.fixture_service = FixtureProcessingService()
        self.fixtures = []
        self.selected_file_path = None
        
        self.setup_ui()
        self.setModal(True)
        self.resize(1000, 700)
        
        # Load saved MVR directory if available
        if self.config:
            last_dir = self.config.get_last_mvr_directory()
            if last_dir and os.path.exists(last_dir):
                self.last_mvr_directory = last_dir
            else:
                self.last_mvr_directory = ""
        else:
            self.last_mvr_directory = ""
    
    def setup_ui(self):
        """Create the dialog user interface."""
        self.setWindowTitle("MVR Import - Select Fixtures")
        
        # Main layout
        main_layout = QVBoxLayout(self)
        
        # Create splitter for two-panel layout
        splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(splitter)
        
        # Left panel - File selection and controls
        left_panel = self.create_left_panel()
        splitter.addWidget(left_panel)
        
        # Right panel - Preview and info
        right_panel = self.create_right_panel()
        splitter.addWidget(right_panel)
        
        # Set splitter proportions
        splitter.setSizes([300, 700])
        
        # Button layout
        button_layout = QHBoxLayout()
        
        # Import button
        self.import_btn = QPushButton("Import Selected Fixtures")
        self.import_btn.setEnabled(False)
        self.import_btn.clicked.connect(self.import_mvr)
        self.import_btn.setStyleSheet("QPushButton { background-color: #4CAF50; color: white; font-weight: bold; }")
        button_layout.addWidget(self.import_btn)
        
        # Cancel button
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        main_layout.addLayout(button_layout)
    
    def create_left_panel(self) -> QWidget:
        """Create the left panel with file selection and controls."""
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        
        # File selection group
        file_group = QGroupBox("MVR File Selection")
        file_layout = QVBoxLayout(file_group)
        
        # File path display
        self.file_label = QLabel("No file selected")
        self.file_label.setWordWrap(True)
        self.file_label.setStyleSheet("padding: 10px; border: 1px solid #ccc; border-radius: 4px; background-color: #f9f9f9;")
        file_layout.addWidget(self.file_label)
        
        # Browse button
        browse_btn = QPushButton("Browse MVR File...")
        browse_btn.clicked.connect(self.browse_mvr_file)
        file_layout.addWidget(browse_btn)
        
        left_layout.addWidget(file_group)
        
        # Fixture count group
        count_group = QGroupBox("Fixture Count")
        count_layout = QVBoxLayout(count_group)
        
        # Fixture count status
        self.fixture_count_status = QLabel("No fixtures loaded")
        self.fixture_count_status.setStyleSheet("color: gray; font-style: italic;")
        count_layout.addWidget(self.fixture_count_status)
        
        left_layout.addWidget(count_group)
        
        # Info text area
        info_group = QGroupBox("Import Information")
        info_layout = QVBoxLayout(info_group)
        
        self.info_text = QTextEdit()
        self.info_text.setReadOnly(True)
        self.info_text.setMaximumHeight(150)
        self.info_text.setPlainText("Select an MVR file to begin...")
        info_layout.addWidget(self.info_text)
        
        left_layout.addWidget(info_group)
        
        # Add stretch to push everything to the top
        left_layout.addStretch()
        
        return left_widget
    
    def create_right_panel(self) -> QWidget:
        """Create the right panel with preview table."""
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        
        # Preview group
        preview_group = QGroupBox("Fixture Preview")
        preview_layout = QVBoxLayout(preview_group)
        
        # Preview info
        self.preview_info = QLabel("Load an MVR file to see fixture preview")
        self.preview_info.setStyleSheet("color: gray; font-style: italic; padding: 10px;")
        preview_layout.addWidget(self.preview_info)
        
        # Add selection controls (will be added after preview_info)
        self.add_row_selection_controls(preview_layout)
        
        # Preview table
        self.preview_table = SelectableMVRTableWidget(self)
        preview_layout.addWidget(self.preview_table)
        
        right_layout.addWidget(preview_group)
        
        return right_widget
    
    def browse_mvr_file(self):
        """Open file dialog to select MVR file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select MVR File",
            self.last_mvr_directory,
            "MVR Files (*.mvr);;All Files (*)"
        )
        
        if file_path:
            self.load_mvr_file(file_path)
    
    def load_mvr_file(self, file_path: str):
        """Load fixtures from MVR file."""
        try:
            self.selected_file_path = file_path
            
            # Update file label
            self.file_label.setText(f"✓ {Path(file_path).name}")
            self.file_label.setStyleSheet("padding: 10px; border: 1px solid #4CAF50; border-radius: 4px; background-color: #E8F5E8; color: #2E7D32; font-weight: bold;")
            
            # Save directory for next time
            if self.config:
                self.config.set_last_mvr_directory(str(Path(file_path).parent))
            
            # Load fixtures using MVR service
            self.fixtures = self.mvr_service.load_mvr_file(file_path)
            
            if not self.fixtures:
                QMessageBox.warning(self, "No Fixtures", "No fixtures found in the selected MVR file.")
                return
            
            # Update preview
            self.update_preview()
            self.update_info_text()
            self.update_import_button_state()
            self.update_selection_buttons_state()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load MVR file:\n{str(e)}")
            self.file_label.setText("Error loading file")
            self.file_label.setStyleSheet("padding: 10px; border: 1px solid #f44336; border-radius: 4px; background-color: #ffebee; color: #c62828;")
    
    def update_preview(self):
        """Update the preview table with fixture data."""
        if not self.fixtures:
            self.preview_info.setText("No fixtures to display")
            return
        
        # Update preview info
        self.preview_info.setText(f"Found {len(self.fixtures)} fixtures in MVR file")
        self.preview_info.setStyleSheet("color: green; font-weight: bold; padding: 10px;")
        
        # Setup table data
        self.preview_table.setup_table_data(self.fixtures)
        
        # Connect selection changes to update status
        self.preview_table.selectionModel().selectionChanged.connect(self.update_selection_status)
    
    def update_info_text(self):
        """Update the info text area."""
        if not self.fixtures:
            self.info_text.setPlainText("No fixtures loaded.")
            return
        
        selected_count = len(self.preview_table.get_checked_rows())
        total_count = len(self.fixtures)
        
        # Count fixture types
        fixture_types = {}
        for fixture in self.fixtures:
            fixture_type = fixture.get('gdtf_spec', 'Unknown')
            fixture_types[fixture_type] = fixture_types.get(fixture_type, 0) + 1
        
        info_lines = [
            f"MVR File: {Path(self.selected_file_path).name}",
            f"Total Fixtures: {total_count}",
            f"Selected for Import: {selected_count}",
            "",
            "Fixture Types Found:"
        ]
        
        for fixture_type, count in sorted(fixture_types.items()):
            info_lines.append(f"  • {fixture_type}: {count}")
        
        if selected_count > 0:
            info_lines.extend([
                "",
                "Next Steps:",
                "1. Review selected fixtures in the preview",
                "2. Click 'Import Selected Fixtures' to proceed",
                "3. Match fixture types to GDTF profiles",
                "4. Select attributes for analysis"
            ])
        
        self.info_text.setPlainText("\n".join(info_lines))
    
    def update_import_button_state(self):
        """Update the import button enabled state."""
        has_data = bool(self.fixtures)
        has_checked_rows = bool(self.preview_table.get_checked_rows()) if has_data else False
        
        # Enable import button only if we have data and checked rows
        button_enabled = has_data and has_checked_rows
        self.import_btn.setEnabled(button_enabled)
        
        # Update fixture count status
        if has_data:
            checked_count = len(self.preview_table.get_checked_rows())
            total_count = len(self.fixtures)
            self.fixture_count_status.setText(f"{checked_count}/{total_count} fixtures selected for import")
            self.fixture_count_status.setStyleSheet("color: green; font-weight: bold;")
        else:
            self.fixture_count_status.setText("No fixtures loaded")
            self.fixture_count_status.setStyleSheet("color: gray; font-style: italic;")
        
        # Update info text
        self.update_info_text()
    
    def import_mvr(self):
        """Import the selected fixtures."""
        try:
            # Get selected fixture indices
            selected_indices = self.preview_table.get_checked_rows()
            
            if not selected_indices:
                QMessageBox.warning(self, "No Selection", "Please select at least one fixture to import.")
                return
            
            # Get selected fixtures
            selected_fixtures = [self.fixtures[i] for i in selected_indices]
            
            # Convert to FixtureMatch objects using the fixture processing service
            fixture_matches = []
            for fixture_data in selected_fixtures:
                fixture_match = self.fixture_service._convert_raw_data_to_fixture_match(fixture_data)
                fixture_matches.append(fixture_match)
            
            if not fixture_matches:
                QMessageBox.warning(self, "No Data", "No valid fixture data found.")
                return
            
            # Emit success signal with processed fixtures
            self.import_successful.emit(fixture_matches)
            
            # Show success message
            skipped_count = len(selected_indices) - len(fixture_matches)
            message_lines = [
                f"Successfully imported {len(fixture_matches)} fixtures from MVR file.",
                "",
                f"• {len(fixture_matches)} fixtures imported"
            ]
            
            if skipped_count > 0:
                message_lines.append(f"• {skipped_count} invalid fixtures skipped")
            
            message_lines.extend([
                "",
                "Next steps:",
                "1. Load external GDTF profiles (if needed)",
                "2. Match fixture types to GDTF profiles",
                "3. Select attributes for analysis"
            ])
            
            QMessageBox.information(
                self,
                "Import Successful",
                "\n".join(message_lines)
            )
            
            # Close dialog
            self.accept()
            
        except Exception as e:
            QMessageBox.critical(self, "Import Error", f"Failed to import fixtures:\n{str(e)}")
            import traceback
            print(f"MVR import error: {traceback.format_exc()}")
    
    def add_row_selection_controls(self, layout: QVBoxLayout):
        """Add controls to select/deselect all rows and batch operations."""
        # Add to the right panel, above the preview table
        controls_layout = QHBoxLayout()
        
        # Row selection controls
        select_all_btn = QPushButton("Select All")
        select_all_btn.clicked.connect(self.select_all_fixtures)
        select_all_btn.setToolTip("Select all rows (Ctrl+A)")
        controls_layout.addWidget(select_all_btn)
        
        deselect_all_btn = QPushButton("Deselect All")
        deselect_all_btn.clicked.connect(self.deselect_all_fixtures)
        deselect_all_btn.setToolTip("Deselect all rows")
        controls_layout.addWidget(deselect_all_btn)
        
        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.VLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        controls_layout.addWidget(separator)
        
        # Batch operations for selected rows
        batch_check_btn = QPushButton("✓ Check Selected")
        batch_check_btn.clicked.connect(self.check_selected_fixtures)
        batch_check_btn.setToolTip("Check all selected rows for import")
        controls_layout.addWidget(batch_check_btn)
        
        batch_uncheck_btn = QPushButton("✗ Uncheck Selected")
        batch_uncheck_btn.clicked.connect(self.uncheck_selected_fixtures)
        batch_uncheck_btn.setToolTip("Uncheck all selected rows to exclude from import")
        controls_layout.addWidget(batch_uncheck_btn)
        
        # Separator
        separator2 = QFrame()
        separator2.setFrameShape(QFrame.Shape.VLine)
        separator2.setFrameShadow(QFrame.Shadow.Sunken)
        controls_layout.addWidget(separator2)
        
        # Check/Uncheck all rows operations
        check_all_btn = QPushButton("✓ Check All")
        check_all_btn.clicked.connect(self.check_all_fixtures)
        check_all_btn.setToolTip("Check all rows for import")
        controls_layout.addWidget(check_all_btn)
        
        uncheck_all_btn = QPushButton("✗ Uncheck All")
        uncheck_all_btn.clicked.connect(self.uncheck_all_fixtures)
        uncheck_all_btn.setToolTip("Uncheck all rows to exclude from import")
        controls_layout.addWidget(uncheck_all_btn)
        
        controls_layout.addStretch()
        
        # Add selection status label
        self.selection_status_label = QLabel("No rows selected")
        self.selection_status_label.setStyleSheet("color: #666; font-style: italic;")
        controls_layout.addWidget(self.selection_status_label)
        
        # Add the controls layout
        layout.addLayout(controls_layout)
        
        # Store buttons for enabling/disabling
        self.selection_buttons = [select_all_btn, deselect_all_btn, batch_check_btn, batch_uncheck_btn, check_all_btn, uncheck_all_btn]
        
        # Initially disable buttons
        for btn in self.selection_buttons:
            btn.setEnabled(False)
    
    def select_all_fixtures(self):
        """Select all fixtures in the table."""
        self.preview_table.selectAll()
        self.update_selection_status()
    
    def deselect_all_fixtures(self):
        """Deselect all fixtures in the table."""
        self.preview_table.clearSelection()
        self.update_selection_status()
    
    def check_selected_fixtures(self):
        """Check all selected fixtures."""
        self.preview_table.check_selected_rows()
        self.update_selection_status()
        self.update_import_button_state()
    
    def uncheck_selected_fixtures(self):
        """Uncheck all selected fixtures."""
        self.preview_table.uncheck_selected_rows()
        self.update_selection_status()
        self.update_import_button_state()
    
    def check_all_fixtures(self):
        """Check all fixtures for import."""
        self.preview_table.check_all_rows()
        self.update_selection_status()
        self.update_import_button_state()
    
    def uncheck_all_fixtures(self):
        """Uncheck all fixtures to exclude from import."""
        self.preview_table.uncheck_all_rows()
        self.update_selection_status()
        self.update_import_button_state()
    
    def update_selection_buttons_state(self):
        """Update the state of selection buttons."""
        has_data = bool(self.fixtures)
        for btn in self.selection_buttons:
            btn.setEnabled(has_data)
    
    def update_selection_status(self):
        """Update the selection status label."""
        if hasattr(self, 'selection_status_label'):
            selected_rows = self.preview_table.get_selected_rows()
            total_rows = self.preview_table.rowCount()
            
            if not selected_rows:
                self.selection_status_label.setText("No rows selected")
            elif len(selected_rows) == 1:
                self.selection_status_label.setText(f"Row {selected_rows[0] + 1} selected")
            elif len(selected_rows) == total_rows:
                self.selection_status_label.setText(f"All {total_rows} rows selected")
            else:
                self.selection_status_label.setText(f"{len(selected_rows)} of {total_rows} rows selected") 