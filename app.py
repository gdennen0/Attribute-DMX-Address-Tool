"""
Main application window for AttributeAddresser.
Clean UI with business logic completely separated into core modules.
"""

import sys
from typing import List, Dict, Any, Optional
from pathlib import Path

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QGroupBox, QMenuBar, QMenu,
    QFileDialog, QMessageBox, QSplitter, QSizePolicy,
    QInputDialog, QDialog
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction

from config import Config
import core
from core.project import project_manager
from dialogs import MVRImportDialog, MA3ImportDialog, CSVImportDialog, SettingsDialog, AttributeSelectionDialog
from views.fixture_grouping_table import FixtureGroupingTable


class MainWindow(QMainWindow):
    """Main application window with simple, clean UI."""
    
    def __init__(self):
        super().__init__()
        
        # Initialize state
        self.config = Config()
        self.project_state = core.create_project_state()
        
        self.setWindowTitle("AttributeAddresser")
        self.setMinimumSize(1400, 800)  # Increased from 1000x700 to 1400x800
        
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
        self.import_ma3_button = QPushButton("Import MA3 XML...")
        self.import_csv_button = QPushButton("Import CSV...")
        self.settings_button = QPushButton("Settings")
        
        self.import_mvr_button.clicked.connect(self._import_mvr)
        self.import_ma3_button.clicked.connect(self._import_ma3)
        self.import_csv_button.clicked.connect(self._import_csv)
        self.settings_button.clicked.connect(self._open_settings)
        
        toolbar_layout.addWidget(self.import_mvr_button)
        toolbar_layout.addWidget(self.import_ma3_button)
        toolbar_layout.addWidget(self.import_csv_button)
        toolbar_layout.addStretch()
        toolbar_layout.addWidget(self.settings_button)
        main_layout.addLayout(toolbar_layout)
        
        # Main content area
        content_splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left panel - Fixtures
        left_panel = self._setup_fixtures_panel()
        content_splitter.addWidget(left_panel)
        
        # Right panel - (removed export panel - functionality moved to individual export buttons)
        content_splitter.setSizes([600, 400])
        main_layout.addWidget(content_splitter, stretch=1)
        
        # Status bar
        self.status_label = QLabel("Ready")
        main_layout.addWidget(self.status_label)
    
    def _setup_menu_bar(self):
        """Set up the menu bar."""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("File")
        
        save_project_action = QAction("Save Project...", self)
        save_project_action.setShortcut("Ctrl+S")
        save_project_action.triggered.connect(self._save_project)
        file_menu.addAction(save_project_action)
        
        save_as_project_action = QAction("Save Project As...", self)
        save_as_project_action.setShortcut("Ctrl+Shift+S")
        save_as_project_action.triggered.connect(self._save_project_as)
        file_menu.addAction(save_as_project_action)
        
        load_project_action = QAction("Load Project...", self)
        load_project_action.setShortcut("Ctrl+O")
        load_project_action.triggered.connect(self._load_project)
        file_menu.addAction(load_project_action)
        
        # Recent projects submenu
        self.recent_projects_menu = file_menu.addMenu("Recent Projects")
        self.recent_projects_menu.aboutToShow.connect(self._update_recent_projects_menu)
        
        file_menu.addSeparator()
        
        import_mvr_action = QAction("Import MVR...", self)
        import_mvr_action.triggered.connect(self._import_mvr)
        file_menu.addAction(import_mvr_action)
        
        import_ma3_action = QAction("Import MA3 XML...", self)
        import_ma3_action.triggered.connect(self._import_ma3)
        file_menu.addAction(import_ma3_action)
        
        import_csv_action = QAction("Import CSV...", self)
        import_csv_action.triggered.connect(self._import_csv)
        file_menu.addAction(import_csv_action)
        
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
        """Set up the fixtures panel with separate Ma and Remote tables."""
        panel = QGroupBox("Fixtures")
        layout = QVBoxLayout(panel)
        
        # Create splitter for side-by-side tables
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        
        # Ma fixtures panel
        ma_panel = self._setup_ma_fixtures_panel()
        splitter.addWidget(ma_panel)
        
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
        
        # Ensure the panel stretches vertically
        panel.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        return panel
    
    def _setup_ma_fixtures_panel(self) -> QGroupBox:
        """Set up the ma fixtures panel."""
        panel = QGroupBox("Ma Fixtures")
        layout = QVBoxLayout(panel)
        
        # Ma fixtures table
        self.ma_table = FixtureGroupingTable()
        self.ma_table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._setup_ma_table()
        layout.addWidget(self.ma_table)
        
        # Ma actions layout
        ma_actions_widget = QWidget()
        ma_actions_widget.setFixedHeight(40)  # Fixed height to keep tables aligned
        ma_actions_layout = QHBoxLayout(ma_actions_widget)
        ma_actions_layout.setContentsMargins(0, 0, 0, 0)  # Remove margins
        
        self.apply_sequences_button = QPushButton("Apply sequence numbers")
        self.apply_sequences_button.clicked.connect(self._apply_sequence_numbers)
        
        # Renumber Sequences button
        self.renumber_sequences_button = QPushButton("Renumber Sequences")
        self.renumber_sequences_button.clicked.connect(self._renumber_sequences)
        
        # Export MA3 Sequences button
        self.export_ma3_sequences_button = QPushButton("Export MA3 Sequences")
        self.export_ma3_sequences_button.clicked.connect(self._export_ma3_sequences)
        
        # Export CSV button
        self.export_ma_csv_button = QPushButton("Export CSV")
        self.export_ma_csv_button.clicked.connect(self._export_ma_csv)
        
        ma_actions_layout.addStretch()
        ma_actions_layout.addWidget(self.apply_sequences_button)
        ma_actions_layout.addWidget(self.renumber_sequences_button)
        ma_actions_layout.addWidget(self.export_ma3_sequences_button)
        ma_actions_layout.addWidget(self.export_ma_csv_button)
        layout.addWidget(ma_actions_widget)
        
        return panel
    
    def _setup_remote_fixtures_panel(self) -> QGroupBox:
        """Set up the remote fixtures panel."""
        panel = QGroupBox("Remote Fixtures")
        layout = QVBoxLayout(panel)
        
        # Remote fixtures table
        self.remote_table = FixtureGroupingTable()
        self.remote_table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._setup_remote_table()
        layout.addWidget(self.remote_table)
        
        # Remote actions layout (empty for now, but same height to keep tables aligned)
        remote_actions_widget = QWidget()
        remote_actions_widget.setFixedHeight(40)  # Same fixed height as ma actions
        remote_actions_layout = QHBoxLayout(remote_actions_widget)
        remote_actions_layout.setContentsMargins(0, 0, 0, 0)  # Remove margins
        
        # Add a spacer to maintain layout consistency
        remote_actions_layout.addStretch()
        
        # Export MA3 Remotes button
        self.export_ma3_remotes_button = QPushButton("Export MA3 Remotes")
        self.export_ma3_remotes_button.clicked.connect(self._export_ma3_remotes)
        
        # Export CSV button
        self.export_remote_csv_button = QPushButton("Export CSV")
        self.export_remote_csv_button.clicked.connect(self._export_remote_csv)
        
        remote_actions_layout.addStretch()
        remote_actions_layout.addWidget(self.export_ma3_remotes_button)
        remote_actions_layout.addWidget(self.export_remote_csv_button)
        
        layout.addWidget(remote_actions_widget)
        
        return panel
    
    def _setup_ma_table(self):
        """Set up the ma fixtures table."""
        # The FixtureGroupingTable handles its own setup
        # Connect the fixture order changed signal
        self.ma_table.fixtureOrderChanged.connect(self._on_ma_fixture_order_changed)
        self.ma_table.setOnDataChangedCallback(self._on_ma_data_changed)
    
    def _setup_remote_table(self):
        """Set up the remote fixtures table."""
        # The FixtureGroupingTable handles its own setup
        # Connect the fixture order changed signal
        self.remote_table.fixtureOrderChanged.connect(self._on_remote_fixture_order_changed)
        self.remote_table.setOnDataChangedCallback(self._on_remote_data_changed)
    
    def _import_mvr(self):
        """Open MVR import dialog."""
        dialog = MVRImportDialog(self.config, self)
        dialog.fixtures_imported.connect(self._add_fixtures)
        dialog.exec()
    
    def _import_ma3(self):
        """Open MA3 XML import dialog."""
        dialog = MA3ImportDialog(self.config, self)
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
    
    def _add_fixtures(self, fixtures: List[Dict[str, Any]]):
        """Add imported fixtures to the project."""
        # Validate fixtures before adding
        for fixture in fixtures:
            if not self.validate_fixture_data():
                print(f"Warning: Fixture {fixture.get('name', 'Unknown')} has invalid role")
        
        self.project_state['fixtures'].extend(fixtures)
        
        # Validate fixture roles for consistency after addition
        if not self.validate_fixture_data():
            print("Warning: Some fixtures have invalid roles")
        
        # Assign sequences only to ma fixtures (not remote fixtures on import)
        matched_ma_fixtures = self.get_ma_fixtures_matched()
        if matched_ma_fixtures:
            sequence_start = self.config.get_sequence_start_number()
            core.assign_sequences(matched_ma_fixtures, sequence_start)
        
        self._update_fixtures_tables()
        self._update_status_info()
        self._update_ui_state()
        
        count = len(fixtures)
        self.status_label.setText(f"Imported {count} fixture{'s' if count != 1 else ''}")
    
    def _update_fixtures_tables(self):
        """Update both ma and remote fixtures tables."""
        self._update_ma_table()
        self._update_remote_table()
    
    def _update_ma_table(self):
        """Update the ma fixtures table display."""
        # Get ma fixtures using centralized access method
        ma_fixtures = self.get_ma_fixtures()
        
        # Update the fixture grouping table
        self.ma_table.setFixtures(ma_fixtures)

    def _update_remote_table(self):
        """Update the remote fixtures table display."""
        # Get remote fixtures using centralized access method
        remote_fixtures = self.get_remote_fixtures()
        
        # Update the fixture grouping table
        self.remote_table.setFixtures(remote_fixtures)
    
    def _on_ma_fixture_order_changed(self, new_order):
        """Handle when ma fixture order changes."""
        # Update the project state with the new fixture order
        ma_fixtures = self.get_ma_fixtures()
        fixture_map = {fixture.get('fixture_id'): fixture for fixture in ma_fixtures}
        
        # Reorder fixtures based on new order
        reordered_fixtures = []
        for fixture_id in new_order:
            if fixture_id in fixture_map:
                reordered_fixtures.append(fixture_map[fixture_id])
        
        # Update the project state
        all_fixtures = self.project_state['fixtures']
        remote_fixtures = self.get_remote_fixtures()
        
        # Replace ma fixtures with reordered ones
        self.project_state['fixtures'] = reordered_fixtures + remote_fixtures
        
        # Update status
        self.status_label.setText(f"Ma fixture order updated")
    
    def _on_remote_fixture_order_changed(self, new_order):
        """Handle when remote fixture order changes."""
        # Update the project state with the new fixture order
        remote_fixtures = self.get_remote_fixtures()
        fixture_map = {fixture.get('fixture_id'): fixture for fixture in remote_fixtures}
        
        # Reorder fixtures based on new order
        reordered_fixtures = []
        for fixture_id in new_order:
            if fixture_id in fixture_map:
                reordered_fixtures.append(fixture_map[fixture_id])
        
        # Update the project state
        ma_fixtures = self.get_ma_fixtures()
        
        # Replace remote fixtures with reordered ones
        self.project_state['fixtures'] = ma_fixtures + reordered_fixtures
        
        # Update status
        self.status_label.setText(f"Remote fixture order updated")
    
    def _on_ma_data_changed(self):
        """Handle when ma table data changes."""
        # This is called when fixtures are reordered in the ma table
        # The fixture order is already updated in the table, so we just need to sync
        pass
    
    def _on_remote_data_changed(self):
        """Handle when remote table data changes."""
        # This is called when fixtures are reordered in the remote table
        # The fixture order is already updated in the table, so we just need to sync
        pass
    
    def _update_status_info(self):
        """Update the status information display."""
        fixtures = self.project_state['fixtures']
        if not fixtures:
            self.status_label.setText("No fixtures imported. Use Import MVR or Import CSV to get started.")
            return
        
        # Get selected attributes from config
        selected_attributes = self.config.get_selected_attributes()
        
        # Get fixture statistics using centralized access method
        stats = self.get_fixture_statistics()
        
        status_text = f"Project Status:\n"
        status_text += f"• Total fixtures: {stats['total_fixtures']}\n"
        status_text += f"• Ma fixtures: {stats['ma_fixtures']} ({stats['ma_matched']} matched)\n"
        status_text += f"• Remote fixtures: {stats['remote_fixtures']} ({stats['remote_matched']} matched)\n"
        if stats['unassigned_fixtures'] > 0:
            status_text += f"• Unassigned fixtures: {stats['unassigned_fixtures']}\n"
        status_text += f"• Selected attributes: {len(selected_attributes)}"
        
        if selected_attributes:
            status_text += f" ({', '.join(selected_attributes[:5])}"
            if len(selected_attributes) > 5:
                status_text += f" +{len(selected_attributes) - 5} more"
            status_text += ")"
        
        self.status_label.setText(status_text)
    
    def _clear_fixtures(self):
        """Clear all fixtures."""
        reply = QMessageBox.question(
            self, "Clear Fixtures", 
            "Are you sure you want to clear all fixtures?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.project_state['fixtures'].clear()
            self._update_fixtures_tables()
            self._update_status_info()
            self._update_ui_state()
            self.status_label.setText("Cleared all fixtures")
    
    def _apply_sequence_numbers(self):
        """Apply sequence numbers from ma fixtures to remote fixtures by row number."""
        # Get ma and remote fixtures using centralized access methods
        ma_fixtures = self.get_ma_fixtures()
        remote_fixtures = self.get_remote_fixtures()
        
        if not ma_fixtures:
            QMessageBox.warning(self, "No Ma Fixtures", "No ma fixtures found. Please import fixtures and set some as ma first.")
            return
        
        if not remote_fixtures:
            QMessageBox.warning(self, "No Remote Fixtures", "No remote fixtures found. Please import fixtures and set some as remote first.")
            return
        
        # Build ma attribute rows (same logic as in _update_ma_table)
        ma_attribute_rows = []
        for fixture in ma_fixtures:
            if fixture.get('matched', False):
                # Get sorted attributes from the fixture's GDTF profile model
                profile_model = fixture.get('gdtf_profile')
                if profile_model:
                    selected_attributes = profile_model.get_sorted_attributes()
                else:
                    # Fallback to unsorted attributes if no profile model
                    selected_attributes = list(fixture.get('attributes', {}).keys())
                
                for attr_name in selected_attributes:
                    if attr_name in fixture.get('attributes', {}):
                        sequence_num = fixture.get('sequences', {}).get(attr_name, '—')
                        ma_attribute_rows.append({
                            'fixture_id': fixture.get('fixture_id', 0),
                            'fixture_name': fixture.get('name', ''),
                            'attribute': attr_name,
                            'sequence': sequence_num,
                            'fixture': fixture
                        })
        
        # Build remote attribute rows (same logic as in _update_remote_table)
        remote_attribute_rows = []
        for fixture in remote_fixtures:
            if fixture.get('matched', False):
                # Get sorted attributes from the fixture's GDTF profile model
                profile_model = fixture.get('gdtf_profile')
                if profile_model:
                    selected_attributes = profile_model.get_sorted_attributes()
                else:
                    # Fallback to unsorted attributes if no profile model
                    selected_attributes = list(fixture.get('attributes', {}).keys())
                
                for attr_name in selected_attributes:
                    if attr_name in fixture.get('attributes', {}):
                        remote_attribute_rows.append({
                            'fixture_id': fixture.get('fixture_id', 0),
                            'fixture_name': fixture.get('name', ''),
                            'attribute': attr_name,
                            'fixture': fixture
                        })
        
        # Apply sequences by row number
        applied_count = 0
        min_rows = min(len(ma_attribute_rows), len(remote_attribute_rows))
        
        for i in range(min_rows):
            ma_row = ma_attribute_rows[i]
            remote_row = remote_attribute_rows[i]
            
            # Only apply if ma has a valid sequence number
            if ma_row['sequence'] != '—' and ma_row['sequence'] != '':
                remote_fixture = remote_row['fixture']
                attr_name = remote_row['attribute']
                
                # Initialize sequences dict if it doesn't exist
                if 'sequences' not in remote_fixture:
                    remote_fixture['sequences'] = {}
                
                # Copy sequence number
                remote_fixture['sequences'][attr_name] = ma_row['sequence']
                applied_count += 1
        
        # Update the tables to show the changes
        self._update_fixtures_tables()
        
        # Show result
        if applied_count > 0:
            self.status_label.setText(f"Applied {applied_count} sequence number{'s' if applied_count != 1 else ''} from ma to remote fixtures")
        else:
            QMessageBox.information(self, "No Sequences Applied", "No sequence numbers were applied. Make sure ma fixtures have sequence numbers assigned.")
    
    def _renumber_sequences(self):
        """Renumber sequences for ma fixtures based on current order and user settings."""
        from dialogs import RenumberSequencesDialog
        
        # Get ma fixtures using centralized access method
        ma_fixtures = self.get_ma_fixtures()
        
        if not ma_fixtures:
            QMessageBox.warning(self, "No Ma Fixtures", "No ma fixtures found. Please import fixtures and set some as ma first.")
            return
        
        # Show configuration dialog
        dialog = RenumberSequencesDialog(self.config, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        
        # Get settings from dialog
        settings = dialog.get_settings()
        start_number = settings["start_number"]
        interval = settings["interval"]
        add_breaks = settings["add_breaks"]
        break_sequences = settings["break_sequences"]
        
        # Renumber sequences
        sequence_num = start_number
        total_sequences = 0
        
        for fixture in ma_fixtures:
            if fixture.get('matched', False):
                # Initialize sequences dict if it doesn't exist
                if 'sequences' not in fixture:
                    fixture['sequences'] = {}
                
                # Get sorted attributes from the fixture's GDTF profile model
                profile_model = fixture.get('gdtf_profile')
                if profile_model:
                    sorted_attributes = profile_model.get_sorted_attributes()
                else:
                    # Fallback to unsorted attributes if no profile model
                    sorted_attributes = list(fixture.get('attributes', {}).keys())
                
                # Assign sequences to each attribute
                for attr_name in sorted_attributes:
                    if attr_name in fixture.get('attributes', {}):
                        fixture['sequences'][attr_name] = sequence_num
                        sequence_num += interval
                        total_sequences += 1
                
                # Add break after all attributes for this fixture if enabled
                if add_breaks:
                    sequence_num += break_sequences
        
        # Update the tables to show the changes
        self._update_fixtures_tables()
        
        # Show result
        self.status_label.setText(f"Renumbered {total_sequences} sequence{'s' if total_sequences != 1 else ''} starting from {start_number}")
        QMessageBox.information(
            self,
            "Sequences Renumbered",
            f"Successfully renumbered {total_sequences} sequence{'s' if total_sequences != 1 else ''}.\n\n"
            f"Starting number: {start_number}\n"
            f"Interval: {interval}\n"
            f"Breaks: {'Yes' if add_breaks else 'No'}"
            + (f"\nBreak sequences: {break_sequences}" if add_breaks else "")
        )
    
    def _export_ma3_remotes(self):
        """Export remote fixtures as MA3 DMX Remotes XML."""
        from PyQt6.QtWidgets import QFileDialog
        
        # Get remote fixtures only using centralized access method
        remote_fixtures = self.get_remote_fixtures()
        
        if not remote_fixtures:
            QMessageBox.warning(self, "No Remote Fixtures", "No remote fixtures found to export.")
            return
        
        # Get MA3 configuration from settings
        ma3_config = self.config.get_ma3_xml_config()
        
        # Get save file path from user
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export MA3 DMX Remotes",
            str(Path.home() / "ma3_dmx_remotes.xml"),
            "MA3 XML Files (*.xml)"
        )
        
        if not file_path:
            return
        
        try:
            # Export using the core exporter
            from core.exporter import export_to_ma3_dmx_remotes
            
            # Generate the XML - pass fixtures directly
            xml_content = export_to_ma3_dmx_remotes(remote_fixtures, ma3_config)
            
            # Save to file
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(xml_content)
            
            QMessageBox.information(
                self,
                "Export Successful",
                f"MA3 DMX Remotes exported successfully to:\n{file_path}"
            )
            self.status_label.setText(f"Exported MA3 DMX Remotes to {Path(file_path).name}")
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "Export Error",
                f"Failed to export MA3 DMX Remotes:\n{str(e)}"
            )
    
    def _export_ma3_sequences(self):
        """Export ma fixtures as MA3 sequences XML."""
        from PyQt6.QtWidgets import QFileDialog
        
        # Get ma fixtures only using centralized access method
        ma_fixtures = self.get_ma_fixtures()
        
        if not ma_fixtures:
            QMessageBox.warning(self, "No Ma Fixtures", "No ma fixtures found to export.")
            return
        
        # Get save file path from user
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export MA3 Sequences",
            str(Path.home() / "ma3_sequences.xml"),
            "MA3 XML Files (*.xml)"
        )
        
        if not file_path:
            return
        
        try:
            # Export using the core exporter
            from core.exporter import export_to_ma3_sequences
            
            # Generate the XML - pass fixtures directly
            xml_content = export_to_ma3_sequences(ma_fixtures)
            
            # Save to file
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(xml_content)
            
            # Count sequences generated
            sequence_count = 0
            for fixture in ma_fixtures:
                if fixture.get('matched', False):
                    sequence_count += len(fixture.get('sequences', {}))
            
            QMessageBox.information(
                self,
                "Export Successful",
                f"MA3 Sequences exported successfully to:\n{file_path}\n\n"
                f"Generated {sequence_count} sequences with values set to 100."
            )
            self.status_label.setText(f"Exported MA3 Sequences to {Path(file_path).name}")
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "Export Error",
                f"Failed to export MA3 Sequences:\n{str(e)}"
            )
    
    def _export_ma_csv(self):
        """Export ma fixtures as CSV."""
        from PyQt6.QtWidgets import QFileDialog
        
        # Get ma fixtures only using centralized access method
        ma_fixtures = self.get_ma_fixtures()
        
        if not ma_fixtures:
            QMessageBox.warning(self, "No Ma Fixtures", "No ma fixtures found to export.")
            return
        
        # Get save file path from user
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Ma Fixtures CSV",
            str(Path.home() / "ma_fixtures.csv"),
            "CSV Files (*.csv)"
        )
        
        if not file_path:
            return
        
        try:
            # Export using the core exporter
            from core.exporter import export_to_csv
            
            # Generate the CSV content
            csv_content = export_to_csv(ma_fixtures)
            
            # Save to file
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(csv_content)
            
            QMessageBox.information(
                self,
                "Export Successful",
                f"Ma fixtures exported successfully to:\n{file_path}"
            )
            self.status_label.setText(f"Exported Ma CSV to {Path(file_path).name}")
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "Export Error",
                f"Failed to export Ma CSV:\n{str(e)}"
            )
    
    def _export_remote_csv(self):
        """Export remote fixtures as CSV."""
        from PyQt6.QtWidgets import QFileDialog
        
        # Get remote fixtures only using centralized access method
        remote_fixtures = self.get_remote_fixtures()
        
        if not remote_fixtures:
            QMessageBox.warning(self, "No Remote Fixtures", "No remote fixtures found to export.")
            return
        
        # Get save file path from user
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Remote Fixtures CSV",
            str(Path.home() / "remote_fixtures.csv"),
            "CSV Files (*.csv)"
        )
        
        if not file_path:
            return
        
        try:
            # Export using the core exporter
            from core.exporter import export_to_csv
            
            # Generate the CSV content
            csv_content = export_to_csv(remote_fixtures)
            
            # Save to file
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(csv_content)
            
            QMessageBox.information(
                self,
                "Export Successful",
                f"Remote fixtures exported successfully to:\n{file_path}"
            )
            self.status_label.setText(f"Exported Remote CSV to {Path(file_path).name}")
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "Export Error",
                f"Failed to export Remote CSV:\n{str(e)}"
            )
    
    def _update_ui_state(self):
        """Update UI state based on current data."""
        has_fixtures = len(self.project_state['fixtures']) > 0
        has_selected_attributes = len(self.config.get_selected_attributes()) > 0
        
        # Get ma and remote fixtures using centralized access methods
        ma_fixtures = self.get_ma_fixtures()
        remote_fixtures = self.get_remote_fixtures()
        
        # Enable/disable buttons
        self.clear_fixtures_button.setEnabled(has_fixtures)
        self.apply_sequences_button.setEnabled(len(ma_fixtures) > 0 and len(remote_fixtures) > 0)
        self.renumber_sequences_button.setEnabled(len(ma_fixtures) > 0)
        self.export_ma3_remotes_button.setEnabled(len(remote_fixtures) > 0)
        self.export_ma3_sequences_button.setEnabled(len(ma_fixtures) > 0)
        self.export_ma_csv_button.setEnabled(len(ma_fixtures) > 0)
        self.export_remote_csv_button.setEnabled(len(remote_fixtures) > 0)
    
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
    
    def _update_recent_projects_menu(self):
        """Update the recent projects menu with current projects."""
        self.recent_projects_menu.clear()
        
        recent_projects = self.config.get_recent_projects()
        
        if not recent_projects:
            no_projects_action = QAction("No recent projects", self)
            no_projects_action.setEnabled(False)
            self.recent_projects_menu.addAction(no_projects_action)
            return
        
        for i, project_path in enumerate(recent_projects):
            # Check if project file still exists
            if not Path(project_path).exists():
                continue
            
            # Create action with project name
            project_name = Path(project_path).stem
            action = QAction(f"{i+1}. {project_name}", self)
            action.setData(project_path)
            action.triggered.connect(lambda checked, path=project_path: self._load_recent_project(path))
            self.recent_projects_menu.addAction(action)
        
        # Add separator and clear action if we have projects
        if self.recent_projects_menu.actions():
            self.recent_projects_menu.addSeparator()
            clear_action = QAction("Clear Recent Projects", self)
            clear_action.triggered.connect(self._clear_recent_projects)
            self.recent_projects_menu.addAction(clear_action)
    
    def _load_recent_project(self, project_path: str):
        """Load a project from the recent projects list."""
        project_file = Path(project_path)
        
        if not project_file.exists():
            QMessageBox.warning(
                self,
                "Project Not Found",
                f"The project file could not be found:\n{project_path}\n\n"
                "It may have been moved or deleted."
            )
            # Remove from recent projects
            self.config.remove_recent_project(project_path)
            return
        
        # Check if this is a valid project
        project_info = project_manager.get_project_info(project_file)
        if not project_info:
            QMessageBox.warning(
                self,
                "Invalid Project",
                "The selected file is not a valid AttributeAddresser project.\n\n"
                "Please select a .aa file created by this application."
            )
            # Remove from recent projects
            self.config.remove_recent_project(project_path)
            return
        
        # Confirm loading (in case user has unsaved changes)
        reply = QMessageBox.question(
            self,
            "Load Project",
            f"Load project '{project_info['name']}'?\n"
            f"This will replace the current project data.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        # Load the project
        app_state, config_data = project_manager.load_project(project_file)
        
        if app_state is not None:
            # Restore application state
            self.project_state = app_state
            
            # Store the current project path
            self.current_project_path = project_file
            
            # Restore configuration if needed
            if config_data:
                self._restore_config(config_data)
            
            # Reprocess matched fixtures to recalculate universe/channel/absolute address data
            core.reprocess_matched_fixtures(self.project_state['fixtures'])
            
            # Update UI
            self._update_fixtures_tables()
            self._update_status_info()
            self._update_ui_state()
            
            QMessageBox.information(
                self,
                "Project Loaded",
                f"Project '{project_info['name']}' loaded successfully.\n"
                f"Fixtures: {project_info['fixture_count']}"
            )
            self.status_label.setText(f"Project loaded: {project_info['name']}")
        else:
            QMessageBox.critical(
                self,
                "Load Error",
                "Failed to load project. Please check the console for details."
            )
    
    def _clear_recent_projects(self):
        """Clear all recent projects."""
        reply = QMessageBox.question(
            self,
            "Clear Recent Projects",
            "Are you sure you want to clear all recent projects?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.config.clear_recent_projects()

    def _save_project(self):
        """Save the current project."""
        # If we have a current project path, save there, otherwise do Save As
        if hasattr(self, 'current_project_path') and self.current_project_path:
            success = project_manager.save_project(self.current_project_path, self.project_state, self.config)
            if success:
                # Add to recent projects
                self.config.add_recent_project(str(self.current_project_path))
                # Update last project directory
                self.config.set_last_project_directory(str(self.current_project_path.parent))
                self.status_label.setText(f"Project saved to {self.current_project_path.name}")
            else:
                QMessageBox.critical(self, "Save Error", "Failed to save project. Please check the console for details.")
        else:
            self._save_project_as()
    
    def _save_project_as(self):
        """Save the current project with a new name."""
        from PyQt6.QtWidgets import QFileDialog, QInputDialog
        
        # Get project name from user
        project_name, ok = QInputDialog.getText(
            self,
            "Save Project As",
            "Enter project name:",
            text="MyProject"
        )
        
        if not ok or not project_name.strip():
            return
        
        # Clean the project name (remove invalid characters)
        project_name = "".join(c for c in project_name if c.isalnum() or c in (' ', '-', '_')).strip()
        if not project_name:
            QMessageBox.warning(self, "Invalid Name", "Please enter a valid project name.")
            return
        
        # Get save file path from user - use last project directory if available
        last_dir = self.config.get_last_project_directory()
        if last_dir and Path(last_dir).exists():
            default_path = Path(last_dir) / f"{project_name}.aa"
        else:
            default_path = Path.home() / f"{project_name}.aa"
        
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Project As",
            str(default_path),
            "AttributeAddresser Projects (*.aa)"
        )
        
        if not file_path:
            return
        
        project_path = Path(file_path)
        
        # Check if project already exists
        if project_path.exists():
            reply = QMessageBox.question(
                self,
                "Project Exists",
                f"Project '{project_name}' already exists. Do you want to overwrite it?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply != QMessageBox.StandardButton.Yes:
                return
        
        # Save the project
        success = project_manager.save_project(project_path, self.project_state, self.config)
        
        if success:
            # Store the current project path
            self.current_project_path = project_path
            # Add to recent projects
            self.config.add_recent_project(str(project_path))
            # Update last project directory
            self.config.set_last_project_directory(str(project_path.parent))
            QMessageBox.information(
                self,
                "Project Saved",
                f"Project '{project_name}' saved successfully to:\n{project_path}"
            )
            self.status_label.setText(f"Project saved: {project_name}")
        else:
            QMessageBox.critical(
                self,
                "Save Error",
                "Failed to save project. Please check the console for details."
            )
    
    def _load_project(self):
        """Load a project."""
        from PyQt6.QtWidgets import QFileDialog
        
        # Get load file path from user - use last project directory if available
        last_dir = self.config.get_last_project_directory()
        if last_dir and Path(last_dir).exists():
            default_dir = last_dir
        else:
            default_dir = str(Path.home())
        
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Load Project",
            default_dir,
            "AttributeAddresser Projects (*.aa)"
        )
        
        if not file_path:
            return
        
        project_path = Path(file_path)
        
        # Check if this is a valid project
        project_info = project_manager.get_project_info(project_path)
        if not project_info:
            QMessageBox.warning(
                self,
                "Invalid Project",
                "The selected file is not a valid AttributeAddresser project.\n\n"
                "Please select a .aa file created by this application."
            )
            return
        
        # Confirm loading (in case user has unsaved changes)
        reply = QMessageBox.question(
            self,
            "Load Project",
            f"Load project '{project_info['name']}'?\n"
            f"This will replace the current project data.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        # Load the project
        app_state, config_data = project_manager.load_project(project_path)
        
        if app_state is not None:
            # Restore application state
            self.project_state = app_state
            
            # Store the current project path
            self.current_project_path = project_path
            
            # Add to recent projects
            self.config.add_recent_project(str(project_path))
            # Update last project directory
            self.config.set_last_project_directory(str(project_path.parent))
            
            # Restore configuration if needed
            if config_data:
                self._restore_config(config_data)
            
            # Reprocess matched fixtures to recalculate universe/channel/absolute address data
            core.reprocess_matched_fixtures(self.project_state['fixtures'])
            
            # Update UI
            self._update_fixtures_tables()
            self._update_status_info()
            self._update_ui_state()
            
            QMessageBox.information(
                self,
                "Project Loaded",
                f"Project '{project_info['name']}' loaded successfully.\n"
                f"Fixtures: {project_info['fixture_count']}"
            )
            self.status_label.setText(f"Project loaded: {project_info['name']}")
        else:
            QMessageBox.critical(
                self,
                "Load Error",
                "Failed to load project. Please check the console for details."
            )
    
    def _restore_config(self, config_data: Dict[str, Any]):
        """Restore configuration from saved data."""
        # Configuration is handled separately from project data
        # Project data contains fixtures and GDTF profiles
        # Config contains user preferences and settings
        if config_data:
            print(f"Config data available: {list(config_data.keys())}")
    
    # Centralized data access methods for single source of truth
    def get_ma_fixtures(self) -> List[Dict[str, Any]]:
        """Get all ma fixtures from the project state."""
        return core.get_ma_fixtures(self.project_state['fixtures'])
    
    def get_remote_fixtures(self) -> List[Dict[str, Any]]:
        """Get all remote fixtures from the project state."""
        return core.get_remote_fixtures(self.project_state['fixtures'])
    
    def get_ma_fixtures_matched(self) -> List[Dict[str, Any]]:
        """Get all matched ma fixtures from the project state."""
        return core.get_ma_fixtures_matched(self.project_state['fixtures'])
    
    def get_remote_fixtures_matched(self) -> List[Dict[str, Any]]:
        """Get all matched remote fixtures from the project state."""
        return core.get_remote_fixtures_matched(self.project_state['fixtures'])
    
    def get_fixture_statistics(self) -> Dict[str, Any]:
        """Get comprehensive fixture statistics."""
        return core.validate_fixture_roles(self.project_state['fixtures'])
    
    def validate_fixture_data(self) -> bool:
        """Validate that all fixtures have consistent data."""
        return core.ensure_fixture_role_consistency(self.project_state['fixtures'])


def main():
    """Run the application."""
    app = QApplication(sys.argv)
    app.setApplicationName("AttributeAddresser")
    app.setApplicationVersion("2.0")
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec()) 