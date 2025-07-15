"""
Simple settings dialog.
Allows users to configure application settings.
"""

from typing import List, Dict, Any
from pathlib import Path
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QFileDialog, QGroupBox, QGridLayout, QLineEdit, QSpinBox,
    QComboBox, QCheckBox
)
from PyQt6.QtCore import Qt


class SettingsDialog(QDialog):
    """Simple dialog for application settings."""
    
    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.config = config
        
        self.setWindowTitle("Settings")
        self.setMinimumSize(500, 400)
        
        self._setup_ui()
        self._load_settings()
    
    def _setup_ui(self):
        """Set up the user interface."""
        layout = QVBoxLayout(self)
        
        # GDTF Settings
        gdtf_group = QGroupBox("GDTF Settings")
        gdtf_layout = QGridLayout(gdtf_group)
        
        gdtf_layout.addWidget(QLabel("External GDTF Folder:"), 0, 0)
        self.gdtf_folder_edit = QLineEdit()
        self.gdtf_browse_button = QPushButton("Browse...")
        self.gdtf_browse_button.clicked.connect(self._browse_gdtf_folder)
        
        gdtf_layout.addWidget(self.gdtf_folder_edit, 0, 1)
        gdtf_layout.addWidget(self.gdtf_browse_button, 0, 2)
        
        layout.addWidget(gdtf_group)
        
        # Export Settings
        export_group = QGroupBox("Export Settings")
        export_layout = QGridLayout(export_group)
        
        export_layout.addWidget(QLabel("Default Export Format:"), 0, 0)
        self.export_format_combo = QComboBox()
        self.export_format_combo.addItems(['text', 'csv', 'json', 'ma3_xml'])
        export_layout.addWidget(self.export_format_combo, 0, 1)
        
        export_layout.addWidget(QLabel("Sequence Start Number:"), 1, 0)
        self.sequence_start_spin = QSpinBox()
        self.sequence_start_spin.setRange(1, 9999)
        export_layout.addWidget(self.sequence_start_spin, 1, 1)
        
        export_layout.addWidget(QLabel("Auto-save Results:"), 2, 0)
        self.auto_save_check = QCheckBox()
        export_layout.addWidget(self.auto_save_check, 2, 1)
        
        export_layout.addWidget(QLabel("Output Directory:"), 3, 0)
        self.output_dir_edit = QLineEdit()
        self.output_browse_button = QPushButton("Browse...")
        self.output_browse_button.clicked.connect(self._browse_output_dir)
        
        export_layout.addWidget(self.output_dir_edit, 3, 1)
        export_layout.addWidget(self.output_browse_button, 3, 2)
        
        layout.addWidget(export_group)
        
        # MA3 XML Settings
        ma3_group = QGroupBox("MA3 XML Settings")
        ma3_layout = QGridLayout(ma3_group)
        
        ma3_layout.addWidget(QLabel("Trigger On Value:"), 0, 0)
        self.trigger_on_spin = QSpinBox()
        self.trigger_on_spin.setRange(0, 255)
        ma3_layout.addWidget(self.trigger_on_spin, 0, 1)
        
        ma3_layout.addWidget(QLabel("Trigger Off Value:"), 1, 0)
        self.trigger_off_spin = QSpinBox()
        self.trigger_off_spin.setRange(0, 255)
        ma3_layout.addWidget(self.trigger_off_spin, 1, 1)
        
        ma3_layout.addWidget(QLabel("Output Range (From):"), 2, 0)
        self.out_from_spin = QSpinBox()
        self.out_from_spin.setRange(0, 100)
        self.out_from_spin.setSuffix("%")
        ma3_layout.addWidget(self.out_from_spin, 2, 1)
        
        ma3_layout.addWidget(QLabel("Output Range (To):"), 3, 0)
        self.out_to_spin = QSpinBox()
        self.out_to_spin.setRange(0, 100)
        self.out_to_spin.setSuffix("%")
        ma3_layout.addWidget(self.out_to_spin, 3, 1)
        
        layout.addWidget(ma3_group)
        
        # Dialog buttons
        button_layout = QHBoxLayout()
        self.ok_button = QPushButton("OK")
        self.cancel_button = QPushButton("Cancel")
        self.reset_button = QPushButton("Reset to Defaults")
        
        self.ok_button.clicked.connect(self._save_and_close)
        self.cancel_button.clicked.connect(self.reject)
        self.reset_button.clicked.connect(self._reset_defaults)
        
        button_layout.addWidget(self.reset_button)
        button_layout.addStretch()
        button_layout.addWidget(self.ok_button)
        button_layout.addWidget(self.cancel_button)
        layout.addLayout(button_layout)
    
    def _load_settings(self):
        """Load current settings into UI."""
        # GDTF settings
        self.gdtf_folder_edit.setText(self.config.get_external_gdtf_folder())
        
        # Export settings
        self.export_format_combo.setCurrentText(self.config.get_output_format())
        self.sequence_start_spin.setValue(self.config.get_sequence_start_number())
        self.auto_save_check.setChecked(self.config.get_save_results())
        self.output_dir_edit.setText(self.config.get_output_directory())
        
        # MA3 settings
        ma3_config = self.config.get_ma3_xml_config()
        self.trigger_on_spin.setValue(ma3_config.get('trigger_on', 255))
        self.trigger_off_spin.setValue(ma3_config.get('trigger_off', 0))
        self.out_from_spin.setValue(int(ma3_config.get('out_from', 0)))
        self.out_to_spin.setValue(int(ma3_config.get('out_to', 100)))
    
    def _browse_gdtf_folder(self):
        """Browse for GDTF folder."""
        folder = QFileDialog.getExistingDirectory(
            self,
            "Select GDTF Folder",
            self.gdtf_folder_edit.text()
        )
        
        if folder:
            self.gdtf_folder_edit.setText(folder)
    
    def _browse_output_dir(self):
        """Browse for output directory."""
        folder = QFileDialog.getExistingDirectory(
            self,
            "Select Output Directory",
            self.output_dir_edit.text()
        )
        
        if folder:
            self.output_dir_edit.setText(folder)
    
    def _save_and_close(self):
        """Save settings and close dialog."""
        # Save GDTF settings
        self.config.set_external_gdtf_folder(self.gdtf_folder_edit.text())
        
        # Save export settings
        self.config.set_output_format(self.export_format_combo.currentText())
        self.config.set_sequence_start_number(self.sequence_start_spin.value())
        self.config.set_save_results(self.auto_save_check.isChecked())
        self.config.set_output_directory(self.output_dir_edit.text())
        
        # Save MA3 settings
        ma3_config = {
            'trigger_on': self.trigger_on_spin.value(),
            'trigger_off': self.trigger_off_spin.value(),
            'in_from': 0,
            'in_to': 255,
            'out_from': float(self.out_from_spin.value()),
            'out_to': float(self.out_to_spin.value()),
            'resolution': '16bit'
        }
        self.config.set_ma3_xml_config(ma3_config)
        
        self.accept()
    
    def _reset_defaults(self):
        """Reset all settings to defaults."""
        # Reset UI to defaults
        self.gdtf_folder_edit.setText("")
        self.export_format_combo.setCurrentText("text")
        self.sequence_start_spin.setValue(1001)
        self.auto_save_check.setChecked(True)
        self.output_dir_edit.setText("output")
        self.trigger_on_spin.setValue(255)
        self.trigger_off_spin.setValue(0)
        self.out_from_spin.setValue(0)
        self.out_to_spin.setValue(100) 