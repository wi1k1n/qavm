# QAVM

Pronounce it as KAY-VIM (almost like the name Kevin with an "m").

**Quality Assurance Version Manager** searches and handles specific software on your machine. The main focus is to list and conveniently categorize different versions of the same software, making it a perfect tool for Quality Assurance specialists.

This is a rethought, generalized version of the [C4D Version Manager](https://github.com/wi1k1n/cinema4d_version_manager), optimized and restructured code-wise to work with any software — not just Cinema 4D.

The main app code is hosted on GitHub: <https://github.com/wi1k1n/qavm>

This repository (`qavm-plugins`) hosts plugins for QAVM, including Cinema 4D, Redshift, AEC (Revit, Vectorworks), and more.

---

## Completed Features

The following items have been implemented:

- Theme selection (light/dark mode)
- Deadlock fix when switching software with saved preferences
- Currently selected software displayed in the window title
- Per-software QAVM preferences
- Hide/Show table widget columns (with settings persistence)
- Improved preferences API for plugins (with bug fixes)
- Plugin tabs support (multiple tile/table tabs)
- Basic plugin concept implementations (`BaseTileBuilder`, `BaseSettings`, etc.)

---

## Bugs

- [ ] **Poor settings layout on macOS** — Qt renders widgets with weird paddings, margins, and alignments on macOS
- [ ] **Install date inconsistency** — The "Installed date" column behaves inconsistently across plugins (currently affects C4D; all plugins are potentially affected)
- [ ] **Closing QAVM during update check throws an exception** — Background update checker doesn't handle shutdown gracefully
- [ ] **Wrong text color in tags usage dialog** — Compare tags with usages vs. empty ones have inconsistent text colors
- [ ] **C4D version sort is broken for old R-versions** — Sorting logic fails for legacy Cinema 4D R-prefixed versions

---

## Features & Improvements

### Version Detection

- [ ] **Redshift / C4D / AEC version detection improvement**
  - Add a setting to use command-line version detection as an alternative source
  - Cache the detected version and update only when the executable changes
  - Show a tooltip indicating the source of version detection (binary parse, cmdline, cache)
  - For Redshift in C4D: display **two separate version columns** — RS-plugin and RS-core
  - Improve overall UX of version representation (more readable formatting)

### Tag System

- [ ] **Tag filter improvements**
  - Add a "View → Clear Filter" action to quickly reset all applied filters
  - Improve `TableColumnFilterPopup` contrast (add border for visual separation)
  - Show targets in the popup sorted the same way as in the current table view
  - Add an alternative entry point for filter popup (e.g., clicking the left part of the header, or Alt+Click) — MMB is nice but needs a backup
- [ ] **Assigning tag from wrong scope should prompt user confirmation**
- [ ] **Table row widget should show all assigned tags regardless of scope** — Scope is only an assigning aid; the table is the source of truth
- [ ] **Use plugin name and software name instead of plugin ID / software ID** in the tags preset filter and tag tooltips

### UI / Context Menu

- [ ] **C4D context menu: folder (show/copy)** — Add "Show Folder" and "Copy Path" actions to the C4D context menu
- [ ] **C4D software settings** — Expose Cinema 4D preferences/settings within QAVM
- [ ] **Prefs combo boxes setting** — Allow configuring run mode: `run` ↔ `runw/console`, `run/wconsole` ↔ `run`, flat

### Plugin Management

- [ ] **Import custom plugins** — Provide a menu action (and optionally drag-and-drop support) so users can import custom plugins as a folder or zip file; QAVM automatically installs them into its plugins folder
- [ ] **Custom plugins machine key** — Store a machine-unique key encrypted with QAVM's internal SSL key for custom plugin licensing/identification

### Example Plugin

- [ ] **Rewrite example plugin from scratch** — The current example plugin (`qavm/source/plugins/example/`) is outdated and needs a complete rewrite as a clean reference implementation

---

## Future Ideas

The following are longer-term ideas not currently on the active roadmap:

- Show software in the menubar directly (instead of switch → software)
- Show in status bar the time it was synced last time
- Shortcut / context menu entry to show the running application
- Centralized handling of `PluginUID` and `SoftwareID` (currently scattered throughout the codebase)
- Add timer to scan processes and detect if they were stopped from outside QAVM
- Start/Stop/IsRunning API should include checking already-running processes and "attach" to them
- Add API for "context" — tying together different software aspects (e.g., accessing Settings from within Tile/TableBuilder or ContextMenu)
- Keep in mind that the app can list everything, hence executables can be more than one (important for extra-arguments plugins)
- Add API versioning so plugins declare minimal supported API version
- Allow plugins to order tabs
- Reorder plugins in the "Switch" list with a favorites system and a separate "plugin manager" window
- Installing plugins should be as easy as drag-and-drop (or folder/zip selection from menu), with an API for checking plugin updates
- Add system of adding tags to descriptors with meta information (ideally as a separate plugin)
- Sort/Filter/Group enhancements:
  - Plugins register their own filter targets
  - Minimal boolean logic (and/or/not) with complex setups (e.g., railroad-style)
  - Sorting capabilities in tile widget
  - Grouping abilities (similar to the old C4D Version Manager)
- Multiple software at the same time on the same layout
- Free Move tab
