#!/usr/bin/env python3
"""
File organizer - moves files based on config rules
"""
import json
import fnmatch
import shutil
from pathlib import Path
from datetime import datetime
import argparse


class FileOrganizer:
    def __init__(self, config_path=None):
        """Initialize with config file."""
        if config_path is None:
            config_dir = Path.home() / '.config' / 'file-organizer'
            config_path = config_dir / 'config.json'
        
        self.config_path = Path(config_path)
        self.config = self.load_config()
        self.stats = {
            'processed': 0,
            'moved': 0,
            'skipped': 0,
            'errors': 0
        }
    
    def load_config(self):
        """Load configuration from file."""
        try:
            with open(self.config_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"Error: Config file not found at {self.config_path}")
            print("Run config_editor.py first to create a configuration.")
            exit(1)
    
    def matches_category(self, file_path, category_settings):
        """Check if file matches category rules."""
        ext = file_path.suffix.lower()
        filename = file_path.name
        
        extensions = category_settings.get('extensions', [])
        patterns = category_settings.get('patterns', [])
        match_mode = category_settings.get('match_mode', 'either')
        
        # Check extension match
        ext_match = ext in extensions if extensions else False
        
        # Check pattern match
        pattern_match = any(fnmatch.fnmatch(filename, pattern) 
                          for pattern in patterns) if patterns else False
        
        # Apply match mode logic
        if match_mode == 'both':
            return ext_match and pattern_match
        elif match_mode == 'either':
            return ext_match or pattern_match
        elif match_mode == 'extension':
            return ext_match
        elif match_mode == 'pattern':
            return pattern_match
        
        return False
    
    def categorize_file(self, file_path):
        """Determine category and destination for a file."""
        for category, settings in self.config['categories'].items():
            if self.matches_category(file_path, settings):
                return category, settings['destination']
        return None, None
    
    def should_ignore(self, file_path):
        """Check if file should be ignored based on rules."""
        rules = self.config.get('rules', {})
        
        # Ignore hidden files
        if rules.get('ignore_hidden', True) and file_path.name.startswith('.'):
            return True
        
        # Ignore system files
        if rules.get('ignore_system', True):
            system_files = ['Thumbs.db', 'Desktop.ini', '.DS_Store']
            if file_path.name in system_files:
                return True
        
        return False
    
    def organize_file(self, file_path, base_dir, dry_run=False):
        """Move file to appropriate destination."""
        if self.should_ignore(file_path):
            self.stats['skipped'] += 1
            return None
        
        category, dest_folder = self.categorize_file(file_path)
        
        if category is None:
            self.stats['skipped'] += 1
            return None
        
        # Build destination path
        dest_dir = base_dir / dest_folder
        
        # Optionally create date-based subdirectories
        if self.config.get('rules', {}).get('create_subdirs_by_date', False):
            file_date = datetime.fromtimestamp(file_path.stat().st_mtime)
            date_folder = file_date.strftime('%Y-%m')
            dest_dir = dest_dir / date_folder
        
        # Create destination directory
        if not dry_run:
            dest_dir.mkdir(parents=True, exist_ok=True)
        
        # Handle filename conflicts
        dest_path = dest_dir / file_path.name
        counter = 1
        while dest_path.exists() and dest_path != file_path:
            stem = file_path.stem
            suffix = file_path.suffix
            dest_path = dest_dir / f"{stem}_{counter}{suffix}"
            counter += 1
        
        # Move the file
        if dry_run:
            print(f"[DRY RUN] Would move: {file_path} -> {dest_path}")
        else:
            try:
                shutil.move(str(file_path), str(dest_path))
                print(f"Moved: {file_path.name} -> {dest_folder}/")
                self.stats['moved'] += 1
            except Exception as e:
                print(f"Error moving {file_path}: {e}")
                self.stats['errors'] += 1
                return None
        
        return dest_path
    
    def organize_directory(self, source_dir, recursive=False, dry_run=False):
        """Organize all files in a directory."""
        source_path = Path(source_dir).resolve()
        
        if not source_path.exists():
            print(f"Error: Directory {source_path} does not exist")
            return
        
        print(f"Organizing files in: {source_path}")
        print(f"Dry run: {dry_run}")
        print("-" * 60)
        
        # Get files to process
        if recursive:
            files = [f for f in source_path.rglob('*') if f.is_file()]
        else:
            files = [f for f in source_path.iterdir() if f.is_file()]
        
        # Process each file
        for file_path in files:
            self.stats['processed'] += 1
            self.organize_file(file_path, source_path, dry_run)
        
        # Print summary
        print("-" * 60)
        print(f"Summary:")
        print(f"  Processed: {self.stats['processed']}")
        print(f"  Moved: {self.stats['moved']}")
        print(f"  Skipped: {self.stats['skipped']}")
        print(f"  Errors: {self.stats['errors']}")


def main():
    parser = argparse.ArgumentParser(
        description='Organize files based on configured rules'
    )
    parser.add_argument(
        'directory',
        nargs='?',
        default=None,
        help='Directory to organize (default: target_directory from config)'
    )
    parser.add_argument(
        '-r', '--recursive',
        action='store_true',
        help='Process subdirectories recursively'
    )
    parser.add_argument(
        '-d', '--dry-run',
        action='store_true',
        help='Show what would be done without actually moving files'
    )
    parser.add_argument(
        '-c', '--config',
        help='Path to config file (default: ~/.config/file-organizer/config.json)'
    )
    
    args = parser.parse_args()
    
    organizer = FileOrganizer(config_path=args.config)
    directory = args.directory
    if directory is None:
        directory = organizer.config.get('rules', {}).get('target_directory', '')
        if not directory:
            print("Error: No directory specified and no target_directory in config.")
            print("Run: file_organizer.py <directory>")
            print("Or set target_directory in config_editor.py or via generate.py")
            exit(1)
    
    organizer.organize_directory(
        directory,
        recursive=args.recursive,
        dry_run=args.dry_run
    )


if __name__ == "__main__":
    main()
