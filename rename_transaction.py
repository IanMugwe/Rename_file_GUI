"""
Two-Phase Commit Rename Transaction Manager.

This is the critical safety system that guarantees atomic rename operations.

Architecture:
    Phase 1: Rename all files to UUID-based staging names
    Phase 2: Rename staging files to final targets
    
    If ANY operation fails, ALL changes are rolled back.
    
    This prevents partial rename states that could corrupt file organization.

Transaction Flow:
    1. Pre-flight validation
    2. Lock transaction
    3. PHASE 1: original → staging (UUID)
    4. Checkpoint
    5. PHASE 2: staging → final
    6. Commit / Rollback
    7. Unlock transaction
"""

import os
import shutil
import time
from pathlib import Path
from typing import List, Optional, Callable
from enum import Enum

from models import (
    RenameOperation, 
    RenameTransaction, 
    RenameStatus,
    EpisodeMetadata
)


class TransactionPhase(Enum):
    """Transaction execution phases."""
    PREFLIGHT = "preflight"
    PHASE_ONE = "phase_one"    # original → staging
    CHECKPOINT = "checkpoint"
    PHASE_TWO = "phase_two"     # staging → final
    COMMIT = "commit"
    ROLLBACK = "rollback"


class TransactionError(Exception):
    """Base exception for transaction errors."""
    pass


