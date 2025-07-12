"""
Controller for MVR File Analyzer.
Handles business logic and coordinates between services.
"""

import traceback
from typing import Dict, List, Any, Optional
from pathlib import Path

from services.mvr_service import MVRService
from services.gdtf_service import GDTFService
from models.data_models import FixtureMatch, AnalysisResults


class MVRController:
    """
    Controller for the MVR File Analyzer.
    Coordinates between UI and services.
    """
    
    def __init__(self):
        self.mvr_service = MVRService()
        self.gdtf_service = GDTFService()
        self.loaded_fixtures = []
        self.matched_fixtures = []
        self.current_file_path = None
        self.analysis_results = None
    
    def load_mvr_file(self, file_path: str) -> Dict[str, Any]:
        """
        Load an MVR file and return status information.
        
        Returns:
            Dict containing load status and fixture information
        """
        try:
            self.current_file_path = file_path
            
            # Load MVR file
            self.loaded_fixtures = self.mvr_service.load_mvr_file(file_path)
            
            # Load GDTF profiles from the MVR
            internal_profiles = self.gdtf_service.load_profiles_from_mvr(file_path)
            
            # Initial matching attempt
            self.matched_fixtures = self.gdtf_service.match_fixtures(
                self.loaded_fixtures, internal_profiles
            )
            
            # Calculate match statistics
            total_fixtures = len(self.matched_fixtures)
            matched_count = sum(1 for f in self.matched_fixtures if f.match_status == "matched")
            unmatched_count = total_fixtures - matched_count
            
            return {
                "success": True,
                "total_fixtures": total_fixtures,
                "matched_fixtures": matched_count,
                "unmatched_fixtures": unmatched_count,
                "gdtf_profiles_loaded": len(internal_profiles),
                "fixture_types": self._get_fixture_types(),
                "unmatched_fixture_data": [f for f in self.matched_fixtures if f.match_status != "matched"]
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
    
    def analyze_fixtures_by_type(self, fixture_type_attributes: Dict[str, List[str]], output_format: str = "text", ma3_config: dict = None) -> Dict[str, Any]:
        """
        Analyze fixtures with per-fixture-type attributes.
        
        Args:
            fixture_type_attributes: Dict mapping fixture_type -> list of attribute names
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
            
            # Validate that we have some attributes to analyze
            total_attributes = sum(len(attrs) for attrs in fixture_type_attributes.values())
            if total_attributes == 0:
                return {
                    "success": False,
                    "error": "No attributes selected for analysis"
                }
            
            # Run analysis per fixture type
            results = self.mvr_service.analyze_fixtures_by_type(
                self.matched_fixtures, fixture_type_attributes, output_format, ma3_config
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
        return {
            "file_loaded": self.current_file_path is not None,
            "current_file": self.current_file_path,
            "total_fixtures": len(self.matched_fixtures),
            "matched_fixtures": sum(1 for f in self.matched_fixtures if f.match_status == "matched"),
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