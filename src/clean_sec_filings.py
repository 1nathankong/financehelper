#!/usr/bin/env python3
"""
SEC Filing Text Cleaner

This script processes raw SEC filing text files and removes unnecessary
information before vectorization, including:
- Structured metadata (URLs, IDs, dates)
- Headers with page numbers
- Legal boilerplate sections
- Footnote markers and short formatting lines
- Empty lines and whitespace
"""

import re
import os
from pathlib import Path
from typing import List, Tuple


class SECFilingCleaner:
    """Cleans SEC filing text files for vector database preparation."""
    
    def __init__(self):
        # Patterns to identify content to remove
        self.url_pattern = re.compile(r'^https?://[^\s]+$')
        self.metadata_pattern = re.compile(r'^(iso4217:|xbrli:|us-gaap:|[a-z]+:[A-Z]|P\d+[YDM]|false|FY|\d{10})$')
        self.company_prefix_pattern = re.compile(r'^[a-z]+:[A-Za-z0-9]+.*$')
        self.header_pattern = re.compile(r'^.+\s\|\s\d{4}\sForm\s10-K\s\|\s\d+$')
        self.date_pattern = re.compile(r'^\d{4}-\d{2}-\d{2}$')
        self.company_id_pattern = re.compile(r'^\d{10}$')
        self.arrow_line_pattern = re.compile(r'^.*→.*$')
        self.short_line_pattern = re.compile(r'^.{1,3}$')
        self.footnote_pattern = re.compile(r'^\([0-9]+\)$|^\*+$')
        
        # Legal/administrative sections to remove
        self.legal_sections = [
            'SIGNATURES',
            'Power of Attorney',
            'KNOW ALL PERSONS BY THESE PRESENTS',
            'Pursuant to the requirements',
            'Filed herewith',
            'Furnished herewith',
            'Indicates management contract',
            'Item 16.    Form 10-K Summary'
        ]
    
    def is_metadata_line(self, line: str) -> bool:
        """Check if line is metadata that should be removed."""
        line = line.strip()
        
        # Skip empty lines
        if not line:
            return True
            
        # Remove URL lines
        if self.url_pattern.match(line):
            return True
            
        # Remove structured metadata
        if self.metadata_pattern.match(line):
            return True
            
        # Remove company prefix patterns (e.g., "aapl:", "tsla:", "us-gaap:")
        if self.company_prefix_pattern.match(line):
            return True
            
        # Remove lines that are exactly "Member" or end with "Member"
        if line == "Member" or line.endswith("Member"):
            return True
            
        # Remove headers with page numbers
        if self.header_pattern.match(line):
            return True
            
        # Remove date lines
        if self.date_pattern.match(line):
            return True
            
        # Remove company ID lines
        if self.company_id_pattern.match(line):
            return True
            
        # Remove arrow formatting lines
        if self.arrow_line_pattern.match(line):
            return True
            
        # Remove very short lines (likely formatting)
        if self.short_line_pattern.match(line):
            return True
            
        # Remove footnote markers
        if self.footnote_pattern.match(line):
            return True
            
        return False
    
    def is_legal_section(self, line: str) -> bool:
        """Check if line starts a legal/administrative section."""
        line = line.strip()
        return any(section in line for section in self.legal_sections)
    
    def clean_text(self, text: str) -> str:
        """Clean the raw SEC filing text."""
        lines = text.split('\n')
        cleaned_lines = []
        skip_legal_section = False
        
        for i, line in enumerate(lines):
            # Check if we're in a legal section
            if self.is_legal_section(line):
                skip_legal_section = True
                continue
                
            # Skip if in legal section
            if skip_legal_section:
                continue
                
            # Skip metadata lines
            if self.is_metadata_line(line):
                continue
                
            # Clean the line
            cleaned_line = line.strip()
            
            # Skip if line becomes empty after cleaning
            if not cleaned_line:
                continue
                
            # Remove line numbers at the beginning (e.g., "1000→")
            cleaned_line = re.sub(r'^\s*\d+→', '', cleaned_line)
            
            # Skip if line becomes empty after removing line numbers
            if not cleaned_line.strip():
                continue
                
            cleaned_lines.append(cleaned_line.strip())
        
        # Join lines and clean up extra whitespace
        cleaned_text = '\n'.join(cleaned_lines)
        
        # Remove multiple consecutive newlines
        cleaned_text = re.sub(r'\n{3,}', '\n\n', cleaned_text)
        
        # Remove excessive whitespace
        cleaned_text = re.sub(r' {2,}', ' ', cleaned_text)
        
        return cleaned_text.strip()
    
    def process_file(self, input_path: str, output_path: str) -> Tuple[int, int]:
        """Process a single SEC filing file."""
        try:
            with open(input_path, 'r', encoding='utf-8') as f:
                raw_text = f.read()
            
            original_lines = len(raw_text.split('\n'))
            cleaned_text = self.clean_text(raw_text)
            cleaned_lines = len(cleaned_text.split('\n'))
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(cleaned_text)
                
            return original_lines, cleaned_lines
            
        except Exception as e:
            print(f"Error processing {input_path}: {e}")
            return 0, 0
    
    def process_directory(self, input_dir: str, output_dir: str) -> None:
        """Process all text files in a directory."""
        input_path = Path(input_dir)
        output_path = Path(output_dir)
        
        # Create output directory if it doesn't exist
        output_path.mkdir(parents=True, exist_ok=True)
        
        txt_files = list(input_path.glob('*.txt'))
        
        if not txt_files:
            print(f"No .txt files found in {input_dir}")
            return
            
        print(f"Processing {len(txt_files)} files...")
        
        total_original_lines = 0
        total_cleaned_lines = 0
        
        for txt_file in txt_files:
            output_file = output_path / f"cleaned_{txt_file.name}"
            print(f"Processing: {txt_file.name}")
            
            original, cleaned = self.process_file(str(txt_file), str(output_file))
            total_original_lines += original
            total_cleaned_lines += cleaned
            
            if original > 0:
                reduction_percent = ((original - cleaned) / original) * 100
                print(f"  {original} → {cleaned} lines ({reduction_percent:.1f}% reduction)")
        
        print(f"\nSummary:")
        print(f"Total original lines: {total_original_lines}")
        print(f"Total cleaned lines: {total_cleaned_lines}")
        if total_original_lines > 0:
            overall_reduction = ((total_original_lines - total_cleaned_lines) / total_original_lines) * 100
            print(f"Overall reduction: {overall_reduction:.1f}%")


def main():
    """Main function to run the SEC filing cleaner."""
    cleaner = SECFilingCleaner()
    
    # Default paths
    input_directory = "sec_txt"
    output_directory = "sec_txt_cleaned"
    
    # Check if input directory exists
    if not os.path.exists(input_directory):
        print(f"Input directory '{input_directory}' not found.")
        print("Please ensure your scraped SEC filing text files are in a 'sec_txt' directory.")
        return
    
    print("SEC Filing Text Cleaner")
    print("=" * 50)
    print(f"Input directory: {input_directory}")
    print(f"Output directory: {output_directory}")
    print()
    
    # Process all files
    cleaner.process_directory(input_directory, output_directory)
    
    print(f"\nCleaned files saved to: {output_directory}")
    print("Ready for vector database ingestion!")


if __name__ == "__main__":
    main()