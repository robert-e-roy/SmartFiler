#!/usr/bin/env python3
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Header, Footer, Button, Input, TextArea, Label, ListView, ListItem, Select, Static
from textual.binding import Binding
from textual_fspicker import SelectDirectory, FileOpen
import json
from pathlib import Path
import fnmatch
import argparse
import sys

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
            width: 30;
            height: 100%;
            border: solid $primary;
            padding: 1;
        }

        #details-panel {
            width: 1fr;
            height: 100%;
            padding: 1;
            overflow-y: auto;
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
            height: 4;
        }

        Select {
            margin-bottom: 1;
        }

        .target-dir {
            border: solid $accent;
            padding: 1;
            margin-bottom: 1;
            background: $boost;
        }

        .config-file-display {
            border: solid $primary;
            padding: 1;
            margin-bottom: 1;
        }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("s", "save", "Save"),
        Binding("a", "add", "Add Category"),
        Binding("u", "update", "Update Category"),
        Binding("d", "delete", "Delete Category"),
        Binding("t", "select_target", "Set Target Directory"),
        Binding("o", "open_config", "Open Config File"),
    ]

    def __init__(self, config_path=None):
        super().__init__()

        # Determine config file path
        if config_path:
            self.config_file = Path(config_path)
        else:
            config_dir = Path.home() / '.config' / 'file-organizer'
            config_dir.mkdir(parents=True, exist_ok=True)
            self.config_file = config_dir / 'config.json'

        self.config = self.load_config()
        self.current_category = None
        self.has_unsaved_changes = False
        self.loading_category = False

    def compose(self) -> ComposeResult:
        yield Header()

        with Container(id="main-container"):
            with Vertical(id="category-list"):
                yield Label("Categories", classes="section-title")
                yield ListView(id="categories")

            with Vertical(id="details-panel"):
                # Config file display
                with Vertical(classes="config-file-display"):
                    yield Label("Config File", classes="section-title")
                    yield Static(id="config-file-display", expand=False)
                    yield Button("Open Config File", id="btn-open-config", variant="default")

                # Buttons at the top
                with Horizontal(classes="button-row"):
                    yield Button("Add New", id="btn-add", variant="success")
                    yield Button("Update", id="btn-update", variant="primary")
                    yield Button("Delete", id="btn-delete", variant="error")
                    yield Button("Save Config", id="btn-save", variant="success")
                    yield Button("Test File", id="btn-test", variant="default")
                    yield Button("Quit", id="btn-quit", variant="error")

                # Target directory display
                with Vertical(classes="target-dir"):
                    yield Label("Target Directory", classes="section-title")
                    yield Static(id="target-display", expand=False)
                    yield Button("Set Target Directory", id="btn-target", variant="default")

                yield Label("Category Details", classes="section-title")

                with Vertical(classes="input-group"):
                    yield Label("Category Name:")
                    yield Input(placeholder="e.g., screenshots", id="category-name")

                with Vertical(classes="input-group"):
                    yield Label("Extensions (one per line):")
                    yield TextArea(id="extensions", classes="text-area")

                with Vertical(classes="input-group"):
                    yield Label("Filename Patterns (one per line, * for wildcard):")
                    yield TextArea(id="patterns", classes="text-area")

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
        self.update_target_display()
        self.update_config_file_display()

        # Auto-select first category if any exist
        if len(self.config['categories']) > 0:
            first_category = sorted(self.config['categories'].keys())[0]
            self.load_category_details(first_category)

    def update_config_file_display(self):
        """Update the config file path display."""
        self.query_one("#config-file-display", Static).update(f"📄 {self.config_file}")

    def update_target_display(self):
        """Update the target directory display."""
        target_dir = self.config.get('rules', {}).get('target_directory', 'Not set')
        if not target_dir:
            target_dir = 'Not set'
        self.query_one("#target-display", Static).update(f"📁 {target_dir}")

    def load_category_details(self, category_name):
        """Load category details into form fields."""
        self.loading_category = True

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

        self.loading_category = False
        self.has_unsaved_changes = False

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Handle category selection."""
        category_name = event.item.category_name
        self.load_category_details(category_name)

    def on_input_changed(self, event) -> None:
        """Track when form fields change."""
        if not self.loading_category:
            self.has_unsaved_changes = True

    def on_text_area_changed(self, event) -> None:
        """Track when text areas change."""
        if not self.loading_category:
            self.has_unsaved_changes = True

    def on_select_changed(self, event) -> None:
        """Track when select changes."""
        if not self.loading_category:
            self.has_unsaved_changes = True

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
        elif button_id == "btn-target":
            self.action_select_target()
        elif button_id == "btn-open-config":
            self.action_open_config()
        elif button_id == "btn-quit":
            self.action_quit()

    def refresh_category_list(self):
        """Refresh the category list view."""
        list_view = self.query_one("#categories", ListView)
        list_view.clear()

        sorted_categories = sorted(self.config['categories'].keys())
        for category in sorted_categories:
            item = ListItem(Label(category))
            item.category_name = category
            list_view.append(item)

        list_view.refresh()

        if self.current_category and self.current_category in self.config['categories']:
            try:
                index = sorted_categories.index(self.current_category)
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
        self.has_unsaved_changes = False

        self.refresh_category_list()
        self.clear_fields()
        self.current_category = None

        self.notify(f"Added category: {name}", severity="information")

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
        self.has_unsaved_changes = False
        self.current_category = name
        self.refresh_category_list()
        self.load_category_details(name)
        self.notify(f"Updated category: {name}", severity="information")

    def delete_category(self):
        """Delete current category."""
        if not self.current_category:
            self.notify("Select a category first", severity="warning")
            return

        del self.config['categories'][self.current_category]
        self.save_config()
        self.has_unsaved_changes = False
        self.refresh_category_list()
        self.notify(f"Deleted category: {self.current_category}", severity="information")
        self.clear_fields()
        self.current_category = None

    def test_filename(self):
        """Test a filename against current category rules."""
        from textual.screen import ModalScreen

        class TestDialog(ModalScreen):
            def compose(self) -> ComposeResult:
                with Vertical():
                    yield Label("Test Filename")
                    yield Input(placeholder="Enter filename to test", id="test-input")
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

    def clear_fields(self):
        """Clear input fields."""
        self.query_one("#category-name", Input).value = ""
        self.query_one("#destination", Input).value = ""
        self.query_one("#extensions", TextArea).text = ""
        self.query_one("#patterns", TextArea).text = ""
        self.query_one("#match-mode", Select).value = "either"

    def action_save(self):
        """Save config file."""
        self.save_config()
        self.notify(f"Config saved to {self.config_file}", severity="information")

    def action_select_target(self):
        """Select target directory for organizing."""
        def handle_directory_selected(directory: Path | None) -> None:
            if directory:
                self.config['rules']['target_directory'] = str(directory)
                self.save_config()
                self.update_target_display()
                self.notify(f"Target directory set: {directory}", severity="information")

        self.push_screen(SelectDirectory("~/"), handle_directory_selected)

    def action_open_config(self):
        """Open a different config file."""
        def handle_file_selected(file_path: Path | None) -> None:
            if file_path and file_path.suffix == '.json':
                if self.has_unsaved_changes:
                    self.notify("Save your changes first!", severity="warning")
                    return

                self.config_file = file_path
                self.config = self.load_config()
                self.current_category = None
                self.has_unsaved_changes = False

                self.refresh_category_list()
                self.update_target_display()
                self.update_config_file_display()
                self.clear_fields()

                self.notify(f"Loaded config: {file_path.name}", severity="information")

        config_dir = Path.home() / '.config' / 'file-organizer'
        self.push_screen(FileOpen(str(config_dir)), handle_file_selected)

    def action_quit(self):
        """Quit the app."""
        if self.has_unsaved_changes:
            self.notify("You have unsaved changes! Press 'q' again to quit anyway.", severity="warning")
            self.has_unsaved_changes = False
        else:
            self.exit()

    def action_update(self):
        """Update category via keybinding."""
        self.update_category()

    def action_add(self):
        """Add new category via keybinding."""
        self.add_category()

    def action_delete(self):
        """Delete category via keybinding."""
        self.delete_category()


def main():
    parser = argparse.ArgumentParser(
        description='Interactive config editor for SmartFiler'
    )
    parser.add_argument(
        '-c', '--config',
        help='Path to config file (default: ~/.config/file-organizer/config.json)'
    )

    args = parser.parse_args()

    app = ConfigEditor(config_path=args.config)
    app.run()


if __name__ == "__main__":
    main()
