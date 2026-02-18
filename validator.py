"""
Format string validation and safe formatting.

Prevents format string injection attacks and validates
user-provided format strings before use.
"""

import re
from typing import Dict, Optional, Set
from string import Formatter
from models import ValidationResult, EpisodeMetadata


class SafeFormatter:
    """
    Safe string formatter with strict whitelist.
    
    Prevents:
    - Attribute access (obj.__dict__)
    - Item access (obj['key'])
    - Format spec exploits
    - Arbitrary code execution
    """
    
    # Allowed placeholder names
    ALLOWED_PLACEHOLDERS: Set[str] = {
        'number',
        'title',
        'season',
        'episode',
        'extension'
    }
    
    # Pattern to detect attribute/item access
    DANGEROUS_PATTERN = re.compile(r'[.\[\]]')
    
    def __init__(self):
        """Initialize formatter."""
        self.formatter = Formatter()
    
    def validate_format_string(self, format_str: str) -> ValidationResult:
        """
        Validate format string before use.
        
        Checks:
        - Only allowed placeholders used
        - No attribute/item access
        - No format spec exploits
        - Syntactically valid
        """
        warnings = []
        
        try:
            # Parse format string
            parsed = list(self.formatter.parse(format_str))
        except Exception as e:
            return ValidationResult(
                is_valid=False,
                error_message=f"Invalid format syntax: {str(e)}"
            )
        
        # Check each field
        for literal_text, field_name, format_spec, conversion in parsed:
            if field_name is None:
                continue
            
            # Check for dangerous patterns
            if self.DANGEROUS_PATTERN.search(field_name):
                return ValidationResult(
                    is_valid=False,
                    error_message=f"Forbidden pattern in field: {field_name}"
                )
            
            # Check whitelist
            if field_name not in self.ALLOWED_PLACEHOLDERS:
                return ValidationResult(
                    is_valid=False,
                    error_message=f"Unknown placeholder: {{{field_name}}}. "
                                f"Allowed: {', '.join(sorted(self.ALLOWED_PLACEHOLDERS))}"
                )
            
            # Check format spec (allow basic formatting like :02d)
            if format_spec:
                if not re.match(r'^[0-9<>^]*[dfs]?$', format_spec):
                    warnings.append(f"Unusual format spec: {format_spec}")
            
            # Check conversion (allow !s, !r, !a)
            if conversion and conversion not in ('s', 'r', 'a'):
                return ValidationResult(
                    is_valid=False,
                    error_message=f"Invalid conversion: !{conversion}"
                )
        
        # Check for common issues
        if '{' in format_str and '}' not in format_str:
            return ValidationResult(
                is_valid=False,
                error_message="Unmatched brace in format string"
            )
        
        return ValidationResult(is_valid=True, warnings=warnings)
    
    def format_safe(self, format_str: str, metadata: EpisodeMetadata,
                   zero_padding: int = 2) -> str:
        """
        Safely format filename using metadata.
        
        Args:
            format_str: Format template (e.g., "{number}. {title}")
            metadata: Episode metadata
            zero_padding: Number of digits for zero padding
        
        Returns:
            Formatted filename
        
        Raises:
            ValueError: If format string is invalid
        """
        # Validate first
        validation = self.validate_format_string(format_str)
        if not validation.is_valid:
            raise ValueError(validation.error_message)
        
        # Build safe context dictionary with both int and string versions
        # This allows format specs like :02d to work
        number_val = metadata.extracted_number or 0
        season_val = metadata.season or 0
        episode_val = metadata.episode or 0
        
        context = {
            'number': number_val,  # Keep as int for numeric formatting
            'title': metadata.cleaned_title or 'untitled',
            'season': season_val,  # Keep as int
            'episode': episode_val,  # Keep as int
            'extension': metadata.extension
        }
        
        # Format using only whitelisted context
        try:
            return format_str.format(**context)
        except KeyError as e:
            raise ValueError(f"Missing required field: {e}")
        except Exception as e:
            raise ValueError(f"Format error: {e}")
    
    @staticmethod
    def get_default_format() -> str:
        """Get default format string."""
        return "{number}. {title}"
    
    @staticmethod
    def get_format_examples() -> Dict[str, str]:
        """Get example format strings."""
        return {
            "Simple": "{number}. {title}",
            "Zero-padded": "{number:02d}. {title}",
            "With season": "S{season}E{episode}. {title}",
            "Title first": "{title} - {number}",
            "Bracketed": "[{number}] {title}"
        }


class FilenameValidator:
    """
    Validates generated filenames before rename.
    """
    
    # Windows path length limit
    MAX_PATH_LENGTH = 260
    
    # Maximum filename length (conservative)
    MAX_FILENAME_LENGTH = 200
    
    @staticmethod
    def validate_filename(filename: str, directory: str) -> ValidationResult:
        """
        Validate filename meets all safety requirements.
        
        Args:
            filename: Proposed filename
            directory: Target directory path
        
        Returns:
            ValidationResult with any issues
        """
        warnings = []
        
        # Check length
        if len(filename) > FilenameValidator.MAX_FILENAME_LENGTH:
            return ValidationResult(
                is_valid=False,
                error_message=f"Filename too long: {len(filename)} chars "
                            f"(max {FilenameValidator.MAX_FILENAME_LENGTH})"
            )
        
        # Check full path length (Windows)
        full_path = f"{directory}/{filename}"
        if len(full_path) > FilenameValidator.MAX_PATH_LENGTH:
            warnings.append(
                f"Path length {len(full_path)} exceeds Windows limit "
                f"({FilenameValidator.MAX_PATH_LENGTH})"
            )
        
        # Check for empty name
        if not filename or filename.isspace():
            return ValidationResult(
                is_valid=False,
                error_message="Filename cannot be empty"
            )
        
        # Check for illegal characters (should be caught earlier, but double-check)
        illegal_chars = '<>:"/\\|?*'
        found_illegal = [c for c in illegal_chars if c in filename]
        if found_illegal:
            return ValidationResult(
                is_valid=False,
                error_message=f"Illegal characters found: {found_illegal}"
            )
        
        # Check for leading/trailing spaces or dots
        if filename != filename.strip(' .'):
            warnings.append("Filename has leading/trailing spaces or dots")
        
        # Check for reserved Windows names
        base = filename.split('.')[0].upper()
        reserved = {'CON', 'PRN', 'AUX', 'NUL', 'COM1', 'COM2', 'COM3', 
                   'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9',
                   'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6',
                   'LPT7', 'LPT8', 'LPT9'}
        if base in reserved:
            return ValidationResult(
                is_valid=False,
                error_message=f"Reserved Windows filename: {base}"
            )
        
        # Check for excessive dots
        if filename.count('.') > 2:
            warnings.append("Filename contains multiple dots")
        
        return ValidationResult(is_valid=True, warnings=warnings)
    
    @staticmethod
    def validate_extension(extension: str, allowed: Optional[Set[str]] = None) -> bool:
        """
        Validate file extension.
        
        Args:
            extension: File extension (with dot)
            allowed: Set of allowed extensions (e.g., {'.mp4', '.mkv'})
        
        Returns:
            True if valid
        """
        if not extension:
            return False
        
        if not extension.startswith('.'):
            return False
        
        if allowed and extension.lower() not in allowed:
            return False
        
        return True
