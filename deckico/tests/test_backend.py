import importlib.util
import logging
import sys
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parents[1]


def load_backend():
    name = "deckico_backend_under_test"
    for n in [n for n in sys.modules if n == name or n.startswith(name + ".")]:
        del sys.modules[n]
    spec = importlib.util.spec_from_file_location(name, HERE / "backend.py", submodule_search_locations=[str(HERE)])
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


class Unavailable(Exception):
    pass


class FakePaths:
    def __init__(self, steam="/steam"):
        self.steam = steam

    def steam_root(self):
        if self.steam is None:
            raise Unavailable("Steam's folder wasn't found")
        return Path(self.steam)

    def libraries(self):
        return [self.steam_root() / "steamapps", Path("/sd/steamapps")]

    def userdata(self, all=False):
        assert all
        return [self.steam_root() / "userdata/111"]


class FakeCtx:
    Unavailable = Unavailable

    def __init__(self):
        self.log = logging.getLogger("test.deckico")
        self.listeners = []
        self.events = self
        self.paths = FakePaths()

    def on(self, name, cb):
        self.listeners.append((name, cb))


class Backend(unittest.TestCase):
    def setUp(self):
        self.b = load_backend()
        self.ctx = FakeCtx()

    def test_runs_on_every_steam_start(self):
        self.b.setup(self.ctx)
        self.assertEqual(self.ctx.listeners, [("steam_start", self.b.run)])
        with mock.patch.object(self.b.icons, "apply", return_value=(3, 1)) as apply, \
                self.assertLogs("test.deckico", "INFO") as logs:
            self.b.run({"instance": "x"})
        apply.assert_called_once_with([Path("/steam/steamapps"), Path("/sd/steamapps")],
                                      [Path("/steam/userdata/111")], Path("/steam"))
        self.assertIn("icons set on 3 folders (1 without an image)", logs.output[0])

    def test_no_steam_folder_does_nothing(self):
        self.b.setup(self.ctx)
        self.ctx.paths.steam = None
        with mock.patch.object(self.b.icons, "apply") as apply, \
                mock.patch.object(self.b.icons, "remove") as remove, \
                self.assertLogs("test.deckico", "INFO") as logs:
            self.b.run()
            self.b.uninstall(self.ctx, purge=False)
        apply.assert_not_called()
        remove.assert_not_called()
        self.assertIn("no icons set: Steam's folder wasn't found", logs.output[0])
        self.assertIn("no icons removed: Steam's folder wasn't found", logs.output[1])
        self.assertFalse(self.b._lock.locked())

    def test_one_pass_at_a_time(self):
        self.b.setup(self.ctx)
        with mock.patch.object(self.b.icons, "apply") as apply:
            self.b._lock.acquire()
            try:
                self.b.run()
            finally:
                self.b._lock.release()
        apply.assert_not_called()

    def test_uninstall_removes_the_icons(self):
        with mock.patch.object(self.b.icons, "remove", return_value=7) as remove, \
                self.assertLogs("test.deckico", "INFO") as logs:
            self.b.uninstall(self.ctx, purge=False)
        remove.assert_called_once_with([Path("/steam/steamapps"), Path("/sd/steamapps")])
        self.assertIn("removed 7 icons", logs.output[0])


if __name__ == "__main__":
    unittest.main()
