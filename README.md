# AttributeAddresser

A simple tool to analyze MVR files and extract fixture addresses for lighting control systems.

## Overview

AttributeAddresser is a Python application that helps lighting professionals analyze MVR (MA3 show files) and CSV files to extract and manage fixture addresses, sequences, and attributes. It provides a clean, intuitive interface for importing data, matching fixture types to GDTF profiles, and exporting results in various formats.

## Features

- **MVR File Import**: Import and parse MA3 show files (.mvr)
- **CSV File Import**: Import fixture data from CSV files with column mapping
- **GDTF Profile Matching**: Match fixture types to GDTF profiles for accurate attribute mapping
- **Fixture Management**: Organize fixtures into Master and Remote groups
- **Sequence Management**: Apply and renumber sequence numbers
- **Export Options**: Export to MA3 sequences, CSV, and other formats
- **Project Saving**: Save and load project files for later use
- **Recent Projects**: Quick access to recently opened projects

## Requirements

- Python 3.10 or higher
- PyQt6 6.9.1

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/AttributeAddresser.git
cd AttributeAddresser
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

Run the application:
```bash
python main.py
```

### Basic Workflow

1. **Import Data**: Use "Import MVR..." or "Import CSV..." to load fixture data
2. **Configure Fixtures**: Match fixture types to GDTF profiles and select attributes
3. **Organize Fixtures**: Arrange fixtures into Master and Remote groups as needed
4. **Apply Sequences**: Use "Apply sequence numbers" to assign sequence numbers
5. **Export Results**: Export data in your preferred format
6. **Save Project**: Save your work for later use
7. **Recent Projects**: Access recently opened projects from the File menu

### File Formats

- **MVR Files**: MA3 show files containing fixture and sequence data
- **CSV Files**: Comma-separated values with fixture information
- **GDTF Files**: Fixture profiles for accurate attribute mapping

## Project Structure

```
AttributeAddresser/
├── main.py                 # Application entry point
├── app.py                  # Main application window
├── config.py              # Configuration management
├── config.json            # User settings
├── requirements.txt       # Python dependencies
├── core/                  # Business logic modules
│   ├── data.py           # Data models and utilities
│   ├── mvr_parser.py     # MVR file parsing
│   ├── csv_parser.py     # CSV file parsing
│   ├── gdtf_parser.py    # GDTF file parsing
│   ├── matcher.py        # Fixture matching logic
│   ├── exporter.py       # Export functionality
│   └── project.py        # Project management
├── dialogs/              # Dialog windows
│   ├── mvr_dialog.py     # MVR import dialog
│   ├── csv_dialog.py     # CSV import dialog
│   ├── gdtf_dialog.py    # GDTF matching dialog
│   ├── settings_dialog.py # Settings dialog
│   └── ...
├── views/                # UI components
│   ├── fixture_grouping_table.py # Main fixture table
│   └── draggable_tables.py      # Draggable table components
└── controllers/          # Business logic controllers
    └── attribute_selection_controller.py
```

## Configuration

The application stores user preferences in `config.json`, including:
- Last used directories (MVR, CSV, GDTF, Projects)
- Recent projects list (up to 10 projects)
- Selected attributes
- GDTF profile matches
- Export settings
- Sequence numbering preferences

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

[Add your license information here]

## Support

For issues and questions, please create an issue on the GitHub repository. 