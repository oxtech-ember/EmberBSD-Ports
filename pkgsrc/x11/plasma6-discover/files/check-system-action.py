#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
"""Check the two polkit operations and the local Discover update entry points."""

from pathlib import Path
from xml.etree import ElementTree
import unittest

ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "files" / "EmberBSDBackend"


class SystemAction(unittest.TestCase):
    def test_fixed_argv_and_authorization(self):
        source = (BACKEND / "EmberBSDBackend.cpp").read_text()
        self.assertIn('process->setProgram(QStringLiteral("/usr/pkg/bin/pkexec"));', source)
        self.assertIn('const QString client = QStringLiteral("/usr/sbin/ember-update");', source)
        self.assertIn('if (m_system)\n            process->setArguments({client, QStringLiteral("apply")});', source)
        self.assertIn('process->setArguments({client, QStringLiteral("install"), m_root, QStringLiteral("--pkgname"),', source)
        self.assertIn("m_base + QLatin1Char('-') + m_version", source)
        action = ElementTree.parse(BACKEND / "org.emberbsd.discover.update.policy").find("action")
        self.assertEqual(action.findtext("defaults/allow_active"), "auth_admin")
        for scope in ("allow_any", "allow_inactive"):
            self.assertEqual(action.findtext("defaults/" + scope), "no")
        self.assertEqual({x.get("key"): x.text for x in action.findall("annotate")}, {
            "org.freedesktop.policykit.exec.path": "/usr/sbin/ember-update",
            "org.freedesktop.policykit.exec.argv1": "apply",
        })

    def test_catalog_and_install_use_native_actions(self):
        source = (BACKEND / "EmberBSDBackend.cpp").read_text()
        self.assertIn('process->start(client, {QStringLiteral("catalog")});', source)
        self.assertNotIn("ember-sdk.pyz", source)
        policy = ElementTree.parse(BACKEND / "org.emberbsd.discover.install.policy").find("action")
        self.assertEqual(policy.findtext("annotate[@key='org.freedesktop.policykit.exec.path']"), "/usr/sbin/ember-update")
        self.assertEqual(policy.findtext("annotate[@key='org.freedesktop.policykit.exec.argv1']"), "install")
        self.assertEqual(policy.findtext("defaults/allow_active"), "auth_admin")
        self.assertIn('if (result == "idle")', source)
        self.assertIn('else if (result == "ready")', source)
        self.assertIn('emberStagedPackages().contains(name)', source)

    def test_single_notifier_owns_automatic_updates(self):
        header = (ROOT / "patches" / "patch-notifier_DiscoverNotifier.h").read_text()
        self.assertIn("m_systemNotifier != nullptr && m_backends.size() == 1", header)
        notifier = (ROOT / "patches" / "patch-notifier_DiscoverNotifier.cpp").read_text()
        self.assertIn("usesSystemUpdateService() || !checkTriggerTimes", notifier)
        self.assertIn("usesSystemUpdateService() && !isOnline()", notifier)
        self.assertIn('return m_systemNotifier->property("emberUpdateStatus")', notifier)

    def test_update_entries_do_not_query_the_store(self):
        source = (BACKEND / "EmberBSDBackend.cpp").read_text()
        entry = source.split("ResultsStream *EmberBSDBackend::search(", 1)[1].split("ResultsStream *EmberBSDBackend::searchCatalog(", 1)[0]
        self.assertIn("filter.state == AbstractResource::Upgradeable", entry)
        self.assertLess(entry.index("return new ResultsStream"), entry.index("return searchCatalog(filter);"))
        self.assertRegex(source, r"void EmberBSDBackend::checkForUpdates\(\)\s*\{\s*m_updateState.refresh\(\);\s*\}")
        notifier = (BACKEND / "EmberBSDNotifier.cpp").read_text()
        self.assertIn("m_state.refresh()", notifier)
        self.assertNotIn("QProcess", notifier)
        self.assertNotIn("QNetwork", notifier)


if __name__ == "__main__":
    unittest.main()
