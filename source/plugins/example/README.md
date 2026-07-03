# Example Plugin — QAVM Reference Implementation

This plugin demonstrates how to build a QAVM plugin from scratch. It covers all major plugin concepts: software registration, qualifiers, descriptors, tile builders, table builders, context menus, settings, custom views, menu items, and workspaces.

## Quick Start

To use this plugin as a starting point for your own:

1. Copy the `example/` folder to a new location.
2. Rename the folder and update `PLUGIN_ID`, `PLUGIN_NAME`, and other module-level constants in `example.py`.
3. Remove or replace the example-specific qualifiers, descriptors, and builders.
4. Load QAVM with `--extraPluginsFolder /path/to/your/plugin`.

## Plugin Structure

```
example/
├── example.py          # Entry point — declares PLUGIN_ID, PLUGIN_NAME, etc. and registers software/workspaces
├── example_simple.py   # Minimal example: one software, one descriptor type (any directory), basic table + tiles
├── example_all.py      # Full-featured example: multiple descriptor types (.exe, .png), tile builders with borders,
│                        # settings tabs, custom views, menu items, workspaces
├── example_images.py   # (Optional) Additional software registration — images/directories with icon extraction
└── utils.py            # Helper utilities (logging, etc.)
```

## Core Concepts

### 1. Entry Point (`example.py`)

The entry point file must declare these module-level constants:

| Constant | Description | Example |
|----------|-------------|---------|
| `PLUGIN_ID` | Unique plugin identifier in domain format | `'in.wi1k.tools.qavm.plugin.example'` |
| `PLUGIN_VERSION` | Plugin version (major.minor.patch) | `'0.2.0'` |
| `PLUGIN_VARIANT` | Optional variant string (e.g., `'Alpha'`) | `''` |
| `PLUGIN_NAME` | Display name in QAVM UI | `'(Example Plugin)'` |
| `PLUGIN_DEVELOPER` | Developer name or organization | `'Ilya Mazlov'` |
| `PLUGIN_WEBSITE` | Plugin website or repository URL | `'https://github.com/wi1k1n/qavm'` |

And implement these registration functions:

```python
def RegisterPluginSoftware():
    """Return a list of software registration dicts."""
    return [...]

def RegisterPluginWorkspaces():
    """Return a dict of workspace definitions."""
    return {...}
```

### 2. Software Registration

Each software module is registered with a dict:

```python
{
    'id': 'software.first',                    # Unique ID under PLUGIN_ID domain
    'name': '(Example) First',                 # Display name
    'descriptors': {                           # Descriptor types (qualifier → descriptor mapping)
        'exe': {'qualifier': ExampleQualifierEXE, 'descriptor': ExampleDescriptorEXE},
        'png': {'qualifier': ExampleQualifierPNG, 'descriptor': ExampleDescriptorPNG},
    },
    'views': {                                 # UI views per descriptor type
        'tiles':  {'exe': ExampleTileBuilderEXE, 'png': ExampleTileBuilderPNG},
        'table':  {'exe': ExampleTableBuilderEXE, 'png': ExampleTableBuilderPNG},
        'custom': {'1': ExampleCustomView1},
    },
    'menuitems': {                             # Menu actions in the QAVM menubar
        '1': ExampleMenuItem1,
    },
    'settings': ExampleSettings,               # Settings class (optional)
}
```

### 3. Qualifiers (`BaseQualifier`)

Qualifiers identify software directories. Two methods:

- **`Identify(currentPath, fileContents)`** — Return `True` if this path represents your software.
- **`GetIdentificationConfig()`** *(optional)* — Configure search behavior (e.g., search files vs. directories).

```python
class ExampleQualifierEXE(BaseQualifier):
    def Identify(self, currentPath: Path, fileContents: dict) -> bool:
        if not currentPath.is_dir():
            return False
        exeFiles = list(currentPath.glob('*.exe'))
        return len(exeFiles) > 0
```

### 4. Descriptors (`BaseDescriptor`)

Descriptors represent a single installed version of your software. They carry data used by tiles, tables, and context menus.

```python
class ExampleDescriptorEXE(BaseDescriptor):
    def __init__(self, dirPath: Path, settings: SoftwareBaseSettings, fileContents: dict):
        super().__init__(dirPath, settings, fileContents)
        # Add your own properties:
        self.targetPaths = list(self.dirPath.glob('*.exe'))
        self.filesCount = len(list(self.dirPath.glob('*.*')))
```

Inherited from `BaseDescriptor`:
- `self.UID` — Unique identifier for this software instance
- `self.dirPath` — Path to the software directory
- `self.settings` — Software-specific settings instance
- `self.majorVersion`, `self.subversion`, `self.buildString` — Version info (populate in subclass)

### 5. Tile Builders (`BaseTileBuilder`)

Tile builders create visual tiles for the tile view.

