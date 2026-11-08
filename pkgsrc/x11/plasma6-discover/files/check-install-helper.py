#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.

"""The install helper accepts one catalog root and refuses everything else.

These cases do not install a package. A non-root caller never reaches pkexec's
package operation.
"""

import importlib.util
import pathlib
import unittest
from importlib.machinery import SourceFileLoader

HELPER = pathlib.Path(__file__).resolve().parent / "EmberBSDBackend" / "emberbsd-discover-install"
loader = SourceFileLoader("emberbsd_discover_install", str(HELPER))
spec = importlib.util.spec_from_loader(loader.name, loader)
helper = importlib.util.module_from_spec(spec)
loader.exec_module(helper)


class InstallHelper(unittest.TestCase):
    def test_catalog_root_is_accepted(self):
        self.assertTrue(helper.valid_root("sysutils/plasma6-milou"))
        self.assertTrue(helper.valid_root("x11/plasma6-discover"))

    def test_shell_and_removal_arguments_are_refused(self):
        for root in ("", "sysutils/plasma6-milou;rm", "sysutils/../milou",
                     "/usr/pkg", "sysutils/plasma6-milou\nrm", "--remove",
                     "sysutils/plasma6-milou && true", "remove", "sysutils/plasma6-milou@native"):
            self.assertFalse(helper.valid_root(root), root)
            self.assertEqual(helper.main(["helper", root]), 2)

    def test_missing_or_extra_arguments_are_refused(self):
        self.assertEqual(helper.main(["helper"]), 2)
        self.assertEqual(helper.main(["helper", "sysutils/plasma6-milou", "extra"]), 2)

    def test_valid_root_without_authorization_does_not_install(self):
        self.assertEqual(helper.main(["helper", "sysutils/plasma6-milou"]), 2)


if __name__ == "__main__":
    unittest.main()
