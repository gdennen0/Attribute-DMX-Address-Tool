"""
Simple CSV file parser.
Reads CSV files and converts them to fixture data using minimal, clean functions.
"""

import csv
from typing import List, Dict, Any, Optional
from pathlib import Path

from .data import create_fixture


def parse_csv_file(csv_path: str, column_mapping: Dict[str, str], 
                  start_fixture_id: int = 1) -> Dict[str, Any]:
    """Parse CSV file and extract fixture data."""
    try:
        with open(csv_path, 'r', newline='', encoding='utf-8') as file:
            # Detect CSV dialect
            sample = file.read(1024)
            file.seek(0)
            sniffer = csv.Sniffer()
            dialect = sniffer.sniff(sample)
            
            # Read CSV data
            reader = csv.DictReader(file, dialect=dialect)
            rows = list(reader)
            
            if not rows:
                return {'error': 'CSV file is empty'}
            
            # Get available columns
            available_columns = list(rows[0].keys())
            
            # Convert rows to fixtures
            fixtures = _convert_rows_to_fixtures(rows, column_mapping, start_fixture_id)
            
            return {
                'fixtures': fixtures,
                'available_columns': available_columns,
                'success': True
            }
            
    except Exception as e:
        return {'error': f'Failed to parse CSV file: {str(e)}'}


def parse_csv_file_with_fixture_id_validation(csv_path: str, column_mapping: Dict[str, str], 
                                             start_fixture_id: int = 1) -> Dict[str, Any]:
    """Parse CSV file and extract fixture data with fixture ID validation."""
    try:
        with open(csv_path, 'r', newline='', encoding='utf-8') as file:
            # Detect CSV dialect
            sample = file.read(1024)
            file.seek(0)
            sniffer = csv.Sniffer()
            dialect = sniffer.sniff(sample)
            
            # Read CSV data
            reader = csv.DictReader(file, dialect=dialect)
            rows = list(reader)
            
            if not rows:
                return {'error': 'CSV file is empty'}
            
            # Get available columns
            available_columns = list(rows[0].keys())
            
            # Convert rows to fixtures with validation
            fixtures = _convert_rows_to_fixtures_with_validation(rows, column_mapping, start_fixture_id)
            
            return {
                'fixtures': fixtures,
                'available_columns': available_columns,
                'success': True
            }
            
    except Exception as e:
        return {'error': f'Failed to parse CSV file: {str(e)}'}


def _convert_rows_to_fixtures(rows: List[Dict[str, str]], 
                             column_mapping: Dict[str, str],
                             start_fixture_id: int) -> List[Dict[str, Any]]:
    """Convert CSV rows to fixture dictionaries."""
    fixtures = []
    fixture_id = start_fixture_id
    
    for row in rows:
        # Extract mapped values
        name = row.get(column_mapping.get('name', ''), f'Fixture_{fixture_id}')
        fixture_type = row.get(column_mapping.get('type', ''), 'Unknown')
        mode = row.get(column_mapping.get('mode', ''), 'Default')
        
        # Parse universe and address from CSV
        csv_universe = None
        csv_channel = None
        base_address = 1
        
        universe_str = row.get(column_mapping.get('universe', ''), '')
        address_str = row.get(column_mapping.get('address', ''), '')
        
        if universe_str and address_str:
            # We have both universe and address from CSV
            try:
                csv_universe = int(universe_str)
                csv_channel = int(address_str)
                if csv_universe >= 1 and csv_channel >= 1 and csv_channel <= 512:
                    base_address = (csv_universe - 1) * 512 + csv_channel
                else:
                    csv_universe = 1
                    csv_channel = 1
                    base_address = 1
            except ValueError:
                csv_universe = 1
                csv_channel = 1
                base_address = 1
        elif address_str:
            # We have only address - assume it's the channel value (universe 1)
            try:
                csv_channel = int(address_str)
                if csv_channel < 1 or csv_channel > 512:
                    csv_channel = 1
                csv_universe = 1
                # Calculate absolute address: (universe - 1) * 512 + channel
                base_address = csv_channel  # Universe 1, so (1-1) * 512 + channel = channel
            except ValueError:
                csv_universe = 1
                csv_channel = 1
                base_address = 1
        else:
            # No address information provided
            csv_universe = 1
            csv_channel = 1
            base_address = 1
        
        # Parse fixture ID if provided
        id_str = row.get(column_mapping.get('fixture_id', ''), str(fixture_id))
        try:
            parsed_id = int(id_str)
        except ValueError:
            parsed_id = fixture_id
        
        fixture = create_fixture(
            name=name,
            fixture_type=fixture_type,
            mode=mode,
            base_address=base_address,
            fixture_id=parsed_id
        )
        
        # Store the CSV universe and channel values for reference
        fixture['csv_universe'] = csv_universe
        fixture['csv_channel'] = csv_channel
        
        fixtures.append(fixture)
        fixture_id += 1
    
    return fixtures


