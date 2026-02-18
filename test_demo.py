"""
Test & Demonstration Script

Validates core functionality without requiring GUI.
"""

import sys
from pathlib import Path
from typing import List

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

from parser import EpisodeParser
from sanitizer import FilenameSanitizer
from sorter import NaturalSorter, ConflictDetector
from validator import SafeFormatter, FilenameValidator
from models import EpisodeMetadata


def test_parser():
    """Test episode number extraction."""
    print("\n" + "="*70)
    print("TESTING: Episode Parser")
    print("="*70)
    
    parser = EpisodeParser()
    
    test_cases = [
        "S01E05 - The Great Episode.mp4",
        "Breaking Bad 2x03 - Title [1080p].mkv",
        "Episode 12 - Final Battle.avi",
        "[15] Some Anime Episode.mkv",
        "Documentary - Part 3.mp4",
        "05 - Leading Number.mp4",
        "Title with 1080p and 2023 but ep 07.mp4",
        "No numbers here just title.mp4"
    ]
    
    for filename in test_cases:
        filepath = Path(filename)
        meta = parser.parse(filepath)
        
        print(f"\nFile: {filename}")
        print(f"  Number: {meta.extracted_number}")
        print(f"  Confidence: {meta.confidence:.2f}")
        print(f"  Method: {meta.extraction_method}")
        if meta.season:
            print(f"  Season: {meta.season}, Episode: {meta.episode}")


def test_sanitizer():
    """Test filename sanitization."""
    print("\n" + "="*70)
    print("TESTING: Filename Sanitizer")
    print("="*70)
    
    sanitizer = FilenameSanitizer()
    
    test_cases = [
        "Movie.2023.1080p.WEB-DL.x264.AAC-RARBG",
        "Series S01E05 [1080p] [h265] [HEVC]",
        "Documentary.4K.HDR.DTS-HD.MA.5.1",
        "Video_with_underscores_and.dots",
        "Title with [YTS.MX] watermark",
        "Content-from-www.example.com",
    ]
    
    for filename in test_cases:
        cleaned = sanitizer.sanitize(filename)
        print(f"\nOriginal: {filename}")
        print(f"Cleaned:  {cleaned}")


def test_formatter():
    """Test safe formatting."""
    print("\n" + "="*70)
    print("TESTING: Safe Formatter")
    print("="*70)
    
    formatter = SafeFormatter()
    
    # Create test metadata
    meta = EpisodeMetadata(
        original_name="test.mp4",
        file_path=Path("test.mp4"),
        season=1,
        episode=5,
        extracted_number=5,
        confidence=0.9,
        cleaned_title="The Great Episode",
        extension=".mp4",
        extraction_method="test"
    )
    
    formats = [
        "{number}. {title}",
        "{number:02d}. {title}",
        "S{season}E{episode}. {title}",
        "[{number:03d}] {title}",
        "{title} - Episode {number}"
    ]
    
    for format_str in formats:
        result = formatter.format_safe(format_str, meta)
        print(f"\nFormat: {format_str}")
        print(f"Result: {result}")
    
    # Test invalid format
    print("\nTesting invalid format:")
    invalid = "{number}.{__dict__}"
    validation = formatter.validate_format_string(invalid)
    print(f"Format: {invalid}")
    print(f"Valid: {validation.is_valid}")
    print(f"Error: {validation.error_message}")


def test_natural_sort():
    """Test natural sorting."""
    print("\n" + "="*70)
    print("TESTING: Natural Sort")
    print("="*70)
    
    filenames = [
        "Episode 2.mp4",
        "Episode 10.mp4",
        "Episode 1.mp4",
        "Episode 20.mp4",
        "S01E05.mp4",
        "S01E15.mp4",
        "S01E3.mp4"
    ]
    
    # Create metadata
    parser = EpisodeParser()
    metadata_list = []
    for fname in filenames:
        meta = parser.parse(Path(fname))
        metadata_list.append(meta)
    
    # Sort
    sorted_meta = NaturalSorter.sort_metadata(metadata_list)
    
    print("\nOriginal order:")
    for fname in filenames:
        print(f"  {fname}")
    
    print("\nSorted order:")
    for meta in sorted_meta:
        print(f"  {meta.original_name} (number: {meta.extracted_number})")


def test_conflict_detection():
    """Test conflict detection."""
    print("\n" + "="*70)
    print("TESTING: Conflict Detection")
    print("="*70)
    
    # Create test metadata with duplicates
    parser = EpisodeParser()
    
    filenames = [
        "Episode 1 - First.mp4",
        "Episode 1 - Duplicate.mp4",
        "Episode 2.mp4",
        "Episode 4.mp4",  # Gap at 3
        "Episode 5.mp4"
    ]
    
    metadata_list = []
    for fname in filenames:
        meta = parser.parse(Path(fname))
        metadata_list.append(meta)
    
    # Detect gaps
    gaps = ConflictDetector.detect_number_gaps(metadata_list)
    print(f"\nNumber gaps detected: {gaps}")
    
    # Detect duplicates
    duplicates = ConflictDetector.detect_duplicate_numbers(metadata_list)
    print(f"\nDuplicate numbers:")
    for num, metas in duplicates.items():
        print(f"  Number {num}: {len(metas)} files")
        for meta in metas:
            print(f"    - {meta.original_name}")


def test_validation():
    """Test filename validation."""
    print("\n" + "="*70)
    print("TESTING: Filename Validation")
    print("="*70)
    
    validator = FilenameValidator()
    
    test_cases = [
        ("valid_filename.mp4", "/home/user/videos"),
        ("file:with:colons.mp4", "/home/user/videos"),  # Invalid on Windows
        ("CON.mp4", "/home/user/videos"),  # Reserved Windows name
        ("a" * 250 + ".mp4", "/home/user/videos"),  # Too long
        ("normal_file.mp4", "/home/user/videos")
    ]
    
    for filename, directory in test_cases:
        result = validator.validate_filename(filename, directory)
        print(f"\nFilename: {filename}")
        print(f"  Valid: {result.is_valid}")
        if not result.is_valid:
            print(f"  Error: {result.error_message}")
        if result.warnings:
            print(f"  Warnings: {result.warnings}")


def run_all_tests():
    """Run all tests."""
    print("\n" + "#"*70)
    print("# PLAYLIST RENAMER PRO - CORE FUNCTIONALITY TESTS")
    print("#"*70)
    
    test_parser()
    test_sanitizer()
    test_formatter()
    test_natural_sort()
    test_conflict_detection()
    test_validation()
    
    print("\n" + "="*70)
    print("ALL TESTS COMPLETED")
    print("="*70)
    print("\nNote: These tests validate core logic without GUI.")
    print("To test the full application, run: python main.py")


if __name__ == '__main__':
    run_all_tests()