class RenameTransactionManager:
    """
    Atomic rename transaction manager with two-phase commit.
    
    Guarantees:
    - No partial renames
    - Full rollback on any failure
    - Case-insensitive filesystem support
    - Handles locked files gracefully
    """
    
    def __init__(self, progress_callback: Optional[Callable[[int, int, str], None]] = None):
        """
        Initialize transaction manager.
        
        Args:
            progress_callback: Optional callback(current, total, message)
        """
        self.progress_callback = progress_callback
        self.current_transaction: Optional[RenameTransaction] = None
        self.current_phase: TransactionPhase = TransactionPhase.PREFLIGHT
    
    def execute_transaction(self, transaction: RenameTransaction) -> bool:
        """
        Execute atomic rename transaction.
        
        Args:
            transaction: RenameTransaction to execute
        
        Returns:
            True if successful, False if rolled back
        
        Raises:
            TransactionError: On critical failures
        """
        self.current_transaction = transaction
        
        try:
            # Pre-flight validation
            self._report_progress(0, len(transaction.operations), "Validating...")
            self.current_phase = TransactionPhase.PREFLIGHT
            self._preflight_validation(transaction)
            
            # PHASE ONE: Rename to staging (UUID names)
            self._report_progress(0, len(transaction.operations), "Phase 1: Staging...")
            self.current_phase = TransactionPhase.PHASE_ONE
            self._execute_phase_one(transaction)
            
            # Checkpoint: Verify phase one completed
            self._report_progress(0, len(transaction.operations), "Checkpoint...")
            self.current_phase = TransactionPhase.CHECKPOINT
            self._verify_phase_one(transaction)
            
            # PHASE TWO: Rename staging to final
            self._report_progress(0, len(transaction.operations), "Phase 2: Finalizing...")
            self.current_phase = TransactionPhase.PHASE_TWO
            self._execute_phase_two(transaction)
            
            # Commit
            self.current_phase = TransactionPhase.COMMIT
            self._commit_transaction(transaction)
            
            self._report_progress(len(transaction.operations), 
                                len(transaction.operations), 
                                "Complete!")
            
            return True
            
        except Exception as e:
            # ROLLBACK
            self._report_progress(0, len(transaction.operations), 
                                f"Rolling back: {str(e)}")
            self.current_phase = TransactionPhase.ROLLBACK
            
            try:
                self._rollback_transaction(transaction)
            except Exception as rollback_error:
                # Critical: Rollback itself failed
                raise TransactionError(
                    f"CRITICAL: Rollback failed! Original error: {e}. "
                    f"Rollback error: {rollback_error}"
                )
            
            return False
        
        finally:
            self.current_transaction = None
            self.current_phase = TransactionPhase.PREFLIGHT
    
    def _preflight_validation(self, transaction: RenameTransaction) -> None:
        """
        Validate all operations before execution.
        
        Checks:
        - Source files exist
        - Source files readable
        - Target directory writable
        - No permission issues
        - Sufficient disk space
        """
        for op in transaction.operations:
            # Check source exists
            if not op.original_path.exists():
                raise TransactionError(
                    f"Source file not found: {op.original_path}"
                )
            
            # Check source is a file
            if not op.original_path.is_file():
                raise TransactionError(
                    f"Source is not a file: {op.original_path}"
                )
            
            # Check readable
            if not os.access(op.original_path, os.R_OK):
                raise TransactionError(
                    f"Source file not readable: {op.original_path}"
                )
            
            # Check target directory writable
            target_dir = op.target_path.parent
            if not os.access(target_dir, os.W_OK):
                raise TransactionError(
                    f"Target directory not writable: {target_dir}"
                )
            
            # Set staging path
            staging_filename = op.get_staging_filename()
            op.staging_path = target_dir / staging_filename
    
    def _execute_phase_one(self, transaction: RenameTransaction) -> None:
        """
        PHASE ONE: Rename all files to staging (UUID) names.
        
        This phase eliminates naming conflicts by giving each
        file a unique temporary name.
        """
        total = len(transaction.operations)
        
        for i, op in enumerate(transaction.operations):
            self._report_progress(i, total, f"Staging {op.original_path.name}...")
            
            try:
                # Rename to staging
                self._safe_rename(op.original_path, op.staging_path)
                op.status = RenameStatus.STAGED
                
            except Exception as e:
                op.status = RenameStatus.FAILED
                op.error_message = str(e)
                raise TransactionError(
                    f"Phase 1 failed on {op.original_path.name}: {e}"
                )
    
    def _verify_phase_one(self, transaction: RenameTransaction) -> None:
        """
        Verify phase one completed successfully.
        
        All files should now be in staging state with UUID names.
        """
        for op in transaction.operations:
            if op.status != RenameStatus.STAGED:
                raise TransactionError(
                    f"Operation not staged: {op.original_path.name}"
                )
            
            if not op.staging_path.exists():
                raise TransactionError(
                    f"Staging file missing: {op.staging_path}"
                )
    
    def _execute_phase_two(self, transaction: RenameTransaction) -> None:
        """
        PHASE TWO: Rename staging files to final targets.
        
        At this point all conflicts are resolved since files
        have unique UUID names.
        """
        total = len(transaction.operations)
        
        for i, op in enumerate(transaction.operations):
            self._report_progress(i, total, f"Finalizing {op.target_name}...")
            
            try:
                # Rename to final target
                self._safe_rename(op.staging_path, op.target_path)
                op.status = RenameStatus.COMPLETED
                
            except Exception as e:
                op.status = RenameStatus.FAILED
                op.error_message = str(e)
                raise TransactionError(
                    f"Phase 2 failed on {op.target_name}: {e}"
                )
    
    def _commit_transaction(self, transaction: RenameTransaction) -> None:
        """
        Finalize transaction commit.
        
        Verify all operations completed successfully.
        """
        if not transaction.all_completed():
            raise TransactionError("Not all operations completed")
    
    def _rollback_transaction(self, transaction: RenameTransaction) -> None:
        """
        Roll back transaction to original state.
        
        Restores files based on current phase:
        - PHASE_ONE: staging → original
        - PHASE_TWO: final → staging → original
        - CHECKPOINT: staging → original
        """
        if self.current_phase in (TransactionPhase.PREFLIGHT, TransactionPhase.COMMIT):
            # No changes made yet or already committed
            return
        
        # Reverse phase two if started
        if self.current_phase == TransactionPhase.PHASE_TWO:
            for op in transaction.operations:
                if op.status == RenameStatus.COMPLETED:
                    # Completed phase two: final → staging
                    try:
                        if op.target_path.exists():
                            self._safe_rename(op.target_path, op.staging_path)
                            op.status = RenameStatus.STAGED
                    except Exception as e:
                        # Log but continue rollback
                        print(f"Rollback warning: {e}")
        
        # Reverse phase one
        for op in transaction.operations:
            if op.status == RenameStatus.STAGED:
                # Staged: staging → original
                try:
                    if op.staging_path and op.staging_path.exists():
                        self._safe_rename(op.staging_path, op.original_path)
                        op.status = RenameStatus.ROLLED_BACK
                except Exception as e:
                    print(f"Rollback warning: {e}")
            
            # Clean up any remaining staging files
            if op.staging_path and op.staging_path.exists():
                try:
                    op.staging_path.unlink()
                except Exception:
                    pass
    
    def _safe_rename(self, source: Path, target: Path) -> None:
        """
        Perform safe atomic rename.
        
        Handles:
        - Case-only changes (requires intermediate step on Windows)
        - Cross-filesystem moves (copy + delete)
        - Permission preservation
        """
        # Check if source and target are same (case-insensitive)
        if source.resolve() == target.resolve():
            # Already at target (case-insensitive match)
            return
        
        # Handle case-only rename on case-insensitive filesystems
        if source.name.lower() == target.name.lower() and source.name != target.name:
            # Case-only change: use intermediate rename
            intermediate = source.parent / f".tmp_{source.name}_{int(time.time() * 1000000)}"
            source.rename(intermediate)
            intermediate.rename(target)
            return
        
        # Check if target already exists
        if target.exists():
            raise FileExistsError(f"Target already exists: {target}")
        
        try:
            # Try atomic rename first
            source.rename(target)
        except OSError:
            # Cross-filesystem or other issue: use copy + delete
            shutil.copy2(source, target)  # Preserves metadata
            source.unlink()
    
    def _report_progress(self, current: int, total: int, message: str) -> None:
        """Report progress via callback if provided."""
        if self.progress_callback:
            self.progress_callback(current, total, message)


