"""
GDTF Profile Matching Dialog.
Allows users to match fixture types to GDTF profiles and modes, and select attributes for analysis.
"""

from typing import Dict, List, Optional, Any
from pathlib import Path
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, 
    QPushButton, QComboBox, QGroupBox, QScrollArea, QWidget,
    QFileDialog, QMessageBox, QFrame, QCheckBox, QListWidget,
    QListWidgetItem, QSplitter, QTextEdit
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QColor

import core


class GDTFMatchingDialog(QDialog):
    """
    Dialog for matching fixture types to GDTF profiles and selecting attributes.
    """
    
    profiles_updated = pyqtSignal()  # Signal when GDTF profiles are updated
    
    def __init__(self, fixtures: List[Dict[str, Any]], config, parent=None):
        super().__init__(parent)
        self.fixtures = fixtures
        self.config = config
        self.fixture_type_controls = {}
        self.gdtf_profiles = {}
        self.external_profiles = {}
        
        self.setWindowTitle("GDTF Profile Matching & Attribute Selection")
        self.setMinimumSize(1200, 800)
        
        self._setup_ui()
        self._load_current_profiles()
        self._load_fixture_types()
    
    def _setup_ui(self):
        """Set up the user interface."""
        layout = QVBoxLayout(self)
        
        # Title
        title = QLabel("Match Fixture Types to GDTF Profiles & Select Attributes")
        title.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        layout.addWidget(title)
        
        # External GDTF folder section
        external_group = QGroupBox("External GDTF Profiles")
        external_layout = QGridLayout(external_group)
        
        external_layout.addWidget(QLabel("GDTF Folder:"), 0, 0)
        
        self.folder_label = QLabel("No external folder selected")
        self.folder_label.setStyleSheet("color: gray; font-style: italic;")
        external_layout.addWidget(self.folder_label, 0, 1)
        
        browse_folder_btn = QPushButton("Browse External GDTF Folder...")
        browse_folder_btn.clicked.connect(self._browse_gdtf_folder)
        external_layout.addWidget(browse_folder_btn, 0, 2)
        
        self.profiles_info = QLabel("No external profiles loaded")
        self.profiles_info.setStyleSheet("color: blue;")
        external_layout.addWidget(self.profiles_info, 1, 1, 1, 2)
        
        layout.addWidget(external_group)
        
        # Instructions
        instructions = QLabel(
            "Select GDTF profile and mode for each fixture type. "
            "Choose which attributes to analyze for DMX address calculation. "
            "✓ = Fully matched, ⚠ = Partially matched, ✗ = Not matched"
        )
        instructions.setWordWrap(True)
        instructions.setStyleSheet("color: #666; margin: 10px 0;")
        layout.addWidget(instructions)
        
        # Main content area - splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left side - fixture type matching
        matching_widget = self._create_matching_widget()
        splitter.addWidget(matching_widget)
        
        # Right side - attribute selection
        attributes_widget = self._create_attributes_widget()
        splitter.addWidget(attributes_widget)
        
        splitter.setSizes([600, 400])
        layout.addWidget(splitter)
        
        # Status area
        self.status_text = QTextEdit()
        self.status_text.setMaximumHeight(80)
        self.status_text.setReadOnly(True)
        layout.addWidget(self.status_text)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.auto_match_button = QPushButton("Auto-Match All")
        self.auto_match_button.clicked.connect(self._auto_match_all)
        button_layout.addWidget(self.auto_match_button)
        
        button_layout.addStretch()
        
        ok_btn = QPushButton("Apply Changes")
        ok_btn.setDefault(True)
        ok_btn.clicked.connect(self.accept)
        button_layout.addWidget(ok_btn)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
    
    def _create_matching_widget(self) -> QWidget:
        """Create the fixture type matching widget."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        layout.addWidget(QLabel("Fixture Type Matching:"))
        
        # Scrollable area for fixture matching
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        
        self.fixture_widget = QWidget()
        self.fixture_layout = QVBoxLayout(self.fixture_widget)
        
        scroll.setWidget(self.fixture_widget)
        layout.addWidget(scroll)
        
        return widget
    
    def _create_attributes_widget(self) -> QWidget:
        """Create the attribute selection widget."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        layout.addWidget(QLabel("Attribute Selection:"))
        
        # Attribute selection list
        self.attributes_list = QListWidget()
        self.attributes_list.setToolTip("Select attributes to analyze for DMX address calculation")
        layout.addWidget(self.attributes_list)
        
        # Attribute selection buttons
        attr_buttons_layout = QHBoxLayout()
        
        select_all_attr_btn = QPushButton("Select All")
        select_all_attr_btn.clicked.connect(self._select_all_attributes)
        attr_buttons_layout.addWidget(select_all_attr_btn)
        
        select_none_attr_btn = QPushButton("Select None")
        select_none_attr_btn.clicked.connect(self._select_none_attributes)
        attr_buttons_layout.addWidget(select_none_attr_btn)
        
        select_common_attr_btn = QPushButton("Select Common")
        select_common_attr_btn.clicked.connect(self._select_common_attributes)
        attr_buttons_layout.addWidget(select_common_attr_btn)
        
        layout.addLayout(attr_buttons_layout)
        
        return widget
    
    def _load_current_profiles(self):
        """Load current GDTF profiles from fixtures and external folder."""
        # Extract GDTF profiles from fixtures (from MVR imports)
        self.gdtf_profiles = {}
        for fixture in self.fixtures:
            if fixture.get('gdtf_profile'):
                profile_name = fixture.get('type', 'Unknown')
                self.gdtf_profiles[profile_name] = fixture['gdtf_profile']
        
        # Load external GDTF folder if configured
        external_folder = self.config.get_external_gdtf_folder()
        if external_folder and Path(external_folder).exists():
            self._load_external_gdtf_profiles(external_folder, update_ui=False)
    
    def _load_fixture_types(self):
        """Load all fixture types and create matching controls."""
        # Clear existing controls
        for i in reversed(range(self.fixture_layout.count())):
            widget = self.fixture_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)
        self.fixture_type_controls.clear()
        
        # Group fixtures by type
        fixture_types = {}
        for fixture in self.fixtures:
            fixture_type = fixture.get('type', 'Unknown')
            if fixture_type not in fixture_types:
                fixture_types[fixture_type] = {
                    'count': 0,
                    'fixtures': [],
                    'sample_names': [],
                    'current_profile': None,
                    'current_mode': None
                }
            
            fixture_types[fixture_type]['count'] += 1
            fixture_types[fixture_type]['fixtures'].append(fixture)
            
            # Add sample names (up to 3)
            if len(fixture_types[fixture_type]['sample_names']) < 3:
                fixture_types[fixture_type]['sample_names'].append(fixture.get('name', ''))
            
            # Track current profile/mode if already matched
            if fixture.get('matched') and not fixture_types[fixture_type]['current_profile']:
                fixture_types[fixture_type]['current_profile'] = fixture.get('gdtf_profile_name')
                fixture_types[fixture_type]['current_mode'] = fixture.get('mode')
        
        if not fixture_types:
            no_fixtures_label = QLabel("No fixtures loaded.")
            no_fixtures_label.setStyleSheet("color: red; font-weight: bold; padding: 20px;")
            self.fixture_layout.addWidget(no_fixtures_label)
            return
        
        # Check if we have any GDTF profiles available
        all_profiles = {**self.gdtf_profiles, **self.external_profiles}
        if not all_profiles:
            self._show_no_profiles_guidance()
        
        # Create matching controls for each fixture type
        for fixture_type, info in fixture_types.items():
            group_widget = self._create_fixture_type_control(fixture_type, info)
            self.fixture_layout.addWidget(group_widget)
        
        # Update attribute list
        self._update_attribute_list()
    
    def _create_fixture_type_control(self, fixture_type: str, info: Dict) -> QWidget:
        """Create UI controls for a fixture type."""
        # Determine match status
        matched_count = sum(1 for f in info['fixtures'] if f.get('matched'))
        total_count = info['count']
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
            names_text = ', '.join(sample_names)
            sample_label = QLabel(f"Examples: {names_text}")
            sample_label.setStyleSheet("color: #666;")
            layout.addWidget(sample_label, 0, 0, 1, 2)
        
        # Profile selection
        layout.addWidget(QLabel("GDTF Profile:"), 1, 0)
        profile_combo = QComboBox()
        profile_combo.addItem("-- Select Profile --", "")
        
        # Add profiles grouped by source
        self._populate_profile_combo(profile_combo)
        
        # Pre-populate with current profile if it exists
        current_profile = info.get('current_profile')
        if current_profile:
            index = profile_combo.findData(current_profile)
            if index >= 0:
                profile_combo.setCurrentIndex(index)
        
        profile_combo.currentIndexChanged.connect(
            lambda index, ft=fixture_type, combo=profile_combo: self._on_profile_changed(ft, combo.currentData())
        )
        layout.addWidget(profile_combo, 1, 1)
        
        # Mode selection
        layout.addWidget(QLabel("GDTF Mode:"), 2, 0)
        mode_combo = QComboBox()
        mode_combo.addItem("-- Select Mode --", "")
        
        # If we have a current profile selected, populate modes
        if current_profile:
            modes = self._get_profile_modes(current_profile)
            for mode_name in modes:
                mode_combo.addItem(mode_name, mode_name)
            
            # Pre-populate with current mode if it exists
            current_mode = info.get('current_mode')
            if current_mode:
                index = mode_combo.findData(current_mode)
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
    
    def _populate_profile_combo(self, profile_combo: QComboBox):
        """Populate a profile combo box with sections for MVR and external profiles."""
        # Add MVR profiles section
        if self.gdtf_profiles:
            divider_index = profile_combo.count()
            profile_combo.addItem("── MVR GDTF PROFILES ──", "")
            item = profile_combo.model().item(divider_index)
            item.setEnabled(False)
            font = item.font()
            font.setBold(True)
            item.setFont(font)
            item.setForeground(QColor(100, 100, 100))
            
            for profile_name in sorted(self.gdtf_profiles.keys()):
                profile_combo.addItem(f"  {profile_name}", profile_name)
        
        # Add External profiles section
        if self.external_profiles:
            divider_index = profile_combo.count()
            profile_combo.addItem("── EXTERNAL GDTF PROFILES ──", "")
            item = profile_combo.model().item(divider_index)
            item.setEnabled(False)
            font = item.font()
            font.setBold(True)
            item.setFont(font)
            item.setForeground(QColor(100, 100, 100))
            
            for profile_name in sorted(self.external_profiles.keys()):
                profile_combo.addItem(f"  {profile_name}", profile_name)
    
    def _on_profile_changed(self, fixture_type: str, profile_name: str):
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
            modes = self._get_profile_modes(profile_name)
            for mode_name in modes:
                mode_combo.addItem(mode_name, mode_name)
        
        # Update attribute list
        self._update_attribute_list()
    
    def _get_profile_modes(self, profile_name: str) -> List[str]:
        """Get available modes for a specific GDTF profile."""
        profile = self.gdtf_profiles.get(profile_name) or self.external_profiles.get(profile_name)
        if profile and 'modes' in profile:
            return list(profile['modes'].keys())
        return []
    
    def _browse_gdtf_folder(self):
        """Browse for external GDTF folder."""
        start_dir = ""
        if self.config:
            last_dir = self.config.get_last_gdtf_directory()
            start_dir = last_dir if last_dir and Path(last_dir).exists() else ""
        
        # Use native macOS dialog with files visible but greyed out
        folder_path = QFileDialog.getExistingDirectory(
            self,
            "Select GDTF Folder",
            start_dir
        )
        
        if folder_path:
            if self.config:
                self.config.set_last_gdtf_directory(folder_path)
                self.config.set_external_gdtf_folder(folder_path)
            self._load_external_gdtf_profiles(folder_path)
    
    def _load_external_gdtf_profiles(self, folder_path: str, update_ui: bool = True):
        """Load external GDTF profiles from folder."""
        try:
            self.external_profiles = core.parse_external_gdtf_folder(folder_path)
            
            # Update UI
            if update_ui:
                self.folder_label.setText(Path(folder_path).name)
                self.folder_label.setStyleSheet("color: black; font-weight: bold;")
                
                self.profiles_info.setText(f"Loaded {len(self.external_profiles)} external GDTF profiles")
                self.profiles_info.setStyleSheet("color: green;")
                
                # Refresh the fixture type controls
                self._update_all_profile_dropdowns()
                self._update_attribute_list()
                
                self.status_text.append(f"Loaded {len(self.external_profiles)} external GDTF profiles from {Path(folder_path).name}")
        
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load GDTF profiles:\n{str(e)}")
    
    def _update_all_profile_dropdowns(self):
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
            self._populate_profile_combo(profile_combo)
            
            # Restore profile selection if it still exists
            if current_profile:
                index = profile_combo.findData(current_profile)
                if index >= 0:
                    profile_combo.setCurrentIndex(index)
                    
                    # Repopulate modes for the selected profile
                    mode_combo.clear()
                    mode_combo.addItem("-- Select Mode --", "")
                    
                    modes = self._get_profile_modes(current_profile)
                    for mode_name in modes:
                        mode_combo.addItem(mode_name, mode_name)
                    
                    # Restore mode selection if it still exists
                    if current_mode:
                        mode_index = mode_combo.findData(current_mode)
                        if mode_index >= 0:
                            mode_combo.setCurrentIndex(mode_index)
    
    def _update_attribute_list(self):
        """Update the attribute selection list based on available profiles."""
        self.attributes_list.clear()
        
        # Collect all available attributes from all profiles
        all_attributes = set()
        all_profiles = {**self.gdtf_profiles, **self.external_profiles}
        
        for profile in all_profiles.values():
            if 'modes' in profile:
                for mode in profile['modes'].values():
                    all_attributes.update(mode.keys())
        
        # Add attributes to list with checkboxes
        for attr_name in sorted(all_attributes):
            item = QListWidgetItem(attr_name)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Unchecked)
            self.attributes_list.addItem(item)
        
        # Pre-select common attributes
        self._select_common_attributes()
    
    def _select_all_attributes(self):
        """Select all attributes."""
        for i in range(self.attributes_list.count()):
            item = self.attributes_list.item(i)
            item.setCheckState(Qt.CheckState.Checked)
    
    def _select_none_attributes(self):
        """Deselect all attributes."""
        for i in range(self.attributes_list.count()):
            item = self.attributes_list.item(i)
            item.setCheckState(Qt.CheckState.Unchecked)
    
    def _select_common_attributes(self):
        """Select commonly used attributes."""
        common_attributes = {
            'Dimmer', 'Pan', 'Tilt', 'ColorAdd_R', 'ColorAdd_G', 'ColorAdd_B',
            'ColorAdd_W', 'ColorAdd_A', 'ColorAdd_UV', 'Gobo1', 'Gobo2',
            'Zoom', 'Focus', 'Iris', 'Shutter1', 'Strobe1'
        }
        
        for i in range(self.attributes_list.count()):
            item = self.attributes_list.item(i)
            if item.text() in common_attributes:
                item.setCheckState(Qt.CheckState.Checked)
            else:
                item.setCheckState(Qt.CheckState.Unchecked)
    
    def _auto_match_all(self):
        """Auto-match all fixture types to available GDTF profiles."""
        all_profiles = {**self.gdtf_profiles, **self.external_profiles}
        if not all_profiles:
            QMessageBox.information(self, "No Profiles", "No GDTF profiles available for matching.")
            return
        
        matches_made = 0
        
        for fixture_type, controls in self.fixture_type_controls.items():
            profile_combo = controls['profile_combo']
            mode_combo = controls['mode_combo']
            
            # Try to find a matching profile
            matched_profile = None
            for profile_name in all_profiles.keys():
                if fixture_type.lower() in profile_name.lower() or profile_name.lower() in fixture_type.lower():
                    matched_profile = profile_name
                    break
            
            if matched_profile:
                # Set the profile
                index = profile_combo.findData(matched_profile)
                if index >= 0:
                    profile_combo.setCurrentIndex(index)
                    
                    # Auto-select first available mode
                    modes = self._get_profile_modes(matched_profile)
                    if modes:
                        mode_combo.clear()
                        mode_combo.addItem("-- Select Mode --", "")
                        for mode_name in modes:
                            mode_combo.addItem(mode_name, mode_name)
                        mode_combo.setCurrentIndex(1)  # Select first mode
                        matches_made += 1
        
        if matches_made > 0:
            self.status_text.append(f"Auto-matched {matches_made} fixture type(s)")
        else:
            self.status_text.append("No automatic matches found")
    
    def _show_no_profiles_guidance(self):
        """Show guidance when no GDTF profiles are available."""
        guidance_frame = QFrame()
        guidance_frame.setStyleSheet("background-color: #FFF3CD; border: 1px solid #F5C2C7; border-radius: 5px; padding: 10px; margin: 10px;")
        guidance_layout = QVBoxLayout(guidance_frame)
        
        title = QLabel("⚠ No GDTF Profiles Available")
        title.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        title.setStyleSheet("color: #664D03; margin-bottom: 10px;")
        guidance_layout.addWidget(title)
        
        guidance_text = (
            "No GDTF profiles are currently loaded. To match fixture types and analyze DMX addresses:\n\n"
            "1. Use the 'Browse External GDTF Folder' button above to select a folder containing GDTF files (.gdtf)\n"
            "2. For MVR imports, ensure the MVR file contains embedded GDTF profiles\n"
            "3. Return here to match your fixture types after loading profiles"
        )
        
        guidance_label = QLabel(guidance_text)
        guidance_label.setWordWrap(True)
        guidance_label.setStyleSheet("color: #664D03; line-height: 1.4;")
        guidance_layout.addWidget(guidance_label)
        
        self.fixture_layout.addWidget(guidance_frame)
    
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
    
    def get_selected_attributes(self) -> List[str]:
        """Get the list of selected attributes."""
        selected_attributes = []
        
        for i in range(self.attributes_list.count()):
            item = self.attributes_list.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                selected_attributes.append(item.text())
        
        return selected_attributes
    
    def apply_matches_to_fixtures(self):
        """Apply the selected matches to the fixtures."""
        matches = self.get_fixture_type_matches()
        selected_attributes = self.get_selected_attributes()
        
        # Get all available profiles
        all_profiles = {**self.gdtf_profiles, **self.external_profiles}
        
        fixtures_updated = 0
        
        for fixture in self.fixtures:
            fixture_type = fixture.get('type', 'Unknown')
            
            if fixture_type in matches:
                match_info = matches[fixture_type]
                profile_name = match_info['profile']
                mode_name = match_info['mode']
                
                # Apply profile and mode to fixture
                profile = all_profiles.get(profile_name)
                if profile and 'modes' in profile and mode_name in profile['modes']:
                    fixture['gdtf_profile_name'] = profile_name
                    fixture['gdtf_profile'] = profile
                    fixture['mode'] = mode_name
                    fixture['matched'] = True
                    fixture['selected_attributes'] = selected_attributes
                    fixtures_updated += 1
        
        self.status_text.append(f"Applied matches to {fixtures_updated} fixture(s)")
        return fixtures_updated 