"""
Simple export functionality.
Exports fixture data to various formats using minimal, clean functions.
"""

import json
import csv
from typing import List, Dict, Any
from pathlib import Path

from .data import get_export_data


def export_to_text(fixtures: List[Dict[str, Any]], selected_attributes: List[str]) -> str:
    """Export fixture data to text format."""
    export_data = get_export_data(fixtures, selected_attributes)
    
    if not export_data:
        return "No fixture data to export."
    
    lines = []
    lines.append("Fixture Address Export")
    lines.append("=" * 40)
    lines.append("")
    
    current_fixture = None
    for item in export_data:
        if item['fixture_name'] != current_fixture:
            if current_fixture is not None:
                lines.append("")
            current_fixture = item['fixture_name']
            role_text = f" ({item['role'].title()})"
            master_text = ""
            if item['role'] == 'remote' and 'master_fixture_id' in item:
                master_text = f" -> Master ID: {item['master_fixture_id']}"
            
            lines.append(f"Fixture: {item['fixture_name']} (ID: {item['fixture_id']}){role_text}{master_text}")
            lines.append("-" * 30)
        
        lines.append(f"  {item['attribute']:<15} Address: {item['address']:<5} Sequence: {item['sequence']}")
    
    return "\n".join(lines)


def export_to_csv(fixtures: List[Dict[str, Any]], selected_attributes: List[str]) -> str:
    """Export fixture data to CSV format."""
    export_data = get_export_data(fixtures, selected_attributes)
    
    if not export_data:
        return "fixture_name,fixture_id,attribute,address,sequence,role,master_fixture_id\n"
    
    lines = []
    lines.append("fixture_name,fixture_id,attribute,address,sequence,role,master_fixture_id")
    
    for item in export_data:
        master_id = item.get('master_fixture_id', '')
        lines.append(f"{item['fixture_name']},{item['fixture_id']},{item['attribute']},{item['address']},{item['sequence']},{item['role']},{master_id}")
    
    return "\n".join(lines)


def export_to_json(fixtures: List[Dict[str, Any]], selected_attributes: List[str]) -> str:
    """Export fixture data to JSON format."""
    export_data = get_export_data(fixtures, selected_attributes)
    
    # Group by fixture for better JSON structure
    fixtures_dict = {}
    for item in export_data:
        fixture_key = f"{item['fixture_name']}_{item['fixture_id']}"
        if fixture_key not in fixtures_dict:
            fixtures_dict[fixture_key] = {
                'name': item['fixture_name'],
                'fixture_id': item['fixture_id'],
                'attributes': {}
            }
        
        fixtures_dict[fixture_key]['attributes'][item['attribute']] = {
            'address': item['address'],
            'sequence': item['sequence']
        }
    
    return json.dumps(list(fixtures_dict.values()), indent=2)


def export_to_ma3_xml(fixtures: List[Dict[str, Any]], selected_attributes: List[str], 
                     ma3_config: Dict[str, Any] = None) -> str:
    """Export fixture data to MA3 XML sequence format."""
    export_data = get_export_data(fixtures, selected_attributes)
    
    if not export_data:
        return "<!-- No fixture data to export -->"
    
    # Default MA3 configuration
    if ma3_config is None:
        ma3_config = {
            "trigger_on": 255,
            "trigger_off": 0,
            "in_from": 0,
            "in_to": 255,
            "out_from": 0.0,
            "out_to": 100.0,
            "resolution": "16bit"
        }
    
    # Group data by attribute
    attributes_dict = {}
    for item in export_data:
        attr = item['attribute']
        if attr not in attributes_dict:
            attributes_dict[attr] = []
        attributes_dict[attr].append(item)
    
    # Generate XML for each attribute
    xml_parts = []
    xml_parts.append('<?xml version="1.0" encoding="UTF-8"?>')
    xml_parts.append('<GMA3 DataVersion="2.2.5.2">')
    
    for attr_name, attr_items in attributes_dict.items():
        sequence_xml = _generate_ma3_sequence(attr_name, attr_items, ma3_config)
        xml_parts.append(sequence_xml)
    
    xml_parts.append('</GMA3>')
    
    return "\n".join(xml_parts)


