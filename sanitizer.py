"""
Filename sanitization and cleaning engine.

Removes technical artifacts, normalizes Unicode, and ensures
cross-platform filesystem compatibility.
"""

import re
import unicodedata
from typing import Set


class FilenameSanitizer:
    """
    Industrial-grade filename cleaner.
    
    Removes:
    - Video codecs (x264, h265, HEVC, etc.)
    - Resolution tags (1080p, 720p, 4K, etc.)
    - Audio codecs (AAC, DTS, AC3, etc.)
    - Release groups ([RARBG], {YTS}, etc.)
    - Website watermarks
    - Duplicate whitespace
    - Unsafe filesystem characters
    
    Normalizes:
    - Unicode to NFC form
    - Smart quotes to ASCII
    - Em/en dashes to hyphens
    - Multiple dots/spaces
    """
    
    # Windows forbidden characters: < > : " / \ | ? *
    WINDOWS_FORBIDDEN = re.compile(r'[<>:"/\\|?*]')
    
    # Control characters (0x00-0x1F, 0x7F)
    CONTROL_CHARS = re.compile(r'[\x00-\x1F\x7F]')
    
    def __init__(self):
        """Initialize with precompiled patterns."""
        # Video resolution patterns
        self.resolution_patterns = [
            re.compile(r'\b\d{3,4}[pPiI]\b'),  # 1080p, 720i, 480p
            re.compile(r'\b[248][kK]\b'),       # 4K, 8K, 2K
            re.compile(r'\bUHD\b', re.IGNORECASE),
            re.compile(r'\bHD\b(?!\w)'),        # HD but not HDR
            re.compile(r'\bFHD\b', re.IGNORECASE),
            re.compile(r'\b\d{3,4}x\d{3,4}\b'), # 1920x1080
        ]
        
        # Video codec patterns
        self.codec_patterns = [
            re.compile(r'\b[xXhH]\.?26[45]\b'),     # x264, h265, H.264
            re.compile(r'\bHEVC\b', re.IGNORECASE),
            re.compile(r'\bAVC\b(?!\w)', re.IGNORECASE),
            re.compile(r'\bVP9\b', re.IGNORECASE),
            re.compile(r'\bAV1\b', re.IGNORECASE),
            re.compile(r'\bXviD\b', re.IGNORECASE),
            re.compile(r'\bDivX\b', re.IGNORECASE),
            re.compile(r'\b10bit\b', re.IGNORECASE),
            re.compile(r'\bHDR(?:10)?\b', re.IGNORECASE),
            re.compile(r'\bDolby[-\s]?Vision\b', re.IGNORECASE),
        ]
        
        # Audio codec patterns
        self.audio_patterns = [
            re.compile(r'\bAAC(?:[-.\s]?2\.0)?\b', re.IGNORECASE),
            re.compile(r'\bAC3\b', re.IGNORECASE),
            re.compile(r'\bDTS(?:[-.\s]?HD)?(?:[-.\s]?MA)?\b', re.IGNORECASE),
            re.compile(r'\bTrueHD\b', re.IGNORECASE),
            re.compile(r'\bFLAC\b', re.IGNORECASE),
            re.compile(r'\bMP3\b', re.IGNORECASE),
            re.compile(r'\bOpus\b', re.IGNORECASE),
            re.compile(r'\bAtmos\b', re.IGNORECASE),
            re.compile(r'\b[257]\.1(?:\.\d)?\b'),  # 5.1, 7.1.4
        ]
        
        # Release group patterns (bracketed/braced)
        self.release_group_patterns = [
            re.compile(r'\[[^\]]+\]'),   # [RARBG], [YTS.MX]
            re.compile(r'\{[^}]+\}'),    # {Group}
            re.compile(r'\([^)]*(?:RARBG|YTS|YIFY|ETRG|FGT)[^)]*\)', re.IGNORECASE),
        ]
        
        # File source patterns
        self.source_patterns = [
            re.compile(r'\bWEB[-.\s]?DL\b', re.IGNORECASE),
            re.compile(r'\bWEB[-.\s]?Rip\b', re.IGNORECASE),
            re.compile(r'\bBlu[-.\s]?Ray\b', re.IGNORECASE),
            re.compile(r'\bBDRip\b', re.IGNORECASE),
            re.compile(r'\bDVDRip\b', re.IGNORECASE),
            re.compile(r'\bHDTV\b', re.IGNORECASE),
            re.compile(r'\bWEBRip\b', re.IGNORECASE),
        ]
        
        # Streaming service tags
        self.streaming_patterns = [
            re.compile(r'\bNetflix\b', re.IGNORECASE),
            re.compile(r'\bAmazon\b', re.IGNORECASE),
            re.compile(r'\bDisney\+?\b', re.IGNORECASE),
            re.compile(r'\bHBO\b', re.IGNORECASE),
            re.compile(r'\bHulu\b', re.IGNORECASE),
            re.compile(r'\bApple[-.\s]?TV\+?\b', re.IGNORECASE),
        ]
        
        # YouTube ID pattern
        self.youtube_pattern = re.compile(r'-[A-Za-z0-9_-]{11}(?=\.|$)')
        
        # Website watermarks
        self.website_patterns = [
            re.compile(r'\bwww\.[a-z0-9]+\.[a-z]{2,}\b', re.IGNORECASE),
            re.compile(r'\b[a-z0-9]+\.com\b', re.IGNORECASE),
            re.compile(r'\b[a-z0-9]+\.net\b', re.IGNORECASE),
        ]
        
        # Common junk tokens
        self.junk_patterns = [
            re.compile(r'\bREPACK\b', re.IGNORECASE),
            re.compile(r'\bPROPER\b', re.IGNORECASE),
            re.compile(r'\bREMUX\b', re.IGNORECASE),
            re.compile(r'\bHYBRID\b', re.IGNORECASE),
            re.compile(r'\bDUAL\b', re.IGNORECASE),
            re.compile(r'\bMULTi\d?\b', re.IGNORECASE),
        ]
    
    def sanitize(self, filename: str) -> str:
        """
        Clean filename of all technical artifacts.
        
        Args:
            filename: Raw filename (without extension)
        
        Returns:
            Cleaned filename safe for all platforms
        """
        cleaned = filename
        
        # Remove all technical patterns
        cleaned = self._remove_patterns(cleaned, self.resolution_patterns)
        cleaned = self._remove_patterns(cleaned, self.codec_patterns)
        cleaned = self._remove_patterns(cleaned, self.audio_patterns)
        cleaned = self._remove_patterns(cleaned, self.source_patterns)
        cleaned = self._remove_patterns(cleaned, self.streaming_patterns)
        cleaned = self._remove_patterns(cleaned, self.junk_patterns)
        cleaned = self._remove_patterns(cleaned, self.release_group_patterns)
        
        # Remove YouTube IDs
        cleaned = self.youtube_pattern.sub('', cleaned)
        
        # Remove website watermarks
        cleaned = self._remove_patterns(cleaned, self.website_patterns)
        
        # Normalize Unicode
        cleaned = self._normalize_unicode(cleaned)
        
        # Remove filesystem-unsafe characters
        cleaned = self._remove_unsafe_chars(cleaned)
        
        # Clean up separators
        cleaned = self._normalize_separators(cleaned)
        
        # Remove duplicate spaces
        cleaned = re.sub(r'\s+', ' ', cleaned)
        
        # Trim whitespace and trailing dots/spaces
        cleaned = cleaned.strip(' .')
        
        # Ensure not empty
        if not cleaned:
            cleaned = "untitled"
        
        return cleaned
    
    def _remove_patterns(self, text: str, patterns: list) -> str:
        """Remove all matching patterns from text."""
        for pattern in patterns:
            text = pattern.sub('', text)
        return text
    
    def _normalize_unicode(self, text: str) -> str:
        """
        Normalize Unicode to NFC form and convert smart characters.
        
        NFC (Canonical Decomposition followed by Canonical Composition)
        ensures consistent representation across platforms.
        """
        # Normalize to NFC
        text = unicodedata.normalize('NFC', text)
        
        # Convert smart quotes to ASCII
        text = text.replace('\u2018', "'")  # Left single quote
        text = text.replace('\u2019', "'")  # Right single quote
        text = text.replace('\u201C', '"')  # Left double quote
        text = text.replace('\u201D', '"')  # Right double quote
        
        # Convert dashes
        text = text.replace('\u2013', '-')  # En dash
        text = text.replace('\u2014', '-')  # Em dash
        text = text.replace('\u2015', '-')  # Horizontal bar
        
        # Convert ellipsis
        text = text.replace('\u2026', '...')
        
        return text
    
    def _remove_unsafe_chars(self, text: str) -> str:
        """Remove characters unsafe for Windows/macOS/Linux filesystems."""
        # Remove Windows forbidden characters
        text = self.WINDOWS_FORBIDDEN.sub('', text)
        
        # Remove control characters
        text = self.CONTROL_CHARS.sub('', text)
        
        # Remove leading/trailing dots (Windows issue)
        text = text.strip('.')
        
        return text
    
    def _normalize_separators(self, text: str) -> str:
        """
        Normalize filename separators.
        
        Converts common separators (., _, -) to spaces for readability.
        Preserves intentional punctuation.
        """
        # Replace underscores with spaces
        text = text.replace('_', ' ')
        
        # Replace dots with spaces (but not in abbreviations)
        # Don't replace dot if surrounded by letters (acronyms)
        text = re.sub(r'(?<!\w)\.(?!\w)', ' ', text)
        text = re.sub(r'(?<=\w)\.(?=\s)', ' ', text)
        text = re.sub(r'(?<=\s)\.(?=\w)', ' ', text)
        
        # Normalize multiple separators
        text = re.sub(r'[-\s]+', ' ', text)
        
        return text
    
    def is_safe_filename(self, filename: str) -> bool:
        """
        Check if filename is safe for cross-platform use.
        
        Returns False if contains forbidden characters.
        """
        if self.WINDOWS_FORBIDDEN.search(filename):
            return False
        
        if self.CONTROL_CHARS.search(filename):
            return False
        
        # Check for reserved Windows names
        base = filename.split('.')[0].upper()
        reserved = {'CON', 'PRN', 'AUX', 'NUL', 'COM1', 'COM2', 'COM3', 
                   'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9',
                   'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6',
                   'LPT7', 'LPT8', 'LPT9'}
        if base in reserved:
            return False
        
        return True
