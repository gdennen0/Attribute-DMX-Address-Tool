"""
Simple export functionality.
Exports fixture data to various formats using minimal, clean functions.
"""

import json
import csv
from typing import List, Dict, Any
from pathlib import Path

from .data import get_export_data


def export_to_text(fixtures: List[Dict[str, Any]]) -> str:
    """Export fixture data to text format."""
    export_data = get_export_data(fixtures)
    
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


def export_to_csv(fixtures: List[Dict[str, Any]]) -> str:
    """Export fixture data to CSV format."""
    export_data = get_export_data(fixtures)
    
    if not export_data:
        return "fixture_name,fixture_id,attribute,address,sequence,role,master_fixture_id\n"
    
    lines = []
    lines.append("fixture_name,fixture_id,attribute,address,sequence,role,master_fixture_id")
    
    for item in export_data:
        master_id = item.get('master_fixture_id', '')
        lines.append(f"{item['fixture_name']},{item['fixture_id']},{item['attribute']},{item['address']},{item['sequence']},{item['role']},{master_id}")
    
    return "\n".join(lines)


def export_to_json(fixtures: List[Dict[str, Any]]) -> str:
    """Export fixture data to JSON format."""
    export_data = get_export_data(fixtures)
    
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


def export_to_ma3_xml(fixtures: List[Dict[str, Any]], ma3_config: Dict[str, Any] = None) -> str:
    """Export fixture data to MA3 XML sequence format."""
    export_data = get_export_data(fixtures)
    
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


def export_to_ma3_dmx_remotes(fixtures: List[Dict[str, Any]], ma3_config: Dict[str, Any] = None) -> str:
    """Export fixture data to MA3 DMX Remotes XML format."""
    import uuid
    from xml.etree.ElementTree import Element, SubElement, tostring
    from xml.dom import minidom
    
    export_data = get_export_data(fixtures)
    
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
    
    # Create root element
    root = Element("GMA3", DataVersion="2.2.5.2")
    
    # Create a DMX remote for each fixture attribute
    for item in export_data:
        # Create DMX remote element
        dmx_remote = SubElement(root, "DmxRemote")
        
        # Set attributes (with fixture ID prefix)
        remote_name = f"{item['fixture_id']}_{item['fixture_name']}_{item['attribute']}"
        dmx_remote.set("Name", remote_name)
        dmx_remote.set("Guid", str(uuid.uuid4()).replace('-', ' ').upper())
        
        # Add sequence target if sequence number is available
        if item['sequence']:
            dmx_remote.set("Target", f"ShowData.DataPools.Default.Sequences.{item['sequence']}")
        
        dmx_remote.set("TriggerOn", _value_to_hex(ma3_config["trigger_on"]))
        dmx_remote.set("TriggerOff", _value_to_hex(ma3_config["trigger_off"]))
        dmx_remote.set("InFrom", _value_to_hex(ma3_config["in_from"]))
        dmx_remote.set("InTo", _value_to_hex(ma3_config["in_to"]))
        dmx_remote.set("OutFrom", f"{ma3_config['out_from']:6.1f}")
        dmx_remote.set("OutTo", f"{ma3_config['out_to']:6.1f}")
        dmx_remote.set("Address", item['address'])  # Already formatted as "universe.channel"
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


