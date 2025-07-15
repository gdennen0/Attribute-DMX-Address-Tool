"""
AttributeAddresser - Main Entry Point
A simple tool to analyze MVR files and extract fixture addresses.

Completely rewritten for simplicity and maintainability.
"""
import sys
import os

# Add the current directory to Python path so we can import our modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import main as app_main


def main():
    """Start the AttributeAddresser application."""
    print("Starting AttributeAddresser v2.0...")
    
    # Start the GUI application
    app_main()


if __name__ == "__main__":
    main() 