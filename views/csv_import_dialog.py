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
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

from services.csv_service import CSVService


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
        
        # Preview label
        self.preview_label = QLabel("CSV Preview")
        self.preview_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        layout.addWidget(self.preview_label)
        
        # Preview table
        self.preview_table = QTableWidget()
        self.preview_table.setAlternatingRowColors(True)
        self.preview_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
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
        
        # Add one extra column for checkboxes
        self.preview_table.setRowCount(len(preview_rows))
        self.preview_table.setColumnCount(len(self.headers) + 1)
        
        # Set headers with checkbox column first
        headers = ['✓'] + self.headers
        self.preview_table.setHorizontalHeaderLabels(headers)
        
        # Populate table with checkbox column and data
        for row_idx, row in enumerate(preview_rows):
            # Add checkbox in first column
            checkbox_item = QTableWidgetItem()
            checkbox_item.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
            checkbox_item.setCheckState(Qt.CheckState.Checked)  # Default to checked
            checkbox_item.setToolTip("Uncheck to exclude this row from import")
            self.preview_table.setItem(row_idx, 0, checkbox_item)
            
            # Add data in remaining columns
            for col_idx, cell in enumerate(row):
                if col_idx < len(self.headers):
                    item = QTableWidgetItem(str(cell))
                    item.setToolTip(str(cell))  # Show full content on hover
                    item.setFlags(Qt.ItemFlag.ItemIsEnabled)  # Make read-only
                    self.preview_table.setItem(row_idx, col_idx + 1, item)
        
        # Resize columns to content with reasonable limits
        self.preview_table.resizeColumnsToContents()
        
        # Set checkbox column to fixed width
        self.preview_table.setColumnWidth(0, 30)
        
        # Set maximum column width for data columns to prevent overly wide columns
        for col in range(1, self.preview_table.columnCount()):
            current_width = self.preview_table.columnWidth(col)
            if current_width > 200:
                self.preview_table.setColumnWidth(col, 200)
        
        # Disable sorting for checkbox column, enable for others
        self.preview_table.setSortingEnabled(False)  # We'll manage this manually
        
        # Connect checkbox changes to update info
        self.preview_table.itemChanged.connect(self.update_preview_info)
        
        # Update the preview info
        self.update_preview_info()
    
    def update_preview_info(self):
        """Update the preview information display."""
        if not self.headers or not self.data_rows:
            return
        
        # Calculate statistics
        total_rows = len(self.data_rows)
        total_cols = len(self.headers)
        
        # Count checked rows
        checked_rows = 0
        for row_idx in range(self.preview_table.rowCount()):
            checkbox_item = self.preview_table.item(row_idx, 0)
            if checkbox_item and checkbox_item.checkState() == Qt.CheckState.Checked:
                checked_rows += 1
        
        # Check for empty cells in checked rows only
        empty_cells = 0
        non_empty_cells = 0
        
        for row_idx, row in enumerate(self.data_rows):
            # Only count if row is checked
            checkbox_item = self.preview_table.item(row_idx, 0)
            if checkbox_item and checkbox_item.checkState() == Qt.CheckState.Checked:
                for cell in row:
                    if not cell.strip():
                        empty_cells += 1
                    else:
                        non_empty_cells += 1
        
        # Update preview label text
        if hasattr(self, 'preview_label'):
            self.preview_label.setText(
                f"CSV Preview - {checked_rows}/{total_rows} rows selected × {total_cols} columns "
                f"({non_empty_cells} filled, {empty_cells} empty cells in selected rows)"
            )
        
        # Update info text
        self.update_info_text()
    
    def get_selected_rows(self) -> List[List[str]]:
        """Get only the rows that are checked in the preview table."""
        selected_rows = []
        
        for row_idx in range(self.preview_table.rowCount()):
            checkbox_item = self.preview_table.item(row_idx, 0)
            if checkbox_item and checkbox_item.checkState() == Qt.CheckState.Checked:
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
        self.mapping_combos = {}
        
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
            self.mapping_combos[field] = combo
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
            self.mapping_combos[field] = combo
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
        """Update the column mapping when selections change."""
        self.column_mapping = {}
        
        for field, combo in self.mapping_combos.items():
            index = combo.currentData()
            if index >= 0:
                self.column_mapping[field] = index
        
        self.update_info_text()
        self.update_import_button_state()
    
    def update_fixture_id_method(self, method: str, checked: bool):
        """Update the fixture ID generation method."""
        if checked:
            self.fixture_id_config['method'] = method
            
            # Update start number if custom_start method
            if method == 'custom_start' and 'input' in self.id_widgets[method]:
                self.fixture_id_config['start_number'] = self.id_widgets[method]['input'].value()
        
        self.update_info_text()
        self.update_import_button_state()
    
    def update_info_text(self):
        """Update the info text with current configuration."""
        if not self.headers or not self.data_rows:
            return
        
        # Get selected rows
        selected_rows = self.get_selected_rows()
        
        info_lines = []
        info_lines.append(f"CSV File: {len(selected_rows)}/{len(self.data_rows)} rows selected, {len(self.headers)} columns")
        info_lines.append("")
        
        # Column mapping status
        info_lines.append("Column Mapping:")
        required_fields = ['name', 'universe', 'dmx_address', 'fixture_type']
        mapped_required = sum(1 for field in required_fields if field in self.column_mapping)
        info_lines.append(f"  Required fields mapped: {mapped_required}/{len(required_fields)}")
        
        optional_mapped = sum(1 for field, _ in self.column_mapping.items() if field not in required_fields)
        info_lines.append(f"  Optional fields mapped: {optional_mapped}")
        info_lines.append("")
        
        # Data validation preview (for selected rows only)
        if mapped_required == len(required_fields) and selected_rows:
            valid_rows = 0
            invalid_rows = 0
            
            for row in selected_rows:
                if self.csv_service._is_valid_fixture_row(row, self.column_mapping):
                    valid_rows += 1
                else:
                    invalid_rows += 1
            
            info_lines.append(f"Data Validation (Selected Rows):")
            info_lines.append(f"  Valid fixture rows: {valid_rows}")
            if invalid_rows > 0:
                info_lines.append(f"  Invalid/blank rows: {invalid_rows} (will be skipped)")
            info_lines.append("")
        
        # Fixture ID generation
        method = self.fixture_id_config.get('method', 'sequential')
        method_name = next((opt['name'] for opt in self.csv_service.get_fixture_id_generation_options() if opt['method'] == method), method)
        info_lines.append(f"Fixture ID Generation: {method_name}")
        
        if method == 'custom_start':
            start_num = self.fixture_id_config.get('start_number', 1)
            info_lines.append(f"  Starting from: {start_num}")
        
        info_lines.append("")
        
        # Ready status
        if not selected_rows:
            info_lines.append("⚠ No rows selected for import")
        elif mapped_required == len(required_fields):
            info_lines.append("✓ Ready to import")
        else:
            missing = [field for field in required_fields if field not in self.column_mapping]
            info_lines.append(f"⚠ Missing required fields: {', '.join(missing)}")
        
        self.info_text.setPlainText('\n'.join(info_lines))
    
    def update_import_button_state(self):
        """Update the import button enabled state based on current configuration."""
        required_fields = ['name', 'universe', 'dmx_address', 'fixture_type']
        all_required_mapped = all(field in self.column_mapping for field in required_fields)
        has_data = bool(self.headers and self.data_rows)
        has_selected_rows = bool(self.get_selected_rows()) if has_data else False
        
        self.import_btn.setEnabled(all_required_mapped and has_data and has_selected_rows)
    
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
            from controllers import MVRController
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
        """Add controls to select/deselect all rows."""
        # Add to the right panel, above the preview table
        controls_layout = QHBoxLayout()
        
        select_all_btn = QPushButton("Select All")
        select_all_btn.clicked.connect(self.select_all_rows)
        controls_layout.addWidget(select_all_btn)
        
        deselect_all_btn = QPushButton("Deselect All")
        deselect_all_btn.clicked.connect(self.deselect_all_rows)
        controls_layout.addWidget(deselect_all_btn)
        
        controls_layout.addStretch()
        
        # Insert before preview table
        right_panel_layout = self.preview_table.parent().layout()
        right_panel_layout.insertLayout(1, controls_layout)
    
    def select_all_rows(self):
        """Select all rows in the preview table."""
        for row_idx in range(self.preview_table.rowCount()):
            checkbox_item = self.preview_table.item(row_idx, 0)
            if checkbox_item:
                checkbox_item.setCheckState(Qt.CheckState.Checked)
    
    def deselect_all_rows(self):
        """Deselect all rows in the preview table."""
        for row_idx in range(self.preview_table.rowCount()):
            checkbox_item = self.preview_table.item(row_idx, 0)
            if checkbox_item:
                checkbox_item.setCheckState(Qt.CheckState.Unchecked) 