def export_to_ma3_sequences(fixtures: List[Dict[str, Any]]) -> str:
    """Export fixture data to MA3 sequences XML format with values set to 100."""
    import uuid
    from xml.etree.ElementTree import Element, SubElement, tostring
    from xml.dom import minidom
    
    export_data = get_export_data(fixtures)
    
    if not export_data:
        return "<!-- No fixture data to export -->"
    
    # Create root element
    root = Element("GMA3", DataVersion="2.2.5.2")
    
    # Create a sequence for each fixture-attribute combination
    for item in export_data:
        if not item['sequence']:  # Skip if no sequence number
            continue
            
        # Create sequence element
        sequence = SubElement(root, "Sequence")
        
        # Set sequence attributes - name should be "fixture_id_attribute"
        sequence_name = f"{item['fixture_id']}_{item['attribute']}"
        sequence.set("Name", sequence_name)
        sequence.set("Guid", str(uuid.uuid4()).replace('-', ' ').upper())
        sequence.set("AutoStart", "Yes")
        sequence.set("AutoStop", "Yes")
        sequence.set("AutoFix", "No")
        sequence.set("AutoStomp", "No")
        sequence.set("SoftLTP", "Yes")
        sequence.set("XFadeReload", "No")
        sequence.set("SwapProtect", "No")
        sequence.set("KillProtect", "No")
        sequence.set("UseExecutorTime", "Yes")
        sequence.set("OffwhenOverridden", "Yes")
        sequence.set("SequMIB", "Enabled")
        sequence.set("AutoPrePos", "No")
        sequence.set("WrapAround", "Yes")
        sequence.set("MasterGoMode", "None")
        sequence.set("SpeedfromRate", "No")
        sequence.set("Tracking", "Yes")
        sequence.set("IncludeLinkLastGo", "Yes")
        sequence.set("RateScale", "One")
        sequence.set("SpeedScale", "One")
        sequence.set("PreferCueAppearance", "No")
        sequence.set("ExecutorDisplayMode", "Both")
        sequence.set("Action", "Pool Default")
        
        # Create OffCue
        off_cue = SubElement(sequence, "Cue")
        off_cue.set("Name", "OffCue")
        off_cue.set("Release", "Yes")
        off_cue.set("Assert", "Assert")
        off_cue.set("AllowDuplicates", "")
        off_cue.set("TrigType", "")
        
        off_part = SubElement(off_cue, "Part")
        off_part.set("Guid", str(uuid.uuid4()).replace('-', ' ').upper())
        off_part.set("AlignRangeX", "No")
        off_part.set("AlignRangeY", "No")
        off_part.set("AlignRangeZ", "No")
        off_part.set("PreserveGridPositions", "No")
        off_part.set("MAgic", "No")
        off_part.set("Mode", "0")
        off_part.set("Action", "Pool Default")
        
        # Create CueZero
        cue_zero = SubElement(sequence, "Cue")
        cue_zero.set("Name", "CueZero")
        cue_zero.set("No", "  0")
        
        cue_zero_part = SubElement(cue_zero, "Part")
        cue_zero_part.set("Guid", str(uuid.uuid4()).replace('-', ' ').upper())
        cue_zero_part.set("AlignRangeX", "No")
        cue_zero_part.set("AlignRangeY", "No")
        cue_zero_part.set("AlignRangeZ", "No")
        cue_zero_part.set("PreserveGridPositions", "No")
        cue_zero_part.set("MAgic", "No")
        cue_zero_part.set("Mode", "0")
        cue_zero_part.set("Action", "Pool Default")
        
        # Create Cue 1 with the actual data
        cue_one = SubElement(sequence, "Cue")
        cue_one.set("No", "  1")
        cue_one.set("AllowDuplicates", "")
        
        cue_one_part = SubElement(cue_one, "Part")
        cue_one_part.set("Guid", str(uuid.uuid4()).replace('-', ' ').upper())
        cue_one_part.set("AlignRangeX", "No")
        cue_one_part.set("AlignRangeY", "No")
        cue_one_part.set("AlignRangeZ", "No")
        cue_one_part.set("PreserveGridPositions", "No")
        cue_one_part.set("MAgic", "No")
        cue_one_part.set("Mode", "0")
        cue_one_part.set("Action", "Pool Default")
        cue_one_part.set("Sync", "")
        cue_one_part.set("Morph", "")
        
        # Create PresetData
        preset_data = SubElement(cue_one_part, "PresetData")
        preset_data.set("Size", "1")  # Only one fixture per sequence
        
        # Create Phaser for this specific fixture-attribute combination
        phaser = SubElement(preset_data, "Phaser")
        phaser.set("IDType", "0")
        phaser.set("ID", str(item['fixture_id']))  # Use fixture ID, not sequence number
        
        # Map attribute name to MA3 format
        ma3_attr_map = {
            'Dim': 'Dimmer',
            'R': 'ColorRGB_R',
            'G': 'ColorRGB_G', 
            'B': 'ColorRGB_B',
            'W': 'ColorRGB_W',
            'WW': 'ColorRGB_WW',
            'CW': 'ColorRGB_CW',
            'White': 'ColorRGB_White',
            'Pan': 'Position_Pan',
            'Tilt': 'Position_Tilt',
            'Zoom': 'Beam_Zoom',
            'Focus': 'Beam_Focus',
            'Iris': 'Beam_Iris'
        }
        
        ma3_attr = ma3_attr_map.get(item['attribute'], item['attribute'])
        phaser.set("Attribute", ma3_attr)
        phaser.set("GridPos", "0")
        phaser.set("GridPosMatr", "0")
        phaser.set("Selective", "true")
        
        # Create Step with value 100
        step = SubElement(phaser, "Step")
        step.set("Function", ma3_attr)
        step.set("Absolute", "100")
    
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


def _value_to_hex(value: int) -> str:
    """Convert a numeric value to a 6-character hex color string."""
    # For MA3, we convert the value to a hex color representation
    # Values are treated as RGB components, so we repeat the hex value
    hex_val = f"{value:02X}"
    return hex_val + hex_val + hex_val


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
    sequence = str(item['sequence'])  # Convert to string to avoid serialization error
    
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
    return ['text', 'csv', 'json', 'ma3_xml', 'ma3_dmx_remotes', 'ma3_sequences']


def export_fixtures(fixtures: List[Dict[str, Any]], selected_attributes: List[str], 
                   export_format: str, ma3_config: Dict[str, Any] = None) -> str:
    """Export fixtures in the specified format."""
    if export_format == 'text':
        return export_to_text(fixtures)
    elif export_format == 'csv':
        return export_to_csv(fixtures)
    elif export_format == 'json':
        return export_to_json(fixtures)
    elif export_format == 'ma3_xml':
        return export_to_ma3_xml(fixtures, ma3_config)
    elif export_format == 'ma3_dmx_remotes':
        return export_to_ma3_dmx_remotes(fixtures, ma3_config)
    elif export_format == 'ma3_sequences':
        return export_to_ma3_sequences(fixtures)
    else:
        raise ValueError(f"Unknown export format: {export_format}") 