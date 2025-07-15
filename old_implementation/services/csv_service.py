"""
CSV Service - Handles CSV file operations and analysis.
Clean separation of CSV business logic for arbitrary fixture data imports.
"""

import csv
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import re

from models.data_models import FixtureData, FixtureMatch


class CSVService:
    """
    Service for handling CSV file operations and analysis.
    Provides clean interface for CSV loading, parsing, and column mapping.
    """
    
    def __init__(self):
        self.universe_size = 512
        self.fixture_id_generators = {
            'sequential': self._generate_sequential_ids,
            'desk_channel': self._generate_from_desk_channel,
            'dmx_address': self._generate_from_dmx_address,
            'custom_start': self._generate_custom_sequential_ids
        }
    
    def load_csv_file(self, file_path: str) -> Tuple[List[str], List[List[str]]]:
        """
        Load CSV file and return headers and data rows.
        
        Args:
            file_path: Path to the CSV file
            
        Returns:
            Tuple of (headers, data_rows)
        """
        csv_path = Path(file_path)
        if not csv_path.exists():
            raise FileNotFoundError(f"CSV file not found: {file_path}")
        
        try:
            with open(csv_path, 'r', encoding='utf-8', newline='') as file:
                # Try to detect delimiter
                sample = file.read(1024)
                file.seek(0)
                
                sniffer = csv.Sniffer()
                try:
                    delimiter = sniffer.sniff(sample).delimiter
                except csv.Error:
                    # If delimiter detection fails, default to comma
                    delimiter = ','
                
                reader = csv.reader(file, delimiter=delimiter)
                rows = list(reader)
                
                if not rows:
                    raise ValueError("CSV file is empty")
                
                headers = rows[0]
                data_rows = [row for row in rows[1:] if any(cell.strip() for cell in row)]  # Skip empty rows
                
                # Clean headers and data rows
                headers = [header.strip() for header in headers]
                cleaned_data_rows = []
                
                for row in data_rows:
                    # Pad row to match header length if needed
                    while len(row) < len(headers):
                        row.append('')
                    
                    # Clean each cell by stripping whitespace
                    cleaned_row = [cell.strip() for cell in row]
                    
                    # Only include rows that have at least one non-empty cell
                    if any(cell for cell in cleaned_row):
                        cleaned_data_rows.append(cleaned_row)
                
                return headers, cleaned_data_rows
                
        except Exception as e:
            raise Exception(f"Error loading CSV file: {e}")
    
    def process_csv_data(self, headers: List[str], data_rows: List[List[str]], 
                        column_mapping: Dict[str, int], fixture_id_config: Dict[str, Any]) -> List[FixtureData]:
        """
        Process CSV data into FixtureData objects.
        
        Args:
            headers: CSV headers
            data_rows: CSV data rows
            column_mapping: Mapping of required fields to column indices
            fixture_id_config: Configuration for fixture ID generation
            
        Returns:
            List of FixtureData objects
        """
        fixtures = []
        
        # Generate fixture IDs based on configuration
        fixture_ids = self._generate_fixture_ids(data_rows, column_mapping, fixture_id_config)
        
        for i, row in enumerate(data_rows):
            try:
                # Skip rows that don't have essential data
                if not self._is_valid_fixture_row(row, column_mapping):
                    continue
                
                # Extract data from row
                fixture_data = self._extract_fixture_data(row, column_mapping, fixture_ids[i])
                
                if fixture_data:
                    fixtures.append(fixture_data)
                    
            except Exception as e:
                print(f"Warning: Could not process row {i+1}: {e}")
                continue
        
        return fixtures
    
    def _is_valid_fixture_row(self, row: List[str], column_mapping: Dict[str, int]) -> bool:
        """Check if a row has the minimum required data for a fixture."""
        # Must have at least a name/description and universe/DMX info
        name_col = column_mapping.get('name', -1)
        universe_col = column_mapping.get('universe', -1)
        dmx_col = column_mapping.get('dmx_address', -1)
        
        # Check name column
        if name_col >= 0 and len(row) > name_col:
            name = row[name_col].strip()
            if not name:
                return False
        else:
            return False
        
        # Check universe column
        if universe_col >= 0 and len(row) > universe_col:
            universe = row[universe_col].strip()
            if not universe:
                return False
            try:
                universe_val = int(universe)
                if universe_val < 1:
                    return False
            except ValueError:
                return False
        else:
            return False
        
        # Check DMX address column
        if dmx_col >= 0 and len(row) > dmx_col:
            dmx = row[dmx_col].strip()
            if not dmx:
                return False
            try:
                dmx_val = int(dmx)
                if dmx_val < 1 or dmx_val > 512:
                    return False
            except ValueError:
                return False
        else:
            return False
        
        return True
    
    def _extract_fixture_data(self, row: List[str], column_mapping: Dict[str, int], fixture_id: int) -> Optional[FixtureData]:
        """Extract fixture data from a CSV row."""
        try:
            # Extract name (combine multiple fields if needed)
            name_parts = []
            for field in ['space', 'description', 'arch_zone']:
                col_idx = column_mapping.get(field, -1)
                if col_idx >= 0 and len(row) > col_idx:
                    part = row[col_idx].strip()
                    if part:
                        name_parts.append(part)
            
            if not name_parts:
                # Fallback to name column
                name_col = column_mapping.get('name', -1)
                if name_col >= 0 and len(row) > name_col:
                    name = row[name_col].strip()
                    if name:
                        name_parts.append(name)
            
            name = ' - '.join(name_parts) if name_parts else f"Fixture {fixture_id}"
            
            # Extract universe with validation
            universe_col = column_mapping.get('universe', -1)
            if universe_col >= 0 and len(row) > universe_col:
                universe_str = row[universe_col].strip()
                try:
                    universe = int(universe_str)
                    if universe < 1:
                        universe = 1
                except ValueError:
                    universe = 1
            else:
                universe = 1
            
            # Extract DMX address with validation
            dmx_col = column_mapping.get('dmx_address', -1)
            if dmx_col >= 0 and len(row) > dmx_col:
                dmx_str = row[dmx_col].strip()
                try:
                    dmx_address = int(dmx_str)
                    if dmx_address < 1 or dmx_address > 512:
                        dmx_address = 1
                except ValueError:
                    dmx_address = 1
            else:
                dmx_address = 1
            
            # Calculate base address (universe and DMX to absolute address)
            base_address = (universe - 1) * self.universe_size + dmx_address
            
            # Extract fixture type with cleaning
            fixture_type_col = column_mapping.get('fixture_type', -1)
            if fixture_type_col >= 0 and len(row) > fixture_type_col:
                fixture_type = row[fixture_type_col].strip()
                if not fixture_type:
                    fixture_type = "Unknown"
            else:
                fixture_type = "Unknown"
            
            # Extract mode with cleaning
            mode_col = column_mapping.get('mode', -1)
            if mode_col >= 0 and len(row) > mode_col:
                mode = row[mode_col].strip()
                if not mode:
                    mode = "Standard"
            else:
                mode = "Standard"
            
            # Generate UUID for fixture
            fixture_uuid = str(uuid.uuid4())
            
            return FixtureData(
                name=name,
                uuid=fixture_uuid,
                gdtf_spec=fixture_type,  # We'll map this to GDTF later
                gdtf_mode=mode,
                base_address=base_address,
                fixture_id=fixture_id,
                position=None,
                rotation=None
            )
            
        except Exception as e:
            print(f"Error extracting fixture data: {e}")
            return None
    
    def _generate_fixture_ids(self, data_rows: List[List[str]], 
                             column_mapping: Dict[str, int], 
                             fixture_id_config: Dict[str, Any]) -> List[int]:
        """Generate fixture IDs based on configuration."""
        method = fixture_id_config.get('method', 'sequential')
        
        if method not in self.fixture_id_generators:
            method = 'sequential'
        
        return self.fixture_id_generators[method](data_rows, column_mapping, fixture_id_config)
    
    def _generate_sequential_ids(self, data_rows: List[List[str]], 
                                column_mapping: Dict[str, int], 
                                fixture_id_config: Dict[str, Any]) -> List[int]:
        """Generate sequential fixture IDs starting from 1."""
        return list(range(1, len(data_rows) + 1))
    
    def _generate_custom_sequential_ids(self, data_rows: List[List[str]], 
                                       column_mapping: Dict[str, int], 
                                       fixture_id_config: Dict[str, Any]) -> List[int]:
        """Generate sequential fixture IDs starting from a custom number."""
        start_num = fixture_id_config.get('start_number', 1)
        return list(range(start_num, start_num + len(data_rows)))
    
    def _generate_from_desk_channel(self, data_rows: List[List[str]], 
                                   column_mapping: Dict[str, int], 
                                   fixture_id_config: Dict[str, Any]) -> List[int]:
        """Generate fixture IDs from desk channel column."""
        desk_channel_col = column_mapping.get('desk_channel', -1)
        ids = []
        
        for row in data_rows:
            if desk_channel_col >= 0 and len(row) > desk_channel_col:
                try:
                    # Extract numeric part from desk channel
                    desk_channel = row[desk_channel_col].strip()
                    # Remove any non-numeric characters
                    numeric_part = re.sub(r'[^0-9]', '', desk_channel)
                    if numeric_part:
                        ids.append(int(numeric_part))
                    else:
                        ids.append(len(ids) + 1)  # Fallback
                except (ValueError, IndexError):
                    ids.append(len(ids) + 1)  # Fallback
            else:
                ids.append(len(ids) + 1)  # Fallback
        
        return ids
    
    def _generate_from_dmx_address(self, data_rows: List[List[str]], 
                                  column_mapping: Dict[str, int], 
                                  fixture_id_config: Dict[str, Any]) -> List[int]:
        """Generate fixture IDs from DMX address."""
        dmx_col = column_mapping.get('dmx_address', -1)
        ids = []
        
        for row in data_rows:
            if dmx_col >= 0 and len(row) > dmx_col:
                try:
                    dmx_address = int(row[dmx_col].strip())
                    ids.append(dmx_address)
                except (ValueError, IndexError):
                    ids.append(len(ids) + 1)  # Fallback
            else:
                ids.append(len(ids) + 1)  # Fallback
        
        return ids
    
    def convert_to_fixture_matches(self, fixtures: List[FixtureData]) -> List[FixtureMatch]:
        """Convert FixtureData objects to FixtureMatch objects for analysis."""
        matches = []
        
        for fixture in fixtures:
            match = FixtureMatch(
                name=fixture.name,
                uuid=fixture.uuid,
                gdtf_spec=fixture.gdtf_spec,
                gdtf_mode=fixture.gdtf_mode,
                base_address=fixture.base_address,
                fixture_id=fixture.fixture_id,
                match_status="gdtf_missing"  # Will be updated during GDTF matching
            )
            matches.append(match)
        
        return matches
    
    def get_suggested_column_mapping(self, headers: List[str]) -> Dict[str, int]:
        """
        Suggest column mappings based on header names.
        
        Args:
            headers: List of CSV headers
            
        Returns:
            Dictionary mapping required fields to suggested column indices
        """
        mapping = {}
        
        # Define mapping patterns
        patterns = {
            'name': ['name', 'description', 'fixture name', 'fixture'],
            'space': ['space', 'room', 'studio', 'location', 'area'],
            'description': ['description', 'desc', 'location', 'position'],
            'arch_zone': ['arch zone', 'zone', 'architectural zone', 'arch_zone'],
            'desk_channel': ['desk chan', 'desk channel', 'channel', 'chan', 'desk'],
            'universe': ['univ', 'universe', 'uni', 'dmx universe'],
            'dmx_address': ['dmx', 'dmx address', 'address', 'dmx_address', 'dmx_addr'],
            'mode': ['mode', 'fixture mode', 'dmx mode', 'channel mode'],
            'fixture_type': ['fixture type', 'type', 'fixture_type', 'model', 'manufacturer'],
            'note': ['note', 'notes', 'comment', 'comments', 'remark']
        }
        
        # Find best matches for each field
        for field, pattern_list in patterns.items():
            best_match = -1
            best_score = 0
            
            for i, header in enumerate(headers):
                header_lower = header.lower().strip()
                
                for pattern in pattern_list:
                    pattern_lower = pattern.lower()
                    
                    # Exact match gets highest score
                    if header_lower == pattern_lower:
                        score = 100
                    # Partial match
                    elif pattern_lower in header_lower or header_lower in pattern_lower:
                        score = 50
                    # Contains key words
                    elif any(word in header_lower for word in pattern_lower.split()):
                        score = 25
                    else:
                        score = 0
                    
                    if score > best_score:
                        best_score = score
                        best_match = i
            
            if best_match >= 0:
                mapping[field] = best_match
        
        return mapping
    
    def get_fixture_id_generation_options(self) -> List[Dict[str, Any]]:
        """Get available fixture ID generation options."""
        return [
            {
                'method': 'sequential',
                'name': 'Sequential (1, 2, 3, ...)',
                'description': 'Generate fixture IDs sequentially starting from 1',
                'requires_input': False
            },
            {
                'method': 'custom_start',
                'name': 'Sequential from custom number',
                'description': 'Generate fixture IDs sequentially starting from a number you specify',
                'requires_input': True,
                'input_label': 'Starting number:'
            },
            {
                'method': 'desk_channel',
                'name': 'Use Desk Channel',
                'description': 'Use the desk channel column as fixture IDs',
                'requires_input': False
            },
            {
                'method': 'dmx_address',
                'name': 'Use DMX Address',
                'description': 'Use the DMX address as fixture IDs',
                'requires_input': False
            }
        ] 