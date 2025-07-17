"""
Simple data structures for AttributeAddresser.
All data represented as simple dictionaries and lists for easy state management.
"""

from typing import Dict, List, Any, Optional


class GDTFProfileModel:
    """Model for GDTF profile with selected attributes."""
    
    def __init__(self, name: str, mode: str, channels: Dict[str, int], selected_attributes: List[str] = None):
        self.name = name
        self.mode = mode
        self.channels = channels  # {attribute_name: channel_offset}
        self.selected_attributes = selected_attributes or []
        self._sorted_attributes = None  # Cache for sorted attributes
    
    def get_sorted_attributes(self) -> List[str]:
        """Get selected attributes sorted by channel offset."""
        if self._sorted_attributes is None:
            # Sort selected attributes by their channel offset
            available_attributes = [attr for attr in self.selected_attributes if attr in self.channels]
            self._sorted_attributes = sorted(available_attributes, key=lambda attr: self.channels[attr])
        return self._sorted_attributes
    
    def set_selected_attributes(self, attributes: List[str]):
        """Set selected attributes and clear cache."""
        self.selected_attributes = attributes
        self._sorted_attributes = None  # Clear cache
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'name': self.name,
            'mode': self.mode,
            'channels': self.channels,
            'selected_attributes': self.selected_attributes
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'GDTFProfileModel':
        """Create from dictionary."""
        return cls(
            name=data['name'],
            mode=data['mode'],
            channels=data['channels'],
            selected_attributes=data.get('selected_attributes', [])
        )


def create_fixture(name: str, fixture_type: str, mode: str, base_address: int, 
                  fixture_id: int = 0, uuid: str = "", **kwargs) -> Dict[str, Any]:
    """Create a fixture dictionary with standard structure."""
    return {
        'name': name,
        'type': fixture_type,
        'mode': mode,
        'base_address': base_address,
        'fixture_id': fixture_id,
        'uuid': uuid,
        'selected': True,  # Default to selected for import
        'matched': False,
        'gdtf_profile': None,  # Will be GDTFProfileModel instance
        'attributes': {},  # {attribute_name: channel_offset}
        'addresses': {},   # {attribute_name: absolute_address}
        'universes': {},   # {attribute_name: universe_number}
        'channels': {},    # {attribute_name: channel_number}
        'sequences': {},   # {attribute_name: sequence_number}
        'fixture_role': 'none',  # 'master', 'remote', or 'none'
        'linked_fixtures': [],  # List of fixture IDs linked to this fixture
        **kwargs
    }


def create_gdtf_profile(name: str, modes: Dict[str, Dict[str, int]]) -> Dict[str, Any]:
    """Create a GDTF profile dictionary."""
    return {
        'name': name,
        'modes': modes  # {mode_name: {attribute_name: channel_offset}}
    }


def create_project_state() -> Dict[str, Any]:
    """Create initial project state."""
    return {
        'fixtures': [],
        'gdtf_profiles': {},  # {profile_name: gdtf_profile}
        'selected_attributes': [],
        'sequence_start': 1001,
        'output_format': 'text'
    }


def get_fixture_attributes(fixture: Dict[str, Any]) -> List[str]:
    """Get list of attributes for a fixture."""
    return list(fixture.get('attributes', {}).keys())


def set_fixture_selected(fixture: Dict[str, Any], selected: bool):
    """Set fixture selection status."""
    fixture['selected'] = selected


def is_fixture_selected(fixture: Dict[str, Any]) -> bool:
    """Check if fixture is selected for import (used in import dialogs)."""
    return fixture.get('selected', False)


def set_fixture_role(fixture: Dict[str, Any], role: str):
    """Set fixture role (master or remote)."""
    if role in ['master', 'remote']:
        fixture['fixture_role'] = role
        fixture['linked_fixtures'] = []


def get_fixture_role(fixture: Dict[str, Any]) -> str:
    """Get fixture role."""
    return fixture.get('fixture_role', 'none')


