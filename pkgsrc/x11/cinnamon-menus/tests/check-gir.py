#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
"""Check the CMenu GIR launch callback contract required by Cinnamon."""

import sys
import xml.etree.ElementTree as ET
from pathlib import Path


CORE = "http://www.gtk.org/introspection/core/1.0"
ROOT = "{" + CORE + "}"


def fail(message):
    raise SystemExit(f"FAIL: {message}")


def main():
    if len(sys.argv) != 2:
        fail("usage: check-gir.py CMenu-3.0.gir")

    path = Path(sys.argv[1])
    repository = ET.parse(path).getroot()
    namespace = repository.find(ROOT + "namespace")
    if namespace is None or namespace.get("name") != "CMenu":
        fail("missing CMenu namespace")

    includes = {item.get("name") for item in repository.findall(ROOT + "include")}
    if not {"Gio", "GioUnix"}.issubset(includes):
        fail("CMenu GIR must include Gio and GioUnix")

    method = namespace.find(".//" + ROOT + "method[@name='launch_uris_as_manager']")
    if method is None:
        fail("missing launch_uris_as_manager")
    if method.get("introspectable") == "0":
        fail("launch_uris_as_manager is not introspectable")

    parameters = method.find(ROOT + "parameters")
    if parameters is None:
        fail("launch_uris_as_manager has no parameter list")
    entries = list(parameters)
    by_name = {entry.get("name"): entry for entry in entries}
    non_instance = [entry for entry in entries if entry.tag == ROOT + "parameter"]
    expected = {
        "user_setup": ("GLib.SpawnChildSetupFunc", "async", "user_setup_data"),
        "pid_callback": ("GioUnix.DesktopAppLaunchCallback", "call", "pid_callback_data"),
    }
    for callback_name, (type_name, scope, closure_name) in expected.items():
        callback = by_name.get(callback_name)
        closure = by_name.get(closure_name)
        if callback is None or closure is None:
            fail(f"missing {callback_name} or {closure_name}")
        value_type = callback.find(ROOT + "type")
        if value_type is None or value_type.get("name") != type_name:
            fail(f"{callback_name} has the wrong callback type")
        if callback.get("scope") != scope:
            fail(f"{callback_name} has the wrong scope")
        try:
            closure_index = int(callback.get("closure", ""))
        except ValueError:
            fail(f"{callback_name} has no valid closure index")
        if (
            closure_index >= len(non_instance)
            or non_instance[closure_index].get("name") != closure_name
        ):
            fail(f"{callback_name} closure does not reference {closure_name}")

    print("PASS: CMenu launch callback types, scopes, and closure links are valid")


if __name__ == "__main__":
    main()
