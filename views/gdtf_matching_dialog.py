"""
GDTF Matching Dialog - Clean UI for matching fixtures to GDTF profiles.
Uses controller architecture for business logic.
"""

import os
from typing import Dict, List, Optional
from pathlib import Path

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, 
    QPushButton, QComboBox, QGroupBox, QScrollArea, QWidget,
    QFileDialog, QMessageBox, QFrame
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from controllers import MVRController


class GDTFMatchingDialog(QDialog):
    """
    Clean dialog for matching fixtures to GDTF profiles.
    Uses controller for all business logic.
    """
    
    def __init__(self, parent, controller: MVRController, config=None):
        super().__init__(parent)
        self.controller = controller
        self.config = config
        self.fixture_type_controls = {}
        self.setup_ui()
        self.load_unmatched_fixtures()
    
    def setup_ui(self):
        """Create the dialog interface."""
        self.setWindowTitle("GDTF Profile Matching")
        self.setGeometry(200, 200, 1000, 700)
        
        layout = QVBoxLayout(self)
        
        # Title
        title = QLabel("Match Fixture Types to GDTF Profiles")
        title.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        layout.addWidget(title)
        
        # External GDTF folder section
        external_group = QGroupBox("External GDTF Profiles (Optional)")
        external_layout = QGridLayout(external_group)
        
        external_layout.addWidget(QLabel("GDTF Folder:"), 0, 0)
        
        self.folder_label = QLabel("No external folder selected")
        self.folder_label.setStyleSheet("color: gray; font-style: italic;")
        external_layout.addWidget(self.folder_label, 0, 1)
        
        browse_folder_btn = QPushButton("Browse External GDTF Folder...")
        browse_folder_btn.clicked.connect(self.browse_gdtf_folder)
        external_layout.addWidget(browse_folder_btn, 0, 2)
        
        self.profiles_info = QLabel("Using internal GDTF profiles from MVR file")
        self.profiles_info.setStyleSheet("color: blue;")
        external_layout.addWidget(self.profiles_info, 1, 1, 1, 2)
        
        layout.addWidget(external_group)
        
        # Instructions
        instructions = QLabel(
            "Select the appropriate GDTF profile and mode for each fixture type. "
            "All fixtures of the same type will use the same profile and mode."
        )
        instructions.setWordWrap(True)
        instructions.setStyleSheet("color: #666; margin: 10px 0;")
        layout.addWidget(instructions)
        
        # Scrollable area for fixture matching
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        
        self.fixture_widget = QWidget()
        self.fixture_layout = QVBoxLayout(self.fixture_widget)
        
        scroll.setWidget(self.fixture_widget)
        layout.addWidget(scroll)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        ok_btn = QPushButton("Apply Changes")
        ok_btn.setDefault(True)
        ok_btn.clicked.connect(self.accept)
        button_layout.addWidget(ok_btn)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
    
    def load_unmatched_fixtures(self):
        """Load unmatched fixtures from controller and create UI."""
        # Clear existing controls
        for control in self.fixture_type_controls.values():
            control['group'].setParent(None)
        self.fixture_type_controls.clear()
        
        # Get current status
        status = self.controller.get_current_status()
        if not status["file_loaded"]:
            return
        
        # Get fixture information grouped by type
        fixture_info = self._get_fixture_type_info()
        
        if not fixture_info:
            no_fixtures_label = QLabel("No fixtures need manual matching.")
            no_fixtures_label.setStyleSheet("color: green; font-weight: bold; padding: 20px;")
            self.fixture_layout.addWidget(no_fixtures_label)
            return
        
        # Create matching controls for each fixture type
        for fixture_type, info in fixture_info.items():
            group_widget = self.create_fixture_type_control(fixture_type, info)
            self.fixture_layout.addWidget(group_widget)
    
    def _get_fixture_type_info(self) -> Dict[str, Dict]:
        """Get fixture type information from controller."""
        return self.controller.get_unmatched_fixture_types()
    
    def create_fixture_type_control(self, fixture_type: str, info: Dict) -> QWidget:
        """Create UI controls for a fixture type."""
        group = QGroupBox(f"Fixture Type: {fixture_type}")
        group.setStyleSheet("QGroupBox { font-weight: bold; margin-top: 10px; }")
        layout = QGridLayout(group)
        
        # Fixture count
        count_label = QLabel(f"Fixtures: {info.get('count', 0)}")
        count_label.setStyleSheet("color: #666;")
        layout.addWidget(count_label, 0, 0)
        
        # Sample fixture names
        sample_names = info.get('sample_names', [])
        if sample_names:
            names_text = ', '.join(sample_names[:3])
            if len(sample_names) > 3:
                names_text += f" ... and {len(sample_names) - 3} more"
            sample_label = QLabel(f"Examples: {names_text}")
            sample_label.setStyleSheet("color: #666;")
            layout.addWidget(sample_label, 0, 1)
        
        # Profile selection
        layout.addWidget(QLabel("GDTF Profile:"), 1, 0)
        profile_combo = QComboBox()
        profile_combo.addItem("-- Select Profile --", "")
        
        # Add available profiles
        available_profiles = self.controller.get_available_profiles()
        for profile_name in available_profiles:
            profile_combo.addItem(profile_name, profile_name)
        
        profile_combo.currentTextChanged.connect(
            lambda text, ft=fixture_type: self.on_profile_changed(ft, text)
        )
        layout.addWidget(profile_combo, 1, 1)
        
        # Mode selection
        layout.addWidget(QLabel("GDTF Mode:"), 2, 0)
        mode_combo = QComboBox()
        mode_combo.addItem("-- Select Mode --", "")
        layout.addWidget(mode_combo, 2, 1)
        
        # Store references
        self.fixture_type_controls[fixture_type] = {
            'group': group,
            'profile_combo': profile_combo,
            'mode_combo': mode_combo,
            'info': info
        }
        
        return group
    
    def browse_gdtf_folder(self):
        """Browse for external GDTF folder."""
        # Get last used directory
        start_dir = ""
        if self.config:
            last_dir = self.config.get_last_gdtf_directory()
            start_dir = last_dir if last_dir and os.path.exists(last_dir) else ""
        
        folder_path = QFileDialog.getExistingDirectory(
            self,
            "Select GDTF Folder",
            start_dir,
            QFileDialog.Option.ShowDirsOnly
        )
        
        if folder_path:
            # Save the directory for next time
            if self.config:
                self.config.set_last_gdtf_directory(folder_path)
            self.load_external_gdtf_profiles(folder_path)
    
    def load_external_gdtf_profiles(self, folder_path: str):
        """Load external GDTF profiles."""
        try:
            result = self.controller.load_external_gdtf_profiles(folder_path)
            
            if result["success"]:
                profiles_loaded = result["profiles_loaded"]
                
                # Update UI
                self.folder_label.setText(Path(folder_path).name)
                self.folder_label.setStyleSheet("color: black; font-weight: bold;")
                
                self.profiles_info.setText(
                    f"Loaded {profiles_loaded} external GDTF profiles"
                )
                self.profiles_info.setStyleSheet("color: green;")
                
                # Update all profile dropdowns
                self.update_profile_dropdowns()
                
            else:
                QMessageBox.critical(
                    self,
                    "Error",
                    f"Failed to load GDTF profiles:\n{result['error']}"
                )
                
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Error loading external GDTF profiles:\n{str(e)}"
            )
    
    def update_profile_dropdowns(self):
        """Update all profile dropdown menus."""
        available_profiles = self.controller.get_available_profiles()
        
        for controls in self.fixture_type_controls.values():
            profile_combo = controls['profile_combo']
            current_selection = profile_combo.currentData()
            
            # Clear and repopulate
            profile_combo.clear()
            profile_combo.addItem("-- Select Profile --", "")
            
            for profile_name in available_profiles:
                profile_combo.addItem(profile_name, profile_name)
            
            # Restore selection if it still exists
            if current_selection:
                index = profile_combo.findData(current_selection)
                if index >= 0:
                    profile_combo.setCurrentIndex(index)
    
    def on_profile_changed(self, fixture_type: str, profile_name: str):
        """Handle profile selection change."""
        if fixture_type not in self.fixture_type_controls:
            return
        
        controls = self.fixture_type_controls[fixture_type]
        mode_combo = controls['mode_combo']
        
        # Clear modes
        mode_combo.clear()
        mode_combo.addItem("-- Select Mode --", "")
        
        # Add modes for selected profile
        if profile_name:
            modes = self.controller.get_profile_modes(profile_name)
            for mode_name in modes:
                mode_combo.addItem(mode_name, mode_name)
    
    def get_fixture_type_matches(self) -> Dict[str, Dict[str, str]]:
        """Get the fixture type matches from the dialog."""
        matches = {}
        
        for fixture_type, controls in self.fixture_type_controls.items():
            profile_combo = controls['profile_combo']
            mode_combo = controls['mode_combo']
            
            profile_name = profile_combo.currentData()
            mode_name = mode_combo.currentData()
            
            if profile_name and mode_name:
                matches[fixture_type] = {
                    'profile': profile_name,
                    'mode': mode_name
                }
        
        return matches 