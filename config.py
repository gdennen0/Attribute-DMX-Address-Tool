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
            "selected_attributes": [],  # Global selected attributes (used for backward compatibility)
            "fixture_type_attributes": {}, 
            "last_mvr_directory": "",
            "last_export_directory": "",
            "last_gdtf_directory": "",
            "last_csv_directory": "",  
            "last_project_directory": "", 
            "recent_projects": [],  
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
            "sequence_start_number": 1001,
            "renumber_sequences_config": {
                "start_number": 1001,
                "interval": 1,
                "add_breaks": False,
                "break_sequences": 5
            }
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
    
    def get_last_project_directory(self) -> str:
        """Get last used project directory."""
        return self.config.get("last_project_directory", "")
    
    def set_last_project_directory(self, directory: str):
        """Set last used project directory and save config."""
        self.config["last_project_directory"] = directory
        self.save_config()
    
    def get_recent_projects(self) -> List[str]:
        """Get list of recent project paths."""
        return self.config.get("recent_projects", [])
    
    def add_recent_project(self, project_path: str):
        """Add a project to recent projects list and save config."""
        recent_projects = self.get_recent_projects()
        
        # Remove if already exists (to move to top)
        if project_path in recent_projects:
            recent_projects.remove(project_path)
        
        # Add to beginning of list
        recent_projects.insert(0, project_path)
        
        # Keep only last 10 projects
        recent_projects = recent_projects[:10]
        
        self.config["recent_projects"] = recent_projects
        self.save_config()
    
    def remove_recent_project(self, project_path: str):
        """Remove a project from recent projects list and save config."""
        recent_projects = self.get_recent_projects()
        if project_path in recent_projects:
            recent_projects.remove(project_path)
            self.config["recent_projects"] = recent_projects
            self.save_config()
    
    def clear_recent_projects(self):
        """Clear all recent projects and save config."""
        self.config["recent_projects"] = []
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
    
    def get_sequence_start_number(self) -> int:
        """Get the starting number for sequence numbering."""
        return self.config.get("sequence_start_number", 1)
    
    def set_sequence_start_number(self, start_number: int):
        """Set the starting number for sequence numbering and save config."""
        self.config["sequence_start_number"] = start_number
        self.save_config()
    
    def get_fixture_type_matches(self) -> Dict[str, Dict[str, str]]:
        """Get saved fixture type matches (profile and mode mappings)."""
        return self.config.get("fixture_type_matches", {})
    
    def set_fixture_type_matches(self, fixture_type_matches: Dict[str, Dict[str, str]]):
        """Set fixture type matches and save config."""
        self.config["fixture_type_matches"] = fixture_type_matches
        self.save_config()
    
    def get_renumber_sequences_config(self) -> dict:
        """Get renumber sequences configuration."""
        default_config = {
            "start_number": 1001,
            "interval": 1,
            "add_breaks": False,
            "break_sequences": 5
        }
        return self.config.get("renumber_sequences_config", default_config)
    
    def set_renumber_sequences_config(self, renumber_config: dict):
        """Set renumber sequences configuration and save config."""
        self.config["renumber_sequences_config"] = renumber_config
        self.save_config() 