"""
Controller for Attribute Selection Dialog.
Handles business logic for fixture selection and GDTF matching after import.
"""

from typing import Dict, List, Any, Optional
from pathlib import Path
import os
import zipfile
import xml.etree.ElementTree as ET
import io

import core

class GDTFMode:
    def __init__(self, name, channels, activation_groups=None, total_channels=0):
        self.name = name
        self.channels = channels
        self.activation_groups = activation_groups or {}
        self.total_channels = total_channels or len(channels)

class GDTFProfile:
    def __init__(self, name, modes):
        self.name = name
        self.modes = modes  # Dict[str, GDTFMode]
    def get_mode_names(self):
        return list(self.modes.keys())
    def get_mode(self, mode_name):
        return self.modes.get(mode_name)

class AttributeSelectionController:
    """
    Controller for the Attribute Selection Dialog.
    Handles fixture type grouping, GDTF matching, and configuration management.
    """
    
    def __init__(self, config):
        self.config = config
        self.fixtures = []
        self.gdtf_profiles = {}  # profile_name -> GDTFProfile
        self.fixture_type_matches = {}
        self.external_gdtf_folder = None
        
    def set_fixtures(self, fixtures: List[Dict[str, Any]]):
        """Set the fixtures to work with (only selected fixtures from import)."""
        self.fixtures = fixtures
        
    def get_fixture_types_from_selected(self) -> Dict[str, Dict]:
        """Get fixture type information from selected fixtures only."""
        if not self.fixtures:
            return {}
        
        # Group by fixture type
        fixture_types = {}
        for fixture in self.fixtures:
            fixture_type = fixture.get('type', 'Unknown')
            # Remove .gdtf extension for consistent naming
            fixture_type_clean = fixture_type.replace('.gdtf', '') if fixture_type.endswith('.gdtf') else fixture_type
            
            if fixture_type_clean not in fixture_types:
                fixture_types[fixture_type_clean] = {
                    'count': 0,
                    'sample_names': [],
                    'fixtures': [],
                    'matched_count': 0,
                    'current_match': None
                }
            
            fixture_types[fixture_type_clean]['count'] += 1
            fixture_types[fixture_type_clean]['fixtures'].append(fixture)
            
            # Track matched fixtures and get current match info
            if fixture.get('matched'):
                fixture_types[fixture_type_clean]['matched_count'] += 1
                if fixture_types[fixture_type_clean]['current_match'] is None:
                    fixture_types[fixture_type_clean]['current_match'] = {
                        'profile': fixture.get('gdtf_profile_name'),
                        'mode': fixture.get('mode')
                    }
            
            # Add sample names (up to 5)
            if len(fixture_types[fixture_type_clean]['sample_names']) < 5:
                fixture_types[fixture_type_clean]['sample_names'].append(fixture.get('name', ''))
        
        return fixture_types
    
    def load_external_gdtf_profiles(self, folder_path: str) -> Dict[str, Any]:
        """Load external GDTF profiles from the specified folder."""
        try:
            if not os.path.exists(folder_path):
                return {
                    "success": False,
                    "error": f"Folder does not exist: {folder_path}"
                }
            # Parse external GDTF profiles
            loaded_profiles = {}
            for file in Path(folder_path).glob("*.gdtf"):
                profile = self._load_gdtf_from_file(file)
                if profile:
                    loaded_profiles[profile.name] = profile
            if loaded_profiles:
                self.gdtf_profiles.update(loaded_profiles)
                self.external_gdtf_folder = folder_path
                self.config.set_external_gdtf_folder(folder_path)
                self.config.set_last_gdtf_directory(folder_path)
                return {
                    "success": True,
                    "profiles_loaded": len(loaded_profiles),
                    "total_profiles": len(self.gdtf_profiles)
                }
            else:
                return {
                    "success": False,
                    "error": "No GDTF profiles found in the specified folder"
                }
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to load GDTF profiles: {str(e)}"
            }
    def _load_gdtf_from_file(self, gdtf_file: Path) -> Optional[GDTFProfile]:
        try:
            with zipfile.ZipFile(gdtf_file, 'r') as gdtf_archive:
                if 'description.xml' not in gdtf_archive.namelist():
                    return None
                with gdtf_archive.open('description.xml') as desc_file:
                    content = desc_file.read().decode('utf-8')
                    return self._parse_gdtf_xml(content, gdtf_file.name)
        except Exception as e:
            print(f"Error loading GDTF from file: {e}")
            return None
    def _parse_gdtf_xml(self, xml_content: str, filename: str) -> Optional[GDTFProfile]:
        try:
            root = ET.fromstring(xml_content)
            profile_name = filename.replace('.gdtf', '')
            modes = {}
            fixture_type = root.find('FixtureType')
            if fixture_type is not None:
                dmx_modes_parent = fixture_type.find('DMXModes')
                if dmx_modes_parent is not None:
                    for mode_elem in dmx_modes_parent.findall('DMXMode'):
                        mode_name = mode_elem.get('Name', '')
                        if not mode_name:
                            continue
                        channels = {}
                        activation_groups = {}
                        dmx_channels_elem = mode_elem.find('DMXChannels')
                        if dmx_channels_elem is not None:
                            dmx_channel_elements = dmx_channels_elem.findall('DMXChannel')
                            for dmx_channel_elem in dmx_channel_elements:
                                offset_str = dmx_channel_elem.get('Offset', '')
                                if not offset_str:
                                    continue
                                offset_parts = offset_str.split(',')
                                if offset_parts:
                                    try:
                                        channel_offset = int(offset_parts[0])
                                    except ValueError:
                                        continue
                                logical_channel = dmx_channel_elem.find('LogicalChannel')
                                if logical_channel is not None:
                                    attribute_name, activation_group = self._extract_attribute_info_from_logical_channel(logical_channel, root)
                                    if attribute_name and attribute_name != "NoFeature":
                                        channels[attribute_name] = channel_offset
                                        activation_groups[attribute_name] = activation_group
                        gdtf_mode = GDTFMode(
                            name=mode_name,
                            channels=channels,
                            activation_groups=activation_groups,
                            total_channels=len(channels)
                        )
                        modes[mode_name] = gdtf_mode
            return GDTFProfile(name=profile_name, modes=modes)
        except ET.ParseError as e:
            print(f"Error parsing GDTF XML: {e}")
            return None
    def _extract_attribute_info_from_logical_channel(self, logical_channel_elem, root):
        try:
            attribute_ref = logical_channel_elem.get('Attribute')
            if not attribute_ref:
                return None, None
            for attr_elem in root.findall('.//Attribute'):
                if attr_elem.get('Name') == attribute_ref:
                    attribute_name = attr_elem.get('Pretty', attr_elem.get('Name'))
                    activation_group = attr_elem.get('ActivationGroup')
                    return attribute_name, activation_group
            return attribute_ref, None
        except Exception:
            return None, None
    def get_profiles_by_source(self) -> Dict[str, List[str]]:
        profiles_by_source = {'mvr': [], 'external': []}
        for profile_name in self.gdtf_profiles.keys():
            profiles_by_source['external'].append(profile_name)
        return profiles_by_source
    def get_profile_modes(self, profile_name: str) -> List[str]:
        profile = self.gdtf_profiles.get(profile_name)
        if not profile:
            return []
        return profile.get_mode_names()
    
    def update_fixture_matches(self, fixture_type_matches: Dict[str, Dict[str, str]], fixture_type_attributes: Dict[str, List[str]] = None) -> Dict[str, Any]:
        """Update fixture matches based on user selections and create GDTF profile models."""
        try:
            updated_count = 0
            
            for fixture_type, match_info in fixture_type_matches.items():
                profile_name = match_info.get('profile')
                mode_name = match_info.get('mode')
                
                if profile_name and mode_name:
                    # Get the GDTF profile
                    profile = self.gdtf_profiles.get(profile_name)
                    if not profile:
                        continue
                    
                    # Get selected attributes for this fixture type
                    selected_attributes = []
                    if fixture_type_attributes and fixture_type in fixture_type_attributes:
                        selected_attributes = fixture_type_attributes[fixture_type]
                    
                    # Convert GDTFProfile to dictionary format expected by match_fixture_to_gdtf
                    profile_dict = {
                        'name': profile.name,
                        'modes': {}
                    }
                    
                    for mode_name_key, mode_obj in profile.modes.items():
                        profile_dict['modes'][mode_name_key] = mode_obj.channels
                    
                    # Update all fixtures of this type
                    for fixture in self.fixtures:
                        if fixture.get('type', '').replace('.gdtf', '') == fixture_type:
                            # Use the core match_fixture_to_gdtf function to properly process the fixture
                            import core
                            if core.match_fixture_to_gdtf(fixture, profile_dict, mode_name, selected_attributes):
                                fixture['gdtf_profile_name'] = profile_name
                                # Also set activation groups for the fixture
                                mode_obj = profile.modes.get(mode_name)
                                if mode_obj:
                                    fixture['activation_groups'] = mode_obj.activation_groups
                                updated_count += 1
            
            # Save matches to config for future use
            self.config.set_fixture_type_matches(fixture_type_matches)
            
            return {
                "success": True,
                "updated_count": updated_count
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to update fixture matches: {str(e)}"
            }
    
    def get_saved_fixture_matches(self) -> Dict[str, Dict[str, str]]:
        """Get previously saved fixture type matches from config."""
        return self.config.get_fixture_type_matches()
    
    def get_external_gdtf_folder(self) -> Optional[str]:
        """Get the currently loaded external GDTF folder."""
        return self.external_gdtf_folder or self.config.get_external_gdtf_folder()
    
    def get_match_summary(self) -> Dict[str, Any]:
        """Get a summary of the current matching status."""
        if not self.fixtures:
            return {
                "total": 0,
                "matched": 0,
                "unmatched": 0,
                "match_rate": 0.0
            }
        
        total = len(self.fixtures)
        matched = sum(1 for f in self.fixtures if f.get('matched', False))
        unmatched = total - matched
        match_rate = (matched / total * 100) if total > 0 else 0.0
        
        return {
            "total": total,
            "matched": matched,
            "unmatched": unmatched,
            "match_rate": match_rate
        } 

    def get_available_attributes_for_profile_mode(self, profile_name: str, mode_name: str) -> List[str]:
        profile = self.gdtf_profiles.get(profile_name)
        if not profile:
            return []
        mode = profile.get_mode(mode_name)
        if not mode:
            return []
        return sorted(mode.channels.keys())
    def get_fixture_type_attributes(self) -> Dict[str, List[str]]:
        return self.config.get_fixture_type_attributes()
    def set_fixture_type_attributes(self, fixture_type_attributes: Dict[str, List[str]]):
        self.config.set_fixture_type_attributes(fixture_type_attributes) 