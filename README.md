# QAVM

Quality Assurance Version Manager manages software on your machine. The main focus is to list and conveniently categorize different versions of the same software, hence it's a perfect tool for the Quality Assurance specialists.

This is a rethought version of the [C4D Version Manager](https://github.com/wi1k1n/cinema4d_version_manager), generalized to be applicable to any software and optimized and restructured code-wise.

## Improvements & bugs

* Don't throw away calculated results (such that switching back-n-forth between software is fast)
	* have a setting to show software in the menubar directly (instead of switch->software)

* Show in status bar the time it was synced last time

* Add theme selection: light/dark + color
	* for light/dark the switch should be between yoda and darth vader ;)

* Add shortcut/contextMenuEntry to show the running application

* PluginUID and SoftwareID are used all over the place separately or concatenated, and this creates kind of a mess. Should be a centralized place of hanlding such IDs

* (Bug) Somehow avoid the deadlock, when switching to another software is saved in preferences, but the plugin crashes

* Improve performance of creating tiles
	* More caching
	* Potentially parallelizable (ideally having a separate API for parallelizing)

* Don't rescan when switching between software (unless explicit action from the user)

* (Bug) Add timer, which scans processes and detects if they were stopped from outside of the QAVM app

* Add currently selected software to the window title

* Per-software QAVM-preferences

* Start/Stop/IsRunning processes API should include checking the already running processes, being able to "attach" to them (i.e. control them even if not executed from QAVM)

* Add API for having "context", which ties together different software aspects (i.e. having access e.g.. to Settings from within the Tile/TableBuilder or ContextMenu)

* Keep in mind that the app can technically list everything, hence the executables can be more than one

* Add API versioning (such that the plugins can declare the minimal supported API and report it instead of crashing)

* Allow the plugin to work with multiple tile tabs, multiple table tabs

* Allow the plugin to order tabs

* Store last opened tab as tab id, rather than index

* Unpack the built-in plugins on first startup (no installers please!)

* Save table widget sorting settings for next run

* Hide/Show table widget columns
	* and save this setting for next runs

* Support multiselection on table widget (e.g. for the context menu)

* Improve preferences API (for easier usage by plugins)
	* (Bug) and make it actually work ;)

* Reorder plugins in the "Switch" list
	* have "favorites" system
	* only list software handlers there
	* have a separate "plugin manager" window, showing what's where

## Further ideas

* Installing plugins should be as easy as d&d (or at most select folder or zip-file from the menu).
	* Ideally some API for checking for the plugin updates. I.e. each plugin implements it's own logic for checking if there's new version, but doesn't have to deal with creating a menu entry for that

* Add system of adding tags to the descriptors
	* Also attach meta information to descriptors (ideally in a generic way and hence implemented as a separate plugin)

* Multiple software at the same time (including placing them on the same layout)

* The API for the plugin to add their own tabs

* Free Move tab

* Add basic implementation for the plugin concepts (e.g. Tile/TableBuilder, Context, Settings...) that are easy to use by plugins. (The BaseTileBuilder, BaseSettings etc.. are effectively just "dummy" implementations)