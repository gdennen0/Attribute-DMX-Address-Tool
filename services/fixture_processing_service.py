"""
Unified Fixture Processing Service - Handles both MVR and CSV fixture data.
Provides standardized data extraction and processing for all fixture sources.
"""

from typing import Dict, List, Optional, Any, Union
from pathlib import Path
import uuid

from models.data_models import FixtureData, FixtureMatch
from services.mvr_service import MVRService
from services.csv_service import CSVService


class FixtureProcessingService:
    """
    Unified service for processing fixture data from any source.
    Handles both MVR and CSV sources with standardized output.
    """
    
    def __init__(self):
        self.mvr_service = MVRService()
        self.csv_service = CSVService()
        self.universe_size = 512
    
    def load_fixtures_from_mvr(self, file_path: str) -> List[FixtureMatch]:
        """
        Load fixtures from MVR file and return standardized FixtureMatch objects.
        
        Args:
            file_path: Path to the MVR file
            
        Returns:
            List of FixtureMatch objects (unmatched, ready for GDTF matching)
        """
        # Load raw fixture data from MVR
        raw_fixtures = self.mvr_service.load_mvr_file(file_path)
        
        # Convert to standardized FixtureMatch objects
        fixture_matches = []
        for raw_fixture in raw_fixtures:
            fixture_match = self._convert_raw_data_to_fixture_match(raw_fixture)
            fixture_matches.append(fixture_match)
        
        return fixture_matches
    
    def load_fixtures_from_csv(self, file_path: str, column_mapping: Dict[str, int], 
                             fixture_id_config: Dict[str, Any]) -> List[FixtureMatch]:
        """
        Load fixtures from CSV file and return standardized FixtureMatch objects.
        
        Args:
            file_path: Path to the CSV file
            column_mapping: Mapping of required fields to column indices
            fixture_id_config: Configuration for fixture ID generation
            
        Returns:
            List of FixtureMatch objects (unmatched, ready for GDTF matching)
        """
        # Load and process CSV data
        headers, data_rows = self.csv_service.load_csv_file(file_path)
        fixtures = self.csv_service.process_csv_data(headers, data_rows, column_mapping, fixture_id_config)
        
        # Convert to standardized FixtureMatch objects
        fixture_matches = []
        for fixture in fixtures:
            fixture_match = self._convert_fixture_data_to_fixture_match(fixture)
            fixture_matches.append(fixture_match)
        
        return fixture_matches
    
    def load_fixtures_from_csv_data(self, headers: List[str], data_rows: List[List[str]], 
                                   column_mapping: Dict[str, int], 
                                   fixture_id_config: Dict[str, Any]) -> List[FixtureMatch]:
        """
        Load fixtures from CSV data and return standardized FixtureMatch objects.
        
        Args:
            headers: CSV headers
            data_rows: CSV data rows
            column_mapping: Mapping of required fields to column indices
            fixture_id_config: Configuration for fixture ID generation
            
        Returns:
            List of FixtureMatch objects (unmatched, ready for GDTF matching)
        """
        # Process CSV data
        fixtures = self.csv_service.process_csv_data(headers, data_rows, column_mapping, fixture_id_config)
        
        # Convert to standardized FixtureMatch objects
        fixture_matches = []
        for fixture in fixtures:
            fixture_match = self._convert_fixture_data_to_fixture_match(fixture)
            fixture_matches.append(fixture_match)
        
        return fixture_matches
    
    def _convert_raw_data_to_fixture_match(self, raw_fixture: Dict[str, Any]) -> FixtureMatch:
        """Convert raw MVR fixture data to standardized FixtureMatch object."""
        return FixtureMatch(
            name=raw_fixture.get('name', 'Unknown'),
            uuid=raw_fixture.get('uuid', str(uuid.uuid4())),
            gdtf_spec=raw_fixture.get('gdtf_spec', ''),
            gdtf_mode=raw_fixture.get('gdtf_mode', ''),
            base_address=raw_fixture.get('base_address', 1),
            fixture_id=raw_fixture.get('fixture_id', 0),
            gdtf_profile=None,
            matched_mode=None,
            attribute_offsets={},
            match_status="gdtf_missing"  # All fixtures start unmatched
        )
    
    def _convert_fixture_data_to_fixture_match(self, fixture: FixtureData) -> FixtureMatch:
        """Convert FixtureData to standardized FixtureMatch object."""
        return FixtureMatch(
            name=fixture.name,
            uuid=fixture.uuid,
            gdtf_spec=fixture.gdtf_spec,
            gdtf_mode=fixture.gdtf_mode,
            base_address=fixture.base_address,
            fixture_id=fixture.fixture_id,
            gdtf_profile=None,
            matched_mode=None,
            attribute_offsets={},
            match_status="gdtf_missing"  # All fixtures start unmatched
        )
    
    def get_fixture_summary(self, fixtures: List[FixtureMatch]) -> Dict[str, Any]:
        """
        Get summary information about fixtures.
        
        Args:
            fixtures: List of FixtureMatch objects
            
        Returns:
            Dictionary with fixture summary statistics
        """
        if not fixtures:
            return {
                "total_fixtures": 0,
                "fixture_types": [],
                "fixture_type_counts": {},
                "address_range": None
            }
        
        # Count fixtures by type
        fixture_type_counts = {}
        for fixture in fixtures:
            fixture_type = fixture.gdtf_spec or "Unknown"
            fixture_type_counts[fixture_type] = fixture_type_counts.get(fixture_type, 0) + 1
        
        # Calculate address range
        addresses = [f.base_address for f in fixtures if f.base_address > 0]
        address_range = None
        if addresses:
            address_range = {
                "min": min(addresses),
                "max": max(addresses),
                "span": max(addresses) - min(addresses) + 1
            }
        
        return {
            "total_fixtures": len(fixtures),
            "fixture_types": sorted(fixture_type_counts.keys()),
            "fixture_type_counts": fixture_type_counts,
            "address_range": address_range
        }
    
    def validate_fixtures(self, fixtures: List[FixtureMatch]) -> Dict[str, Any]:
        """
        Validate fixture data for common issues.
        
        Args:
            fixtures: List of FixtureMatch objects
            
        Returns:
            Dictionary with validation results
        """
        issues = []
        warnings = []
        
        # Check for duplicate fixture IDs
        fixture_ids = [f.fixture_id for f in fixtures]
        duplicates = set([x for x in fixture_ids if fixture_ids.count(x) > 1])
        if duplicates:
            issues.append(f"Duplicate fixture IDs found: {sorted(duplicates)}")
        
        # Check for address conflicts
        base_addresses = [f.base_address for f in fixtures]
        address_duplicates = set([x for x in base_addresses if base_addresses.count(x) > 1])
        if address_duplicates:
            warnings.append(f"Duplicate base addresses found: {sorted(address_duplicates)}")
        
        # Check for missing fixture types
        missing_types = [f.fixture_id for f in fixtures if not f.gdtf_spec or f.gdtf_spec == "Unknown"]
        if missing_types:
            warnings.append(f"Fixtures with missing/unknown types: {len(missing_types)} fixtures")
        
        return {
            "is_valid": len(issues) == 0,
            "issues": issues,
            "warnings": warnings,
            "fixture_count": len(fixtures)
        } 