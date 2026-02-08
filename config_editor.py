#!/usr/bin/env python3

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.widgets import Header, Footer, Button, Input, TextArea, Label, ListView, ListItem, Select
from textual.binding import Binding
import json
from pathlib import Path
import fnmatch

class ConfigEditor(App):
    """A Textual app to manage file organizer config with pattern matching."""
    
    CSS = """
    Screen {
        background: $surface;
    }
    
    #main-container {
        height: 100%;
        layout: horizontal;
    }
    
    #category-list {
        width: 38;
        height: 100%;
        border: solid $primary;
        padding: 1;
    }
    
    #category-list .reorder-row {
        height: 1fr;
    }
    
    #category-list ListView {
        width: 1fr;
        height: 100%;
    }
    
    #details-panel {
        width: 1fr;
        height: 100%;
        padding: 1;
    }
    
    #details-scroll {
        overflow-y: auto;
        scrollbar-size: 1 1;
        height: 1fr;
    }
    
    .input-group {
        height: auto;
        margin-bottom: 1;
    }
    
    .button-row {
        height: auto;
        margin-bottom: 1;
    }
    
    Button {
        margin-right: 1;
    }
    
    TextArea {
        height: auto;
        min-height: 2;
    }
    
    Select {
        margin-bottom: 1;
    }
    
    .reorder-row {
        width: 100%;
    }
    
    .reorder-row TextArea {
        width: 1fr;
    }
    
    .reorder-buttons {
        width: auto;
        margin-left: 1;
    }
    
    .reorder-buttons Button {
        min-width: 3;
        padding: 0 1;
        margin-bottom: 1;
    }
    """
    
    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("s", "save", "Save"),
        Binding("a", "add", "Add Category"),
        Binding("u", "update", "Update Category"),
        Binding("d", "delete", "Delete Category"),

    ]
    
    def __init__(self):
        super().__init__()
        
        # Use ~/.config/file-organizer/ for config storage
        config_dir = Path.home() / '.config' / 'file-organizer'
        config_dir.mkdir(parents=True, exist_ok=True)
        
        self.config_file = config_dir / 'config.json'
        self.config = self.load_config()
        self.current_category = None
        self.has_unsaved_changes = False  # Track unsaved changes
        self.loading_category = False  # ADD THIS FLAG


    def compose(self) -> ComposeResult:
        yield Header()
        
        with Container(id="main-container"):
            with Vertical(id="category-list"):
                yield Label("Categories", classes="section-title")
                with Horizontal(classes="reorder-row"):
                    yield ListView(id="categories")
                    with Vertical(classes="reorder-buttons"):
                        yield Button("↑", id="btn-cat-up")
                        yield Button("↓", id="btn-cat-down")
            
            with Vertical(id="details-panel"):
                yield Label("Category Details", classes="section-title")
                
                with Horizontal(classes="button-row"):
                    yield Button("Add New", id="btn-add", variant="success")
                    yield Button("Update", id="btn-update", variant="primary")
                    yield Button("Delete", id="btn-delete", variant="error")
                    yield Button("Save Config", id="btn-save", variant="success")
                    yield Button("Test File", id="btn-test", variant="default")
                    yield Button("Quit", id="btn-quit", variant="error")
                
                with Vertical(classes="input-group"):
                    yield Label("Target Directory (optional, base path for organized files):")
                    yield Input(placeholder="e.g. /Users/me/Downloads or leave empty", id="target-directory")
                
                with VerticalScroll(id="details-scroll"):
                    with Vertical(classes="input-group"):
                        yield Label("Category Name:")
                        yield Input(placeholder="e.g., screenshots", id="category-name")
                
                    with Vertical(classes="input-group"):
                        yield Label("Extensions (one per line, dot optional e.g. png or .png):")
                        with Horizontal(classes="reorder-row"):
                            yield TextArea(id="extensions", classes="text-area")
                            with Vertical(classes="reorder-buttons"):
                                yield Button("↑", id="btn-ext-up")
                                yield Button("↓", id="btn-ext-down")
                    
                    with Vertical(classes="input-group"):
                        yield Label("Filename Patterns (one per line, * for wildcard):")
                        with Horizontal(classes="reorder-row"):
                            yield TextArea(id="patterns", classes="text-area")
                            with Vertical(classes="reorder-buttons"):
                                yield Button("↑", id="btn-pat-up")
                                yield Button("↓", id="btn-pat-down")
                    
                    with Vertical(classes="input-group"):
                        yield Label("Match Mode:")
                        yield Select(
                            [
                                ("Extension AND Pattern (both must match)", "both"),
                                ("Extension OR Pattern (either can match)", "either"),
                                ("Extension Only", "extension"),
                                ("Pattern Only", "pattern"),
                            ],
                            id="match-mode",
                            value="either"
                        )
                    
                    with Vertical(classes="input-group"):
                        yield Label("Destination Folder:")
                        yield Input(placeholder="e.g., Screenshots", id="destination")

        
        yield Footer()
    
    def load_config(self):
        """Load config from file."""
        try:
            with open(self.config_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {
                "categories": {},
                "rules": {
                    "ignore_hidden": True,
                    "ignore_system": True,
                    "create_subdirs_by_date": False,
                    "dry_run": False,
                    "target_directory": ""
                }
            }
    
    def save_config(self):
        """Save config to file."""
        with open(self.config_file, 'w') as f:
            json.dump(self.config, f, indent=2)
    
    def on_mount(self) -> None:
        """Populate category list on startup."""
        self.refresh_category_list()
        # Load global target directory
        target = self.config.get('rules', {}).get('target_directory', '')
        self.query_one("#target-directory", Input).value = target or ''
        # Auto-select first category if any exist
        if len(self.config['categories']) > 0:
            first_category = list(self.config['categories'].keys())[0]
            self.load_category_details(first_category)
    
    def load_category_details(self, category_name):
        """Load category details into form fields."""
        self.loading_category = True  # SET FLAG BEFORE LOADING

        self.current_category = category_name
        category_data = self.config['categories'][category_name]

        self.query_one("#category-name", Input).value = category_name
        self.query_one("#destination", Input).value = category_data['destination']

        extensions_text = '\n'.join(category_data.get('extensions', []))
        self.query_one("#extensions", TextArea).text = extensions_text

        patterns_text = '\n'.join(category_data.get('patterns', []))
        self.query_one("#patterns", TextArea).text = patterns_text

        match_mode = category_data.get('match_mode', 'either')
        self.query_one("#match-mode", Select).value = match_mode

        self.has_unsaved_changes = False  # Reset when loading

    def on_input_changed(self, event) -> None:
        """Track when form fields change."""
        if not self.loading_category:  # ONLY TRACK IF NOT LOADING
            self.has_unsaved_changes = True


    def on_text_area_changed(self, event) -> None:
        """Track when text areas change."""
        if not self.loading_category:  # ONLY TRACK IF NOT LOADING
            self.has_unsaved_changes = True
        

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Handle category selection."""
        category_name = event.item.category_name
        self.load_category_details(category_name)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button clicks."""
        button_id = event.button.id
        
        if button_id == "btn-add":
            self.add_category()
        elif button_id == "btn-update":
            self.update_category()
        elif button_id == "btn-delete":
            self.delete_category()
        elif button_id == "btn-save":
            self.action_save()
        elif button_id == "btn-test":
            self.test_filename()
        elif button_id == "btn-quit":
            self.action_quit()
        elif button_id in ("btn-ext-up", "btn-ext-down", "btn-pat-up", "btn-pat-down"):
            text_area_id = "extensions" if "ext" in button_id else "patterns"
            direction = "up" if "up" in button_id else "down"
            self.move_line_in_text_area(text_area_id, direction)
        elif button_id in ("btn-cat-up", "btn-cat-down"):
            direction = "up" if "up" in button_id else "down"
            self.move_category(direction)

    def refresh_category_list(self):
        """Refresh the category list view (preserves config order)."""
        list_view = self.query_one("#categories", ListView)
        list_view.clear()
        
        category_order = list(self.config['categories'].keys())
        for category in category_order:
            item = ListItem(Label(category))
            item.category_name = category
            list_view.append(item)
        
        list_view.refresh()
        
        if self.current_category and self.current_category in self.config['categories']:
            try:
                index = category_order.index(self.current_category)
                list_view.index = index
            except (ValueError, IndexError):
                pass

    def add_category(self):
        """Add a new category."""
        name = self.query_one("#category-name", Input).value.strip()
        destination = self.query_one("#destination", Input).value.strip()
        extensions_text = self.query_one("#extensions", TextArea).text
        patterns_text = self.query_one("#patterns", TextArea).text
        match_mode = self.query_one("#match-mode", Select).value

        if not name:
            self.notify("Category name required", severity="error")
            return

        extensions = [ext.strip() for ext in extensions_text.split('\n') if ext.strip()]
        extensions = [ext.lower() if ext.startswith('.') else f'.{ext.lower()}' for ext in extensions]

        patterns = [p.strip() for p in patterns_text.split('\n') if p.strip()]

        self.config['categories'][name] = {
            "extensions": extensions,
            "patterns": patterns,
            "match_mode": match_mode,
            "destination": destination or name
        }

        self.save_config()
        self.has_unsaved_changes = False  # ADD THIS
        # Add to list and clear form for next entry

        self.refresh_category_list()
        self.clear_fields()
        self.current_category = None  # No category selected after add
        self.notify(f"Added category: {name}", severity="information")

        self.clear_fields()  # ADD THIS - clear form after adding

        self.notify(f"Added category: {name}", severity="information")

    def delete_category(self):
        """Delete current category."""
        if not self.current_category:
            self.notify("Select a category first", severity="warning")
            return

        del self.config['categories'][self.current_category]
        self.save_config()
        self.has_unsaved_changes = False  # ADD THIS
        self.refresh_category_list()
        self.notify(f"Deleted category: {self.current_category}", severity="information")
        self.clear_fields()
        self.current_category = None

    def update_category(self):
        """Update existing category."""
        if not self.current_category:
            self.notify("Select a category first", severity="warning")
            return

        name = self.query_one("#category-name", Input).value.strip()
        destination = self.query_one("#destination", Input).value.strip()
        extensions_text = self.query_one("#extensions", TextArea).text
        patterns_text = self.query_one("#patterns", TextArea).text
        match_mode = self.query_one("#match-mode", Select).value

        extensions = [ext.strip() for ext in extensions_text.split('\n') if ext.strip()]
        extensions = [ext.lower() if ext.startswith('.') else f'.{ext.lower()}' for ext in extensions]

        patterns = [p.strip() for p in patterns_text.split('\n') if p.strip()]

        if name != self.current_category:
            del self.config['categories'][self.current_category]

        self.config['categories'][name] = {
        "extensions": extensions,
        "patterns": patterns,
        "match_mode": match_mode,
        "destination": destination or name
        }

        self.save_config()
        self.has_unsaved_changes = False  # Clear after saving
        self.current_category = name
        self.refresh_category_list()
        self.load_category_details(name)
        self.notify(f"Updated category: {name}", severity="information")
    
    def test_filename(self):
        """Test a filename against current category rules."""
        from textual.screen import ModalScreen
        from textual.widgets import Static
        from textual.work import work
        
        class TestDialog(ModalScreen):
            def compose(self) -> ComposeResult:
                with Vertical():
                    yield Label("Test Filename")
                    with Horizontal():
                        yield Input(placeholder="Enter filename or path", id="test-input")
                        yield Button("Browse", id="btn-browse", variant="default")
                    yield Button("Test", id="btn-test-now", variant="primary")
                    yield Static("", id="test-result")
                    yield Button("Close", id="btn-close")
            
            def on_button_pressed(self, event: Button.Pressed):
                if event.button.id == "btn-test-now":
                    filename = self.query_one("#test-input", Input).value
                    result = self.app.match_file(filename)
                    self.query_one("#test-result", Static).update(result)
                elif event.button.id == "btn-close":
                    self.app.pop_screen()
                elif event.button.id == "btn-browse":
                    self.browse_file()
            
            @work(exclusive=True)
            async def browse_file(self):
                from textual_fspicker import FileOpen
                if path := await self.push_screen_wait(FileOpen()):
                    self.query_one("#test-input", Input).value = str(path)
        
        self.push_screen(TestDialog())
    
    def match_file(self, filename):
        """Test if filename matches any category."""
        file_path = Path(filename)
        ext = file_path.suffix.lower()
        name = file_path.name
        
        matches = []
        
        for category, settings in self.config['categories'].items():
            ext_match = ext in settings.get('extensions', [])
            pattern_match = any(fnmatch.fnmatch(name, pattern) 
                              for pattern in settings.get('patterns', []))
            
            match_mode = settings.get('match_mode', 'either')
            
            matched = False
            if match_mode == 'both':
                matched = ext_match and pattern_match
            elif match_mode == 'either':
                matched = ext_match or pattern_match
            elif match_mode == 'extension':
                matched = ext_match
            elif match_mode == 'pattern':
                matched = pattern_match
            
            if matched:
                matches.append(f"✓ {category} → {settings['destination']}")
        
        if matches:
            return "Matches:\n" + "\n".join(matches)
        else:
            return "No matches found"
    
    def move_category(self, direction: str) -> None:
        """Move the selected category up or down in the list."""
        if not self.current_category or self.current_category not in self.config['categories']:
            self.notify("Select a category first", severity="warning")
            return
        keys = list(self.config['categories'].keys())
        idx = keys.index(self.current_category)
        if direction == "up" and idx > 0:
            keys[idx], keys[idx - 1] = keys[idx - 1], keys[idx]
        elif direction == "down" and idx < len(keys) - 1:
            keys[idx], keys[idx + 1] = keys[idx + 1], keys[idx]
        else:
            return
        # Rebuild categories dict in new order
        ordered = {k: self.config['categories'][k] for k in keys}
        self.config['categories'] = ordered
        self.has_unsaved_changes = True
        self.refresh_category_list()

    def move_line_in_text_area(self, text_area_id: str, direction: str) -> None:
        """Move the line containing the cursor up or down in the given TextArea."""
        text_area = self.query_one(f"#{text_area_id}", TextArea)
        lines = text_area.text.split('\n')
        if not lines:
            return
        row, _ = text_area.cursor_location
        row = min(row, len(lines) - 1)
        if direction == "up" and row > 0:
            lines[row], lines[row - 1] = lines[row - 1], lines[row]
            new_row = row - 1
        elif direction == "down" and row < len(lines) - 1:
            lines[row], lines[row + 1] = lines[row + 1], lines[row]
            new_row = row + 1
        else:
            return
        self.loading_category = True
        text_area.text = '\n'.join(lines)
        text_area.cursor_location = (new_row, min(text_area.cursor_location[1], len(lines[new_row])))
        self.loading_category = False
        self.has_unsaved_changes = True

    def clear_fields(self):
        """Clear input fields."""
        self.query_one("#category-name", Input).value = ""
        self.query_one("#destination", Input).value = ""
        self.query_one("#extensions", TextArea).text = ""
        self.query_one("#patterns", TextArea).text = ""
        self.query_one("#match-mode", Select).value = "either"
    
    def action_delete(self):
        """Delete category via keybinding."""
        self.delete_category()
    
    def action_save(self):
        """Save config file."""
        target = self.query_one("#target-directory", Input).value.strip()
        if 'rules' not in self.config:
            self.config['rules'] = {}
        self.config['rules']['target_directory'] = target
        self.save_config()
        self.notify(f"Config saved to {self.config_file}", severity="information")
    
    def action_quit(self):
        """Quit the app."""
        if self.has_unsaved_changes:
            self.notify("You have unsaved changes! Press 'q' again to quit anyway.", severity="warning")
            self.has_unsaved_changes = False  # Clear flag so next 'q' will quit
        else:
            self.exit()

    def action_update(self):
        """Update category via keybinding."""
        self.update_category()
    
    def action_add(self):
        """Add new category via keybinding."""
        self.add_category()


if __name__ == "__main__":
    app = ConfigEditor()
    app.run()
