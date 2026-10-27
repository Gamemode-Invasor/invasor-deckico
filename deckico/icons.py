"""Icons for Steam's per-game folders, as deckico-cli does it.

Every <library>/steamapps/{compatdata,shadercache}/<appid>/ gets a `.directory` file
(`Icon=<image>`), so file managers show the game's image instead of a plain folder. The
image is the user's custom art in userdata/<account>/config/grid/ or, failing that, the
icon Steam downloaded to appcache/librarycache/<appid>/.

Plain functions over the folders the caller gives (backend.py asks ctx.paths), so the tests
run on a fake tree.
"""
import os
import re
from pathlib import Path

NAME_FILE = ".directory"
FOLDERS = ("compatdata", "shadercache")

# Custom art in grid/, by priority. Matched case-insensitively, as `find -iname` does.
GRID_PATTERNS = ("{id}_icon.*", "{id}_logo.*", "{id}_hero.*", "{id}.png", "{id}.jpg", "{id}.ico", "{id}p.*")
CACHE_ICON = re.compile(r"[0-9a-f]{40}\.(jpg|png)")


def _files(folder, depth):
    """Files in folder and its subfolders down to depth levels, in a stable order."""
    out = []
    for dirpath, dirnames, filenames in os.walk(folder):
        level = len(Path(dirpath).relative_to(folder).parts) + 1
        if level >= depth:
            dirnames.clear()
        dirnames.sort()
        out += [Path(dirpath) / f for f in sorted(filenames)]
    return out


def grid_files(accounts):
    """The files in every account's config/grid/ (and one level below), in a stable order."""
    return [f for account in accounts for f in _files(Path(account) / "config/grid", 2)]


def find_image(appid, grids, steam_root):
    """The best image for an appid, or None. grids: the files grid_files() found; steam_root:
    Steam's folder, for the icon it downloaded."""
    for pattern in GRID_PATTERNS:
        regex = re.compile(re.escape(pattern.format(id=appid)).replace(r"\*", ".*"), re.IGNORECASE)
        for f in grids:
            if regex.fullmatch(f.name):
                return f
    cache = Path(steam_root) / "appcache/librarycache" / str(appid)
    if cache.is_dir():
        for f in sorted(cache.iterdir()):
            if f.is_file() and CACHE_ICON.fullmatch(f.name):
                return f
    return None


def _game_folders(libs):
    for lib in libs:
        for name in FOLDERS:
            base = Path(lib) / name
            if not base.is_dir():
                continue
            for d in sorted(base.iterdir()):
                if d.is_dir() and d.name.isascii() and d.name.isdigit() and d.name != "0":
                    yield d


def apply(libs, accounts, steam_root):
    """Write every game folder's .directory. Returns (folders with an icon, folders without an image)."""
    grids = grid_files(accounts)
    images = {}
    done = missing = 0
    for d in _game_folders(libs):
        if d.name not in images:
            images[d.name] = find_image(d.name, grids, steam_root)
        img = images[d.name]
        if img is None:
            missing += 1
            continue
        target = d / NAME_FILE
        if target.is_symlink():  # never write through a link to somewhere else
            missing += 1
            continue
        content = f"[Desktop Entry]\nIcon={img}\n"
        try:
            if not (target.is_file() and target.read_text(errors="replace") == content):
                target.write_text(content)
            done += 1
        except OSError:
            missing += 1
    return done, missing


def remove(libs):
    """Delete the .directory of every game folder (deckico-cli --removeicons). Returns how many."""
    removed = 0
    for lib in libs:
        for name in FOLDERS:
            base = Path(lib) / name
            if not base.is_dir():
                continue
            for f in base.glob(f"*/{NAME_FILE}"):
                try:
                    if f.is_file():
                        f.unlink()
                        removed += 1
                except OSError:
                    pass
    return removed
