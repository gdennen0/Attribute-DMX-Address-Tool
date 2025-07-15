"""
CSV Import Dialog - Clean UI for importing CSV files with column mapping and fixture ID generation.
Uses controller architecture for business logic.
"""

import os
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, 
    QPushButton, QComboBox, QGroupBox, QScrollArea, QWidget,
    QFileDialog, QMessageBox, QFrame, QTableWidget, QTableWidgetItem,
    QRadioButton, QButtonGroup, QSpinBox, QTextEdit, QSplitter
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QMouseEvent, QKeyEvent

from services.csv_service import CSVService


class SelectableTableWidget(QTableWidget):
    """Custom table widget with proper multi-row selection support."""
    
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
        # Emit signal or update parent as needed
        pass
    
    def get_selected_rows(self) -> List[int]:
        """Get list of currently selected row indices."""
        selected_rows = []
        for index in self.selectionModel().selectedRows():
            selected_rows.append(index.row())
        return sorted(selected_rows)
    
    def is_row_selected(self, row: int) -> bool:
        """Check if a row is selected."""
        return row in self.get_selected_rows()
    
    def keyPressEvent(self, event):
        """Handle keyboard events for shortcuts."""
        if event.key() == Qt.Key.Key_A and event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            # Ctrl+A - select all rows
            self.selectAll()
            event.accept()
            return
        
        # Call parent implementation
        super().keyPressEvent(event)
    
    def setup_table_data(self, headers: List[str], data_rows: List[List[str]]):
        """Set up the table with proper data and selection support."""
        if not headers or not data_rows:
            return
        
        # Add one extra column for checkboxes
        self.setRowCount(len(data_rows))
        self.setColumnCount(len(headers) + 1)
        
        # Set headers with checkbox column first
        table_headers = ['✓'] + headers
        self.setHorizontalHeaderLabels(table_headers)
        
        # Populate table with checkbox column and data
        for row_idx, row in enumerate(data_rows):
            # Add checkbox in first column
            checkbox_item = QTableWidgetItem()
            checkbox_item.setFlags(
                Qt.ItemFlag.ItemIsUserCheckable | 
                Qt.ItemFlag.ItemIsEnabled |
                Qt.ItemFlag.ItemIsSelectable
            )
            checkbox_item.setCheckState(Qt.CheckState.Checked)  # Default to checked
            checkbox_item.setToolTip("Uncheck to exclude this row from import")
            self.setItem(row_idx, 0, checkbox_item)
            
            # Add data in remaining columns
            for col_idx, cell in enumerate(row):
                if col_idx < len(headers):
                    item = QTableWidgetItem(str(cell))
                    item.setToolTip(str(cell))  # Show full content on hover
                    # CRUCIAL: Make items selectable but read-only
                    item.setFlags(
                        Qt.ItemFlag.ItemIsEnabled |
                        Qt.ItemFlag.ItemIsSelectable
                    )
                    self.setItem(row_idx, col_idx + 1, item)
        
        # Resize columns to content with reasonable limits
        self.resizeColumnsToContents()
        
        # Set checkbox column to fixed width
        self.setColumnWidth(0, 30)
        
        # Set maximum column width for data columns to prevent overly wide columns
        for col in range(1, self.columnCount()):
            current_width = self.columnWidth(col)
            if current_width > 200:
                self.setColumnWidth(col, 200)
        
        # Disable sorting for now (can be re-enabled if needed)
        self.setSortingEnabled(False)
    
    def get_checked_rows(self) -> List[int]:
        """Get list of row indices that have their checkbox checked."""
        checked_rows = []
        try:
            for row_idx in range(self.rowCount()):
                checkbox_item = self.item(row_idx, 0)
                if checkbox_item and checkbox_item.checkState() == Qt.CheckState.Checked:
                    checked_rows.append(row_idx)
        except Exception as e:
            print(f"ERROR in get_checked_rows: {e}")
        
        print(f"DEBUG: get_checked_rows() returning: {checked_rows}")
        return checked_rows
    
    def set_row_checked(self, row: int, checked: bool):
        """Set the checkbox state for a specific row."""
        if 0 <= row < self.rowCount():
            checkbox_item = self.item(row, 0)
            if checkbox_item:
                checkbox_item.setCheckState(Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked)
    
    def check_selected_rows(self):
        """Check all selected rows."""
        for row_idx in self.get_selected_rows():
            self.set_row_checked(row_idx, True)
    
    def uncheck_selected_rows(self):
        """Uncheck all selected rows."""
        for row_idx in self.get_selected_rows():
            self.set_row_checked(row_idx, False)
    
    def check_all_rows(self):
        """Check all rows."""
        for row_idx in range(self.rowCount()):
            self.set_row_checked(row_idx, True)
    
    def uncheck_all_rows(self):
        """Uncheck all rows."""
        for row_idx in range(self.rowCount()):
            self.set_row_checked(row_idx, False)


