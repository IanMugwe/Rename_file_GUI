"""
Main GUI Application.

Production-grade desktop interface using Tkinter.
Features:
- Responsive UI (non-blocking operations)
- Progress tracking
- Real-time preview
- Conflict warnings
- Export capabilities
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
from typing import Optional, List

from controller import ApplicationController, AppConfig
from threading_worker import BackgroundWorker, WorkerResult
from models import EpisodeMetadata, RenameTransaction


class PlaylistRenamerGUI:
    """
    Main application GUI.
    
    Implements:
    - Directory selection
    - Format customization
    - Preview table
    - Conflict detection
    - Background execution
    - Progress tracking
    """
    
    def __init__(self, root: tk.Tk):
        """
        Initialize GUI.
        
        Args:
            root: Tk root window
        """
        self.root = root
        self.root.title("Playlist Renamer Pro - Enterprise Edition")
        self.root.geometry("1200x800")
        
        # Application state
        self.controller = ApplicationController()
        self.worker = BackgroundWorker()
        self.current_metadata: List[EpisodeMetadata] = []
        self.current_transaction: Optional[RenameTransaction] = None
        
        # Build UI
        self._build_ui()
        
        # Start UI update loop
        self._start_update_loop()
    
    def _build_ui(self):
        """Build user interface."""
        # Main container
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(2, weight=1)
        
        # Top section: Directory and controls
        self._build_control_section(main_frame)
        
        # Middle section: Preview table
        self._build_preview_section(main_frame)
        
        # Bottom section: Actions and progress
        self._build_action_section(main_frame)
    
    def _build_control_section(self, parent):
        """Build directory and format controls."""
        control_frame = ttk.LabelFrame(parent, text="Configuration", padding="10")
        control_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        control_frame.columnconfigure(1, weight=1)
        
        # Directory selection
        ttk.Label(control_frame, text="Directory:").grid(row=0, column=0, sticky=tk.W)
        
        self.dir_entry = ttk.Entry(control_frame, width=60)
        self.dir_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=5)
        
        self.browse_btn = ttk.Button(control_frame, text="Browse...", 
                                     command=self._browse_directory)
        self.browse_btn.grid(row=0, column=2, padx=5)
        
        self.scan_btn = ttk.Button(control_frame, text="Scan", 
                                   command=self._scan_directory)
        self.scan_btn.grid(row=0, column=3)
        
        # Format string
        ttk.Label(control_frame, text="Format:").grid(row=1, column=0, sticky=tk.W, pady=(10, 0))
        
        self.format_entry = ttk.Entry(control_frame, width=60)
        self.format_entry.insert(0, "{number}. {title}")
        self.format_entry.grid(row=1, column=1, sticky=(tk.W, tk.E), padx=5, pady=(10, 0))
        
        # Format presets dropdown
        format_preset_frame = ttk.Frame(control_frame)
        format_preset_frame.grid(row=1, column=2, columnspan=2, pady=(10, 0))
        
        ttk.Label(format_preset_frame, text="Preset:").pack(side=tk.LEFT, padx=(0, 5))
        
        self.format_preset = ttk.Combobox(format_preset_frame, width=20, state='readonly')
        self.format_preset.pack(side=tk.LEFT)
        self.format_preset['values'] = (
            "{number}. {title}",
            "{number:02d}. {title}",
            "S{season}E{episode}. {title}",
            "{title} - {number}",
            "[{number}] {title}"
        )
        self.format_preset.bind('<<ComboboxSelected>>', self._apply_format_preset)
        
        # Options
        options_frame = ttk.Frame(control_frame)
        options_frame.grid(row=2, column=0, columnspan=4, sticky=tk.W, pady=(10, 0))
        
        self.recursive_var = tk.BooleanVar()
        self.recursive_check = ttk.Checkbutton(options_frame, text="Recursive scan",
                                               variable=self.recursive_var)
        self.recursive_check.pack(side=tk.LEFT, padx=(0, 20))
        
        # File type filter
        ttk.Label(options_frame, text="File type:").pack(side=tk.LEFT, padx=(0, 5))
        self.filetype_var = tk.StringVar(value="video")
        self.filetype_combo = ttk.Combobox(options_frame, width=10, state='readonly',
                                           textvariable=self.filetype_var)
        self.filetype_combo.pack(side=tk.LEFT, padx=(0, 20))
        self.filetype_combo['values'] = ("video", "audio", "documents", "all")
        
        self.dry_run_var = tk.BooleanVar()
        self.dry_run_check = ttk.Checkbutton(options_frame, text="Dry run (preview only)",
                                             variable=self.dry_run_var)
        self.dry_run_check.pack(side=tk.LEFT, padx=(0, 20))
        
        # Zero padding
        ttk.Label(options_frame, text="Zero padding:").pack(side=tk.LEFT, padx=(0, 5))
        self.padding_var = tk.IntVar(value=2)
        padding_spin = ttk.Spinbox(options_frame, from_=1, to=5, width=5,
                                   textvariable=self.padding_var)
        padding_spin.pack(side=tk.LEFT)
    
    def _build_preview_section(self, parent):
        """Build preview table."""
        preview_frame = ttk.LabelFrame(parent, text="Preview", padding="10")
        preview_frame.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        preview_frame.columnconfigure(0, weight=1)
        preview_frame.rowconfigure(0, weight=1)
        
        # Statistics bar
        self.stats_label = ttk.Label(preview_frame, text="No files loaded", 
                                     font=('TkDefaultFont', 9, 'italic'))
        self.stats_label.grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
        
        # Treeview with scrollbar
        tree_frame = ttk.Frame(preview_frame)
        tree_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        tree_frame.columnconfigure(0, weight=1)
        tree_frame.rowconfigure(0, weight=1)
        
        self.preview_tree = ttk.Treeview(tree_frame, 
                                        columns=('original', 'number', 'new_name', 'confidence'),
                                        show='headings',
                                        height=20)
        
        self.preview_tree.heading('original', text='Original Filename')
        self.preview_tree.heading('number', text='#')
        self.preview_tree.heading('new_name', text='New Filename')
        self.preview_tree.heading('confidence', text='Confidence')
        
        self.preview_tree.column('original', width=300)
        self.preview_tree.column('number', width=50, anchor='center')
        self.preview_tree.column('new_name', width=300)
        self.preview_tree.column('confidence', width=80, anchor='center')
        
        # Scrollbars
        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.preview_tree.yview)
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.preview_tree.xview)
        self.preview_tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        
        self.preview_tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        vsb.grid(row=0, column=1, sticky=(tk.N, tk.S))
        hsb.grid(row=1, column=0, sticky=(tk.W, tk.E))
    
    def _build_action_section(self, parent):
        """Build action buttons and progress."""
        action_frame = ttk.Frame(parent)
        action_frame.grid(row=3, column=0, sticky=(tk.W, tk.E))
        action_frame.columnconfigure(1, weight=1)
        
        # Buttons
        button_frame = ttk.Frame(action_frame)
        button_frame.grid(row=0, column=0, sticky=tk.W)
        
        self.preview_btn = ttk.Button(button_frame, text="Generate Preview",
                                      command=self._generate_preview, state='disabled')
        self.preview_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        self.export_btn = ttk.Button(button_frame, text="Export CSV",
                                     command=self._export_csv, state='disabled')
        self.export_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        self.rename_btn = ttk.Button(button_frame, text="Execute Rename",
                                     command=self._execute_rename, state='disabled')
        self.rename_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        self.cancel_btn = ttk.Button(button_frame, text="Cancel",
                                     command=self._cancel_operation, state='disabled')
        self.cancel_btn.pack(side=tk.LEFT)
        
        # Progress bar
        progress_frame = ttk.Frame(action_frame)
        progress_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(10, 0))
        progress_frame.columnconfigure(0, weight=1)
        
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(progress_frame, mode='determinate',
                                           variable=self.progress_var)
        self.progress_bar.grid(row=0, column=0, sticky=(tk.W, tk.E))
        
        self.progress_label = ttk.Label(progress_frame, text="Ready")
        self.progress_label.grid(row=1, column=0, sticky=tk.W, pady=(5, 0))
    
    def _browse_directory(self):
        """Browse for directory."""
        directory = filedialog.askdirectory(title="Select Directory")
        if directory:
            self.dir_entry.delete(0, tk.END)
            self.dir_entry.insert(0, directory)
    
    def _scan_directory(self):
        """Scan directory in background."""
        directory = self.dir_entry.get()
        if not directory:
            messagebox.showwarning("Warning", "Please select a directory")
            return
        
        dir_path = Path(directory)
        if not self.controller.set_directory(dir_path):
            messagebox.showerror("Error", "Invalid directory")
            return
        
        # Update config
        self.controller.config.recursive_scan = self.recursive_var.get()
        self.controller.config.extension_filter = self.filetype_var.get()
        self.controller.scanner.recursive = self.recursive_var.get()
        
        # Update file type filter
        filetype = self.filetype_var.get()
        self.controller.scanner.set_extensions_from_preset(filetype)
        
        # Disable controls
        self._set_controls_enabled(False)
        self.progress_label.config(text="Scanning...")
        
        # Run in background
        def scan_task():
            return self.controller.scan_and_parse()
        
        def on_complete(result: WorkerResult):
            # Re-enable in main thread via update loop
            pass
        
        self.worker.start(scan_task, on_complete=on_complete)
    
    def _generate_preview(self):
        """Generate rename preview."""
        if not self.current_metadata:
            return
        
        format_str = self.format_entry.get()
        
        # Validate format
        is_valid, error = self.controller.validate_format_string(format_str)
        if not is_valid:
            messagebox.showerror("Format Error", error)
            return
        
        # Update config
        self.controller.config.format_string = format_str
        self.controller.config.zero_padding = self.padding_var.get()
        
        try:
            # Build transaction
            transaction = self.controller.build_transaction(format_str)
            self.current_transaction = transaction
            
            # Check conflicts
            conflicts = self.controller.detect_conflicts(transaction)
            
            if conflicts['has_conflicts']:
                self._show_conflicts(conflicts)
            
            # Update preview
            self._update_preview_table(transaction)
            
            # Enable execute button
            self.rename_btn.config(state='normal')
            self.export_btn.config(state='normal')
        
        except Exception as e:
            messagebox.showerror("Error", f"Preview generation failed: {e}")
    
    def _execute_rename(self):
        """Execute rename operation."""
        if not self.current_transaction:
            return
        
        # Confirm
        count = len(self.current_transaction.operations)
        mode = "DRY RUN" if self.dry_run_var.get() else "RENAME"
        
        if not messagebox.askyesno("Confirm", 
                                  f"{mode} {count} files?"):
            return
        
        # Update config
        self.controller.config.dry_run_mode = self.dry_run_var.get()
        
        # Disable controls
        self._set_controls_enabled(False)
        self.cancel_btn.config(state='normal')
        
        # Progress callback
        def progress_callback(current, total, message):
            self.worker.report_progress(current, total, message)
        
        # Execute in background
        def rename_task():
            return self.controller.execute_transaction(
                self.current_transaction,
                progress_callback
            )
        
        def on_complete(result: WorkerResult):
            pass  # Handled in update loop
        
        self.worker.start(rename_task, on_complete=on_complete)
    
    def _cancel_operation(self):
        """Cancel current operation."""
        self.worker.cancel()
        self.cancel_btn.config(state='disabled')
    
    def _export_csv(self):
        """Export preview to CSV."""
        if not self.current_transaction:
            return
        
        filename = filedialog.asksaveasfilename(
            title="Export Preview",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        
        if filename:
            success = self.controller.export_rename_plan(Path(filename))
            if success:
                messagebox.showinfo("Success", "Preview exported successfully")
            else:
                messagebox.showerror("Error", "Export failed")
    
    def _apply_format_preset(self, event=None):
        """Apply selected format preset."""
        preset = self.format_preset.get()
        if preset:
            self.format_entry.delete(0, tk.END)
            self.format_entry.insert(0, preset)
    
    def _update_preview_table(self, transaction: RenameTransaction):
        """Update preview table with transaction."""
        # Clear existing
        for item in self.preview_tree.get_children():
            self.preview_tree.delete(item)
        
        # Add items
        for op in transaction.operations:
            confidence_str = f"{op.metadata.confidence:.2f}"
            number = op.metadata.extracted_number or '?'
            
            self.preview_tree.insert('', 'end', values=(
                op.original_path.name,
                number,
                op.target_name,
                confidence_str
            ))
    
    def _show_conflicts(self, conflicts: dict):
        """Show conflict warnings."""
        warnings = []
        
        if conflicts['duplicate_targets']:
            count = len(conflicts['duplicate_targets'])
            warnings.append(f"• {count} duplicate target names detected")
        
        if conflicts['file_collisions']:
            count = len(conflicts['file_collisions'])
            warnings.append(f"• {count} files would overwrite existing files")
        
        if conflicts['number_gaps']:
            gaps = conflicts['number_gaps'][:5]  # Show first 5
            gaps_str = ', '.join(map(str, gaps))
            warnings.append(f"• Number gaps detected: {gaps_str}")
        
        if warnings:
            message = "⚠️ Conflicts Detected:\n\n" + "\n".join(warnings)
            message += "\n\nProceed with caution!"
            messagebox.showwarning("Conflicts Detected", message)
    
    def _update_statistics(self):
        """Update statistics label."""
        stats = self.controller.get_statistics()
        
        if stats['total_files'] == 0:
            self.stats_label.config(text="No files loaded")
        else:
            text = (f"Files: {stats['total_files']} | "
                   f"With numbers: {stats['with_numbers']} | "
                   f"Avg confidence: {stats['avg_confidence']:.2f}")
            self.stats_label.config(text=text)
    
    def _set_controls_enabled(self, enabled: bool):
        """Enable/disable controls."""
        state = 'normal' if enabled else 'disabled'
        
        self.browse_btn.config(state=state)
        self.scan_btn.config(state=state)
        self.preview_btn.config(state=state)
        self.rename_btn.config(state=state)
        self.export_btn.config(state=state)
        self.format_entry.config(state=state)
        self.dir_entry.config(state=state)
    
    def _start_update_loop(self):
        """Start UI update loop for background tasks."""
        self._update_from_worker()
        self.root.after(100, self._start_update_loop)
    
    def _update_from_worker(self):
        """Update UI from worker thread (called from main thread)."""
        # Check for progress updates
        progress = self.worker.get_progress()
        if progress:
            current, total, message = progress
            if total > 0:
                percent = (current / total) * 100
                self.progress_var.set(percent)
            self.progress_label.config(text=message)
        
        # Check if worker completed
        if not self.worker.is_running() and self.worker.status.value != 'idle':
            result = self.worker.wait(timeout=0.01)
            
            if result:
                if result.success:
                    self._on_operation_success(result.data)
                else:
                    self._on_operation_failure(result.error)
                
                # Reset worker
                self.worker.status = self.worker.status.__class__.IDLE
                self.progress_var.set(0)
                self.progress_label.config(text="Ready")
                self._set_controls_enabled(True)
                self.cancel_btn.config(state='disabled')
    
    def _on_operation_success(self, data):
        """Handle successful operation."""
        if isinstance(data, tuple) and len(data) == 2:
            # Scan result
            metadata_list, errors = data
            
            if errors:
                messagebox.showerror("Scan Errors", "\n".join(errors))
                return
            
            self.current_metadata = metadata_list
            self._update_statistics()
            
            # Clear preview
            for item in self.preview_tree.get_children():
                self.preview_tree.delete(item)
            
            # Show basic list
            for meta in metadata_list:
                self.preview_tree.insert('', 'end', values=(
                    meta.original_name,
                    meta.extracted_number or '?',
                    '-',
                    f"{meta.confidence:.2f}"
                ))
            
            self.preview_btn.config(state='normal')
            messagebox.showinfo("Scan Complete", f"Found {len(metadata_list)} files")
        
        elif isinstance(data, bool):
            # Rename result
            if data:
                mode = "Dry run" if self.controller.config.dry_run_mode else "Rename"
                messagebox.showinfo("Success", f"{mode} completed successfully")
            else:
                messagebox.showwarning("Partial Failure", "Some operations failed")
    
    def _on_operation_failure(self, error: str):
        """Handle operation failure."""
        messagebox.showerror("Operation Failed", error)


def main():
    """Main entry point."""
    root = tk.Tk()
    app = PlaylistRenamerGUI(root)
    root.mainloop()


if __name__ == '__main__':
    main()