def get_master_fixtures(fixtures: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Get all master fixtures."""
    return [f for f in fixtures if get_fixture_role(f) == 'master']


def get_remote_fixtures(fixtures: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Get all remote fixtures."""
    return [f for f in fixtures if get_fixture_role(f) == 'remote']


def get_master_fixtures_matched(fixtures: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Get all matched master fixtures."""
    return [f for f in fixtures if get_fixture_role(f) == 'master' and f.get('matched', False)]


def get_remote_fixtures_matched(fixtures: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Get all matched remote fixtures."""
    return [f for f in fixtures if get_fixture_role(f) == 'remote' and f.get('matched', False)]


def get_fixtures_by_role(fixtures: List[Dict[str, Any]], role: str) -> List[Dict[str, Any]]:
    """Get fixtures by role (master, remote, or none)."""
    return [f for f in fixtures if get_fixture_role(f) == role]


def get_fixtures_by_role_matched(fixtures: List[Dict[str, Any]], role: str) -> List[Dict[str, Any]]:
    """Get matched fixtures by role (master, remote, or none)."""
    return [f for f in fixtures if get_fixture_role(f) == role and f.get('matched', False)]


def validate_fixture_roles(fixtures: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Validate fixture roles and return summary statistics."""
    master_count = len(get_master_fixtures(fixtures))
    remote_count = len(get_remote_fixtures(fixtures))
    none_count = len(get_fixtures_by_role(fixtures, 'none'))
    
    master_matched = len(get_master_fixtures_matched(fixtures))
    remote_matched = len(get_remote_fixtures_matched(fixtures))
    
    return {
        'total_fixtures': len(fixtures),
        'master_fixtures': master_count,
        'remote_fixtures': remote_count,
        'unassigned_fixtures': none_count,
        'master_matched': master_matched,
        'remote_matched': remote_matched,
        'master_unmatched': master_count - master_matched,
        'remote_unmatched': remote_count - remote_matched
    }


def ensure_fixture_role_consistency(fixtures: List[Dict[str, Any]]) -> bool:
    """Ensure all fixtures have valid roles assigned."""
    for fixture in fixtures:
        role = get_fixture_role(fixture)
        if role not in ['master', 'remote', 'none']:
            return False
    return True


def get_fixture_by_id(fixtures: List[Dict[str, Any]], fixture_id: int) -> Optional[Dict[str, Any]]:
    """Get a specific fixture by its ID."""
    for fixture in fixtures:
        if fixture.get('fixture_id') == fixture_id:
            return fixture
    return None


def get_fixtures_by_type(fixtures: List[Dict[str, Any]], fixture_type: str) -> List[Dict[str, Any]]:
    """Get all fixtures of a specific type."""
    return [f for f in fixtures if f.get('type') == fixture_type]


def get_fixtures_by_type_and_role(fixtures: List[Dict[str, Any]], fixture_type: str, role: str) -> List[Dict[str, Any]]:
    """Get fixtures of a specific type and role."""
    return [f for f in fixtures if f.get('type') == fixture_type and get_fixture_role(f) == role]


def calculate_universe_and_channel(absolute_address: int, universe_size: int = 512) -> tuple[int, int]:
    """Calculate universe and channel from absolute DMX address."""
    # Convert to 0-based for calculation, then back to 1-based
    universe = ((absolute_address - 1) // universe_size) + 1
    channel = ((absolute_address - 1) % universe_size) + 1
    return universe, channel


def match_fixture_to_gdtf(fixture: Dict[str, Any], gdtf_profile: Dict[str, Any], mode: str, selected_attributes: List[str] = None) -> bool:
    """Match a fixture to a GDTF profile and mode."""
    if mode not in gdtf_profile['modes']:
        return False
    
    mode_data = gdtf_profile['modes'][mode]
    
    # Create GDTFProfileModel
    profile_model = GDTFProfileModel(
        name=gdtf_profile['name'],
        mode=mode,
        channels=mode_data.copy(),
        selected_attributes=selected_attributes or []
    )
    
    fixture['gdtf_profile'] = profile_model
    fixture['mode'] = mode
    fixture['attributes'] = mode_data.copy()
    fixture['matched'] = True
    
    # Calculate absolute addresses, universes, and channels
    base = fixture['base_address']
    fixture['addresses'] = {}
    fixture['universes'] = {}
    fixture['channels'] = {}
    
    # Preserve original CSV values for display
    original_csv_universe = fixture.get('csv_universe')
    original_csv_channel = fixture.get('csv_channel')
    
    for attr, offset in mode_data.items():
        # Calculate absolute DMX address (1-based)
        # base_address is 1-based, offset is 1-based from GDTF
        absolute_address = base + (offset - 1)
        fixture['addresses'][attr] = absolute_address
        
        # For CSV fixtures, use the original CSV universe and calculate channel based on offset
        if original_csv_universe is not None and original_csv_channel is not None:
            # Use the original CSV universe
            fixture['universes'][attr] = original_csv_universe
            # Calculate channel: original channel + offset - 1
            fixture['channels'][attr] = original_csv_channel + (offset - 1)
        else:
            # For non-CSV fixtures, calculate universe and channel from absolute address
            universe, channel = calculate_universe_and_channel(absolute_address)
            fixture['universes'][attr] = universe
            fixture['channels'][attr] = channel
    
    return True


def assign_sequences(fixtures: List[Dict[str, Any]], start_number: int = 1001):
    """Assign sequence numbers to fixture attributes using their GDTF profile models."""
    sequence_num = start_number
    
    # Assign sequences to all selected and matched fixtures
    for fixture in fixtures:
        if not fixture.get('selected') or not fixture.get('matched'):
            continue
            
        fixture['sequences'] = {}
        
        # Get sorted attributes from the fixture's GDTF profile model
        profile_model = fixture.get('gdtf_profile')
        if profile_model:
            sorted_attributes = profile_model.get_sorted_attributes()
        else:
            # Fallback to unsorted attributes if no profile model
            sorted_attributes = list(fixture.get('attributes', {}).keys())
        
        for attr in sorted_attributes:
            if attr in fixture.get('attributes', {}):
                fixture['sequences'][attr] = sequence_num
                sequence_num += 1


def get_export_data(fixtures: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Get export data for fixtures and attributes using their GDTF profile models."""
    export_data = []
    
    for fixture in fixtures:
        if not fixture.get('matched'):
            continue
        
        # Get sorted attributes from the fixture's GDTF profile model
        profile_model = fixture.get('gdtf_profile')
        if profile_model:
            sorted_attributes = profile_model.get_sorted_attributes()
        else:
            # Fallback to unsorted attributes if no profile model
            sorted_attributes = list(fixture.get('attributes', {}).keys())
            
        for attr in sorted_attributes:
            if attr in fixture.get('attributes', {}):
                # Get universe and channel for proper address formatting
                universe = fixture['universes'].get(attr, 1)
                channel = fixture['channels'].get(attr, 1)
                absolute_address = fixture['addresses'].get(attr, 1)
                
                item = {
                    'fixture_name': fixture['name'],
                    'fixture_id': fixture['fixture_id'],
                    'attribute': attr,
                    'universe': universe,
                    'channel': channel,
                    'absolute_address': absolute_address,
                    'sequence': fixture['sequences'].get(attr, 0)
                }
                
                export_data.append(item)
    
    return export_data 