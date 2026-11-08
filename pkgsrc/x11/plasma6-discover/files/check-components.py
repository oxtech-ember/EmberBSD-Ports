#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.

"""Classify Plasma components the same way EmberBSDResource does.

The signed catalog row is PKGPATH, PKGNAME and catalog_role. Desktop binding
is separate and only exists for an installed launcher. This test reads the
backend sources so the exclusion list cannot drift from the cases below.
"""

import pathlib
import re
import unittest

ROOT = pathlib.Path(__file__).resolve().parent / "EmberBSDBackend"
RESOURCE = (ROOT / "EmberBSDResource.cpp").read_text()
BACKEND = (ROOT / "EmberBSDBackend.cpp").read_text()
CATEGORIES = (ROOT / "emberbsd-categories.xml").read_text()
BUTTON = (pathlib.Path(__file__).resolve().parent.parent / "patches" / "patch-discover_qml_InstallApplicationButton.qml").read_text()


def exclusion_list():
    match = re.search(r"const QStringList plasmaLibraryOrSdk = \{([^}]+)\}", RESOURCE)
    if match is None:
        raise AssertionError("component exclusion list is missing")
    return re.findall(r'QStringLiteral\("([^"]+)"\)', match.group(1))


EXCLUDED = set(exclusion_list())


def is_component(base, catalog_role, desktop):
    if desktop or catalog_role in {"library", "desktop"}:
        return False
    if not base.startswith("plasma6-") or base.startswith("plasma6-lib"):
        return False
    return base not in EXCLUDED


def catalog_state(action):
    if action == "upgrade":
        return "Upgradeable"
    if action == "available":
        return "None"
    if action in {"installed", "installed-newer", "version-uncompared"}:
        return "Installed"
    return "unset"


class ComponentPolicy(unittest.TestCase):
    def test_exclusion_list_is_the_signed_library_and_sdk_names(self):
        self.assertEqual(EXCLUDED, {
            "plasma6-kdecoration",
            "plasma6-kpipewire",
            "plasma6-kwayland",
            "plasma6-kwin-qtwaylandscanner",
            "plasma6-layer-shell-qt",
            "plasma6-plasma-activities",
            "plasma6-plasma-activities-stats",
            "plasma6-plasma-sdk",
            "plasma6-plasma5support",
            "plasma6-qqc2-breeze-style",
            "plasma6-union",
        })

    def test_milou_is_a_component_and_installed_state_is_not_a_reinstall(self):
        self.assertTrue(is_component("plasma6-milou", "package", False))
        self.assertEqual(catalog_state("installed"), "Installed")
        self.assertIn("m_component = !m_desktop && isPlasmaComponent", RESOURCE)
        self.assertIn("if (!desktop.isEmpty())", RESOURCE)

    def test_available_component_uses_the_same_signed_name(self):
        self.assertTrue(is_component("plasma6-powerdevil", "package", False))
        self.assertEqual(catalog_state("available"), "None")
        self.assertEqual(catalog_state("upgrade"), "Upgradeable")

    def test_desktop_application_is_not_duplicated_as_a_component(self):
        self.assertFalse(is_component("plasma6-spectacle", "package", True))
        self.assertFalse(is_component("plasma6-discover", "desktop", False))

    def test_libraries_sdk_and_unrelated_packages_are_excluded(self):
        self.assertFalse(is_component("plasma6-libplasma", "package", False))
        self.assertFalse(is_component("plasma6-plasma-sdk", "package", False))
        self.assertFalse(is_component("plasma6-kwayland", "package", False))
        self.assertFalse(is_component("kf6-kirigami", "package", False))
        self.assertFalse(is_component("curl", "package", False))
        self.assertFalse(is_component("plasma6-milou", "library", False))

    def test_uninstalled_plasma_application_stays_a_component_until_a_launcher_binds(self):
        # The signed catalog has no desktop metadata. An available Plasma
        # application is distinguishable from a component only after install.
        self.assertTrue(is_component("plasma6-spectacle", "package", False))

    def test_categories_keep_applications_and_all_packages(self):
        self.assertIn("<Name>All Applications</Name>", CATEGORIES)
        self.assertIn("<Name>Components</Name>", CATEGORIES)
        self.assertIn("<Category>components</Category>", CATEGORIES)
        self.assertIn("<Name>All packages</Name>", CATEGORIES)
        self.assertIn('category == QLatin1String("components")', RESOURCE)
        self.assertIn("return m_component;", RESOURCE)

    def test_search_keeps_application_and_package_filters(self):
        self.assertIn('matchesCategoryName(QStringLiteral("components"))', BACKEND)
        self.assertIn("if (!resource->isComponent())", BACKEND)
        self.assertIn("!resource->isDesktop()", BACKEND)
        self.assertIn('matchesCategoryName(QStringLiteral("packages"))', BACKEND)
        self.assertIn("void EmberBSDBackend::completePending()", BACKEND)
        self.assertIn("m_pending.append(PendingSearch{stream, filter})", BACKEND)
        self.assertIn("item.stream->deliver(match(item.filter))", BACKEND)
        self.assertIn("QTimer::singleShot(0, this, [this]", BACKEND)

    def test_states_and_transactions_stay_on_the_signed_catalog(self):
        self.assertIn('m_action == QLatin1String("installed")', RESOURCE)
        self.assertIn('m_action == QLatin1String("available")', RESOURCE)
        self.assertIn('m_action == QLatin1String("upgrade")', RESOURCE)
        self.assertIn("return refused(app, Transaction::InstallRole);", BACKEND)
        self.assertIn("return refused(app, Transaction::RemoveRole);", BACKEND)
        self.assertIn("Install stays unavailable until a verified helper exists", BUTTON)
        self.assertIn("Update stays unavailable until a verified helper exists", BUTTON)
        self.assertIn("displayName !== \"EmberBSD\"", BUTTON)
        self.assertIn("state === Discover.AbstractResource.Upgradeable", BUTTON)


if __name__ == "__main__":
    unittest.main()