def _convert_rows_to_fixtures_with_validation(rows: List[Dict[str, str]], 
                                             column_mapping: Dict[str, str],
                                             start_fixture_id: int) -> List[Dict[str, Any]]:
    """Convert CSV rows to fixture dictionaries with fixture ID validation."""
    fixtures = []
    fixture_id = start_fixture_id
    
    for row in rows:
        # Extract mapped values
        name = row.get(column_mapping.get('name', ''), f'Fixture_{fixture_id}')
        fixture_type = row.get(column_mapping.get('type', ''), 'Unknown')
        mode = row.get(column_mapping.get('mode', ''), 'Default')
        
        # Parse universe and address from CSV
        csv_universe = None
        csv_channel = None
        base_address = 1
        
        universe_str = row.get(column_mapping.get('universe', ''), '')
        address_str = row.get(column_mapping.get('address', ''), '')
        
        if universe_str and address_str:
            # We have both universe and address from CSV
            try:
                csv_universe = int(universe_str)
                csv_channel = int(address_str)
                if csv_universe >= 1 and csv_channel >= 1 and csv_channel <= 512:
                    base_address = (csv_universe - 1) * 512 + csv_channel
                else:
                    csv_universe = 1
                    csv_channel = 1
                    base_address = 1
            except ValueError:
                csv_universe = 1
                csv_channel = 1
                base_address = 1
        elif address_str:
            # We have only address - assume it's the channel value (universe 1)
            try:
                csv_channel = int(address_str)
                if csv_channel < 1 or csv_channel > 512:
                    csv_channel = 1
                csv_universe = 1
                # Calculate absolute address: (universe - 1) * 512 + channel
                base_address = csv_channel  # Universe 1, so (1-1) * 512 + channel = channel
            except ValueError:
                csv_universe = 1
                csv_channel = 1
                base_address = 1
        else:
            # No address information provided
            csv_universe = 1
            csv_channel = 1
            base_address = 1
        
        # Parse fixture ID with validation
        id_str = row.get(column_mapping.get('fixture_id', ''), '')
        parsed_id = None
        
        if id_str:
            try:
                parsed_id = int(id_str)
            except ValueError:
                # Invalid fixture ID - will be handled by the dialog
                parsed_id = None
        
        if parsed_id is None:
            # Use sequential ID as fallback
            parsed_id = fixture_id
        
        fixture = create_fixture(
            name=name,
            fixture_type=fixture_type,
            mode=mode,
            base_address=base_address,
            fixture_id=parsed_id
        )
        
        # Store the CSV universe and channel values for reference
        fixture['csv_universe'] = csv_universe
        fixture['csv_channel'] = csv_channel
        
        # Mark if fixture ID was invalid
        if id_str and parsed_id == fixture_id:
            fixture['fixture_id_invalid'] = True
            fixture['original_fixture_id'] = id_str
        
        fixtures.append(fixture)
        fixture_id += 1
    
    return fixtures


