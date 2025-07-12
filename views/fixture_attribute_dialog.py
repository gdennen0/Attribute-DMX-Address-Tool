"""
Fixture Attribute Selection Dialog - Clean UI for selecting attributes per fixture type.
Uses controller architecture for business logic.
"""

import os
from typing import Dict, List, Optional
from pathlib import Path

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, 
    QPushButton, QComboBox, QGroupBox, QScrollArea, QWidget,
    QCheckBox, QMessageBox, QFrame
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from controllers import MVRController


class FixtureAttributeDialog(QDialog):
    """
    Dialog for selecting attributes per fixture type.
    Uses controller for all business logic.
    """
    
    def __init__(self, parent, controller: MVRController, config=None, existing_fixture_type_attributes=None):
        super().__init__(parent)
        self.controller = controller
        self.config = config
        self.existing_fixture_type_attributes = existing_fixture_type_attributes or {}
        self.fixture_type_controls = {}
        self.fixture_type_attributes = {}  # Store selected attributes per fixture type
        self.setup_ui()
        self.load_fixture_types()
        
        # Load existing selections into the dialog
        self.load_existing_selections()
    
    def setup_ui(self):
        """Create the dialog interface."""
        self.setWindowTitle("Attribute Selection per Fixture Type")
        self.setGeometry(200, 200, 1200, 800)
        
        layout = QVBoxLayout(self)
        
        # Title
        title = QLabel("Select Attributes for Each Fixture Type")
        title.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        layout.addWidget(title)
        
        # Instructions
        instructions = QLabel(
            "Choose which attributes to analyze for each fixture type. "
            "Different fixture types can have different attributes selected."
        )
        instructions.setWordWrap(True)
        instructions.setStyleSheet("color: #666; margin: 10px 0;")
        layout.addWidget(instructions)
        
        # Scrollable area for fixture type controls
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        
        self.fixture_widget = QWidget()
        self.fixture_layout = QVBoxLayout(self.fixture_widget)
        
        scroll.setWidget(self.fixture_widget)
        layout.addWidget(scroll)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        # Global controls
        select_all_btn = QPushButton("Select All Attributes")
        select_all_btn.clicked.connect(self.select_all_attributes)
        button_layout.addWidget(select_all_btn)
        
        clear_all_btn = QPushButton("Clear All Attributes")
        clear_all_btn.clicked.connect(self.clear_all_attributes)
        button_layout.addWidget(clear_all_btn)
        
        button_layout.addStretch()
        
        # Dialog controls
        ok_btn = QPushButton("Continue with Analysis")
        ok_btn.setDefault(True)
        ok_btn.clicked.connect(self.accept)
        button_layout.addWidget(ok_btn)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
    
    def load_fixture_types(self):
        """Load fixture types from controller and create UI."""
        # Clear existing controls
        for control in self.fixture_type_controls.values():
            control['group'].setParent(None)
        self.fixture_type_controls.clear()
        
        # Get current status
        status = self.controller.get_current_status()
        if not status["file_loaded"]:
            return
        
        # Get fixture types information
        fixture_types_info = self._get_fixture_types_info()
        
        if not fixture_types_info:
            no_fixtures_label = QLabel("No fixture types found.")
            no_fixtures_label.setStyleSheet("color: red; font-weight: bold; padding: 20px;")
            self.fixture_layout.addWidget(no_fixtures_label)
            return
        
        # Create attribute selection controls for each fixture type
        for fixture_type, info in fixture_types_info.items():
            group_widget = self.create_fixture_type_control(fixture_type, info)
            self.fixture_layout.addWidget(group_widget)
    
    def _get_fixture_types_info(self) -> Dict[str, Dict]:
        """Get fixture type information from controller."""
        # Get all fixtures (both matched and unmatched)
        all_fixtures = self.controller.matched_fixtures
        
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
                    'available_attributes': set()
                }
            
            fixture_types[fixture_type_clean]['count'] += 1
            fixture_types[fixture_type_clean]['fixtures'].append(fixture)
            
            # Track matched fixtures
            if fixture.is_matched():
                fixture_types[fixture_type_clean]['matched_count'] += 1
                # Get attributes for this fixture type
                if fixture.matched_mode:
                    fixture_types[fixture_type_clean]['available_attributes'].update(
                        fixture.matched_mode.channels.keys()
                    )
            
            # Add sample names (up to 5)
            if len(fixture_types[fixture_type_clean]['sample_names']) < 5:
                fixture_types[fixture_type_clean]['sample_names'].append(fixture.name)
        
        # Convert attributes set to sorted list
        for fixture_type in fixture_types:
            fixture_types[fixture_type]['available_attributes'] = sorted(
                list(fixture_types[fixture_type]['available_attributes'])
            )
        
        return fixture_types
    
    def create_fixture_type_control(self, fixture_type: str, info: Dict) -> QWidget:
        """Create UI controls for a fixture type."""
        group = QGroupBox(f"Fixture Type: {fixture_type}")
        group.setStyleSheet("QGroupBox { font-weight: bold; margin-top: 10px; }")
        layout = QVBoxLayout(group)
        
        # Fixture info section
        info_layout = QHBoxLayout()
        
        # Fixture count
        count_label = QLabel(f"Fixtures: {info.get('count', 0)}")
        count_label.setStyleSheet("color: #666;")
        info_layout.addWidget(count_label)
        
        # Matched count
        matched_count = info.get('matched_count', 0)
        if matched_count > 0:
            matched_label = QLabel(f"Matched: {matched_count}")
            matched_label.setStyleSheet("color: green;")
            info_layout.addWidget(matched_label)
        else:
            matched_label = QLabel("No GDTF matches")
            matched_label.setStyleSheet("color: red;")
            info_layout.addWidget(matched_label)
        
        info_layout.addStretch()
        layout.addLayout(info_layout)
        
        # Sample fixture names
        sample_names = info.get('sample_names', [])
        if sample_names:
            names_text = ', '.join(sample_names[:3])
            if len(sample_names) > 3:
                names_text += f" ... and {len(sample_names) - 3} more"
            sample_label = QLabel(f"Examples: {names_text}")
            sample_label.setStyleSheet("color: #666; font-style: italic;")
            layout.addWidget(sample_label)
        
        # Attributes section
        available_attributes = info.get('available_attributes', [])
        
        if available_attributes:
            # Attributes selection
            attr_label = QLabel("Select Attributes:")
            attr_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
            layout.addWidget(attr_label)
            
            # Scrollable area for attributes
            attr_scroll = QScrollArea()
            attr_scroll.setWidgetResizable(True)
            attr_scroll.setMaximumHeight(200)
            
            attr_widget = QWidget()
            attr_layout = QGridLayout(attr_widget)
            
            # Create checkboxes for attributes
            checkboxes = {}
            for i, attr_name in enumerate(available_attributes):
                checkbox = QCheckBox(attr_name)
                row = i // 3
                col = i % 3
                attr_layout.addWidget(checkbox, row, col)
                checkboxes[attr_name] = checkbox
            
            attr_scroll.setWidget(attr_widget)
            layout.addWidget(attr_scroll)
            
            # Control buttons for this fixture type
            control_layout = QHBoxLayout()
            
            select_all_btn = QPushButton("Select All")
            select_all_btn.clicked.connect(
                lambda checked, ft=fixture_type: self.select_all_for_fixture_type(ft)
            )
            control_layout.addWidget(select_all_btn)
            
            clear_all_btn = QPushButton("Clear All")
            clear_all_btn.clicked.connect(
                lambda checked, ft=fixture_type: self.clear_all_for_fixture_type(ft)
            )
            control_layout.addWidget(clear_all_btn)
            
            control_layout.addStretch()
            layout.addLayout(control_layout)
            
        else:
            # No attributes available
            no_attr_label = QLabel("No attributes available (requires GDTF matching)")
            no_attr_label.setStyleSheet("color: orange; font-style: italic;")
            layout.addWidget(no_attr_label)
            checkboxes = {}
        
        # Store references
        self.fixture_type_controls[fixture_type] = {
            'group': group,
            'checkboxes': checkboxes,
            'info': info,
            'available_attributes': available_attributes
        }
        
        # Initialize fixture type attributes storage
        self.fixture_type_attributes[fixture_type] = []
        
        return group
    
    def select_all_for_fixture_type(self, fixture_type: str):
        """Select all attributes for a specific fixture type."""
        if fixture_type in self.fixture_type_controls:
            checkboxes = self.fixture_type_controls[fixture_type]['checkboxes']
            for checkbox in checkboxes.values():
                checkbox.setChecked(True)
    
    def clear_all_for_fixture_type(self, fixture_type: str):
        """Clear all attributes for a specific fixture type."""
        if fixture_type in self.fixture_type_controls:
            checkboxes = self.fixture_type_controls[fixture_type]['checkboxes']
            for checkbox in checkboxes.values():
                checkbox.setChecked(False)
    
    def select_all_attributes(self):
        """Select all attributes for all fixture types."""
        for fixture_type in self.fixture_type_controls:
            self.select_all_for_fixture_type(fixture_type)
    
    def clear_all_attributes(self):
        """Clear all attributes for all fixture types."""
        for fixture_type in self.fixture_type_controls:
            self.clear_all_for_fixture_type(fixture_type)
    
    def get_fixture_type_attributes(self) -> Dict[str, List[str]]:
        """Get the selected attributes for each fixture type."""
        fixture_type_attributes = {}
        
        for fixture_type, controls in self.fixture_type_controls.items():
            checkboxes = controls['checkboxes']
            selected_attributes = []
            
            for attr_name, checkbox in checkboxes.items():
                if checkbox.isChecked():
                    selected_attributes.append(attr_name)
            
            fixture_type_attributes[fixture_type] = selected_attributes
        
        return fixture_type_attributes
    
    def validate_selections(self) -> bool:
        """Validate that at least one attribute is selected for fixtures with matches."""
        fixture_type_attributes = self.get_fixture_type_attributes()
        
        # Check if any fixture type with matches has no attributes selected
        for fixture_type, controls in self.fixture_type_controls.items():
            matched_count = controls['info'].get('matched_count', 0)
            selected_attributes = fixture_type_attributes.get(fixture_type, [])
            
            if matched_count > 0 and not selected_attributes:
                QMessageBox.warning(
                    self, 
                    "No Attributes Selected", 
                    f"Please select at least one attribute for fixture type '{fixture_type}' "
                    f"which has {matched_count} matched fixtures."
                )
                return False
        
        return True
    
    def accept(self):
        """Accept the dialog if selections are valid."""
        if self.validate_selections():
            super().accept() 

    def load_existing_selections(self):
        """Load existing attribute selections into the dialog."""
        if not self.existing_fixture_type_attributes:
            return
            
        for fixture_type, selected_attributes in self.existing_fixture_type_attributes.items():
            if fixture_type in self.fixture_type_controls:
                controls = self.fixture_type_controls[fixture_type]
                checkboxes = controls['checkboxes']
                
                # Check the previously selected attributes
                for attr_name in selected_attributes:
                    if attr_name in checkboxes:
                        checkboxes[attr_name].setChecked(True) 