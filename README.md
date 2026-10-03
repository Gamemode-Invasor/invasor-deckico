# Deckico

A module for [Invasor](../invasor) that puts **each game's icon on its Steam folders**: every
`steamapps/compatdata/<appid>/` and `steamapps/shadercache/<appid>/`, in every library (internal storage, the ones in
Steam's `libraryfolders.vdf`, and SD cards or disks under `/run/media`). A file manager then shows the game's image
instead of a plain folder, so you can tell at a glance which Proton prefix or shader cache belongs to which game.

Deckico has no tab and nothing to set up. It works in the background:

- **When:** every time Steam starts or restarts (also when switching between Desktop and Game Mode), and when Invasor
  starts with Steam already running. New games get their icon at the next Steam start.
- **Which image:** your custom art in `userdata/<account>/config/grid/` first (`<appid>_icon`, `_logo`, `_hero`,
  `<appid>.png`, `.jpg`, `.ico`, `<appid>p`, in that order), else the icon Steam downloaded to
  `appcache/librarycache/<appid>/`. Folders with no image are left alone.
- **What it writes:** a `.directory` file (`[Desktop Entry]` / `Icon=<image>`) in each of those folders, rewritten only
  when the image changed. Nothing else is touched.
- **Uninstalling the module** removes every `.directory` from those folders. Disabling it removes nothing.

The log (`journalctl --user -u invasor`) says how many folders got an icon each time.

It does the same as the `deckico-cli` script. If you used that one, remove its autostart entry
(`deckico-cli -u`) so it doesn't run twice.

## Build, test and install
With the core checked out next to this repository (`../invasor`):

```sh
python3 ../invasor/tools/pack_module.py deckico       # check, tests -> deckico-<version>.zip
python3 ../invasor/tools/install_module.py deckico    # or install that zip from ⚙ Settings › Install module
```

Needs an Invasor core with `ctx.on_steam_start` and `author` support in module.json.

## License
[GNU General Public License v3.0 or later](LICENSE) (GPL-3.0-or-later).
