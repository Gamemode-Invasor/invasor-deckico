import tempfile
import unittest
from pathlib import Path

import icons

SHA = "0123456789abcdef0123456789abcdef01234567"


class Icons(unittest.TestCase):
    def setUp(self):
        d = tempfile.TemporaryDirectory()
        self.addCleanup(d.cleanup)
        self.root = Path(d.name)
        self.steam = self.root / "Steam"
        self.sd = self.root / "sd"
        self.media = self.root / "media"
        apps = self.steam / "steamapps"
        apps.mkdir(parents=True)
        (apps / "libraryfolders.vdf").write_text(
            '"libraryfolders"\n{\n\t"0"\n\t{\n\t\t"path"\t\t"%s"\n\t}\n\t"1"\n\t{\n\t\t"path"\t\t"%s"\n\t}\n}\n'
            % (self.steam, self.sd))
        # 10: grid art in two users (priority), 20: only Steam's cached icon, 30: nothing,
        # 40: art only for user 0 (ignored), 50: art in a grid subfolder.
        for lib, name, appid in [(self.steam, "compatdata", "10"), (self.steam, "shadercache", "10"),
                                 (self.steam, "compatdata", "20"), (self.sd, "compatdata", "30"),
                                 (self.sd, "shadercache", "40"), (self.steam, "compatdata", "50"),
                                 (self.steam, "compatdata", "0"), (self.steam, "compatdata", "notanid")]:
            (lib / "steamapps" / name / appid).mkdir(parents=True)
        self.grid("111", "10_hero.png")
        self.grid("222", "10_ICON.jpg")
        self.grid("0", "40_icon.png")
        self.grid("111", "sub/50p.png")
        cache = self.steam / "appcache/librarycache/20"
        cache.mkdir(parents=True)
        (cache / "header.jpg").write_text("x")
        (cache / f"{SHA}.jpg").write_text("x")
        # Mounted media, found even when Steam doesn't list it.
        (self.media / "deck" / "steamapps" / "compatdata" / "20").mkdir(parents=True)
        # What ctx.paths answers: every library, and every account but 0.
        self.libs = [self.steam / "steamapps", self.sd / "steamapps", self.media / "deck" / "steamapps"]
        self.accounts = [self.steam / "userdata" / u for u in ("111", "222")]

    def grid(self, user, name):
        f = self.steam / "userdata" / user / "config/grid" / name
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text("x")
        return f

    def icon(self, lib, name, appid):
        f = lib / "steamapps" / name / appid / ".directory"
        return f.read_text() if f.exists() else None

    def test_find_image(self):
        grid = self.steam / "userdata"
        files = icons.grid_files(self.accounts)
        self.assertEqual(icons.find_image("10", files, self.steam), grid / "222/config/grid/10_ICON.jpg")  # _icon beats _hero
        self.assertEqual(icons.find_image("20", files, self.steam), self.steam / f"appcache/librarycache/20/{SHA}.jpg")
        self.assertIsNone(icons.find_image("30", files, self.steam))
        self.assertIsNone(icons.find_image("40", files, self.steam))  # only user 0 has it (ctx.paths leaves 0 out)
        self.assertEqual(icons.find_image("50", files, self.steam), grid / "111/config/grid/sub/50p.png")

    def test_apply_and_remove(self):
        self.assertEqual(icons.apply(self.libs, self.accounts, self.steam), (5, 2))
        icon10 = f"[Desktop Entry]\nIcon={self.steam / 'userdata/222/config/grid/10_ICON.jpg'}\n"
        self.assertEqual(self.icon(self.steam, "compatdata", "10"), icon10)
        self.assertEqual(self.icon(self.steam, "shadercache", "10"), icon10)
        self.assertIn(SHA, self.icon(self.media / "deck", "compatdata", "20"))
        self.assertIsNone(self.icon(self.sd, "compatdata", "30"))
        self.assertIsNone(self.icon(self.steam, "compatdata", "0"))
        self.assertIsNone(self.icon(self.steam, "compatdata", "notanid"))
        self.assertEqual(icons.apply(self.libs, self.accounts, self.steam), (5, 2))  # again: same result
        # A .directory that is a link is never written through.
        outside = self.root / "outside.txt"
        outside.write_text("keep")
        link = self.steam / "steamapps/compatdata/10/.directory"
        link.unlink()
        link.symlink_to(outside)
        self.assertEqual(icons.apply(self.libs, self.accounts, self.steam), (4, 3))
        self.assertEqual(outside.read_text(), "keep")
        link.unlink()
        link.write_text(icon10)
        # Only the .directory files go; the folders and anything else stay.
        other = self.steam / "steamapps/compatdata/10/pfx.lock"
        other.write_text("x")
        self.assertEqual(icons.remove(self.libs), 5)
        self.assertIsNone(self.icon(self.steam, "compatdata", "10"))
        self.assertTrue(other.exists())
        self.assertEqual(icons.remove(self.libs), 0)

    def test_no_steam_is_nothing_to_do(self):
        nothing = self.root / "nothing"
        self.assertEqual(icons.apply([nothing / "steamapps"], [nothing / "userdata/111"], nothing), (0, 0))
        self.assertEqual(icons.apply([], [], nothing), (0, 0))
        self.assertEqual(icons.remove([nothing / "steamapps"]), 0)


if __name__ == "__main__":
    unittest.main()
