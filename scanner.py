"""
Directory scanning service.

Efficiently discovers files for processing with support for:
- Recursive scanning
- Extension filtering
- Large directories (10,000+ files)
- Generator-based iteration (memory efficient)
"""

import os
import time
from pathlib import Path
from typing import List, Set, Optional, Generator
from models import ScanResult


class DirectoryScannerService:
    """
    High-performance directory scanner.
    
    Uses generators for memory efficiency with large file sets.
    """
    
    # Common video extensions
    DEFAULT_VIDEO_EXTENSIONS = {
        '.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.webm',
        '.m4v', '.mpg', '.mpeg', '.3gp', '.ogv', '.ts', '.m2ts'
    }
    
    # Common audio extensions
    DEFAULT_AUDIO_EXTENSIONS = {
        '.mp3', '.flac', '.wav', '.m4a', '.aac', '.ogg', '.wma',
        '.opus', '.ape', '.alac'
    }
    
    # Common document extensions
    DEFAULT_DOC_EXTENSIONS = {
        '.pdf', '.doc', '.docx', '.txt', '.rtf', '.odt'
    }
    
    def __init__(self, 
                 recursive: bool = False,
                 extensions: Optional[Set[str]] = None,
                 max_depth: int = 5):
        """
        Initialize scanner.
        
        Args:
            recursive: Scan subdirectories
            extensions: Allowed extensions (None = all files)
            max_depth: Maximum recursion depth
        """
        self.recursive = recursive
        self.extensions = extensions
        self.max_depth = max_depth
    
    def scan_directory(self, directory: Path) -> ScanResult:
        """
        Scan directory and return all matching files.
        
        Args:
            directory: Path to scan
        
        Returns:
            ScanResult with found files and statistics
        """
        if not directory.exists():
            return ScanResult(
                files_found=[],
                files_processed=0,
                files_skipped=0,
                errors=[f"Directory not found: {directory}"]
            )
        
        if not directory.is_dir():
            return ScanResult(
                files_found=[],
                files_processed=0,
                files_skipped=0,
                errors=[f"Not a directory: {directory}"]
            )
        
        start_time = time.time()
        files_found = []
        files_skipped = 0
        errors = []
        
        try:
            # Use generator for memory efficiency
            for filepath in self._iterate_files(directory, current_depth=0):
                # Check extension filter
                if self.extensions:
                    if filepath.suffix.lower() not in self.extensions:
                        files_skipped += 1
                        continue
                
                files_found.append(filepath)
        
        except PermissionError as e:
            errors.append(f"Permission denied: {e}")
        except Exception as e:
            errors.append(f"Scan error: {e}")
        
        scan_time_ms = (time.time() - start_time) * 1000
        
        return ScanResult(
            files_found=files_found,
            files_processed=len(files_found),
            files_skipped=files_skipped,
            errors=errors,
            scan_time_ms=scan_time_ms
        )
    
    def _iterate_files(self, directory: Path, current_depth: int) -> Generator[Path, None, None]:
        """
        Generator that yields file paths.
        
        Memory efficient for large directories.
        """
        try:
            # Get directory entries
            entries = list(directory.iterdir())
        except PermissionError:
            return
        
        # Process files first
        for entry in entries:
            try:
                if entry.is_file():
                    # Skip hidden files (Unix)
                    if entry.name.startswith('.'):
                        continue
                    
                    # Skip staging files from previous operations
                    if entry.name.startswith('.rename_staging_'):
                        continue
                    
                    yield entry
            
            except (PermissionError, OSError):
                continue
        
        # Recurse into subdirectories if enabled
        if self.recursive and current_depth < self.max_depth:
            for entry in entries:
                try:
                    if entry.is_dir():
                        # Skip hidden directories
                        if entry.name.startswith('.'):
                            continue
                        
                        # Recurse
                        yield from self._iterate_files(entry, current_depth + 1)
                
                except (PermissionError, OSError):
                    continue
    
    def count_files_fast(self, directory: Path) -> int:
        """
        Fast file count without loading all paths into memory.
        
        Useful for progress bar initialization.
        """
        count = 0
        
        try:
            for _ in self._iterate_files(directory, current_depth=0):
                count += 1
        except Exception:
            pass
        
        return count
    
    @classmethod
    def get_preset_extensions(cls, preset: str) -> Set[str]:
        """
        Get predefined extension sets.
        
        Args:
            preset: 'video', 'audio', 'documents', or 'all'
        
        Returns:
            Set of extensions
        """
        presets = {
            'video': cls.DEFAULT_VIDEO_EXTENSIONS,
            'audio': cls.DEFAULT_AUDIO_EXTENSIONS,
            'documents': cls.DEFAULT_DOC_EXTENSIONS,
            'all': None  # No filter
        }
        
        return presets.get(preset.lower())
    
    def set_extensions_from_preset(self, preset: str) -> None:
        """Set extension filter from preset."""
        self.extensions = self.get_preset_extensions(preset)


class FileFilterService:
    """
    Additional filtering logic for scanned files.
    """
    
    @staticmethod
    def filter_by_size(files: List[Path], 
                      min_size: Optional[int] = None,
                      max_size: Optional[int] = None) -> List[Path]:
        """
        Filter files by size in bytes.
        
        Args:
            files: List of file paths
            min_size: Minimum size (bytes)
            max_size: Maximum size (bytes)
        
        Returns:
            Filtered file list
        """
        filtered = []
        
        for filepath in files:
            try:
                size = filepath.stat().st_size
                
                if min_size and size < min_size:
                    continue
                
                if max_size and size > max_size:
                    continue
                
                filtered.append(filepath)
            
            except (OSError, PermissionError):
                continue
        
        return filtered
    
    @staticmethod
    def filter_by_pattern(files: List[Path], pattern: str) -> List[Path]:
        """
        Filter files matching glob pattern.
        
        Args:
            files: List of file paths
            pattern: Glob pattern (e.g., "*Episode*")
        
        Returns:
            Matching files
        """
        import fnmatch
        
        return [f for f in files if fnmatch.fnmatch(f.name, pattern)]
    
    @staticmethod
    def exclude_pattern(files: List[Path], pattern: str) -> List[Path]:
        """
        Exclude files matching pattern.
        
        Args:
            files: List of file paths
            pattern: Glob pattern to exclude
        
        Returns:
            Non-matching files
        """
        import fnmatch
        
        return [f for f in files if not fnmatch.fnmatch(f.name, pattern)]
