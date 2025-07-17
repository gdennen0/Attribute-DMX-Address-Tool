"""
Simple fixture matching logic.
Matches fixtures to GDTF profiles using minimal, clean functions.
"""

from typing import List, Dict, Any, Optional
import re

from .data import match_fixture_to_gdtf, assign_sequences


def auto_match_fixtures(fixtures: List[Dict[str, Any]], 
                       gdtf_profiles: Dict[str, Dict[str, Any]]) -> None:
    """Automatically match fixtures to GDTF profiles where possible."""
    for fixture in fixtures:
        if fixture.get('matched'):
            continue
            
        fixture_type = fixture.get('type', '')
        fixture_mode = fixture.get('mode', '')
        
        # Try exact match first
        matched_profile = _find_exact_match(fixture_type, gdtf_profiles)
        
        # If no exact match, try fuzzy matching
        if not matched_profile:
            matched_profile = _find_fuzzy_match(fixture_type, gdtf_profiles)
        
        if matched_profile:
            # Find matching mode
            best_mode = _find_best_mode(fixture_mode, matched_profile)
            if best_mode:
                match_fixture_to_gdtf(fixture, matched_profile, best_mode)


def _find_exact_match(fixture_type: str, gdtf_profiles: Dict[str, Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Find exact match between fixture type and GDTF profile."""
    # Direct name match
    if fixture_type in gdtf_profiles:
        return gdtf_profiles[fixture_type]
    
    # Try profile names
    for profile_name, profile in gdtf_profiles.items():
        if profile['name'] == fixture_type:
            return profile
    
    return None


def _find_fuzzy_match(fixture_type: str, gdtf_profiles: Dict[str, Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Find fuzzy match between fixture type and GDTF profile."""
    if not fixture_type:
        return None
    
    # Normalize fixture type for comparison
    normalized_fixture = _normalize_string(fixture_type)
    
    best_match = None
    best_score = 0
    
    for profile_name, profile in gdtf_profiles.items():
        # Check profile key name
        score = _calculate_similarity(normalized_fixture, _normalize_string(profile_name))
        if score > best_score:
            best_score = score
            best_match = profile
        
        # Check profile display name
        profile_display_name = profile.get('name', '')
        score = _calculate_similarity(normalized_fixture, _normalize_string(profile_display_name))
        if score > best_score:
            best_score = score
            best_match = profile
    
    # Only return match if similarity is high enough
    return best_match if best_score > 0.7 else None


def _find_best_mode(fixture_mode: str, gdtf_profile: Dict[str, Any]) -> Optional[str]:
    """Find best matching mode in GDTF profile."""
    available_modes = list(gdtf_profile.get('modes', {}).keys())
    
    if not available_modes:
        return None
    
    # If no mode specified, return first available
    if not fixture_mode:
        return available_modes[0]
    
    # Try exact match first
    if fixture_mode in available_modes:
        return fixture_mode
    
    # Fuzzy match on mode names
    normalized_mode = _normalize_string(fixture_mode)
    best_match = None
    best_score = 0
    
    for mode in available_modes:
        score = _calculate_similarity(normalized_mode, _normalize_string(mode))
        if score > best_score:
            best_score = score
            best_match = mode
    
    # Return best match if similarity is reasonable
    return best_match if best_score > 0.5 else available_modes[0]


def _normalize_string(text: str) -> str:
    """Normalize string for comparison."""
    if not text:
        return ''
    
    # Convert to lowercase and remove special characters
    normalized = re.sub(r'[^a-z0-9]', '', text.lower())
    return normalized


def _calculate_similarity(str1: str, str2: str) -> float:
    """Calculate similarity between two strings."""
    if not str1 or not str2:
        return 0.0
    
    if str1 == str2:
        return 1.0
    
    # Check if one is contained in the other
    if str1 in str2 or str2 in str1:
        return 0.8
    
    # Simple character-based similarity
    longer = str1 if len(str1) > len(str2) else str2
    shorter = str2 if len(str1) > len(str2) else str1
    
    if len(longer) == 0:
        return 1.0
    
    matches = sum(1 for i, char in enumerate(shorter) if i < len(longer) and char == longer[i])
    return matches / len(longer)


def manual_match_fixture(fixture: Dict[str, Any], gdtf_profile: Dict[str, Any], mode: str) -> bool:
    """Manually match a fixture to a specific GDTF profile and mode."""
    return match_fixture_to_gdtf(fixture, gdtf_profile, mode)


def get_match_summary(fixtures: List[Dict[str, Any]]) -> Dict[str, int]:
    """Get summary of matching results."""
    total = len(fixtures)
    matched = sum(1 for f in fixtures if f.get('matched', False))
    selected = sum(1 for f in fixtures if f.get('selected', False))
    
    return {
        'total': total,
        'matched': matched,
        'unmatched': total - matched,
        'selected': selected,
        'match_rate': (matched / total * 100) if total > 0 else 0
    }


def process_fixtures_for_export(fixtures: List[Dict[str, Any]], 
                               selected_attributes: List[str],
                               sequence_start: int = 1001) -> None:
    """Process fixtures for export by assigning sequences."""
    # Filter to selected and matched fixtures
    export_fixtures = [f for f in fixtures if f.get('selected') and f.get('matched')]
    
    # Assign sequence numbers
    assign_sequences(export_fixtures, selected_attributes, sequence_start)


def get_fixture_role(fixture: Dict[str, Any]) -> str:
    """Get the role of a fixture (master, remote, or none)."""
    return fixture.get('fixture_role', 'none') 