#!/usr/bin/env python3
"""Validate the pinned Dawn feature restriction and adaptation contract."""
import os
from pathlib import Path
import subprocess
import tempfile

HERE = Path(__file__).resolve().parent
SCRIPT = HERE / "patch-dawn-netbsd-platform.sh"
ORIGINAL = "    if (!gpu_info::IsNvidia(GetVendorId()) && SupportsBufferMapExtendedUsages(mDeviceInfo)) {"


def run(*args, **kw):
    return subprocess.run(args, check=True, **kw)


def main():
    compiler = os.environ.get("CXX")
    if not compiler:
        raise SystemExit("Set CXX to the selected native C++ compiler")
    with tempfile.TemporaryDirectory(prefix="dawn-feature-test-") as tmp:
        root = Path(tmp)
        platform = root / "src/utils/platform.h"
        platform.parent.mkdir(parents=True)
        platform.write_text("#elif defined(__EMSCRIPTEN__)\n#else\n#endif\n")
        physical = root / "src/dawn/native/vulkan/PhysicalDeviceVk.cpp"
        physical.parent.mkdir(parents=True)
        physical.write_text(ORIGINAL + "\n"
                            "        EnableFeature(Feature::BufferMapExtendedUsages);\n"
                            "        // Now `kMapExtendedUsageMemoryPropertyFlags` contains exactly the flags that are required\n"
                            "        // for `BufferMapWriteExtendedUsages`.\n"
                            "        EnableFeature(Feature::BufferMapWriteExtendedUsages);\n"
                            "    }\n")
        run("sh", str(SCRIPT), str(root))
        patched = physical.read_text()
        run("sh", str(SCRIPT), str(root))
        assert physical.read_text() == patched, "patch is not idempotent"
        assert patched.count("netbsdRaven2MapStorageBroken &&") == 1
        # Compile the exact inserted predicate and condition, with fake adapter
        # inputs; both features share this condition in the pinned Dawn source.
        harness = root / "guard.cpp"
        harness.write_text("""unsigned parse(const char *s) { unsigned n = 0; while (*s) { char c = *s++; n = n * 10 + (c - '0'); } return n; }
namespace gpu_info { bool IsNvidia(unsigned v) { return v == 0x10de; } }
struct Info {} mDeviceInfo;
bool SupportsBufferMapExtendedUsages(Info) { return true; }
unsigned vendor, device; bool radv;
unsigned GetVendorId() { return vendor; }
unsigned GetDeviceId() { return device; }
bool IsAmdMesa() { return radv; }
bool enabled() {
""" + patched.split("        EnableFeature(", 1)[0] + """        return true;
    }
    return false;
}
int main(int argc, char **argv) {
    vendor = parse(argv[1]);
    device = parse(argv[2]);
    radv = parse(argv[3]);
    return enabled() == bool(parse(argv[4])) ? 0 : 1;
}
""")
        for netbsd in (False, True):
            binary = root / ("netbsd" if netbsd else "other")
            command = [compiler, "-std=c++17", str(harness), "-o", str(binary)]
            if netbsd:
                command.insert(1, "-D__NetBSD__")
            run(*command)
            for vendor, device, radv, expected in (
                ("4098", "5592", "1", "0" if netbsd else "1"),
                ("4098", "5592", "0", "1"),
                ("4098", "5593", "1", "1"),
                ("4099", "5592", "1", "1"),
            ):
                run(str(binary), vendor, device, radv, expected)
        # Mismatched and duplicate preimages must fail rather than silently ship.
        for source in ("changed upstream\n", ORIGINAL + "\n" + ORIGINAL + "\n"):
            physical.write_text(source)
            result = subprocess.run(["sh", str(SCRIPT), str(root)], capture_output=True)
            assert result.returncode != 0, "bad preimage accepted"
    print("Dawn mapped-feature guard: PASS")


if __name__ == "__main__":
    main()
