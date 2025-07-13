"""
Clean GUI for MVR File Analyzer
Pure UI logic using controller architecture.
"""

import sys
import os
from pathlib import Path
from typing import List, Optional, Dict, Any

# PyQt6 imports
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QFileDialog, QTextEdit, QCheckBox,
    QGroupBox, QScrollArea, QComboBox, QProgressBar, QMessageBox,
    QFrame, QGridLayout, QDialog, QMenuBar, QMenu, QRadioButton,
    QButtonGroup, QTableWidget, QTableWidgetItem, QHeaderView,
    QTreeWidget, QTreeWidgetItem
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QSettings
from PyQt6.QtGui import QFont, QAction, QColor

# Import our clean architecture
from config import Config
from controllers.main_controller import MVRController
from views.gdtf_matching_dialog import GDTFMatchingDialog
from views.fixture_attribute_dialog import FixtureAttributeDialog
from views.ma3_xml_dialog import MA3XMLDialog
from views.csv_import_dialog import CSVImportDialog


class AnalysisWorker(QThread):
    """Background worker for running analysis without freezing the GUI."""
    
    progress_update = pyqtSignal(str)
    analysis_complete = pyqtSignal(dict)
    analysis_error = pyqtSignal(str)
    
    def __init__(self, controller: MVRController, fixture_type_attributes: Dict[str, List[str]], output_format: str, ma3_config: dict = None):
        super().__init__()
        self.controller = controller
        self.fixture_type_attributes = fixture_type_attributes
        self.output_format = output_format
        self.ma3_config = ma3_config
    
    def run(self):
        """Run the analysis in background thread."""
        try:
            self.progress_update.emit("Starting analysis...")
            result = self.controller.analyze_fixtures_by_type(self.fixture_type_attributes, self.output_format, self.ma3_config)
            
            if result["success"]:
                self.analysis_complete.emit(result)
            else:
                self.analysis_error.emit(result["error"])
                
        except Exception as e:
            self.analysis_error.emit(str(e))