class CSVImportDialog(QDialog):
    """
    Dialog for importing CSV files with column mapping and fixture ID generation.
    """
    
    # Signal emitted when CSV import is successful
    import_successful = pyqtSignal(list)  # List of FixtureData objects
    
    def __init__(self, parent, config=None):
        super().__init__(parent)
        self.config = config
        self.csv_service = CSVService()
        self.headers = []
        self.data_rows = []
        self.column_mapping = {}
        self.fixture_id_config = {'method': 'sequential'}
        
        self.setup_ui()
        self.setModal(True)
        self.resize(1000, 700)
        
        # Load saved CSV directory if available
        if self.config:
            last_dir = self.config.get_last_csv_directory()
            if last_dir and os.path.exists(last_dir):
                self.last_csv_directory = last_dir
            else:
                self.last_csv_directory = ""
        else:
            self.last_csv_directory = ""
    
    def setup_ui(self):
        """Create the dialog user interface."""
        self.setWindowTitle("CSV Import")
        
        # Main layout
        main_layout = QVBoxLayout(self)
        
        # Create splitter for two-panel layout
        splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(splitter)
        
        # Left panel - Configuration
        left_panel = self.create_left_panel()
        splitter.addWidget(left_panel)
        
        # Right panel - Preview
        right_panel = self.create_right_panel()
        splitter.addWidget(right_panel)
        
        # Set splitter proportions
        splitter.setSizes([400, 600])
        
        # Dialog buttons
        button_layout = QHBoxLayout()
        
        self.import_btn = QPushButton("Import CSV")
        self.import_btn.clicked.connect(self.import_csv)
        self.import_btn.setEnabled(False)
        button_layout.addWidget(self.import_btn)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        button_layout.addStretch()
        main_layout.addLayout(button_layout)
    
    def create_left_panel(self) -> QWidget:
        """Create the left configuration panel."""
        panel = QFrame()
        panel.setFrameStyle(QFrame.Shape.StyledPanel)
        layout = QVBoxLayout(panel)
        
        # File selection
        file_group = QGroupBox("1. Select CSV File")
        file_layout = QVBoxLayout(file_group)
        
        self.file_label = QLabel("No file selected")
        self.file_label.setWordWrap(True)
        self.file_label.setStyleSheet("padding: 10px; border: 1px solid #ccc; border-radius: 4px;")
        file_layout.addWidget(self.file_label)
        
        browse_btn = QPushButton("Browse CSV File...")
        browse_btn.clicked.connect(self.browse_csv_file)
        file_layout.addWidget(browse_btn)
        
        layout.addWidget(file_group)
        
        # Column mapping
        self.mapping_group = QGroupBox("2. Column Mapping")
        self.mapping_layout = QVBoxLayout(self.mapping_group)
        
        self.mapping_scroll = QScrollArea()
        self.mapping_widget = QWidget()
        self.mapping_grid = QGridLayout(self.mapping_widget)
        self.mapping_scroll.setWidget(self.mapping_widget)
        self.mapping_scroll.setWidgetResizable(True)
        self.mapping_layout.addWidget(self.mapping_scroll)
        
        self.mapping_group.setEnabled(False)
        layout.addWidget(self.mapping_group)
        
        # Fixture ID generation
        self.id_group = QGroupBox("3. Fixture ID Generation")
        self.id_layout = QVBoxLayout(self.id_group)
        
        self.id_button_group = QButtonGroup()
        self.id_widgets = {}
        
        self.id_group.setEnabled(False)
        layout.addWidget(self.id_group)
        
        layout.addStretch()
        return panel
    
    def create_right_panel(self) -> QWidget:
        """Create the right preview panel."""
        panel = QFrame()
        panel.setFrameStyle(QFrame.Shape.StyledPanel)
        layout = QVBoxLayout(panel)
        
        # Preview label with usage instructions
        self.preview_label = QLabel("CSV Preview")
        self.preview_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        layout.addWidget(self.preview_label)
        
        # Usage instructions
        usage_label = QLabel("💡 Click to select rows • Shift+Click for range selection • Ctrl+Click to toggle • Ctrl+A to select all")
        usage_label.setStyleSheet("color: #666; font-size: 11px; margin-bottom: 5px;")
        layout.addWidget(usage_label)
        
        # Preview table - use custom table widget for shift-click selection
        self.preview_table = SelectableTableWidget()
        self.preview_table.setAlternatingRowColors(True)
        self.preview_table.horizontalHeader().setStretchLastSection(False)
        layout.addWidget(self.preview_table)
        
        # Info text
        self.info_text = QTextEdit()
        self.info_text.setMaximumHeight(150)
        self.info_text.setReadOnly(True)
        self.info_text.setPlainText("Select a CSV file to see preview and mapping options.")
        layout.addWidget(self.info_text)
        
        return panel
    
    def browse_csv_file(self):
        """Open file dialog to select CSV file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select CSV File",
            self.last_csv_directory,
            "CSV Files (*.csv);;All Files (*)"
        )
        
        if file_path:
            # Save directory for next time
            if self.config:
                self.config.set_last_csv_directory(str(Path(file_path).parent))
            self.last_csv_directory = str(Path(file_path).parent)
            self.load_csv_file(file_path)
    
    def load_csv_file(self, file_path: str):
        """Load and process CSV file."""
        try:
            # Update UI to show loading
            self.file_label.setText(f"Loading {Path(file_path).name}...")
            self.file_label.setStyleSheet("padding: 10px; border: 1px solid #2196F3; border-radius: 4px; background-color: #E3F2FD; color: #1976D2; font-weight: bold;")
            
            # Load CSV data
            self.headers, self.data_rows = self.csv_service.load_csv_file(file_path)
            
            # Update UI to show success
            self.file_label.setText(f"✓ {Path(file_path).name} ({len(self.data_rows)} rows loaded)")
            self.file_label.setStyleSheet("padding: 10px; border: 1px solid #4CAF50; border-radius: 4px; background-color: #E8F5E8; color: #2E7D32; font-weight: bold;")
            
            # Update preview
            self.update_preview()
            
            # Add row selection controls
            self.add_row_selection_controls()
            
            # Create column mapping interface
            self.create_column_mapping_interface()
            
            # Create fixture ID generation interface
            self.create_fixture_id_interface()
            
            # Enable controls
            self.mapping_group.setEnabled(True)
            self.id_group.setEnabled(True)
            
            # Update import button state
            self.update_import_button_state()
            
        except Exception as e:
            self.file_label.setText(f"✗ Error loading {Path(file_path).name}")
            self.file_label.setStyleSheet("padding: 10px; border: 1px solid #F44336; border-radius: 4px; background-color: #FFEBEE; color: #C62828; font-weight: bold;")
            QMessageBox.critical(self, "Error", f"Failed to load CSV file:\n{str(e)}")
    
    def update_preview(self):
        """Update the preview table with CSV data."""
        if not self.headers or not self.data_rows:
            return
        
        # Show all rows
        preview_rows = self.data_rows
        
        # Setup the table with data
        self.preview_table.setup_table_data(self.headers, preview_rows)
        
        # Connect checkbox changes to update info
        self.preview_table.itemChanged.connect(self.update_preview_info)
        self.preview_table.itemChanged.connect(self.update_import_button_state)
        
        # Update the preview info
        self.update_preview_info()
        
        # Initialize selection status
        self.update_selection_status()
        
        # Update import button state
        self.update_import_button_state()
    
    def update_preview_info(self):
        """Update the preview information display."""
        if not self.headers or not self.data_rows:
            return
        
        # Calculate statistics
        total_rows = len(self.data_rows)
        total_cols = len(self.headers)
        
        # Get checked rows
        checked_rows = self.preview_table.get_checked_rows()
        checked_count = len(checked_rows)
        
        # Check for empty cells in checked rows only
        empty_cells = 0
        non_empty_cells = 0
        
        for row_idx in checked_rows:
            if row_idx < len(self.data_rows):
                row = self.data_rows[row_idx]
                for cell in row:
                    if not str(cell).strip():
                        empty_cells += 1
                    else:
                        non_empty_cells += 1
        
        # Update preview label text
        if hasattr(self, 'preview_label'):
            self.preview_label.setText(
                f"CSV Preview - {checked_count}/{total_rows} rows checked × {total_cols} columns "
                f"({non_empty_cells} filled, {empty_cells} empty cells in checked rows)"
            )
        
        # Update info text
        self.update_info_text()
    
    def get_selected_rows(self) -> List[List[str]]:
        """Get only the rows that are checked in the preview table."""
        selected_rows = []
        
        checked_rows = self.preview_table.get_checked_rows()
        for row_idx in checked_rows:
            if row_idx < len(self.data_rows):
                selected_rows.append(self.data_rows[row_idx])
        
        return selected_rows
    
    def create_column_mapping_interface(self):
        """Create the column mapping interface."""
        # Clear existing widgets
        for i in reversed(range(self.mapping_grid.count())):
            self.mapping_grid.itemAt(i).widget().setParent(None)
        
        # Get suggested mappings
        suggested_mappings = self.csv_service.get_suggested_column_mapping(self.headers)
        
        # Required fields
        required_fields = {
            'name': 'Fixture Name',
            'universe': 'Universe',
            'dmx_address': 'DMX Address',
            'fixture_type': 'Fixture Type'
        }
        
        # Optional fields
        optional_fields = {
            'space': 'Space/Room',
            'description': 'Description',
            'arch_zone': 'Arch Zone',
            'desk_channel': 'Desk Channel',
            'mode': 'Mode',
            'note': 'Note'
        }
        
        # Create mapping controls
        self.mapping_widgets = {}
        
        # Headers
        self.mapping_grid.addWidget(QLabel("Field"), 0, 0)
        self.mapping_grid.addWidget(QLabel("CSV Column"), 0, 1)
        self.mapping_grid.addWidget(QLabel("Required"), 0, 2)
        
        row = 1
        
        # Required fields
        for field, display_name in required_fields.items():
            label = QLabel(display_name)
            label.setStyleSheet("font-weight: bold;")
            self.mapping_grid.addWidget(label, row, 0)
            
            combo = QComboBox()
            combo.addItem("-- Select Column --", -1)
            for i, header in enumerate(self.headers):
                combo.addItem(header, i)
            
            # Set suggested mapping
            if field in suggested_mappings:
                combo.setCurrentIndex(suggested_mappings[field] + 1)
            
            combo.currentIndexChanged.connect(self.update_column_mapping)
            self.mapping_widgets[field] = {'combo': combo}
            self.mapping_grid.addWidget(combo, row, 1)
            
            required_label = QLabel("Yes")
            required_label.setStyleSheet("color: red; font-weight: bold;")
            self.mapping_grid.addWidget(required_label, row, 2)
            
            row += 1
        
        # Optional fields
        for field, display_name in optional_fields.items():
            label = QLabel(display_name)
            self.mapping_grid.addWidget(label, row, 0)
            
            combo = QComboBox()
            combo.addItem("-- Select Column --", -1)
            for i, header in enumerate(self.headers):
                combo.addItem(header, i)
            
            # Set suggested mapping
            if field in suggested_mappings:
                combo.setCurrentIndex(suggested_mappings[field] + 1)
            
            combo.currentIndexChanged.connect(self.update_column_mapping)
            self.mapping_widgets[field] = {'combo': combo}
            self.mapping_grid.addWidget(combo, row, 1)
            
            optional_label = QLabel("No")
            optional_label.setStyleSheet("color: gray;")
            self.mapping_grid.addWidget(optional_label, row, 2)
            
            row += 1
        
        # Update initial mapping
        self.update_column_mapping()
    
    def create_fixture_id_interface(self):
        """Create the fixture ID generation interface."""
        # Clear existing widgets
        for i in reversed(range(self.id_layout.count())):
            widget = self.id_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)
        
        # Get generation options
        options = self.csv_service.get_fixture_id_generation_options()
        
        for option in options:
            radio = QRadioButton(option['name'])
            radio.setToolTip(option['description'])
            
            if option['method'] == 'sequential':
                radio.setChecked(True)  # Default selection
            
            self.id_button_group.addButton(radio)
            self.id_widgets[option['method']] = {'radio': radio}
            
            # Create layout for this option
            option_layout = QHBoxLayout()
            option_layout.addWidget(radio)
            
            # Add input widget if required
            if option.get('requires_input'):
                input_widget = QSpinBox()
                input_widget.setRange(1, 99999)
                input_widget.setValue(1)
                input_widget.setEnabled(False)
                
                label = QLabel(option['input_label'])
                option_layout.addWidget(label)
                option_layout.addWidget(input_widget)
                
                self.id_widgets[option['method']]['input'] = input_widget
                
                # Connect radio button to enable/disable input
                radio.toggled.connect(lambda checked, widget=input_widget: widget.setEnabled(checked))
            
            option_layout.addStretch()
            self.id_layout.addLayout(option_layout)
        
        # Connect radio buttons to update method
        for method, widgets in self.id_widgets.items():
            widgets['radio'].toggled.connect(lambda checked, m=method: self.update_fixture_id_method(m, checked))
    
    def update_column_mapping(self):
        """Update the column mapping from combo box selections."""
        self.column_mapping = {}
        
        # Get mapping from combo boxes - maps field names to CSV column indices
        for field_name, widgets in self.mapping_widgets.items():
            combo = widgets['combo']
            column_index = combo.currentData()
            if column_index is not None and column_index >= 0:  # -1 means "-- Select Column --"
                self.column_mapping[field_name] = column_index
        
        # Update info text and import button state
        self.update_info_text()
        self.update_import_button_state()
    
    def update_fixture_id_method(self, method: str, checked: bool):
        """Update the fixture ID generation method."""
        if checked:
            self.fixture_id_config['method'] = method
            # Update info text and import button state
            self.update_info_text()
            self.update_import_button_state()
    
    def update_info_text(self):
        """Update the info text display based on current configuration."""
        if not self.headers or not self.data_rows:
            self.info_text.setPlainText("Select a CSV file to see preview and mapping options.")
            return
        
        # Get checked rows
        checked_rows = self.preview_table.get_checked_rows()
        selected_rows = self.preview_table.get_selected_rows()
        
        info_parts = []
        
        # Data overview
        info_parts.append(f"📊 DATA OVERVIEW")
        info_parts.append(f"• Total rows: {len(self.data_rows)}")
        info_parts.append(f"• Checked rows: {len(checked_rows)}")
        info_parts.append(f"• Selected rows: {len(selected_rows)}")
        info_parts.append(f"• Total columns: {len(self.headers)}")
        
        # Column mapping status
        mapped_columns = len(self.column_mapping)
        info_parts.append(f"\n🔗 COLUMN MAPPING")
        info_parts.append(f"• Mapped columns: {mapped_columns}/{len(self.headers)}")
        
        # Required fields check
        required_fields = ['name', 'universe', 'dmx_address', 'fixture_type']
        missing_fields = []
        for field in required_fields:
            if field not in self.column_mapping:
                missing_fields.append(field)
        
        if missing_fields:
            info_parts.append(f"• Missing required mappings: {', '.join(missing_fields)}")
        else:
            info_parts.append("• All required fields mapped ✓")
        
        # Fixture ID generation
        info_parts.append(f"\n🔢 FIXTURE ID GENERATION")
        info_parts.append(f"• Method: {self.fixture_id_config.get('method', 'sequential')}")
        
        # Import readiness
        info_parts.append(f"\n📥 IMPORT STATUS")
        can_import = len(checked_rows) > 0 and len(missing_fields) == 0
        if can_import:
            info_parts.append("• Ready to import ✓")
        else:
            reasons = []
            if len(checked_rows) == 0:
                reasons.append("no rows checked")
            if len(missing_fields) > 0:
                reasons.append("missing required mappings")
            info_parts.append(f"• Cannot import: {', '.join(reasons)}")
        
        # Selection instructions
        info_parts.append(f"\n💡 SELECTION HELP")
        info_parts.append("• Click to select rows")
        info_parts.append("• Shift+Click for range selection")
        info_parts.append("• Ctrl+Click to toggle selection")
        info_parts.append("• Ctrl+A to select all")
        info_parts.append("• Use buttons to check/uncheck selected rows")
        
        self.info_text.setPlainText('\n'.join(info_parts))
    
    def update_import_button_state(self):
        """Update the import button enabled state based on current configuration."""
        # Check if we have required column mappings
        required_fields = ['name', 'universe', 'dmx_address', 'fixture_type']  # Match actual requirements
        all_required_mapped = all(field in self.column_mapping for field in required_fields)
        
        # Check if we have data
        has_data = bool(self.headers and self.data_rows)
        
        # Check if we have checked rows (not selected rows)
        has_checked_rows = bool(self.preview_table.get_checked_rows()) if has_data else False
        
        # Debug logging to understand the state
        print(f"DEBUG: Import button state check:")
        print(f"  - Column mapping: {self.column_mapping}")
        print(f"  - Required fields: {required_fields}")
        print(f"  - All required mapped: {all_required_mapped}")
        print(f"  - Has data: {has_data}")
        print(f"  - Has checked rows: {has_checked_rows}")
        if has_data:
            print(f"  - Checked rows: {self.preview_table.get_checked_rows()}")
        
        # Enable import button only if all conditions are met
        button_enabled = all_required_mapped and has_data and has_checked_rows
        print(f"  - Button enabled: {button_enabled}")
        self.import_btn.setEnabled(button_enabled)
    
    def import_csv(self):
        """Import the CSV data with current configuration."""
        try:
            # Validate required fields
            required_fields = ['name', 'universe', 'dmx_address', 'fixture_type']
            missing_fields = [field for field in required_fields if field not in self.column_mapping]
            
            if missing_fields:
                QMessageBox.warning(self, "Missing Fields", f"Please map the following required fields:\n{', '.join(missing_fields)}")
                return
            
            # Update fixture ID config if needed
            if self.fixture_id_config.get('method') == 'custom_start':
                method_widgets = self.id_widgets.get('custom_start', {})
                if 'input' in method_widgets:
                    self.fixture_id_config['start_number'] = method_widgets['input'].value()
            
            # Get selected rows
            selected_data_rows = self.get_selected_rows()
            
            # Create a temporary controller to use the unified approach
            from controllers.main_controller import MVRController
            temp_controller = MVRController()
            
            # Use the unified loading method
            result = temp_controller.load_fixtures_unified(
                'csv',
                headers=self.headers,
                data_rows=selected_data_rows,
                column_mapping=self.column_mapping,
                fixture_id_config=self.fixture_id_config
            )
            
            if not result["success"]:
                QMessageBox.critical(self, "Import Error", f"Failed to import CSV file:\n{result['error']}")
                return
            
            # Get the processed fixtures
            fixtures = temp_controller.matched_fixtures
            
            if not fixtures:
                QMessageBox.warning(self, "No Data", "No valid fixture data found in CSV file.")
                return
            
            # Emit success signal with processed fixtures
            self.import_successful.emit(fixtures)
            
            # Show success message with details
            skipped_rows = len(selected_data_rows) - len(fixtures)
            message_lines = [
                f"Successfully imported {len(fixtures)} fixtures from CSV file.",
                "",
                f"• {len(fixtures)} valid fixture rows imported"
            ]
            
            if skipped_rows > 0:
                message_lines.append(f"• {skipped_rows} invalid/blank rows skipped")
            
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
            QMessageBox.critical(self, "Import Error", f"Failed to import CSV file:\n{str(e)}")
            import traceback
            print(f"CSV import error: {traceback.format_exc()}")
    
    def get_last_csv_directory(self) -> str:
        """Get the last used CSV directory."""
        return self.last_csv_directory 

    def add_row_selection_controls(self):
        """Add controls to select/deselect all rows and batch operations."""
        # Add to the right panel, above the preview table
        controls_layout = QHBoxLayout()
        
        # Row selection controls
        select_all_btn = QPushButton("Select All")
        select_all_btn.clicked.connect(self.select_all_rows)
        select_all_btn.setToolTip("Select all rows (Ctrl+A)")
        controls_layout.addWidget(select_all_btn)
        
        deselect_all_btn = QPushButton("Deselect All")
        deselect_all_btn.clicked.connect(self.deselect_all_rows)
        deselect_all_btn.setToolTip("Deselect all rows")
        controls_layout.addWidget(deselect_all_btn)
        
        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.VLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        controls_layout.addWidget(separator)
        
        # Batch operations for selected rows
        batch_check_btn = QPushButton("✓ Check Selected")
        batch_check_btn.clicked.connect(self.check_selected_rows)
        batch_check_btn.setToolTip("Check all selected rows for import")
        controls_layout.addWidget(batch_check_btn)
        
        batch_uncheck_btn = QPushButton("✗ Uncheck Selected")
        batch_uncheck_btn.clicked.connect(self.uncheck_selected_rows)
        batch_uncheck_btn.setToolTip("Uncheck all selected rows to exclude from import")
        controls_layout.addWidget(batch_uncheck_btn)
        
        # Separator
        separator2 = QFrame()
        separator2.setFrameShape(QFrame.Shape.VLine)
        separator2.setFrameShadow(QFrame.Shadow.Sunken)
        controls_layout.addWidget(separator2)
        
        # Check/Uncheck all rows operations
        check_all_btn = QPushButton("✓ Check All")
        check_all_btn.clicked.connect(self.check_all_rows)
        check_all_btn.setToolTip("Check all rows for import")
        controls_layout.addWidget(check_all_btn)
        
        uncheck_all_btn = QPushButton("✗ Uncheck All")
        uncheck_all_btn.clicked.connect(self.uncheck_all_rows)
        uncheck_all_btn.setToolTip("Uncheck all rows to exclude from import")
        controls_layout.addWidget(uncheck_all_btn)
        
        controls_layout.addStretch()
        
        # Add selection status label
        self.selection_status_label = QLabel("No rows selected")
        self.selection_status_label.setStyleSheet("color: #666; font-style: italic;")
        controls_layout.addWidget(self.selection_status_label)
        
        # Insert before preview table
        right_panel_layout = self.preview_table.parent().layout()
        right_panel_layout.insertLayout(1, controls_layout)
        
        # Connect selection change to update status
        self.preview_table.selectionModel().selectionChanged.connect(self.update_selection_status)
    
    def select_all_rows(self):
        """Select all rows in the preview table."""
        self.preview_table.selectAll()
        self.update_selection_status()
    
    def deselect_all_rows(self):
        """Deselect all rows in the preview table."""
        self.preview_table.clearSelection()
        self.update_selection_status()
    
    def check_selected_rows(self):
        """Check all selected rows for import."""
        self.preview_table.check_selected_rows()
        self.update_selection_status()
        self.update_preview_info()
        self.update_import_button_state()
    
    def uncheck_selected_rows(self):
        """Uncheck all selected rows to exclude from import."""
        self.preview_table.uncheck_selected_rows()
        self.update_selection_status()
        self.update_preview_info()
        self.update_import_button_state()
    
    def check_all_rows(self):
        """Check all rows for import."""
        self.preview_table.check_all_rows()
        self.update_selection_status()
        self.update_preview_info()
        self.update_import_button_state()
    
    def uncheck_all_rows(self):
        """Uncheck all rows to exclude from import."""
        self.preview_table.uncheck_all_rows()
        self.update_selection_status()
        self.update_preview_info()
        self.update_import_button_state()
    
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