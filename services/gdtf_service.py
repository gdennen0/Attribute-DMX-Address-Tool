"""
GDTF Service - Handles all GDTF profile operations.
Clean separation of GDTF business logic.
"""

import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Optional, Any
import io

from models.data_models import GDTFProfile, GDTFMode, FixtureMatch, MatchSummary


class GDTFService:
    """
    Service for handling GDTF profile operations.
    Provides clean interface for GDTF loading, parsing, and matching.
    """
    
    def __init__(self):
        self.profiles: Dict[str, GDTFProfile] = {}
        self.universe_size = 512
    
    def load_profiles_from_mvr(self, mvr_path: str) -> Dict[str, GDTFProfile]:
        """
        Load GDTF profiles from an MVR file.
        
        Args:
            mvr_path: Path to the MVR file
            
        Returns:
            Dictionary of loaded profiles {profile_name: GDTFProfile}
        """
        mvr_file = Path(mvr_path)
        if not mvr_file.exists():
            raise FileNotFoundError(f"MVR file not found: {mvr_path}")
        
        try:
            with zipfile.ZipFile(mvr_file, 'r') as zip_file:
                gdtf_files = [f for f in zip_file.namelist() if f.endswith('.gdtf')]
                
                for gdtf_filename in gdtf_files:
                    try:
                        profile = self._load_gdtf_from_zip(zip_file, gdtf_filename)
                        if profile:
                            self.profiles[profile.name] = profile
                    except Exception as e:
                        print(f"Warning: Could not load GDTF file {gdtf_filename}: {e}")
                        
        except Exception as e:
            raise Exception(f"Error loading MVR file: {e}")
        
        return self.profiles.copy()
    
    def load_profiles_from_folder(self, folder_path: str) -> Dict[str, GDTFProfile]:
        """
        Load GDTF profiles from a folder.
        
        Args:
            folder_path: Path to folder containing GDTF files
            
        Returns:
            Dictionary of loaded profiles {profile_name: GDTFProfile}
        """
        folder = Path(folder_path)
        if not folder.exists():
            raise FileNotFoundError(f"Folder not found: {folder_path}")
        
        gdtf_files = list(folder.glob("*.gdtf"))
        loaded_profiles = {}
        
        for gdtf_file in gdtf_files:
            try:
                profile = self._load_gdtf_from_file(gdtf_file)
                if profile:
                    loaded_profiles[profile.name] = profile
                    self.profiles[profile.name] = profile
            except Exception as e:
                print(f"Warning: Could not load GDTF file {gdtf_file.name}: {e}")
        
        return loaded_profiles
    
    def _load_gdtf_from_zip(self, zip_file: zipfile.ZipFile, gdtf_filename: str) -> Optional[GDTFProfile]:
        """Load a GDTF profile from a ZIP file."""
        try:
            with zip_file.open(gdtf_filename) as gdtf_zip:
                gdtf_data = io.BytesIO(gdtf_zip.read())
                
                with zipfile.ZipFile(gdtf_data, 'r') as gdtf_archive:
                    if 'description.xml' not in gdtf_archive.namelist():
                        return None
                    
                    with gdtf_archive.open('description.xml') as desc_file:
                        content = desc_file.read().decode('utf-8')
                        return self._parse_gdtf_xml(content, gdtf_filename)
                        
        except Exception as e:
            print(f"Error loading GDTF from ZIP: {e}")
            return None
    
    def _load_gdtf_from_file(self, gdtf_file: Path) -> Optional[GDTFProfile]:
        """Load a GDTF profile from a file."""
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
        """Parse GDTF XML content and extract profile information."""
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
                        
                        # Extract channels for this mode
                        channels = {}
                        
                        # Look for DMXChannels structure
                        dmx_channels_elem = mode_elem.find('DMXChannels')
                        if dmx_channels_elem is not None:
                            dmx_channel_elements = dmx_channels_elem.findall('DMXChannel')
                            
                            for i, dmx_channel_elem in enumerate(dmx_channel_elements):
                                # Get the offset for this channel
                                offset_str = dmx_channel_elem.get('Offset', '')
                                if not offset_str:
                                    continue
                                
                                # Parse offset (can be single number or range like "1,2")
                                offset_parts = offset_str.split(',')
                                if offset_parts:
                                    try:
                                        channel_offset = int(offset_parts[0])
                                    except ValueError:
                                        continue
                                
                                # Find the LogicalChannel within this DMXChannel
                                logical_channel = dmx_channel_elem.find('LogicalChannel')
                                if logical_channel is not None:
                                    attribute_name = self._extract_attribute_name_from_logical_channel(logical_channel, root)
                                    if attribute_name and attribute_name != "NoFeature":
                                        channels[attribute_name] = channel_offset
                        
                        gdtf_mode = GDTFMode(
                            name=mode_name,
                            channels=channels,
                            total_channels=len(channels)
                        )
                        modes[mode_name] = gdtf_mode
            
            return GDTFProfile(name=profile_name, modes=modes)
            
        except ET.ParseError as e:
            print(f"Error parsing GDTF XML: {e}")
            return None
    
    def _extract_attribute_name(self, channel_elem, root) -> Optional[str]:
        """Extract attribute name from a channel element."""
        try:
            # Look for the attribute reference in the channel
            attribute_ref = channel_elem.get('Attribute')
            if not attribute_ref:
                return None
            
            # Find the attribute definition
            for attr_elem in root.findall('.//Attribute'):
                if attr_elem.get('Name') == attribute_ref:
                    # Return the Pretty name if available, otherwise the Name
                    return attr_elem.get('Pretty', attr_elem.get('Name'))
            
            # If not found, return the reference as-is
            return attribute_ref
            
        except Exception:
            return None
    
    def _extract_attribute_name_from_logical_channel(self, logical_channel_elem, root) -> Optional[str]:
        """Extract attribute name from a LogicalChannel element."""
        try:
            # Look for the attribute reference in the logical channel
            attribute_ref = logical_channel_elem.get('Attribute')
            if not attribute_ref:
                return None
            
            # Find the attribute definition
            for attr_elem in root.findall('.//Attribute'):
                if attr_elem.get('Name') == attribute_ref:
                    # Return the Pretty name if available, otherwise the Name
                    return attr_elem.get('Pretty', attr_elem.get('Name'))
            
            # If not found, return the reference as-is
            return attribute_ref
            
        except Exception:
            return None
    
    def match_fixtures(self, fixture_data_list: List[Dict], profiles: Dict[str, GDTFProfile]) -> List[FixtureMatch]:
        """
        Match fixtures to GDTF profiles.
        
        Args:
            fixture_data_list: List of fixture data dictionaries
            profiles: Available GDTF profiles
            
        Returns:
            List of FixtureMatch objects
        """
        matched_fixtures = []
        
        for fixture_data in fixture_data_list:
            match = self._match_single_fixture(fixture_data, profiles)
            matched_fixtures.append(match)
        
        return matched_fixtures
    
    def _match_single_fixture(self, fixture_data: Dict, profiles: Dict[str, GDTFProfile]) -> FixtureMatch:
        """Match a single fixture to its GDTF profile."""
        name = fixture_data.get('name', 'Unknown')
        uuid = fixture_data.get('uuid', '')
        gdtf_spec = fixture_data.get('gdtf_spec', '')
        gdtf_mode = fixture_data.get('gdtf_mode', '')
        base_address = fixture_data.get('base_address', 1)
        fixture_id = fixture_data.get('fixture_id', 0)
        
        # Try to find the GDTF profile
        gdtf_profile = profiles.get(gdtf_spec)
        
        if not gdtf_profile:
            return FixtureMatch(
                name=name,
                uuid=uuid,
                gdtf_spec=gdtf_spec,
                gdtf_mode=gdtf_mode,
                base_address=base_address,
                fixture_id=fixture_id,
                gdtf_profile=None,
                matched_mode=None,
                attribute_offsets={},
                match_status="gdtf_missing"
            )
        
        # Try to find the mode
        matched_mode = gdtf_profile.get_mode(gdtf_mode)
        
        if not matched_mode:
            return FixtureMatch(
                name=name,
                uuid=uuid,
                gdtf_spec=gdtf_spec,
                gdtf_mode=gdtf_mode,
                base_address=base_address,
                fixture_id=fixture_id,
                gdtf_profile=gdtf_profile,
                matched_mode=None,
                attribute_offsets={},
                match_status="mode_missing"
            )
        
        # Successfully matched
        return FixtureMatch(
            name=name,
            uuid=uuid,
            gdtf_spec=gdtf_spec,
            gdtf_mode=gdtf_mode,
            base_address=base_address,
            fixture_id=fixture_id,
            gdtf_profile=gdtf_profile,
            matched_mode=matched_mode,
            attribute_offsets=matched_mode.channels.copy(),
            match_status="matched"
        )
    
    def apply_profile_to_fixture(self, fixture: FixtureMatch, profile_name: str, mode_name: str) -> FixtureMatch:
        """
        Apply a selected GDTF profile and mode to a fixture.
        
        Args:
            fixture: The fixture to update
            profile_name: Name of the GDTF profile to apply
            mode_name: Name of the mode to apply
            
        Returns:
            Updated FixtureMatch object
        """
        # Find the profile
        profile = self.profiles.get(profile_name)
        if not profile:
            fixture.match_status = "gdtf_missing"
            return fixture
        
        # Find the mode
        mode = profile.get_mode(mode_name)
        if not mode:
            fixture.match_status = "mode_missing"
            return fixture
        
        # Apply the profile and mode
        fixture.gdtf_spec = profile_name
        fixture.gdtf_mode = mode_name
        fixture.gdtf_profile = profile
        fixture.matched_mode = mode
        fixture.attribute_offsets = mode.channels.copy()
        fixture.match_status = "matched"
        
        return fixture
    
    def calculate_absolute_addresses(self, fixture: FixtureMatch, selected_attributes: List[str]) -> Dict[str, tuple]:
        """
        Calculate absolute DMX addresses for selected attributes.
        
        Args:
            fixture: The fixture to calculate addresses for
            selected_attributes: List of attribute names to calculate
            
        Returns:
            Dictionary mapping attribute_name -> (universe, channel)
        """
        if not fixture.is_matched():
            return {}
        
        addresses = {}
        base_address = fixture.base_address
        
        for attr_name in selected_attributes:
            if attr_name in fixture.attribute_offsets:
                offset = fixture.attribute_offsets[attr_name]
                absolute_address = base_address + offset - 1  # Convert to 0-based
                
                # Calculate universe and channel
                universe = (absolute_address // self.universe_size) + 1
                channel = (absolute_address % self.universe_size) + 1
                
                addresses[attr_name] = (universe, channel)
        
        return addresses
    
    def get_available_attributes(self) -> List[str]:
        """Get all available attributes from all loaded GDTF profiles."""
        attributes = set()
        
        for profile in self.profiles.values():
            for mode in profile.modes.values():
                attributes.update(mode.channels.keys())
        
        return sorted(list(attributes))
    
    def get_available_profiles(self) -> List[str]:
        """Get all available GDTF profile names."""
        return sorted(list(self.profiles.keys()))
    
    def get_profile_modes(self, profile_name: str) -> List[str]:
        """Get available modes for a specific GDTF profile."""
        profile = self.profiles.get(profile_name)
        if not profile:
            return []
        return profile.get_mode_names()
    
    def get_match_summary(self, fixtures: List[FixtureMatch]) -> MatchSummary:
        """
        Get a summary of matching results.
        
        Args:
            fixtures: List of FixtureMatch objects
            
        Returns:
            MatchSummary object with statistics
        """
        total = len(fixtures)
        matched = sum(1 for f in fixtures if f.match_status == "matched")
        gdtf_missing = sum(1 for f in fixtures if f.match_status == "gdtf_missing")
        mode_missing = sum(1 for f in fixtures if f.match_status == "mode_missing")
        error = sum(1 for f in fixtures if f.match_status == "error")
        
        return MatchSummary(
            total_fixtures=total,
            matched=matched,
            gdtf_missing=gdtf_missing,
            mode_missing=mode_missing,
            error=error
        )
    
    def clear_profiles(self):
        """Clear all loaded profiles."""
        self.profiles.clear()
    
    def get_profile_info(self, profile_name: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a specific profile."""
        profile = self.profiles.get(profile_name)
        if not profile:
            return None
        
        return {
            'name': profile.name,
            'modes': list(profile.modes.keys()),
            'mode_count': len(profile.modes),
            'total_attributes': len(self._get_profile_attributes(profile))
        }
    
    def _get_profile_attributes(self, profile: GDTFProfile) -> set:
        """Get all attributes used by a profile."""
        attributes = set()
        for mode in profile.modes.values():
            attributes.update(mode.channels.keys())
        return attributes 