"""
Data models for MVR File Analyzer.
Clean data structures with no business logic.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Any


@dataclass
class GDTFMode:
    """Represents a GDTF mode with its channel mappings."""
    name: str
    channels: Dict[str, int]  # attribute_name -> channel_offset
    activation_groups: Dict[str, Optional[str]] = None  # attribute_name -> activation_group_name
    total_channels: int = 0
    
    def __post_init__(self):
        if self.activation_groups is None:
            self.activation_groups = {}
        if self.total_channels == 0:
            self.total_channels = len(self.channels)


@dataclass
class GDTFProfile:
    """Represents a GDTF profile with its modes."""
    name: str
    modes: Dict[str, GDTFMode]  # mode_name -> GDTFMode
    
    def get_mode_names(self) -> List[str]:
        """Get list of mode names."""
        return list(self.modes.keys())
    
    def get_mode(self, mode_name: str) -> Optional[GDTFMode]:
        """Get a specific mode by name."""
        return self.modes.get(mode_name)


@dataclass
class FixtureMatch:
    """Represents a matched fixture with its GDTF profile and mode."""
    name: str
    uuid: str
    gdtf_spec: str
    gdtf_mode: str
    base_address: int
    fixture_id: int = 0  # Added fixture_id field
    gdtf_profile: Optional[GDTFProfile] = None
    matched_mode: Optional[GDTFMode] = None
    attribute_offsets: Dict[str, int] = None
    match_status: str = "pending"  # "matched", "gdtf_missing", "mode_missing", "error"
    absolute_addresses: Dict[str, Dict[str, int]] = None  # attribute_name -> {"universe": X, "channel": Y, "absolute_address": Z}
    attribute_sequences: Dict[str, int] = None  # attribute_name -> sequence_number
    attribute_activation_groups: Dict[str, Optional[str]] = None  # attribute_name -> activation_group_name
    
    def __post_init__(self):
        if self.attribute_offsets is None:
            self.attribute_offsets = {}
        if self.absolute_addresses is None:
            self.absolute_addresses = {}
        if self.attribute_sequences is None:
            self.attribute_sequences = {}
        if self.attribute_activation_groups is None:
            self.attribute_activation_groups = {}
    
    def is_matched(self) -> bool:
        """Check if fixture is successfully matched."""
        return self.match_status == "matched"
    
    def get_address_for_attribute(self, attribute_name: str) -> Optional[tuple]:
        """Get (universe, channel) for a specific attribute."""
        addr_info = self.absolute_addresses.get(attribute_name)
        if addr_info and isinstance(addr_info, dict):
            return (addr_info.get("universe"), addr_info.get("channel"))
        return None
    
    def get_sequence_for_attribute(self, attribute_name: str) -> Optional[int]:
        """Get sequence number for a specific attribute."""
        return self.attribute_sequences.get(attribute_name)
    
    def get_activation_group_for_attribute(self, attribute_name: str) -> Optional[str]:
        """Get activation group for a specific attribute."""
        return self.attribute_activation_groups.get(attribute_name)


@dataclass
class AnalysisResults:
    """Contains the complete results of MVR analysis."""
    fixtures: List[FixtureMatch]
    summary: Dict[str, Any]
    selected_attributes: List[str]
    output_format: str
    export_data: str
    validation_info: Dict[str, Any]
    table_order: Optional[List[tuple]] = None  # Store table order for export
    fixture_type_attributes: Optional[Dict[str, List[str]]] = None  # Store fixture type attributes for per-fixture-type analysis
    
    def get_matched_fixtures(self) -> List[FixtureMatch]:
        """Get only successfully matched fixtures."""
        return [f for f in self.fixtures if f.is_matched()]
    
    def get_unmatched_fixtures(self) -> List[FixtureMatch]:
        """Get fixtures that couldn't be matched."""
        return [f for f in self.fixtures if not f.is_matched()]
    
    def get_match_rate(self) -> float:
        """Get the percentage of fixtures that were successfully matched."""
        if not self.fixtures:
            return 0.0
        return (len(self.get_matched_fixtures()) / len(self.fixtures)) * 100


@dataclass
class FixtureData:
    """Raw fixture data extracted from MVR file."""
    name: str
    uuid: str
    gdtf_spec: str
    gdtf_mode: str
    base_address: int
    fixture_id: int = 0  # Added fixture_id field
    position: Optional[Dict[str, float]] = None
    rotation: Optional[Dict[str, float]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for processing."""
        return {
            'name': self.name,
            'uuid': self.uuid,
            'gdtf_spec': self.gdtf_spec,
            'gdtf_mode': self.gdtf_mode,
            'base_address': self.base_address,
            'fixture_id': self.fixture_id,
            'position': self.position,
            'rotation': self.rotation
        }


@dataclass
class MatchSummary:
    """Summary of matching results."""
    total_fixtures: int
    matched: int
    gdtf_missing: int
    mode_missing: int
    error: int
    
    @property
    def unmatched(self) -> int:
        """Total unmatched fixtures."""
        return self.total_fixtures - self.matched
    
    @property
    def match_rate(self) -> float:
        """Match rate as percentage."""
        if self.total_fixtures == 0:
            return 0.0
        return (self.matched / self.total_fixtures) * 100
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'total_fixtures': self.total_fixtures,
            'matched': self.matched,
            'unmatched': self.unmatched,
            'gdtf_missing': self.gdtf_missing,
            'mode_missing': self.mode_missing,
            'error': self.error,
            'match_rate': self.match_rate
        } 