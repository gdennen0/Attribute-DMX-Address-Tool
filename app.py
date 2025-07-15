"""
Main application window for AttributeAddresser.
Clean UI with business logic completely separated into core modules.
"""

import sys
from typing import List, Dict, Any, Optional
from pathlib import Path

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QTextEdit, QTableWidget, QTableWidgetItem,
    QHeaderView, QCheckBox, QGroupBox, QMenuBar, QMenu, QComboBox,
    QFileDialog, QMessageBox, QSplitter, QScrollArea
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QAction, QFont

from config import Config
import core
from dialogs import MVRImportDialog, CSVImportDialog, SettingsDialog, FixtureLinkingDialog


class MainWindow(QMainWindow):
    """Main application window with simple, clean UI."""
    
    def __init__(self):
        super().__init__()
        
        # Initialize state
        self.config = Config()
        self.project_state = core.create_project_state()
        
        self.setWindowTitle("AttributeAddresser")
        self.setMinimumSize(1000, 700)
        
        self._setup_ui()
        self._update_ui_state()
    
    def _setup_ui(self):
        """Set up the user interface."""
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QVBoxLayout(central_widget)
        
        # Menu bar
        self._setup_menu_bar()
        
        # Toolbar
        toolbar_layout = QHBoxLayout()
        self.import_mvr_button = QPushButton("Import MVR...")
        self.import_csv_button = QPushButton("Import CSV...")
        self.link_fixtures_button = QPushButton("Link Fixtures...")
        self.settings_button = QPushButton("Settings")
        
        self.import_mvr_button.clicked.connect(self._import_mvr)
        self.import_csv_button.clicked.connect(self._import_csv)
        self.link_fixtures_button.clicked.connect(self._open_fixture_linking)
        self.settings_button.clicked.connect(self._open_settings)
        
        toolbar_layout.addWidget(self.import_mvr_button)
        toolbar_layout.addWidget(self.import_csv_button)
        toolbar_layout.addWidget(self.link_fixtures_button)
        toolbar_layout.addStretch()
        toolbar_layout.addWidget(self.settings_button)
        main_layout.addLayout(toolbar_layout)
        
        # Main content area
        content_splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left panel - Fixtures
        left_panel = self._setup_fixtures_panel()
        content_splitter.addWidget(left_panel)
        
        # Right panel - Attributes and Export
        right_panel = self._setup_export_panel()
        content_splitter.addWidget(right_panel)
        
        content_splitter.setSizes([600, 400])
        main_layout.addWidget(content_splitter)
        
        # Status bar
        self.status_label = QLabel("Ready")
        main_layout.addWidget(self.status_label)
    
    def _setup_menu_bar(self):
        """Set up the menu bar."""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("File")
        
        import_mvr_action = QAction("Import MVR...", self)
        import_mvr_action.triggered.connect(self._import_mvr)
        file_menu.addAction(import_mvr_action)
        
        import_csv_action = QAction("Import CSV...", self)
        import_csv_action.triggered.connect(self._import_csv)
        file_menu.addAction(import_csv_action)
        
        file_menu.addSeparator()
        
        link_fixtures_action = QAction("Link Fixtures...", self)
        link_fixtures_action.triggered.connect(self._open_fixture_linking)
        file_menu.addAction(link_fixtures_action)
        
        file_menu.addSeparator()
        
        settings_action = QAction("Settings...", self)
        settings_action.triggered.connect(self._open_settings)
        file_menu.addAction(settings_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Help menu
        help_menu = menubar.addMenu("Help")
        about_action = QAction("About", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)
    
    def _setup_fixtures_panel(self) -> QWidget:
        """Set up the fixtures panel with separate Master and Remote tables."""
        panel = QGroupBox("Fixtures")
        layout = QVBoxLayout(panel)
        
        # Create splitter for side-by-side tables
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Master fixtures panel
        master_panel = self._setup_master_fixtures_panel()
        splitter.addWidget(master_panel)
        
        # Remote fixtures panel
        remote_panel = self._setup_remote_fixtures_panel()
        splitter.addWidget(remote_panel)
        
        splitter.setSizes([450, 450])
        layout.addWidget(splitter)
        
        # Global fixture controls
        controls_layout = QHBoxLayout()
        
        self.clear_fixtures_button = QPushButton("Clear All Fixtures")
        self.clear_fixtures_button.clicked.connect(self._clear_fixtures)
        
        controls_layout.addStretch()
        controls_layout.addWidget(self.clear_fixtures_button)
        layout.addLayout(controls_layout)
        
        return panel
    
    def _setup_master_fixtures_panel(self) -> QGroupBox:
        """Set up the master fixtures panel."""
        panel = QGroupBox("Master Fixtures")
        layout = QVBoxLayout(panel)
        
        # Master fixtures table
        self.master_table = QTableWidget()
        self._setup_master_table()
        layout.addWidget(self.master_table)
        
        # Master controls
        controls_layout = QHBoxLayout()
        
        self.select_all_masters_button = QPushButton("Select All")
        self.select_none_masters_button = QPushButton("Select None")
        
        self.select_all_masters_button.clicked.connect(self._select_all_masters)
        self.select_none_masters_button.clicked.connect(self._select_none_masters)
        
        controls_layout.addWidget(self.select_all_masters_button)
        controls_layout.addWidget(self.select_none_masters_button)
        controls_layout.addStretch()
        layout.addLayout(controls_layout)
        
        return panel
    
    def _setup_remote_fixtures_panel(self) -> QGroupBox:
        """Set up the remote fixtures panel."""
        panel = QGroupBox("Remote Fixtures")
        layout = QVBoxLayout(panel)
        
        # Remote fixtures table
        self.remote_table = QTableWidget()
        self._setup_remote_table()
        layout.addWidget(self.remote_table)
        
        # Remote controls
        controls_layout = QHBoxLayout()
        
        self.select_all_remotes_button = QPushButton("Select All")
        self.select_none_remotes_button = QPushButton("Select None")
        
        self.select_all_remotes_button.clicked.connect(self._select_all_remotes)
        self.select_none_remotes_button.clicked.connect(self._select_none_remotes)
        
        controls_layout.addWidget(self.select_all_remotes_button)
        controls_layout.addWidget(self.select_none_remotes_button)
        controls_layout.addStretch()
        layout.addLayout(controls_layout)
        
        return panel
    
    def _setup_export_panel(self) -> QWidget:
        """Set up the export panel."""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # Attributes selection
        attributes_group = QGroupBox("Select Attributes")
        attributes_layout = QVBoxLayout(attributes_group)
        
        # Available attributes (scrollable)
        self.attributes_scroll = QScrollArea()
        self.attributes_widget = QWidget()
        self.attributes_layout = QVBoxLayout(self.attributes_widget)
        self.attributes_scroll.setWidget(self.attributes_widget)
        self.attributes_scroll.setWidgetResizable(True)
        self.attributes_scroll.setMaximumHeight(250)
        
        attributes_layout.addWidget(self.attributes_scroll)
        
        # Attribute controls
        attr_controls_layout = QHBoxLayout()
        self.select_all_attrs_button = QPushButton("Select All")
        self.select_none_attrs_button = QPushButton("Select None")
        
        self.select_all_attrs_button.clicked.connect(self._select_all_attributes)
        self.select_none_attrs_button.clicked.connect(self._select_none_attributes)
        
        attr_controls_layout.addWidget(self.select_all_attrs_button)
        attr_controls_layout.addWidget(self.select_none_attrs_button)
        attr_controls_layout.addStretch()
        attributes_layout.addLayout(attr_controls_layout)
        
        layout.addWidget(attributes_group)
        
        # Export options
        export_group = QGroupBox("Export")
        export_layout = QVBoxLayout(export_group)
        
        # Format selection
        format_layout = QHBoxLayout()
        format_layout.addWidget(QLabel("Format:"))
        self.export_format_combo = QComboBox()
        self.export_format_combo.addItems(core.get_export_formats())
        format_layout.addWidget(self.export_format_combo)
        format_layout.addStretch()
        export_layout.addLayout(format_layout)
        
        # Export buttons
        export_buttons_layout = QHBoxLayout()
        self.preview_button = QPushButton("Preview")
        self.export_button = QPushButton("Export to File...")
        
        self.preview_button.clicked.connect(self._preview_export)
        self.export_button.clicked.connect(self._export_to_file)
        
        export_buttons_layout.addWidget(self.preview_button)
        export_buttons_layout.addWidget(self.export_button)
        export_layout.addLayout(export_buttons_layout)
        
        layout.addWidget(export_group)
        
        # Preview area
        preview_group = QGroupBox("Preview")
        preview_layout = QVBoxLayout(preview_group)
        
        self.preview_text = QTextEdit()
        self.preview_text.setReadOnly(True)
        self.preview_text.setFont(QFont("Courier", 9))
        preview_layout.addWidget(self.preview_text)
        
        layout.addWidget(preview_group)
        
        return panel
    
    def _setup_master_table(self):
        """Set up the master fixtures table."""
        headers = ["Select", "Name", "Type", "Mode", "Address", "ID", "Role", "Linked Remotes", "Status"]
        self.master_table.setColumnCount(len(headers))
        self.master_table.setHorizontalHeaderLabels(headers)
        
        # Configure column sizing
        header = self.master_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        for i in range(3, len(headers)):
            header.setSectionResizeMode(i, QHeaderView.ResizeMode.ResizeToContents)
        
        self.master_table.setColumnWidth(0, 60)
        self.master_table.setAlternatingRowColors(True)
        self.master_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
    
    def _setup_remote_table(self):
        """Set up the remote fixtures table."""
        headers = ["Select", "Name", "Type", "Mode", "Address", "ID", "Role", "Master", "Status"]
        self.remote_table.setColumnCount(len(headers))
        self.remote_table.setHorizontalHeaderLabels(headers)
        
        # Configure column sizing
        header = self.remote_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        for i in range(3, len(headers)):
            header.setSectionResizeMode(i, QHeaderView.ResizeMode.ResizeToContents)
        
        self.remote_table.setColumnWidth(0, 60)
        self.remote_table.setAlternatingRowColors(True)
        self.remote_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
    
    def _import_mvr(self):
        """Open MVR import dialog."""
        dialog = MVRImportDialog(self.config, self)
        dialog.fixtures_imported.connect(self._add_fixtures)
        dialog.exec()
    
    def _import_csv(self):
        """Open CSV import dialog."""
        dialog = CSVImportDialog(self.config, self)
        dialog.fixtures_imported.connect(self._add_fixtures)
        dialog.exec()
    
    def _open_settings(self):
        """Open settings dialog."""
        dialog = SettingsDialog(self.config, self)
        dialog.exec()
    
    def _open_fixture_linking(self):
        """Open fixture linking dialog."""
        if not self.project_state['fixtures']:
            QMessageBox.information(self, "No Fixtures", "Please import some fixtures first.")
            return
        
        dialog = FixtureLinkingDialog(self.project_state['fixtures'], self)
        dialog.relationships_updated.connect(self._update_fixtures_tables)
        dialog.exec()
    
    def _add_fixtures(self, fixtures: List[Dict[str, Any]]):
        """Add imported fixtures to the project."""
        self.project_state['fixtures'].extend(fixtures)
        self._update_fixtures_tables()
        self._update_attributes_list()
        self._update_ui_state()
        
        count = len(fixtures)
        self.status_label.setText(f"Imported {count} fixture{'s' if count != 1 else ''}")
    
    def _update_fixtures_tables(self):
        """Update both master and remote fixtures tables."""
        self._update_master_table()
        self._update_remote_table()
    
    def _update_master_table(self):
        """Update the master fixtures table display."""
        fixtures = self.project_state['fixtures']
        # Show master fixtures and unassigned fixtures (for manual assignment)
        master_fixtures = [f for f in fixtures if core.get_fixture_role(f) in ['master', 'unassigned']]
        
        self.master_table.setRowCount(len(master_fixtures))
        
        for row, fixture in enumerate(master_fixtures):
            # Checkbox
            checkbox = QCheckBox()
            checkbox.setChecked(fixture.get('selected', True))
            checkbox.stateChanged.connect(lambda state, f=fixture: self._master_selection_changed(f, state))
            self.master_table.setCellWidget(row, 0, checkbox)
            
            # Fixture data
            self.master_table.setItem(row, 1, QTableWidgetItem(fixture.get('name', '')))
            self.master_table.setItem(row, 2, QTableWidgetItem(fixture.get('type', '')))
            self.master_table.setItem(row, 3, QTableWidgetItem(fixture.get('mode', '')))
            self.master_table.setItem(row, 4, QTableWidgetItem(str(fixture.get('base_address', 1))))
            self.master_table.setItem(row, 5, QTableWidgetItem(str(fixture.get('fixture_id', 0))))
            
            # Role
            role = core.get_fixture_role(fixture)
            role_item = QTableWidgetItem(role.title())
            if role == 'unassigned':
                role_item.setBackground(Qt.GlobalColor.yellow)
            elif role == 'master':
                role_item.setBackground(Qt.GlobalColor.green)
            self.master_table.setItem(row, 6, role_item)
            
            # Linked remotes
            linked_remotes = core.get_linked_remotes(fixture, fixtures)
            if linked_remotes:
                remote_names = [r['name'] for r in linked_remotes]
                relationship_info = f"{', '.join(remote_names[:2])}"
                if len(remote_names) > 2:
                    relationship_info += f" (+{len(remote_names) - 2} more)"
            else:
                relationship_info = "No remotes"
            
            self.master_table.setItem(row, 7, QTableWidgetItem(relationship_info))
            
            # Status
            status = "Matched" if fixture.get('matched') else "Unmatched"
            status_item = QTableWidgetItem(status)
            if fixture.get('matched'):
                status_item.setBackground(Qt.GlobalColor.green)
            else:
                status_item.setBackground(Qt.GlobalColor.lightGray)
            self.master_table.setItem(row, 8, status_item)
    
    def _update_remote_table(self):
        """Update the remote fixtures table display."""
        fixtures = self.project_state['fixtures']
        # Show remote fixtures and unassigned fixtures (for manual assignment)  
        remote_fixtures = [f for f in fixtures if core.get_fixture_role(f) in ['remote', 'unassigned']]
        
        self.remote_table.setRowCount(len(remote_fixtures))
        
        for row, fixture in enumerate(remote_fixtures):
            # Checkbox
            checkbox = QCheckBox()
            checkbox.setChecked(fixture.get('selected', True))
            checkbox.stateChanged.connect(lambda state, f=fixture: self._remote_selection_changed(f, state))
            self.remote_table.setCellWidget(row, 0, checkbox)
            
            # Fixture data
            self.remote_table.setItem(row, 1, QTableWidgetItem(fixture.get('name', '')))
            self.remote_table.setItem(row, 2, QTableWidgetItem(fixture.get('type', '')))
            self.remote_table.setItem(row, 3, QTableWidgetItem(fixture.get('mode', '')))
            self.remote_table.setItem(row, 4, QTableWidgetItem(str(fixture.get('base_address', 1))))
            self.remote_table.setItem(row, 5, QTableWidgetItem(str(fixture.get('fixture_id', 0))))
            
            # Role
            role = core.get_fixture_role(fixture)
            role_item = QTableWidgetItem(role.title())
            if role == 'unassigned':
                role_item.setBackground(Qt.GlobalColor.yellow)
            elif role == 'remote':
                role_item.setBackground(Qt.GlobalColor.cyan)
            self.remote_table.setItem(row, 6, role_item)
            
            # Master fixture
            master_fixture = core.get_master_for_remote(fixture, fixtures)
            if master_fixture:
                relationship_info = f"{master_fixture['name']}"
            else:
                relationship_info = "No master"
            
            self.remote_table.setItem(row, 7, QTableWidgetItem(relationship_info))
            
            # Status
            status = "Matched" if fixture.get('matched') else "Unmatched"
            status_item = QTableWidgetItem(status)
            if fixture.get('matched'):
                status_item.setBackground(Qt.GlobalColor.green)
            else:
                status_item.setBackground(Qt.GlobalColor.lightGray)
            self.remote_table.setItem(row, 8, status_item)
    
    def _update_attributes_list(self):
        """Update the available attributes list."""
        # Clear existing checkboxes
        for i in reversed(range(self.attributes_layout.count())):
            child = self.attributes_layout.itemAt(i).widget()
            if child:
                child.setParent(None)
        
        # Get available attributes
        available_attributes = core.get_available_attributes(self.project_state['fixtures'])
        
        # Create checkboxes for each attribute
        for attr in available_attributes:
            checkbox = QCheckBox(attr)
            checkbox.setChecked(attr in self.project_state['selected_attributes'])
            checkbox.stateChanged.connect(lambda state, attribute=attr: self._attribute_selection_changed(attribute, state))
            self.attributes_layout.addWidget(checkbox)
        
        # Add stretch at the end
        self.attributes_layout.addStretch()
    
    def _master_selection_changed(self, fixture: Dict[str, Any], state: int):
        """Handle master fixture selection change."""
        selected = state == Qt.CheckState.Checked.value
        core.set_fixture_selected(fixture, selected)
        self._update_attributes_list()
    
    def _remote_selection_changed(self, fixture: Dict[str, Any], state: int):
        """Handle remote fixture selection change."""
        selected = state == Qt.CheckState.Checked.value
        core.set_fixture_selected(fixture, selected)
        self._update_attributes_list()
    
    def _attribute_selection_changed(self, attribute: str, state: int):
        """Handle attribute selection change."""
        selected = state == Qt.CheckState.Checked.value
        if selected and attribute not in self.project_state['selected_attributes']:
            self.project_state['selected_attributes'].append(attribute)
        elif not selected and attribute in self.project_state['selected_attributes']:
            self.project_state['selected_attributes'].remove(attribute)
    
    def _select_all_masters(self):
        """Select all master fixtures."""
        for row in range(self.master_table.rowCount()):
            checkbox = self.master_table.cellWidget(row, 0)
            if checkbox:
                checkbox.setChecked(True)
    
    def _select_none_masters(self):
        """Deselect all master fixtures."""
        for row in range(self.master_table.rowCount()):
            checkbox = self.master_table.cellWidget(row, 0)
            if checkbox:
                checkbox.setChecked(False)
    
    def _select_all_remotes(self):
        """Select all remote fixtures."""
        for row in range(self.remote_table.rowCount()):
            checkbox = self.remote_table.cellWidget(row, 0)
            if checkbox:
                checkbox.setChecked(True)
    
    def _select_none_remotes(self):
        """Deselect all remote fixtures."""
        for row in range(self.remote_table.rowCount()):
            checkbox = self.remote_table.cellWidget(row, 0)
            if checkbox:
                checkbox.setChecked(False)
    

    
    def _clear_fixtures(self):
        """Clear all fixtures."""
        reply = QMessageBox.question(
            self, "Clear Fixtures", 
            "Are you sure you want to clear all fixtures?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.project_state['fixtures'].clear()
            self.project_state['selected_attributes'].clear()
            self._update_fixtures_tables()
            self._update_attributes_list()
            self._update_ui_state()
            self.status_label.setText("Cleared all fixtures")
    
    def _select_all_attributes(self):
        """Select all attributes."""
        for i in range(self.attributes_layout.count()):
            item = self.attributes_layout.itemAt(i)
            if item and item.widget() and isinstance(item.widget(), QCheckBox):
                item.widget().setChecked(True)
    
    def _select_none_attributes(self):
        """Deselect all attributes."""
        for i in range(self.attributes_layout.count()):
            item = self.attributes_layout.itemAt(i)
            if item and item.widget() and isinstance(item.widget(), QCheckBox):
                item.widget().setChecked(False)
    
    def _preview_export(self):
        """Preview export data."""
        if not self.project_state['selected_attributes']:
            QMessageBox.information(self, "No Attributes", "Please select at least one attribute to export.")
            return
        
        if not any(f.get('selected') for f in self.project_state['fixtures']):
            QMessageBox.information(self, "No Fixtures", "Please select at least one fixture to export.")
            return
        
        # Process fixtures for export
        core.process_fixtures_for_export(
            self.project_state['fixtures'],
            self.project_state['selected_attributes'],
            self.config.get_sequence_start_number()
        )
        
        # Generate preview
        export_format = self.export_format_combo.currentText()
        ma3_config = self.config.get_ma3_xml_config() if export_format == 'ma3_xml' else None
        
        export_content = core.export_fixtures(
            self.project_state['fixtures'],
            self.project_state['selected_attributes'],
            export_format,
            ma3_config
        )
        
        self.preview_text.setPlainText(export_content)
        self.status_label.setText(f"Generated {export_format} preview")
    
    def _export_to_file(self):
        """Export data to file."""
        if not self.project_state['selected_attributes']:
            QMessageBox.information(self, "No Attributes", "Please select at least one attribute to export.")
            return
        
        if not any(f.get('selected') for f in self.project_state['fixtures']):
            QMessageBox.information(self, "No Fixtures", "Please select at least one fixture to export.")
            return
        
        # Choose file
        export_format = self.export_format_combo.currentText()
        file_ext = {
            'text': 'txt',
            'csv': 'csv', 
            'json': 'json',
            'ma3_xml': 'xml'
        }.get(export_format, 'txt')
        
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export File",
            self.config.get_last_export_directory(),
            f"{export_format.upper()} Files (*.{file_ext})"
        )
        
        if not file_path:
            return
        
        self.config.set_last_export_directory(str(Path(file_path).parent))
        
        try:
            # Process fixtures for export
            core.process_fixtures_for_export(
                self.project_state['fixtures'],
                self.project_state['selected_attributes'],
                self.config.get_sequence_start_number()
            )
            
            # Generate export content
            ma3_config = self.config.get_ma3_xml_config() if export_format == 'ma3_xml' else None
            export_content = core.export_fixtures(
                self.project_state['fixtures'],
                self.project_state['selected_attributes'],
                export_format,
                ma3_config
            )
            
            # Save to file
            if core.save_export_to_file(export_content, file_path):
                QMessageBox.information(self, "Export Complete", f"Successfully exported to {Path(file_path).name}")
                self.status_label.setText(f"Exported to {Path(file_path).name}")
            else:
                QMessageBox.warning(self, "Export Failed", "Failed to save export file.")
                
        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Export failed: {str(e)}")
    
    def _update_ui_state(self):
        """Update UI state based on current data."""
        has_fixtures = len(self.project_state['fixtures']) > 0
        has_selected_fixtures = any(f.get('selected') for f in self.project_state['fixtures'])
        has_selected_attributes = len(self.project_state['selected_attributes']) > 0
        
        # Enable/disable buttons
        # self.select_all_fixtures_button.setEnabled(has_fixtures)
        # self.select_none_fixtures_button.setEnabled(has_fixtures)
        self.clear_fixtures_button.setEnabled(has_fixtures)
        self.link_fixtures_button.setEnabled(has_fixtures)
        
        self.select_all_attrs_button.setEnabled(has_fixtures)
        self.select_none_attrs_button.setEnabled(has_fixtures)
        
        self.preview_button.setEnabled(has_selected_fixtures and has_selected_attributes)
        self.export_button.setEnabled(has_selected_fixtures and has_selected_attributes)
    
    def _show_about(self):
        """Show about dialog."""
        QMessageBox.about(
            self,
            "About AttributeAddresser",
            "AttributeAddresser v2.0\n\n"
            "A simple tool for analyzing MVR and CSV files to extract "
            "lighting fixture addresses and generate DMX documentation.\n\n"
            "Completely rewritten for simplicity and maintainability."
        )


def main():
    """Run the application."""
    app = QApplication(sys.argv)
    app.setApplicationName("AttributeAddresser")
    app.setApplicationVersion("2.0")
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec()) 