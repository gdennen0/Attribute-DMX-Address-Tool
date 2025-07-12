# MVR File Analyzer

A Python application for analyzing MVR (Model View Render) files and extracting fixture attribute addresses for lighting control systems. This tool helps lighting professionals understand their fixture layouts and generate organized reports.

## Quick Start

### Requirements
- Python 3.8 or higher
- PyQt6 

### Installation

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Run the application:
   ```bash
   python main.py
   ```

## Project Structure

```
AtrributeAddreser/
├── main.py              # Application entry point
├── gui.py               # Main GUI interface
├── controllers.py       # Application logic controllers
├── config.py            # Configuration management
├── config.json          # User settings and folder memory
├── requirements.txt     # Dependencies
├── models/              # Data models
├── services/            # Core services (MVR & GDTF)
├── views/               # GUI components
├── GDTF_files/          # Sample GDTF files
├── mvr_files/           # Sample MVR files
└── output/              # Generated analysis results
```

## How to Use

### Basic Workflow
1. Launch the application with `python main.py`
2. Browse and select your MVR file
3. The application automatically extracts fixture information and IDs
4. Click "Select Attributes" to choose which attributes to analyze per fixture type
5. Choose your preferred export format (including MA3 XML if needed)
6. Click "Analyze" to generate results
7. Export results or save your project for later use

### What You Get
The application creates organized reports showing:
- Fixtures grouped by their ID numbers (sorted in ascending order)
- Calculated DMX addresses for each fixture
- Attribute breakdown with clear hierarchy
- Address conflict detection when fixtures overlap

## Features

**Project Management**
- Save and load projects with all settings (.aap files)
- Recent projects menu for quick access
- Auto-save protection with unsaved changes warnings
- Separate attribute selection and analysis workflow

**Smart Analysis**
- Extracts fixture IDs from MVR files automatically
- Calculates DMX addresses using the standard formula: `(Universe - 1) × 512 + Channel`
- Detects and reports address conflicts between fixtures
- Matches fixtures with GDTF profiles when available

**Organized Output**
- Four export formats: Text (human-readable), CSV (spreadsheet-ready), JSON (structured data), MA3 XML (GrandMA3 DMX remotes)
- Hierarchical presentation with fixtures as parent containers
- No redundant information - each fixture appears once with its attributes listed below
- Professional formatting with clear visual separation

**User-Friendly Interface**
- Folder memory remembers your last used directories
- Clean, intuitive GUI built with PyQt6
- Automatic file saving to the output directory
- Real-time analysis feedback

## Supported Attributes

The application analyzes common fixture attributes including:
- **Dim**: Intensity control
- **Focus1**: Primary focus/zoom
- **G1, G2**: Gobo wheels
- **Color**: Color mixing or wheel
- **Pan, Tilt**: Position control
- **Custom attributes**: Any attributes defined in your MVR files

## Configuration

The application saves your preferences in `config.json`:

```json
{
  "selected_attributes": ["Dim", "Focus1", "G1", "G2"],
  "output_format": "text",
  "save_results": true,
  "output_directory": "output",
  "last_mvr_directory": "/path/to/your/mvr/files",
  "last_export_directory": "/path/to/your/exports",
  "last_gdtf_directory": "/path/to/your/gdtf/files"
}
```

## File Formats

**MVR Files**
Standard MVR files containing fixture definitions, positions, and addressing information. The application automatically parses XML structure to extract fixture IDs and attribute mappings.

**GDTF Files**
Load GDTF files for enhanced fixture matching and detailed attribute information. The application provides a dedicated dialog for selecting and managing GDTF files.

**Export Formats**
- **Text**: Clean, hierarchical format perfect for documentation
- **CSV**: Structured format with fixture/attribute row types for spreadsheet analysis
- **JSON**: Nested structure with fixture info and attributes for programmatic use
- **MA3 XML**: GrandMA3 DMX remote definitions for direct import into MA3 software

**MA3 XML Features**
- Creates individual DMX remotes for each fixture attribute
- Remote names include fixture ID prefix for easy identification (e.g., "1_FixtureName_Dim")
- Configurable trigger levels (DMX 0-255), input ranges (DMX 0-255), and output ranges (0-100%)
- Supports 8bit, 16bit, and 24bit resolution
- Color-coded trigger and input values (hex format)
- Unique GUIDs for each remote
- Direct import compatibility with GrandMA3 software

## Technical Notes

- DMX address calculation follows industry standard: `(Universe - 1) × 512 + Channel`
- Fixture IDs are extracted from `<FixtureID>` elements in MVR XML
- Results are sorted by fixture ID in ascending order
- The application handles large MVR files efficiently
- Comprehensive error handling provides clear feedback

## Support

This application is designed for professional lighting workflows. The interface includes helpful guidance, and all operations provide clear feedback about what's happening behind the scenes.

---

*Built for lighting professionals who need reliable, organized analysis of their MVR files.* 