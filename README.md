# SmartFiler

A flexible file organizer that automatically sorts files into folders based on configurable rules. Define categories by file extension and filename patterns, then let SmartFiler move files into the right place.

## Features

- **Rule-based organization** — Match files by extension, filename pattern, or both
- **Config generator** — Build config from an existing directory structure
- **Interactive config editor** — TUI app to create and edit categories
- **Dry run mode** — Preview changes before applying them
- **Recursive support** — Organize nested directories
- **Conflict handling** — Automatic renaming when destination files exist

## Quick Start

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Create your config

**Option A:** Generate from an existing folder structure

```bash
python generate.py /path/to/your/organized/folder
```

**Option B:** Create and edit manually with the config editor

```bash
python config_editor.py
# Use specific config
python config_editor.py -c /path/to/my-config.json

# Or use 'o' key or button to browse for config files
```

### 3. Organize files

```bash
# Preview what would happen (dry run)
python file_organizer.py /path/to/messy/folder --dry-run

# Actually organize
python file_organizer.py /path/to/messy/folder

# Include subdirectories
python file_organizer.py /path/to/folder -r
```

## Components

| Script | Description |
|--------|-------------|
| `file_organizer.py` | Moves files based on config rules |
| `config_editor.py` | Interactive TUI to manage categories |
| `generate.py` | Generates config from existing directory structure |

## Configuration

Config is stored at `~/.config/file-organizer/config.json`.

### Category structure

Each category can include:

- **Extensions** — e.g. `.png`, `.jpg`, `.pdf`
- **Patterns** — fnmatch patterns, e.g. `Screenshot*`, `IMG_*`
- **Match mode** — `extension`, `pattern`, `either`, or `both`
- **Destination** — Target folder name (relative to source directory)

### Global rules

- `ignore_hidden` — Skip files starting with `.`
- `ignore_system` — Skip Thumbs.db, Desktop.ini, .DS_Store
- `create_subdirs_by_date` — Create `YYYY-MM` subfolders in each destination

## Usage examples

```bash
# Use a custom config file
python file_organizer.py ~/Downloads -c /path/to/config.json

# Dry run to see what would be moved
python file_organizer.py ~/Downloads -d

# Preview generated config without saving
python generate.py ~/Documents -p
```

## Keyboard shortcuts (config editor)

| Key | Action |
|-----|--------|
| `q` | Quit |
| `s` | Save |
| `a` | Add category |
| `u` | Update category |
| `d` | Delete category |

## License

GNU General Public License v3 — see [LICENSE](LICENSE) for details.
