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
from .attribute_selection_dialog import AttributeSelectionDialog


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
        self.toggle_selected_button = QPushButton("Toggle Selected")
        self.gdtf_matching_button = QPushButton("GDTF Profile Matching...")
        self.set_as_master_button = QPushButton("Set Selected as Master")
        self.set_as_remote_button = QPushButton("Set Selected as Remote")
        
        self.select_all_button.clicked.connect(self._select_all)
        self.select_none_button.clicked.connect(self._select_none)
        self.toggle_selected_button.clicked.connect(self._toggle_selected)
        self.gdtf_matching_button.clicked.connect(self._open_gdtf_matching)
        self.set_as_master_button.clicked.connect(self._set_selected_as_master)
        self.set_as_remote_button.clicked.connect(self._set_selected_as_remote)
        
        self.select_all_button.setEnabled(False)
        self.select_none_button.setEnabled(False)
        self.toggle_selected_button.setEnabled(False)
        self.gdtf_matching_button.setEnabled(False)
        self.set_as_master_button.setEnabled(False)
        self.set_as_remote_button.setEnabled(False)
        
        selection_layout.addWidget(self.select_all_button)
        selection_layout.addWidget(self.select_none_button)
        selection_layout.addWidget(self.toggle_selected_button)
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
        required_fields = ['name', 'type', 'mode', 'universe', 'address', 'fixture_id']
        field_labels = {
            'name': 'Fixture Name:',
            'type': 'Fixture Type:',
            'mode': 'DMX Mode:',
            'universe': 'Universe:',
            'address': 'Address:',
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
    
    def _setup_table(self):
        """Set up the data table."""
        self.data_table.setAlternatingRowColors(True)
        self.data_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.data_table.setSelectionMode(QTableWidget.SelectionMode.ExtendedSelection)
        
        # Set table properties for better display
        self.data_table.setShowGrid(True)
        self.data_table.setGridStyle(Qt.PenStyle.SolidLine)
        
        # Set header properties
        header = self.data_table.horizontalHeader()
        header.setStretchLastSection(False)
        header.setDefaultAlignment(Qt.AlignmentFlag.AlignLeft)
    
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
        
        # Resize columns for CSV preview
        header = self.data_table.horizontalHeader()
        # Reset all column resize modes first
        for i in range(len(headers)):
            header.setSectionResizeMode(i, QHeaderView.ResizeMode.Interactive)
        
        # For CSV preview, use ResizeToContents for all columns
        for i in range(len(headers)):
            header.setSectionResizeMode(i, QHeaderView.ResizeMode.ResizeToContents)
        
        self.preview_label.setText(f"CSV Preview (showing first {len(data_rows)} rows):")
    
    def _update_parse_button(self):
        """Update parse button state."""
        # Check if required mappings are set
        required_fields = ['name', 'type']
        has_required = all(
            self.mapping_combos[field].currentData() 
            for field in required_fields
        )
        
        # Check if we have either universe+address or just address
        has_universe = bool(self.mapping_combos['universe'].currentData())
        has_address = bool(self.mapping_combos['address'].currentData())
        
        # Need either both universe and address, or just address
        has_addressing = (has_universe and has_address) or has_address
        
        self.parse_button.setEnabled(has_required and has_addressing and hasattr(self, 'csv_file_path'))
    
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
            
            # Parse CSV with fixture ID validation
            result = core.parse_csv_file_with_fixture_id_validation(
                self.csv_file_path, 
                self.column_mapping,
                1  # Start with ID 1
            )
            
            if 'error' in result:
                QMessageBox.warning(self, "Error", result['error'])
                return
            
            self.fixtures = result['fixtures']
            
            # Check for invalid fixture IDs and prompt user
            invalid_fixtures = [f for f in self.fixtures if f.get('fixture_id_invalid', False)]
            if invalid_fixtures:
                self._handle_invalid_fixture_ids(invalid_fixtures)
            
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
            self.toggle_selected_button.setEnabled(True)
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
        headers = ["Select", "Name", "Type", "Mode", "Universe", "Channel", "ID", "Role", "Status"]
        self.data_table.setColumnCount(len(headers))
        self.data_table.setHorizontalHeaderLabels(headers)
        self.data_table.setRowCount(len(self.fixtures))
        
        for row, fixture in enumerate(self.fixtures):
            # Checkbox
            checkbox = QCheckBox()
            checkbox.setChecked(fixture.get('selected', True))
            checkbox.stateChanged.connect(lambda state, r=row: self._checkbox_changed(r, state))
            
            # Center the checkbox in the cell
            checkbox.setStyleSheet("QCheckBox { margin: auto; }")
            self.data_table.setCellWidget(row, 0, checkbox)
            
            # Fixture data
            self.data_table.setItem(row, 1, QTableWidgetItem(fixture.get('name', '')))
            self.data_table.setItem(row, 2, QTableWidgetItem(fixture.get('type', '')))
            self.data_table.setItem(row, 3, QTableWidgetItem(fixture.get('mode', '')))
            # Show universe and channel values
            csv_universe = fixture.get('csv_universe', 1)
            csv_channel = fixture.get('csv_channel', fixture.get('base_address', 1))
            self.data_table.setItem(row, 4, QTableWidgetItem(str(csv_universe)))
            self.data_table.setItem(row, 5, QTableWidgetItem(str(csv_channel)))
            self.data_table.setItem(row, 6, QTableWidgetItem(str(fixture.get('fixture_id', 0))))
            
            # Role
            role = core.get_fixture_role(fixture)
            role_display = "NONE" if role == "none" else role.title()
            role_item = QTableWidgetItem(role_display)
            if role == 'none':
                role_item.setBackground(Qt.GlobalColor.lightGray)
            elif role == 'master':
                role_item.setBackground(Qt.GlobalColor.darkGreen)
                role_item.setForeground(Qt.GlobalColor.white)
            elif role == 'remote':
                role_item.setBackground(Qt.GlobalColor.darkBlue)
                role_item.setForeground(Qt.GlobalColor.white)
            self.data_table.setItem(row, 7, role_item)
            
            # Status
            status = "Matched" if fixture.get('matched') else "Unmatched"
            status_item = QTableWidgetItem(status)
            if fixture.get('matched'):
                status_item.setBackground(Qt.GlobalColor.green)
            else:
                status_item.setBackground(Qt.GlobalColor.lightGray)
            self.data_table.setItem(row, 8, status_item)
        
        # Resize columns
        header = self.data_table.horizontalHeader()
        # Reset all column resize modes first
        for i in range(len(headers)):
            header.setSectionResizeMode(i, QHeaderView.ResizeMode.Interactive)
        
        # Set specific resize modes
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)  # Select checkbox
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)  # Name
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)  # Type
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)  # Mode
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)  # Universe
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)  # Channel
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)  # ID
        header.setSectionResizeMode(7, QHeaderView.ResizeMode.ResizeToContents)  # Role
        header.setSectionResizeMode(8, QHeaderView.ResizeMode.ResizeToContents)  # Status
        
        # Set checkbox column width with some padding
        self.data_table.setColumnWidth(0, 80)
        
        # Center the "Select" header text
        header_item = self.data_table.horizontalHeaderItem(0)
        if header_item:
            header_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.preview_label.setText("Parsed Fixtures:")
        self._update_import_button()
    
    def _handle_invalid_fixture_ids(self, invalid_fixtures: List[Dict[str, Any]]):
        """Handle fixtures with invalid fixture IDs by prompting user for manual entry."""
        from PyQt6.QtWidgets import QInputDialog
        
        # Show warning about invalid fixture IDs
        fixture_names = [f.get('name', 'Unknown') for f in invalid_fixtures]
        warning_msg = f"The following fixtures have invalid fixture IDs:\n\n"
        warning_msg += "\n".join(f"• {name}" for name in fixture_names[:10])  # Show first 10
        if len(fixture_names) > 10:
            warning_msg += f"\n... and {len(fixture_names) - 10} more"
        warning_msg += "\n\nYou will be prompted to enter valid fixture IDs for each one."
        
        QMessageBox.information(self, "Invalid Fixture IDs", warning_msg)
        
        # Prompt for each invalid fixture
        for fixture in invalid_fixtures:
            original_id = fixture.get('original_fixture_id', '')
            fixture_name = fixture.get('name', 'Unknown')
            
            # Show input dialog
            new_id, ok = QInputDialog.getInt(
                self,
                "Enter Fixture ID",
                f"Enter a valid fixture ID for '{fixture_name}'\n(Original value: {original_id})",
                value=fixture.get('fixture_id', 1),
                min=1,
                max=9999
            )
            
            if ok:
                # Update the fixture ID
                fixture['fixture_id'] = new_id
                fixture['fixture_id_invalid'] = False
                if 'original_fixture_id' in fixture:
                    del fixture['original_fixture_id']
            else:
                # User cancelled - keep the sequential ID
                fixture['fixture_id_invalid'] = False
                if 'original_fixture_id' in fixture:
                    del fixture['original_fixture_id']
    
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
    
    def _toggle_selected(self):
        """Toggle checkbox state of highlighted/selected rows."""
        selected_rows = set()
        for item in self.data_table.selectedItems():
            selected_rows.add(item.row())
        
        if not selected_rows:
            QMessageBox.information(self, "No Selection", "Please select rows to toggle their checkbox state.")
            return
        
        # Count how many are currently checked vs unchecked
        checked_count = 0
        unchecked_count = 0
        
        for row in selected_rows:
            checkbox = self.data_table.cellWidget(row, 0)
            if checkbox:
                if checkbox.isChecked():
                    checked_count += 1
                else:
                    unchecked_count += 1
        
        # Toggle all selected rows
        for row in selected_rows:
            checkbox = self.data_table.cellWidget(row, 0)
            if checkbox:
                checkbox.setChecked(not checkbox.isChecked())
        
        # Show status message
        if checked_count > 0 and unchecked_count > 0:
            self.status_text.append(f"Toggled {len(selected_rows)} selected rows (mixed state)")
        elif checked_count > 0:
            self.status_text.append(f"Unchecked {len(selected_rows)} selected rows")
        else:
            self.status_text.append(f"Checked {len(selected_rows)} selected rows")
    
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
            # Check if any fixtures have 'none' role and show warning
            fixtures_with_none_role = [f for f in selected_fixtures if core.get_fixture_role(f) == 'none']
            if fixtures_with_none_role:
                fixture_names = [f.get('name', 'Unknown') for f in fixtures_with_none_role]
                warning_msg = f"The following fixtures have NONE role and will be imported but may not appear in the main window tables:\n\n"
                warning_msg += "\n".join(f"• {name}" for name in fixture_names[:10])  # Show first 10
                if len(fixture_names) > 10:
                    warning_msg += f"\n... and {len(fixture_names) - 10} more"
                warning_msg += "\n\nYou can assign roles during import using the role assignment buttons."
                QMessageBox.information(self, "Role Assignment Notice", warning_msg)
            
            # Show attribute selection dialog after import
            self.show_attribute_selection_dialog(selected_fixtures)
        else:
            QMessageBox.information(self, "No Selection", "Please select at least one fixture to import.")
    
    def show_attribute_selection_dialog(self, selected_fixtures: List[Dict[str, Any]]):
        """Show the attribute selection dialog after successful import."""
        dialog = AttributeSelectionDialog(selected_fixtures, self.config, self)
        dialog.attributes_selected.connect(self.on_attributes_selected)
        result = dialog.exec()
        
        if result == QDialog.DialogCode.Accepted:
            # The dialog has already emitted the attributes_selected signal
            # and applied the fixture matches, so we can proceed with import
            self.fixtures_imported.emit(selected_fixtures)
            self.accept()
        else:
            # User cancelled the attribute selection, so we don't import
            pass
    
    def on_attributes_selected(self, selected_attributes: List[str]):
        """Handle attributes selected from the attribute selection dialog."""
        # Save selected attributes to config
        self.config.set_selected_attributes(selected_attributes) 