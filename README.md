# AttributeAddresser

A professional tool for analyzing MVR and CSV files to extract lighting fixture addresses and generate DMX documentation.

## Features

- **Multi-Format Import Support:**
  - **MVR Files:** Complete analysis with embedded GDTF profiles
  - **CSV Files:** Flexible import with column mapping and fixture ID generation

- **Advanced GDTF Profile Matching:**
  - Automatic matching for MVR files with embedded GDTF profiles
  - External GDTF profile loading for CSV imports
  - Intelligent fuzzy matching between fixture types and GDTF profiles
  - Manual fixture type to GDTF profile mapping

- **Analysis:**
  - Per-fixture-type attribute selection
  - DMX address calculation with universe/channel mapping
  - Address conflict detection and reporting
  - Multiple export formats (Text, CSV, JSON, MA3 XML)

- **Output:**
  - CSV
  - Text
  - Json
  - MA3 XML DMX remote generation with configurable settings

## System Requirements

- Python 3.8+
- PyQt6
- Additional dependencies listed in requirements.txt

## Installation

1. Clone the repository
2. Install dependencies: `pip install -r requirements.txt`
3. Run the application: `python main.py`