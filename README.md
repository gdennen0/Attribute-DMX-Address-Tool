# AttributeAddresser v2.0

A professional tool for analyzing MVR and CSV files to extract lighting fixture addresses and generate DMX documentation.

**Completely rewritten for simplicity and maintainability.**

## Features

- **Multi-Format Import Support:**
  - **MVR Files:** Complete analysis with embedded GDTF profiles
  - **CSV Files:** Flexible import with column mapping and fixture ID generation

- **Advanced GDTF Profile Matching:**
  - Automatic matching for MVR files with embedded GDTF profiles
  - External GDTF profile loading for CSV imports
  - Intelligent fuzzy matching between fixture types and GDTF profiles

- **Analysis:**
  - Per-fixture attribute selection with checkboxes
  - DMX address calculation with sequence numbering
  - Multiple export formats (Text, CSV, JSON, MA3 XML)

- **Clean Architecture:**
  - Simple data structures using dictionaries and lists
  - Complete separation of UI logic from business logic
  - Minimal codebase with single-responsibility functions
  - Easy to modify and maintain

## System Requirements

- Python 3.8+
- PyQt6

## Installation

1. Clone the repository
2. Install dependencies: `pip install -r requirements.txt`
3. Run the application: `python main.py`

## Architecture

The application uses a clean, simple architecture:

```
main.py              # Entry point
app.py               # Main window with clean UI layout
config.py            # Configuration management
core/                # Business logic (pure functions)
  ├── data.py        # Simple data structures
  ├── mvr_parser.py  # MVR file parsing
  ├── csv_parser.py  # CSV file parsing  
  ├── gdtf_parser.py # GDTF profile parsing
  ├── matcher.py     # Fixture matching logic
  └── exporter.py    # Export functionality
dialogs/             # UI dialog windows
  ├── mvr_dialog.py  # MVR import with checkboxes
  ├── csv_dialog.py  # CSV import with table matching
  └── settings_dialog.py # Settings configuration
```

## Usage

1. **Import fixtures:** Use "Import MVR..." or "Import CSV..." to load fixture data
2. **Select fixtures:** Use checkboxes to choose which fixtures to include
3. **Link fixtures (optional):** Use "Link Fixtures..." to set up master/remote relationships
   - Designate fixtures as master or remote
   - Link remote fixtures to master fixtures
   - Masters pass their sequence numbers to linked remotes
4. **Select attributes:** Choose which fixture attributes to export
5. **Export:** Generate output in your preferred format (Text, CSV, JSON, MA3 XML)

### Master/Remote Fixture Relationships

The application supports master/remote fixture relationships where:
- **Master fixtures** generate sequence numbers for their attributes
- **Remote fixtures** can be linked to master fixtures to inherit their sequence numbers
- Multiple remotes can be linked to a single master
- Unlinked remotes get their own unique sequence numbers
- Use the "Link Fixtures..." dialog to manage these relationships

The application maintains the same user experience as the original while being much simpler and more maintainable underneath.