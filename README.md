# Individual HDA

Individual HDA is a personal Houdini digital-asset library. It runs inside Houdini and keeps HDA files, versions, thumbnails, notes, tags, favorites, preview videos, and HIP-file locations together.

![Individual HDA interface](image/ihda_main.png)

![Individual HDA workflow](image/ihda_main.gif)

## Requirements

- Houdini 21 or later with Qt 6 and Python 3.11+
- A writable local directory for the library database and files
- Optional FFmpeg and ffprobe for preview videos

The application uses Houdini's bundled Python and PySide6. Do not install a second Qt or Python package into Houdini.

## Installation

Use a Houdini package so the repository stays in one location.

1. In Houdini's Python Shell, print the user preference directory:

   ```python
   import hou
   print(hou.getenv("HOUDINI_USER_PREF_DIR"))
   ```

2. Copy [`packages/IndividualHDA.json`](packages/IndividualHDA.json) to the `packages` directory inside that preference directory.

3. Set `IHDA_ROOT` in the package file to the directory containing this repository's `main.py`:

   ```json
   {
     "enable": true,
     "load_package_once": true,
     "env": [{"IHDA_ROOT": "/path/to/IndividualHDA"}],
     "hpath": "$IHDA_ROOT"
   }
   ```

   Use forward slashes in JSON paths. Examples: `C:/Users/you/tools/IndividualHDA`, `/Users/you/tools/IndividualHDA`, `/home/you/tools/IndividualHDA`.

4. Restart Houdini and open **Windows → Python Panel → Individual HDA**.

Do not copy the source or `.pypanel` file when using the package. Remove an old manually copied `individualHDA.pypanel` if it creates a duplicate panel.

## First launch

Open **Preferences** and select the directory that contains `ihda.db`, or an empty directory for a new library. Save the preference and reopen the panel.

For video features, select the FFmpeg installation or its `bin` directory. Both `ffmpeg` and `ffprobe` must be available there or on `PATH` before Houdini starts.

Settings are stored under `$HOUDINI_USER_PREF_DIR/IndividualHDA/.config`. Set `IHDA_CONFIG_DIR` to override that location.

Assets are registered under your OS login name. Set `IHDA_USER` to use a pipeline-assigned name instead. An existing local library keeps the single user it already has, so older libraries created as `anonymous` open unchanged.

## Use

- Drag a node with the middle mouse button to register it or import an asset.
- Browse categories and search by name, tag, or node type.
- Manage versions, notes, tags, favorites, thumbnails, and preview videos.
- Inspect asset instances recorded from HIP files.
- Export or import a complete library archive.
- Open the Web tab for Houdini help and web content.

The existing panel layout, menus, and interaction patterns are preserved.

## Library Tools

Open **Library Tools** in the panel menu for:

- **Health:** check database integrity, incomplete records, and missing files; export a report.
- **Backups and restore:** create named backups, validate archives, and stage a restore.
- **Repair moved paths:** preview and update stored paths after moving a library.
- **Compare versions:** compare metadata, parameter interfaces, and expanded HDA sections; import a selected version into a matching Houdini network.
- **Explorer:** search a large library in cancellable 200-row pages.
- **Recovery files:** inspect, back up, and remove unreferenced recovery files safely.

Restore and path repair close the panel after completion. Reopen it to refresh the library. See the [Library Tools guide](docs/LIBRARY_TOOLS.md) for details.

## Data safety

The database uses SQLite schema v4 with foreign keys, validation checks, normalized tags, indexes, and transactional migrations. Existing databases are backed up before an upgrade.

File operations use a persistent journal. Imports, renames, deletions, path repairs, and restores can be recovered after an interrupted operation. Recovery copies are retained until you remove them through **Library Tools**.

The application is designed for a single local user. Network filesystems and simultaneous writers from multiple processes are not supported.

## Development

Use a separate environment; do not install development dependencies into Houdini:

```sh
python -m venv .venv
python -m pip install pytest ruff mypy "PySide6>=6.5.3,<7"
python -m pytest -q
python -m ruff check .
python -m ruff format --check .
python -m mypy
```

Run the Houdini smoke test with `hython`:

```sh
hython tests/houdini_smoke.py
```

It uses temporary files and a fresh Houdini process. Architecture, schema, recovery, and validation details are in [`docs/`](docs/); release decisions are in [`CHANGELOG.md`](CHANGELOG.md).

## Support

<a href="https://buymeacoffee.com/seongcheol"><img src="https://img.buymeacoffee.com/button-api/?text=Buy me a book&emoji=📖&slug=seongcheol&button_colour=40DCA5&font_colour=ffffff&font_family=Bree&outline_colour=000000&coffee_colour=FFDD00" alt="Buy me a book" /></a>

## License

MIT License. Copyright (c) 2020 Seongcheol Jeon. Third-party notices are in [`THIRD_PARTY_LICENSES.txt`](THIRD_PARTY_LICENSES.txt).
