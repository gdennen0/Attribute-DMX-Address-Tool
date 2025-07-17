#!/usr/bin/env python3
"""
Test the multi-row move logic without GUI.
"""

def test_multi_row_move_logic():
    """Test the multi-row move logic with sample data."""
    
    # Simulate table data
    table_data = [
        {"ID": "1", "Name": "Fixture A"},
        {"ID": "2", "Name": "Fixture B"},
        {"ID": "3", "Name": "Fixture C"},
        {"ID": "4", "Name": "Fixture D"},
        {"ID": "5", "Name": "Fixture E"},
        {"ID": "6", "Name": "Fixture F"},
        {"ID": "7", "Name": "Fixture G"},
        {"ID": "8", "Name": "Fixture H"},
    ]
    
    def perform_multi_row_move(source_rows, target_row, data):
        """Simulate the multi-row move logic."""
        print(f"Moving rows {source_rows} to target {target_row}")
        print(f"Original data: {[row['Name'] for row in data]}")
        
        # Store all row data first
        row_data_list = []
        for source_row in source_rows:
            row_data = data[source_row].copy()
            row_data_list.append(row_data)
            print(f"Stored data for row {source_row}: {row_data}")
        
        # Remove all source rows in reverse order to maintain indices
        for source_row in reversed(source_rows):
            print(f"Removing row {source_row}")
            del data[source_row]
        
        # Calculate the final target position after removing source rows
        final_target = target_row
        for source_row in source_rows:
            if source_row < target_row:
                final_target -= 1
        
        print(f"Final target position: {final_target}")
        
        # Insert all rows at the target position
        moved_rows = []
        for i, row_data in enumerate(row_data_list):
            insert_position = final_target + i
            print(f"Inserting row at position {insert_position}")
            data.insert(insert_position, row_data)
            moved_rows.append(insert_position)
        
        print(f"Moved rows to positions: {moved_rows}")
        print(f"Final data: {[row['Name'] for row in data]}")
        print()
        return moved_rows
    
    # Test cases
    test_cases = [
        ([1, 2], 5),  # Move rows 1,2 to position 5
        ([0, 1], 3),  # Move rows 0,1 to position 3
        ([2, 3, 4], 0),  # Move rows 2,3,4 to beginning
        ([5, 6], 8),  # Move rows 5,6 to end
    ]
    
    for i, (source_rows, target_row) in enumerate(test_cases):
        print(f"=== Test Case {i+1} ===")
        test_data = table_data.copy()
        result = perform_multi_row_move(source_rows, target_row, test_data)
        print(f"Result: {result}")
        print()

if __name__ == "__main__":
    test_multi_row_move_logic() 