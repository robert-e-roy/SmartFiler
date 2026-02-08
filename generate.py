#!/usr/bin/env python3
"""
Generate file organizer config from existing directory structure
"""
import json
from pathlib import Path
from collections import defaultdict
import argparse
import re


def analyze_directory(directory_path):
    """Scan directory and build config based on existing organization."""
    directory = Path(directory_path)
    
    if not directory.exists() or not directory.is_dir():
        print(f"Error: {directory_path} is not a valid directory")
        return None
    
    # Track extensions and filenames by folder
    folder_data = defaultdict(lambda: {'extensions': set(), 'filenames': []})
    
    # Walk the directory (non-recursive by default)
    for item in directory.iterdir():
        if item.is_dir():
            # This is a category folder
            folder_name = item.name
            
            # Skip hidden folders
            if folder_name.startswith('.'):
                continue
            
            # Scan files in this folder
            for file_path in item.iterdir():
                if file_path.is_file() and not file_path.name.startswith('.'):
                    ext = file_path.suffix.lower()
                    if ext:
                        folder_data[folder_name]['extensions'].add(ext)
                    folder_data[folder_name]['filenames'].append(file_path.name)
    
    return folder_data


def detect_patterns(filenames):
    """Try to detect common filename patterns."""
    patterns = []
    
    # Common pattern indicators
    pattern_checks = [
        (r'^Screenshot', 'Screenshot*'),
        (r'^Screen Shot', 'Screen Shot*'),
        (r'IMG_\d+', 'IMG_*'),
        (r'DSC\d+', 'DSC*'),
        (r'^download', 'download*'),
        (r'^\d{4}-\d{2}-\d{2}', '*'),  # Date pattern
        (r'_\d+x\d+', '*_*x*'),  # Resolution pattern
        (r'^temp', 'temp*'),
        (r'^tmp', 'tmp*'),
        (r'backup', '*backup*'),
        (r'draft', '*draft*'),
        (r'final', '*final*'),
        (r'copy', '*copy*'),
    ]
    
    # Check filenames for common patterns
    for regex, pattern in pattern_checks:
        matches = sum(1 for name in filenames if re.search(regex, name, re.IGNORECASE))
        # If more than 30% of files match, add the pattern
        if matches > len(filenames) * 0.3:
            if pattern not in patterns:
                patterns.append(pattern)
    
    return patterns


def generate_config(source_dir, output_file=None):
    """Generate config file from directory structure."""
    folder_data = analyze_directory(source_dir)
    
    if not folder_data:
        return None
    
    source_path = Path(source_dir).resolve()
    # Build config structure
    config = {
        "categories": {},
        "rules": {
            "ignore_hidden": True,
            "ignore_system": True,
            "create_subdirs_by_date": False,
            "dry_run": False,
            "target_directory": str(source_path)
        }
    }
    
    print(f"Analyzing directory: {source_dir}")
    print("=" * 60)
    
    for folder, data in sorted(folder_data.items()):
        extensions = sorted(list(data['extensions']))
        patterns = detect_patterns(data['filenames'])
        
        # Determine match mode
        if extensions and patterns:
            match_mode = "either"
        elif extensions:
            match_mode = "extension"
        elif patterns:
            match_mode = "pattern"
        else:
            continue  # Skip empty folders
        
        config["categories"][folder.lower()] = {
            "extensions": extensions,
            "patterns": patterns,
            "match_mode": match_mode,
            "destination": folder
        }
        
        # Print summary
        print(f"\n{folder}:")
        print(f"  Extensions: {', '.join(extensions) if extensions else 'none'}")
        print(f"  Patterns: {', '.join(patterns) if patterns else 'none'}")
        print(f"  Match mode: {match_mode}")
        print(f"  Files analyzed: {len(data['filenames'])}")
    
    # Save config
    if output_file is None:
        config_dir = Path.home() / '.config' / 'file-organizer'
        config_dir.mkdir(parents=True, exist_ok=True)
        output_file = config_dir / 'config.json'
    
    with open(output_file, 'w') as f:
        json.dump(config, f, indent=2)
    
    print("\n" + "=" * 60)
    print(f"Config generated with {len(config['categories'])} categories")
    print(f"Saved to: {output_file}")
    print("\nYou can now edit this config using config_editor.py")
    
    return config


def main():
    parser = argparse.ArgumentParser(
        description='Generate file organizer config from existing directory structure'
    )
    parser.add_argument(
        'directory',
        help='Directory to analyze (should contain categorized subfolders)'
    )
    parser.add_argument(
        '-o', '--output',
        help='Output config file (default: ~/.config/file-organizer/config.json)'
    )
    parser.add_argument(
        '-p', '--preview',
        action='store_true',
        help='Preview only, do not save config'
    )
    
    args = parser.parse_args()
    
    if args.preview:
        folder_data = analyze_directory(args.directory)
        if folder_data:
            print(f"\nPreview of directory structure in: {args.directory}")
            print("=" * 60)
            for folder, data in sorted(folder_data.items()):
                print(f"\n{folder}:")
                print(f"  Extensions: {sorted(data['extensions'])}")
                patterns = detect_patterns(data['filenames'])
                print(f"  Detected patterns: {patterns}")
                print(f"  Sample files: {data['filenames'][:3]}")
    else:
        generate_config(args.directory, args.output)


if __name__ == "__main__":
    main()
