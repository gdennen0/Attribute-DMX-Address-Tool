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
    QFrame, QGridLayout, QDialog, QMenuBar, QMenu
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QSettings
from PyQt6.QtGui import QFont, QAction

# Import our clean architecture
from controllers import MVRController
from config import Config
from views.gdtf_matching_dialog import GDTFMatchingDialog
from views.fixture_attribute_dialog import FixtureAttributeDialog
from views.ma3_xml_dialog import MA3XMLDialog


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
        
        # Main layout
        main_layout = QHBoxLayout(central_widget)
        
        # Left panel (controls)
        left_panel = self.create_left_panel()
        main_layout.addWidget(left_panel, 1)
        
        # Right panel (results)
        right_panel = self.create_right_panel()
        main_layout.addWidget(right_panel, 2)
        
        # Status bar
        self.status_bar = self.statusBar()
        self.status_bar.showMessage("Ready")
        
        # Set minimum sizes
        left_panel.setMinimumWidth(350)
        right_panel.setMinimumWidth(500)
        
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
    
    def create_left_panel(self) -> QWidget:
        """Create the left control panel."""
        panel = QFrame()
        panel.setFrameStyle(QFrame.Shape.StyledPanel)
        layout = QVBoxLayout(panel)
        
        # File selection group
        file_group = QGroupBox("1. File Selection")
        file_layout = QVBoxLayout(file_group)
        
        self.file_label = QLabel("No file selected")
        self.file_label.setWordWrap(True)
        self.file_label.setStyleSheet("padding: 10px; border: 1px solid #ccc; border-radius: 4px;")
        file_layout.addWidget(self.file_label)
        
        browse_btn = QPushButton("Browse MVR File...")
        browse_btn.clicked.connect(self.browse_file)
        file_layout.addWidget(browse_btn)
        
        layout.addWidget(file_group)
        
        # GDTF Matching group
        gdtf_group = QGroupBox("2. GDTF Profile Matching")
        gdtf_layout = QVBoxLayout(gdtf_group)
        
        self.gdtf_status_label = QLabel("Load an MVR file first")
        self.gdtf_status_label.setWordWrap(True)
        self.gdtf_status_label.setStyleSheet("color: gray; font-style: italic; padding: 5px;")
        gdtf_layout.addWidget(self.gdtf_status_label)
        
        self.match_gdtf_btn = QPushButton("Match GDTF Profiles")
        self.match_gdtf_btn.clicked.connect(self.match_gdtf_profiles)
        self.match_gdtf_btn.setEnabled(False)
        gdtf_layout.addWidget(self.match_gdtf_btn)
        
        layout.addWidget(gdtf_group)
        
        # Analysis group
        analysis_group = QGroupBox("3. Analysis")
        analysis_layout = QVBoxLayout(analysis_group)
        
        self.analysis_status_label = QLabel("Complete steps 1-2 first")
        self.analysis_status_label.setWordWrap(True)
        self.analysis_status_label.setStyleSheet("color: gray; font-style: italic; padding: 5px;")
        analysis_layout.addWidget(self.analysis_status_label)
        
        # Output format selection
        format_layout = QHBoxLayout()
        format_layout.addWidget(QLabel("Output Format:"))
        self.format_combo = QComboBox()
        self.format_combo.addItems(["text", "csv", "json", "ma3_xml"])
        self.format_combo.setCurrentText(self.config.get_output_format())
        self.format_combo.currentTextChanged.connect(self.on_format_changed)
        format_layout.addWidget(self.format_combo)
        
        # MA3 XML configuration button (initially hidden)
        self.ma3_config_btn = QPushButton("MA3 XML Settings")
        self.ma3_config_btn.clicked.connect(self.configure_ma3_xml)
        self.ma3_config_btn.setVisible(False)
        format_layout.addWidget(self.ma3_config_btn)
        
        analysis_layout.addLayout(format_layout)
        
        # Buttons layout
        buttons_layout = QHBoxLayout()
        
        # Select Attributes button
        self.select_attrs_btn = QPushButton("Select Attributes")
        self.select_attrs_btn.clicked.connect(self.select_attributes)
        self.select_attrs_btn.setEnabled(False)
        buttons_layout.addWidget(self.select_attrs_btn)
        
        # Analyze button
        self.analyze_btn = QPushButton("Analyze")
        self.analyze_btn.clicked.connect(self.analyze_fixtures)
        self.analyze_btn.setEnabled(False)
        buttons_layout.addWidget(self.analyze_btn)
        
        analysis_layout.addLayout(buttons_layout)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        analysis_layout.addWidget(self.progress_bar)
        
        layout.addWidget(analysis_group)
        
        # Export group
        export_group = QGroupBox("4. Export")
        export_layout = QVBoxLayout(export_group)
        
        self.export_btn = QPushButton("Export Results")
        self.export_btn.clicked.connect(self.export_results)
        self.export_btn.setEnabled(False)
        export_layout.addWidget(self.export_btn)
        
        layout.addWidget(export_group)
        
        # Stretch to push everything to the top
        layout.addStretch()
        
        return panel
    
    def create_right_panel(self) -> QWidget:
        """Create the right results panel."""
        panel = QFrame()
        panel.setFrameStyle(QFrame.Shape.StyledPanel)
        layout = QVBoxLayout(panel)
        
        # Results title
        title = QLabel("Analysis Results")
        title.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        layout.addWidget(title)
        
        # Results text area
        self.results_text = QTextEdit()
        self.results_text.setReadOnly(True)
        self.results_text.setFont(QFont("Courier", 10))
        self.results_text.setPlainText("No analysis results yet.\n\nPlease:\n1. Load an MVR file\n2. Match GDTF profiles\n3. Select attributes per fixture type\n4. Run analysis")
        layout.addWidget(self.results_text)
        
        return panel
    
    def browse_file(self):
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
                
                self.status_bar.showMessage(f"Loaded {result['total_fixtures']} fixtures from {Path(file_path).name}")
                
            else:
                QMessageBox.critical(self, "Error", f"Failed to load MVR file:\n{result['error']}")
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error loading file:\n{str(e)}")
    
    def match_gdtf_profiles(self):
        """Open GDTF matching dialog."""
        try:
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
                    
                    self.status_bar.showMessage(f"Updated fixture matches: {matched_count}/{total_count} matched")
                else:
                    QMessageBox.critical(self, "Error", f"Failed to update matches:\n{result['error']}")
                    
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error in GDTF matching:\n{str(e)}")
    
    def select_attributes(self):
        """Open attribute selection dialog."""
        try:
            # Open the fixture attribute dialog with existing selections
            dialog = FixtureAttributeDialog(self, self.controller, self.config, self.fixture_type_attributes)
            
            if dialog.exec() == QDialog.DialogCode.Accepted:
                # Get selected attributes per fixture type
                self.fixture_type_attributes = dialog.get_fixture_type_attributes()
                
                # Validate that we have some attributes selected
                total_selected = sum(len(attrs) for attrs in self.fixture_type_attributes.values())
                if total_selected == 0:
                    QMessageBox.warning(self, "No Attributes", "No attributes were selected for analysis.")
                    self.analyze_btn.setEnabled(False)
                    return
                
                # Store the attributes in config (for future reference)
                self.config.set_fixture_type_attributes(self.fixture_type_attributes)
                
                # Enable analyze button and mark project as dirty
                self.analyze_btn.setEnabled(True)
                self.mark_project_dirty()
                
                # Update status
                self.status_bar.showMessage(f"Attributes selected for {len(self.fixture_type_attributes)} fixture types")
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error in attribute selection:\n{str(e)}")
    
    def analyze_fixtures(self):
        """Start fixture analysis with per-fixture-type attributes."""
        if not self.fixture_type_attributes:
            QMessageBox.warning(self, "No Attributes", "Please select attributes first.")
            return
        
        # Get output format
        output_format = self.format_combo.currentText()
        
        # Handle MA3 XML configuration
        ma3_config = None
        if output_format == "ma3_xml":
            # Use stored config if available, otherwise prompt for config
            if self.ma3_config is None:
                QMessageBox.information(
                    self,
                    "MA3 XML Configuration Required",
                    "Please configure MA3 XML settings first using the 'MA3 XML Settings' button."
                )
                return
            ma3_config = self.ma3_config
        
        # Note: Output format is already saved to config via on_format_changed
        
        # Disable controls during analysis
        self.analyze_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Indeterminate progress
        
        # Start analysis in background thread
        self.worker = AnalysisWorker(self.controller, self.fixture_type_attributes, output_format, ma3_config)
        self.worker.progress_update.connect(self.update_progress)
        self.worker.analysis_complete.connect(self.analysis_complete)
        self.worker.analysis_error.connect(self.analysis_error)
        self.worker.start()
    
    def update_progress(self, message: str):
        """Update progress message."""
        self.status_bar.showMessage(message)
    
    def analysis_complete(self, result: dict):
        """Handle successful analysis completion."""
        self.worker = None
        self.progress_bar.setVisible(False)
        self.analyze_btn.setEnabled(True)
        
        # Store results
        self.current_results = result
        
        # Update UI
        self.results_text.setPlainText(result["export_data"])
        self.export_btn.setEnabled(True)
        
        # Update UI state
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
        self.analyze_btn.setEnabled(True)
        
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
    
    def configure_ma3_xml(self):
        """Open MA3 XML configuration dialog."""
        dialog = MA3XMLDialog(self, self.config)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.ma3_config = dialog.get_config()
            self.mark_project_dirty()  # Mark project as dirty when MA3 config changes
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
        self.gdtf_status_label.setText("Load an MVR file first")
        self.gdtf_status_label.setStyleSheet("color: gray; font-style: italic; padding: 5px;")
        self.results_text.setPlainText("No analysis results yet.\n\nPlease:\n1. Load an MVR file\n2. Match GDTF profiles\n3. Select attributes per fixture type\n4. Run analysis")
        
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
        
        # Update select attributes button
        can_select_attributes = (
            status["file_loaded"] and 
            status["matched_fixtures"] > 0
        )
        
        self.select_attrs_btn.setEnabled(can_select_attributes)
        
        # Update analyze button
        can_analyze = (
            can_select_attributes and 
            len(self.fixture_type_attributes) > 0
        )
        
        self.analyze_btn.setEnabled(can_analyze)
        
        if can_select_attributes:
            if can_analyze:
                self.analysis_status_label.setText("Ready to analyze with selected attributes!")
                self.analysis_status_label.setStyleSheet("color: green; font-weight: bold; padding: 5px;")
            else:
                self.analysis_status_label.setText("Ready for attribute selection!")
                self.analysis_status_label.setStyleSheet("color: blue; font-weight: bold; padding: 5px;")
        else:
            self.analysis_status_label.setText("Complete steps 1-2 first")
            self.analysis_status_label.setStyleSheet("color: gray; font-style: italic; padding: 5px;")
        
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
    
    # Additional macOS-specific settings for menu bar
    if sys.platform == "darwin":  # macOS
        # Try to set the process name for the menu bar
        try:
            from Foundation import NSBundle
            bundle = NSBundle.mainBundle()
            if bundle:
                info = bundle.localizedInfoDictionary() or bundle.infoDictionary()
                if info:
                    info['CFBundleName'] = 'AttributeAddresser'
                    info['CFBundleDisplayName'] = 'AttributeAddresser'
        except ImportError:
            # Foundation framework not available, continue without it
            pass
        
        # Alternative approach using PyObjC if available
        try:
            import objc
            from Foundation import NSProcessInfo
            process_info = NSProcessInfo.processInfo()
            process_info.setProcessName_("AttributeAddresser")
        except ImportError:
            # PyObjC not available, continue without it
            pass
        
        # Set the application menu title
        app.setProperty("LSUIElement", False)
    
    # Create and show the main window
    window = MVRApp()
    window.show()
    
    # Run the application
    sys.exit(app.exec())


if __name__ == "__main__":
    main() 