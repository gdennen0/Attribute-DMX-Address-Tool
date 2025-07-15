"""
Simple data structures for AttributeAddresser.
All data represented as simple dictionaries and lists for easy state management.
"""

from typing import Dict, List, Any, Optional


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
        'gdtf_profile': None,
        'attributes': {},  # {attribute_name: channel_offset}
        'addresses': {},   # {attribute_name: absolute_address}
        'sequences': {},   # {attribute_name: sequence_number}
        'fixture_role': 'unassigned',  # 'master', 'remote', or 'unassigned'
        'linked_fixtures': [],  # List of fixture IDs linked to this fixture
        'master_fixture_id': None,  # If remote, ID of the master fixture
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
    """Check if fixture is selected for import."""
    return fixture.get('selected', False)


def set_fixture_role(fixture: Dict[str, Any], role: str):
    """Set fixture role (master or remote)."""
    if role in ['master', 'remote']:
        fixture['fixture_role'] = role
        if role == 'master':
            fixture['master_fixture_id'] = None
        else:
            fixture['linked_fixtures'] = []


def get_fixture_role(fixture: Dict[str, Any]) -> str:
    """Get fixture role."""
    return fixture.get('fixture_role', 'master')


def link_remote_to_master(remote_fixture: Dict[str, Any], master_fixture: Dict[str, Any]):
    """Link a remote fixture to a master fixture."""
    if get_fixture_role(remote_fixture) != 'remote' or get_fixture_role(master_fixture) != 'master':
        return False
    
    # Set master reference in remote
    remote_fixture['master_fixture_id'] = master_fixture['fixture_id']
    
    # Add remote to master's linked list
    if remote_fixture['fixture_id'] not in master_fixture['linked_fixtures']:
        master_fixture['linked_fixtures'].append(remote_fixture['fixture_id'])
    
    return True


def unlink_remote_from_master(remote_fixture: Dict[str, Any], master_fixture: Dict[str, Any]):
    """Unlink a remote fixture from a master fixture."""
    # Remove master reference from remote
    remote_fixture['master_fixture_id'] = None
    
    # Remove remote from master's linked list
    if remote_fixture['fixture_id'] in master_fixture['linked_fixtures']:
        master_fixture['linked_fixtures'].remove(remote_fixture['fixture_id'])


def get_master_fixtures(fixtures: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Get all master fixtures."""
    return [f for f in fixtures if get_fixture_role(f) == 'master']


def get_remote_fixtures(fixtures: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Get all remote fixtures."""
    return [f for f in fixtures if get_fixture_role(f) == 'remote']


def get_linked_remotes(master_fixture: Dict[str, Any], all_fixtures: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Get all remote fixtures linked to a master."""
    linked_ids = master_fixture.get('linked_fixtures', [])
    return [f for f in all_fixtures if f['fixture_id'] in linked_ids]


def get_master_for_remote(remote_fixture: Dict[str, Any], all_fixtures: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Get the master fixture for a remote fixture."""
    master_id = remote_fixture.get('master_fixture_id')
    if master_id is None:
        return None
    
    for fixture in all_fixtures:
        if fixture['fixture_id'] == master_id:
            return fixture
    return None


def match_fixture_to_gdtf(fixture: Dict[str, Any], gdtf_profile: Dict[str, Any], mode: str) -> bool:
    """Match a fixture to a GDTF profile and mode."""
    if mode not in gdtf_profile['modes']:
        return False
    
    mode_data = gdtf_profile['modes'][mode]
    fixture['gdtf_profile'] = gdtf_profile
    fixture['mode'] = mode
    fixture['attributes'] = mode_data.copy()
    fixture['matched'] = True
    
    # Calculate absolute addresses
    base = fixture['base_address']
    fixture['addresses'] = {
        attr: base + offset 
        for attr, offset in mode_data.items()
    }
    
    return True


def assign_sequences(fixtures: List[Dict[str, Any]], selected_attributes: List[str], start_number: int = 1001):
    """Assign sequence numbers to fixture attributes with master/remote support."""
    sequence_num = start_number
    
    # First pass: Assign sequences to master fixtures
    master_fixtures = get_master_fixtures(fixtures)
    for fixture in master_fixtures:
        if not fixture.get('selected') or not fixture.get('matched'):
            continue
            
        fixture['sequences'] = {}
        for attr in selected_attributes:
            if attr in fixture.get('attributes', {}):
                fixture['sequences'][attr] = sequence_num
                sequence_num += 1
    
    # Second pass: Copy sequences from masters to their linked remotes
    for master_fixture in master_fixtures:
        if not master_fixture.get('selected') or not master_fixture.get('matched'):
            continue
            
        linked_remotes = get_linked_remotes(master_fixture, fixtures)
        for remote_fixture in linked_remotes:
            if remote_fixture.get('selected') and remote_fixture.get('matched'):
                # Copy sequences from master to remote
                remote_fixture['sequences'] = master_fixture['sequences'].copy()
    
    # Third pass: Assign sequences to unlinked remote fixtures
    remote_fixtures = get_remote_fixtures(fixtures)
    for fixture in remote_fixtures:
        if not fixture.get('selected') or not fixture.get('matched'):
            continue
        
        # Skip if already has sequences from master
        if fixture.get('sequences'):
            continue
            
        fixture['sequences'] = {}
        for attr in selected_attributes:
            if attr in fixture.get('attributes', {}):
                fixture['sequences'][attr] = sequence_num
                sequence_num += 1


def get_export_data(fixtures: List[Dict[str, Any]], selected_attributes: List[str]) -> List[Dict[str, Any]]:
    """Get export data for selected fixtures and attributes."""
    export_data = []
    
    for fixture in fixtures:
        if not fixture.get('selected') or not fixture.get('matched'):
            continue
            
        for attr in selected_attributes:
            if attr in fixture.get('attributes', {}):
                # Include role and master info in export data
                item = {
                    'fixture_name': fixture['name'],
                    'fixture_id': fixture['fixture_id'],
                    'attribute': attr,
                    'address': fixture['addresses'].get(attr, 0),
                    'sequence': fixture['sequences'].get(attr, 0),
                    'role': fixture.get('fixture_role', 'master')
                }
                
                # Add master info for remote fixtures
                if fixture.get('fixture_role') == 'remote' and fixture.get('master_fixture_id'):
                    item['master_fixture_id'] = fixture['master_fixture_id']
                
                export_data.append(item)
    
    return export_data 