def _generate_ma3_sequence(attr_name: str, items: List[Dict[str, Any]], 
                          ma3_config: Dict[str, Any]) -> str:
    """Generate MA3 XML sequence for a specific attribute."""
    lines = []
    
    # Generate unique GUID (simplified)
    import uuid
    sequence_guid = str(uuid.uuid4()).replace('-', ' ').upper()
    part_guid = str(uuid.uuid4()).replace('-', ' ').upper()
    
    # Sequence header
    lines.append(f'    <Sequence Name="{attr_name}" Guid="{sequence_guid}" AutoStart="Yes" AutoStop="Yes" AutoFix="No" AutoStomp="No" SoftLTP="Yes" XFadeReload="No" SwapProtect="No" KillProtect="No" UseExecutorTime="Yes" OffwhenOverridden="Yes" SequMIB="Enabled" AutoPrePos="No" WrapAround="Yes" MasterGoMode="None" SpeedfromRate="No" Tracking="Yes" IncludeLinkLastGo="Yes" RateScale="One" SpeedScale="One" PreferCueAppearance="No" ExecutorDisplayMode="Both" Action="Pool Default">')
    
    # Off cue
    off_cue_guid = str(uuid.uuid4()).replace('-', ' ').upper()
    lines.append(f'        <Cue Name="OffCue" Release="Yes" Assert="Assert" AllowDuplicates="" TrigType="">')
    lines.append(f'            <Part Guid="{off_cue_guid}" AlignRangeX="No" AlignRangeY="No" AlignRangeZ="No" PreserveGridPositions="No" MAgic="No" Mode="0" Action="Pool Default" />')
    lines.append('        </Cue>')
    
    # Zero cue
    zero_cue_guid = str(uuid.uuid4()).replace('-', ' ').upper()
    lines.append(f'        <Cue Name="CueZero" No="  0">')
    lines.append(f'            <Part Guid="{zero_cue_guid}" AlignRangeX="No" AlignRangeY="No" AlignRangeZ="No" PreserveGridPositions="No" MAgic="No" Mode="0" Action="Pool Default" />')
    lines.append('        </Cue>')
    
    # Main cue with presets
    main_cue_guid = str(uuid.uuid4()).replace('-', ' ').upper()
    lines.append(f'        <Cue No="  1" AllowDuplicates="">')
    lines.append(f'            <Part Guid="{main_cue_guid}" AlignRangeX="No" AlignRangeY="No" AlignRangeZ="No" PreserveGridPositions="No" MAgic="No" Mode="0" Action="Pool Default" Sync="" Morph="">')
    lines.append(f'                <PresetData Size="{len(items)}">')
    
    # Add phasers for each fixture
    for item in items:
        phaser_lines = _generate_ma3_phaser(attr_name, item, ma3_config)
        lines.extend(phaser_lines)
    
    lines.append('                </PresetData>')
    lines.append('            </Part>')
    lines.append('        </Cue>')
    lines.append('    </Sequence>')
    
    return "\n".join(lines)


def _generate_ma3_phaser(attr_name: str, item: Dict[str, Any], ma3_config: Dict[str, Any]) -> List[str]:
    """Generate MA3 phaser XML for a single fixture attribute."""
    lines = []
    
    # Map common attributes to MA3 attribute names
    ma3_attr_map = {
        'Dim': 'Dimmer',
        'R': 'ColorRGB_R',
        'G': 'ColorRGB_G', 
        'B': 'ColorRGB_B',
        'W': 'ColorRGB_W',
        'WW': 'ColorRGB_WW',
        'CW': 'ColorRGB_CW',
        'Pan': 'Position_Pan',
        'Tilt': 'Position_Tilt',
        'Zoom': 'Beam_Zoom',
        'Focus': 'Beam_Focus',
        'Iris': 'Beam_Iris'
    }
    
    ma3_attr = ma3_attr_map.get(attr_name, attr_name)
    sequence = item['sequence']
    
    lines.append(f'                    <Phaser IDType="0" ID="{sequence}" Attribute="{ma3_attr}" GridPos="0" GridPosMatr="0" Selective="true">')
    lines.append(f'                        <Step Function="{ma3_attr}" Absolute="{ma3_config["out_to"]}" />')
    lines.append('                    </Phaser>')
    
    return lines


def save_export_to_file(content: str, file_path: str) -> bool:
    """Save export content to file."""
    try:
        with open(file_path, 'w', encoding='utf-8') as file:
            file.write(content)
        return True
    except Exception as e:
        print(f"Error saving file: {e}")
        return False


def get_export_formats() -> List[str]:
    """Get list of available export formats."""
    return ['text', 'csv', 'json', 'ma3_xml']


def export_fixtures(fixtures: List[Dict[str, Any]], selected_attributes: List[str], 
                   export_format: str, ma3_config: Dict[str, Any] = None) -> str:
    """Export fixtures in the specified format."""
    if export_format == 'text':
        return export_to_text(fixtures, selected_attributes)
    elif export_format == 'csv':
        return export_to_csv(fixtures, selected_attributes)
    elif export_format == 'json':
        return export_to_json(fixtures, selected_attributes)
    elif export_format == 'ma3_xml':
        return export_to_ma3_xml(fixtures, selected_attributes, ma3_config)
    else:
        raise ValueError(f"Unknown export format: {export_format}") 