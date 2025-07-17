"""
Dialog for configuring renumber sequences settings.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QSpinBox, 
    QCheckBox, QDialogButtonBox, QGroupBox, QFormLayout
)
from PyQt6.QtCore import Qt
from typing import Dict, Any


class RenumberSequencesDialog(QDialog):
    """Dialog for configuring renumber sequences settings."""
    
    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.config = config
        self.setWindowTitle("Renumber Sequences")
        self.setModal(True)
        self.setFixedSize(400, 300)
        
        self._setup_ui()
        self._load_current_settings()
    
    def _setup_ui(self):
        """Set up the user interface."""
        layout = QVBoxLayout(self)
        
        # Settings group
        settings_group = QGroupBox("Renumber Settings")
        settings_layout = QFormLayout(settings_group)
        
        # Start number
        self.start_number_spin = QSpinBox()
        self.start_number_spin.setRange(1, 99999)
        self.start_number_spin.setValue(1001)
        self.start_number_spin.setToolTip("Starting sequence number for renumbering")
        settings_layout.addRow("Start Number:", self.start_number_spin)
        
        # Interval
        self.interval_spin = QSpinBox()
        self.interval_spin.setRange(1, 100)
        self.interval_spin.setValue(1)
        self.interval_spin.setToolTip("Number of sequences to increment between each attribute")
        settings_layout.addRow("Interval:", self.interval_spin)
        
        # Add breaks checkbox
        self.add_breaks_checkbox = QCheckBox("Add breaks after all attributes for each fixture")
        self.add_breaks_checkbox.setToolTip("Add a gap in sequence numbers after all attributes of each fixture are completed")
        settings_layout.addRow("", self.add_breaks_checkbox)
        
        # Break sequences
        self.break_sequences_spin = QSpinBox()
        self.break_sequences_spin.setRange(1, 50)
        self.break_sequences_spin.setValue(5)
        self.break_sequences_spin.setToolTip("Number of sequences to skip for breaks")
        settings_layout.addRow("Break Sequences:", self.break_sequences_spin)
        
        # Enable/disable break sequences based on checkbox
        self.add_breaks_checkbox.toggled.connect(self.break_sequences_spin.setEnabled)
        
        layout.addWidget(settings_group)
        
        # Dialog buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
    
    def _load_current_settings(self):
        """Load current settings from config."""
        renumber_config = self.config.get_renumber_sequences_config()
        
        self.start_number_spin.setValue(renumber_config.get("start_number", 1001))
        self.interval_spin.setValue(renumber_config.get("interval", 1))
        self.add_breaks_checkbox.setChecked(renumber_config.get("add_breaks", False))
        self.break_sequences_spin.setValue(renumber_config.get("break_sequences", 5))
        
        # Set initial enabled state
        self.break_sequences_spin.setEnabled(self.add_breaks_checkbox.isChecked())
    
    def get_settings(self) -> Dict[str, Any]:
        """Get the current settings from the dialog."""
        return {
            "start_number": self.start_number_spin.value(),
            "interval": self.interval_spin.value(),
            "add_breaks": self.add_breaks_checkbox.isChecked(),
            "break_sequences": self.break_sequences_spin.value()
        }
    
    def accept(self):
        """Save settings and accept the dialog."""
        settings = self.get_settings()
        self.config.set_renumber_sequences_config(settings)
        super().accept() 