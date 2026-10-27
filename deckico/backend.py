"""Deckico: game icons on Steam's compatdata and shadercache folders.

No tab: every time Steam starts (and when Invasor starts with Steam already up) the icons
are set again, so new games get theirs. Uninstalling the module removes them.
"""
import threading

from . import icons

ctx = None
_lock = threading.Lock()


def setup(context):
    global ctx
    ctx = context
    ctx.events.on("steam_start", run)


def run(payload=None):
    # One pass at a time: a Steam restart during a pass doesn't start a second one.
    if not _lock.acquire(blocking=False):
        return
    try:
        paths = ctx.paths
        done, missing = icons.apply(paths.libraries(), paths.userdata(all=True), paths.steam_root())
        ctx.log.info("icons set on %d folders (%d without an image)", done, missing)
    except ctx.Unavailable as e:
        ctx.log.info("no icons set: %s", e)
    finally:
        _lock.release()


def uninstall(context, purge):
    """Remove the icons it left in Steam's folders (deckico-cli --removeicons)."""
    try:
        context.log.info("removed %d icons", icons.remove(context.paths.libraries()))
    except context.Unavailable as e:
        context.log.info("no icons removed: %s", e)


METHODS = {}
