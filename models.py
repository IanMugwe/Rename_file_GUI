"""
Core data models for the playlist renamer system.
Immutable, typed structures for safe data flow.
"""

from dataclasses import dataclass, field
from typing import Optional, List
from pathlib import Path
from enum import Enum
import uuid


class RenameStatus(Enum):
    """Status of a rename operation."""
    PENDING = "pending"
    STAGED = "staged"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


class ConfidenceLevel(Enum):
    """Confidence in episode number extraction."""
    HIGH = 0.9      # Season/Episode format (S01E02, 1x02)
    MEDIUM = 0.6    # Explicit Episode/Ep markers
    LOW = 0.3       # Standalone numbers
    NONE = 0.0      # No number found


@dataclass(frozen=True)
class EpisodeMetadata:
    """
    Immutable metadata extracted from a filename.
    
    Confidence scoring ensures deterministic selection when
    multiple number candidates exist.
    """
    original_name: str
    file_path: Path
    
    # Extracted components
    season: Optional[int] = None
    episode: Optional[int] = None
    extracted_number: Optional[int] = None
    confidence: float = 0.0
    
    # Cleaned content
    cleaned_title: str = ""
    extension: str = ""
    
    # Metadata
    extraction_method: str = ""  # Which regex pattern matched
    
    def __post_init__(self):
        """Validate confidence bounds."""
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"Confidence must be in [0, 1], got {self.confidence}")


@dataclass
class RenameOperation:
    """
    Represents a single file rename operation in the transaction.
    
    Tracks all three states: original → staging → final
    This enables full rollback capability.
    """
    # Original state
    original_path: Path
    metadata: EpisodeMetadata
    
    # Computed target
    target_name: str
    target_path: Path
    
    # Staging (UUID-based temporary)
    staging_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    staging_path: Optional[Path] = None
    
    # Transaction state
    status: RenameStatus = RenameStatus.PENDING
    error_message: Optional[str] = None
    
    def get_staging_filename(self) -> str:
        """Generate staging filename with original extension preserved."""
        return f".rename_staging_{self.staging_id}{self.metadata.extension}"
    
    def is_case_only_change(self) -> bool:
        """Detect if this is only a case change (Windows problematic)."""
        return (self.original_path.name.lower() == self.target_name.lower() and
                self.original_path.name != self.target_name)


@dataclass
class RenameTransaction:
    """
    Atomic transaction containing multiple rename operations.
    
    Implements two-phase commit:
    - Phase 1: Rename all to staging (UUID names)
    - Phase 2: Rename staging to final targets
    
    Any failure triggers full rollback.
    """
    operations: List[RenameOperation] = field(default_factory=list)
    transaction_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    
    def add_operation(self, operation: RenameOperation) -> None:
        """Add operation to transaction."""
        self.operations.append(operation)
    
    def get_pending_operations(self) -> List[RenameOperation]:
        """Get operations not yet completed."""
        return [op for op in self.operations if op.status == RenameStatus.PENDING]
    
    def get_staged_operations(self) -> List[RenameOperation]:
        """Get operations in staging state."""
        return [op for op in self.operations if op.status == RenameStatus.STAGED]
    
    def all_completed(self) -> bool:
        """Check if all operations completed successfully."""
        return all(op.status == RenameStatus.COMPLETED for op in self.operations)
    
    def any_failed(self) -> bool:
        """Check if any operation failed."""
        return any(op.status == RenameStatus.FAILED for op in self.operations)


@dataclass
class ValidationResult:
    """Result of format string or filename validation."""
    is_valid: bool
    error_message: Optional[str] = None
    warnings: List[str] = field(default_factory=list)


@dataclass
class ScanResult:
    """Result of directory scanning operation."""
    files_found: List[Path]
    files_processed: int
    files_skipped: int
    errors: List[str] = field(default_factory=list)
    scan_time_ms: float = 0.0
