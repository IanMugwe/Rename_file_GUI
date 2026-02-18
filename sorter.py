"""
Sorting and ordering logic for rename operations.

Implements natural sort (human-friendly number ordering)
and conflict detection algorithms.
"""

import re
from typing import List, Dict, Set, Tuple
from pathlib import Path
from models import EpisodeMetadata, RenameOperation


class NaturalSorter:
    """
    Natural sorting algorithm.
    
    Sorts strings in human-friendly order:
    - "Item 2" comes before "Item 10"
    - "S01E02" comes before "S01E10"
    """
    
    @staticmethod
    def natural_sort_key(text: str) -> List:
        """
        Generate sort key for natural ordering.
        
        Splits text into alternating strings and integers:
        "Episode 2" → ["Episode ", 2]
        "Episode 10" → ["Episode ", 10]
        """
        def convert(text_part):
            return int(text_part) if text_part.isdigit() else text_part.lower()
        
        return [convert(part) for part in re.split(r'(\d+)', text)]
    
    @classmethod
    def sort_metadata(cls, metadata_list: List[EpisodeMetadata]) -> List[EpisodeMetadata]:
        """
        Sort metadata by extracted number, falling back to natural sort.
        
        Priority:
        1. Sort by extracted_number if present
        2. Fall back to natural sort of original filename
        """
        def sort_key(meta: EpisodeMetadata):
            # Primary: extracted number (None sorts to end)
            number = meta.extracted_number if meta.extracted_number is not None else 999999
            
            # Secondary: natural sort of original name
            natural_key = cls.natural_sort_key(meta.original_name)
            
            return (number, natural_key)
        
        return sorted(metadata_list, key=sort_key)
    
    @classmethod
    def sort_by_confidence_then_number(cls, metadata_list: List[EpisodeMetadata]) -> List[EpisodeMetadata]:
        """
        Alternative sort: by confidence first, then number.
        
        Useful for quality-checking extraction results.
        """
        def sort_key(meta: EpisodeMetadata):
            # Primary: confidence (descending)
            confidence = -meta.confidence
            
            # Secondary: number
            number = meta.extracted_number if meta.extracted_number is not None else 999999
            
            return (confidence, number)
        
        return sorted(metadata_list, key=sort_key)


class ConflictDetector:
    """
    Detects naming conflicts before rename operations.
    
    Handles:
    - Duplicate target names
    - Case-only changes (Windows)
    - Existing files that would be overwritten
    - Circular renames
    """
    
    @staticmethod
    def detect_duplicate_targets(operations: List[RenameOperation]) -> Dict[str, List[RenameOperation]]:
        """
        Find operations that would produce duplicate filenames.
        
        Returns:
            Dict mapping target_name → list of operations producing that name
        """
        target_map: Dict[str, List[RenameOperation]] = {}
        
        for op in operations:
            target_lower = op.target_name.lower()
            if target_lower not in target_map:
                target_map[target_lower] = []
            target_map[target_lower].append(op)
        
        # Return only duplicates
        return {name: ops for name, ops in target_map.items() if len(ops) > 1}
    
    @staticmethod
    def detect_target_collisions(operations: List[RenameOperation]) -> List[Tuple[RenameOperation, Path]]:
        """
        Find operations where target file already exists.
        
        Returns:
            List of (operation, existing_file_path) tuples
        """
        collisions = []
        
        # Get set of all source paths
        source_paths = {op.original_path for op in operations}
        
        for op in operations:
            # Check if target exists and is NOT one of our source files
            if op.target_path.exists() and op.target_path not in source_paths:
                collisions.append((op, op.target_path))
        
        return collisions
    
    @staticmethod
    def detect_case_only_changes(operations: List[RenameOperation]) -> List[RenameOperation]:
        """
        Find operations that only change filename case.
        
        These are problematic on case-insensitive filesystems (Windows, macOS default).
        """
        return [op for op in operations if op.is_case_only_change()]
    
    @staticmethod
    def detect_circular_renames(operations: List[RenameOperation]) -> List[List[RenameOperation]]:
        """
        Detect circular rename chains.
        
        Example: A→B, B→C, C→A creates a cycle
        
        Returns:
            List of cycles, each cycle is a list of operations
        """
        # Build adjacency map: source → target
        rename_map = {op.original_path: op.target_path for op in operations}
        op_map = {op.original_path: op for op in operations}
        
        cycles = []
        visited = set()
        
        def find_cycle(start: Path, current: Path, path: List[Path]) -> bool:
            """DFS to detect cycles."""
            if current == start and len(path) > 1:
                # Found cycle
                cycle_ops = [op_map[p] for p in path if p in op_map]
                if cycle_ops:
                    cycles.append(cycle_ops)
                return True
            
            if current in visited:
                return False
            
            visited.add(current)
            
            # Follow rename chain
            if current in rename_map:
                next_path = rename_map[current]
                return find_cycle(start, next_path, path + [current])
            
            return False
        
        # Check each operation as potential cycle start
        for op in operations:
            if op.original_path not in visited:
                find_cycle(op.original_path, op.original_path, [])
        
        return cycles
    
    @staticmethod
    def detect_number_gaps(metadata_list: List[EpisodeMetadata]) -> List[int]:
        """
        Detect gaps in episode numbering.
        
        Returns:
            List of missing episode numbers
        """
        numbers = [m.extracted_number for m in metadata_list 
                  if m.extracted_number is not None]
        
        if not numbers:
            return []
        
        numbers_set = set(numbers)
        min_num = min(numbers)
        max_num = max(numbers)
        
        gaps = []
        for i in range(min_num, max_num + 1):
            if i not in numbers_set:
                gaps.append(i)
        
        return gaps
    
    @staticmethod
    def detect_duplicate_numbers(metadata_list: List[EpisodeMetadata]) -> Dict[int, List[EpisodeMetadata]]:
        """
        Detect files with same episode number.
        
        Returns:
            Dict mapping episode_number → list of metadata with that number
        """
        number_map: Dict[int, List[EpisodeMetadata]] = {}
        
        for meta in metadata_list:
            if meta.extracted_number is not None:
                num = meta.extracted_number
                if num not in number_map:
                    number_map[num] = []
                number_map[num].append(meta)
        
        # Return only duplicates
        return {num: metas for num, metas in number_map.items() if len(metas) > 1}


class NumberingAdjuster:
    """
    Adjust episode numbering to fix gaps or start from specific number.
    """
    
    @staticmethod
    def renumber_sequentially(metadata_list: List[EpisodeMetadata], 
                             start: int = 1) -> List[EpisodeMetadata]:
        """
        Renumber episodes sequentially starting from 'start'.
        
        Creates new metadata objects with adjusted numbers.
        Preserves original ordering.
        """
        renumbered = []
        
        for i, meta in enumerate(metadata_list):
            # Create new metadata with adjusted number
            new_meta = EpisodeMetadata(
                original_name=meta.original_name,
                file_path=meta.file_path,
                season=meta.season,
                episode=meta.episode,
                extracted_number=start + i,
                confidence=meta.confidence,
                cleaned_title=meta.cleaned_title,
                extension=meta.extension,
                extraction_method=f"{meta.extraction_method}_renumbered"
            )
            renumbered.append(new_meta)
        
        return renumbered