```python
class ExampleTileBuilderEXE(BaseTileBuilder):
    def GetName(self) -> str:
        return 'Example Tiles EXE'

    def GetSupportedDescriptorTypes(self, descriptorTypes: list[str]) -> list[str]:
        return ['exe']  # Only handle 'exe' descriptors

    def GetContextMenu(self, desc: BaseDescriptor) -> Optional[QMenu]:
        menu = QMenu()
        menu.addAction('Open folder', partial(OpenFolderInExplorer, desc.dirPath))
        return menu

    def CreateTileWidget(self, descriptor: ExampleDescriptorEXE, parent) -> QWidget:
        # Create and return a widget representing this software tile
        widget = QWidget(parent)
        # ... populate widget ...
        return widget
```

Key methods:
- **`GetName()`** — Display name for this tile view
- **`GetSupportedDescriptorTypes()`** — Which descriptor types this builder handles
- **`GetContextMenu()`** — Right-click context menu for a descriptor
- **`CreateTileWidget()`** — Create the visual tile widget
- **`ProcessDescriptors()`** *(optional)* — Filter/transform descriptors before display

### 6. Table Builders (`BaseTableBuilder`)

Table builders define columns and cell values for the table view.

```python
class ExampleTableBuilderEXE(BaseTableBuilder):
    def GetSupportedDescriptorTypes(self, descriptorTypes: list[str]) -> list[str]:
        return ['exe']

    def GetTableColumnInfo(self) -> list[TableColumnInfo]:
        return [
            TableColumnInfo('Folder name', lambda desc: desc.dirPath.name),
            TableColumnInfo('Files count', lambda desc: NumberTableWidgetItem(desc.filesCount)),
            TableColumnInfo('Path', lambda desc: PathTableWidgetItem(desc.dirPath)),
        ]

    def GetContextMenu(self, desc: BaseDescriptor) -> Optional[QMenu]:
        return None  # Or return a QMenu with actions
```

### 7. Settings (`SoftwareBaseSettings`)

Plugin-specific settings per software.

```python
class ExampleSettings(SoftwareBaseSettings):
    def GetSettingsVersion(self) -> int:
        return 1

    CONTAINER_DEFAULTS: dict[str, Any] = {
        'mySetting': 'default value',
    }

    def CreateWidgets(self, parent: QWidget) -> list[tuple[str, QWidget]]:
        # Return list of (tab_name, widget) tuples
        return [
            ('Example', QLabel('Settings go here', parent)),
        ]
```

### 8. Custom Views (`BaseCustomView`)

Add custom tabs to the software detail panel.

```python
class ExampleCustomView1(BaseCustomView):
    def __init__(self, settings: SoftwareBaseSettings, parent=None):
        super().__init__(settings, parent)
        layout = QVBoxLayout(self)
        label = QLabel('Custom view content', self)
        layout.addWidget(label)
```

### 9. Menu Items (`BaseMenuItem`)

Add actions to the QAVM menubar.

```python
class ExampleMenuItem1(BaseMenuItem):
    def GetMenu(self, parent) -> Optional[QMenu | QAction]:
        menu = QMenu('Example Plugin', parent)
        menu.addAction('Action 1', partial(self._doSomething, 1))
        return menu
```

### 10. Workspaces (`RegisterPluginWorkspaces`)

Define workspace presets that show specific software/views combinations.

```python
def RegisterPluginWorkspaces():
    return {
        'first': {
            'name': 'First Workspace',
            'ids': ['software.first#*'],           # All views of software.first
        },
        'png': {
            'name': 'PNG View',
            'ids': [
                'software.first#views/tiles/png',  # Specific view
                'software.first#views/table/png',
            ],
        },
    }
```

## Inheritance Pattern

QAVM uses multiple inheritance to combine behaviors:

```python
class MyTileBuilder(BaseTileBuilder, ContextMenuMixin):
    ...

class MyTableBuilder(BaseTableBuilder, ContextMenuMixin):
    ...
```

Common mixins:
- **`ContextMenuBase`** — Shared context menu logic across tile and table builders
- **`RunningBorderMixin`** — Animated border when process is running

## Tips

1. **UIDs are unique per software instance** — The `UID` combines `PLUGIN_ID`, software ID, and a hash of the path.
2. **Descriptor types are scoped to plugins** — Two plugins can both use `'exe'` as a descriptor type without conflict.
3. **Settings versioning** — Increment `GetSettingsVersion()` when your settings schema changes; QAVM will prompt for migration.
4. **Thread safety** — UI operations must run on the main thread. Use signals/slots for cross-thread communication.
5. **Performance** — Avoid expensive operations in `Identify()`, `GetTableCellValue()`, or `CreateTileWidget()` — these are called frequently during scanning.

## See Also

- [QAVM API Documentation](../../qavmapi/) — Full API reference
- [Maxon Plugin](../maxon/) — Real-world plugin example (Cinema 4D, Redshift, AEC)
- [QAVM Main README](../../README.md) — Core application documentation
