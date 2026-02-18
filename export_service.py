"""
Export service for preview and analysis.

Exports rename plans to CSV for:
- User review before execution
- Audit trails
- Data analysis
"""

import csv
from pathlib import Path
from typing import List
from datetime import datetime

from models import EpisodeMetadata, RenameOperation, RenameTransaction


class ExportService:
    """
    Export service for rename data.
    
    Provides CSV export for preview and documentation.
    """
    
    @staticmethod
    def export_metadata_preview(metadata_list: List[EpisodeMetadata],
                                output_file: Path) -> bool:
        """
        Export metadata extraction preview to CSV.
        
        Shows what was extracted from each filename.
        
        Args:
            metadata_list: List of metadata
            output_file: Output CSV path
        
        Returns:
            True if successful
        """
        try:
            with open(output_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                
                # Header
                writer.writerow([
                    'Original Filename',
                    'Extracted Number',
                    'Season',
                    'Episode',
                    'Confidence',
                    'Extraction Method',
                    'Cleaned Title'
                ])
                
                # Data rows
                for meta in metadata_list:
                    writer.writerow([
                        meta.original_name,
                        meta.extracted_number or '',
                        meta.season or '',
                        meta.episode or '',
                        f"{meta.confidence:.2f}",
                        meta.extraction_method,
                        meta.cleaned_title
                    ])
            
            return True
        
        except Exception as e:
            print(f"Export error: {e}")
            return False
    
    @staticmethod
    def export_rename_plan(transaction: RenameTransaction,
                          output_file: Path) -> bool:
        """
        Export complete rename plan to CSV.
        
        Shows before/after for user review.
        
        Args:
            transaction: Rename transaction
            output_file: Output CSV path
        
        Returns:
            True if successful
        """
        try:
            with open(output_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                
                # Header
                writer.writerow([
                    'Original Filename',
                    'New Filename',
                    'Directory',
                    'Number',
                    'Confidence',
                    'Status'
                ])
                
                # Data rows
                for op in transaction.operations:
                    writer.writerow([
                        op.original_path.name,
                        op.target_name,
                        str(op.original_path.parent),
                        op.metadata.extracted_number or '',
                        f"{op.metadata.confidence:.2f}",
                        op.status.value
                    ])
            
            return True
        
        except Exception as e:
            print(f"Export error: {e}")
            return False
    
    @staticmethod
    def export_comparison(operations: List[RenameOperation],
                         output_file: Path) -> bool:
        """
        Export side-by-side comparison.
        
        Simpler format for quick review.
        
        Args:
            operations: List of rename operations
            output_file: Output CSV path
        
        Returns:
            True if successful
        """
        try:
            with open(output_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                
                # Header
                writer.writerow(['Before', 'After'])
                
                # Data rows
                for op in operations:
                    writer.writerow([
                        op.original_path.name,
                        op.target_name
                    ])
            
            return True
        
        except Exception as e:
            print(f"Export error: {e}")
            return False
    
    @staticmethod
    def generate_report(transaction: RenameTransaction,
                       output_file: Path,
                       include_stats: bool = True) -> bool:
        """
        Generate comprehensive report with statistics.
        
        Args:
            transaction: Completed transaction
            output_file: Output text file path
            include_stats: Include statistics section
        
        Returns:
            True if successful
        """
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write("=" * 70 + "\n")
                f.write("PLAYLIST RENAMER PRO - OPERATION REPORT\n")
                f.write("=" * 70 + "\n\n")
                
                f.write(f"Transaction ID: {transaction.transaction_id}\n")
                f.write(f"Generated: {datetime.now():%Y-%m-%d %H:%M:%S}\n\n")
                
                if include_stats:
                    # Statistics
                    total = len(transaction.operations)
                    completed = sum(1 for op in transaction.operations 
                                  if op.status.value == 'completed')
                    failed = sum(1 for op in transaction.operations 
                               if op.status.value == 'failed')
                    
                    f.write("STATISTICS\n")
                    f.write("-" * 70 + "\n")
                    f.write(f"Total Operations: {total}\n")
                    f.write(f"Completed: {completed}\n")
                    f.write(f"Failed: {failed}\n")
                    f.write(f"Success Rate: {completed/total*100:.1f}%\n\n")
                
                # Operations
                f.write("OPERATIONS\n")
                f.write("-" * 70 + "\n\n")
                
                for i, op in enumerate(transaction.operations, 1):
                    f.write(f"{i}. {op.status.value.upper()}\n")
                    f.write(f"   From: {op.original_path.name}\n")
                    f.write(f"   To:   {op.target_name}\n")
                    
                    if op.error_message:
                        f.write(f"   Error: {op.error_message}\n")
                    
                    f.write("\n")
            
            return True
        
        except Exception as e:
            print(f"Report generation error: {e}")
            return False
