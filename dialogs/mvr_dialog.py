"""
Simple MVR import dialog.
Allows users to select MVR file and choose fixtures to import via checkboxes.
"""

from typing import List, Dict, Any, Optional
from pathlib import Path

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QFileDialog, QMessageBox, QTableWidget, QTableWidgetItem,
    QCheckBox, QHeaderView, QProgressBar, QTextEdit
)
from PyQt6.QtCore import Qt, pyqtSignal

import core
from .gdtf_dialog import GDTFMatchingDialog
from .attribute_selection_dialog import AttributeSelectionDialog


class MVRImportDialog(QDialog):
    """Simple dialog for importing MVR files with fixture selection."""
    
    fixtures_imported = pyqtSignal(list)  # List of selected fixtures
    
    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.config = config
        self.fixtures = []
        self.gdtf_profiles = {}
        
        self.setWindowTitle("Import MVR File")
        self.setMinimumSize(800, 600)
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Set up the user interface."""
        layout = QVBoxLayout(self)
        
        # File selection
        file_layout = QHBoxLayout()
        self.file_label = QLabel("No file selected")
        self.browse_button = QPushButton("Browse MVR File...")
        self.browse_button.clicked.connect(self._browse_file)
        
        file_layout.addWidget(QLabel("MVR File:"))
        file_layout.addWidget(self.file_label, 1)
        file_layout.addWidget(self.browse_button)
        layout.addLayout(file_layout)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # Status text
        self.status_text = QTextEdit()
        self.status_text.setMaximumHeight(100)
        self.status_text.setReadOnly(True)
        layout.addWidget(self.status_text)
        
        # Fixtures table
        layout.addWidget(QLabel("Select fixtures to import:"))
        self.fixtures_table = QTableWidget()
        self._setup_table()
        layout.addWidget(self.fixtures_table)
        
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
        
        selection_layout.addWidget(self.select_all_button)
        selection_layout.addWidget(self.select_none_button)
        selection_layout.addWidget(self.gdtf_matching_button)
        selection_layout.addStretch()
        selection_layout.addWidget(self.set_as_master_button)
        selection_layout.addWidget(self.set_as_remote_button)
        layout.addLayout(selection_layout)
        
        # Dialog buttons
        button_layout = QHBoxLayout()
        self.import_button = QPushButton("Import Selected")
        self.cancel_button = QPushButton("Cancel")
        
        self.import_button.clicked.connect(self._import_fixtures)
        self.cancel_button.clicked.connect(self.reject)
        self.import_button.setEnabled(False)
        
        button_layout.addStretch()
        button_layout.addWidget(self.import_button)
        button_layout.addWidget(self.cancel_button)
        layout.addLayout(button_layout)
    
    def _setup_table(self):
        """Set up the fixtures table."""
        headers = ["Select", "Name", "Type", "Mode", "Address", "ID", "Role", "Status"]
        self.fixtures_table.setColumnCount(len(headers))
        self.fixtures_table.setHorizontalHeaderLabels(headers)
        
        # Resize columns
        header = self.fixtures_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)
        
        self.fixtures_table.setColumnWidth(0, 60)
    
    def _browse_file(self):
        """Browse for MVR file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select MVR File",
            self.config.get_last_mvr_directory(),
            "MVR Files (*.mvr)"
        )
        
        if file_path:
            self.config.set_last_mvr_directory(str(Path(file_path).parent))
            self._load_mvr_file(file_path)
    
    def _load_mvr_file(self, file_path: str):
        """Load and parse MVR file."""
        self.file_label.setText(Path(file_path).name)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Indeterminate progress
        self.status_text.append(f"Loading MVR file: {Path(file_path).name}")
        
        try:
            # First validate the file
            if not core.validate_mvr_file(file_path):
                error_msg = "Invalid MVR file. MVR files must be zip archives containing GeneralSceneDescription.xml"
                self.status_text.append(f"Error: {error_msg}")
                QMessageBox.warning(self, "Invalid File", error_msg)
                return
            
            # Parse MVR file
            result = core.parse_mvr_file(file_path)
            
            if 'error' in result:
                self.status_text.append(f"Error: {result['error']}")
                QMessageBox.warning(self, "Error", result['error'])
                return
            
            self.fixtures = result['fixtures']
            self.gdtf_profiles = result['gdtf_profiles']
            
            if not self.fixtures:
                self.status_text.append("Warning: No fixtures found in MVR file")
                QMessageBox.information(self, "No Fixtures", "No fixtures were found in the MVR file. The file may be empty or have an unsupported format.")
                return
            
            # Auto-match fixtures to GDTF profiles
            if self.gdtf_profiles:
                self.status_text.append("Auto-matching fixtures to GDTF profiles...")
                core.auto_match_fixtures(self.fixtures, self.gdtf_profiles)
            
            # Load external GDTF folder if configured
            external_folder = self.config.get_external_gdtf_folder()
            if external_folder:
                self.status_text.append("Loading external GDTF profiles...")
                external_profiles = core.parse_external_gdtf_folder(external_folder)
                self.gdtf_profiles.update(external_profiles)
                
                # Re-run matching with external profiles
                core.auto_match_fixtures(self.fixtures, self.gdtf_profiles)
            
            # Update table
            self._populate_table()
            
            # Show summary
            summary = core.get_match_summary(self.fixtures)
            self.status_text.append(f"Loaded {summary['total']} fixtures, {summary['matched']} matched ({summary['match_rate']:.1f}%)")
            
        except Exception as e:
            error_msg = f"Failed to load MVR file: {str(e)}"
            self.status_text.append(f"Error: {error_msg}")
            QMessageBox.critical(self, "Error", error_msg)
        
        finally:
            self.progress_bar.setVisible(False)
    
    def _populate_table(self):
        """Populate the fixtures table."""
        self.fixtures_table.setRowCount(len(self.fixtures))
        
        for row, fixture in enumerate(self.fixtures):
            # Checkbox
            checkbox = QCheckBox()
            checkbox.setChecked(fixture.get('selected', True))
            checkbox.stateChanged.connect(lambda state, r=row: self._checkbox_changed(r, state))
            self.fixtures_table.setCellWidget(row, 0, checkbox)
            
            # Fixture data
            self.fixtures_table.setItem(row, 1, QTableWidgetItem(fixture.get('name', '')))
            self.fixtures_table.setItem(row, 2, QTableWidgetItem(fixture.get('type', '')))
            self.fixtures_table.setItem(row, 3, QTableWidgetItem(fixture.get('mode', '')))
            self.fixtures_table.setItem(row, 4, QTableWidgetItem(str(fixture.get('base_address', 1))))
            self.fixtures_table.setItem(row, 5, QTableWidgetItem(str(fixture.get('fixture_id', 0))))
            
            # Role
            role = core.get_fixture_role(fixture)
            role_display = "NONE" if role == "none" else role.title()
            role_item = QTableWidgetItem(role_display)
            if role == 'none':
                role_item.setBackground(Qt.GlobalColor.yellow)
            elif role == 'master':
                role_item.setBackground(Qt.GlobalColor.green)
            elif role == 'remote':
                role_item.setBackground(Qt.GlobalColor.cyan)
            self.fixtures_table.setItem(row, 6, role_item)
            
            # Status
            status = "Matched" if fixture.get('matched') else "Unmatched"
            status_item = QTableWidgetItem(status)
            if fixture.get('matched'):
                status_item.setBackground(Qt.GlobalColor.green)
            else:
                status_item.setBackground(Qt.GlobalColor.lightGray)
            self.fixtures_table.setItem(row, 7, status_item)
        
        self._update_import_button()
    
    def _checkbox_changed(self, row: int, state: int):
        """Handle checkbox state change."""
        if row < len(self.fixtures):
            selected = state == Qt.CheckState.Checked.value
            core.set_fixture_selected(self.fixtures[row], selected)
        self._update_import_button()
    
    def _select_all(self):
        """Select all fixtures."""
        for row in range(self.fixtures_table.rowCount()):
            checkbox = self.fixtures_table.cellWidget(row, 0)
            if checkbox:
                checkbox.setChecked(True)
    
    def _select_none(self):
        """Deselect all fixtures."""
        for row in range(self.fixtures_table.rowCount()):
            checkbox = self.fixtures_table.cellWidget(row, 0)
            if checkbox:
                checkbox.setChecked(False)
    
    def _set_selected_as_master(self):
        """Set selected fixtures as master role."""
        selected_count = 0
        for row in range(self.fixtures_table.rowCount()):
            checkbox = self.fixtures_table.cellWidget(row, 0)
            if checkbox and checkbox.isChecked() and row < len(self.fixtures):
                fixture = self.fixtures[row]
                core.set_fixture_role(fixture, 'master')
                selected_count += 1
        
        if selected_count > 0:
            self._populate_table()  # Refresh table to show updated roles
            self.status_text.append(f"Set {selected_count} fixture{'s' if selected_count != 1 else ''} as master")
        else:
            QMessageBox.information(self, "No Selection", "Please select fixtures to set as master.")
    
    def _set_selected_as_remote(self):
        """Set selected fixtures as remote role."""
        selected_count = 0
        for row in range(self.fixtures_table.rowCount()):
            checkbox = self.fixtures_table.cellWidget(row, 0)
            if checkbox and checkbox.isChecked() and row < len(self.fixtures):
                fixture = self.fixtures[row]
                core.set_fixture_role(fixture, 'remote')
                selected_count += 1
        
        if selected_count > 0:
            self._populate_table()  # Refresh table to show updated roles
            self.status_text.append(f"Set {selected_count} fixture{'s' if selected_count != 1 else ''} as remote")
        else:
            QMessageBox.information(self, "No Selection", "Please select fixtures to set as remote.")
    
    def _open_gdtf_matching(self):
        """Open the GDTF profile matching dialog."""
        if not self.fixtures:
            QMessageBox.information(self, "No Fixtures", "Please load an MVR file first.")
            return
        
        dialog = GDTFMatchingDialog(self.fixtures, self.config, self)
        result = dialog.exec()
        
        if result == QDialog.DialogCode.Accepted:
            # Apply the matches to fixtures
            updated_count = dialog.apply_matches_to_fixtures()
            
            if updated_count > 0:
                # Refresh the fixtures table to show updated match status
                self._populate_table()
                
                # Show updated summary
                summary = core.get_match_summary(self.fixtures)
                self.status_text.append(f"GDTF matching complete: {summary['matched']}/{summary['total']} fixtures matched ({summary['match_rate']:.1f}%)")
            else:
                self.status_text.append("No GDTF matches were applied")
    
    def _update_import_button(self):
        """Update import button state based on selection."""
        selected_count = 0
        for row in range(self.fixtures_table.rowCount()):
            checkbox = self.fixtures_table.cellWidget(row, 0)
            if checkbox and checkbox.isChecked():
                selected_count += 1
        
        self.import_button.setEnabled(selected_count > 0)
        self.import_button.setText(f"Import Selected ({selected_count})")
    
    def _import_fixtures(self):
        """Import selected fixtures."""
        selected_fixtures = []
        
        for row in range(self.fixtures_table.rowCount()):
            checkbox = self.fixtures_table.cellWidget(row, 0)
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


from pathlib import Path 