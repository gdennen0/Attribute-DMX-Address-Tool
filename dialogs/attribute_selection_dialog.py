"""
Attribute Selection Dialog - Clean UI for selecting attributes and matching GDTF profiles.
Appears after MVR/CSV import to configure fixture types and attributes.
"""

import os
from typing import Dict, List, Optional
from pathlib import Path

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, 
    QPushButton, QComboBox, QGroupBox, QScrollArea, QWidget,
    QFileDialog, QMessageBox, QFrame, QCheckBox, QSplitter
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QColor

from controllers.attribute_selection_controller import AttributeSelectionController


class AttributeSelectionDialog(QDialog):
    """
    Dialog for selecting attributes and matching GDTF profiles after import.
    Combines fixture type matching with attribute selection.
    """
    
    attributes_selected = pyqtSignal(list)  # List of selected attributes
    
    def __init__(self, fixtures: List[Dict], config, parent=None):
        super().__init__(parent)
        self.config = config
        self.controller = AttributeSelectionController(config)
        self.controller.set_fixtures(fixtures)
        self.fixture_type_controls = {}
        self.attribute_controls = {}
        self.selected_attributes = self.config.get_selected_attributes()
        
        self.setWindowTitle("Attribute Selection & GDTF Matching")
        self.setGeometry(200, 200, 1200, 800)
        
        self.setup_ui()
        self.load_fixture_types()
        self.load_saved_matches()
        
        # Load saved external GDTF folder if available
        external_folder = self.config.get_external_gdtf_folder()
        if external_folder and os.path.exists(external_folder):
            self.load_external_gdtf_profiles(external_folder)
    
    def setup_ui(self):
        """Create the dialog interface."""
        layout = QVBoxLayout(self)
        
        # Title
        title = QLabel("Configure Fixture Types & Select Attributes")
        title.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        layout.addWidget(title)
        
        # Main content area - only GDTF matching panel
        content_panel = self.setup_gdtf_matching_panel()
        layout.addWidget(content_panel)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        ok_btn = QPushButton("Apply & Continue")
        ok_btn.setDefault(True)
        ok_btn.clicked.connect(self.accept)
        button_layout.addWidget(ok_btn)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
    
    def setup_gdtf_matching_panel(self) -> QWidget:
        """Set up the GDTF matching panel."""
        panel = QGroupBox("GDTF Profile Matching")
        layout = QVBoxLayout(panel)
        
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
        
        self.profiles_info = QLabel("No external GDTF profiles loaded")
        self.profiles_info.setStyleSheet("color: blue;")
        external_layout.addWidget(self.profiles_info, 1, 1, 1, 2)
        
        layout.addWidget(external_group)
        
        # Instructions
        instructions = QLabel(
            "Match GDTF profiles to your fixture types. All fixtures of the same type will use the same profile and mode. "
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
        
        return panel
    
    def select_all_for_fixture_type(self, fixture_type: str):
        """Select all attributes for a specific fixture type."""
        controls = self.fixture_type_controls.get(fixture_type)
        if controls:
            for checkbox in controls['attr_checkboxes'].values():
                checkbox.setChecked(True)
    
    def select_none_for_fixture_type(self, fixture_type: str):
        """Deselect all attributes for a specific fixture type."""
        controls = self.fixture_type_controls.get(fixture_type)
        if controls:
            for checkbox in controls['attr_checkboxes'].values():
                checkbox.setChecked(False)
    
    def load_fixture_types(self):
        """Load fixture types from selected fixtures and create UI for matching."""
        # Clear existing controls
        for control in self.fixture_type_controls.values():
            control['group'].setParent(None)
        self.fixture_type_controls.clear()
        
        # Clear any existing guidance widgets
        for i in reversed(range(self.fixture_layout.count())):
            widget = self.fixture_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)
        
        # Get fixture type information
        fixture_info = self.controller.get_fixture_types_from_selected()
        
        if not fixture_info:
            no_fixtures_label = QLabel("No fixtures loaded.")
            no_fixtures_label.setStyleSheet("color: red; font-weight: bold; padding: 20px;")
            self.fixture_layout.addWidget(no_fixtures_label)
            return
        
        # Check if we have any GDTF profiles available
        profiles_by_source = self.controller.get_profiles_by_source()
        has_profiles = bool(profiles_by_source.get('mvr', []) or profiles_by_source.get('external', []))
        
        if not has_profiles:
            # Show guidance for when no profiles are available
            self.show_no_profiles_guidance()
        
        # Create matching controls for each fixture type
        for fixture_type, info in fixture_info.items():
            group_widget = self.create_fixture_type_control(fixture_type, info)
            self.fixture_layout.addWidget(group_widget)
    
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
        self.populate_profile_combo(profile_combo, fixture_type)
        
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
        # Attribute selection (per fixture type)
        attr_label = QLabel("Attributes:")
        layout.addWidget(attr_label, 3, 0)
        
        # Select All/None buttons for this fixture type
        select_buttons_layout = QHBoxLayout()
        select_all_btn = QPushButton("Select All")
        select_none_btn = QPushButton("Select None")
        select_all_btn.clicked.connect(lambda: self.select_all_for_fixture_type(fixture_type))
        select_none_btn.clicked.connect(lambda: self.select_none_for_fixture_type(fixture_type))
        select_buttons_layout.addWidget(select_all_btn)
        select_buttons_layout.addWidget(select_none_btn)
        select_buttons_layout.addStretch()
        layout.addLayout(select_buttons_layout, 3, 1)
        
        attr_widget = QWidget()
        attr_layout = QVBoxLayout(attr_widget)
        attr_layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(attr_widget, 4, 1)
        
        # Store references
        self.fixture_type_controls[fixture_type] = {
            'group': group,
            'profile_combo': profile_combo,
            'mode_combo': mode_combo,
            'attr_widget': attr_widget,
            'attr_layout': attr_layout,
            'attr_checkboxes': {},
            'info': info
        }
        # Populate attributes if profile+mode is set
        if current_match and current_match.get('profile') and current_match.get('mode'):
            self.populate_attribute_checkboxes(fixture_type, current_match['profile'], current_match['mode'])
        # Connect mode change to update attributes
        mode_combo.currentIndexChanged.connect(
            lambda idx, ft=fixture_type, pc=profile_combo, mc=mode_combo: self.on_mode_changed(ft, pc.currentData(), mc.currentData())
        )
        return group
    
    def populate_profile_combo(self, profile_combo: QComboBox, fixture_type: str = None):
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
        # Clear attributes
        self.clear_attribute_checkboxes(fixture_type)
    
    def on_mode_changed(self, fixture_type: str, profile_name: str, mode_name: str):
        self.populate_attribute_checkboxes(fixture_type, profile_name, mode_name)
    
    def populate_attribute_checkboxes(self, fixture_type: str, profile_name: str, mode_name: str):
        controls = self.fixture_type_controls[fixture_type]
        attr_layout = controls['attr_layout']
        # Clear old
        self.clear_attribute_checkboxes(fixture_type)
        available_attrs = self.controller.get_available_attributes_for_profile_mode(profile_name, mode_name)
        saved_attrs = self.controller.get_fixture_type_attributes().get(fixture_type, [])
        for attr in available_attrs:
            checkbox = QCheckBox(attr)
            checkbox.setChecked(attr in saved_attrs)
            checkbox.stateChanged.connect(lambda state, ft=fixture_type, a=attr: self.on_attribute_changed(ft, a, state))
            controls['attr_checkboxes'][attr] = checkbox
            attr_layout.addWidget(checkbox)
    
    def clear_attribute_checkboxes(self, fixture_type: str):
        controls = self.fixture_type_controls[fixture_type]
        for cb in controls['attr_checkboxes'].values():
            cb.setParent(None)
        controls['attr_checkboxes'].clear()
    
    def on_attribute_changed(self, fixture_type: str, attribute: str, state: int):
        # Save per-type attribute selection in memory
        if not hasattr(self, 'per_type_selected_attributes'):
            self.per_type_selected_attributes = {}
        selected = state == Qt.CheckState.Checked.value
        attrs = self.per_type_selected_attributes.get(fixture_type, set())
        if selected:
            attrs.add(attribute)
        else:
            attrs.discard(attribute)
        self.per_type_selected_attributes[fixture_type] = attrs
    
    def select_all_attributes(self):
        """Select all available attributes."""
        for fixture_type, controls in self.fixture_type_controls.items():
            attr_layout = controls['attr_layout']
            for checkbox in controls['attr_checkboxes'].values():
                checkbox.setChecked(True)
    
    def select_none_attributes(self):
        """Deselect all attributes."""
        for fixture_type, controls in self.fixture_type_controls.items():
            attr_layout = controls['attr_layout']
            for checkbox in controls['attr_checkboxes'].values():
                checkbox.setChecked(False)
    
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
    
    def accept(self):
        """Handle dialog acceptance - save matches and attributes."""
        # Collect fixture type matches
        fixture_type_matches = {}
        for fixture_type, controls in self.fixture_type_controls.items():
            profile_combo = controls['profile_combo']
            mode_combo = controls['mode_combo']
            
            profile_name = profile_combo.currentData()
            mode_name = mode_combo.currentData()
            
            if profile_name and mode_name:
                fixture_type_matches[fixture_type] = {
                    'profile': profile_name,
                    'mode': mode_name
                }
        
        # Collect fixture type attributes
        fixture_type_attributes = {}
        for fixture_type, controls in self.fixture_type_controls.items():
            selected_attrs = []
            for attr_name, checkbox in controls['attr_checkboxes'].items():
                if checkbox.isChecked():
                    selected_attrs.append(attr_name)
            if selected_attrs:
                fixture_type_attributes[fixture_type] = selected_attrs
        
        # Update fixture matches and create GDTF profile models
        result = self.controller.update_fixture_matches(fixture_type_matches, fixture_type_attributes)
        
        if result['success']:
            # Save fixture type attributes to config
            self.controller.set_fixture_type_attributes(fixture_type_attributes)
            
            # Emit signal with selected attributes (for backward compatibility)
            all_selected_attributes = []
            for attributes in fixture_type_attributes.values():
                all_selected_attributes.extend(attributes)
            self.attributes_selected.emit(all_selected_attributes)
            
            super().accept()
        else:
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to update fixture matches:\n{result['error']}"
            )
    
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
                self.load_fixture_types()
                
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
    
    def load_saved_matches(self):
        """Load previously saved fixture type matches."""
        saved_matches = self.controller.get_saved_fixture_matches()
        saved_attrs = self.controller.get_fixture_type_attributes()
        self.per_type_selected_attributes = {k: set(v) for k, v in saved_attrs.items()}
        if saved_matches:
            self.controller.update_fixture_matches(saved_matches)
            for fixture_type, match in saved_matches.items():
                controls = self.fixture_type_controls.get(fixture_type)
                if controls:
                    profile_combo = controls['profile_combo']
                    mode_combo = controls['mode_combo']
                    if match.get('profile'):
                        idx = profile_combo.findData(match['profile'])
                        if idx >= 0:
                            profile_combo.setCurrentIndex(idx)
                            mode_combo.clear()
                            mode_combo.addItem("-- Select Mode --", "")
                            modes = self.controller.get_profile_modes(match['profile'])
                            for mode_name in modes:
                                mode_combo.addItem(mode_name, mode_name)
                            if match.get('mode'):
                                mode_idx = mode_combo.findData(match['mode'])
                                if mode_idx >= 0:
                                    mode_combo.setCurrentIndex(mode_idx)
                                    # Populate attributes for this type
                                    self.populate_attribute_checkboxes(fixture_type, match['profile'], match['mode'])
    
    def show_no_profiles_guidance(self):
        """Show guidance when no GDTF profiles are available."""
        guidance_frame = QFrame()
        guidance_frame.setStyleSheet("background-color: #FFF3CD; border: 1px solid #F5C2C7; border-radius: 5px; padding: 10px; margin: 10px;")
        guidance_layout = QVBoxLayout(guidance_frame)
        
        title = QLabel("⚠ No GDTF Profiles Available")
        title.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        title.setStyleSheet("color: #664D03; margin-bottom: 10px;")
        guidance_layout.addWidget(title)
        
        guidance_text = (
            "No GDTF profiles are currently loaded. To match fixture types and analyze DMX addresses, "
            "you need to load external GDTF profiles.\n\n"
            "Please use the 'Browse External GDTF Folder' button above to select a folder containing "
            "GDTF files (.gdtf), then return here to match your fixture types."
        )
        
        guidance_label = QLabel(guidance_text)
        guidance_label.setWordWrap(True)
        guidance_label.setStyleSheet("color: #664D03; line-height: 1.4;")
        guidance_layout.addWidget(guidance_label)
        
        self.fixture_layout.addWidget(guidance_frame) 