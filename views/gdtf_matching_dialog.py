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
from PyQt6.QtGui import QFont, QColor

from controllers.main_controller import MVRController



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
        
        # Load saved external GDTF folder if available
        if self.config:
            external_folder = self.config.get_external_gdtf_folder()
            if external_folder and os.path.exists(external_folder):
                self.load_external_gdtf_profiles(external_folder)
    
    def setup_ui(self):
        """Create the dialog interface."""
        self.setWindowTitle("GDTF Profile Matching & Editing")
        self.setGeometry(200, 200, 1000, 700)
        
        layout = QVBoxLayout(self)
        
        # Title
        title = QLabel("Match & Edit Fixture Types to GDTF Profiles")
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
            "Select or edit the GDTF profile and mode for each fixture type. "
            "All fixtures of the same type will use the same profile and mode. "
            "✓ = Fully matched, ⚠ = Partially matched, ✗ = Not matched"
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
        """Load all fixtures from controller and create UI for matching/editing."""
        # Clear existing controls
        for control in self.fixture_type_controls.values():
            control['group'].setParent(None)
        self.fixture_type_controls.clear()
        
        # Clear any existing guidance widgets
        for i in reversed(range(self.fixture_layout.count())):
            widget = self.fixture_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)
        
        # Get current status
        status = self.controller.get_current_status()
        if not status["file_loaded"]:
            return
        
        # Get fixture information grouped by type (all fixtures, not just unmatched)
        fixture_info = self._get_all_fixture_type_info()
        
        if not fixture_info:
            no_fixtures_label = QLabel("No fixtures loaded.")
            no_fixtures_label.setStyleSheet("color: red; font-weight: bold; padding: 20px;")
            self.fixture_layout.addWidget(no_fixtures_label)
            return
        
        # Check if we have any GDTF profiles available
        profiles_by_source = self.controller.get_profiles_by_source()
        has_profiles = bool(profiles_by_source.get('mvr', []) or profiles_by_source.get('external', []))
        
        if not has_profiles:
            # Show guidance for CSV imports or when no profiles are available
            self._show_no_profiles_guidance()
        
        # Create matching controls for each fixture type
        for fixture_type, info in fixture_info.items():
            group_widget = self.create_fixture_type_control(fixture_type, info)
            self.fixture_layout.addWidget(group_widget)
    
    def _get_fixture_type_info(self) -> Dict[str, Dict]:
        """Get fixture type information from controller."""
        return self.controller.get_unmatched_fixture_types()
    
    def _get_all_fixture_type_info(self) -> Dict[str, Dict]:
        """Get all fixture type information from controller (both matched and unmatched)."""
        # Get all fixtures from controller
        all_fixtures = self.controller.matched_fixtures
        
        if not all_fixtures:
            return {}
        
        # Group by fixture type
        fixture_types = {}
        for fixture in all_fixtures:
            fixture_type = fixture.gdtf_spec or "Unknown"
            # Remove .gdtf extension for consistent naming
            fixture_type_clean = fixture_type.replace('.gdtf', '') if fixture_type.endswith('.gdtf') else fixture_type
            
            if fixture_type_clean not in fixture_types:
                fixture_types[fixture_type_clean] = {
                    'count': 0,
                    'sample_names': [],
                    'fixtures': [],
                    'matched_count': 0,
                    'current_match': None  # Store current match info
                }
            
            fixture_types[fixture_type_clean]['count'] += 1
            fixture_types[fixture_type_clean]['fixtures'].append(fixture)
            
            # Track matched fixtures and get current match info
            if fixture.is_matched():
                fixture_types[fixture_type_clean]['matched_count'] += 1
                if fixture_types[fixture_type_clean]['current_match'] is None:
                    fixture_types[fixture_type_clean]['current_match'] = {
                        'profile': fixture.gdtf_profile.name if fixture.gdtf_profile else None,
                        'mode': fixture.gdtf_mode
                    }
            
            # Add sample names (up to 5)
            if len(fixture_types[fixture_type_clean]['sample_names']) < 5:
                fixture_types[fixture_type_clean]['sample_names'].append(fixture.name)
        
        return fixture_types
    
    def _populate_profile_combo(self, profile_combo: QComboBox, fixture_type: str = None):
        """Populate a profile combo box with sections for MVR and external profiles."""
        profiles_by_source = self.controller.get_profiles_by_source()
        
        # Add MVR profiles section
        mvr_profiles = profiles_by_source.get('mvr', [])
        if mvr_profiles:
            # Add section divider
            divider_index = profile_combo.count()
            profile_combo.addItem("── MVR GDTF PROFILES ──", "")
            # Style the divider item and make it unselectable
            item = profile_combo.model().item(divider_index)
            item.setEnabled(False)
            # Make the text bold and different color
            font = item.font()
            font.setBold(True)
            item.setFont(font)
            item.setForeground(QColor(100, 100, 100))  # Gray color
            
            # Add MVR profiles with indentation
            for profile_name in mvr_profiles:
                profile_combo.addItem(f"  {profile_name}", profile_name)
        
        # Add External profiles section
        external_profiles = profiles_by_source.get('external', [])
        if external_profiles:
            # Add section divider
            divider_index = profile_combo.count()
            profile_combo.addItem("── EXTERNAL GDTF PROFILES ──", "")
            # Style the divider item and make it unselectable
            item = profile_combo.model().item(divider_index)
            item.setEnabled(False)
            # Make the text bold and different color
            font = item.font()
            font.setBold(True)
            item.setFont(font)
            item.setForeground(QColor(100, 100, 100))  # Gray color
            
            # Add external profiles with indentation
            for profile_name in external_profiles:
                profile_combo.addItem(f"  {profile_name}", profile_name)
    
    def create_fixture_type_control(self, fixture_type: str, info: Dict) -> QWidget:
        """Create UI controls for a fixture type."""
        # Determine match status
        matched_count = info.get('matched_count', 0)
        total_count = info.get('count', 0)
        current_match = info.get('current_match')
        is_fully_matched = matched_count == total_count and matched_count > 0
        
        # Create group with status indication
        if is_fully_matched:
            group_title = f"✓ {fixture_type} (All {total_count} matched)"
            group_style = "QGroupBox { font-weight: bold; margin-top: 10px; color: green; }"
        elif matched_count > 0:
            group_title = f"⚠ {fixture_type} ({matched_count}/{total_count} matched)"
            group_style = "QGroupBox { font-weight: bold; margin-top: 10px; color: orange; }"
        else:
            group_title = f"✗ {fixture_type} (0/{total_count} matched)"
            group_style = "QGroupBox { font-weight: bold; margin-top: 10px; color: red; }"
        
        group = QGroupBox(group_title)
        group.setStyleSheet(group_style)
        layout = QGridLayout(group)
        
        # Sample fixture names
        sample_names = info.get('sample_names', [])
        if sample_names:
            names_text = ', '.join(sample_names[:3])
            if len(sample_names) > 3:
                names_text += f" ... and {len(sample_names) - 3} more"
            sample_label = QLabel(f"Examples: {names_text}")
            sample_label.setStyleSheet("color: #666;")
            layout.addWidget(sample_label, 0, 0, 1, 2)
        
        # Profile selection
        layout.addWidget(QLabel("GDTF Profile:"), 1, 0)
        profile_combo = QComboBox()
        profile_combo.addItem("-- Select Profile --", "")
        
        # Add profiles grouped by source with dividers
        self._populate_profile_combo(profile_combo, fixture_type)
        
        # Pre-populate with current match if it exists
        if current_match and current_match.get('profile'):
            index = profile_combo.findData(current_match['profile'])
            if index >= 0:
                profile_combo.setCurrentIndex(index)
        
        profile_combo.currentIndexChanged.connect(
            lambda index, ft=fixture_type, combo=profile_combo: self.on_profile_changed(ft, combo.currentData())
        )
        layout.addWidget(profile_combo, 1, 1)
        
        # Mode selection
        layout.addWidget(QLabel("GDTF Mode:"), 2, 0)
        mode_combo = QComboBox()
        mode_combo.addItem("-- Select Mode --", "")
        
        # If we have a current profile selected, populate modes
        if current_match and current_match.get('profile'):
            modes = self.controller.get_profile_modes(current_match['profile'])
            for mode_name in modes:
                mode_combo.addItem(mode_name, mode_name)
            
            # Pre-populate with current mode if it exists
            if current_match.get('mode'):
                index = mode_combo.findData(current_match['mode'])
                if index >= 0:
                    mode_combo.setCurrentIndex(index)
        
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
                self.config.set_external_gdtf_folder(folder_path)
            self.load_external_gdtf_profiles(folder_path)
    
    def load_external_gdtf_profiles(self, folder_path: str):
        """Load external GDTF profiles while preserving current selections."""
        try:
            result = self.controller.load_external_gdtf_profiles(folder_path)
            
            if result["success"]:
                profiles_loaded = result["profiles_loaded"]
                
                # Update UI
                self.folder_label.setText(Path(folder_path).name)
                self.folder_label.setStyleSheet("color: black; font-weight: bold;")
                
                self.profiles_info.setText(
                    f"Added {profiles_loaded} external GDTF profiles"
                )
                self.profiles_info.setStyleSheet("color: green;")
                
                # Always refresh the entire dialog when new profiles are loaded
                self.load_unmatched_fixtures()
                
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
        """Update all profile dropdown menus while preserving current selections."""
        for fixture_type, controls in self.fixture_type_controls.items():
            profile_combo = controls['profile_combo']
            mode_combo = controls['mode_combo']
            
            # Save current selections
            current_profile = profile_combo.currentData()
            current_mode = mode_combo.currentData()
            
            # Clear and repopulate profile dropdown
            profile_combo.clear()
            profile_combo.addItem("-- Select Profile --", "")
            
            # Add profiles with sections and suggestions
            self._populate_profile_combo(profile_combo, fixture_type)
            
            # Restore profile selection if it still exists
            if current_profile:
                index = profile_combo.findData(current_profile)
                if index >= 0:
                    profile_combo.setCurrentIndex(index)
                    
                    # Repopulate modes for the selected profile
                    mode_combo.clear()
                    mode_combo.addItem("-- Select Mode --", "")
                    
                    modes = self.controller.get_profile_modes(current_profile)
                    for mode_name in modes:
                        mode_combo.addItem(mode_name, mode_name)
                    
                    # Restore mode selection if it still exists
                    if current_mode:
                        mode_index = mode_combo.findData(current_mode)
                        if mode_index >= 0:
                            mode_combo.setCurrentIndex(mode_index)
    
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

    def _show_no_profiles_guidance(self):
        """Show guidance when no GDTF profiles are available."""
        guidance_frame = QFrame()
        guidance_frame.setStyleSheet("background-color: #FFF3CD; border: 1px solid #F5C2C7; border-radius: 5px; padding: 10px; margin: 10px;")
        guidance_layout = QVBoxLayout(guidance_frame)
        
        title = QLabel("⚠ No GDTF Profiles Available")
        title.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        title.setStyleSheet("color: #664D03; margin-bottom: 10px;")
        guidance_layout.addWidget(title)
        
        # Different guidance based on import type
        import_type = getattr(self.controller, 'current_import_type', 'unknown')
        if import_type == 'csv':
            guidance_text = (
                "CSV imports don't contain GDTF profiles. To match fixture types and analyze DMX addresses, "
                "you need to load external GDTF profiles.\n\n"
                "Please use the 'Browse External GDTF Folder' button above to select a folder containing "
                "GDTF files (.gdtf), then return here to match your fixture types."
            )
        else:
            guidance_text = (
                "No GDTF profiles are currently loaded. You can:\n"
                "1. Load external GDTF profiles using the 'Browse External GDTF Folder' button above\n"
                "2. If you loaded an MVR file, make sure it contains GDTF profiles"
            )
        
        guidance_label = QLabel(guidance_text)
        guidance_label.setWordWrap(True)
        guidance_label.setStyleSheet("color: #664D03; line-height: 1.4;")
        guidance_layout.addWidget(guidance_label)
        
        self.fixture_layout.addWidget(guidance_frame) 