"""
Logging service for rename operations.

Provides:
- Timestamped operation logs
- Structured audit trail
- Undo history
- Error tracking
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
from models import RenameTransaction, RenameOperation


class LoggingService:
    """
    Structured logging for rename operations.
    
    Creates audit trail for all operations with ability
    to reconstruct history and enable undo.
    """
    
    def __init__(self, log_dir: Optional[Path] = None):
        """
        Initialize logging service.
        
        Args:
            log_dir: Directory for log files (default: ~/.playlist_renamer/logs)
        """
        if log_dir is None:
            log_dir = Path.home() / '.playlist_renamer' / 'logs'
        
        self.log_dir = log_dir
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Set up Python logging
        self.logger = self._setup_logger()
    
    def _setup_logger(self) -> logging.Logger:
        """Set up Python logger with file handler."""
        logger = logging.getLogger('playlist_renamer')
        logger.setLevel(logging.DEBUG)
        
        # Avoid duplicate handlers
        if logger.handlers:
            return logger
        
        # File handler
        log_file = self.log_dir / f'renamer_{datetime.now():%Y%m%d}.log'
        
        try:
            file_handler = logging.FileHandler(log_file, encoding='utf-8')
            file_handler.setLevel(logging.DEBUG)
            
            # Format
            formatter = logging.Formatter(
                '%(asctime)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            file_handler.setFormatter(formatter)
            
            logger.addHandler(file_handler)
        except (OSError, PermissionError) as e:
            # Log to console if file logging fails
            print(f"Warning: Could not create log file: {e}")
        
        return logger
    
    def log_transaction_start(self, transaction: RenameTransaction) -> None:
        """Log transaction start."""
        self.logger.info(f"Transaction {transaction.transaction_id} started with "
                        f"{len(transaction.operations)} operations")
    
    def log_transaction_complete(self, transaction: RenameTransaction, 
                                 success: bool, duration_ms: float) -> None:
        """
        Log transaction completion.
        
        Creates detailed JSON log for audit trail.
        """
        status = "SUCCESS" if success else "FAILED"
        
        self.logger.info(f"Transaction {transaction.transaction_id} {status} "
                        f"in {duration_ms:.2f}ms")
        
        # Create detailed transaction log
        log_data = self._build_transaction_log(transaction, success, duration_ms)
        
        # Write JSON log
        self._write_transaction_log(transaction.transaction_id, log_data)
    
    def log_operation(self, operation: RenameOperation, phase: str) -> None:
        """Log individual operation."""
        self.logger.debug(f"{phase}: {operation.original_path.name} -> "
                         f"{operation.target_name} [{operation.status.value}]")
    
    def log_error(self, message: str, exception: Optional[Exception] = None) -> None:
        """Log error with optional exception."""
        if exception:
            self.logger.error(f"{message}: {str(exception)}", exc_info=True)
        else:
            self.logger.error(message)
    
    def log_warning(self, message: str) -> None:
        """Log warning."""
        self.logger.warning(message)
    
    def _build_transaction_log(self, transaction: RenameTransaction,
                               success: bool, duration_ms: float) -> Dict[str, Any]:
        """Build structured transaction log."""
        operations_log = []
        
        for op in transaction.operations:
            op_log = {
                'original_path': str(op.original_path),
                'target_name': op.target_name,
                'target_path': str(op.target_path),
                'status': op.status.value,
                'error': op.error_message,
                'metadata': {
                    'extracted_number': op.metadata.extracted_number,
                    'confidence': op.metadata.confidence,
                    'extraction_method': op.metadata.extraction_method,
                    'season': op.metadata.season,
                    'episode': op.metadata.episode
                }
            }
            operations_log.append(op_log)
        
        return {
            'transaction_id': transaction.transaction_id,
            'timestamp': datetime.now().isoformat(),
            'success': success,
            'duration_ms': duration_ms,
            'operation_count': len(transaction.operations),
            'operations': operations_log
        }
    
    def _write_transaction_log(self, transaction_id: str, log_data: Dict[str, Any]) -> None:
        """Write transaction log to JSON file."""
        log_file = self.log_dir / f'transaction_{transaction_id}.json'
        
        try:
            with open(log_file, 'w', encoding='utf-8') as f:
                json.dump(log_data, f, indent=2, ensure_ascii=False)
        except (OSError, PermissionError) as e:
            self.logger.error(f"Could not write transaction log: {e}")
    
    def get_transaction_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get recent transaction history.
        
        Args:
            limit: Maximum number of transactions to return
        
        Returns:
            List of transaction log dictionaries
        """
        history = []
        
        try:
            # Get all transaction log files
            log_files = sorted(
                self.log_dir.glob('transaction_*.json'),
                key=lambda p: p.stat().st_mtime,
                reverse=True
            )
            
            # Load recent transactions
            for log_file in log_files[:limit]:
                try:
                    with open(log_file, 'r', encoding='utf-8') as f:
                        history.append(json.load(f))
                except Exception:
                    continue
        
        except Exception as e:
            self.logger.error(f"Error loading transaction history: {e}")
        
        return history
    
    def build_undo_script(self, transaction_id: str, output_file: Path) -> bool:
        """
        Generate undo script for a transaction.
        
        Creates a shell script that reverses the rename operations.
        
        Args:
            transaction_id: Transaction to reverse
            output_file: Path for undo script
        
        Returns:
            True if successful
        """
        log_file = self.log_dir / f'transaction_{transaction_id}.json'
        
        if not log_file.exists():
            self.logger.error(f"Transaction log not found: {transaction_id}")
            return False
        
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                log_data = json.load(f)
            
            # Generate undo commands
            undo_commands = []
            undo_commands.append("#!/bin/bash")
            undo_commands.append(f"# Undo script for transaction {transaction_id}")
            undo_commands.append(f"# Generated: {datetime.now().isoformat()}")
            undo_commands.append("")
            
            for op in log_data['operations']:
                if op['status'] == 'completed':
                    # Reverse: target -> original
                    target = op['target_path']
                    original = op['original_path']
                    undo_commands.append(f'mv "{target}" "{original}"')
            
            # Write script
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write('\n'.join(undo_commands))
            
            # Make executable (Unix)
            try:
                output_file.chmod(0o755)
            except Exception:
                pass
            
            self.logger.info(f"Undo script generated: {output_file}")
            return True
        
        except Exception as e:
            self.logger.error(f"Error generating undo script: {e}")
            return False


class PerformanceLogger:
    """
    Performance monitoring for optimization.
    """
    
    def __init__(self):
        """Initialize performance logger."""
        self.metrics: Dict[str, List[float]] = {}
    
    def record_metric(self, name: str, value: float) -> None:
        """Record performance metric."""
        if name not in self.metrics:
            self.metrics[name] = []
        self.metrics[name].append(value)
    
    def get_average(self, name: str) -> Optional[float]:
        """Get average for metric."""
        if name not in self.metrics or not self.metrics[name]:
            return None
        return sum(self.metrics[name]) / len(self.metrics[name])
    
    def get_summary(self) -> Dict[str, Dict[str, float]]:
        """Get summary statistics for all metrics."""
        summary = {}
        
        for name, values in self.metrics.items():
            if not values:
                continue
            
            summary[name] = {
                'count': len(values),
                'avg': sum(values) / len(values),
                'min': min(values),
                'max': max(values)
            }
        
        return summary