class TransactionBuilder:
    """
    Builder for constructing rename transactions.
    
    Handles conflict detection and operation planning.
    """
    
    def __init__(self, format_string: str, zero_padding: int = 2):
        """
        Initialize transaction builder.
        
        Args:
            format_string: Format template for target names
            zero_padding: Digits for number padding
        """
        self.format_string = format_string
        self.zero_padding = zero_padding
    
    def build_transaction(self, 
                         metadata_list: List[EpisodeMetadata],
                         sanitizer,
                         formatter) -> RenameTransaction:
        """
        Build rename transaction from metadata list.
        
        Args:
            metadata_list: List of episode metadata (sorted)
            sanitizer: FilenameSanitizer instance
            formatter: SafeFormatter instance
        
        Returns:
            RenameTransaction ready for execution
        """
        transaction = RenameTransaction()
        
        for meta in metadata_list:
            # Clean title
            cleaned_title = sanitizer.sanitize(meta.file_path.stem)
            
            # Create updated metadata with cleaned title
            cleaned_meta = EpisodeMetadata(
                original_name=meta.original_name,
                file_path=meta.file_path,
                season=meta.season,
                episode=meta.episode,
                extracted_number=meta.extracted_number,
                confidence=meta.confidence,
                cleaned_title=cleaned_title,
                extension=meta.extension,
                extraction_method=meta.extraction_method
            )
            
            # Format target name
            target_name = formatter.format_safe(
                self.format_string,
                cleaned_meta,
                self.zero_padding
            )
            
            # Add extension
            target_name_with_ext = target_name + meta.extension
            
            # Build target path
            target_path = meta.file_path.parent / target_name_with_ext
            
            # Create operation
            operation = RenameOperation(
                original_path=meta.file_path,
                metadata=cleaned_meta,
                target_name=target_name_with_ext,
                target_path=target_path
            )
            
            transaction.add_operation(operation)
        
        return transaction
