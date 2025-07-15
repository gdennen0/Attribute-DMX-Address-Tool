"""
MA3 XML Configuration Dialog
Allows users to configure parameters for MA3 XML export.
"""

import sys
from typing import Dict, Any

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, 
    QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox, QPushButton, 
    QGroupBox, QMessageBox, QDialogButtonBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont


class MA3XMLDialog(QDialog):
    """Dialog for configuring MA3 XML export parameters."""
    
    def __init__(self, parent=None, config_manager=None):
        super().__init__(parent)
        self.setWindowTitle("MA3 XML Configuration")
        self.setModal(True)
        self.setMinimumWidth(500)
        
        self.config_manager = config_manager
        
        # Load saved configuration or use defaults
        if config_manager:
            self.config = config_manager.get_ma3_xml_config()
        else:
            self.config = {
                "trigger_on": 255,
                "trigger_off": 0,
                "in_from": 0,
                "in_to": 255,
                "out_from": 0.0,
                "out_to": 100.0,
                "resolution": "16bit"
            }
        
        self.setup_ui()
        self.setup_connections()
        
    def setup_ui(self):
        """Setup the user interface."""
        layout = QVBoxLayout(self)
        
        # Title
        title_label = QLabel("Configure MA3 XML Export Parameters")
        title_font = QFont()
        title_font.setBold(True)
        title_font.setPointSize(12)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)
        
        # Description
        desc_label = QLabel("These settings will be applied to all DMX remotes generated from your attributes.\nTrigger values are DMX levels (0-255), output values are percentages (0-100%).")
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("color: #666; margin-bottom: 10px;")
        layout.addWidget(desc_label)
        
        # Trigger Settings Group
        trigger_group = QGroupBox("Trigger Settings (DMX Values)")
        trigger_layout = QGridLayout(trigger_group)
        
        # Trigger On
        trigger_layout.addWidget(QLabel("Trigger On (0-255):"), 0, 0)
        self.trigger_on_spin = QSpinBox()
        self.trigger_on_spin.setRange(0, 255)
        self.trigger_on_spin.setValue(self.config["trigger_on"])
        self.trigger_on_spin.setToolTip("DMX value at which the remote triggers on (will be converted to hex color)")
        trigger_layout.addWidget(self.trigger_on_spin, 0, 1)
        
        # Trigger Off
        trigger_layout.addWidget(QLabel("Trigger Off (0-255):"), 1, 0)
        self.trigger_off_spin = QSpinBox()
        self.trigger_off_spin.setRange(0, 255)
        self.trigger_off_spin.setValue(self.config["trigger_off"])
        self.trigger_off_spin.setToolTip("DMX value at which the remote triggers off (will be converted to hex color)")
        trigger_layout.addWidget(self.trigger_off_spin, 1, 1)
        
        layout.addWidget(trigger_group)
        
        # Input Range Settings Group
        input_group = QGroupBox("Input Range Settings")
        input_layout = QGridLayout(input_group)
        
        # Input From
        input_layout.addWidget(QLabel("Input From (0-255):"), 0, 0)
        self.in_from_spin = QSpinBox()
        self.in_from_spin.setRange(0, 255)
        self.in_from_spin.setValue(self.config["in_from"])
        self.in_from_spin.setToolTip("Minimum input value (will be converted to hex color)")
        input_layout.addWidget(self.in_from_spin, 0, 1)
        
        # Input To
        input_layout.addWidget(QLabel("Input To (0-255):"), 1, 0)
        self.in_to_spin = QSpinBox()
        self.in_to_spin.setRange(0, 255)
        self.in_to_spin.setValue(self.config["in_to"])
        self.in_to_spin.setToolTip("Maximum input value (will be converted to hex color)")
        input_layout.addWidget(self.in_to_spin, 1, 1)
        
        layout.addWidget(input_group)
        
        # Output Range Settings Group
        output_group = QGroupBox("Output Range Settings")
        output_layout = QGridLayout(output_group)
        
        # Output From
        output_layout.addWidget(QLabel("Output From (%):"), 0, 0)
        self.out_from_spin = QDoubleSpinBox()
        self.out_from_spin.setRange(0.0, 100.0)
        self.out_from_spin.setValue(self.config["out_from"])
        self.out_from_spin.setDecimals(1)
        self.out_from_spin.setToolTip("Minimum output percentage")
        output_layout.addWidget(self.out_from_spin, 0, 1)
        
        # Output To
        output_layout.addWidget(QLabel("Output To (%):"), 1, 0)
        self.out_to_spin = QDoubleSpinBox()
        self.out_to_spin.setRange(0.0, 100.0)
        self.out_to_spin.setValue(self.config["out_to"])
        self.out_to_spin.setDecimals(1)
        self.out_to_spin.setToolTip("Maximum output percentage")
        output_layout.addWidget(self.out_to_spin, 1, 1)
        
        layout.addWidget(output_group)
        
        # Resolution Settings Group
        resolution_group = QGroupBox("Resolution Settings")
        resolution_layout = QGridLayout(resolution_group)
        
        resolution_layout.addWidget(QLabel("Resolution:"), 0, 0)
        self.resolution_combo = QComboBox()
        self.resolution_combo.addItems(["8bit", "16bit", "24bit"])
        self.resolution_combo.setCurrentText(self.config["resolution"])
        self.resolution_combo.setToolTip("DMX resolution for the remote")
        resolution_layout.addWidget(self.resolution_combo, 0, 1)
        
        layout.addWidget(resolution_group)
        
        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
    def setup_connections(self):
        """Setup signal connections."""
        # Update config when values change
        self.trigger_on_spin.valueChanged.connect(self.update_config)
        self.trigger_off_spin.valueChanged.connect(self.update_config)
        self.in_from_spin.valueChanged.connect(self.update_config)
        self.in_to_spin.valueChanged.connect(self.update_config)
        self.out_from_spin.valueChanged.connect(self.update_config)
        self.out_to_spin.valueChanged.connect(self.update_config)
        self.resolution_combo.currentTextChanged.connect(self.update_config)
        
    def update_config(self):
        """Update the configuration based on current widget values."""
        self.config = {
            "trigger_on": self.trigger_on_spin.value(),
            "trigger_off": self.trigger_off_spin.value(),
            "in_from": self.in_from_spin.value(),
            "in_to": self.in_to_spin.value(),
            "out_from": self.out_from_spin.value(),
            "out_to": self.out_to_spin.value(),
            "resolution": self.resolution_combo.currentText()
        }
        
    def get_config(self) -> Dict[str, Any]:
        """Get the current configuration."""
        return self.config.copy()
    
    def accept(self):
        """Validate and accept the dialog."""
        # Validate ranges
        if self.trigger_on_spin.value() <= self.trigger_off_spin.value():
            QMessageBox.warning(
                self,
                "Invalid Range",
                "Trigger On DMX value must be greater than Trigger Off DMX value."
            )
            return
            
        if self.in_from_spin.value() >= self.in_to_spin.value():
            QMessageBox.warning(
                self,
                "Invalid Range", 
                "Input From value must be less than Input To value."
            )
            return
            
        if self.out_from_spin.value() >= self.out_to_spin.value():
            QMessageBox.warning(
                self,
                "Invalid Range",
                "Output From value must be less than Output To value."
            )
            return
            
        # Save configuration if config manager is available
        if self.config_manager:
            self.config_manager.set_ma3_xml_config(self.config)
            
        super().accept() 