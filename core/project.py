"""
Project management for AttributeAddresser.
Handles saving and loading complete project state including fixtures, settings, and external files.
"""

import json
import shutil
import uuid
import zipfile
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
from datetime import datetime

import core


class ProjectManager:
    """Manages saving and loading complete project state."""
    
    def __init__(self):
        self.project_version = 2.0
        self.project_file_name = "project.json"
        self.files_folder_name = "project_files"
        self.project_extension = ".aa"

    def save_project(self, project_path: Path, app_state: Dict[str, Any], config: Any) -> bool:
        """Save complete project state to a .aa zip file."""
        try:
            # Ensure the project path has .aa extension
            if not project_path.suffix.lower() == self.project_extension:
                project_path = project_path.with_suffix(self.project_extension)
            
            # Create temporary directory for project files
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                
                # Create files subdirectory
                files_path = temp_path / self.files_folder_name
                files_path.mkdir(exist_ok=True)
                
                # Build project data structure
                project_data = self._build_project_data(app_state, config, files_path)
                
                # Save project JSON
                project_file = temp_path / self.project_file_name
                with open(project_file, "w", encoding="utf-8") as f:
                    json.dump(project_data, f, indent=2, ensure_ascii=False)
                
                # Create zip file
                with zipfile.ZipFile(project_path, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                    # Add all files from temp directory to zip
                    for file_path in temp_path.rglob('*'):
                        if file_path.is_file():
                            # Calculate relative path within zip
                            relative_path = file_path.relative_to(temp_path)
                            zip_file.write(file_path, relative_path)
            
            return True
        except Exception as e:
            print(f"Error saving project: {e}")
            return False

    def load_project(self, project_path: Path) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
        """Load complete project state from a .aa zip file."""
        try:
            # Validate file extension
            if not project_path.suffix.lower() == self.project_extension:
                return None, None
            
            # Create temporary directory for extraction
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                
                # Extract zip file
                with zipfile.ZipFile(project_path, 'r') as zip_file:
                    zip_file.extractall(temp_path)
                
                # Load project JSON
                project_file = temp_path / self.project_file_name
                if not project_file.exists():
                    return None, None
                
                with open(project_file, "r", encoding="utf-8") as f:
                    project_data = json.load(f)
                
                # Validate project version
                if project_data.get("version") != self.project_version:
                    print(f"Warning: Project version mismatch. Expected {self.project_version}, got {project_data.get('version')}")
                
                app_state = project_data.get("app_state", {})
                config_data = project_data.get("config", {})
                
                # Deserialize app_state to restore GDTFProfileModel objects
                deserialized_app_state = self._deserialize_app_state(app_state)
                
                return deserialized_app_state, config_data
                
        except Exception as e:
            print(f"Error loading project: {e}")
            return None, None

    def _build_project_data(self, app_state: Dict[str, Any], config: Any, files_path: Path) -> Dict[str, Any]:
        """Build complete project data structure."""
        # Preprocess app_state to convert GDTFProfileModel objects to dictionaries
        serialized_app_state = self._serialize_app_state(app_state)
        
        project_data = {
            "version": self.project_version,
            "created": datetime.now().isoformat(),
            "modified": datetime.now().isoformat(),
            "project_id": str(uuid.uuid4()),
            "app_state": serialized_app_state,
            "config": self._serialize_config(config),
            "external_files": self._copy_external_files(config, files_path),
            "table_states": self._capture_table_states(),
            "dialog_states": self._capture_dialog_states()
        }
        return project_data

    def _serialize_app_state(self, app_state: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively serialize app_state, converting GDTFProfileModel objects to dictionaries."""
        if not isinstance(app_state, dict):
            return app_state
        
        serialized = {}
        for key, value in app_state.items():
            if key == 'fixtures' and isinstance(value, list):
                # Special handling for fixtures list
                serialized[key] = [self._serialize_fixture(fixture) for fixture in value]
            else:
                serialized[key] = self._serialize_value(value)
        
        return serialized
    
    def _serialize_fixture(self, fixture: Dict[str, Any]) -> Dict[str, Any]:
        """Serialize a single fixture, converting GDTFProfileModel to dictionary."""
        if not isinstance(fixture, dict):
            return fixture
        
        serialized_fixture = {}
        for key, value in fixture.items():
            if key == 'gdtf_profile' and hasattr(value, 'to_dict'):
                # Convert GDTFProfileModel to dictionary
                serialized_fixture[key] = value.to_dict()
            else:
                serialized_fixture[key] = self._serialize_value(value)
        
        return serialized_fixture
    
    def _serialize_value(self, value: Any) -> Any:
        """Serialize a single value, handling GDTFProfileModel objects."""
        if hasattr(value, 'to_dict') and callable(getattr(value, 'to_dict')):
            # Convert objects with to_dict method to dictionaries
            return value.to_dict()
        elif isinstance(value, dict):
            return {k: self._serialize_value(v) for k, v in value.items()}
        elif isinstance(value, list):
            return [self._serialize_value(item) for item in value]
        else:
            return value

    def _serialize_config(self, config: Any) -> Dict[str, Any]:
        """Serialize configuration object to dictionary."""
        config_data = {}
        config_methods = [
            "get_external_gdtf_folder",
            "get_selected_attributes",
            "get_sequence_start_number",
            "get_output_format",
            "get_ma3_xml_config",
            "get_last_export_directory"
        ]
        for method_name in config_methods:
            if hasattr(config, method_name):
                try:
                    method = getattr(config, method_name)
                    if callable(method):
                        config_data[method_name] = method()
                except Exception as e:
                    print(f"Warning: Could not serialize config method {method_name}: {e}")
        
        # Add fixture type attributes if needed
        config_data['fixture_type_attributes'] = {}
        return config_data

    def _copy_external_files(self, config: Any, files_path: Path) -> Dict[str, str]:
        """Copy external files to project directory and return mapping."""
        external_files = {}
        
        # Copy GDTF profiles
        gdtf_folder = getattr(config, "get_external_gdtf_folder", lambda: None)()
        if gdtf_folder and Path(gdtf_folder).exists():
            gdtf_files = list(Path(gdtf_folder).glob("*.gdtf"))
            for gdtf_file in gdtf_files:
                dest_path = files_path / f"gdtf_{gdtf_file.name}"
                shutil.copy2(gdtf_file, dest_path)
                external_files[f"gdtf_{gdtf_file.name}"] = str(gdtf_file)
        
        # Copy any other external files (MVR, CSV, etc.)
        # This would be expanded based on what files are currently loaded
        
        return external_files

    def _capture_table_states(self) -> Dict[str, Any]:
        """Capture current table states."""
        # This would capture table selections, sorting, etc.
        # For now, return empty dict - will be implemented when we have table references
        return {}

    def _capture_dialog_states(self) -> Dict[str, Any]:
        """Capture current dialog states."""
        # This would capture any open dialogs and their states
        # For now, return empty dict - will be implemented when we have dialog references
        return {}

    def get_project_info(self, project_path: Path) -> Optional[Dict[str, Any]]:
        """Get basic project information without loading the full project."""
        try:
            # Validate file extension
            if not project_path.suffix.lower() == self.project_extension:
                return None
            
            # Create temporary directory for extraction
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                
                # Extract zip file
                with zipfile.ZipFile(project_path, 'r') as zip_file:
                    zip_file.extractall(temp_path)
                
                # Load project JSON
                project_file = temp_path / self.project_file_name
                if not project_file.exists():
                    return None
                
                with open(project_file, "r", encoding="utf-8") as f:
                    project_data = json.load(f)
                
                return {
                    "name": project_path.stem,  # Name without extension
                    "version": project_data.get("version"),
                    "created": project_data.get("created"),
                    "modified": project_data.get("modified"),
                    "fixture_count": len(project_data.get("app_state", {}).get("fixtures", [])),
                    "path": str(project_path)
                }
                
        except Exception as e:
            print(f"Error reading project info: {e}")
            return None

    def _deserialize_app_state(self, app_state: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively deserialize app_state, converting dictionaries back to GDTFProfileModel objects."""
        if not isinstance(app_state, dict):
            return app_state
        
        deserialized = {}
        for key, value in app_state.items():
            if key == 'fixtures' and isinstance(value, list):
                # Special handling for fixtures list
                deserialized[key] = [self._deserialize_fixture(fixture) for fixture in value]
            else:
                deserialized[key] = self._deserialize_value(value)
        
        return deserialized
    
    def _deserialize_fixture(self, fixture: Dict[str, Any]) -> Dict[str, Any]:
        """Deserialize a single fixture, converting dictionary back to GDTFProfileModel."""
        if not isinstance(fixture, dict):
            return fixture
        
        deserialized_fixture = {}
        for key, value in fixture.items():
            if key == 'gdtf_profile' and isinstance(value, dict):
                # Convert dictionary back to GDTFProfileModel
                try:
                    from core.data import GDTFProfileModel
                    deserialized_fixture[key] = GDTFProfileModel.from_dict(value)
                except Exception as e:
                    print(f"Warning: Could not deserialize GDTFProfileModel: {e}")
                    deserialized_fixture[key] = value
            else:
                deserialized_fixture[key] = self._deserialize_value(value)
        
        return deserialized_fixture
    
    def _deserialize_value(self, value: Any) -> Any:
        """Deserialize a single value, handling GDTFProfileModel dictionaries."""
        if isinstance(value, dict):
            # Check if this looks like a GDTFProfileModel dictionary
            if 'name' in value and 'mode' in value and 'channels' in value:
                try:
                    from core.data import GDTFProfileModel
                    return GDTFProfileModel.from_dict(value)
                except Exception as e:
                    print(f"Warning: Could not deserialize GDTFProfileModel: {e}")
                    return {k: self._deserialize_value(v) for k, v in value.items()}
            else:
                return {k: self._deserialize_value(v) for k, v in value.items()}
        elif isinstance(value, list):
            return [self._deserialize_value(item) for item in value]
        else:
            return value


# Global project manager instance
project_manager = ProjectManager() 