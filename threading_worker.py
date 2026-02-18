"""
Background worker thread for long-running operations.

Keeps UI responsive during:
- Directory scanning
- Transaction execution
- Export operations
"""

import threading
import queue
from typing import Callable, Any, Optional
from enum import Enum


class WorkerStatus(Enum):
    """Worker thread status."""
    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class WorkerResult:
    """Result from worker thread."""
    
    def __init__(self, success: bool, data: Any = None, error: Optional[str] = None):
        self.success = success
        self.data = data
        self.error = error


class BackgroundWorker:
    """
    Background worker for long-running operations.
    
    Prevents UI freezing during intensive tasks.
    Supports cancellation and progress reporting.
    """
    
    def __init__(self):
        """Initialize worker."""
        self.thread: Optional[threading.Thread] = None
        self.status = WorkerStatus.IDLE
        self.cancel_flag = threading.Event()
        self.result_queue: queue.Queue = queue.Queue()
        self.progress_queue: queue.Queue = queue.Queue()
    
    def start(self, 
             target: Callable,
             args: tuple = (),
             on_complete: Optional[Callable[[WorkerResult], None]] = None,
             on_progress: Optional[Callable[[int, int, str], None]] = None) -> None:
        """
        Start background operation.
        
        Args:
            target: Function to run in background
            args: Arguments for target function
            on_complete: Callback when complete (called from main thread)
            on_progress: Progress callback (current, total, message)
        """
        if self.is_running():
            raise RuntimeError("Worker already running")
        
        self.status = WorkerStatus.RUNNING
        self.cancel_flag.clear()
        
        def worker_wrapper():
            """Wrapper that catches exceptions."""
            try:
                result_data = target(*args)
                result = WorkerResult(success=True, data=result_data)
                self.status = WorkerStatus.COMPLETED
            
            except Exception as e:
                result = WorkerResult(success=False, error=str(e))
                self.status = WorkerStatus.FAILED
            
            # Put result in queue
            self.result_queue.put(result)
            
            # Call completion callback if provided
            if on_complete:
                on_complete(result)
        
        # Store progress callback
        self._progress_callback = on_progress
        
        # Start thread
        self.thread = threading.Thread(target=worker_wrapper, daemon=True)
        self.thread.start()
    
    def is_running(self) -> bool:
        """Check if worker is currently running."""
        return self.status == WorkerStatus.RUNNING and self.thread and self.thread.is_alive()
    
    def cancel(self) -> None:
        """Request cancellation of current operation."""
        self.cancel_flag.set()
        self.status = WorkerStatus.CANCELLED
    
    def is_cancelled(self) -> bool:
        """Check if cancellation was requested."""
        return self.cancel_flag.is_set()
    
    def wait(self, timeout: Optional[float] = None) -> Optional[WorkerResult]:
        """
        Wait for worker to complete.
        
        Args:
            timeout: Maximum time to wait (None = indefinite)
        
        Returns:
            WorkerResult or None if timeout
        """
        if not self.thread:
            return None
        
        self.thread.join(timeout)
        
        # Get result if available
        try:
            return self.result_queue.get_nowait()
        except queue.Empty:
            return None
    
    def report_progress(self, current: int, total: int, message: str) -> None:
        """
        Report progress (called from worker thread).
        
        Args:
            current: Current item
            total: Total items
            message: Status message
        """
        # Put in queue for main thread to consume
        self.progress_queue.put((current, total, message))
        
        # Also call callback directly if in worker thread
        if hasattr(self, '_progress_callback') and self._progress_callback:
            try:
                self._progress_callback(current, total, message)
            except Exception:
                pass  # Ignore callback errors
    
    def get_progress(self) -> Optional[tuple[int, int, str]]:
        """
        Get latest progress update (called from main thread).
        
        Returns:
            (current, total, message) or None if no update
        """
        try:
            return self.progress_queue.get_nowait()
        except queue.Empty:
            return None


class WorkerPool:
    """
    Pool of background workers for concurrent operations.
    
    Currently single-threaded to avoid race conditions,
    but architecture supports expansion.
    """
    
    def __init__(self, max_workers: int = 1):
        """
        Initialize worker pool.
        
        Args:
            max_workers: Maximum concurrent workers (default 1 for safety)
        """
        self.max_workers = max_workers
        self.workers: list[BackgroundWorker] = []
    
    def submit(self,
              target: Callable,
              args: tuple = (),
              on_complete: Optional[Callable] = None,
              on_progress: Optional[Callable] = None) -> Optional[BackgroundWorker]:
        """
        Submit task to worker pool.
        
        Args:
            target: Function to execute
            args: Function arguments
            on_complete: Completion callback
            on_progress: Progress callback
        
        Returns:
            BackgroundWorker instance or None if pool full
        """
        # Clean up completed workers
        self.workers = [w for w in self.workers if w.is_running()]
        
        # Check if pool full
        if len(self.workers) >= self.max_workers:
            return None
        
        # Create new worker
        worker = BackgroundWorker()
        self.workers.append(worker)
        
        # Start task
        worker.start(target, args, on_complete, on_progress)
        
        return worker
    
    def cancel_all(self) -> None:
        """Cancel all running workers."""
        for worker in self.workers:
            if worker.is_running():
                worker.cancel()
    
    def wait_all(self, timeout: Optional[float] = None) -> None:
        """Wait for all workers to complete."""
        for worker in self.workers:
            worker.wait(timeout)
    
    def get_active_count(self) -> int:
        """Get number of active workers."""
        return sum(1 for w in self.workers if w.is_running())
