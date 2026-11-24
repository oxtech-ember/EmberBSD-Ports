# SPDX-License-Identifier: BSD-2-Clause
"""Check manifest discovery after moving the packaged Vulkan loader on Darwin."""
import argparse
import ctypes
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


class LayerProperties(ctypes.Structure):
    _fields_ = [
        ("name", ctypes.c_char * 256),
        ("spec_version", ctypes.c_uint32),
        ("implementation_version", ctypes.c_uint32),
        ("description", ctypes.c_char * 256),
    ]


def layer_names(loader):
    library = ctypes.CDLL(str(loader))
    enumerate_layers = library.vkEnumerateInstanceLayerProperties
    enumerate_layers.argtypes = [ctypes.POINTER(ctypes.c_uint32), ctypes.POINTER(LayerProperties)]
    enumerate_layers.restype = ctypes.c_int32
    count = ctypes.c_uint32()
    if enumerate_layers(ctypes.byref(count), None) != 0:
        raise RuntimeError("Cannot count Vulkan layers")
    layers = (LayerProperties * count.value)()
    if enumerate_layers(ctypes.byref(count), layers) != 0:
        raise RuntimeError("Cannot enumerate Vulkan layers")
    return [layer.name.decode() for layer in layers[:count.value]]


def install_manifest(directory, name):
    directory.mkdir(parents=True, exist_ok=True)
    manifest = {"file_format_version": "1.0.0", "layer": {
        "name": name, "type": "GLOBAL", "library_path": "./probe.dylib",
        "api_version": "1.0.0", "implementation_version": "1",
        "description": "Manifest discovery test",
    }}
    (directory / (name + ".json")).write_text(json.dumps(manifest))


def check(loader, stage):
    prefix = stage / "relocated SDK"
    destination = prefix / "lib" / loader.name
    destination.parent.mkdir(parents=True)
    shutil.copyfile(loader, destination)
    relative = Path("vulkan/explicit_layer.d")
    names = ["VK_LAYER_EMBER_data", "VK_LAYER_EMBER_xdg", "VK_LAYER_EMBER_etc"]
    for location, name in zip(["share", "etc/xdg", "etc"], names):
        install_manifest(prefix / location / relative, name)
    override = stage / "external layers"
    extra = "VK_LAYER_EMBER_override"
    install_manifest(override, extra)
    env = {k: v for k, v in os.environ.items() if not k.startswith(("VK_", "XDG_", "DYLD_"))}
    env["HOME"] = str(stage)
    def verify(additions, expected):
        run = subprocess.check_output([sys.executable, str(Path(__file__).resolve()), "--enumerate", destination],
                                      env=env | additions, cwd=stage, text=True)
        actual = {name for name in json.loads(run) if name.startswith("VK_LAYER_EMBER_")}
        if actual != expected:
            raise RuntimeError(f"Expected {sorted(expected)}, found {sorted(actual)}")

    verify({}, set(names))
    verify({"VK_LAYER_PATH": str(override)}, {extra})
    literal = stage / "@loader_path" / "xdg"
    user_layer = "VK_LAYER_EMBER_literal"
    install_manifest(literal / relative, user_layer)
    verify({"XDG_DATA_DIRS": "@loader_path/xdg", "XDG_CONFIG_DIRS": str(stage / "empty")}, {user_layer, names[2]})

    selected = {"control": "on", "name": extra, "path": str(override / (extra + ".json"))}
    settings = {"file_format_version": "1.0.0", "settings": {"layers": [selected]}}
    for location in ("etc/xdg", "etc", "share"):
        directory = prefix / location / "vulkan/loader_settings.d"
        directory.mkdir(parents=True, exist_ok=True)
        file = directory / "vk_loader_settings.json"
        file.write_text(json.dumps(settings))
        verify({}, {extra})
        file.unlink()
    print("Verified installed manifests and settings, XDG overrides, and literal user paths")



if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--enumerate", action="store_true")
    parser.add_argument("loader", type=Path)
    args = parser.parse_args()
    if args.enumerate:
        print(json.dumps(layer_names(args.loader)))
    else:
        with tempfile.TemporaryDirectory() as scratch:
            check(args.loader.resolve(strict=True), Path(scratch))
