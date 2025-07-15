"""
Simple MVR file parser.
Extracts fixture data from MVR files using minimal, clean functions.
"""

import zipfile
import xml.etree.ElementTree as ET
from typing import List, Dict, Any, Optional
from pathlib import Path
import tempfile
import os

from .data import create_fixture


def parse_mvr_file(mvr_path: str) -> Dict[str, Any]:
    """Parse MVR file and extract fixture data."""
    try:
        with zipfile.ZipFile(mvr_path, 'r') as zip_file:
            # Extract main XML content using flexible approach like old implementation
            xml_content = _extract_mvr_xml(zip_file)
            
            # Parse XML
            root = ET.fromstring(xml_content)
            fixtures = _extract_fixtures_from_xml(root)
            
            # Extract GDTF files for embedded profiles
            gdtf_profiles = _extract_gdtf_profiles(zip_file)
            
            return {
                'fixtures': fixtures,
                'gdtf_profiles': gdtf_profiles,
                'success': True
            }
            
    except Exception as e:
        return {'error': f'Failed to parse MVR file: {str(e)}'}


def _extract_mvr_xml(zip_file: zipfile.ZipFile) -> str:
    """Extract XML content from MVR file using flexible approach like old implementation."""
    try:
        # Look for all XML files
        xml_files = [f for f in zip_file.namelist() if f.endswith('.xml')]
        
        if not xml_files:
            raise ValueError("No XML files found in MVR archive")
        
        # Try to find the main scene description file
        main_xml = None
        for xml_file in xml_files:
            if 'GeneralSceneDescription' in xml_file or 'Scene' in xml_file:
                main_xml = xml_file
                break
        
        # If no main scene file found, use the first XML file
        if not main_xml:
            main_xml = xml_files[0]
        
        # Extract and decode the XML content
        with zip_file.open(main_xml) as xml_content:
            content = xml_content.read().decode('utf-8')
            return content
            
    except Exception as e:
        raise Exception(f"Error extracting MVR content: {e}")


def _extract_fixtures_from_xml(root: ET.Element) -> List[Dict[str, Any]]:
    """Extract fixture data from XML root element."""
    fixtures = []
    fixture_id_counter = 1
    
    # Find all fixture elements
    for layer in root.findall('.//Layer'):
        for child_list in layer.findall('.//ChildList'):
            for fixture_elem in child_list.findall('.//Fixture'):
                fixture_data = _parse_fixture_element(fixture_elem, fixture_id_counter)
                if fixture_data:
                    fixtures.append(fixture_data)
                    fixture_id_counter += 1
    
    return fixtures


def _parse_fixture_element(fixture_elem: ET.Element, fixture_id: int) -> Optional[Dict[str, Any]]:
    """Parse individual fixture element."""
    try:
        # Get basic fixture info
        name = fixture_elem.get('name', f'Fixture_{fixture_id}')
        uuid = fixture_elem.get('uuid', '')
        
        # Get GDTF spec - try both .text and .get('value') approaches
        gdtf_spec_elem = fixture_elem.find('GDTFSpec')
        gdtf_spec = ''
        if gdtf_spec_elem is not None:
            # Try .text first (old implementation approach)
            gdtf_spec = gdtf_spec_elem.text or gdtf_spec_elem.get('value', '') or ''
        
        if not gdtf_spec:
            # Still create fixture even without GDTF spec
            gdtf_spec = 'Unknown'
        
        # Get GDTF mode - try both approaches
        gdtf_mode_elem = fixture_elem.find('GDTFMode')
        gdtf_mode = ''
        if gdtf_mode_elem is not None:
            gdtf_mode = gdtf_mode_elem.text or gdtf_mode_elem.get('value', '') or ''
        
        # Get addresses - try both approaches
        base_address = 1
        addresses_elem = fixture_elem.find('Addresses')
        if addresses_elem is not None:
            address_elem = addresses_elem.find('Address')
            if address_elem is not None:
                try:
                    # Try .text first, then .get('value')
                    address_value = address_elem.text or address_elem.get('value', '1')
                    base_address = int(address_value)
                except (ValueError, TypeError):
                    base_address = 1
        
        # Get fixture ID - look for FixtureID element like old implementation
        parsed_fixture_id = fixture_id
        fixture_id_elem = fixture_elem.find('FixtureID')
        if fixture_id_elem is not None:
            try:
                parsed_fixture_id = int(fixture_id_elem.text or fixture_id_elem.get('value', str(fixture_id)))
            except (ValueError, TypeError):
                parsed_fixture_id = fixture_id
        
        return create_fixture(
            name=name,
            fixture_type=gdtf_spec,
            mode=gdtf_mode,
            base_address=base_address,
            fixture_id=parsed_fixture_id,
            uuid=uuid
        )
        
    except Exception as e:
        print(f"Warning: Could not extract fixture data: {e}")
        return None


def _extract_gdtf_profiles(zip_file: zipfile.ZipFile) -> Dict[str, Dict[str, Any]]:
    """Extract and parse GDTF profiles from MVR file."""
    gdtf_profiles = {}
    
    # Find GDTF files in the archive
    for file_name in zip_file.namelist():
        if file_name.endswith('.gdtf'):
            try:
                profile_name = Path(file_name).stem
                gdtf_data = _parse_gdtf_file_from_zip(zip_file, file_name)
                if gdtf_data:
                    gdtf_profiles[profile_name] = gdtf_data
            except Exception as e:
                print(f"Error parsing GDTF file {file_name}: {e}")
    
    return gdtf_profiles


def _parse_gdtf_file_from_zip(zip_file: zipfile.ZipFile, gdtf_filename: str) -> Optional[Dict[str, Any]]:
    """Parse GDTF file from within MVR zip."""
    try:
        # Extract GDTF file to temporary location
        gdtf_data = zip_file.read(gdtf_filename)
        
        with tempfile.NamedTemporaryFile(suffix='.gdtf', delete=False) as temp_file:
            temp_file.write(gdtf_data)
            temp_path = temp_file.name
        
        try:
            # Parse the GDTF file
            import core.gdtf_parser as gdtf_parser
            return gdtf_parser.parse_gdtf_file(temp_path)
        finally:
            # Clean up temporary file
            if os.path.exists(temp_path):
                os.unlink(temp_path)
                
    except Exception as e:
        print(f"Error extracting GDTF from zip: {e}")
        return None


def validate_mvr_file(mvr_path: str) -> bool:
    """Check if file is a valid MVR file."""
    try:
        # Accept .mvr files primarily, but be flexible with extensions
        if not (mvr_path.endswith('.mvr') or mvr_path.endswith('.zip')):
            return False
        
        with zipfile.ZipFile(mvr_path, 'r') as zip_file:
            # Look for any XML files (more flexible like old implementation)
            xml_files = [f for f in zip_file.namelist() if f.endswith('.xml')]
            
            # Valid if we have at least one XML file
            return len(xml_files) > 0
        
    except zipfile.BadZipFile:
        return False
    except:
        return False 