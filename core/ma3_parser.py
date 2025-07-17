"""
Simple MA3 XML file parser.
Extracts fixture data from MA3 patch XML files using minimal, clean functions.
"""

import xml.etree.ElementTree as ET
from typing import List, Dict, Any, Optional
from pathlib import Path

from .data import create_fixture


def parse_ma3_file(ma3_path: str) -> Dict[str, Any]:
    """Parse MA3 XML file and extract fixture data."""
    try:
        # Parse XML
        tree = ET.parse(ma3_path)
        root = tree.getroot()
        
        # Validate it's a MA3 file
        if root.tag != 'GMA3':
            raise ValueError("Not a valid MA3 XML file. Root element must be 'GMA3'")
        
        fixtures = _extract_fixtures_from_xml(root)
        
        return {
            'fixtures': fixtures,
            'gdtf_profiles': {},  # MA3 files don't contain embedded GDTF profiles
            'success': True
        }
        
    except Exception as e:
        return {'error': f'Failed to parse MA3 XML file: {str(e)}'}


def _extract_fixtures_from_xml(root: ET.Element) -> List[Dict[str, Any]]:
    """Extract fixture data from XML root element."""
    fixtures = []
    fixture_id_counter = 1
    
    # Find all fixture elements
    for fixture_elem in root.findall('Fixture'):
        fixture_data = _parse_fixture_element(fixture_elem, fixture_id_counter)
        if fixture_data:
            fixtures.append(fixture_data)
            fixture_id_counter += 1
    
    return fixtures


def _parse_fixture_element(fixture_elem: ET.Element, fixture_id: int) -> Optional[Dict[str, Any]]:
    """Parse individual fixture element from MA3 XML."""
    try:
        # Get basic fixture info from attributes
        name = fixture_elem.get('Name', f'Fixture_{fixture_id}')
        uuid = fixture_elem.get('Guid', '')
        mode = fixture_elem.get('Mode', '')
        fid = fixture_elem.get('FID', str(fixture_id))
        
        # Parse patch information to get universe and channel
        patch = fixture_elem.get('Patch', '1.001')
        universe, channel = _parse_patch_universe_channel(patch)
        
        # Calculate absolute address from universe and channel
        # Formula: absolute_address = (universe - 1) * 512 + channel
        absolute_address = (universe - 1) * 512 + channel
        
        # Parse fixture ID from FID
        try:
            parsed_fixture_id = int(fid)
        except (ValueError, TypeError):
            parsed_fixture_id = fixture_id
        
        # Extract fixture type from mode (e.g., "2.DMXModes.8 bit" -> "2")
        fixture_type = _extract_fixture_type_from_mode(mode)
        
        return create_fixture(
            name=name,
            fixture_type=fixture_type,
            mode=mode,
            base_address=absolute_address,  # Use absolute address as base_address
            fixture_id=parsed_fixture_id,
            uuid=uuid,
            # Store original universe and channel values for GDTF matching
            ma3_universe=universe,
            ma3_channel=channel,
            patch=patch
        )
        
    except Exception as e:
        print(f"Warning: Could not extract fixture data: {e}")
        return None


def _parse_patch_universe_channel(patch: str) -> tuple[int, int]:
    """Parse MA3 patch address (e.g., '101.001' -> (101, 1), '101.206' -> (101, 206))."""
    try:
        # MA3 patch format is typically "universe.channel"
        if '.' in patch:
            parts = patch.split('.')
            if len(parts) >= 2:
                universe = int(parts[0])
                channel = int(parts[1])
                return universe, channel
        # If no dot, try to parse as single number (assume universe 1)
        channel = int(patch)
        return 1, channel
    except (ValueError, TypeError):
        return 1, 1


def _extract_fixture_type_from_mode(mode: str) -> str:
    """Extract fixture type from MA3 mode string."""
    try:
        # MA3 mode format is typically "type.DMXModes.mode_name"
        # Extract the type part (first component)
        if '.' in mode:
            return mode.split('.')[0]
        return mode
    except:
        return mode


def validate_ma3_file(ma3_path: str) -> bool:
    """Check if file is a valid MA3 XML file."""
    try:
        # Check file extension
        if not ma3_path.lower().endswith('.xml'):
            return False
        
        # Try to parse XML and check root element
        tree = ET.parse(ma3_path)
        root = tree.getroot()
        
        # Valid if root element is GMA3
        return root.tag == 'GMA3'
        
    except ET.ParseError:
        return False
    except Exception:
        return False 