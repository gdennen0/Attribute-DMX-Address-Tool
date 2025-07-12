"""
MVR Service - Handles MVR file operations and analysis.
Clean separation of MVR business logic.
"""

import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Optional, Any
import json
import csv
import io

from models.data_models import FixtureMatch, AnalysisResults, FixtureData


class MVRService:
    """
    Service for handling MVR file operations and analysis.
    Provides clean interface for MVR loading, parsing, and analysis.
    """
    
    def __init__(self):
        self.universe_size = 512
    
    def load_mvr_file(self, file_path: str) -> List[Dict]:
        """
        Load fixture data from an MVR file.
        
        Args:
            file_path: Path to the MVR file
            
        Returns:
            List of fixture data dictionaries
        """
        mvr_path = Path(file_path)
        if not mvr_path.exists():
            raise FileNotFoundError(f"MVR file not found: {file_path}")
        
        try:
            # Extract and parse MVR content
            xml_content = self._extract_mvr_xml(mvr_path)
            fixtures = self._parse_mvr_xml(xml_content)
            
            if not fixtures:
                raise ValueError("No fixtures found in MVR file")
            
            return fixtures
            
        except Exception as e:
            raise Exception(f"Error loading MVR file: {e}")
    
    def _extract_mvr_xml(self, mvr_path: Path) -> str:
        """Extract XML content from MVR file."""
        try:
            with zipfile.ZipFile(mvr_path, 'r') as zip_file:
                # Look for the main scene description file
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
                    
        except zipfile.BadZipFile:
            raise ValueError("File is not a valid MVR archive")
        except Exception as e:
            raise Exception(f"Error extracting MVR content: {e}")
    
    def _parse_mvr_xml(self, xml_content: str) -> List[Dict]:
        """Parse MVR XML content to extract fixture data."""
        try:
            root = ET.fromstring(xml_content)
            fixtures = []
            
            # Find all fixture elements
            for fixture_elem in root.findall('.//Fixture'):
                fixture_data = self._extract_fixture_data(fixture_elem)
                if fixture_data:
                    fixtures.append(fixture_data)
            
            return fixtures
            
        except ET.ParseError as e:
            raise Exception(f"Error parsing MVR XML: {e}")
    
    def _extract_fixture_data(self, fixture_elem) -> Optional[Dict]:
        """Extract fixture data from a single fixture XML element."""
        try:
            name = fixture_elem.get('name', 'Unknown')
            uuid = fixture_elem.get('uuid', '')
            
            # Extract GDTF specification
            gdtf_spec_elem = fixture_elem.find('GDTFSpec')
            gdtf_spec = gdtf_spec_elem.text if gdtf_spec_elem is not None else ''
            
            # Extract GDTF mode
            gdtf_mode_elem = fixture_elem.find('GDTFMode')
            gdtf_mode = gdtf_mode_elem.text if gdtf_mode_elem is not None else ''
            
            # Extract base address
            base_address = self._extract_base_address(fixture_elem)
            
            # Extract fixture ID
            fixture_id = self._extract_fixture_id(fixture_elem)
            
            # Extract position and rotation (optional)
            position = self._extract_transform(fixture_elem, 'position')
            rotation = self._extract_transform(fixture_elem, 'rotation')
            
            return {
                'name': name,
                'uuid': uuid,
                'gdtf_spec': gdtf_spec,
                'gdtf_mode': gdtf_mode,
                'base_address': base_address,
                'fixture_id': fixture_id,
                'position': position,
                'rotation': rotation
            }
            
        except Exception as e:
            print(f"Warning: Could not extract fixture data: {e}")
            return None
    
    def _extract_base_address(self, fixture_elem) -> int:
        """Extract base address from fixture element."""
        try:
            addresses_elem = fixture_elem.find('Addresses')
            if addresses_elem is not None:
                address_elem = addresses_elem.find('Address')
                if address_elem is not None:
                    return int(address_elem.text)
        except (ValueError, TypeError):
            pass
        return 1  # Default base address
    
    def _extract_fixture_id(self, fixture_elem) -> int:
        """Extract fixture ID from fixture element."""
        try:
            fixture_id_elem = fixture_elem.find('FixtureID')
            if fixture_id_elem is not None:
                return int(fixture_id_elem.text)
        except (ValueError, TypeError):
            pass
        return 0  # Default fixture ID
    
    def _extract_transform(self, fixture_elem, transform_type: str) -> Optional[Dict[str, float]]:
        """Extract transform data (position/rotation) from fixture element."""
        try:
            transform_elem = fixture_elem.find(transform_type.capitalize())
            if transform_elem is not None:
                return {
                    'x': float(transform_elem.get('x', 0)),
                    'y': float(transform_elem.get('y', 0)),
                    'z': float(transform_elem.get('z', 0))
                }
        except (ValueError, TypeError):
            pass
        return None
    
    def analyze_fixtures(self, fixtures: List[FixtureMatch], selected_attributes: List[str], 
                        output_format: str = "text", ma3_config: dict = None) -> AnalysisResults:
        """
        Analyze fixtures and calculate addresses for selected attributes.
        
        Args:
            fixtures: List of FixtureMatch objects
            selected_attributes: List of attribute names to analyze
            output_format: Output format for results
            
        Returns:
            AnalysisResults object with complete analysis
        """
        if not fixtures:
            raise ValueError("No fixtures provided for analysis")
        
        if not selected_attributes:
            raise ValueError("No attributes selected for analysis")
        
        # Calculate addresses for all fixtures
        fixtures_with_addresses = self._calculate_addresses(fixtures, selected_attributes)
        
        # Generate summary
        summary = self._generate_summary(fixtures_with_addresses, selected_attributes)
        
        # Generate export data
        export_data = self._generate_export_data(fixtures_with_addresses, selected_attributes, output_format, ma3_config)
        
        # Generate validation info
        validation_info = self._generate_validation_info(fixtures, selected_attributes)
        
        return AnalysisResults(
            fixtures=fixtures_with_addresses,
            summary=summary,
            selected_attributes=selected_attributes,
            output_format=output_format,
            export_data=export_data,
            validation_info=validation_info
        )
    
    def analyze_fixtures_by_type(self, fixtures: List[FixtureMatch], fixture_type_attributes: Dict[str, List[str]], 
                                output_format: str = "text", ma3_config: dict = None) -> AnalysisResults:
        """
        Analyze fixtures with per-fixture-type attributes.
        
        Args:
            fixtures: List of FixtureMatch objects
            fixture_type_attributes: Dict mapping fixture_type -> list of attribute names
            output_format: Output format for results
            
        Returns:
            AnalysisResults object with complete analysis
        """
        if not fixtures:
            raise ValueError("No fixtures provided for analysis")
        
        if not fixture_type_attributes:
            raise ValueError("No fixture type attributes provided for analysis")
        
        # Calculate addresses for all fixtures based on their fixture type
        fixtures_with_addresses = self._calculate_addresses_by_type(fixtures, fixture_type_attributes)
        
        # Collect all selected attributes across all fixture types
        all_selected_attributes = []
        for attrs in fixture_type_attributes.values():
            all_selected_attributes.extend(attrs)
        all_selected_attributes = sorted(list(set(all_selected_attributes)))
        
        # Generate summary
        summary = self._generate_summary_by_type(fixtures_with_addresses, fixture_type_attributes)
        
        # Generate export data
        export_data = self._generate_export_data_by_type(fixtures_with_addresses, fixture_type_attributes, output_format, ma3_config)
        
        # Generate validation info
        validation_info = self._generate_validation_info_by_type(fixtures, fixture_type_attributes)
        
        return AnalysisResults(
            fixtures=fixtures_with_addresses,
            summary=summary,
            selected_attributes=all_selected_attributes,
            output_format=output_format,
            export_data=export_data,
            validation_info=validation_info
        )
    
    def _calculate_addresses(self, fixtures: List[FixtureMatch], selected_attributes: List[str]) -> List[FixtureMatch]:
        """Calculate absolute addresses for all fixtures."""
        updated_fixtures = []
        
        for fixture in fixtures:
            if fixture.is_matched():
                # Calculate addresses for this fixture
                addresses = self._calculate_fixture_addresses(fixture, selected_attributes)
                fixture.absolute_addresses = addresses
            
            updated_fixtures.append(fixture)
        
        return updated_fixtures
    
    def _calculate_addresses_by_type(self, fixtures: List[FixtureMatch], fixture_type_attributes: Dict[str, List[str]]) -> List[FixtureMatch]:
        """Calculate absolute addresses for fixtures based on their fixture type."""
        updated_fixtures = []
        
        for fixture in fixtures:
            if fixture.is_matched():
                # Get attributes for this fixture type
                fixture_type = fixture.gdtf_spec or "Unknown"
                # Remove .gdtf extension for consistent naming
                fixture_type_clean = fixture_type.replace('.gdtf', '') if fixture_type.endswith('.gdtf') else fixture_type
                selected_attributes = fixture_type_attributes.get(fixture_type_clean, [])
                
                # Calculate addresses for this fixture
                addresses = self._calculate_fixture_addresses(fixture, selected_attributes)
                fixture.absolute_addresses = addresses
            
            updated_fixtures.append(fixture)
        
        return updated_fixtures
    
    def _calculate_fixture_addresses(self, fixture: FixtureMatch, selected_attributes: List[str]) -> Dict[str, Dict[str, int]]:
        """Calculate absolute addresses for a single fixture."""
        addresses = {}
        base_address = fixture.base_address
        
        for attr_name in selected_attributes:
            if attr_name in fixture.attribute_offsets:
                offset = fixture.attribute_offsets[attr_name]
                # Calculate absolute DMX address (1-based)
                # base_address is 1-based, offset is 1-based from GDTF
                absolute_address = base_address + (offset - 1)
                
                # Calculate universe and channel (both 1-based)
                # Convert to 0-based for calculation, then back to 1-based
                universe = ((absolute_address - 1) // self.universe_size) + 1
                channel = ((absolute_address - 1) % self.universe_size) + 1
                
                addresses[attr_name] = {
                    "universe": universe,
                    "channel": channel,
                    "absolute_address": absolute_address
                }
        
        return addresses
    
    def _generate_summary(self, fixtures: List[FixtureMatch], selected_attributes: List[str]) -> Dict[str, Any]:
        """Generate analysis summary."""
        summary = {
            "total_fixtures": len(fixtures),
            "matched_fixtures": sum(1 for f in fixtures if f.is_matched()),
            "universes_used": set(),
            "attribute_counts": {},
            "conflicts": []
        }
        
        # Track address usage and conflicts
        address_usage = {}
        
        for fixture in fixtures:
            if fixture.is_matched() and hasattr(fixture, 'absolute_addresses'):
                for attr_name, addr_info in fixture.absolute_addresses.items():
                    universe = addr_info["universe"]
                    channel = addr_info["channel"]
                    absolute_address = addr_info["absolute_address"]
                    
                    # Track universes used
                    summary["universes_used"].add(universe)
                    
                    # Track attribute counts
                    if attr_name not in summary["attribute_counts"]:
                        summary["attribute_counts"][attr_name] = 0
                    summary["attribute_counts"][attr_name] += 1
                    
                    # Check for address conflicts using absolute address
                    address_key = f"{absolute_address}"
                    if address_key in address_usage:
                        conflict = {
                            "address": f"DMX {absolute_address} (Universe {universe}, Channel {channel})",
                            "fixture1": address_usage[address_key]["fixture"],
                            "attr1": address_usage[address_key]["attribute"],
                            "fixture2": fixture.name,
                            "attr2": attr_name
                        }
                        summary["conflicts"].append(conflict)
                    else:
                        address_usage[address_key] = {
                            "fixture": fixture.name,
                            "attribute": attr_name
                        }
        
        summary["universes_used"] = sorted(list(summary["universes_used"]))
        return summary
    
    def _generate_summary_by_type(self, fixtures: List[FixtureMatch], fixture_type_attributes: Dict[str, List[str]]) -> Dict[str, Any]:
        """Generate analysis summary for per-fixture-type analysis."""
        summary = {
            "total_fixtures": len(fixtures),
            "matched_fixtures": sum(1 for f in fixtures if f.is_matched()),
            "universes_used": set(),
            "attribute_counts": {},
            "conflicts": [],
            "fixture_type_breakdown": {}
        }
        
        # Track address usage and conflicts
        address_usage = {}
        
        for fixture in fixtures:
            if fixture.is_matched() and hasattr(fixture, 'absolute_addresses'):
                fixture_type = fixture.gdtf_spec or "Unknown"
                # Remove .gdtf extension for consistent naming
                fixture_type_clean = fixture_type.replace('.gdtf', '') if fixture_type.endswith('.gdtf') else fixture_type
                
                # Track fixture type breakdown
                if fixture_type_clean not in summary["fixture_type_breakdown"]:
                    summary["fixture_type_breakdown"][fixture_type_clean] = {
                        "count": 0,
                        "attributes": fixture_type_attributes.get(fixture_type_clean, [])
                    }
                summary["fixture_type_breakdown"][fixture_type_clean]["count"] += 1
                
                for attr_name, addr_info in fixture.absolute_addresses.items():
                    universe = addr_info["universe"]
                    channel = addr_info["channel"]
                    absolute_address = addr_info["absolute_address"]
                    
                    # Track universes used
                    summary["universes_used"].add(universe)
                    
                    # Track attribute counts
                    if attr_name not in summary["attribute_counts"]:
                        summary["attribute_counts"][attr_name] = 0
                    summary["attribute_counts"][attr_name] += 1
                    
                    # Check for address conflicts using absolute address
                    address_key = f"{absolute_address}"
                    if address_key in address_usage:
                        conflict = {
                            "address": f"DMX {absolute_address} (Universe {universe}, Channel {channel})",
                            "fixture1": address_usage[address_key]["fixture"],
                            "attr1": address_usage[address_key]["attribute"],
                            "fixture2": fixture.name,
                            "attr2": attr_name
                        }
                        summary["conflicts"].append(conflict)
                    else:
                        address_usage[address_key] = {
                            "fixture": fixture.name,
                            "attribute": attr_name
                        }
        
        summary["universes_used"] = sorted(list(summary["universes_used"]))
        return summary
    
    def _generate_export_data(self, fixtures: List[FixtureMatch], selected_attributes: List[str], output_format: str, ma3_config: dict = None) -> str:
        """Generate export data in the specified format."""
        if output_format == "text":
            return self._export_text(fixtures, selected_attributes)
        elif output_format == "csv":
            return self._export_csv(fixtures, selected_attributes)
        elif output_format == "json":
            return self._export_json(fixtures, selected_attributes)
        elif output_format == "ma3_xml":
            if ma3_config is None:
                raise ValueError("MA3 XML export requires configuration")
            return self._export_ma3_xml(fixtures, selected_attributes, ma3_config)
        else:
            raise ValueError(f"Unsupported output format: {output_format}")
    
    def _generate_export_data_by_type(self, fixtures: List[FixtureMatch], fixture_type_attributes: Dict[str, List[str]], output_format: str, ma3_config: dict = None) -> str:
        """Generate export data for per-fixture-type analysis."""
        if output_format == "text":
            return self._export_text_by_type(fixtures, fixture_type_attributes)
        elif output_format == "csv":
            return self._export_csv_by_type(fixtures, fixture_type_attributes)
        elif output_format == "json":
            return self._export_json_by_type(fixtures, fixture_type_attributes)
        elif output_format == "ma3_xml":
            if ma3_config is None:
                raise ValueError("MA3 XML export requires configuration")
            return self._export_ma3_xml_by_type(fixtures, fixture_type_attributes, ma3_config)
        else:
            raise ValueError(f"Unsupported output format: {output_format}")
    
    def _export_text(self, fixtures: List[FixtureMatch], selected_attributes: List[str]) -> str:
        """Export results as human-readable text with fixtures as parent containers."""
        lines = []
        
        # Sort fixtures by fixture_id in ascending order
        sorted_fixtures = sorted([f for f in fixtures if f.is_matched()], 
                                key=lambda x: x.fixture_id)
        
        for fixture in sorted_fixtures:
            # Fixture header
            lines.append(f"━━━ FIXTURE {fixture.fixture_id}: {fixture.name} ━━━")
            lines.append(f"Type: {fixture.gdtf_spec}")
            lines.append(f"Mode: {fixture.gdtf_mode}")
            lines.append(f"Base Address: {fixture.base_address}")
            
            # Attributes section
            if hasattr(fixture, 'absolute_addresses') and fixture.absolute_addresses:
                lines.append("")
                lines.append("Attributes:")
                for attr_name in selected_attributes:
                    if attr_name in fixture.absolute_addresses:
                        addr_info = fixture.absolute_addresses[attr_name]
                        universe = addr_info["universe"]
                        channel = addr_info["channel"]
                        absolute_address = addr_info["absolute_address"]
                        lines.append(f"  • {attr_name:15} → DMX {absolute_address:3d} (Universe {universe:3d}, Channel {channel:3d})")
                
                # Show total channels used by this fixture
                total_attrs = len([attr for attr in selected_attributes if attr in fixture.absolute_addresses])
                lines.append(f"  Total attributes: {total_attrs}")
            else:
                lines.append("")
                lines.append("Attributes: None available")
            
            lines.append("")
        
        return "\n".join(lines)
    
    def _export_text_by_type(self, fixtures: List[FixtureMatch], fixture_type_attributes: Dict[str, List[str]]) -> str:
        """Export results as human-readable text with per-fixture-type attributes."""
        lines = []
        
        # Sort fixtures by fixture_id in ascending order
        sorted_fixtures = sorted([f for f in fixtures if f.is_matched()], 
                                key=lambda x: x.fixture_id)
        
        for fixture in sorted_fixtures:
            fixture_type = fixture.gdtf_spec or "Unknown"
            # Remove .gdtf extension for consistent naming
            fixture_type_clean = fixture_type.replace('.gdtf', '') if fixture_type.endswith('.gdtf') else fixture_type
            selected_attributes = fixture_type_attributes.get(fixture_type_clean, [])
            
            # Fixture header
            lines.append(f"━━━ FIXTURE {fixture.fixture_id}: {fixture.name} ━━━")
            lines.append(f"Type: {fixture.gdtf_spec}")
            lines.append(f"Mode: {fixture.gdtf_mode}")
            lines.append(f"Base Address: {fixture.base_address}")
            
            # Attributes section
            if hasattr(fixture, 'absolute_addresses') and fixture.absolute_addresses:
                lines.append("")
                lines.append("Attributes:")
                for attr_name in selected_attributes:
                    if attr_name in fixture.absolute_addresses:
                        addr_info = fixture.absolute_addresses[attr_name]
                        universe = addr_info["universe"]
                        channel = addr_info["channel"]
                        absolute_address = addr_info["absolute_address"]
                        lines.append(f"  • {attr_name:15} → DMX {absolute_address:3d} (Universe {universe:3d}, Channel {channel:3d})")
                
                # Show total channels used by this fixture
                total_attrs = len([attr for attr in selected_attributes if attr in fixture.absolute_addresses])
                lines.append(f"  Total attributes: {total_attrs}")
            else:
                lines.append("")
                lines.append("Attributes: None available")
            
            lines.append("")
        
        return "\n".join(lines)
    
    def _export_csv(self, fixtures: List[FixtureMatch], selected_attributes: List[str]) -> str:
        """Export results as CSV with fixtures as parent containers."""
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow(["Type", "Fixture Name", "Fixture ID", "GDTF Type", "Mode", "Base Address", "Attribute", "Universe", "Channel", "Absolute DMX"])
        
        # Sort fixtures by fixture_id in ascending order
        sorted_fixtures = sorted([f for f in fixtures if f.is_matched()], 
                                key=lambda x: x.fixture_id)
        
        # Write data grouped by fixture
        for fixture in sorted_fixtures:
            if hasattr(fixture, 'absolute_addresses') and fixture.absolute_addresses:
                # Get attributes for this fixture
                fixture_attributes = []
                for attr_name in selected_attributes:
                    if attr_name in fixture.absolute_addresses:
                        addr_info = fixture.absolute_addresses[attr_name]
                        universe = addr_info["universe"]
                        channel = addr_info["channel"]
                        absolute_address = addr_info["absolute_address"]
                        fixture_attributes.append((attr_name, universe, channel, absolute_address))
                
                if fixture_attributes:
                    # Write fixture header row
                    writer.writerow([
                        "FIXTURE",
                        fixture.name,
                        fixture.fixture_id,
                        fixture.gdtf_spec,
                        fixture.gdtf_mode,
                        fixture.base_address,
                        f"{len(fixture_attributes)} attributes",
                        "",
                        "",
                        ""
                    ])
                    
                    # Write attribute rows
                    for attr_name, universe, channel, absolute_address in fixture_attributes:
                        writer.writerow([
                            "ATTRIBUTE",
                            "",  # No fixture name repetition
                            "",  # No fixture ID repetition
                            "",  # No type repetition
                            "",  # No mode repetition
                            "",  # No base address repetition
                            attr_name,
                            universe,
                            channel,
                            absolute_address
                        ])
                    
                    # Add separator row
                    writer.writerow(["", "", "", "", "", "", "", "", "", ""])
            else:
                # Fixture with no attributes
                writer.writerow([
                    "FIXTURE",
                    fixture.name,
                    fixture.fixture_id,
                    fixture.gdtf_spec,
                    fixture.gdtf_mode,
                    fixture.base_address,
                    "No attributes",
                    "",
                    "",
                    ""
                ])
                writer.writerow(["", "", "", "", "", "", "", "", "", ""])
        
        return output.getvalue()
    
    def _export_csv_by_type(self, fixtures: List[FixtureMatch], fixture_type_attributes: Dict[str, List[str]]) -> str:
        """Export results as CSV with per-fixture-type attributes."""
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow(["Type", "Fixture Name", "Fixture ID", "GDTF Type", "Mode", "Base Address", "Attribute", "Universe", "Channel", "Absolute DMX"])
        
        # Sort fixtures by fixture_id in ascending order
        sorted_fixtures = sorted([f for f in fixtures if f.is_matched()], 
                                key=lambda x: x.fixture_id)
        
        # Write data grouped by fixture
        for fixture in sorted_fixtures:
            fixture_type = fixture.gdtf_spec or "Unknown"
            # Remove .gdtf extension for consistent naming
            fixture_type_clean = fixture_type.replace('.gdtf', '') if fixture_type.endswith('.gdtf') else fixture_type
            selected_attributes = fixture_type_attributes.get(fixture_type_clean, [])
            
            if hasattr(fixture, 'absolute_addresses') and fixture.absolute_addresses:
                # Get attributes for this fixture
                fixture_attributes = []
                for attr_name in selected_attributes:
                    if attr_name in fixture.absolute_addresses:
                        addr_info = fixture.absolute_addresses[attr_name]
                        universe = addr_info["universe"]
                        channel = addr_info["channel"]
                        absolute_address = addr_info["absolute_address"]
                        fixture_attributes.append((attr_name, universe, channel, absolute_address))
                
                if fixture_attributes:
                    # Write fixture header row
                    writer.writerow([
                        "FIXTURE",
                        fixture.name,
                        fixture.fixture_id,
                        fixture.gdtf_spec,
                        fixture.gdtf_mode,
                        fixture.base_address,
                        f"{len(fixture_attributes)} attributes",
                        "",
                        "",
                        ""
                    ])
                    
                    # Write attribute rows
                    for attr_name, universe, channel, absolute_address in fixture_attributes:
                        writer.writerow([
                            "ATTRIBUTE",
                            "",  # No fixture name repetition
                            "",  # No fixture ID repetition
                            "",  # No type repetition
                            "",  # No mode repetition
                            "",  # No base address repetition
                            attr_name,
                            universe,
                            channel,
                            absolute_address
                        ])
                    
                    # Add separator row
                    writer.writerow(["", "", "", "", "", "", "", "", "", ""])
            else:
                # Fixture with no attributes
                writer.writerow([
                    "FIXTURE",
                    fixture.name,
                    fixture.fixture_id,
                    fixture.gdtf_spec,
                    fixture.gdtf_mode,
                    fixture.base_address,
                    "No attributes",
                    "",
                    "",
                    ""
                ])
                writer.writerow(["", "", "", "", "", "", "", "", "", ""])
        
        return output.getvalue()
    
    def _export_json(self, fixtures: List[FixtureMatch], selected_attributes: List[str]) -> str:
        """Export results as JSON with fixtures as parent containers."""
        data = {
            "analysis_summary": {
                "total_fixtures": len([f for f in fixtures if f.is_matched()]),
                "attributes_analyzed": selected_attributes,
                "export_timestamp": self._get_timestamp()
            },
            "fixtures": []
        }
        
        # Sort fixtures by fixture_id in ascending order
        sorted_fixtures = sorted([f for f in fixtures if f.is_matched()], 
                                key=lambda x: x.fixture_id)
        
        for fixture in sorted_fixtures:
            # Build attributes list
            attributes_list = []
            if hasattr(fixture, 'absolute_addresses'):
                for attr_name in selected_attributes:
                    if attr_name in fixture.absolute_addresses:
                        addr_info = fixture.absolute_addresses[attr_name]
                        universe = addr_info["universe"]
                        channel = addr_info["channel"]
                        absolute_address = addr_info["absolute_address"]
                        attributes_list.append({
                            "name": attr_name,
                            "universe": universe,
                            "channel": channel,
                            "absolute_dmx": absolute_address,
                            "address": f"{universe}.{channel}"
                        })
            
            fixture_data = {
                "fixture_info": {
                    "name": fixture.name,
                    "fixture_id": fixture.fixture_id,
                    "gdtf_type": fixture.gdtf_spec,
                    "mode": fixture.gdtf_mode,
                    "base_address": fixture.base_address
                },
                "attributes": {
                    "count": len(attributes_list),
                    "details": attributes_list
                }
            }
            
            data["fixtures"].append(fixture_data)
        
        return json.dumps(data, indent=2)
    
    def _export_json_by_type(self, fixtures: List[FixtureMatch], fixture_type_attributes: Dict[str, List[str]]) -> str:
        """Export results as JSON with per-fixture-type attributes."""
        data = {
            "analysis_summary": {
                "total_fixtures": len([f for f in fixtures if f.is_matched()]),
                "fixture_type_attributes": fixture_type_attributes,
                "export_timestamp": self._get_timestamp()
            },
            "fixtures": []
        }
        
        # Sort fixtures by fixture_id in ascending order
        sorted_fixtures = sorted([f for f in fixtures if f.is_matched()], 
                                key=lambda x: x.fixture_id)
        
        for fixture in sorted_fixtures:
            fixture_type = fixture.gdtf_spec or "Unknown"
            # Remove .gdtf extension for consistent naming
            fixture_type_clean = fixture_type.replace('.gdtf', '') if fixture_type.endswith('.gdtf') else fixture_type
            selected_attributes = fixture_type_attributes.get(fixture_type_clean, [])
            
            # Build attributes list
            attributes_list = []
            if hasattr(fixture, 'absolute_addresses'):
                for attr_name in selected_attributes:
                    if attr_name in fixture.absolute_addresses:
                        addr_info = fixture.absolute_addresses[attr_name]
                        universe = addr_info["universe"]
                        channel = addr_info["channel"]
                        absolute_address = addr_info["absolute_address"]
                        attributes_list.append({
                            "name": attr_name,
                            "universe": universe,
                            "channel": channel,
                            "absolute_dmx": absolute_address,
                            "address": f"{universe}.{channel}"
                        })
            
            fixture_data = {
                "fixture_info": {
                    "name": fixture.name,
                    "fixture_id": fixture.fixture_id,
                    "gdtf_type": fixture.gdtf_spec,
                    "mode": fixture.gdtf_mode,
                    "base_address": fixture.base_address
                },
                "attributes": {
                    "count": len(attributes_list),
                    "details": attributes_list
                }
            }
            
            data["fixtures"].append(fixture_data)
        
        return json.dumps(data, indent=2)
    
    def _get_timestamp(self) -> str:
        """Get current timestamp for export."""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    def _export_ma3_xml(self, fixtures: List[FixtureMatch], selected_attributes: List[str], ma3_config: dict) -> str:
        """Export results as MA3 XML format."""
        import uuid
        from xml.etree.ElementTree import Element, SubElement, tostring
        from xml.dom import minidom
        
        # Create root element
        root = Element("GMA3", DataVersion="2.2.5.2")
        
        # Sort fixtures by fixture_id in ascending order
        sorted_fixtures = sorted([f for f in fixtures if f.is_matched()], 
                                key=lambda x: x.fixture_id)
        
        # Create a DMX remote for each attribute of each fixture
        for fixture in sorted_fixtures:
            if hasattr(fixture, 'absolute_addresses') and fixture.absolute_addresses:
                for attr_name in selected_attributes:
                    if attr_name in fixture.absolute_addresses:
                        addr_info = fixture.absolute_addresses[attr_name]
                        universe = addr_info["universe"]
                        channel = addr_info["channel"]
                        absolute_address = addr_info["absolute_address"]
                        
                        # Create DMX remote element
                        dmx_remote = SubElement(root, "DmxRemote")
                        
                        # Set attributes (with fixture ID prefix)
                        remote_name = f"{fixture.fixture_id}_{fixture.name}_{attr_name}"
                        dmx_remote.set("Name", remote_name)
                        dmx_remote.set("Guid", str(uuid.uuid4()).replace('-', ' ').upper())
                        dmx_remote.set("TriggerOn", self._value_to_hex(ma3_config["trigger_on"]))
                        dmx_remote.set("TriggerOff", self._value_to_hex(ma3_config["trigger_off"]))
                        dmx_remote.set("InFrom", self._value_to_hex(ma3_config["in_from"]))
                        dmx_remote.set("InTo", self._value_to_hex(ma3_config["in_to"]))
                        dmx_remote.set("OutFrom", f"{ma3_config['out_from']:6.1f}")
                        dmx_remote.set("OutTo", f"{ma3_config['out_to']:6.1f}")
                        dmx_remote.set("Address", f"{universe}.{channel:03d}")
                        dmx_remote.set("Resolution", ma3_config["resolution"])
        
        # Convert to pretty-printed XML string
        rough_string = tostring(root, encoding='unicode')
        reparsed = minidom.parseString(rough_string)
        pretty_xml = reparsed.toprettyxml(indent="    ", encoding=None)
        
        # Add proper XML declaration and format
        lines = pretty_xml.split('\n')
        # Filter out empty lines and fix formatting
        filtered_lines = [line for line in lines if line.strip()]
        
        # Ensure proper XML declaration
        if not filtered_lines[0].startswith('<?xml'):
            filtered_lines.insert(0, '<?xml version="1.0" encoding="UTF-8"?>')
        
        return '\n'.join(filtered_lines)
    
    def _export_ma3_xml_by_type(self, fixtures: List[FixtureMatch], fixture_type_attributes: Dict[str, List[str]], ma3_config: dict) -> str:
        """Export results as MA3 XML format with per-fixture-type attributes."""
        import uuid
        from xml.etree.ElementTree import Element, SubElement, tostring
        from xml.dom import minidom
        
        # Create root element
        root = Element("GMA3", DataVersion="2.2.5.2")
        
        # Sort fixtures by fixture_id in ascending order
        sorted_fixtures = sorted([f for f in fixtures if f.is_matched()], 
                                key=lambda x: x.fixture_id)
        
        # Create a DMX remote for each attribute of each fixture
        for fixture in sorted_fixtures:
            fixture_type = fixture.gdtf_spec or "Unknown"
            # Remove .gdtf extension for consistent naming
            fixture_type_clean = fixture_type.replace('.gdtf', '') if fixture_type.endswith('.gdtf') else fixture_type
            selected_attributes = fixture_type_attributes.get(fixture_type_clean, [])
            
            if hasattr(fixture, 'absolute_addresses') and fixture.absolute_addresses:
                for attr_name in selected_attributes:
                    if attr_name in fixture.absolute_addresses:
                        addr_info = fixture.absolute_addresses[attr_name]
                        universe = addr_info["universe"]
                        channel = addr_info["channel"]
                        absolute_address = addr_info["absolute_address"]
                        
                        # Create DMX remote element
                        dmx_remote = SubElement(root, "DmxRemote")
                        
                        # Set attributes (with fixture ID prefix)
                        remote_name = f"{fixture.fixture_id}_{fixture.name}_{attr_name}"
                        dmx_remote.set("Name", remote_name)
                        dmx_remote.set("Guid", str(uuid.uuid4()).replace('-', ' ').upper())
                        dmx_remote.set("TriggerOn", self._value_to_hex(ma3_config["trigger_on"]))
                        dmx_remote.set("TriggerOff", self._value_to_hex(ma3_config["trigger_off"]))
                        dmx_remote.set("InFrom", self._value_to_hex(ma3_config["in_from"]))
                        dmx_remote.set("InTo", self._value_to_hex(ma3_config["in_to"]))
                        dmx_remote.set("OutFrom", f"{ma3_config['out_from']:6.1f}")
                        dmx_remote.set("OutTo", f"{ma3_config['out_to']:6.1f}")
                        dmx_remote.set("Address", f"{universe}.{channel:03d}")
                        dmx_remote.set("Resolution", ma3_config["resolution"])
        
        # Convert to pretty-printed XML string
        rough_string = tostring(root, encoding='unicode')
        reparsed = minidom.parseString(rough_string)
        pretty_xml = reparsed.toprettyxml(indent="    ", encoding=None)
        
        # Add proper XML declaration and format
        lines = pretty_xml.split('\n')
        # Filter out empty lines and fix formatting
        filtered_lines = [line for line in lines if line.strip()]
        
        # Ensure proper XML declaration
        if not filtered_lines[0].startswith('<?xml'):
            filtered_lines.insert(0, '<?xml version="1.0" encoding="UTF-8"?>')
        
        return '\n'.join(filtered_lines)
    
    def _value_to_hex(self, value: int) -> str:
        """Convert a numeric value to a 6-character hex color string."""
        # For MA3, we convert the value to a hex color representation
        # Values are treated as RGB components, so we repeat the hex value
        hex_val = f"{value:02X}"
        return hex_val + hex_val + hex_val
    
    def _generate_validation_info(self, fixtures: List[FixtureMatch], selected_attributes: List[str]) -> Dict[str, Any]:
        """Generate validation information."""
        matched_fixtures = [f for f in fixtures if f.is_matched()]
        
        # Get all available attributes
        available_attributes = set()
        for fixture in matched_fixtures:
            if fixture.matched_mode:
                available_attributes.update(fixture.matched_mode.channels.keys())
        
        # Check which selected attributes are valid
        valid_attributes = [attr for attr in selected_attributes if attr in available_attributes]
        
        return {
            "total_fixtures": len(fixtures),
            "matched_fixtures": len(matched_fixtures),
            "gdtf_profiles_loaded": len(set(f.gdtf_spec for f in matched_fixtures if f.gdtf_spec)),
            "available_attributes": sorted(list(available_attributes)),
            "valid_attributes": valid_attributes,
            "invalid_attributes": [attr for attr in selected_attributes if attr not in available_attributes]
        }
    
    def _generate_validation_info_by_type(self, fixtures: List[FixtureMatch], fixture_type_attributes: Dict[str, List[str]]) -> Dict[str, Any]:
        """Generate validation information for per-fixture-type analysis."""
        matched_fixtures = [f for f in fixtures if f.is_matched()]
        
        # Get all available attributes
        available_attributes = set()
        for fixture in matched_fixtures:
            if fixture.matched_mode:
                available_attributes.update(fixture.matched_mode.channels.keys())
        
        # Check validity of attributes per fixture type
        validation_by_type = {}
        for fixture_type, selected_attributes in fixture_type_attributes.items():
            valid_attributes = [attr for attr in selected_attributes if attr in available_attributes]
            invalid_attributes = [attr for attr in selected_attributes if attr not in available_attributes]
            
            validation_by_type[fixture_type] = {
                "selected_attributes": selected_attributes,
                "valid_attributes": valid_attributes,
                "invalid_attributes": invalid_attributes
            }
        
        return {
            "total_fixtures": len(fixtures),
            "matched_fixtures": len(matched_fixtures),
            "gdtf_profiles_loaded": len(set(f.gdtf_spec for f in matched_fixtures if f.gdtf_spec)),
            "available_attributes": sorted(list(available_attributes)),
            "validation_by_type": validation_by_type
        }
    
    def export_results(self, results: AnalysisResults, output_format: str, 
                      save_path: Optional[str] = None, ma3_config: dict = None) -> str:
        """
        Export analysis results to file or return as string.
        
        Args:
            results: AnalysisResults object
            output_format: Format to export to
            save_path: Optional path to save file
            ma3_config: MA3 XML configuration if needed
            
        Returns:
            Export data as string
        """
        export_data = self._generate_export_data(results.fixtures, results.selected_attributes, output_format, ma3_config)
        
        if save_path:
            try:
                with open(save_path, 'w', encoding='utf-8') as f:
                    f.write(export_data)
            except Exception as e:
                raise Exception(f"Error saving file: {e}")
        
        return export_data
    
    def get_fixture_summary(self, fixtures: List[FixtureMatch]) -> Dict[str, Any]:
        """Get a summary of fixture information."""
        total = len(fixtures)
        matched = sum(1 for f in fixtures if f.is_matched())
        
        fixture_types = {}
        for fixture in fixtures:
            fixture_type = fixture.gdtf_spec or "Unknown"
            # Remove .gdtf extension for consistent naming
            fixture_type_clean = fixture_type.replace('.gdtf', '') if fixture_type.endswith('.gdtf') else fixture_type
            if fixture_type_clean not in fixture_types:
                fixture_types[fixture_type_clean] = 0
            fixture_types[fixture_type_clean] += 1
        
        return {
            "total_fixtures": total,
            "matched_fixtures": matched,
            "unmatched_fixtures": total - matched,
            "match_rate": (matched / total * 100) if total > 0 else 0,
            "fixture_types": fixture_types
        } 