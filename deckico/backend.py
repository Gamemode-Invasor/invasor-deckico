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
    ctx.on_steam_start(run)


def run():
    # One pass at a time: a Steam restart during a pass doesn't start a second one.
    if not _lock.acquire(blocking=False):
        return
    try:
        done, missing = icons.apply()
        ctx.log.info("icons set on %d folders (%d without an image)", done, missing)
    finally:
        _lock.release()


def uninstall(context, purge):
    """Remove the icons it left in Steam's folders (deckico-cli --removeicons)."""
    context.log.info("removed %d icons", icons.remove())


METHODS = {}
