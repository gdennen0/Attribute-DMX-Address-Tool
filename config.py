"""
Configuration management for MVR File Analyzer.
Handles saving and loading user preferences.
"""

import json
import os
from pathlib import Path
from typing import List, Dict


class Config:
    """Simple configuration manager for the MVR analyzer."""
    
    def __init__(self, config_file: str = "config.json"):
        self.config_file = Path(config_file)
        self.config = self._load_config()
    
    def _load_config(self) -> dict:
        """Load configuration from file or create default."""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading config: {e}")
        
        # Default configuration
        return {
            "selected_attributes": [],  # Legacy - kept for backward compatibility
            "fixture_type_attributes": {},  # New: per-fixture-type attributes
            "output_format": "text",
            "save_results": True,
            "output_directory": "output",
            "last_mvr_directory": "",
            "last_export_directory": "",
            "last_gdtf_directory": "",
            "last_csv_directory": "",  # New: last used CSV directory
            "external_gdtf_folder": "",
            "ma3_xml_config": {
                "trigger_on": 255,
                "trigger_off": 0,
                "in_from": 0,
                "in_to": 255,
                "out_from": 0.0,
                "out_to": 100.0,
                "resolution": "16bit"
            },
            "available_attributes": [
                "Dim", "R", "G", "B", "W", "WW", "CW", "A", "UV", "Lime", "Cyan", "Magenta", "Yellow",
                "Pan", "Tilt", "Zoom", "Focus", "Iris", "Gobo1", "Gobo2", "Color1", "Color2", 
                "Prism", "Frost", "Shutter", "Strobe"
            ],
            "sequence_start_number": 1001
        }
    
    def save_config(self):
        """Save current configuration to file."""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=2)
        except Exception as e:
            print(f"Error saving config: {e}")
    
    def get_selected_attributes(self) -> List[str]:
        """Get list of selected attributes (legacy method for backward compatibility)."""
        return self.config.get("selected_attributes", [])
    
    def set_selected_attributes(self, attributes: List[str]):
        """Set selected attributes and save config (legacy method for backward compatibility)."""
        self.config["selected_attributes"] = attributes
        self.save_config()
    
    def get_fixture_type_attributes(self) -> Dict[str, List[str]]:
        """Get per-fixture-type attributes."""
        return self.config.get("fixture_type_attributes", {})
    
    def set_fixture_type_attributes(self, fixture_type_attributes: Dict[str, List[str]]):
        """Set per-fixture-type attributes and save config."""
        self.config["fixture_type_attributes"] = fixture_type_attributes
        self.save_config()
    
    def get_output_format(self) -> str:
        """Get output format."""
        return self.config.get("output_format", "text")
    
    def set_output_format(self, format_type: str):
        """Set output format and save config."""
        self.config["output_format"] = format_type
        self.save_config()
    
    def get_save_results(self) -> bool:
        """Get save results setting."""
        return self.config.get("save_results", True)
    
    def set_save_results(self, save: bool):
        """Set save results setting and save config."""
        self.config["save_results"] = save
        self.save_config()
    
    def get_output_directory(self) -> str:
        """Get output directory."""
        return self.config.get("output_directory", "output")
    
    def set_output_directory(self, directory: str):
        """Set output directory and save config."""
        self.config["output_directory"] = directory
        self.save_config()
    
    def get_last_mvr_directory(self) -> str:
        """Get last used MVR directory."""
        return self.config.get("last_mvr_directory", "")
    
    def set_last_mvr_directory(self, directory: str):
        """Set last used MVR directory and save config."""
        self.config["last_mvr_directory"] = directory
        self.save_config()
    
    def get_last_export_directory(self) -> str:
        """Get last used export directory."""
        return self.config.get("last_export_directory", "")
    
    def set_last_export_directory(self, directory: str):
        """Set last used export directory and save config."""
        self.config["last_export_directory"] = directory
        self.save_config()
    
    def get_last_gdtf_directory(self) -> str:
        """Get last used GDTF directory."""
        return self.config.get("last_gdtf_directory", "")
    
    def set_last_gdtf_directory(self, directory: str):
        """Set last used GDTF directory and save config."""
        self.config["last_gdtf_directory"] = directory
        self.save_config()
    
    def get_last_csv_directory(self) -> str:
        """Get last used CSV directory."""
        return self.config.get("last_csv_directory", "")
    
    def set_last_csv_directory(self, directory: str):
        """Set last used CSV directory and save config."""
        self.config["last_csv_directory"] = directory
        self.save_config()
    
    def get_external_gdtf_folder(self) -> str:
        """Get external GDTF folder path."""
        return self.config.get("external_gdtf_folder", "")
    
    def set_external_gdtf_folder(self, folder_path: str):
        """Set external GDTF folder path and save config."""
        self.config["external_gdtf_folder"] = folder_path
        self.save_config()
    
    def get_ma3_xml_config(self) -> dict:
        """Get MA3 XML configuration."""
        default_config = {
            "trigger_on": 255,
            "trigger_off": 0,
            "in_from": 0,
            "in_to": 255,
            "out_from": 0.0,
            "out_to": 100.0,
            "resolution": "16bit"
        }
        return self.config.get("ma3_xml_config", default_config)
    
    def set_ma3_xml_config(self, ma3_config: dict):
        """Set MA3 XML configuration and save config."""
        self.config["ma3_xml_config"] = ma3_config
        self.save_config()
    
    def get_available_attributes(self) -> List[str]:
        """Get list of available attributes for quick selection."""
        return self.config.get("available_attributes", [
            "Dim", "R", "G", "B", "W", "WW", "CW", "A", "UV", "Lime", "Cyan", "Magenta", "Yellow",
            "Pan", "Tilt", "Zoom", "Focus", "Iris", "Gobo1", "Gobo2", "Color1", "Color2", 
            "Prism", "Frost", "Shutter", "Strobe"
        ])

    def get_sequence_start_number(self) -> int:
        """Get the starting number for sequence numbering."""
        return self.config.get("sequence_start_number", 1)
    
    def set_sequence_start_number(self, start_number: int):
        """Set the starting number for sequence numbering and save config."""
        self.config["sequence_start_number"] = start_number
        self.save_config() 