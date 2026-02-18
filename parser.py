"""
Parsing engine for episode number extraction.

Uses confidence-scored regex patterns to deterministically
select the best number candidate from ambiguous filenames.
"""

import re
from typing import Optional, List, Tuple
from pathlib import Path
from models import EpisodeMetadata, ConfidenceLevel


class EpisodeParser:
    """
    Confidence-based episode number extractor.
    
    Patterns are ordered by specificity and confidence level.
    Earlier matches override later ones only if confidence is higher.
    """
    
    def __init__(self):
        """Initialize with precompiled regex patterns."""
        # HIGH CONFIDENCE: Explicit season/episode markers
        self.season_episode_patterns = [
            # S01E02, S1E2
            (re.compile(r'[Ss](\d{1,2})[Ee](\d{1,3})', re.IGNORECASE), 
             ConfidenceLevel.HIGH, "S##E##"),
            # 1x02, 1x2
            (re.compile(r'(\d{1,2})[xX](\d{1,3})'), 
             ConfidenceLevel.HIGH, "##x##"),
            # Season 1 Episode 2
            (re.compile(r'[Ss]eason\s*(\d{1,2})\s*[Ee]pisode\s*(\d{1,3})', re.IGNORECASE),
             ConfidenceLevel.HIGH, "Season # Episode #"),
        ]
        
        # MEDIUM CONFIDENCE: Episode markers without season
        self.episode_patterns = [
            # Episode 02, Ep 02, Ep. 02
            (re.compile(r'[Ee]p(?:isode)?\.?\s*(\d{1,3})', re.IGNORECASE),
             ConfidenceLevel.MEDIUM, "Episode #"),
            # Part 2, Pt 2
            (re.compile(r'[Pp](?:ar)?t\.?\s*(\d{1,3})', re.IGNORECASE),
             ConfidenceLevel.MEDIUM, "Part #"),
            # Chapter 2, Ch 2
            (re.compile(r'[Cc]h(?:apter)?\.?\s*(\d{1,3})', re.IGNORECASE),
             ConfidenceLevel.MEDIUM, "Chapter #"),
            # [02], (02)
            (re.compile(r'[\[\(](\d{1,3})[\]\)]'),
             ConfidenceLevel.MEDIUM, "[#]"),
            # #02
            (re.compile(r'#(\d{1,3})'),
             ConfidenceLevel.MEDIUM, "#"),
        ]
        
        # LOW CONFIDENCE: Standalone numbers
        # Leading number at start: "02 - Title"
        self.leading_number = re.compile(r'^(\d{1,3})(?:\s*[-_.\s]|\s+)')
        
        # Trailing number: "Title - 02"
        self.trailing_number = re.compile(r'[-_.\s](\d{1,3})(?:\s*[-_.\s])?$')
        
        # Any standalone number (last resort)
        self.standalone_number = re.compile(r'\b(\d{1,3})\b')
        
        # EXCLUSION PATTERNS: Things that look like numbers but aren't
        self.exclusion_patterns = [
            re.compile(r'\b(19|20)\d{2}\b'),  # Years: 1999, 2023
            re.compile(r'\b\d{3,4}[pP]\b'),    # Resolution: 1080p, 720p
            re.compile(r'\b[248][kK]\b'),      # Resolution: 4K, 8K
            re.compile(r'\b\d+[km]bps\b', re.IGNORECASE),  # Bitrate
            re.compile(r'\b\d+[hH][zZ]\b'),    # Frequency: 60Hz
            re.compile(r'\bv?\d+\.\d+\b'),     # Version: v1.5, 2.0
        ]
    
    def parse(self, filepath: Path) -> EpisodeMetadata:
        """
        Extract episode metadata from filename.
        
        Returns highest-confidence match found.
        """
        filename = filepath.stem  # Without extension
        extension = filepath.suffix
        
        # Try high-confidence patterns first
        metadata = self._try_season_episode(filename, filepath, extension)
        if metadata and metadata.confidence >= ConfidenceLevel.HIGH.value:
            return metadata
        
        # Try medium-confidence episode patterns
        ep_metadata = self._try_episode_patterns(filename, filepath, extension)
        if ep_metadata and ep_metadata.confidence > (metadata.confidence if metadata else 0):
            metadata = ep_metadata
        
        # Try low-confidence standalone numbers
        num_metadata = self._try_standalone_numbers(filename, filepath, extension)
        if num_metadata and num_metadata.confidence > (metadata.confidence if metadata else 0):
            metadata = num_metadata
        
        # Return best match or empty metadata
        if metadata:
            return metadata
        
        return EpisodeMetadata(
            original_name=filepath.name,
            file_path=filepath,
            extension=extension,
            extraction_method="none"
        )
    
    def _try_season_episode(self, filename: str, filepath: Path, 
                           extension: str) -> Optional[EpisodeMetadata]:
        """Try season/episode patterns (highest confidence)."""
        for pattern, confidence, method in self.season_episode_patterns:
            match = pattern.search(filename)
            if match:
                season = int(match.group(1))
                episode = int(match.group(2))
                
                # Use episode number as the primary number
                return EpisodeMetadata(
                    original_name=filepath.name,
                    file_path=filepath,
                    season=season,
                    episode=episode,
                    extracted_number=episode,
                    confidence=confidence.value,
                    extension=extension,
                    extraction_method=method
                )
        
        return None
    
    def _try_episode_patterns(self, filename: str, filepath: Path,
                             extension: str) -> Optional[EpisodeMetadata]:
        """Try explicit episode markers (medium confidence)."""
        for pattern, confidence, method in self.episode_patterns:
            match = pattern.search(filename)
            if match:
                number = int(match.group(1))
                
                # Validate not an excluded pattern
                if self._is_excluded_number(filename, match.start(1)):
                    continue
                
                return EpisodeMetadata(
                    original_name=filepath.name,
                    file_path=filepath,
                    extracted_number=number,
                    confidence=confidence.value,
                    extension=extension,
                    extraction_method=method
                )
        
        return None
    
    def _try_standalone_numbers(self, filename: str, filepath: Path,
                               extension: str) -> Optional[EpisodeMetadata]:
        """Try standalone number patterns (lowest confidence)."""
        # Try leading number first
        match = self.leading_number.search(filename)
        if match:
            number = int(match.group(1))
            if not self._is_excluded_number(filename, match.start(1)):
                return EpisodeMetadata(
                    original_name=filepath.name,
                    file_path=filepath,
                    extracted_number=number,
                    confidence=ConfidenceLevel.LOW.value,
                    extension=extension,
                    extraction_method="leading_number"
                )
        
        # Try trailing number
        match = self.trailing_number.search(filename)
        if match:
            number = int(match.group(1))
            if not self._is_excluded_number(filename, match.start(1)):
                return EpisodeMetadata(
                    original_name=filepath.name,
                    file_path=filepath,
                    extracted_number=number,
                    confidence=ConfidenceLevel.LOW.value,
                    extension=extension,
                    extraction_method="trailing_number"
                )
        
        # Last resort: find all standalone numbers, use last one
        all_matches = list(self.standalone_number.finditer(filename))
        if all_matches:
            # Reverse search to find last valid number
            for match in reversed(all_matches):
                if not self._is_excluded_number(filename, match.start(1)):
                    number = int(match.group(1))
                    return EpisodeMetadata(
                        original_name=filepath.name,
                        file_path=filepath,
                        extracted_number=number,
                        confidence=ConfidenceLevel.LOW.value * 0.5,  # Even lower
                        extension=extension,
                        extraction_method="standalone_number"
                    )
        
        return None
    
    def _is_excluded_number(self, filename: str, match_position: int) -> bool:
        """Check if number at position matches exclusion patterns."""
        # Extract context around the number
        context_start = max(0, match_position - 10)
        context_end = min(len(filename), match_position + 15)
        context = filename[context_start:context_end]
        
        for pattern in self.exclusion_patterns:
            if pattern.search(context):
                return True
        
        return False
    
    def extract_numbers_debug(self, filename: str) -> List[Tuple[int, float, str]]:
        """
        Debug method to show all detected numbers with confidence scores.
        
        Returns: List of (number, confidence, method) tuples
        """
        results = []
        filepath = Path(filename)
        
        # Try all pattern types
        for pattern, confidence, method in self.season_episode_patterns:
            match = pattern.search(filename)
            if match:
                episode = int(match.group(2))
                results.append((episode, confidence.value, method))
        
        for pattern, confidence, method in self.episode_patterns:
            match = pattern.search(filename)
            if match:
                number = int(match.group(1))
                results.append((number, confidence.value, method))
        
        # Standalone numbers
        match = self.leading_number.search(filename)
        if match:
            results.append((int(match.group(1)), ConfidenceLevel.LOW.value, "leading"))
        
        match = self.trailing_number.search(filename)
        if match:
            results.append((int(match.group(1)), ConfidenceLevel.LOW.value, "trailing"))
        
        return results
