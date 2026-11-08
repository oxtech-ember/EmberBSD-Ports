#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.

"""The offline dialog follows a known reachability value on every launch.

Unknown is not offline. A reported Disconnected, Local or Site state is.
Online closes the dialog. This does not inspect a live network.
"""

import pathlib
import unittest

PATCH = pathlib.Path(__file__).resolve().parent.parent / "patches" / "patch-discover_qml_DiscoverWindow.qml"
TEXT = PATCH.read_text()


def known_offline(reachability):
    return reachability in {"Disconnected", "Local", "Site"}


class OfflineDialog(unittest.TestCase):
    def test_unknown_and_online_do_not_open_the_dialog(self):
        self.assertFalse(known_offline("Unknown"))
        self.assertFalse(known_offline("Online"))
        self.assertIn("-        if (NetworkInformation.reachability !== NetworkInformation.Reachability.Online)", TEXT)
        self.assertIn("+        if (knownOffline())", TEXT)

    def test_known_non_online_states_open_and_online_closes(self):
        for state in ("Disconnected", "Local", "Site"):
            self.assertTrue(known_offline(state))
            self.assertIn(f"NetworkInformation.Reachability.{state}", TEXT)
        self.assertIn("connectionDialog.open()", TEXT)
        self.assertIn("connectionDialog.close()", TEXT)
        self.assertIn("function onReachabilityChanged()", TEXT)


if __name__ == "__main__":
    unittest.main()
