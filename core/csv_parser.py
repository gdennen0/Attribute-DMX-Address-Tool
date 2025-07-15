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
        
        # Parse base address
        address_str = row.get(column_mapping.get('address', ''), '1')
        try:
            base_address = int(address_str)
        except ValueError:
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
        
        fixtures.append(fixture)
        fixture_id += 1
    
    return fixtures


def get_csv_preview(csv_path: str, max_rows: int = 10) -> Dict[str, Any]:
    """Get a preview of CSV file contents."""
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
            for i, row in enumerate(reader):
                if i >= max_rows:
                    break
                rows.append(row)
            
            if not rows:
                return {'error': 'CSV file is empty'}
            
            # First row is usually headers
            headers = rows[0] if rows else []
            data_rows = rows[1:] if len(rows) > 1 else []
            
            return {
                'headers': headers,
                'data_rows': data_rows,
                'success': True
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
        'fixture_id': ''
    }
    
    # Common header patterns
    name_patterns = ['name', 'fixture', 'label', 'unit']
    type_patterns = ['type', 'model', 'gdtf', 'fixture_type', 'fixtureType']
    mode_patterns = ['mode', 'dmx_mode', 'profile']
    address_patterns = ['address', 'dmx', 'channel', 'start_address', 'base_address']
    id_patterns = ['id', 'fixture_id', 'number', 'unit_number']
    
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