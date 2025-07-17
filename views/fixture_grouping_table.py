"""
Fixture grouping table widget for AttributeAddresser.
Groups primary fixtures by their attribute rows and provides drag and drop functionality.
"""

from typing import List, Dict, Any, Optional, Callable
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QTableWidgetItem, QHeaderView, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QColor, QPalette, QDrag, QPixmap

from .draggable_tables import DraggableTableWidget, DragDropTableModel


class FixtureGroupingTable(DraggableTableWidget):
    """Table widget that groups fixtures by their attributes with drag and drop functionality."""
    
    # Signals for when fixture order changes
    fixtureOrderChanged = pyqtSignal(list)  # Emitted when fixture order changes
    attributeOrderChanged = pyqtSignal(dict)  # Emitted when attribute order changes within a fixture
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Store fixture data and grouping information
        self._fixtures = []  # List of fixture dictionaries
        self._grouped_data = []  # List of grouped attribute rows
        self._fixture_groups = {}  # Maps fixture_id to list of row indices
        self._row_to_fixture = {}  # Maps row index to fixture_id
        
        # Callback for when data changes
        self._on_data_changed_callback = None
        
        # Flag to prevent recursion in selectionChanged
        self._processing_selection = False
        
        # Connect drag and drop signals
        self.rowMoved.connect(self._on_row_moved)
        self.rowsMoved.connect(self._on_rows_moved)
        
        # Setup visual styling
        self._setup_styling()
    
    def _setup_styling(self):
        """Setup visual styling for the table."""
        # Enable alternating row colors
        self.setAlternatingRowColors(True)
        
        # Set selection behavior
        self.setSelectionBehavior(self.SelectionBehavior.SelectRows)
        self.setSelectionMode(self.SelectionMode.ExtendedSelection)
        
        # Configure header
        header = self.horizontalHeader()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)  # Fixture Name column
    
    def setFixtures(self, fixtures: List[Dict[str, Any]]):
        """Set the fixtures data and rebuild the table."""
        self._fixtures = fixtures.copy()
        self._rebuild_table()
    
    def _rebuild_table(self):
        """Rebuild the table with grouped fixture data."""
        # Clear existing data
        self._grouped_data = []
        self._fixture_groups = {}
        self._row_to_fixture = {}
        
        # Group fixtures by their attributes
        current_row = 0
        
        for fixture in self._fixtures:
            fixture_id = fixture.get('fixture_id', 0)
            fixture_rows = []
            
            # Get fixture type from GDTF profile or fallback to fixture type
            fixture_type = '—'
            if fixture.get('matched', False):
                profile_model = fixture.get('gdtf_profile')
                if profile_model and hasattr(profile_model, 'name'):
                    fixture_type = profile_model.name
                else:
                    fixture_type = fixture.get('type', '—')
            else:
                fixture_type = fixture.get('type', '—')
            
            if fixture.get('matched', False):
                # Get sorted attributes from the fixture's GDTF profile model
                profile_model = fixture.get('gdtf_profile')
                if profile_model:
                    selected_attributes = profile_model.get_sorted_attributes()
                else:
                    # Fallback to unsorted attributes if no profile model
                    selected_attributes = list(fixture.get('attributes', {}).keys())
                
                # Add each attribute as a separate row
                for attr_name in selected_attributes:
                    if attr_name in fixture.get('attributes', {}):
                        # Get attribute details
                        sequence_num = fixture.get('sequences', {}).get(attr_name, '—')
                        activation_group = fixture.get('activation_groups', {}).get(attr_name, '—')
                        
                        # Get address info - use calculated values from GDTF matching
                        absolute_address = fixture.get('addresses', {}).get(attr_name, '?')
                        universe = fixture.get('universes', {}).get(attr_name, '?')
                        channel = fixture.get('channels', {}).get(attr_name, '?')
                        
                        row_data = {
                            'Fixture ID': str(fixture_id),
                            'Fixture Name': fixture.get('name', ''),
                            'Fixture Type': fixture_type,
                            'Attribute': attr_name,
                            'Sequence': str(sequence_num),
                            'ActivationGroup': str(activation_group),
                            'Universe': str(universe),
                            'Channel': str(channel),
                            'Absolute': str(absolute_address),
                            'Routing': '',
                            'fixture_id': fixture_id,
                            'is_primary': True,
                            'attribute_name': attr_name
                        }
                        
                        self._grouped_data.append(row_data)
                        fixture_rows.append(current_row)
                        self._row_to_fixture[current_row] = fixture_id
                        current_row += 1
            else:
                # Show basic fixture info for unmatched fixtures
                row_data = {
                    'Fixture ID': str(fixture_id),
                    'Fixture Name': fixture.get('name', ''),
                    'Fixture Type': fixture_type,
                    'Attribute': f'Unmatched ({fixture.get("fixture_role", "none")})',
                    'Sequence': '—',
                    'ActivationGroup': '—',
                    'Universe': '—',
                    'Channel': '—',
                    'Absolute': '—',
                    'Routing': '—',
                    'fixture_id': fixture_id,
                    'is_primary': False,
                    'attribute_name': None
                }
                
                self._grouped_data.append(row_data)
                fixture_rows.append(current_row)
                self._row_to_fixture[current_row] = fixture_id
                current_row += 1
            
            # Store fixture group information
            if fixture_rows:
                self._fixture_groups[fixture_id] = fixture_rows
        
        # Update the table model
        self._update_table_model()
    
    def _update_table_model(self):
        """Update the table model with current grouped data."""
        headers = ["Fixture ID", "Fixture Name", "Fixture Type", "Attribute", "Sequence", 
                  "ActivationGroup", "Universe", "Channel", "Absolute", "Routing"]
        
        # Create new model
        model = DragDropTableModel(headers, self)
        model.setDataFromList(self._grouped_data)
        
        # Set the model
        self.setModel(model)
        
        # Configure column sizing
        header = self.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)  # Fixture ID
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)  # Fixture Name
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)  # Fixture Type
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)  # Attribute
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)  # Sequence
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)  # ActivationGroup
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)  # Universe
        header.setSectionResizeMode(7, QHeaderView.ResizeMode.ResizeToContents)  # Channel
        header.setSectionResizeMode(8, QHeaderView.ResizeMode.ResizeToContents)  # Absolute
        header.setSectionResizeMode(9, QHeaderView.ResizeMode.ResizeToContents)  # Routing
        
        # Apply visual grouping
        self._apply_visual_grouping()
    
    def _apply_visual_grouping(self):
        """Apply visual grouping to show which rows belong to which fixtures."""
        # This could be enhanced with background colors or borders
        # For now, we'll just ensure proper spacing and selection behavior
        pass
    
    def _on_row_moved(self, from_row, to_row):
        """Handle single row move."""
        self._update_fixture_order()
    
    def _on_rows_moved(self, selected_rows, target_row):
        """Handle multi-row move."""
        self._update_fixture_order()
    
    def _update_fixture_order(self):
        """Update fixture order based on current table order."""
        # Get the current order of fixtures from the table
        fixture_order = []
        seen_fixtures = set()
        
        for row in range(self.model().rowCount()):
            fixture_id = self._row_to_fixture.get(row)
            if fixture_id is not None and fixture_id not in seen_fixtures:
                fixture_order.append(fixture_id)
                seen_fixtures.add(fixture_id)
        
        # Emit the fixture order changed signal
        self.fixtureOrderChanged.emit(fixture_order)
        
        # Call the data changed callback if set
        if self._on_data_changed_callback:
            self._on_data_changed_callback()
    
    def get_selected_rows(self):
        """Override to automatically include all rows of selected fixtures."""
        # Get the base selected rows
        base_selected = super().get_selected_rows()
        
        # Expand selection to include all rows of selected fixtures
        expanded_selection = set(base_selected)
        
        for row in base_selected:
            fixture_id = self._row_to_fixture.get(row)
            if fixture_id is not None:
                # Add all rows belonging to this fixture
                fixture_rows = self._fixture_groups.get(fixture_id, [])
                expanded_selection.update(fixture_rows)
        
        return sorted(list(expanded_selection))
    
    def startDrag(self, supportedActions):
        """Override to ensure fixture-level grouping during drag operations."""
        # Get selected rows (this will automatically include all fixture rows)
        selected_rows = self.get_selected_rows()
        
        if not selected_rows:
            return
        
        # Store the expanded selection for the parent class to use
        self.drag_start_rows = selected_rows
        
        # Call the parent implementation which will handle the drag
        super().startDrag(supportedActions)
    
    def create_drag_pixmap(self):
        """Override to create fixture-level drag pixmap."""
        if not hasattr(self, 'drag_start_rows') or not self.drag_start_rows:
            return super().create_drag_pixmap()
        
        selected_rows = self.drag_start_rows
        
        # Count unique fixtures being dragged
        fixture_ids = set()
        for row in selected_rows:
            fixture_id = self._row_to_fixture.get(row)
            if fixture_id is not None:
                fixture_ids.add(fixture_id)
        
        # Create text for the pixmap
        if len(fixture_ids) == 1:
            fixture_id = list(fixture_ids)[0]
            fixture_name = ""
            for fixture in self._fixtures:
                if fixture.get('fixture_id') == fixture_id:
                    fixture_name = fixture.get('name', f'Fixture {fixture_id}')
                    break
            text = f"Moving fixture: {fixture_name}"
        else:
            text = f"Moving {len(fixture_ids)} fixtures ({len(selected_rows)} rows)"
        
        # Create pixmap
        from PyQt6.QtGui import QPainter, QFont
        font = QFont()
        font.setPointSize(10)
        
        # Calculate text size
        painter = QPainter()
        painter.setFont(font)
        text_rect = painter.boundingRect(0, 0, 1000, 1000, Qt.AlignmentFlag.AlignLeft, text)
        
        # Create pixmap with padding
        pixmap = QPixmap(text_rect.width() + 20, text_rect.height() + 10)
        pixmap.fill(QColor(240, 240, 240, 200))  # Semi-transparent background
        
        # Draw text
        painter.begin(pixmap)
        painter.setFont(font)
        painter.setPen(QColor(0, 0, 0))
        painter.drawText(10, text_rect.height() + 5, text)
        painter.end()
        
        return pixmap
    
    def selectRow(self, row):
        """Override to select all rows of the fixture when selecting a single row."""
        fixture_id = self._row_to_fixture.get(row)
        if fixture_id is not None:
            # Select all rows belonging to this fixture
            fixture_rows = self._fixture_groups.get(fixture_id, [])
            for fixture_row in fixture_rows:
                super().selectRow(fixture_row)
        else:
            super().selectRow(row)
    
    def selectionChanged(self, selected, deselected):
        """Override to ensure fixture-level selection when selection changes."""
        # Prevent recursion
        if self._processing_selection:
            return
        
        # Call parent implementation first
        super().selectionChanged(selected, deselected)
        
        # Get the newly selected rows
        newly_selected = set()
        for index in selected.indexes():
            newly_selected.add(index.row())
        
        # If there are newly selected rows, expand them to include all fixture rows
        if newly_selected:
            self._processing_selection = True
            
            try:
                expanded_selection = set()
                
                # Get all currently selected rows (including existing selection)
                current_selection = set()
                for index in self.selectedIndexes():
                    current_selection.add(index.row())
                
                # Expand each selected row to include all fixture rows
                for row in current_selection:
                    fixture_id = self._row_to_fixture.get(row)
                    if fixture_id is not None:
                        fixture_rows = self._fixture_groups.get(fixture_id, [])
                        expanded_selection.update(fixture_rows)
                    else:
                        expanded_selection.add(row)
                
                # Clear current selection and select expanded rows
                self.clearSelection()
                for row in sorted(expanded_selection):
                    super().selectRow(row)
            finally:
                self._processing_selection = False
    
    def selectRows(self, rows):
        """Override to ensure fixture-level selection."""
        # Expand selection to include all fixture rows
        expanded_rows = set()
        for row in rows:
            fixture_id = self._row_to_fixture.get(row)
            if fixture_id is not None:
                fixture_rows = self._fixture_groups.get(fixture_id, [])
                expanded_rows.update(fixture_rows)
            else:
                expanded_rows.add(row)
        
        # Clear current selection and select expanded rows
        self.clearSelection()
        for row in sorted(expanded_rows):
            super().selectRow(row)
    
    def setOnDataChangedCallback(self, callback: Callable[[], None]):
        """Set a callback to be called when fixture order changes."""
        self._on_data_changed_callback = callback
    
    def getFixtureGroups(self) -> Dict[int, List[int]]:
        """Get the current fixture groups mapping."""
        return self._fixture_groups.copy()
    
    def getRowToFixtureMapping(self) -> Dict[int, int]:
        """Get the mapping from row indices to fixture IDs."""
        return self._row_to_fixture.copy()
    
    def selectFixture(self, fixture_id: int):
        """Select all rows belonging to a specific fixture."""
        if fixture_id in self._fixture_groups:
            self.selectRows(self._fixture_groups[fixture_id])
    
    def getSelectedFixtures(self) -> List[int]:
        """Get list of fixture IDs that have selected rows."""
        selected_rows = self.getSelectedRows()
        selected_fixtures = set()
        
        for row in selected_rows:
            if row in self._row_to_fixture:
                selected_fixtures.add(self._row_to_fixture[row])
        
        return list(selected_fixtures)
    
    def get_selection_info(self):
        """Override to show fixture-level selection information."""
        selected_rows = self.getSelectedRows()
        if not selected_rows:
            return "No rows selected"
        
        # Count unique fixtures
        fixture_ids = set()
        for row in selected_rows:
            fixture_id = self._row_to_fixture.get(row)
            if fixture_id is not None:
                fixture_ids.add(fixture_id)
        
        if len(fixture_ids) == 1:
            fixture_id = list(fixture_ids)[0]
            fixture_name = ""
            for fixture in self._fixtures:
                if fixture.get('fixture_id') == fixture_id:
                    fixture_name = fixture.get('name', f'Fixture {fixture_id}')
                    break
            return f"Selected fixture: {fixture_name} ({len(selected_rows)} rows)"
        else:
            return f"Selected {len(fixture_ids)} fixtures ({len(selected_rows)} rows)"
    
    def moveFixtureToPosition(self, fixture_id: int, target_position: int):
        """Move a fixture to a specific position in the table."""
        if fixture_id not in self._fixture_groups:
            return
        
        fixture_rows = self._fixture_groups[fixture_id]
        if not fixture_rows:
            return
        
        # Calculate target row (first row of the fixture)
        target_row = target_position
        
        # Move all rows of the fixture
        self.rowsMoved.emit(fixture_rows, target_row)
    
    def insertFixtureAtPosition(self, fixture: Dict[str, Any], position: int):
        """Insert a fixture at a specific position."""
        # Add fixture to the list
        self._fixtures.insert(position, fixture)
        
        # Rebuild the table
        self._rebuild_table()
        
        # Select the newly inserted fixture
        fixture_id = fixture.get('fixture_id', 0)
        self.selectFixture(fixture_id)
    
    def removeFixture(self, fixture_id: int):
        """Remove a fixture from the table."""
        # Remove from fixtures list
        self._fixtures = [f for f in self._fixtures if f.get('fixture_id') != fixture_id]
        
        # Rebuild the table
        self._rebuild_table()
    
    def updateFixtureData(self, fixture_id: int, updated_fixture: Dict[str, Any]):
        """Update a specific fixture's data."""
        # Find and update the fixture
        for i, fixture in enumerate(self._fixtures):
            if fixture.get('fixture_id') == fixture_id:
                self._fixtures[i] = updated_fixture
                break
        
        # Rebuild the table
        self._rebuild_table()
    
    def clear(self):
        """Clear all fixtures from the table."""
        self._fixtures = []
        self._rebuild_table()
    
    def getFixtureAtRow(self, row: int) -> Optional[Dict[str, Any]]:
        """Get the fixture data for a specific row."""
        if row in self._row_to_fixture:
            fixture_id = self._row_to_fixture[row]
            for fixture in self._fixtures:
                if fixture.get('fixture_id') == fixture_id:
                    return fixture
        return None
    
    def getAttributeAtRow(self, row: int) -> Optional[str]:
        """Get the attribute name for a specific row."""
        if row < len(self._grouped_data):
            return self._grouped_data[row].get('attribute_name')
        return None 