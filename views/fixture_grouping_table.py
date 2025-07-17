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
from PyQt6.QtGui import QFont, QColor, QPalette

from views.draggable_tables import DraggableTableWidget, DragDropTableModel


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
        headers = ["Fixture ID", "Fixture Name", "Attribute", "Sequence", 
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
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)  # Attribute
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)  # Sequence
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)  # ActivationGroup
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)  # Universe
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)  # Channel
        header.setSectionResizeMode(7, QHeaderView.ResizeMode.ResizeToContents)  # Absolute
        header.setSectionResizeMode(8, QHeaderView.ResizeMode.ResizeToContents)  # Routing
        
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
        """Update the fixture order based on current table order."""
        # Extract new fixture order from table
        new_fixture_order = []
        seen_fixtures = set()
        
        for row in range(self.model().rowCount()):
            row_data = self.model().getRowData(row)
            fixture_id = int(row_data.get('fixture_id', 0))
            
            if fixture_id not in seen_fixtures:
                new_fixture_order.append(fixture_id)
                seen_fixtures.add(fixture_id)
        
        # Update the fixtures list to match the new order
        self._reorder_fixtures(new_fixture_order)
        
        # Emit signal
        self.fixtureOrderChanged.emit(new_fixture_order)
        
        # Call callback if set
        if self._on_data_changed_callback:
            self._on_data_changed_callback()
    
    def _reorder_fixtures(self, new_order):
        """Reorder the fixtures list to match the new order."""
        # Create a mapping from fixture_id to fixture
        fixture_map = {fixture.get('fixture_id'): fixture for fixture in self._fixtures}
        
        # Reorder fixtures based on new order
        reordered_fixtures = []
        for fixture_id in new_order:
            if fixture_id in fixture_map:
                reordered_fixtures.append(fixture_map[fixture_id])
        
        # Add any fixtures that weren't in the new order (shouldn't happen, but just in case)
        for fixture in self._fixtures:
            if fixture.get('fixture_id') not in new_order:
                reordered_fixtures.append(fixture)
        
        self._fixtures = reordered_fixtures
    
    def getFixtures(self) -> List[Dict[str, Any]]:
        """Get the current fixtures list (in current order)."""
        return self._fixtures.copy()
    
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