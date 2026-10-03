"""Icons for Steam's per-game folders, as deckico-cli does it.

Every <library>/steamapps/{compatdata,shadercache}/<appid>/ gets a `.directory` file
(`Icon=<image>`), so file managers show the game's image instead of a plain folder. The
image is the user's custom art in userdata/<account>/config/grid/ or, failing that, the
icon Steam downloaded to appcache/librarycache/<appid>/.

Plain functions over a Steam root, so the tests run on a fake tree.
"""
import os
import re
from pathlib import Path

STEAM_ROOT = Path.home() / ".local/share/Steam"
NAME_FILE = ".directory"
FOLDERS = ("compatdata", "shadercache")
# SD cards and other disks mounted by the system, even if Steam doesn't list them.
MEDIA_GLOBS = ("/run/media/*/steamapps", "/run/media/*/*/steamapps")

VDF_PATH = re.compile(r'^\s*"path"\s+"(.*)"', re.MULTILINE)
# Custom art in grid/, by priority. Matched case-insensitively, as `find -iname` does.
GRID_PATTERNS = ("{id}_icon.*", "{id}_logo.*", "{id}_hero.*", "{id}.png", "{id}.jpg", "{id}.ico", "{id}p.*")
CACHE_ICON = re.compile(r"[0-9a-f]{40}\.(jpg|png)")


def libraries(steam_root=STEAM_ROOT, media_globs=MEDIA_GLOBS):
    """Every existing steamapps folder (Steam's own, libraryfolders.vdf, mounted media), each once."""
    found = [Path(steam_root) / "steamapps"]
    try:
        text = (Path(steam_root) / "steamapps/libraryfolders.vdf").read_text(errors="replace")
        found += [Path(p.replace("\\\\", "\\")) / "steamapps" for p in VDF_PATH.findall(text)]
    except OSError:
        pass
    for pattern in media_globs:
        found += sorted(Path("/").glob(pattern.lstrip("/")))
    return sorted({Path(os.path.realpath(p)) for p in found if p.is_dir()})


def _grid_dirs(steam_root):
    for grid in sorted(Path(steam_root).glob("userdata/*/config/grid")):
        if grid.parent.parent.name != "0" and grid.is_dir():
            yield grid


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


def find_image(appid, steam_root=STEAM_ROOT):
    """The best image for an appid, or None."""
    grids = [(grid, _files(grid, 2)) for grid in _grid_dirs(steam_root)]
    for pattern in GRID_PATTERNS:
        regex = re.compile(re.escape(pattern.format(id=appid)).replace(r"\*", ".*"), re.IGNORECASE)
        for _grid, files in grids:
            for f in files:
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
            base = lib / name
            if not base.is_dir():
                continue
            for d in sorted(base.iterdir()):
                if d.is_dir() and d.name.isascii() and d.name.isdigit() and d.name != "0":
                    yield d


def apply(steam_root=STEAM_ROOT, media_globs=MEDIA_GLOBS):
    """Write every game folder's .directory. Returns (folders with an icon, folders without an image)."""
    images = {}
    done = missing = 0
    for d in _game_folders(libraries(steam_root, media_globs)):
        if d.name not in images:
            images[d.name] = find_image(d.name, steam_root)
        img = images[d.name]
        if img is None:
            missing += 1
            continue
        target = d / NAME_FILE
        content = f"[Desktop Entry]\nIcon={img}\n"
        try:
            if not (target.is_file() and target.read_text(errors="replace") == content):
                target.write_text(content)
            done += 1
        except OSError:
            missing += 1
    return done, missing


def remove(steam_root=STEAM_ROOT, media_globs=MEDIA_GLOBS):
    """Delete the .directory of every game folder (deckico-cli --removeicons). Returns how many."""
    removed = 0
    for lib in libraries(steam_root, media_globs):
        for name in FOLDERS:
            base = lib / name
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
