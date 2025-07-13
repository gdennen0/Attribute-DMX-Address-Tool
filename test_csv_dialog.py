#!/usr/bin/env python3
"""
Test script for CSV Import Dialog row selection functionality and import button state.
Run this to test the fixed multiple row selection features and debug import button issues.
"""

import sys
import os
from PyQt6.QtWidgets import QApplication

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from views.csv_import_dialog import CSVImportDialog

def main():
    """Test the CSV import dialog."""
    app = QApplication(sys.argv)
    
    # Create and show the dialog
    dialog = CSVImportDialog(None)
    dialog.show()
    
    print("CSV Import Dialog Test - Import Button Debug")
    print("=" * 60)
    print("TESTING THE IMPORT BUTTON STATE FIX")
    print("=" * 60)
    print()
    print("Step-by-step test procedure:")
    print()
    print("1. LOAD CSV FILE:")
    print("   • Click 'Browse CSV File...' button")
    print("   • Select any CSV file with headers")
    print("   • Watch console for DEBUG messages")
    print()
    print("2. CHECK INITIAL STATE:")
    print("   • Import button should be DISABLED initially")
    print("   • Debug should show missing column mappings")
    print("   • Rows should be checked by default")
    print()
    print("3. MAP REQUIRED COLUMNS:")
    print("   • In the Column Mapping section, map these REQUIRED fields:")
    print("     - Fixture Name -> appropriate CSV column")
    print("     - Universe -> appropriate CSV column") 
    print("     - DMX Address -> appropriate CSV column")
    print("     - Fixture Type -> appropriate CSV column")
    print("   • Watch console debug output after each mapping")
    print()
    print("4. VERIFY IMPORT BUTTON ENABLES:")
    print("   • After mapping all 4 required fields, button should ENABLE")
    print("   • Debug should show 'Button enabled: True'")
    print()
    print("5. TEST CHECKBOX DEPENDENCY:")
    print("   • Click 'Uncheck All' button")
    print("   • Import button should become DISABLED")
    print("   • Click 'Check All' button")
    print("   • Import button should become ENABLED again")
    print()
    print("EXPECTED DEBUG OUTPUT:")
    print("• Column mapping should show mapped fields")
    print("• All required mapped should be True when all 4 fields mapped")
    print("• Has data should be True after CSV loaded")
    print("• Has checked rows should be True when rows are checked")
    print("• Button enabled should be True when all conditions met")
    print()
    print("If import button stays disabled, check console for:")
    print("• Missing column mappings")
    print("• get_checked_rows errors")
    print("• False conditions in debug output")
    print()
    
    # Run the application
    sys.exit(app.exec())

if __name__ == '__main__':
    main() 