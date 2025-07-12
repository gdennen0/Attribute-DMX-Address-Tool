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
            "last_gdtf_directory": ""
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
    
    def get_available_attributes(self) -> List[str]:
        """Get list of commonly found MVR attributes (legacy method for backward compatibility)."""
        return [
            "Position X", "Position Y", "Position Z",
            "Rotation X", "Rotation Y", "Rotation Z",
            "Scale X", "Scale Y", "Scale Z",
            "Color", "Intensity", "Dimmer",
            "Pan", "Tilt", "Focus",
            "Gobo", "Prism", "Iris",
            "Shutter", "Speed", "Mode",
            "Address", "Universe", "Channel"
        ] 