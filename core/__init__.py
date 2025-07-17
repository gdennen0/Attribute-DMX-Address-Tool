"""
Core functionality for AttributeAddresser.
Clean separation of business logic from UI.
"""

from . import data
from . import csv_parser
from . import mvr_parser
from . import gdtf_parser
from . import matcher
from . import exporter
from . import project

# Re-export commonly used functions
from .data import (
    create_fixture, create_gdtf_profile, create_project_state,
    get_fixture_attributes, set_fixture_selected, is_fixture_selected,
    set_fixture_role, get_fixture_role, get_master_fixtures, get_remote_fixtures,
    get_master_fixtures_matched, get_remote_fixtures_matched,
    get_fixtures_by_role, get_fixtures_by_role_matched,
    validate_fixture_roles, ensure_fixture_role_consistency,
    get_fixture_by_id, get_fixtures_by_type, get_fixtures_by_type_and_role,
    match_fixture_to_gdtf, assign_sequences, get_export_data,
    calculate_universe_and_channel
)

from .mvr_parser import parse_mvr_file, validate_mvr_file
from .csv_parser import (
    parse_csv_file, parse_csv_file_with_fixture_id_validation, get_csv_preview, 
    create_column_mapping, validate_csv_file, get_fixture_count
)
from .gdtf_parser import parse_gdtf_file, parse_external_gdtf_folder
from .matcher import auto_match_fixtures, get_match_summary
from .project import project_manager 