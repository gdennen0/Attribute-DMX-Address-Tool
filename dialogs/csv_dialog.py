"""
Simple CSV import dialog.
Allows users to select CSV file, map columns, and choose fixtures to import.
"""

from typing import List, Dict, Any, Optional
from pathlib import Path
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QFileDialog, QMessageBox, QTableWidget, QTableWidgetItem,
    QCheckBox, QHeaderView, QComboBox, QGroupBox, QGridLayout,
    QSpinBox, QTextEdit, QProgressBar
)
from PyQt6.QtCore import Qt, pyqtSignal

import core
from .gdtf_dialog import GDTFMatchingDialog


class CSVImportDialog(QDialog):
    """Simple dialog for importing CSV files with column mapping."""
    
    fixtures_imported = pyqtSignal(list)  # List of selected fixtures
    
    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.config = config
        self.csv_data = {}
        self.fixtures = []
        self.column_mapping = {}
        
        self.setWindowTitle("Import CSV File")
        self.setMinimumSize(900, 700)
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Set up the user interface."""
        layout = QVBoxLayout(self)
        
        # File selection
        file_layout = QHBoxLayout()
        self.file_label = QLabel("No file selected")
        self.browse_button = QPushButton("Browse CSV File...")
        self.browse_button.clicked.connect(self._browse_file)
        
        file_layout.addWidget(QLabel("CSV File:"))
        file_layout.addWidget(self.file_label, 1)
        file_layout.addWidget(self.browse_button)
        layout.addLayout(file_layout)
        
        # Column mapping
        self.mapping_group = QGroupBox("Column Mapping")
        self._setup_mapping_ui()
        layout.addWidget(self.mapping_group)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # Status text
        self.status_text = QTextEdit()
        self.status_text.setMaximumHeight(80)
        self.status_text.setReadOnly(True)
        layout.addWidget(self.status_text)
        
        # Preview/fixtures table
        self.preview_label = QLabel("CSV Preview:")
        layout.addWidget(self.preview_label)
        self.data_table = QTableWidget()
        self._setup_table()
        layout.addWidget(self.data_table)
        
        # Selection and role assignment buttons
        selection_layout = QHBoxLayout()
        self.select_all_button = QPushButton("Select All")
        self.select_none_button = QPushButton("Select None")
        self.gdtf_matching_button = QPushButton("GDTF Profile Matching...")
        self.set_as_master_button = QPushButton("Set Selected as Master")
        self.set_as_remote_button = QPushButton("Set Selected as Remote")
        
        self.select_all_button.clicked.connect(self._select_all)
        self.select_none_button.clicked.connect(self._select_none)
        self.gdtf_matching_button.clicked.connect(self._open_gdtf_matching)
        self.set_as_master_button.clicked.connect(self._set_selected_as_master)
        self.set_as_remote_button.clicked.connect(self._set_selected_as_remote)
        
        self.select_all_button.setEnabled(False)
        self.select_none_button.setEnabled(False)
        self.gdtf_matching_button.setEnabled(False)
        self.set_as_master_button.setEnabled(False)
        self.set_as_remote_button.setEnabled(False)
        
        selection_layout.addWidget(self.select_all_button)
        selection_layout.addWidget(self.select_none_button)
        selection_layout.addWidget(self.gdtf_matching_button)
        selection_layout.addStretch()
        selection_layout.addWidget(self.set_as_master_button)
        selection_layout.addWidget(self.set_as_remote_button)
        layout.addLayout(selection_layout)
        
        # Dialog buttons
        button_layout = QHBoxLayout()
        self.parse_button = QPushButton("Parse CSV")
        self.import_button = QPushButton("Import Selected")
        self.cancel_button = QPushButton("Cancel")
        
        self.parse_button.clicked.connect(self._parse_csv)
        self.import_button.clicked.connect(self._import_fixtures)
        self.cancel_button.clicked.connect(self.reject)
        
        self.parse_button.setEnabled(False)
        self.import_button.setEnabled(False)
        
        button_layout.addStretch()
        button_layout.addWidget(self.parse_button)
        button_layout.addWidget(self.import_button)
        button_layout.addWidget(self.cancel_button)
        layout.addLayout(button_layout)
    
    def _setup_mapping_ui(self):
        """Set up column mapping interface."""
        mapping_layout = QGridLayout(self.mapping_group)
        
        # Column mapping controls
        self.mapping_combos = {}
        required_fields = ['name', 'type', 'mode', 'address', 'fixture_id']
        field_labels = {
            'name': 'Fixture Name:',
            'type': 'Fixture Type:',
            'mode': 'DMX Mode:',
            'address': 'Base Address:',
            'fixture_id': 'Fixture ID:'
        }
        
        for i, field in enumerate(required_fields):
            label = QLabel(field_labels[field])
            combo = QComboBox()
            combo.addItem("-- Select Column --", "")
            combo.currentTextChanged.connect(self._update_parse_button)
            
            self.mapping_combos[field] = combo
            mapping_layout.addWidget(label, i, 0)
            mapping_layout.addWidget(combo, i, 1)
        
        # Fixture ID start number
        mapping_layout.addWidget(QLabel("Start Fixture ID:"), len(required_fields), 0)
        self.start_id_spin = QSpinBox()
        self.start_id_spin.setRange(1, 9999)
        self.start_id_spin.setValue(1)
        mapping_layout.addWidget(self.start_id_spin, len(required_fields), 1)
    
    def _setup_table(self):
        """Set up the data table."""
        self.data_table.setAlternatingRowColors(True)
        self.data_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
    
    def _browse_file(self):
        """Browse for CSV file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select CSV File",
            self.config.get_last_csv_directory(),
            "CSV Files (*.csv)"
        )
        
        if file_path:
            self.config.set_last_csv_directory(str(Path(file_path).parent))
            self._load_csv_file(file_path)
    
    def _load_csv_file(self, file_path: str):
        """Load and preview CSV file."""
        self.file_label.setText(Path(file_path).name)
        self.csv_file_path = file_path
        
        try:
            # Get CSV preview
            self.csv_data = core.get_csv_preview(file_path, max_rows=20)
            
            if 'error' in self.csv_data:
                QMessageBox.warning(self, "Error", self.csv_data['error'])
                return
            
            # Update column mapping options
            self._update_mapping_options(self.csv_data['headers'])
            
            # Show preview
            self._show_csv_preview()
            
            self.status_text.append(f"Loaded CSV file: {Path(file_path).name}")
            
        except Exception as e:
            error_msg = f"Failed to load CSV file: {str(e)}"
            QMessageBox.critical(self, "Error", error_msg)
            self.status_text.append(f"Error: {error_msg}")
    
    def _update_mapping_options(self, headers: List[str]):
        """Update column mapping dropdown options."""
        # Clear existing options
        for combo in self.mapping_combos.values():
            combo.clear()
            combo.addItem("-- Select Column --", "")
            for header in headers:
                combo.addItem(header, header)
        
        # Auto-guess column mapping
        guessed_mapping = core.create_column_mapping(headers)
        for field, header in guessed_mapping.items():
            if header and field in self.mapping_combos:
                combo = self.mapping_combos[field]
                index = combo.findData(header)
                if index >= 0:
                    combo.setCurrentIndex(index)
        
        self._update_parse_button()
    
    def _show_csv_preview(self):
        """Show CSV preview in table."""
        if not self.csv_data or 'headers' not in self.csv_data:
            return
        
        headers = self.csv_data['headers']
        data_rows = self.csv_data['data_rows']
        
        if not headers:
            self.preview_label.setText("CSV Preview: No headers found")
            return
        
        # Set up table
        self.data_table.setColumnCount(len(headers))
        self.data_table.setHorizontalHeaderLabels(headers)
        self.data_table.setRowCount(len(data_rows))
        
        # Populate with data
        for row_idx, row_data in enumerate(data_rows):
            for col_idx, cell_data in enumerate(row_data):
                if col_idx < len(headers):
                    item = QTableWidgetItem(str(cell_data))
                    item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
                    self.data_table.setItem(row_idx, col_idx, item)
        
        # Resize columns
        self.data_table.resizeColumnsToContents()
        self.preview_label.setText(f"CSV Preview (showing first {len(data_rows)} rows):")
    
    def _update_parse_button(self):
        """Update parse button state."""
        # Check if required mappings are set
        required_fields = ['name', 'type', 'address']
        has_required = all(
            self.mapping_combos[field].currentData() 
            for field in required_fields
        )
        
        self.parse_button.setEnabled(has_required and hasattr(self, 'csv_file_path'))
    
    def _parse_csv(self):
        """Parse CSV file with current column mapping."""
        if not hasattr(self, 'csv_file_path'):
            return
        
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)
        self.status_text.append("Parsing CSV file...")
        
        try:
            # Build column mapping
            self.column_mapping = {}
            for field, combo in self.mapping_combos.items():
                mapped_column = combo.currentData()
                if mapped_column:
                    self.column_mapping[field] = mapped_column
            
            # Parse CSV
            result = core.parse_csv_file(
                self.csv_file_path, 
                self.column_mapping,
                self.start_id_spin.value()
            )
            
            if 'error' in result:
                QMessageBox.warning(self, "Error", result['error'])
                return
            
            self.fixtures = result['fixtures']
            
            # Load external GDTF profiles for matching
            external_folder = self.config.get_external_gdtf_folder()
            gdtf_profiles = {}
            if external_folder:
                self.status_text.append("Loading GDTF profiles for matching...")
                gdtf_profiles = core.parse_external_gdtf_folder(external_folder)
            
            # Auto-match fixtures if GDTF profiles available
            if gdtf_profiles:
                self.status_text.append("Auto-matching fixtures to GDTF profiles...")
                core.auto_match_fixtures(self.fixtures, gdtf_profiles)
            
            # Update table to show fixtures
            self._show_fixtures_table()
            
            # Show summary
            summary = core.get_match_summary(self.fixtures)
            self.status_text.append(f"Parsed {summary['total']} fixtures, {summary['matched']} matched ({summary['match_rate']:.1f}%)")
            
            # Enable selection and role assignment buttons
            self.select_all_button.setEnabled(True)
            self.select_none_button.setEnabled(True)
            self.gdtf_matching_button.setEnabled(True)
            self.set_as_master_button.setEnabled(True)
            self.set_as_remote_button.setEnabled(True)
            
        except Exception as e:
            error_msg = f"Failed to parse CSV: {str(e)}"
            QMessageBox.critical(self, "Error", error_msg)
            self.status_text.append(f"Error: {error_msg}")
        
        finally:
            self.progress_bar.setVisible(False)
    
    def _show_fixtures_table(self):
        """Show parsed fixtures in table with checkboxes."""
        headers = ["Select", "Name", "Type", "Mode", "Address", "ID", "Role", "Status"]
        self.data_table.setColumnCount(len(headers))
        self.data_table.setHorizontalHeaderLabels(headers)
        self.data_table.setRowCount(len(self.fixtures))
        
        for row, fixture in enumerate(self.fixtures):
            # Checkbox
            checkbox = QCheckBox()
            checkbox.setChecked(fixture.get('selected', True))
            checkbox.stateChanged.connect(lambda state, r=row: self._checkbox_changed(r, state))
            self.data_table.setCellWidget(row, 0, checkbox)
            
            # Fixture data
            self.data_table.setItem(row, 1, QTableWidgetItem(fixture.get('name', '')))
            self.data_table.setItem(row, 2, QTableWidgetItem(fixture.get('type', '')))
            self.data_table.setItem(row, 3, QTableWidgetItem(fixture.get('mode', '')))
            self.data_table.setItem(row, 4, QTableWidgetItem(str(fixture.get('base_address', 1))))
            self.data_table.setItem(row, 5, QTableWidgetItem(str(fixture.get('fixture_id', 0))))
            
            # Role
            role = core.get_fixture_role(fixture)
            role_item = QTableWidgetItem(role.title())
            if role == 'unassigned':
                role_item.setBackground(Qt.GlobalColor.yellow)
            elif role == 'master':
                role_item.setBackground(Qt.GlobalColor.green)
            elif role == 'remote':
                role_item.setBackground(Qt.GlobalColor.cyan)
            self.data_table.setItem(row, 6, role_item)
            
            # Status
            status = "Matched" if fixture.get('matched') else "Unmatched"
            status_item = QTableWidgetItem(status)
            if fixture.get('matched'):
                status_item.setBackground(Qt.GlobalColor.green)
            else:
                status_item.setBackground(Qt.GlobalColor.lightGray)
            self.data_table.setItem(row, 7, status_item)
        
        # Resize columns
        header = self.data_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        for i in range(3, len(headers)):
            header.setSectionResizeMode(i, QHeaderView.ResizeMode.ResizeToContents)
        self.data_table.setColumnWidth(0, 60)
        
        self.preview_label.setText("Parsed Fixtures:")
        self._update_import_button()
    
    def _checkbox_changed(self, row: int, state: int):
        """Handle checkbox state change."""
        if row < len(self.fixtures):
            selected = state == Qt.CheckState.Checked.value
            core.set_fixture_selected(self.fixtures[row], selected)
        self._update_import_button()
    
    def _select_all(self):
        """Select all fixtures."""
        for row in range(self.data_table.rowCount()):
            checkbox = self.data_table.cellWidget(row, 0)
            if checkbox:
                checkbox.setChecked(True)
    
    def _select_none(self):
        """Deselect all fixtures."""
        for row in range(self.data_table.rowCount()):
            checkbox = self.data_table.cellWidget(row, 0)
            if checkbox:
                checkbox.setChecked(False)
    
    def _set_selected_as_master(self):
        """Set selected fixtures as master role."""
        selected_count = 0
        for row in range(self.data_table.rowCount()):
            checkbox = self.data_table.cellWidget(row, 0)
            if checkbox and checkbox.isChecked() and row < len(self.fixtures):
                fixture = self.fixtures[row]
                core.set_fixture_role(fixture, 'master')
                selected_count += 1
        
        if selected_count > 0:
            self._show_fixtures_table()  # Refresh table to show updated roles
            self.status_text.append(f"Set {selected_count} fixture{'s' if selected_count != 1 else ''} as master")
        else:
            QMessageBox.information(self, "No Selection", "Please select fixtures to set as master.")
    
    def _set_selected_as_remote(self):
        """Set selected fixtures as remote role."""
        selected_count = 0
        for row in range(self.data_table.rowCount()):
            checkbox = self.data_table.cellWidget(row, 0)
            if checkbox and checkbox.isChecked() and row < len(self.fixtures):
                fixture = self.fixtures[row]
                core.set_fixture_role(fixture, 'remote')
                selected_count += 1
        
        if selected_count > 0:
            self._show_fixtures_table()  # Refresh table to show updated roles
            self.status_text.append(f"Set {selected_count} fixture{'s' if selected_count != 1 else ''} as remote")
        else:
            QMessageBox.information(self, "No Selection", "Please select fixtures to set as remote.")
    
    def _open_gdtf_matching(self):
        """Open the GDTF profile matching dialog."""
        if not self.fixtures:
            QMessageBox.information(self, "No Fixtures", "Please parse the CSV file first.")
            return
        
        dialog = GDTFMatchingDialog(self.fixtures, self.config, self)
        result = dialog.exec()
        
        if result == QDialog.DialogCode.Accepted:
            # Apply the matches to fixtures
            updated_count = dialog.apply_matches_to_fixtures()
            
            if updated_count > 0:
                # Refresh the fixtures table to show updated match status
                self._show_fixtures_table()
                
                # Show updated summary
                summary = core.get_match_summary(self.fixtures)
                self.status_text.append(f"GDTF matching complete: {summary['matched']}/{summary['total']} fixtures matched ({summary['match_rate']:.1f}%)")
            else:
                self.status_text.append("No GDTF matches were applied")
    
    def _update_import_button(self):
        """Update import button state based on selection."""
        if not self.fixtures:
            self.import_button.setEnabled(False)
            return
        
        selected_count = 0
        for row in range(self.data_table.rowCount()):
            checkbox = self.data_table.cellWidget(row, 0)
            if checkbox and checkbox.isChecked():
                selected_count += 1
        
        self.import_button.setEnabled(selected_count > 0)
        self.import_button.setText(f"Import Selected ({selected_count})")
    
    def _import_fixtures(self):
        """Import selected fixtures."""
        selected_fixtures = []
        
        for row in range(self.data_table.rowCount()):
            checkbox = self.data_table.cellWidget(row, 0)
            if checkbox and checkbox.isChecked():
                fixture = self.fixtures[row]
                core.set_fixture_selected(fixture, True)
                selected_fixtures.append(fixture)
            else:
                core.set_fixture_selected(self.fixtures[row], False)
        
        if selected_fixtures:
            self.fixtures_imported.emit(selected_fixtures)
            self.accept()
        else:
            QMessageBox.information(self, "No Selection", "Please select at least one fixture to import.") 