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
    QFrame, QGridLayout, QDialog
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont

# Import our clean architecture
from controllers import MVRController
from config import Config
from views.gdtf_matching_dialog import GDTFMatchingDialog
from views.fixture_attribute_dialog import FixtureAttributeDialog


class AnalysisWorker(QThread):
    """Background worker for running analysis without freezing the GUI."""
    
    progress_update = pyqtSignal(str)
    analysis_complete = pyqtSignal(dict)
    analysis_error = pyqtSignal(str)
    
    def __init__(self, controller: MVRController, fixture_type_attributes: Dict[str, List[str]], output_format: str):
        super().__init__()
        self.controller = controller
        self.fixture_type_attributes = fixture_type_attributes
        self.output_format = output_format
    
    def run(self):
        """Run the analysis in background thread."""
        try:
            self.progress_update.emit("Starting analysis...")
            result = self.controller.analyze_fixtures_by_type(self.fixture_type_attributes, self.output_format)
            
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
        self.setup_ui()
        self.update_ui_state()
    
    def setup_ui(self):
        """Create the main user interface."""
        self.setWindowTitle("MVR File Analyzer v2.0")
        self.setGeometry(100, 100, 1200, 800)
        
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
        self.format_combo.addItems(["text", "csv", "json"])
        self.format_combo.setCurrentText(self.config.get_output_format())
        format_layout.addWidget(self.format_combo)
        analysis_layout.addLayout(format_layout)
        
        # Analyze button
        self.analyze_btn = QPushButton("Select Attributes & Analyze")
        self.analyze_btn.clicked.connect(self.select_attributes_and_analyze)
        self.analyze_btn.setEnabled(False)
        analysis_layout.addWidget(self.analyze_btn)
        
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
                self.file_label.setText(f"File: {Path(file_path).name}")
                self.file_label.setStyleSheet("padding: 10px; border: 1px solid #4CAF50; border-radius: 4px; background-color: #E8F5E8;")
                
                # Update GDTF status
                total_fixtures = result["total_fixtures"]
                matched_fixtures = result["matched_fixtures"]
                unmatched_fixtures = result["unmatched_fixtures"]
                
                if unmatched_fixtures > 0:
                    self.gdtf_status_label.setText(
                        f"Loaded {total_fixtures} fixtures. {matched_fixtures} matched, {unmatched_fixtures} need manual matching."
                    )
                    self.gdtf_status_label.setStyleSheet("color: orange; font-weight: bold; padding: 5px;")
                    self.match_gdtf_btn.setEnabled(True)
                else:
                    self.gdtf_status_label.setText(
                        f"All {total_fixtures} fixtures successfully matched to GDTF profiles!"
                    )
                    self.gdtf_status_label.setStyleSheet("color: green; font-weight: bold; padding: 5px;")
                    self.match_gdtf_btn.setEnabled(False)
                
                # Update UI state
                self.update_ui_state()
                
                self.status_bar.showMessage(f"Loaded {total_fixtures} fixtures from {Path(file_path).name}")
                
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
                    
                    if matched_count == total_count:
                        self.gdtf_status_label.setText(
                            f"All {total_count} fixtures successfully matched!"
                        )
                        self.gdtf_status_label.setStyleSheet("color: green; font-weight: bold; padding: 5px;")
                        self.match_gdtf_btn.setEnabled(False)
                    else:
                        unmatched = total_count - matched_count
                        self.gdtf_status_label.setText(
                            f"{matched_count}/{total_count} fixtures matched. {unmatched} still need matching."
                        )
                        self.gdtf_status_label.setStyleSheet("color: orange; font-weight: bold; padding: 5px;")
                    
                    # Update UI state
                    self.update_ui_state()
                    
                    self.status_bar.showMessage(f"Updated fixture matches: {matched_count}/{total_count} matched")
                else:
                    QMessageBox.critical(self, "Error", f"Failed to update matches:\n{result['error']}")
                    
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error in GDTF matching:\n{str(e)}")
    
    def select_attributes_and_analyze(self):
        """Open attribute selection dialog and then run analysis."""
        try:
            # Open the fixture attribute dialog
            dialog = FixtureAttributeDialog(self, self.controller, self.config)
            
            if dialog.exec() == QDialog.DialogCode.Accepted:
                # Get selected attributes per fixture type
                self.fixture_type_attributes = dialog.get_fixture_type_attributes()
                
                # Validate that we have some attributes selected
                total_selected = sum(len(attrs) for attrs in self.fixture_type_attributes.values())
                if total_selected == 0:
                    QMessageBox.warning(self, "No Attributes", "No attributes were selected for analysis.")
                    return
                
                # Store the attributes in config (for future reference)
                self.config.set_fixture_type_attributes(self.fixture_type_attributes)
                
                # Run the analysis
                self.analyze_fixtures()
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error in attribute selection:\n{str(e)}")
    
    def analyze_fixtures(self):
        """Start fixture analysis with per-fixture-type attributes."""
        if not self.fixture_type_attributes:
            QMessageBox.warning(self, "No Attributes", "Please select attributes first.")
            return
        
        # Get output format
        output_format = self.format_combo.currentText()
        
        # Update config
        self.config.set_output_format(output_format)
        
        # Disable controls during analysis
        self.analyze_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Indeterminate progress
        
        # Start analysis in background thread
        self.worker = AnalysisWorker(self.controller, self.fixture_type_attributes, output_format)
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
                "json": "json"
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
                result = self.controller.export_results(self.current_results, output_format, file_path)
                
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
        
        # Update analysis button
        can_analyze = (
            status["file_loaded"] and 
            status["matched_fixtures"] > 0
        )
        
        self.analyze_btn.setEnabled(can_analyze)
        
        if can_analyze:
            self.analysis_status_label.setText("Ready for attribute selection and analysis!")
            self.analysis_status_label.setStyleSheet("color: green; font-weight: bold; padding: 5px;")
        else:
            self.analysis_status_label.setText("Complete steps 1-2 first")
            self.analysis_status_label.setStyleSheet("color: gray; font-style: italic; padding: 5px;")


def main():
    """Main entry point for the application."""
    app = QApplication(sys.argv)
    
    # Create and show the main window
    window = MVRApp()
    window.show()
    
    # Run the application
    sys.exit(app.exec())


if __name__ == "__main__":
    main() 