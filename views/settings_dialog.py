"""
Settings Dialog - Configuration dialog for general application preferences.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel, 
    QPushButton, QGroupBox, QSpinBox, QMessageBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from config import Config


class SettingsDialog(QDialog):
    """
    Dialog for configuring general application settings.
    """
    
    def __init__(self, parent, config: Config):
        super().__init__(parent)
        self.config = config
        self.setup_ui()
        self.load_current_settings()
    
    def setup_ui(self):
        """Create the dialog interface."""
        self.setWindowTitle("Application Settings")
        self.setGeometry(200, 200, 400, 300)
        
        layout = QVBoxLayout(self)
        
        # Title
        title = QLabel("Application Settings")
        title.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        layout.addWidget(title)
        
        # Sequence numbering group
        sequence_group = QGroupBox("Sequence Numbering")
        sequence_layout = QFormLayout(sequence_group)
        
        # Sequence start number setting
        self.sequence_start_spin = QSpinBox()
        self.sequence_start_spin.setRange(1, 99999)
        self.sequence_start_spin.setValue(1)
        self.sequence_start_spin.setToolTip("Starting number for global sequence numbering of fixture attributes")
        
        sequence_layout.addRow("Starting sequence number:", self.sequence_start_spin)
        
        # Add description
        description = QLabel(
            "The sequence number is assigned to each master fixture attribute globally.\n"
            "For example, starting at 1: Fixture1-Dim=#1, Fixture1-R=#2, Fixture2-Dim=#3, etc.\n"
            "This number appears in exports and in the table display."
        )
        description.setWordWrap(True)
        description.setStyleSheet("color: #666; font-style: italic; margin-top: 10px;")
        sequence_layout.addRow(description)
        
        layout.addWidget(sequence_group)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        # Reset to defaults button
        reset_btn = QPushButton("Reset to Defaults")
        reset_btn.clicked.connect(self.reset_to_defaults)
        button_layout.addWidget(reset_btn)
        
        button_layout.addStretch()
        
        # Dialog controls
        ok_btn = QPushButton("Save Settings")
        ok_btn.setDefault(True)
        ok_btn.clicked.connect(self.accept)
        button_layout.addWidget(ok_btn)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
    
    def load_current_settings(self):
        """Load current settings from config."""
        sequence_start = self.config.get_sequence_start_number()
        self.sequence_start_spin.setValue(sequence_start)
    
    def reset_to_defaults(self):
        """Reset all settings to their default values."""
        self.sequence_start_spin.setValue(1)
    
    def accept(self):
        """Save settings and close dialog."""
        try:
            # Save sequence start number
            sequence_start = self.sequence_start_spin.value()
            self.config.set_sequence_start_number(sequence_start)
            
            # Show success message
            QMessageBox.information(
                self, 
                "Settings Saved", 
                f"Settings have been saved successfully.\n\n"
                f"Sequence numbering will start at: {sequence_start}"
            )
            
            super().accept()
            
        except Exception as e:
            QMessageBox.critical(
                self, 
                "Error Saving Settings", 
                f"Failed to save settings:\n{str(e)}"
            )
    
    def get_sequence_start_number(self) -> int:
        """Get the configured sequence start number."""
        return self.sequence_start_spin.value() 