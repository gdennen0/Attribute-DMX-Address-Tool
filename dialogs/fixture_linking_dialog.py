"""
Fixture linking dialog for managing master/remote fixture relationships.
Behaves like the old implementation's routing tab with automatic loading and row-based linking.
"""

from typing import List, Dict, Any, Optional
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QTableWidget, QTableWidgetItem, QHeaderView, QGroupBox, 
    QSplitter, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal

import core


class FixtureLinkingDialog(QDialog):
    """Dialog for managing master/remote fixture relationships via row-based linking."""
    
    relationships_updated = pyqtSignal()  # Signal when relationships change
    
    def __init__(self, fixtures: List[Dict[str, Any]], parent=None):
        super().__init__(parent)
        self.fixtures = fixtures
        
        self.setWindowTitle("Fixture Routing - Link by Row Position")
        self.setMinimumSize(1000, 700)
        
        self._setup_ui()
        self._populate_tables()
    
    def _setup_ui(self):
        """Set up the user interface."""
        layout = QVBoxLayout(self)
        
        # Instructions
        instructions = QLabel(
            "Fixtures are linked based on their row position. Master fixture at row 1 links to remote fixture at row 1, etc.\n"
            "Reorder fixtures by dragging rows to change the linking arrangement."
        )
        instructions.setWordWrap(True)
        layout.addWidget(instructions)
        
        # Main content - splitter with master and remote tables
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Master fixtures panel
        master_panel = self._setup_master_panel()
        splitter.addWidget(master_panel)
        
        # Remote fixtures panel
        remote_panel = self._setup_remote_panel()
        splitter.addWidget(remote_panel)
        
        splitter.setSizes([500, 500])
        layout.addWidget(splitter)
        
        # Link controls
        controls_layout = QHBoxLayout()
        
        self.link_by_row_button = QPushButton("Link by Row Position")
        self.link_by_row_button.setToolTip("Link master fixtures to remote fixtures based on their row position")
        self.link_by_row_button.clicked.connect(self._link_by_row_position)
        
        self.clear_links_button = QPushButton("Clear All Links")
        self.clear_links_button.clicked.connect(self._clear_all_links)
        
        controls_layout.addWidget(self.link_by_row_button)
        controls_layout.addWidget(self.clear_links_button)
        controls_layout.addStretch()
        layout.addLayout(controls_layout)
        
        # Dialog buttons
        button_layout = QHBoxLayout()
        self.close_button = QPushButton("Close")
        self.close_button.clicked.connect(self.accept)
        
        button_layout.addStretch()
        button_layout.addWidget(self.close_button)
        layout.addLayout(button_layout)
    
    def _setup_master_panel(self) -> QGroupBox:
        """Set up the master fixtures panel."""
        panel = QGroupBox("Master Fixtures")
        layout = QVBoxLayout(panel)
        
        # Master fixtures table
        self.master_table = QTableWidget()
        self._setup_master_table()
        layout.addWidget(self.master_table)
        
        return panel
    
    def _setup_remote_panel(self) -> QGroupBox:
        """Set up the remote fixtures panel."""
        panel = QGroupBox("Remote Fixtures")
        layout = QVBoxLayout(panel)
        
        # Remote fixtures table
        self.remote_table = QTableWidget()
        self._setup_remote_table()
        layout.addWidget(self.remote_table)
        
        return panel
    
    def _setup_master_table(self):
        """Set up the master fixtures table."""
        headers = ["Name", "Type", "Mode", "Address", "ID", "Linked Remote"]
        self.master_table.setColumnCount(len(headers))
        self.master_table.setHorizontalHeaderLabels(headers)
        
        # Configure column sizing
        header = self.master_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        for i in range(2, len(headers)):
            header.setSectionResizeMode(i, QHeaderView.ResizeMode.ResizeToContents)
        
        self.master_table.setAlternatingRowColors(True)
        self.master_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.master_table.setDragDropMode(QTableWidget.DragDropMode.InternalMove)
    
    def _setup_remote_table(self):
        """Set up the remote fixtures table."""
        headers = ["Name", "Type", "Mode", "Address", "ID", "Master Link"]
        self.remote_table.setColumnCount(len(headers))
        self.remote_table.setHorizontalHeaderLabels(headers)
        
        # Configure column sizing
        header = self.remote_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        for i in range(2, len(headers)):
            header.setSectionResizeMode(i, QHeaderView.ResizeMode.ResizeToContents)
        
        self.remote_table.setAlternatingRowColors(True)
        self.remote_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.remote_table.setDragDropMode(QTableWidget.DragDropMode.InternalMove)
    
    def _populate_tables(self):
        """Populate both tables with fixtures automatically."""
        self._populate_master_table()
        self._populate_remote_table()
        self._update_link_display()
    
    def _populate_master_table(self):
        """Populate the master fixtures table."""
        master_fixtures = [f for f in self.fixtures if core.get_fixture_role(f) == 'master']
        
        self.master_table.setRowCount(len(master_fixtures))
        
        for row, fixture in enumerate(master_fixtures):
            self.master_table.setItem(row, 0, QTableWidgetItem(fixture.get('name', '')))
            self.master_table.setItem(row, 1, QTableWidgetItem(fixture.get('type', '')))
            self.master_table.setItem(row, 2, QTableWidgetItem(fixture.get('mode', '')))
            self.master_table.setItem(row, 3, QTableWidgetItem(str(fixture.get('base_address', 1))))
            self.master_table.setItem(row, 4, QTableWidgetItem(str(fixture.get('fixture_id', 0))))
            
            # Linked remote info (will be updated by _update_link_display)
            self.master_table.setItem(row, 5, QTableWidgetItem("None"))
    
    def _populate_remote_table(self):
        """Populate the remote fixtures table."""
        remote_fixtures = [f for f in self.fixtures if core.get_fixture_role(f) == 'remote']
        
        self.remote_table.setRowCount(len(remote_fixtures))
        
        for row, fixture in enumerate(remote_fixtures):
            self.remote_table.setItem(row, 0, QTableWidgetItem(fixture.get('name', '')))
            self.remote_table.setItem(row, 1, QTableWidgetItem(fixture.get('type', '')))
            self.remote_table.setItem(row, 2, QTableWidgetItem(fixture.get('mode', '')))
            self.remote_table.setItem(row, 3, QTableWidgetItem(str(fixture.get('base_address', 1))))
            self.remote_table.setItem(row, 4, QTableWidgetItem(str(fixture.get('fixture_id', 0))))
            
            # Master link info (will be updated by _update_link_display)
            self.remote_table.setItem(row, 5, QTableWidgetItem("None"))
    
    def _link_by_row_position(self):
        """Link master and remote fixtures based on their row position."""
        master_fixtures = [f for f in self.fixtures if core.get_fixture_role(f) == 'master']
        remote_fixtures = [f for f in self.fixtures if core.get_fixture_role(f) == 'remote']
        
        if not master_fixtures:
            QMessageBox.information(self, "No Masters", "No master fixtures found. Please assign fixture roles during import.")
            return
        
        if not remote_fixtures:
            QMessageBox.information(self, "No Remotes", "No remote fixtures found. Please assign fixture roles during import.")
            return
        
        # Link fixtures based on row position
        links_created = 0
        max_links = min(len(master_fixtures), len(remote_fixtures))
        
        for i in range(max_links):
            master_fixture = master_fixtures[i]
            remote_fixture = remote_fixtures[i]
            
            # Create the link
            if core.link_remote_to_master(remote_fixture, master_fixture):
                links_created += 1
        
        # Update display
        self._update_link_display()
        self.relationships_updated.emit()
        
        # Show confirmation
        if links_created > 0:
            extra_masters = len(master_fixtures) - max_links
            extra_remotes = len(remote_fixtures) - max_links
            
            message = f"Linked {links_created} fixture pairs by row position."
            if extra_masters > 0:
                message += f"\n{extra_masters} master fixture(s) had no corresponding remote."
            if extra_remotes > 0:
                message += f"\n{extra_remotes} remote fixture(s) had no corresponding master."
            
            QMessageBox.information(self, "Linking Complete", message)
        else:
            QMessageBox.warning(self, "No Links Created", "No fixtures were linked. Check that you have both master and remote fixtures.")
    
    def _clear_all_links(self):
        """Clear all fixture links."""
        reply = QMessageBox.question(
            self, "Clear Links", 
            "Are you sure you want to clear all fixture links?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # Clear all links
            remote_fixtures = [f for f in self.fixtures if core.get_fixture_role(f) == 'remote']
            for remote_fixture in remote_fixtures:
                master_fixture = core.get_master_for_remote(remote_fixture, self.fixtures)
                if master_fixture:
                    core.unlink_remote_from_master(remote_fixture, master_fixture)
            
            # Update display
            self._update_link_display()
            self.relationships_updated.emit()
            
            QMessageBox.information(self, "Links Cleared", "All fixture links have been cleared.")
    
    def _update_link_display(self):
        """Update the link information displayed in both tables."""
        # Update master table
        master_fixtures = [f for f in self.fixtures if core.get_fixture_role(f) == 'master']
        for row, master_fixture in enumerate(master_fixtures):
            if row < self.master_table.rowCount():
                linked_remotes = core.get_linked_remotes(master_fixture, self.fixtures)
                if linked_remotes:
                    remote_names = [r['name'] for r in linked_remotes]
                    link_text = f"{', '.join(remote_names[:2])}"
                    if len(remote_names) > 2:
                        link_text += f" (+{len(remote_names) - 2} more)"
                else:
                    link_text = "None"
                
                self.master_table.setItem(row, 5, QTableWidgetItem(link_text))
        
        # Update remote table
        remote_fixtures = [f for f in self.fixtures if core.get_fixture_role(f) == 'remote']
        for row, remote_fixture in enumerate(remote_fixtures):
            if row < self.remote_table.rowCount():
                master_fixture = core.get_master_for_remote(remote_fixture, self.fixtures)
                if master_fixture:
                    link_text = master_fixture['name']
                else:
                    link_text = "None"
                
                self.remote_table.setItem(row, 5, QTableWidgetItem(link_text)) 