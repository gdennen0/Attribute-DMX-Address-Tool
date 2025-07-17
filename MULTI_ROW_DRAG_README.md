# Multi-Row Selection & Dragging Functionality

The AttributeAddresser application includes comprehensive multi-row selection and dragging functionality that allows users to select and move multiple rows simultaneously while maintaining their relative order.

## Features

### Multi-Row Selection
- **Ctrl+Click**: Select individual rows
- **Shift+Click**: Select ranges of rows
- **Click and Drag**: Select multiple rows by dragging over them
- **Ctrl+A**: Select all rows in the table
- **Shift+Up/Down**: Extend selection using keyboard

### Multi-Row Dragging
- **Visual Feedback**: Shows the number of rows being dragged
- **Maintains Order**: Selected rows maintain their relative order when moved
- **Drop Indicator**: Blue line shows where rows will be inserted
- **Cursor Changes**: Cursor changes to indicate drag operation

### Keyboard Shortcuts
- **Ctrl+A**: Select all rows
- **Delete**: Delete selected rows
- **Shift+Up**: Extend selection upward
- **Shift+Down**: Extend selection downward

### Context Menu
- **Selection Info**: Shows current selection details
- **Delete Selected**: Delete all selected rows
- **Insert Above**: Insert row above selection
- **Insert Below**: Insert row below selection

## How to Use

### Selecting Multiple Rows

1. **Individual Selection**: Hold Ctrl and click on rows to select them individually
2. **Range Selection**: Click on a row, then hold Shift and click on another row to select the range
3. **Drag Selection**: Click and drag over multiple rows to select them
4. **Select All**: Press Ctrl+A to select all rows

### Dragging Multiple Rows

1. **Select Rows**: Use any of the selection methods above to select multiple rows
2. **Start Drag**: Click and drag on any selected row
3. **Visual Feedback**: A semi-transparent overlay shows the number of rows being dragged
4. **Drop**: Release the mouse button where you want to insert the rows
5. **Result**: All selected rows move together, maintaining their relative order

### Example Workflow

```
1. Select rows 2, 3, and 4 using Ctrl+Click
2. Click and drag on row 2
3. Drag to position 7
4. Release to move rows 2, 3, 4 to positions 7, 8, 9
```

## Technical Implementation

### Key Classes

- **`DraggableTableView`**: Main table view with drag and drop functionality
- **`DragDropTableModel`**: Custom model that handles MIME data for drag operations
- **`DragDropIndicator`**: Visual indicator for drop zones
- **`DraggableTableWidget`**: Widget wrapper with QTableWidget compatibility

### Signals

- **`rowMoved(int, int)`**: Emitted for single row moves (backward compatibility)
- **`rowsMoved(list, int)`**: Emitted for multi-row moves with selected rows and target position
- **`rowInserted(int)`**: Emitted when a row is inserted
- **`rowDeleted(int)`**: Emitted when a row is deleted

### MIME Data Handling

The implementation uses custom MIME data encoding to track which rows are being dragged:

```python
def encodeData(self, indexes):
    """Encode data for MIME operations."""
    rows = set()
    for index in indexes:
        if index.isValid():
            rows.add(index.row())
    return str(sorted(rows)).encode()
```

## Testing

Run the test application to see the functionality in action:

```bash
python test_multi_row_drag.py
```

This will open a test window with sample data where you can practice multi-row selection and dragging.

## Integration

The multi-row functionality is already integrated into the main application:

- **Master Fixtures Table**: Uses `FixtureGroupingTable` which extends `DraggableTableWidget`
- **Remote Fixtures Table**: Also uses `FixtureGroupingTable` for consistent behavior
- **All Tables**: Inherit the multi-row selection and dragging capabilities

## Benefits

1. **Improved Productivity**: Move multiple fixtures at once instead of one by one
2. **Visual Feedback**: Clear indication of what's being moved and where
3. **Maintains Order**: Relative order of selected items is preserved
4. **Intuitive Interface**: Standard selection and drag patterns users expect
5. **Keyboard Support**: Full keyboard accessibility for power users

## Future Enhancements

Potential improvements could include:

- **Group Selection**: Select entire fixture groups at once
- **Undo/Redo**: Support for undoing multi-row operations
- **Copy/Paste**: Copy selected rows to clipboard
- **Filtered Selection**: Select rows based on criteria
- **Bulk Operations**: Apply operations to multiple selected rows 