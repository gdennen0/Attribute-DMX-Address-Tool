"""
Simple GDTF file parser.
Extracts channel mappings from GDTF files using minimal, clean functions.
"""

import zipfile
import xml.etree.ElementTree as ET
from typing import Dict, Any, Optional
from pathlib import Path

from .data import create_gdtf_profile


def parse_gdtf_file(gdtf_path: str) -> Optional[Dict[str, Any]]:
    """Parse GDTF file and extract mode/channel information."""
    try:
        with zipfile.ZipFile(gdtf_path, 'r') as zip_file:
            # Find the description.xml file
            description_content = None
            for file_name in zip_file.namelist():
                if file_name.endswith('description.xml'):
                    description_content = zip_file.read(file_name).decode('utf-8')
                    break
            
            if not description_content:
                return None
            
            # Parse XML
            root = ET.fromstring(description_content)
            
            # Extract fixture type name
            fixture_type = root.find('.//FixtureType')
            if fixture_type is None:
                return None
            
            name = fixture_type.get('Name', Path(gdtf_path).stem)
            
            # Extract modes
            modes = _extract_modes_from_xml(root)
            
            return create_gdtf_profile(name, modes)
            
    except Exception as e:
        print(f"Error parsing GDTF file {gdtf_path}: {e}")
        return None


def _extract_modes_from_xml(root: ET.Element) -> Dict[str, Dict[str, int]]:
    """Extract DMX modes and their channel mappings."""
    modes = {}
    
    # Find all DMX modes
    for mode in root.findall('.//DMXMode'):
        mode_name = mode.get('Name', 'Unknown')
        
        # Get channel layout for this mode
        channel_layout = _extract_channel_layout(mode)
        if channel_layout:
            modes[mode_name] = channel_layout
    
    return modes


def _extract_channel_layout(mode_element: ET.Element) -> Dict[str, int]:
    """Extract channel layout from a DMX mode."""
    channel_layout = {}
    
    # Find all channel functions in this mode
    for i, channel in enumerate(mode_element.findall('.//Channel')):
        # Get the channel function reference
        channel_func = channel.get('ChannelFunction')
        if not channel_func:
            continue
        
        # Find the corresponding channel function definition
        channel_function = _find_channel_function(mode_element, channel_func)
        if channel_function is not None:
            # Get the attribute name
            attribute = channel_function.get('Attribute')
            if attribute:
                # Remove namespace prefix if present
                if ':' in attribute:
                    attribute = attribute.split(':')[-1]
                
                channel_layout[attribute] = i
    
    return channel_layout


def _find_channel_function(mode_element: ET.Element, channel_func_name: str) -> Optional[ET.Element]:
    """Find channel function definition by name."""
    # Look in the parent fixture type for channel functions
    # Find the root by traversing up the tree
    root = mode_element
    while root.getparent() is not None:
        root = root.getparent()
    
    # Search for channel function
    for channel_func in root.findall('.//ChannelFunction'):
        if channel_func.get('Name') == channel_func_name:
            return channel_func
    
    return None


def parse_external_gdtf_folder(gdtf_folder: str) -> Dict[str, Dict[str, Any]]:
    """Parse all GDTF files in a folder."""
    gdtf_profiles = {}
    
    if not gdtf_folder or not Path(gdtf_folder).exists():
        return gdtf_profiles
    
    folder_path = Path(gdtf_folder)
    
    # Find all GDTF files
    for gdtf_file in folder_path.glob('*.gdtf'):
        try:
            profile = parse_gdtf_file(str(gdtf_file))
            if profile:
                profile_name = gdtf_file.stem
                gdtf_profiles[profile_name] = profile
        except Exception as e:
            print(f"Error parsing {gdtf_file}: {e}")
    
    return gdtf_profiles


def get_available_modes(gdtf_profile: Dict[str, Any]) -> list[str]:
    """Get list of available modes for a GDTF profile."""
    return list(gdtf_profile.get('modes', {}).keys())


def get_mode_attributes(gdtf_profile: Dict[str, Any], mode_name: str) -> Dict[str, int]:
    """Get attribute to channel mapping for a specific mode."""
    modes = gdtf_profile.get('modes', {})
    return modes.get(mode_name, {}) 