def get_csv_preview(csv_path: str, max_rows: int = None) -> Dict[str, Any]:
    """Get a preview of CSV file contents.
    
    Args:
        csv_path: Path to the CSV file
        max_rows: Maximum number of rows to preview. If None, previews all rows up to 10000.
    """
    try:
        with open(csv_path, 'r', newline='', encoding='utf-8') as file:
            # Detect CSV dialect
            sample = file.read(1024)
            file.seek(0)
            sniffer = csv.Sniffer()
            dialect = sniffer.sniff(sample)
            
            # Read preview rows
            reader = csv.reader(file, dialect=dialect)
            rows = []
            
            # If max_rows is None, read all rows up to a safety limit
            if max_rows is None:
                max_rows = 10000  # Safety limit for extremely large files
            
            for i, row in enumerate(reader):
                if i >= max_rows:
                    break
                rows.append(row)
            
            if not rows:
                return {'error': 'CSV file is empty'}
            
            # First row is usually headers
            headers = rows[0] if rows else []
            data_rows = rows[1:] if len(rows) > 1 else []
            
            # Check if we hit the safety limit
            hit_limit = len(rows) >= max_rows
            
            return {
                'headers': headers,
                'data_rows': data_rows,
                'success': True,
                'total_rows_previewed': len(rows),
                'hit_limit': hit_limit
            }
            
    except Exception as e:
        return {'error': f'Failed to preview CSV file: {str(e)}'}


def create_column_mapping(headers: List[str]) -> Dict[str, str]:
    """Create initial column mapping by guessing from headers."""
    mapping = {
        'name': '',
        'type': '',
        'mode': '',
        'address': '',
        'universe': '',
        'fixture_id': ''
    }
    
    # Common header patterns
    name_patterns = ['name', 'fixture', 'label', 'unit', 'description']
    type_patterns = ['type', 'model', 'gdtf', 'fixture_type', 'fixtureType']
    mode_patterns = ['mode', 'dmx_mode', 'profile']
    address_patterns = ['address', 'dmx', 'channel', 'start_address', 'base_address', 'dmx_address']
    universe_patterns = ['universe', 'dmx_universe', 'univ']
    id_patterns = ['id', 'fixture_id', 'number', 'unit_number', 'desk chan']
    
    # Try to match headers to patterns
    for header in headers:
        header_lower = header.lower()
        
        if not mapping['name'] and any(pattern in header_lower for pattern in name_patterns):
            mapping['name'] = header
        elif not mapping['type'] and any(pattern in header_lower for pattern in type_patterns):
            mapping['type'] = header
        elif not mapping['mode'] and any(pattern in header_lower for pattern in mode_patterns):
            mapping['mode'] = header
        elif not mapping['address'] and any(pattern in header_lower for pattern in address_patterns):
            mapping['address'] = header
        elif not mapping['universe'] and any(pattern in header_lower for pattern in universe_patterns):
            mapping['universe'] = header
        elif not mapping['fixture_id'] and any(pattern in header_lower for pattern in id_patterns):
            mapping['fixture_id'] = header
    
    return mapping


def validate_csv_file(csv_path: str) -> bool:
    """Check if file is a valid CSV file."""
    try:
        if not csv_path.endswith('.csv'):
            return False
        
        with open(csv_path, 'r', newline='', encoding='utf-8') as file:
            # Try to read first few lines
            sample = file.read(1024)
            if not sample.strip():
                return False
            
            # Try to detect CSV dialect
            sniffer = csv.Sniffer()
            sniffer.sniff(sample)
            return True
            
    except:
        return False


def get_fixture_count(csv_path: str) -> int:
    """Get number of fixtures in CSV file."""
    try:
        with open(csv_path, 'r', newline='', encoding='utf-8') as file:
            reader = csv.reader(file)
            row_count = sum(1 for row in reader)
            # Subtract 1 for header row
            return max(0, row_count - 1)
    except:
        return 0 