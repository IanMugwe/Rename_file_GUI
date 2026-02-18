"""
Main application controller.

Coordinates between UI and backend services.
Manages application state and workflow.
"""

import time
from pathlib import Path
from typing import Optional, List
from dataclasses import dataclass

from parser import EpisodeParser
from sanitizer import FilenameSanitizer
from sorter import NaturalSorter, ConflictDetector
from validator import SafeFormatter, FilenameValidator
from models import EpisodeMetadata, RenameTransaction

from scanner import DirectoryScannerService
from rename_transaction import RenameTransactionManager, TransactionBuilder
from logging_service import LoggingService
from export_service import ExportService


@dataclass
class AppConfig:
    """Application configuration."""
    format_string: str = "{number}. {title}"
    zero_padding: int = 2
    recursive_scan: bool = False
    extension_filter: Optional[str] = "video"  # video, audio, documents, all
    enable_logging: bool = True
    dry_run_mode: bool = False


class ApplicationController:
    """
    Main application controller.
    
    Orchestrates:
    - Directory scanning
    - Metadata extraction
    - Conflict detection
    - Transaction execution
    - Logging
    """
    
    def __init__(self, config: Optional[AppConfig] = None):
        """
        Initialize controller.
        
        Args:
            config: Application configuration
        """
        self.config = config or AppConfig()
        
        # Initialize services
        self.parser = EpisodeParser()
        self.sanitizer = FilenameSanitizer()
        self.sorter = NaturalSorter()
        self.formatter = SafeFormatter()
        self.validator = FilenameValidator()
        self.conflict_detector = ConflictDetector()
        
        # Scanner with config
        extensions = DirectoryScannerService.get_preset_extensions(
            self.config.extension_filter
        )
        self.scanner = DirectoryScannerService(
            recursive=self.config.recursive_scan,
            extensions=extensions
        )
        
        # Logging
        self.logger = LoggingService() if self.config.enable_logging else None
        
        # Export service
        self.exporter = ExportService()
        
        # State
        self.current_directory: Optional[Path] = None
        self.scanned_metadata: List[EpisodeMetadata] = []
        self.current_transaction: Optional[RenameTransaction] = None
    
    def set_directory(self, directory: Path) -> bool:
        """
        Set working directory.
        
        Args:
            directory: Directory to work with
        
        Returns:
            True if valid
        """
        if not directory.exists() or not directory.is_dir():
            return False
        
        self.current_directory = directory
        return True
    
    def scan_and_parse(self) -> tuple[List[EpisodeMetadata], List[str]]:
        """
        Scan directory and parse all files.
        
        Returns:
            (metadata_list, errors)
        """
        if not self.current_directory:
            return [], ["No directory selected"]
        
        # Scan
        scan_result = self.scanner.scan_directory(self.current_directory)
        
        if scan_result.errors:
            return [], scan_result.errors
        
        if not scan_result.files_found:
            return [], ["No files found"]
        
        # Parse each file
        metadata_list = []
        for filepath in scan_result.files_found:
            meta = self.parser.parse(filepath)
            metadata_list.append(meta)
        
        # Sort by extracted number
        metadata_list = self.sorter.sort_metadata(metadata_list)
        
        # Store
        self.scanned_metadata = metadata_list
        
        return metadata_list, []
    
    def validate_format_string(self, format_str: str) -> tuple[bool, Optional[str]]:
        """
        Validate user format string.
        
        Args:
            format_str: Format template
        
        Returns:
            (is_valid, error_message)
        """
        result = self.formatter.validate_format_string(format_str)
        
        if not result.is_valid:
            return False, result.error_message
        
        return True, None
    
    def build_transaction(self, format_string: Optional[str] = None) -> RenameTransaction:
        """
        Build rename transaction from current metadata.
        
        Args:
            format_string: Custom format (uses config default if None)
        
        Returns:
            RenameTransaction ready for execution
        """
        if not self.scanned_metadata:
            raise ValueError("No metadata available. Run scan_and_parse first.")
        
        format_str = format_string or self.config.format_string
        
        # Validate format
        is_valid, error = self.validate_format_string(format_str)
        if not is_valid:
            raise ValueError(f"Invalid format string: {error}")
        
        # Build transaction
        builder = TransactionBuilder(format_str, self.config.zero_padding)
        transaction = builder.build_transaction(
            self.scanned_metadata,
            self.sanitizer,
            self.formatter
        )
        
        self.current_transaction = transaction
        return transaction
    
    def detect_conflicts(self, transaction: RenameTransaction) -> dict:
        """
        Detect all potential conflicts.
        
        Returns:
            Dictionary with conflict information
        """
        duplicates = self.conflict_detector.detect_duplicate_targets(
            transaction.operations
        )
        
        collisions = self.conflict_detector.detect_target_collisions(
            transaction.operations
        )
        
        case_only = self.conflict_detector.detect_case_only_changes(
            transaction.operations
        )
        
        gaps = self.conflict_detector.detect_number_gaps(
            self.scanned_metadata
        )
        
        duplicate_numbers = self.conflict_detector.detect_duplicate_numbers(
            self.scanned_metadata
        )
        
        return {
            'duplicate_targets': duplicates,
            'file_collisions': collisions,
            'case_only_changes': case_only,
            'number_gaps': gaps,
            'duplicate_numbers': duplicate_numbers,
            'has_conflicts': bool(duplicates or collisions)
        }
    
    def execute_transaction(self, 
                          transaction: RenameTransaction,
                          progress_callback=None) -> bool:
        """
        Execute rename transaction.
        
        Args:
            transaction: Transaction to execute
            progress_callback: Optional callback(current, total, message)
        
        Returns:
            True if successful
        """
        if self.config.dry_run_mode:
            # Dry run: simulate without actual rename
            if progress_callback:
                total = len(transaction.operations)
                for i in range(total + 1):
                    progress_callback(i, total, f"Dry run: {i}/{total}")
                    time.sleep(0.01)  # Simulate work
            return True
        
        # Log start
        if self.logger:
            self.logger.log_transaction_start(transaction)
        
        start_time = time.time()
        
        # Execute
        manager = RenameTransactionManager(progress_callback)
        success = manager.execute_transaction(transaction)
        
        duration_ms = (time.time() - start_time) * 1000
        
        # Log completion
        if self.logger:
            self.logger.log_transaction_complete(transaction, success, duration_ms)
        
        return success
    
    def export_preview_csv(self, output_path: Path) -> bool:
        """
        Export current metadata to CSV.
        
        Args:
            output_path: Output file path
        
        Returns:
            True if successful
        """
        if not self.scanned_metadata:
            return False
        
        return self.exporter.export_metadata_preview(
            self.scanned_metadata,
            output_path
        )
    
    def export_rename_plan(self, output_path: Path) -> bool:
        """
        Export rename plan to CSV.
        
        Args:
            output_path: Output file path
        
        Returns:
            True if successful
        """
        if not self.current_transaction:
            return False
        
        return self.exporter.export_rename_plan(
            self.current_transaction,
            output_path
        )
    
    def get_statistics(self) -> dict:
        """
        Get statistics about current scan.
        
        Returns:
            Dictionary with statistics
        """
        if not self.scanned_metadata:
            return {
                'total_files': 0,
                'with_numbers': 0,
                'avg_confidence': 0.0
            }
        
        total = len(self.scanned_metadata)
        with_numbers = sum(1 for m in self.scanned_metadata 
                          if m.extracted_number is not None)
        
        confidences = [m.confidence for m in self.scanned_metadata 
                      if m.confidence > 0]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
        
        return {
            'total_files': total,
            'with_numbers': with_numbers,
            'without_numbers': total - with_numbers,
            'avg_confidence': avg_confidence,
            'min_number': min((m.extracted_number for m in self.scanned_metadata 
                             if m.extracted_number), default=0),
            'max_number': max((m.extracted_number for m in self.scanned_metadata 
                             if m.extracted_number), default=0)
        }
