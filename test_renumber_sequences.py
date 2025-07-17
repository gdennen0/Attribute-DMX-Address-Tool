#!/usr/bin/env python3
"""
Test script for the renumber sequences functionality.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import Config
from dialogs.renumber_sequences_dialog import RenumberSequencesDialog
from PyQt6.QtWidgets import QApplication


def test_renumber_sequences_config():
    """Test the renumber sequences configuration functionality."""
    print("Testing renumber sequences configuration...")
    
    # Create a config instance
    config = Config()
    
    # Test default values
    default_config = config.get_renumber_sequences_config()
    print(f"Default config: {default_config}")
    
    # Test setting new values
    test_config = {
        "start_number": 2001,
        "interval": 2,
        "add_breaks": True,
        "break_sequences": 10
    }
    
    config.set_renumber_sequences_config(test_config)
    
    # Verify the values were saved
    saved_config = config.get_renumber_sequences_config()
    print(f"Saved config: {saved_config}")
    
    # Test that values match
    assert saved_config == test_config, "Config values don't match!"
    print("✓ Configuration save/load test passed!")
    
    # Reset to defaults
    config.set_renumber_sequences_config(default_config)
    print("✓ Configuration reset test passed!")


def test_renumber_sequences_dialog():
    """Test the renumber sequences dialog."""
    print("\nTesting renumber sequences dialog...")
    
    # Create QApplication if not already created
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    
    # Create config
    config = Config()
    
    # Test dialog creation
    try:
        dialog = RenumberSequencesDialog(config)
        print("✓ Dialog creation test passed!")
        
        # Test getting settings
        settings = dialog.get_settings()
        print(f"Dialog settings: {settings}")
        print("✓ Dialog settings test passed!")
        
        dialog.close()
        
    except Exception as e:
        print(f"✗ Dialog test failed: {e}")
        return False
    
    return True


def test_renumber_logic():
    """Test the renumbering logic."""
    print("\nTesting renumbering logic...")
    
    # Simulate the renumbering logic
    start_number = 1001
    interval = 2
    add_breaks = True
    break_sequences = 5
    
    # Simulate fixtures with attributes
    fixtures = [
        {
            'matched': True,
            'attributes': {'R': 0, 'G': 1, 'B': 2},
            'sequences': {}
        },
        {
            'matched': True,
            'attributes': {'R': 0, 'G': 1, 'B': 2},
            'sequences': {}
        }
    ]
    
    sequence_num = start_number
    total_sequences = 0
    
    for fixture in fixtures:
        if fixture.get('matched', False):
            if 'sequences' not in fixture:
                fixture['sequences'] = {}
            
            # Assign sequences to each attribute
            for attr_name in fixture.get('attributes', {}).keys():
                fixture['sequences'][attr_name] = sequence_num
                print(f"  Assigned sequence {sequence_num} to {attr_name}")
                sequence_num += interval
                total_sequences += 1
            
            # Add break after all attributes for this fixture if enabled
            if add_breaks:
                print(f"  Adding break of {break_sequences} sequences")
                sequence_num += break_sequences
    
    print(f"Total sequences assigned: {total_sequences}")
    print(f"Final sequence number: {sequence_num}")
    
    # Verify the logic
    expected_sequences = 6  # 2 fixtures * 3 attributes each
    # Calculate expected final number: start + (sequences-1)*interval + break_sequences
    # For 6 sequences with interval 2: 1001 + 5*2 = 1011, then add break_sequences (5) = 1016
    expected_final = start_number + (expected_sequences - 1) * interval + break_sequences
    
    assert total_sequences == expected_sequences, f"Expected {expected_sequences} sequences, got {total_sequences}"
    assert sequence_num == expected_final, f"Expected final number {expected_final}, got {sequence_num}"
    
    print("✓ Renumbering logic test passed!")
    
    # Print the results
    for i, fixture in enumerate(fixtures):
        print(f"Fixture {i+1} sequences: {fixture['sequences']}")


def main():
    """Run all tests."""
    print("Running renumber sequences tests...\n")
    
    try:
        test_renumber_sequences_config()
        test_renumber_logic()
        
        if test_renumber_sequences_dialog():
            print("\n✓ All tests passed!")
        else:
            print("\n✗ Some tests failed!")
            
    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main() 