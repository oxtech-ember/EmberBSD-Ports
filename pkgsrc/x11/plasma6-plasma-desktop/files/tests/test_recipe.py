# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted).
"""Recipe checks for plasma6-plasma-desktop.

Plasma 6.8 no longer ships org.kde.kcontrol.kcmclock.conf; the date-and-time
KCM talks to timedated. pkgsrc patch(1) leaves *.orig backups, and cmake
install(DIRECTORY) of the desktop containment would package them unless
post-patch removes them. The Kickoff drop patch must apply with zero fuzz.
"""

from pathlib import Path
import subprocess
import tempfile
import unittest


RECIPE = Path(__file__).resolve().parents[2]
PATCH = RECIPE / "patches" / "patch-containments_desktop_package_contents_ui_main.qml"
MAKEFILE = RECIPE / "Makefile"
QML = Path("containments/desktop/package/contents/ui/main.qml")


class PlasmaDesktopRecipeTests(unittest.TestCase):
    def test_makefile_drops_retired_kcmclock_conf(self):
        text = MAKEFILE.read_text()
        self.assertNotIn("org.kde.kcontrol.kcmclock.conf", text)
        self.assertNotIn("KAUTH_DBUS_DIR", text)
        self.assertNotIn("share/examples/plasma-desktop", text)
        self.assertIn("kaccess.desktop", text)
        self.assertIn("post-patch:", text)
        self.assertIn("*.orig", text)
        self.assertIn("*.orig_dist", text)

    def test_kickoff_drop_patch_applies_without_fuzz(self):
        patch = PATCH.read_text()
        self.assertIn("onDrop: event => {", patch)
        self.assertIn("folderViewLayer.view.linkHere", patch)
        source = _unpatched_qml()
        self.assertEqual(source.splitlines()[253].strip(), "onDrop: event => {")
        with tempfile.TemporaryDirectory(prefix="plasma-desktop-patch-") as name:
            root = Path(name)
            target = root / QML
            target.parent.mkdir(parents=True)
            target.write_text(source)
            result = subprocess.run(
                ["patch", "-p0", "-F0", "-V", "none", "--posix", "-i", str(PATCH)],
                cwd=root, capture_output=True, text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
            combined = (result.stdout + result.stderr).lower()
            self.assertNotIn("fuzz", combined)
            self.assertNotIn("offset", combined)
            self.assertFalse(target.with_suffix(target.suffix + ".orig").exists())
            patched = target.read_text()
            self.assertIn("folderViewLayer.view.linkHere", patched)


def _unpatched_qml():
    """Rebuild the patched region so the official hunk applies at line 254."""
    # Lines 248-272 of plasma-desktop 6.8.2 containments/.../main.qml.
    region = """            if (root.isContainment) {
                appletsLayout.hidePlaceHolder();
            }
        }

        onDrop: event => {
            if (root.isFolder && FolderTools.isFileDrag(event)) {
                handleDragEnd(folderViewLayer.view);
                folderViewLayer.view.drop(root, event, mapToItem(folderViewLayer.view, event.x, event.y));
            } else if (root.isContainment) {
                root.processMimeData(event.mimeData,
                    event.x - appletsLayout.placeHolder.width / 2,
                    event.y - appletsLayout.placeHolder.height / 2);
                event.accept(event.proposedAction);
                appletsLayout.hidePlaceHolder();
            }
        }
"""
    return ("\n" * 248) + region


if __name__ == "__main__":
    unittest.main()
