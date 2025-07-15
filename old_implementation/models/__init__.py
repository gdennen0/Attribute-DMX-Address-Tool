"""
Models package for MVR File Analyzer.
Contains data models and structures.
"""

from .data_models import (
    GDTFMode, GDTFProfile, FixtureMatch, AnalysisResults, 
    FixtureData, MatchSummary
)

__all__ = [
    'GDTFMode', 'GDTFProfile', 'FixtureMatch', 'AnalysisResults',
    'FixtureData', 'MatchSummary'
] 