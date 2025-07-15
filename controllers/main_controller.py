"""
Controller for MVR File Analyzer.
Handles business logic and coordinates between services.
"""

import traceback
from typing import Dict, List, Any, Optional
from pathlib import Path

from services.mvr_service import MVRService
from services.gdtf_service import GDTFService
from services.csv_service import CSVService
from services.fixture_processing_service import FixtureProcessingService
from models.data_models import FixtureMatch, AnalysisResults


class MVRController:
    """
    Controller for the MVR File Analyzer.
    Coordinates between UI and services with unified fixture processing.
    """
    
    def __init__(self):
        self.mvr_service = MVRService()
        self.gdtf_service = GDTFService()
        self.csv_service = CSVService()
        self.fixture_service = FixtureProcessingService()
        
        # Original single-dataset storage (for backward compatibility)
        self.loaded_fixtures = []
        self.matched_fixtures = []
        self.current_file_path = None
        self.current_import_type = None  # 'mvr' or 'csv'
        self.analysis_results = None
        
        # Master and Remote datasets
        self.master_fixtures = []
        self.master_matched_fixtures = []
        self.master_file_path = None
        self.master_import_type = None
        
        self.remote_fixtures = []
        self.remote_matched_fixtures = []
        self.remote_file_path = None
        self.remote_import_type = None
        
        # Alignment results
        self.alignment_results = None
        
        # Manual alignment tracking
        self.manual_alignments = {}  # Dict mapping master_fixture_id -> remote_fixture_id
        self.alignment_mode = "automatic"  # "automatic" or "manual"
    
    def load_fixtures_unified(self, source_type: str, **kwargs) -> Dict[str, Any]:
        """
        Unified fixture loading method that handles both MVR and CSV sources.
        
        Args:
            source_type: 'mvr' or 'csv'
            **kwargs: Additional arguments specific to the source type
            
        Returns:
            Dict containing load status and fixture information
        """
        try:
            if source_type == 'mvr':
                return self._load_mvr_fixtures(**kwargs)
            elif source_type == 'csv':
                return self._load_csv_fixtures(**kwargs)
            else:
                raise ValueError(f"Unsupported source type: {source_type}")
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "details": traceback.format_exc()
            }
    
    def _load_mvr_fixtures(self, file_path: str) -> Dict[str, Any]:
        """Load fixtures from MVR file using unified approach."""
        self.current_file_path = file_path
        self.current_import_type = 'mvr'
        
        # Load fixtures using unified service
        self.matched_fixtures = self.fixture_service.load_fixtures_from_mvr(file_path)
        
        # Load GDTF profiles from the MVR
        internal_profiles = self.gdtf_service.load_profiles_from_mvr(file_path)
        
        # Try initial matching using MVR profiles (exact matches only)
        self.matched_fixtures = self.gdtf_service.match_fixture_objects(
            self.matched_fixtures, internal_profiles
        )
        
        # Get summary
        summary = self._get_matching_summary(self.matched_fixtures)
        fixture_summary = self.fixture_service.get_fixture_summary(self.matched_fixtures)
        
        return {
            "success": True,
            "fixtures": self.matched_fixtures,  # Add the fixtures to the result
            "total_fixtures": summary["total_fixtures"],
            "matched_fixtures": summary["matched"],
            "unmatched_fixtures": summary["gdtf_missing"] + summary["mode_missing"],
            "gdtf_profiles_loaded": len(internal_profiles),
            "fixture_types": fixture_summary["fixture_types"],
            "unmatched_fixture_data": [f for f in self.matched_fixtures if f.match_status != "matched"],
            "import_type": "mvr",
            "match_rate": summary["match_rate"]
        }
    
    def _load_csv_fixtures(self, file_path: str = None, headers: List[str] = None, 
                          data_rows: List[List[str]] = None, column_mapping: Dict[str, int] = None,
                          fixture_id_config: Dict[str, Any] = None) -> Dict[str, Any]:
        """Load fixtures from CSV using unified approach."""
        self.current_import_type = 'csv'
        
        # Load fixtures using unified service
        if file_path:
            self.matched_fixtures = self.fixture_service.load_fixtures_from_csv(
                file_path, column_mapping, fixture_id_config
            )
        else:
            self.matched_fixtures = self.fixture_service.load_fixtures_from_csv_data(
                headers, data_rows, column_mapping, fixture_id_config
            )
        
        # Get summary (CSV fixtures start unmatched)
        summary = self._get_matching_summary(self.matched_fixtures)
        fixture_summary = self.fixture_service.get_fixture_summary(self.matched_fixtures)
        
        return {
            "success": True,
            "total_fixtures": summary["total_fixtures"],
            "matched_fixtures": summary["matched"],
            "unmatched_fixtures": summary["gdtf_missing"] + summary["mode_missing"],
            "gdtf_profiles_loaded": 0,  # No internal profiles from CSV
            "fixture_types": fixture_summary["fixture_types"],
            "unmatched_fixture_data": [f for f in self.matched_fixtures if f.match_status != "matched"],
            "import_type": "csv",
            "match_rate": summary["match_rate"]
        }
    
    def _get_matching_summary(self, fixtures: List[FixtureMatch]) -> Dict[str, Any]:
        """Get a summary of matching results for fixtures."""
        if not fixtures:
            return {
                "total_fixtures": 0,
                "matched": 0,
                "gdtf_missing": 0,
                "mode_missing": 0,
                "error": 0,
                "match_rate": 0.0
            }
        
        total = len(fixtures)
        matched = sum(1 for f in fixtures if f.match_status == "matched")
        gdtf_missing = sum(1 for f in fixtures if f.match_status == "gdtf_missing")
        mode_missing = sum(1 for f in fixtures if f.match_status == "mode_missing")
        error = sum(1 for f in fixtures if f.match_status == "error")
        
        return {
            "total_fixtures": total,
            "matched": matched,
            "gdtf_missing": gdtf_missing,
            "mode_missing": mode_missing,
            "error": error,
            "match_rate": (matched / total * 100) if total > 0 else 0.0
        }
    
    # Legacy methods for backward compatibility
    def load_mvr_file(self, file_path: str) -> Dict[str, Any]:
        """Load an MVR file (legacy method)."""
        return self.load_fixtures_unified('mvr', file_path=file_path)
    
    def load_csv_fixtures(self, fixture_matches: List[FixtureMatch]) -> Dict[str, Any]:
        """Load fixtures from CSV import (legacy method)."""
        try:
            self.current_import_type = 'csv'
            self.matched_fixtures = fixture_matches
            
            # Get summary
            summary = self._get_matching_summary(self.matched_fixtures)
            fixture_summary = self.fixture_service.get_fixture_summary(self.matched_fixtures)
            
            return {
                "success": True,
                "total_fixtures": summary["total_fixtures"],
                "matched_fixtures": summary["matched"],
                "unmatched_fixtures": summary["gdtf_missing"] + summary["mode_missing"],
                "gdtf_profiles_loaded": 0,
                "fixture_types": fixture_summary["fixture_types"],
                "unmatched_fixture_data": [f for f in self.matched_fixtures if f.match_status != "matched"],
                "import_type": "csv",
                "match_rate": summary["match_rate"]
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "details": traceback.format_exc()
            }
    
    def load_external_gdtf_profiles(self, folder_path: str) -> Dict[str, Any]:
        """
        Load GDTF profiles from external folder.
        
        Returns:
            Dict containing load status and profile information
        """
        try:
            profiles = self.gdtf_service.load_profiles_from_folder(folder_path)
            
            return {
                "success": True,
                "profiles_loaded": len(profiles),
                "profile_names": list(profiles.keys())
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "details": traceback.format_exc()
            }
    
    def update_fixture_matches(self, fixture_type_matches: Dict[str, Dict[str, str]]) -> Dict[str, Any]:
        """
        Update fixture matches based on user selections.
        
        Args:
            fixture_type_matches: Dict mapping fixture_type -> {"profile": str, "mode": str}
            
        Returns:
            Dict containing update status and match information
        """
        try:
            # Apply user selections to fixtures
            updated_fixtures = []
            
            for fixture in self.matched_fixtures:
                fixture_type = fixture.gdtf_spec or "Unknown"
                
                # Try exact match first
                match_info = None
                if fixture_type in fixture_type_matches:
                    match_info = fixture_type_matches[fixture_type]
                else:
                    # Try without .gdtf extension if exact match fails
                    fixture_type_clean = fixture_type.replace('.gdtf', '') if fixture_type.endswith('.gdtf') else fixture_type
                    if fixture_type_clean in fixture_type_matches:
                        match_info = fixture_type_matches[fixture_type_clean]
                
                if match_info:
                    profile_name = match_info.get("profile", "")
                    mode_name = match_info.get("mode", "")
                    
                    if profile_name and mode_name:
                        # Apply the selected profile and mode
                        updated_fixture = self.gdtf_service.apply_profile_to_fixture(
                            fixture, profile_name, mode_name
                        )
                        updated_fixtures.append(updated_fixture)
                    else:
                        updated_fixtures.append(fixture)
                else:
                    updated_fixtures.append(fixture)
            
            self.matched_fixtures = updated_fixtures
            
            # Calculate new match statistics
            total_fixtures = len(self.matched_fixtures)
            matched_count = sum(1 for f in self.matched_fixtures if f.match_status == "matched")
            
            return {
                "success": True,
                "total_fixtures": total_fixtures,
                "matched_fixtures": matched_count,
                "unmatched_fixtures": total_fixtures - matched_count,
                "match_rate": (matched_count / total_fixtures * 100) if total_fixtures > 0 else 0
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "details": traceback.format_exc()
            }
    
    def analyze_fixtures(self, selected_attributes: List[str], output_format: str = "text", ma3_config: dict = None) -> Dict[str, Any]:
        """
        Analyze fixtures with selected attributes (legacy method for backward compatibility).
        
        Args:
            selected_attributes: List of attribute names to analyze
            output_format: Format for output data
            
        Returns:
            Dict containing analysis results
        """
        try:
            if not self.matched_fixtures:
                return {
                    "success": False,
                    "error": "No fixtures loaded"
                }
            
            # Run analysis
            results = self.mvr_service.analyze_fixtures(
                self.matched_fixtures, selected_attributes, output_format, ma3_config
            )
            
            # Store results
            self.analysis_results = results
            
            return {
                "success": True,
                "analysis_results": results,
                "export_data": results.export_data,
                "summary": results.summary
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "details": traceback.format_exc()
            }
    
    def analyze_fixtures_by_type(self, fixture_type_attributes: Dict[str, List[str]], output_format: str = "text", ma3_config: dict = None, sequence_start: int = 1, table_order: List[tuple] = None) -> Dict[str, Any]:
        """
        Analyze fixtures with per-fixture-type attributes.
        
        Args:
            fixture_type_attributes: Dict mapping fixture_type -> list of attribute names
            output_format: Format for output data
            sequence_start: Starting number for global sequence numbering
            table_order: Optional list of (fixture_id, attribute_name) tuples defining the order
            
        Returns:
            Dict containing analysis results
        """
        try:
            if not self.matched_fixtures:
                return {
                    "success": False,
                    "error": "No fixtures loaded"
                }
            
            # Validate that we have some attributes to analyze
            total_attributes = sum(len(attrs) for attrs in fixture_type_attributes.values())
            if total_attributes == 0:
                return {
                    "success": False,
                    "error": "No attributes selected for analysis"
                }
            
            # Run analysis per fixture type
            results = self.mvr_service.analyze_fixtures_by_type(
                self.matched_fixtures, fixture_type_attributes, output_format, ma3_config, sequence_start, table_order
            )
            
            # Store results
            self.analysis_results = results
            
            return {
                "success": True,
                "analysis_results": results,
                "export_data": results.export_data,
                "summary": results.summary
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def export_results(self, results: Dict[str, Any], output_format: str, file_path: str, ma3_config: dict = None) -> Dict[str, Any]:
        """
        Export analysis results to a file.
        
        Args:
            results: Analysis results dictionary
            output_format: Format to export
            file_path: Path to save the file
            ma3_config: MA3 XML configuration if needed
            
        Returns:
            Dict containing export status
        """
        try:
            if not results or "analysis_results" not in results:
                return {
                    "success": False,
                    "error": "No analysis results available for export"
                }
            
            analysis_results = results["analysis_results"]
            
            # Export using the service
            export_data = self.mvr_service.export_results(
                analysis_results, output_format, file_path, ma3_config
            )
            
            return {
                "success": True,
                "file_path": file_path,
                "export_data": export_data
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "details": traceback.format_exc()
            }
    
    def get_available_attributes(self) -> List[str]:
        """Get all available attributes from loaded GDTF profiles."""
        return self.gdtf_service.get_available_attributes()
    
    def get_available_profiles(self) -> List[str]:
        """Get list of available GDTF profile names."""
        return self.gdtf_service.get_available_profiles()
    
    def get_profiles_by_source(self) -> Dict[str, List[str]]:
        """Get GDTF profiles grouped by source (mvr or external)."""
        return self.gdtf_service.get_profiles_by_source()
    
    def get_gdtf_loading_status(self) -> Dict[str, Any]:
        """Get status of GDTF loading."""
        profiles = self.gdtf_service.get_available_profiles()
        return {
            "available_profiles": profiles,
            "profile_count": len(profiles)
        }
    
    def get_profile_modes(self, profile_name: str) -> List[str]:
        """Get available modes for a specific GDTF profile."""
        return self.gdtf_service.get_profile_modes(profile_name)
    
    def get_unmatched_fixture_types_list(self) -> List[str]:
        """Get list of unmatched fixture types for recommendations."""
        unmatched_types = []
        for fixture in self.matched_fixtures:
            if fixture.match_status != "matched":
                fixture_type = fixture.gdtf_spec or "Unknown"
                if fixture_type not in unmatched_types:
                    unmatched_types.append(fixture_type)
        return unmatched_types
    
    def _get_fixture_types(self) -> List[str]:
        """Get unique fixture types from loaded fixtures."""
        types = set()
        for fixture in self.matched_fixtures:
            fixture_type = fixture.gdtf_spec or "Unknown"
            # Remove .gdtf extension for consistent naming
            fixture_type_clean = fixture_type.replace('.gdtf', '') if fixture_type.endswith('.gdtf') else fixture_type
            types.add(fixture_type_clean)
        return sorted(list(types))
    
    def get_current_status(self) -> Dict[str, Any]:
        """Get current application status."""
        total_fixtures = len(self.matched_fixtures)
        matched_count = sum(1 for f in self.matched_fixtures if f.match_status == "matched")
        
        return {
            "file_loaded": self.current_file_path is not None or self.current_import_type is not None,
            "current_file": self.current_file_path,
            "total_fixtures": total_fixtures,
            "matched_fixtures": matched_count,
            "unmatched_fixtures": total_fixtures - matched_count,
            "available_profiles": len(self.gdtf_service.get_available_profiles()),
            "available_attributes": len(self.get_available_attributes()),
            "analysis_complete": self.analysis_results is not None
        }
    
    def get_unmatched_fixture_types(self) -> Dict[str, Dict]:
        """Get fixture types that need manual matching."""
        unmatched_fixtures = [f for f in self.matched_fixtures if f.match_status != "matched"]
        
        # Group by fixture type
        fixture_types = {}
        for fixture in unmatched_fixtures:
            fixture_type = fixture.gdtf_spec or "Unknown"
            # Remove .gdtf extension for consistent naming
            fixture_type_clean = fixture_type.replace('.gdtf', '') if fixture_type.endswith('.gdtf') else fixture_type
            
            if fixture_type_clean not in fixture_types:
                fixture_types[fixture_type_clean] = {
                    'count': 0,
                    'sample_names': [],
                    'fixtures': []
                }
            
            fixture_types[fixture_type_clean]['count'] += 1
            fixture_types[fixture_type_clean]['fixtures'].append(fixture)
            
            # Add sample names (up to 5)
            if len(fixture_types[fixture_type_clean]['sample_names']) < 5:
                fixture_types[fixture_type_clean]['sample_names'].append(fixture.name)
        
        return fixture_types 

    def get_current_fixture_type_matches(self) -> Dict[str, Dict[str, str]]:
        """Get current fixture type matches (profile and mode per fixture type)."""
        matches = {}
        
        # Get one fixture per type that is matched
        seen_types = set()
        for fixture in self.matched_fixtures:
            fixture_type = fixture.gdtf_spec or "Unknown"
            # Remove .gdtf extension for consistent naming
            fixture_type_clean = fixture_type.replace('.gdtf', '') if fixture_type.endswith('.gdtf') else fixture_type
            
            if fixture_type_clean not in seen_types and fixture.is_matched() and fixture.gdtf_profile:
                matches[fixture_type_clean] = {
                    'profile': fixture.gdtf_profile.name,
                    'mode': fixture.gdtf_mode
                }
                seen_types.add(fixture_type_clean)
        
        return matches 
    
    def get_current_master_fixture_type_matches(self) -> Dict[str, Dict[str, str]]:
        """Get current master fixture type matches (profile and mode per fixture type)."""
        matches = {}
        
        # Get one fixture per type that is matched
        seen_types = set()
        for fixture in self.master_matched_fixtures:
            fixture_type = fixture.gdtf_spec or "Unknown"
            # Remove .gdtf extension for consistent naming
            fixture_type_clean = fixture_type.replace('.gdtf', '') if fixture_type.endswith('.gdtf') else fixture_type
            
            if fixture_type_clean not in seen_types and fixture.is_matched() and fixture.gdtf_profile:
                matches[fixture_type_clean] = {
                    'profile': fixture.gdtf_profile.name,
                    'mode': fixture.gdtf_mode
                }
                seen_types.add(fixture_type_clean)
        
        return matches
    
    def get_current_remote_fixture_type_matches(self) -> Dict[str, Dict[str, str]]:
        """Get current remote fixture type matches (profile and mode per fixture type)."""
        matches = {}
        
        # Get one fixture per type that is matched
        seen_types = set()
        for fixture in self.remote_matched_fixtures:
            fixture_type = fixture.gdtf_spec or "Unknown"
            # Remove .gdtf extension for consistent naming
            fixture_type_clean = fixture_type.replace('.gdtf', '') if fixture_type.endswith('.gdtf') else fixture_type
            
            if fixture_type_clean not in seen_types and fixture.is_matched() and fixture.gdtf_profile:
                matches[fixture_type_clean] = {
                    'profile': fixture.gdtf_profile.name,
                    'mode': fixture.gdtf_mode
                }
                seen_types.add(fixture_type_clean)
        
        return matches
    
    # Master and Remote fixture management methods
    
    def load_master_mvr_file(self, file_path: str) -> Dict[str, Any]:
        """Load master fixtures from MVR file."""
        try:
            result = self._load_mvr_fixtures(file_path)
            if result["success"]:
                self.master_fixtures = result["fixtures"]
                self.master_matched_fixtures = result["fixtures"]
                self.master_file_path = file_path
                self.master_import_type = 'mvr'
                
                # Update the result to indicate master
                result["dataset_type"] = "master"
                
            return result
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def load_master_csv_fixtures(self, fixture_matches: List[FixtureMatch]) -> Dict[str, Any]:
        """Load master fixtures from CSV data."""
        try:
            # Store the fixtures
            self.master_fixtures = fixture_matches
            self.master_matched_fixtures = fixture_matches
            self.master_file_path = None
            self.master_import_type = 'csv'
            
            summary = self._get_matching_summary(fixture_matches)
            
            return {
                "success": True,
                "fixtures": fixture_matches,
                "dataset_type": "master",
                **summary
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def load_remote_mvr_file(self, file_path: str) -> Dict[str, Any]:
        """Load remote fixtures from MVR file."""
        try:
            result = self._load_mvr_fixtures(file_path)
            if result["success"]:
                self.remote_fixtures = result["fixtures"]
                self.remote_matched_fixtures = result["fixtures"]
                self.remote_file_path = file_path
                self.remote_import_type = 'mvr'
                
                # Update the result to indicate remote
                result["dataset_type"] = "remote"
                
            return result
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def load_remote_csv_fixtures(self, fixture_matches: List[FixtureMatch]) -> Dict[str, Any]:
        """Load remote fixtures from CSV data."""
        try:
            # Store the fixtures
            self.remote_fixtures = fixture_matches
            self.remote_matched_fixtures = fixture_matches
            self.remote_file_path = None
            self.remote_import_type = 'csv'
            
            summary = self._get_matching_summary(fixture_matches)
            
            return {
                "success": True,
                "fixtures": fixture_matches,
                "dataset_type": "remote",
                **summary
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_master_status(self) -> Dict[str, Any]:
        """Get current master dataset status."""
        total_fixtures = len(self.master_matched_fixtures)
        matched_count = sum(1 for f in self.master_matched_fixtures if f.match_status == "matched")
        
        return {
            "file_loaded": self.master_file_path is not None or self.master_import_type is not None,
            "current_file": self.master_file_path,
            "import_type": self.master_import_type,
            "total_fixtures": total_fixtures,
            "matched_fixtures": matched_count,
            "unmatched_fixtures": total_fixtures - matched_count,
        }
    
    def get_remote_status(self) -> Dict[str, Any]:
        """Get current remote dataset status."""
        total_fixtures = len(self.remote_matched_fixtures)
        matched_count = sum(1 for f in self.remote_matched_fixtures if f.match_status == "matched")
        
        return {
            "file_loaded": self.remote_file_path is not None or self.remote_import_type is not None,
            "current_file": self.remote_file_path,
            "import_type": self.remote_import_type,
            "total_fixtures": total_fixtures,
            "matched_fixtures": matched_count,
            "unmatched_fixtures": total_fixtures - matched_count,
        }
    
    def align_fixtures(self, alignment_config: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Align remote fixtures with master fixtures based on names and other criteria.
        
        Args:
            alignment_config: Configuration for alignment algorithm
            
        Returns:
            Dict containing alignment results
        """
        try:
            if not self.master_matched_fixtures:
                return {"success": False, "error": "No master fixtures loaded"}
            
            if not self.remote_matched_fixtures:
                return {"success": False, "error": "No remote fixtures loaded"}
            
            # Default configuration
            config = alignment_config or {
                "match_threshold": 0.8,  # Minimum similarity score for a match
                "case_sensitive": False,
                "allow_partial_matches": True,
                "prioritize_exact_matches": True
            }
            
            alignment_results = []
            remote_matched = set()  # Track which remote fixtures have been matched
            
            for master_fixture in self.master_matched_fixtures:
                best_match = None
                best_score = 0.0
                best_remote_fixture = None
                
                for i, remote_fixture in enumerate(self.remote_matched_fixtures):
                    if i in remote_matched:
                        continue  # Skip already matched remote fixtures
                    
                    # Calculate similarity score
                    score = self._calculate_fixture_similarity(
                        master_fixture, remote_fixture, config
                    )
                    
                    if score > best_score and score >= config["match_threshold"]:
                        best_score = score
                        best_remote_fixture = remote_fixture
                        best_match = i
                
                # Create alignment result
                alignment_result = {
                    "master_fixture": master_fixture,
                    "remote_fixture": best_remote_fixture,
                    "alignment_status": "matched" if best_remote_fixture else "unmatched",
                    "confidence": best_score,
                    "notes": self._generate_alignment_notes(master_fixture, best_remote_fixture, best_score, config)
                }
                
                alignment_results.append(alignment_result)
                
                # Mark remote fixture as matched
                if best_match is not None:
                    remote_matched.add(best_match)
            
            # Add unmatched remote fixtures
            for i, remote_fixture in enumerate(self.remote_matched_fixtures):
                if i not in remote_matched:
                    alignment_result = {
                        "master_fixture": None,
                        "remote_fixture": remote_fixture,
                        "alignment_status": "unmatched_remote",
                        "confidence": 0.0,
                        "notes": "No matching master fixture found"
                    }
                    alignment_results.append(alignment_result)
            
            # Store results
            self.alignment_results = alignment_results
            
            # Automatically assign sequences to aligned remote fixtures
            sequence_assignments = self._assign_sequences_to_aligned_remote_fixtures()
            
            # Calculate summary statistics
            total_alignments = len(alignment_results)
            matched_count = sum(1 for result in alignment_results if result["alignment_status"] == "matched")
            unmatched_master = sum(1 for result in alignment_results if result["alignment_status"] == "unmatched")
            unmatched_remote = sum(1 for result in alignment_results if result["alignment_status"] == "unmatched_remote")
            
            return {
                "success": True,
                "alignment_results": alignment_results,
                "total_alignments": total_alignments,
                "matched_count": matched_count,
                "unmatched_master_count": unmatched_master,
                "unmatched_remote_count": unmatched_remote,
                "alignment_percentage": (matched_count / len(self.master_matched_fixtures)) * 100 if self.master_matched_fixtures else 0,
                "sequence_assignments": sequence_assignments
            }
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return {"success": False, "error": str(e)}
    
    def _calculate_fixture_similarity(self, master_fixture, remote_fixture, config: Dict) -> float:
        """
        Calculate similarity score between master and remote fixtures.
        
        Returns:
            Float between 0.0 and 1.0 indicating similarity
        """
        if not master_fixture or not remote_fixture:
            return 0.0
        
        scores = []
        weights = []
        
        # Name similarity (highest weight)
        name_score = self._calculate_string_similarity(
            master_fixture.name, remote_fixture.name, config["case_sensitive"]
        )
        scores.append(name_score)
        weights.append(0.6)  # 60% weight on name
        
        # Fixture type similarity
        master_type = getattr(master_fixture, 'gdtf_spec', '') or ''
        remote_type = getattr(remote_fixture, 'gdtf_spec', '') or ''
        type_score = self._calculate_string_similarity(
            master_type, remote_type, config["case_sensitive"]
        )
        scores.append(type_score)
        weights.append(0.3)  # 30% weight on type
        
        # DMX mode similarity (if available)
        master_mode = getattr(master_fixture, 'gdtf_mode', '') or ''
        remote_mode = getattr(remote_fixture, 'gdtf_mode', '') or ''
        mode_score = self._calculate_string_similarity(
            master_mode, remote_mode, config["case_sensitive"]
        )
        scores.append(mode_score)
        weights.append(0.1)  # 10% weight on mode
        
        # Calculate weighted average
        total_score = sum(score * weight for score, weight in zip(scores, weights))
        
        return total_score
    
    def _calculate_string_similarity(self, str1: str, str2: str, case_sensitive: bool = False) -> float:
        """
        Calculate similarity between two strings using multiple methods.
        
        Returns:
            Float between 0.0 and 1.0
        """
        if not str1 and not str2:
            return 1.0  # Both empty
        if not str1 or not str2:
            return 0.0  # One empty
        
        # Normalize strings
        if not case_sensitive:
            str1 = str1.lower()
            str2 = str2.lower()
        
        # Exact match
        if str1 == str2:
            return 1.0
        
        # Levenshtein distance based similarity
        distance = self._levenshtein_distance(str1, str2)
        max_len = max(len(str1), len(str2))
        similarity = 1.0 - (distance / max_len)
        
        # Bonus for substring matches
        if str1 in str2 or str2 in str1:
            substring_bonus = 0.2
            similarity = min(1.0, similarity + substring_bonus)
        
        return similarity
    
    def _levenshtein_distance(self, str1: str, str2: str) -> int:
        """Calculate Levenshtein distance between two strings."""
        if len(str1) < len(str2):
            return self._levenshtein_distance(str2, str1)
        
        if len(str2) == 0:
            return len(str1)
        
        previous_row = list(range(len(str2) + 1))
        for i, c1 in enumerate(str1):
            current_row = [i + 1]
            for j, c2 in enumerate(str2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row
        
        return previous_row[-1]
    
    def _generate_alignment_notes(self, master_fixture, remote_fixture, score: float, config: Dict) -> str:
        """Generate human-readable notes about the alignment."""
        if not remote_fixture:
            return "No matching remote fixture found"
        
        notes = []
        
        if score >= 0.95:
            notes.append("Excellent match")
        elif score >= 0.8:
            notes.append("Good match")
        elif score >= config["match_threshold"]:
            notes.append("Acceptable match")
        
        # Add specific matching details
        name_similarity = self._calculate_string_similarity(
            master_fixture.name, remote_fixture.name, config["case_sensitive"]
        )
        
        if name_similarity >= 0.9:
            notes.append("names very similar")
        elif name_similarity >= 0.7:
            notes.append("names somewhat similar")
        else:
            notes.append("names different")
        
        # Check for exact name match
        master_name = master_fixture.name if not config["case_sensitive"] else master_fixture.name.lower()
        remote_name = remote_fixture.name if not config["case_sensitive"] else remote_fixture.name.lower()
        
        if master_name == remote_name:
            notes.append("exact name match")
        
        return "; ".join(notes).capitalize()
    
    def get_alignment_results(self) -> Dict[str, Any]:
        """Get current alignment results."""
        if not self.alignment_results:
            return {"success": False, "error": "No alignment performed yet"}
        
        return {
            "success": True,
            "alignment_results": self.alignment_results,
            "total_alignments": len(self.alignment_results),
            "matched_count": sum(1 for result in self.alignment_results if result["alignment_status"] == "matched"),
        }
    
    def clear_alignment_results(self):
        """Clear current alignment results."""
        self.alignment_results = None
        self.manual_alignments = {}
        self.alignment_mode = "automatic"
    
    def set_manual_alignment(self, master_fixture_id: str, remote_fixture_id: str):
        """Set a manual alignment between master and remote fixtures."""
        if remote_fixture_id:
            self.manual_alignments[master_fixture_id] = remote_fixture_id
            
            # Automatically assign sequences from master to remote fixture
            self._assign_sequences_for_manual_alignment(master_fixture_id, remote_fixture_id)
        else:
            # Remove alignment if remote_fixture_id is None
            if master_fixture_id in self.manual_alignments:
                del self.manual_alignments[master_fixture_id]
        
        self.alignment_mode = "manual"
    
    def remove_manual_alignment(self, master_fixture_id: str):
        """Remove a manual alignment for a master fixture."""
        if master_fixture_id in self.manual_alignments:
            del self.manual_alignments[master_fixture_id]
    
    def get_manual_alignments(self) -> Dict[str, str]:
        """Get current manual alignments."""
        return self.manual_alignments.copy()
    
    def get_alignment_mode(self) -> str:
        """Get current alignment mode."""
        return self.alignment_mode
    
    def generate_alignment_results_from_manual(self) -> Dict[str, Any]:
        """Generate alignment results from manual alignments."""
        try:
            if not self.master_matched_fixtures or not self.remote_matched_fixtures:
                return {"success": False, "error": "Missing master or remote fixtures"}
            
            # Create lookup dictionaries for fixtures
            master_fixtures_by_id = {f.fixture_id: f for f in self.master_matched_fixtures}
            remote_fixtures_by_id = {f.fixture_id: f for f in self.remote_matched_fixtures}
            
            alignment_results = []
            matched_remote_ids = set()
            
            # Process master fixtures
            for master_fixture in self.master_matched_fixtures:
                master_id = master_fixture.fixture_id
                remote_fixture = None
                alignment_status = "unmatched"
                confidence = 0.0
                notes = "No manual alignment set"
                
                if master_id in self.manual_alignments:
                    remote_id = self.manual_alignments[master_id]
                    if remote_id in remote_fixtures_by_id:
                        remote_fixture = remote_fixtures_by_id[remote_id]
                        alignment_status = "matched"
                        confidence = 1.0
                        notes = "Manual alignment"
                        matched_remote_ids.add(remote_id)
                    else:
                        notes = "Manual alignment target not found"
                
                alignment_result = {
                    "master_fixture": master_fixture,
                    "remote_fixture": remote_fixture,
                    "alignment_status": alignment_status,
                    "confidence": confidence,
                    "notes": notes
                }
                alignment_results.append(alignment_result)
            
            # Add unmatched remote fixtures
            for remote_fixture in self.remote_matched_fixtures:
                if remote_fixture.fixture_id not in matched_remote_ids:
                    alignment_result = {
                        "master_fixture": None,
                        "remote_fixture": remote_fixture,
                        "alignment_status": "unmatched_remote",
                        "confidence": 0.0,
                        "notes": "No manual alignment set"
                    }
                    alignment_results.append(alignment_result)
            
            # Store results
            self.alignment_results = alignment_results
            
            # Automatically assign sequences to aligned remote fixtures
            sequence_assignments = self._assign_sequences_to_aligned_remote_fixtures()
            
            # Calculate summary statistics
            total_alignments = len(alignment_results)
            matched_count = sum(1 for result in alignment_results if result["alignment_status"] == "matched")
            unmatched_master = sum(1 for result in alignment_results if result["alignment_status"] == "unmatched")
            unmatched_remote = sum(1 for result in alignment_results if result["alignment_status"] == "unmatched_remote")
            
            return {
                "success": True,
                "alignment_results": alignment_results,
                "total_alignments": total_alignments,
                "matched_count": matched_count,
                "unmatched_master_count": unmatched_master,
                "unmatched_remote_count": unmatched_remote,
                "alignment_percentage": (matched_count / len(self.master_matched_fixtures)) * 100 if self.master_matched_fixtures else 0,
                "sequence_assignments": sequence_assignments
            }
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return {"success": False, "error": str(e)}
    
    def analyze_master_fixtures(self, fixture_type_attributes: Dict[str, List[str]], output_format: str = "text", ma3_config: dict = None, sequence_start: int = 1, table_order: List[tuple] = None) -> Dict[str, Any]:
        """
        Analyze master fixtures with selected attributes.
        
        Args:
            fixture_type_attributes: Dict mapping fixture types to their selected attributes
            output_format: Output format ('text', 'csv', 'json', 'ma3_xml', 'ma3_sequences')
            ma3_config: Configuration for MA3 XML export
            sequence_start: Starting number for global sequence numbering
            table_order: Optional list of (fixture_id, attribute_name) tuples defining the order
            
        Returns:
            Dict containing analysis results
        """
        try:
            if not self.master_matched_fixtures:
                return {"success": False, "error": "No master fixtures loaded"}
            
            # Use the existing analysis method but with master fixtures
            original_fixtures = self.matched_fixtures
            self.matched_fixtures = self.master_matched_fixtures
            
            result = self.analyze_fixtures_by_type(fixture_type_attributes, output_format, ma3_config, sequence_start, table_order)
            
            # Restore original fixtures
            self.matched_fixtures = original_fixtures
            
            if result["success"]:
                result["dataset_type"] = "master"
            
            return result
            
        except Exception as e:
            # Restore original fixtures in case of error
            if 'original_fixtures' in locals():
                self.matched_fixtures = original_fixtures
            import traceback
            traceback.print_exc()
            return {"success": False, "error": str(e)}
    
    def analyze_remote_fixtures(self, fixture_type_attributes: Dict[str, List[str]], output_format: str = "text", ma3_config: dict = None, sequence_start: int = 1) -> Dict[str, Any]:
        """
        Analyze remote fixtures with selected attributes.
        Note: Remote fixtures will not get sequence numbers assigned initially - sequences are blank until assigned via routing.
        
        Args:
            fixture_type_attributes: Dict mapping fixture types to their selected attributes
            output_format: Output format ('text', 'csv', 'json', 'ma3_xml')
            ma3_config: Configuration for MA3 XML export
            sequence_start: Starting number for global sequence numbering (not used for remote fixtures)
            
        Returns:
            Dict containing analysis results
        """
        try:
            if not self.remote_matched_fixtures:
                return {"success": False, "error": "No remote fixtures loaded"}
            
            # Use MVR service to analyze remote fixtures without sequence assignment
            analysis_results = self.mvr_service.analyze_fixtures_by_type_without_sequences(
                self.remote_matched_fixtures, 
                fixture_type_attributes, 
                output_format, 
                ma3_config
            )
            
            # Update the remote matched fixtures with the results
            self.remote_matched_fixtures = analysis_results.fixtures
            
            # Return the same structure as master analysis for consistency
            result = {
                "success": True,
                "analysis_results": analysis_results,  # Keep the full results object
                "summary": analysis_results.summary,
                "export_data": analysis_results.export_data,
                "dataset_type": "remote",
                # Add summary fields at top level for backward compatibility
                "total_fixtures": analysis_results.summary.get("total_fixtures", 0),
                "matched_fixtures": analysis_results.summary.get("matched_fixtures", 0)
            }
            
            return result
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return {"success": False, "error": str(e)}
    
    def update_master_fixture_matches(self, fixture_type_matches: Dict[str, Dict[str, str]]) -> Dict[str, Any]:
        """Update master fixture type matches (profile and mode per fixture type)."""
        try:
            if not self.master_matched_fixtures:
                return {"success": False, "error": "No master fixtures loaded"}
            
            # Use the existing update method but with master fixtures
            original_fixtures = self.matched_fixtures
            self.matched_fixtures = self.master_matched_fixtures
            
            result = self.update_fixture_matches(fixture_type_matches)
            
            # Update master fixtures
            self.master_matched_fixtures = self.matched_fixtures
            
            # Restore original fixtures
            self.matched_fixtures = original_fixtures
            
            if result["success"]:
                result["dataset_type"] = "master"
            
            return result
            
        except Exception as e:
            # Restore original fixtures in case of error
            if 'original_fixtures' in locals():
                self.matched_fixtures = original_fixtures
            return {"success": False, "error": str(e)}
    
    def update_remote_fixture_matches(self, fixture_type_matches: Dict[str, Dict[str, str]]) -> Dict[str, Any]:
        """Update remote fixture type matches (profile and mode per fixture type)."""
        try:
            if not self.remote_matched_fixtures:
                return {"success": False, "error": "No remote fixtures loaded"}
            
            # Use the existing update method but with remote fixtures
            original_fixtures = self.matched_fixtures
            self.matched_fixtures = self.remote_matched_fixtures
            
            result = self.update_fixture_matches(fixture_type_matches)
            
            # Update remote fixtures
            self.remote_matched_fixtures = self.matched_fixtures
            
            # Restore original fixtures
            self.matched_fixtures = original_fixtures
            
            if result["success"]:
                result["dataset_type"] = "remote"
            
            return result
            
        except Exception as e:
            # Restore original fixtures in case of error
            if 'original_fixtures' in locals():
                self.matched_fixtures = original_fixtures
            return {"success": False, "error": str(e)}
    
    def get_master_fixture_info(self) -> Dict[str, Dict]:
        """Get master fixture types information for GDTF matching dialog."""
        if not self.master_matched_fixtures:
            return {}
        
        # Use the existing method but with master fixtures
        original_fixtures = self.matched_fixtures
        self.matched_fixtures = self.master_matched_fixtures
        
        # Get all fixture types (both matched and unmatched)
        fixture_types = {}
        for fixture in self.master_matched_fixtures:
            fixture_type = fixture.gdtf_spec or "Unknown"
            fixture_type_clean = fixture_type.replace('.gdtf', '') if fixture_type.endswith('.gdtf') else fixture_type
            
            if fixture_type_clean not in fixture_types:
                fixture_types[fixture_type_clean] = {
                    'count': 0,
                    'matched_count': 0,
                    'sample_names': [],
                    'fixtures': [],
                    'current_match': None
                }
            
            fixture_types[fixture_type_clean]['count'] += 1
            fixture_types[fixture_type_clean]['fixtures'].append(fixture)
            
            if fixture.is_matched():
                fixture_types[fixture_type_clean]['matched_count'] += 1
                if not fixture_types[fixture_type_clean]['current_match'] and fixture.gdtf_profile:
                    fixture_types[fixture_type_clean]['current_match'] = {
                        'profile': fixture.gdtf_profile.name,
                        'mode': fixture.gdtf_mode
                    }
            
            # Add sample names (up to 5)
            if len(fixture_types[fixture_type_clean]['sample_names']) < 5:
                fixture_types[fixture_type_clean]['sample_names'].append(fixture.name)
        
        # Restore original fixtures
        self.matched_fixtures = original_fixtures
        
        return fixture_types
    
    def get_remote_fixture_info(self) -> Dict[str, Dict]:
        """Get remote fixture types information for GDTF matching dialog."""
        if not self.remote_matched_fixtures:
            return {}
        
        # Use the existing method but with remote fixtures
        original_fixtures = self.matched_fixtures
        self.matched_fixtures = self.remote_matched_fixtures
        
        # Get all fixture types (both matched and unmatched)
        fixture_types = {}
        for fixture in self.remote_matched_fixtures:
            fixture_type = fixture.gdtf_spec or "Unknown"
            fixture_type_clean = fixture_type.replace('.gdtf', '') if fixture_type.endswith('.gdtf') else fixture_type
            
            if fixture_type_clean not in fixture_types:
                fixture_types[fixture_type_clean] = {
                    'count': 0,
                    'matched_count': 0,
                    'sample_names': [],
                    'fixtures': [],
                    'current_match': None
                }
            
            fixture_types[fixture_type_clean]['count'] += 1
            fixture_types[fixture_type_clean]['fixtures'].append(fixture)
            
            if fixture.is_matched():
                fixture_types[fixture_type_clean]['matched_count'] += 1
                if not fixture_types[fixture_type_clean]['current_match'] and fixture.gdtf_profile:
                    fixture_types[fixture_type_clean]['current_match'] = {
                        'profile': fixture.gdtf_profile.name,
                        'mode': fixture.gdtf_mode
                    }
            
            # Add sample names (up to 5)
            if len(fixture_types[fixture_type_clean]['sample_names']) < 5:
                fixture_types[fixture_type_clean]['sample_names'].append(fixture.name)
        
        # Restore original fixtures
        self.matched_fixtures = original_fixtures
        
        return fixture_types

    def _assign_sequences_to_aligned_remote_fixtures(self):
        """
        Automatically assign sequences to remote fixtures that are aligned with master fixtures.
        This ensures remote fixtures get proper sequence numbers for export.
        """
        if not self.alignment_results:
            return
        
        sequence_assignments = 0
        
        for alignment_result in self.alignment_results:
            if alignment_result["alignment_status"] == "matched":
                master_fixture = alignment_result["master_fixture"]
                remote_fixture = alignment_result["remote_fixture"]
                
                # Copy sequences from master to remote fixture
                if hasattr(master_fixture, 'attribute_sequences') and master_fixture.attribute_sequences:
                    if not hasattr(remote_fixture, 'attribute_sequences') or remote_fixture.attribute_sequences is None:
                        remote_fixture.attribute_sequences = {}
                    
                    # Copy sequences for matching attributes
                    for attr_name, sequence_num in master_fixture.attribute_sequences.items():
                        if attr_name in remote_fixture.attribute_offsets:
                            remote_fixture.attribute_sequences[attr_name] = sequence_num
                            sequence_assignments += 1
        
        return sequence_assignments

    def _assign_sequences_for_manual_alignment(self, master_fixture_id: str, remote_fixture_id: str):
        """
        Assign sequences from a master fixture to a remote fixture for manual alignment.
        """
        try:
            # Find the master fixture
            master_fixture = None
            for fixture in self.master_matched_fixtures:
                if str(fixture.fixture_id) == str(master_fixture_id):
                    master_fixture = fixture
                    break
            
            # Find the remote fixture
            remote_fixture = None
            for fixture in self.remote_matched_fixtures:
                if str(fixture.fixture_id) == str(remote_fixture_id):
                    remote_fixture = fixture
                    break
            
            # Assign sequences if both fixtures found
            if master_fixture and remote_fixture:
                if hasattr(master_fixture, 'attribute_sequences') and master_fixture.attribute_sequences:
                    if not hasattr(remote_fixture, 'attribute_sequences') or remote_fixture.attribute_sequences is None:
                        remote_fixture.attribute_sequences = {}
                    
                    # Copy sequences for matching attributes
                    for attr_name, sequence_num in master_fixture.attribute_sequences.items():
                        if attr_name in remote_fixture.attribute_offsets:
                            remote_fixture.attribute_sequences[attr_name] = sequence_num
                            
        except Exception as e:
            # Log error but don't fail the alignment
            print(f"Error assigning sequences for manual alignment: {e}")

    def export_remote_fixtures_direct(self, fixture_type_attributes: Dict[str, List[str]], output_format: str, file_path: str, ma3_config: dict = None, table_order: List[tuple] = None) -> Dict[str, Any]:
        """
        Export remote fixtures directly without re-analyzing them.
        This preserves any sequences that were assigned during alignment.
        
        Args:
            fixture_type_attributes: Dict mapping fixture types to their selected attributes
            output_format: Output format ('text', 'csv', 'json', 'ma3_xml', 'ma3_sequences')
            file_path: Path to save the export file
            ma3_config: Configuration for MA3 XML export
            table_order: Optional list of (fixture_id, attribute_name) tuples defining the order
            
        Returns:
            Dict containing export results
        """
        try:
            if not self.remote_matched_fixtures:
                return {"success": False, "error": "No remote fixtures loaded"}
            
            # Create analysis results directly from existing fixtures (preserves sequences)
            from models.data_models import AnalysisResults
            
            # Collect all selected attributes across all fixture types
            all_selected_attributes = []
            for attrs in fixture_type_attributes.values():
                all_selected_attributes.extend(attrs)
            all_selected_attributes = sorted(list(set(all_selected_attributes)))
            
            # Generate summary from existing fixtures
            summary = self.mvr_service._generate_summary_by_type(self.remote_matched_fixtures, fixture_type_attributes)
            
            # Generate export data from existing fixtures
            export_data = self.mvr_service._generate_export_data_by_type(self.remote_matched_fixtures, fixture_type_attributes, output_format, ma3_config, table_order)
            
            # Create analysis results object
            analysis_results = AnalysisResults(
                fixtures=self.remote_matched_fixtures,
                summary=summary,
                selected_attributes=all_selected_attributes,
                output_format=output_format,
                export_data=export_data,
                validation_info={},
                table_order=table_order,
                fixture_type_attributes=fixture_type_attributes
            )
            
            # Save to file
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(export_data)
            except Exception as e:
                return {"success": False, "error": f"Error saving file: {e}"}
            
            return {
                "success": True,
                "file_path": file_path,
                "export_data": export_data,
                "summary": summary
            }
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return {"success": False, "error": str(e)}

    def export_sequences_xml(self, fixtures: List[FixtureMatch], fixture_type_attributes: Dict[str, List[str]], file_path: str, table_order: List[tuple] = None) -> Dict[str, Any]:
        """
        Export MA3 sequences XML for all fixtures and their attributes with values set to 100.
        
        Args:
            fixtures: List of FixtureMatch objects with sequence numbers assigned
            fixture_type_attributes: Dict mapping fixture types to their selected attributes
            file_path: Path to save the sequences XML file
            table_order: Optional list of (fixture_id, attribute_name) tuples defining the order
            
        Returns:
            Dict containing export results
        """
        try:
            if not fixtures:
                return {"success": False, "error": "No fixtures provided"}
            
            if not fixture_type_attributes:
                return {"success": False, "error": "No fixture type attributes provided"}
            
            # Export sequences using the service
            export_data = self.mvr_service._export_ma3_sequences_xml_by_type(fixtures, fixture_type_attributes, table_order)
            
            # Save to file
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(export_data)
            except Exception as e:
                return {"success": False, "error": f"Error saving file: {e}"}
            
            # Count sequences generated
            sequence_count = 0
            for fixture in fixtures:
                if fixture.is_matched():
                    fixture_type = fixture.gdtf_spec or "Unknown"
                    fixture_type_clean = fixture_type.replace('.gdtf', '') if fixture_type.endswith('.gdtf') else fixture_type
                    selected_attributes = fixture_type_attributes.get(fixture_type_clean, [])
                    
                    for attr_name in selected_attributes:
                        if attr_name in fixture.attribute_offsets and fixture.get_sequence_for_attribute(attr_name):
                            sequence_count += 1
            
            return {
                "success": True,
                "file_path": file_path,
                "export_data": export_data,
                "sequence_count": sequence_count,
                "message": f"Successfully exported {sequence_count} sequences to {file_path}"
            }
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return {"success": False, "error": str(e)}