class MVRApp(QMainWindow):
    """Main application window - Clean UI only."""
    
    def __init__(self):
        super().__init__()
        self.controller = MVRController()
        self.config = Config()
        self.current_results = None
        self.worker = None
        self.fixture_type_attributes = {}  # Store per-fixture-type attributes
        self.ma3_config = None  # Store MA3 configuration
        self.current_project_path = None  # Current project file path
        self.project_dirty = False  # Whether project has unsaved changes
        self.setup_ui()
        self.update_ui_state()
    
    def setup_ui(self):
        """Create the main user interface."""
        self.setWindowTitle("AttributeAddresser")
        self.setGeometry(100, 100, 1200, 800)
        
        # Additional window properties for better branding
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowTitleHint)
        
        # Create menu bar
        self.create_menu_bar()
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout - Single vertical column
        main_layout = QVBoxLayout(central_widget)
        
        # Create horizontal layout for the first three steps
        steps_horizontal_layout = QHBoxLayout()
        
        # Add first three control sections to horizontal layout with equal stretch
        control_sections = self.create_control_sections()
        for section in control_sections:
            steps_horizontal_layout.addWidget(section, 1)  # Each section gets equal stretch (1/3 of space)
        
        # Add the horizontal layout to main layout
        main_layout.addLayout(steps_horizontal_layout)
        
        # Add results section in the middle
        results_section = self.create_results_section()
        main_layout.addWidget(results_section, 1)  # Give it stretch priority
        
        # Add export section at the bottom
        export_section = self.create_export_section()
        main_layout.addWidget(export_section)
        
        # Status bar
        self.status_bar = self.statusBar()
        self.status_bar.showMessage("Ready")
        
        # Set minimum window size
        self.setMinimumWidth(800)
        
        # Initialize MA3 config button visibility based on current format
        current_format = self.format_combo.currentText()
        self.ma3_config_btn.setVisible(current_format == "ma3_xml")
        
        # Load MA3 config if format is ma3_xml and config is None
        if current_format == "ma3_xml" and self.ma3_config is None:
            self.ma3_config = self.config.get_ma3_xml_config()
    
    def create_menu_bar(self):
        """Create the application menu bar."""
        menubar = self.menuBar()
        
        # On macOS, add an application menu
        if sys.platform == "darwin":
            app_menu = menubar.addMenu('AttributeAddresser')
            
            # About action
            about_action = QAction('About AttributeAddresser', self)
            about_action.triggered.connect(self.show_about)
            app_menu.addAction(about_action)
            
            app_menu.addSeparator()
            
            # Quit action (macOS style)
            quit_action = QAction('Quit AttributeAddresser', self)
            quit_action.setShortcut('Cmd+Q')
            quit_action.triggered.connect(self.close)
            app_menu.addAction(quit_action)
        
        # File menu
        file_menu = menubar.addMenu('File')
        
        # New Project
        new_action = QAction('New Project', self)
        new_action.setShortcut('Ctrl+N')
        new_action.triggered.connect(self.new_project)
        file_menu.addAction(new_action)
        
        file_menu.addSeparator()
        
        # Load Project
        load_action = QAction('Load Project...', self)
        load_action.setShortcut('Ctrl+O')
        load_action.triggered.connect(self.load_project)
        file_menu.addAction(load_action)
        
        # Recent Projects submenu
        self.recent_menu = file_menu.addMenu('Recent Projects')
        self.update_recent_projects_menu()
        
        file_menu.addSeparator()
        
        # Save Project
        self.save_action = QAction('Save Project', self)
        self.save_action.setShortcut('Ctrl+S')
        self.save_action.triggered.connect(self.save_project)
        self.save_action.setEnabled(False)
        file_menu.addAction(self.save_action)
        
        # Save Project As
        save_as_action = QAction('Save Project As...', self)
        save_as_action.setShortcut('Ctrl+Shift+S')
        save_as_action.triggered.connect(self.save_project_as)
        file_menu.addAction(save_as_action)
        
        file_menu.addSeparator()
        
        # Exit
        exit_action = QAction('Exit', self)
        exit_action.setShortcut('Ctrl+Q')
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
    
    def create_control_sections(self) -> List[QWidget]:
        """Create all control sections as separate group boxes."""
        sections = []
        
        # File selection group
        file_group = QGroupBox("1. File Selection")
        file_layout = QVBoxLayout(file_group)
        
        # Import type selection
        import_type_layout = QHBoxLayout()
        import_type_layout.addWidget(QLabel("Import Type:"))
        
        self.import_type_group = QButtonGroup()
        self.mvr_radio = QRadioButton("MVR File")
        self.csv_radio = QRadioButton("CSV File")
        self.mvr_radio.setChecked(True)  # Default to MVR
        
        self.import_type_group.addButton(self.mvr_radio)
        self.import_type_group.addButton(self.csv_radio)
        
        import_type_layout.addWidget(self.mvr_radio)
        import_type_layout.addWidget(self.csv_radio)
        import_type_layout.addStretch()
        
        file_layout.addLayout(import_type_layout)
        
        # File status label
        self.file_label = QLabel("No file selected")
        self.file_label.setWordWrap(True)
        self.file_label.setStyleSheet("padding: 10px; border: 1px solid #ccc; border-radius: 4px;")
        file_layout.addWidget(self.file_label)
        
        # Browse button
        self.browse_btn = QPushButton("Browse MVR File...")
        self.browse_btn.clicked.connect(self.browse_file)
        file_layout.addWidget(self.browse_btn)
        
        # Connect radio buttons to update browse button text
        self.mvr_radio.toggled.connect(self.update_browse_button)
        self.csv_radio.toggled.connect(self.update_browse_button)
        
        sections.append(file_group)
        
        # GDTF Matching group
        gdtf_group = QGroupBox("2. GDTF Profile Matching")
        gdtf_layout = QVBoxLayout(gdtf_group)
        
        self.gdtf_status_label = QLabel("Load a file first")
        self.gdtf_status_label.setWordWrap(True)
        self.gdtf_status_label.setStyleSheet("color: gray; font-style: italic; padding: 5px;")
        gdtf_layout.addWidget(self.gdtf_status_label)
        
        # Manual matching button
        self.match_gdtf_btn = QPushButton("Match GDTF Profiles")
        self.match_gdtf_btn.clicked.connect(self.match_gdtf_profiles)
        self.match_gdtf_btn.setEnabled(False)
        self.match_gdtf_btn.setToolTip("Match fixture types to GDTF profiles")
        gdtf_layout.addWidget(self.match_gdtf_btn)
        
        sections.append(gdtf_group)
        
        # Attribute Selection group
        attribute_group = QGroupBox("3. Attribute Selection")
        attribute_layout = QVBoxLayout(attribute_group)
        
        self.attribute_status_label = QLabel("Complete steps 1-2 first")
        self.attribute_status_label.setWordWrap(True)
        self.attribute_status_label.setStyleSheet("color: gray; font-style: italic; padding: 5px;")
        attribute_layout.addWidget(self.attribute_status_label)
        
        # Select Attributes button
        self.select_attrs_btn = QPushButton("Select Attributes")
        self.select_attrs_btn.clicked.connect(self.select_attributes)
        self.select_attrs_btn.setEnabled(False)
        attribute_layout.addWidget(self.select_attrs_btn)
        
        sections.append(attribute_group)
        
        return sections
    
    def update_browse_button(self):
        """Update the browse button text based on selected import type."""
        if self.mvr_radio.isChecked():
            self.browse_btn.setText("Browse MVR File...")
        else:
            self.browse_btn.setText("Browse CSV File...")
    
    def browse_file(self):
        """Open file dialog to select MVR or CSV file based on selection."""
        if self.mvr_radio.isChecked():
            self.browse_mvr_file()
        else:
            self.browse_csv_file()
    
    def browse_mvr_file(self):
        """Open file dialog to select MVR file."""
        # Get last used directory
        last_dir = self.config.get_last_mvr_directory()
        start_dir = last_dir if last_dir and os.path.exists(last_dir) else ""
        
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select MVR File",
            start_dir,
            "MVR Files (*.mvr);;All Files (*)"
        )
        
        if file_path:
            # Save the directory for next time
            self.config.set_last_mvr_directory(str(Path(file_path).parent))
            self.load_mvr_file(file_path)
    
    def create_results_section(self) -> QWidget:
        """Create the results section with hierarchical tree view."""
        # Results group
        results_group = QGroupBox("Analysis Results")
        layout = QVBoxLayout(results_group)
        
        # Results status label
        self.results_status = QLabel("Complete steps 1-3 for automatic analysis")
        self.results_status.setStyleSheet("color: gray; font-style: italic; padding: 10px;")
        layout.addWidget(self.results_status)
        
        # Results tree widget
        self.results_tree = QTreeWidget()
        self.results_tree.setAlternatingRowColors(True)
        self.results_tree.setRootIsDecorated(True)
        self.results_tree.setIndentation(20)
        
        # Set initial headers
        self.results_tree.setHeaderLabels(["Name", "Type", "Value", "Universe", "Channel", "DMX"])
        
        # Set initial empty state
        self._setup_empty_results_tree()
        
        layout.addWidget(self.results_tree)
        
        return results_group

    def create_export_section(self) -> QWidget:
        """Create the export section with format selection and export controls."""
        # Export group
        export_group = QGroupBox("4. Export")
        export_layout = QHBoxLayout(export_group)
        
        # Output format selection
        export_layout.addWidget(QLabel("Output Format:"))
        self.format_combo = QComboBox()
        self.format_combo.addItems(["text", "csv", "json", "ma3_xml"])
        self.format_combo.setCurrentText(self.config.get_output_format())
        self.format_combo.currentTextChanged.connect(self.on_format_changed)
        export_layout.addWidget(self.format_combo)
        
        # MA3 XML configuration button (initially hidden)
        self.ma3_config_btn = QPushButton("MA3 XML Settings")
        self.ma3_config_btn.clicked.connect(self.configure_ma3_xml)
        self.ma3_config_btn.setVisible(False)
        export_layout.addWidget(self.ma3_config_btn)
        
        # Progress bar for automatic analysis
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        export_layout.addWidget(self.progress_bar)
        
        # Export button
        self.export_btn = QPushButton("Export Results")
        self.export_btn.clicked.connect(self.export_results)
        self.export_btn.setEnabled(False)
        export_layout.addWidget(self.export_btn)
        
        return export_group

    def _setup_empty_results_tree(self):
        """Set up the results tree in empty state."""
        self.results_tree.clear()
        
        # Add a status item
        status_item = QTreeWidgetItem()
        status_item.setText(0, "Complete steps 1-3 for automatic analysis")
        status_item.setForeground(0, QColor("gray"))
        
        # Set italic font
        font = QFont()
        font.setItalic(True)
        status_item.setFont(0, font)
        
        self.results_tree.addTopLevelItem(status_item)
        
        # Resize to fit content
        self.results_tree.resizeColumnToContents(0)

    def _populate_results_tree(self, analysis_results: dict):
        """Populate the results tree with hierarchical analysis data."""
        if not analysis_results or not analysis_results.get("success"):
            self._show_error_in_tree("Analysis failed")
            return
        
        results = analysis_results.get("analysis_results")
        if not results:
            self._show_error_in_tree("No analysis results available")
            return
        
        fixtures = results.fixtures
        if not fixtures:
            self._show_error_in_tree("No fixtures to display")
            return
        
        # Clear the tree
        self.results_tree.clear()
        
        # Sort fixtures by fixture_id
        sorted_fixtures = sorted([f for f in fixtures if f.is_matched()], key=lambda x: x.fixture_id)
        
        for fixture in sorted_fixtures:
            # Create fixture parent item
            fixture_type = fixture.gdtf_spec or "Unknown"
            if fixture_type.endswith('.gdtf'):
                fixture_type = fixture_type[:-5]
            
            # Get fixture type to determine which attributes to show
            fixture_type_clean = fixture_type.replace('.gdtf', '') if fixture_type.endswith('.gdtf') else fixture_type
            fixture_attributes = self.fixture_type_attributes.get(fixture_type_clean, [])
            
            # Create fixture item with summary info
            fixture_item = QTreeWidgetItem()
            fixture_item.setText(0, f"Fixture {fixture.fixture_id}: {fixture.name}")
            fixture_item.setText(1, "FIXTURE")
            fixture_item.setText(2, fixture_type)
            fixture_item.setText(3, str(fixture.base_address))
            fixture_item.setText(4, fixture.gdtf_mode or "")
            
            # Set fixture item styling
            font = QFont()
            font.setBold(True)
            fixture_item.setFont(0, font)
            fixture_item.setForeground(0, QColor("darkblue"))
            
            # Add attribute child items
            if hasattr(fixture, 'absolute_addresses') and fixture.absolute_addresses:
                for attr_name in fixture_attributes:
                    if attr_name in fixture.absolute_addresses:
                        addr_info = fixture.absolute_addresses[attr_name]
                        universe = addr_info.get("universe", "?")
                        channel = addr_info.get("channel", "?")
                        absolute_address = addr_info.get("absolute_address", "?")
                        
                        # Create attribute child item
                        attr_item = QTreeWidgetItem()
                        attr_item.setText(0, attr_name)
                        attr_item.setText(1, "ATTRIBUTE")
                        attr_item.setText(2, f"{universe}.{channel}")
                        attr_item.setText(3, str(universe))
                        attr_item.setText(4, str(channel))
                        attr_item.setText(5, str(absolute_address))
                        
                        # Set attribute item styling
                        attr_item.setForeground(0, QColor("darkgreen"))
                        
                        fixture_item.addChild(attr_item)
                    else:
                        # Attribute selected but not available in GDTF
                        attr_item = QTreeWidgetItem()
                        attr_item.setText(0, attr_name)
                        attr_item.setText(1, "ATTRIBUTE")
                        attr_item.setText(2, "N/A - Not in GDTF")
                        
                        # Set N/A styling
                        attr_item.setForeground(0, QColor("orange"))
                        attr_item.setForeground(2, QColor("orange"))
                        
                        fixture_item.addChild(attr_item)
            
            # If no attributes, add a placeholder
            if fixture_item.childCount() == 0:
                no_attr_item = QTreeWidgetItem()
                no_attr_item.setText(0, "No attributes selected")
                no_attr_item.setForeground(0, QColor("gray"))
                
                font = QFont()
                font.setItalic(True)
                no_attr_item.setFont(0, font)
                
                fixture_item.addChild(no_attr_item)
            
            # Add fixture to tree
            self.results_tree.addTopLevelItem(fixture_item)
            
            # Expand the fixture to show attributes
            fixture_item.setExpanded(True)
        
        # Resize columns to fit content
        for i in range(self.results_tree.columnCount()):
            self.results_tree.resizeColumnToContents(i)

    def _show_error_in_tree(self, error_message: str):
        """Show an error message in the tree."""
        self.results_tree.clear()
        
        error_item = QTreeWidgetItem()
        error_item.setText(0, error_message)
        error_item.setForeground(0, QColor("red"))
        
        # Set bold font
        font = QFont()
        font.setBold(True)
        error_item.setFont(0, font)
        
        self.results_tree.addTopLevelItem(error_item)
        
        # Resize to fit content
        self.results_tree.resizeColumnToContents(0)
        
    def _clear_results_tree(self):
        """Clear the results tree and show empty state."""
        self._setup_empty_results_tree()
        self.results_status.setText("Complete steps 1-3 for automatic analysis")
        self.results_status.setStyleSheet("color: gray; font-style: italic; padding: 10px;")

    def _should_trigger_analysis(self) -> bool:
        """Check if automatic analysis should be triggered."""
        # Check if we have everything needed for analysis
        status = self.controller.get_current_status()
        
        # Step 1: File loaded
        if not status["file_loaded"]:
            return False
            
        # Step 2: GDTF matching (at least some fixtures matched)
        if status["matched_fixtures"] <= 0:
            return False
            
        # Step 3: Attributes selected
        if not self.fixture_type_attributes:
            return False
            
        # Check if any attributes are actually selected
        total_attributes = sum(len(attrs) for attrs in self.fixture_type_attributes.values())
        if total_attributes <= 0:
            return False
            
        return True

    def _trigger_automatic_analysis(self):
        """Trigger automatic analysis if conditions are met."""
        if not self._should_trigger_analysis():
            self._clear_results_tree()
            return
            
        # Prevent multiple concurrent analyses
        if self.worker is not None:
            return
            
        self.results_status.setText("Analyzing automatically...")
        self.results_status.setStyleSheet("color: blue; font-weight: bold; padding: 10px;")
        
        # Get output format
        output_format = self.format_combo.currentText()
        
        # Handle MA3 XML configuration
        ma3_config = None
        if output_format == "ma3_xml":
            if self.ma3_config is None:
                self.results_status.setText("Configure MA3 XML settings first")
                self.results_status.setStyleSheet("color: orange; font-weight: bold; padding: 10px;")
                return
            ma3_config = self.ma3_config
        
        # Show progress
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Indeterminate progress
        
        # Start analysis in background thread
        self.worker = AnalysisWorker(self.controller, self.fixture_type_attributes, output_format, ma3_config)
        self.worker.progress_update.connect(self.update_progress)
        self.worker.analysis_complete.connect(self.analysis_complete)
        self.worker.analysis_error.connect(self.analysis_error)
        self.worker.start()

    def _update_results_status(self):
        """Update the results status based on current state."""
        if self._should_trigger_analysis():
            if self.current_results:
                summary = self.current_results.get("summary", {})
                total_fixtures = summary.get("total_fixtures", 0)
                matched_fixtures = summary.get("matched_fixtures", 0)
                conflicts = len(summary.get("conflicts", []))
                
                status_msg = f"Analysis complete: {matched_fixtures}/{total_fixtures} fixtures"
                if conflicts > 0:
                    status_msg += f", {conflicts} conflicts"
                
                self.results_status.setText(status_msg)
                self.results_status.setStyleSheet("color: green; font-weight: bold; padding: 10px;")
            else:
                self.results_status.setText("Ready for automatic analysis")
                self.results_status.setStyleSheet("color: blue; font-weight: bold; padding: 10px;")
        else:
            self.results_status.setText("Complete steps 1-3 for automatic analysis")
            self.results_status.setStyleSheet("color: gray; font-style: italic; padding: 10px;")
    
    def browse_csv_file(self):
        """Open CSV import dialog."""
        try:
            dialog = CSVImportDialog(self, self.config)
            
            # Connect the import successful signal
            dialog.import_successful.connect(self.load_csv_fixtures)
            
            dialog.exec()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error opening CSV import dialog:\n{str(e)}")
    
    def load_csv_fixtures(self, fixture_matches: List):
        """Load fixtures from CSV import."""
        try:
            result = self.controller.load_csv_fixtures(fixture_matches)
            
            if result["success"]:
                # Update UI
                self.file_label.setText(f"✓ CSV Import ({result['total_fixtures']} fixtures)")
                self.file_label.setStyleSheet("padding: 10px; border: 1px solid #4CAF50; border-radius: 4px; background-color: #E8F5E8; color: #2E7D32; font-weight: bold;")
                
                # Update GDTF status
                self._update_gdtf_status(result["matched_fixtures"], result["total_fixtures"])
                
                # Update UI state
                self.update_ui_state()
                self.mark_project_dirty()
                
                # Trigger automatic analysis
                self._trigger_automatic_analysis()
                
                self.status_bar.showMessage(f"Loaded {result['total_fixtures']} fixtures from CSV import")
                
            else:
                QMessageBox.critical(self, "Error", f"Failed to load CSV fixtures:\n{result['error']}")
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error loading CSV fixtures:\n{str(e)}")
    
    def load_mvr_file(self, file_path: str):
        """Load an MVR file using the controller."""
        self.status_bar.showMessage("Loading MVR file...")
        
        try:
            result = self.controller.load_mvr_file(file_path)
            
            if result["success"]:
                # Update UI
                self.file_label.setText(f"✓ {Path(file_path).name}")
                self.file_label.setStyleSheet("padding: 10px; border: 1px solid #4CAF50; border-radius: 4px; background-color: #E8F5E8; color: #2E7D32; font-weight: bold;")
                
                # Update GDTF status
                self._update_gdtf_status(result["matched_fixtures"], result["total_fixtures"])
                
                # Update UI state
                self.update_ui_state()
                self.mark_project_dirty()
                
                # Trigger automatic analysis
                self._trigger_automatic_analysis()
                
                self.status_bar.showMessage(f"Loaded {result['total_fixtures']} fixtures from {Path(file_path).name}")
                
            else:
                QMessageBox.critical(self, "Error", f"Failed to load MVR file:\n{result['error']}")
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error loading file:\n{str(e)}")
    
    def match_gdtf_profiles(self):
        """Open GDTF matching dialog."""
        try:
            # Check if we have fixtures loaded
            if not self.controller.matched_fixtures:
                QMessageBox.warning(self, "No Fixtures", "Please load fixtures first (MVR or CSV).")
                return
            
            dialog = GDTFMatchingDialog(self, self.controller, self.config)
            
            if dialog.exec() == QDialog.DialogCode.Accepted:
                # Get the fixture type matches from the dialog
                fixture_type_matches = dialog.get_fixture_type_matches()
                
                # Update matches in controller
                result = self.controller.update_fixture_matches(fixture_type_matches)
                
                if result["success"]:
                    matched_count = result["matched_fixtures"]
                    total_count = result["total_fixtures"]
                    
                    # Update GDTF status
                    self._update_gdtf_status(matched_count, total_count)
                    
                    # Update UI state
                    self.update_ui_state()
                    self.mark_project_dirty()
                    
                    # Trigger automatic analysis
                    self._trigger_automatic_analysis()
                    
                    self.status_bar.showMessage(f"Updated fixture matches: {matched_count}/{total_count} matched")
                else:
                    QMessageBox.critical(self, "Error", f"Failed to update matches:\n{result['error']}")
                    
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error in GDTF matching:\n{str(e)}")
    
    def load_external_gdtf_profiles(self):
        """Load external GDTF profiles for CSV matching."""
        try:
            # Get the last used directory
            last_dir = self.config.get_external_gdtf_folder() if self.config else ""
            
            folder_path = QFileDialog.getExistingDirectory(
                self, 
                "Select GDTF Profiles Folder", 
                last_dir
            )
            
            if not folder_path:
                return
            
            # Load profiles
            result = self.controller.load_external_gdtf_profiles(folder_path)
            
            if result["success"]:
                profile_count = result["profiles_loaded"]
                
                # Save folder path
                if self.config:
                    self.config.set_external_gdtf_folder(folder_path)
                
                # Update UI state
                self.update_ui_state()
                self.mark_project_dirty()
                
                # Trigger automatic analysis since new GDTF profiles might affect matching
                self._trigger_automatic_analysis()
                
                QMessageBox.information(
                    self, 
                    "External GDTF Profiles Loaded", 
                    f"Successfully loaded {profile_count} GDTF profiles from:\n{folder_path}\n\n"
                    f"Use 'Match GDTF Profiles' to match these profiles to your fixtures."
                )
                
                self.status_bar.showMessage(f"Loaded {profile_count} external GDTF profiles")
                
            else:
                QMessageBox.critical(self, "Error", f"Failed to load external GDTF profiles:\n{result['error']}")
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error loading external GDTF profiles:\n{str(e)}")
    
    def select_attributes(self):
        """Open attribute selection dialog and save selections independently."""
        try:
            # Open the fixture attribute dialog with existing selections
            dialog = FixtureAttributeDialog(self, self.controller, self.config, self.fixture_type_attributes)
            
            if dialog.exec() == QDialog.DialogCode.Accepted:
                # Get selected attributes per fixture type
                self.fixture_type_attributes = dialog.get_fixture_type_attributes()
                
                # Validate that we have some attributes selected
                total_selected = sum(len(attrs) for attrs in self.fixture_type_attributes.values())
                if total_selected == 0:
                    QMessageBox.warning(self, "No Attributes", "No attributes were selected. You can modify your selection anytime.")
                    self.fixture_type_attributes = {}
                else:
                    # Store the attributes in config (for future reference)
                    self.config.set_fixture_type_attributes(self.fixture_type_attributes)
                    
                    # Mark project as dirty
                    self.mark_project_dirty()
                
                # Update UI state after any changes
                self.update_ui_state()
                
                # Trigger automatic analysis
                self._trigger_automatic_analysis()
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error in attribute selection:\n{str(e)}")
    

    
    def update_progress(self, message: str):
        """Update progress message."""
        self.status_bar.showMessage(message)
    
    def analysis_complete(self, result: dict):
        """Handle successful analysis completion."""
        self.worker = None
        self.progress_bar.setVisible(False)
        
        # Store results
        self.current_results = result
        
        # Update UI
        self._populate_results_tree(result)
        self.export_btn.setEnabled(True)
        
        # Update results status
        self._update_results_status()
        
        # Update UI state (this will re-enable buttons appropriately)
        self.update_ui_state()
        
        # Show summary
        summary = result.get("summary", {})
        total_fixtures = summary.get("total_fixtures", 0)
        matched_fixtures = summary.get("matched_fixtures", 0)
        conflicts = len(summary.get("conflicts", []))
        
        status_msg = f"Analysis complete: {matched_fixtures}/{total_fixtures} fixtures analyzed"
        if conflicts > 0:
            status_msg += f", {conflicts} address conflicts found"
        
        self.status_bar.showMessage(status_msg)
    
    def analysis_error(self, error: str):
        """Handle analysis error."""
        self.worker = None
        self.progress_bar.setVisible(False)
        
        # Show error in tree
        self._show_error_in_tree(f"Analysis failed: {error}")
        
        # Update results status
        self.results_status.setText("Analysis failed")
        self.results_status.setStyleSheet("color: red; font-weight: bold; padding: 10px;")
        
        # Update UI state (this will re-enable buttons appropriately)
        self.update_ui_state()
        
        QMessageBox.critical(self, "Analysis Error", f"Analysis failed:\n{error}")
        self.status_bar.showMessage("Analysis failed")
    
    def on_format_changed(self, format_name: str):
        """Handle output format change."""
        # Show/hide MA3 XML configuration button
        self.ma3_config_btn.setVisible(format_name == "ma3_xml")
        
        # If switching to MA3 XML and no config exists, load from saved config
        # Only do this for user-initiated changes, not during project loading
        if format_name == "ma3_xml" and self.ma3_config is None:
            self.ma3_config = self.config.get_ma3_xml_config()
            
        # Update config file and mark project as dirty if this is a user-initiated change
        # (Don't update during loading when signals are blocked)
        if not self.format_combo.signalsBlocked():
            self.config.set_output_format(format_name)  # Save to config file
            self.mark_project_dirty()
            
            # Trigger re-analysis if format change affects analysis
            if self.current_results:
                self._trigger_automatic_analysis()
    
    def configure_ma3_xml(self):
        """Open MA3 XML configuration dialog."""
        dialog = MA3XMLDialog(self, self.config)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.ma3_config = dialog.get_config()
            self.mark_project_dirty()  # Mark project as dirty when MA3 config changes
            
            # Trigger re-analysis if MA3 config changes affect analysis
            if self.current_results and self.format_combo.currentText() == "ma3_xml":
                self._trigger_automatic_analysis()
            QMessageBox.information(
                self,
                "Configuration Saved",
                "MA3 XML settings have been configured and saved."
            )
    
    def mark_project_dirty(self):
        """Mark the project as having unsaved changes."""
        self.project_dirty = True
        self.update_window_title()
        self.update_ui_state()
    
    def update_window_title(self):
        """Update the window title to reflect current project state."""
        base_title = "AttributeAddresser"
        
        if self.current_project_path:
            project_name = Path(self.current_project_path).stem
            if self.project_dirty:
                base_title = f"{base_title} - {project_name} *"
            else:
                base_title = f"{base_title} - {project_name}"
        elif self.project_dirty:
            base_title = f"{base_title} *"
        
        self.setWindowTitle(base_title)
    
    def show_about(self):
        """Show the About dialog."""
        QMessageBox.about(
            self,
            "About AttributeAddresser",
            "AttributeAddresser v1.0\n\n"
            "A professional tool for analyzing MVR files and extracting fixture addresses.\n\n"
            "Features:\n"
            "• MVR file analysis\n"
            "• GDTF profile matching\n"
            "• DMX address calculation\n"
            "• Multiple export formats\n"
            "• MA3 XML remote generation\n\n"
            "© 2025 AttributeAddresser"
        )
    
    def new_project(self):
        """Create a new project."""
        if self.project_dirty:
            reply = QMessageBox.question(
                self, "Unsaved Changes",
                "You have unsaved changes. Do you want to save the current project first?",
                QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel
            )
            
            if reply == QMessageBox.StandardButton.Save:
                if not self.save_project():
                    return  # Save was cancelled
            elif reply == QMessageBox.StandardButton.Cancel:
                return
        
        # Reset all state
        self.current_project_path = None
        self.project_dirty = False
        self.fixture_type_attributes = {}
        self.ma3_config = None
        self.current_results = None
        
        # Reset controller state
        self.controller = MVRController()
        
        # Reset UI dropdowns and controls
        self.format_combo.blockSignals(True)
        self.format_combo.setCurrentText(self.config.get_output_format())  # Reset to default format
        self.format_combo.blockSignals(False)
        self.ma3_config_btn.setVisible(self.format_combo.currentText() == "ma3_xml")
        
        # Reset other UI elements
        self.file_label.setText("No file selected")
        self.file_label.setStyleSheet("padding: 10px; border: 1px solid #ccc; border-radius: 4px;")
        self.gdtf_status_label.setText("Load a file first")
        self.gdtf_status_label.setStyleSheet("color: gray; font-style: italic; padding: 5px;")
        self.attribute_status_label.setText("Complete steps 1-2 first")
        self.attribute_status_label.setStyleSheet("color: gray; font-style: italic; padding: 5px;")
        self._clear_results_tree()
        
        # Reset import type to MVR
        self.mvr_radio.setChecked(True)
        self.update_browse_button()
        
        self.update_ui_state()
        self.update_window_title()
        self.status_bar.showMessage("New project created")
    
    def load_project(self):
        """Load a project from file."""
        if self.project_dirty:
            reply = QMessageBox.question(
                self, "Unsaved Changes",
                "You have unsaved changes. Do you want to save the current project first?",
                QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel
            )
            
            if reply == QMessageBox.StandardButton.Save:
                if not self.save_project():
                    return  # Save was cancelled
            elif reply == QMessageBox.StandardButton.Cancel:
                return
        
        # Get project file path
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Load Project",
            "",
            "AttributeAddresser Project Files (*.aap);;All Files (*)"
        )
        
        if file_path:
            self.load_project_file(file_path)
    
    def save_project(self) -> bool:
        """Save the current project. Returns True if successful."""
        if self.current_project_path:
            return self.save_project_file(self.current_project_path)
        else:
            return self.save_project_as()
    
    def save_project_as(self) -> bool:
        """Save the project with a new name. Returns True if successful."""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Project As",
            "",
            "AttributeAddresser Project Files (*.aap);;All Files (*)"
        )
        
        if file_path:
            if not file_path.endswith('.aap'):
                file_path += '.aap'
            return self.save_project_file(file_path)
        
        return False
    
    def load_project_file(self, file_path: str):
        """Load project state from file."""
        try:
            import json
            with open(file_path, 'r') as f:
                project_data = json.load(f)
            
            # Validate project data
            if project_data.get('version') != '1.0':
                QMessageBox.warning(self, "Invalid Project", "This project file format is not supported.")
                return
            
            # Load MVR file if specified
            mvr_loaded = False
            if project_data.get('mvr_file_path'):
                mvr_path = project_data['mvr_file_path']
                if os.path.exists(mvr_path):
                    self.load_mvr_file(mvr_path)
                    mvr_loaded = True
                else:
                    reply = QMessageBox.question(
                        self, "MVR File Not Found",
                        f"The MVR file '{mvr_path}' was not found. Do you want to locate it?",
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                    )
                    
                    if reply == QMessageBox.StandardButton.Yes:
                        new_mvr_path, _ = QFileDialog.getOpenFileName(
                            self, "Locate MVR File", "", "MVR Files (*.mvr);;All Files (*)"
                        )
                        if new_mvr_path:
                            self.load_mvr_file(new_mvr_path)
                            mvr_loaded = True
            
            # Load external GDTF profiles and apply matches if MVR was loaded
            if mvr_loaded:
                # Load external GDTF profiles first
                external_gdtf_folder = project_data.get('external_gdtf_folder')
                if external_gdtf_folder:
                    self._load_external_gdtf_profiles(external_gdtf_folder)
                
                # Apply saved fixture type matches
                fixture_type_matches = project_data.get('fixture_type_matches')
                if fixture_type_matches:
                    result = self.controller.update_fixture_matches(fixture_type_matches)
                    if result["success"]:
                        self._update_gdtf_status(result["matched_fixtures"], result["total_fixtures"])
                    else:
                        self.status_bar.showMessage("Warning: Could not restore all fixture matches")
            
            # Restore other project state in correct order
            self.fixture_type_attributes = project_data.get('fixture_type_attributes', {})
            self.ma3_config = project_data.get('ma3_config')
            
            # Restore output format without triggering events during loading
            if 'output_format' in project_data:
                # Temporarily block signals to prevent format change events during loading
                self.format_combo.blockSignals(True)
                self.format_combo.setCurrentText(project_data['output_format'])
                self.format_combo.blockSignals(False)
                
                # Manually update the MA3 config button visibility after loading
                format_name = project_data['output_format']
                self.ma3_config_btn.setVisible(format_name == "ma3_xml")
            
            # Set project path and clear dirty flag
            self.current_project_path = file_path
            self.project_dirty = False
            
            # Add to recent projects
            self.add_to_recent_projects(file_path)
            
            # Update UI
            self.update_ui_state()
            self.update_window_title()
            self.status_bar.showMessage(f"Project loaded: {Path(file_path).name}")
            
        except Exception as e:
            QMessageBox.critical(self, "Load Error", f"Failed to load project:\n{str(e)}")
    
    def save_project_file(self, file_path: str) -> bool:
        """Save project state to file. Returns True if successful."""
        try:
            import json
            
            # Collect essential project data
            project_data = {
                'version': '1.0',
                'mvr_file_path': self.controller.current_file_path,
                'fixture_type_attributes': self.fixture_type_attributes,
                'fixture_type_matches': self.controller.get_current_fixture_type_matches(),
                'external_gdtf_folder': self.config.get_external_gdtf_folder(),
                'ma3_config': self.ma3_config,
                'output_format': self.format_combo.currentText()
            }
            
            # Save to file
            with open(file_path, 'w') as f:
                json.dump(project_data, f, indent=2)
            
            # Update project state
            self.current_project_path = file_path
            self.project_dirty = False
            
            # Add to recent projects
            self.add_to_recent_projects(file_path)
            
            # Update UI
            self.update_ui_state()
            self.update_window_title()
            self.status_bar.showMessage(f"Project saved: {Path(file_path).name}")
            
            return True
            
        except Exception as e:
            QMessageBox.critical(self, "Save Error", f"Failed to save project:\n{str(e)}")
            return False
    
    def add_to_recent_projects(self, file_path: str):
        """Add project to recent projects list."""
        settings = QSettings('AttributeAddresser', 'RecentProjects')
        recent_files = settings.value('recent_files', [])
        
        # Remove if already exists
        if file_path in recent_files:
            recent_files.remove(file_path)
        
        # Add to front
        recent_files.insert(0, file_path)
        
        # Keep only last 10
        recent_files = recent_files[:10]
        
        # Save
        settings.setValue('recent_files', recent_files)
        
        # Update menu
        self.update_recent_projects_menu()
    
    def update_recent_projects_menu(self):
        """Update the recent projects menu."""
        self.recent_menu.clear()
        
        settings = QSettings('AttributeAddresser', 'RecentProjects')
        recent_files = settings.value('recent_files', [])
        
        if recent_files:
            for file_path in recent_files:
                if os.path.exists(file_path):
                    action = QAction(Path(file_path).name, self)
                    action.setToolTip(file_path)
                    action.triggered.connect(lambda checked, path=file_path: self.load_project_file(path))
                    self.recent_menu.addAction(action)
        else:
            no_recent_action = QAction('No recent projects', self)
            no_recent_action.setEnabled(False)
            self.recent_menu.addAction(no_recent_action)
    
    def _get_timestamp(self) -> str:
        """Get current timestamp."""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    def _update_gdtf_status(self, matched_count: int, total_count: int):
        """Update GDTF status label and button state."""
        if matched_count == total_count:
            self.gdtf_status_label.setText(f"All {total_count} fixtures successfully matched!")
            self.gdtf_status_label.setStyleSheet("color: green; font-weight: bold; padding: 5px;")
            self.match_gdtf_btn.setText("Edit GDTF Matches")
            self.match_gdtf_btn.setEnabled(True)  # Keep enabled for editing
        else:
            unmatched = total_count - matched_count
            self.gdtf_status_label.setText(f"{matched_count}/{total_count} fixtures matched. {unmatched} need manual matching.")
            self.gdtf_status_label.setStyleSheet("color: orange; font-weight: bold; padding: 5px;")
            self.match_gdtf_btn.setText("Match GDTF Profiles")
            self.match_gdtf_btn.setEnabled(True)
    
    def _load_external_gdtf_profiles(self, gdtf_folder: str) -> bool:
        """Load external GDTF profiles from folder. Returns True if successful."""
        if not gdtf_folder or not os.path.exists(gdtf_folder):
            return False
        
        self.config.set_external_gdtf_folder(gdtf_folder)
        result = self.controller.load_external_gdtf_profiles(gdtf_folder)
        
        if result["success"]:
            self.status_bar.showMessage(f"Loaded {result['profiles_loaded']} external GDTF profiles")
            return True
        return False
    
    def export_results(self):
        """Export analysis results to file."""
        if not self.current_results:
            QMessageBox.warning(self, "No Results", "No analysis results to export.")
            return
        
        try:
            # Get last used directory
            last_dir = self.config.get_last_export_directory()
            start_dir = last_dir if last_dir and os.path.exists(last_dir) else ""
            
            # Determine file extension
            output_format = self.format_combo.currentText()
            extensions = {
                "text": "txt",
                "csv": "csv", 
                "json": "json",
                "ma3_xml": "xml"
            }
            ext = extensions.get(output_format, "txt")
            
            # Get save path
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Export Analysis Results",
                f"{start_dir}/mvr_analysis.{ext}",
                f"{output_format.upper()} Files (*.{ext});;All Files (*)"
            )
            
            if file_path:
                # Save the directory for next time
                self.config.set_last_export_directory(str(Path(file_path).parent))
                
                # Export the results
                ma3_config = None
                if output_format == "ma3_xml":
                    ma3_config = self.ma3_config
                
                result = self.controller.export_results(self.current_results, output_format, file_path, ma3_config)
                
                if result["success"]:
                    QMessageBox.information(
                        self, 
                        "Export Successful", 
                        f"Results exported to:\n{file_path}"
                    )
                    self.status_bar.showMessage(f"Results exported to {Path(file_path).name}")
                else:
                    QMessageBox.critical(self, "Export Error", f"Failed to export results:\n{result['error']}")
                    
        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Error exporting results:\n{str(e)}")
    
    def update_ui_state(self):
        """Update UI state based on current application state."""
        status = self.controller.get_current_status()
        
        # Update GDTF buttons
        file_loaded = status["file_loaded"]
        has_fixtures = status["matched_fixtures"] > 0 or status["unmatched_fixtures"] > 0
        
        # Manual matching button - enabled when fixtures loaded
        self.match_gdtf_btn.setEnabled(has_fixtures)
        
        # Update select attributes button
        can_select_attributes = (
            status["file_loaded"] and 
            status["matched_fixtures"] > 0
        )
        
        self.select_attrs_btn.setEnabled(can_select_attributes)
        
        # Update attribute selection status label
        if can_select_attributes:
            if self.fixture_type_attributes:
                total_attrs = sum(len(attrs) for attrs in self.fixture_type_attributes.values())
                if total_attrs > 0:
                    self.attribute_status_label.setText(f"Attributes saved ({total_attrs} total) - you can modify anytime")
                    self.attribute_status_label.setStyleSheet("color: green; font-weight: bold; padding: 5px;")
                else:
                    self.attribute_status_label.setText("No attributes selected - click to modify")
                    self.attribute_status_label.setStyleSheet("color: orange; font-weight: bold; padding: 5px;")
            else:
                self.attribute_status_label.setText("Ready for attribute selection!")
                self.attribute_status_label.setStyleSheet("color: blue; font-weight: bold; padding: 5px;")
        else:
            self.attribute_status_label.setText("Complete steps 1-2 first")
            self.attribute_status_label.setStyleSheet("color: gray; font-style: italic; padding: 5px;")
        
        # Update results status for automatic analysis
        self._update_results_status()
        
        # Update save action
        self.save_action.setEnabled(self.project_dirty)


def main():
    """Main entry point for the application."""
    app = QApplication(sys.argv)
    
    # Set application properties for proper branding
    app.setApplicationName("AttributeAddresser")
    app.setApplicationDisplayName("AttributeAddresser")
    app.setOrganizationName("AttributeAddresser")
    app.setOrganizationDomain("attributeaddresser.com")
    app.setApplicationVersion("1.0")
    
    # Create and show the main window
    window = MVRApp()
    window.show()
    
    # Run the application
    sys.exit(app.exec())


if __name__ == "__main__":
    main() 