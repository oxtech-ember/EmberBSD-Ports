#!/usr/bin/env python3
"""Check the real Qt plugin path block with native and cross inputs."""

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import tarfile


SOURCE_SHA256 = "8c36b572613ccb0e35d39e87c044ac07e115c2de85bbdb646ffe4533af788a45"
TARGET_PLUGINS = "/usr/pkg/qt6/plugins"


def run(command, cwd):
    result = subprocess.run(command, cwd=cwd, capture_output=True, text=True)
    return {"command": command, "status": result.returncode,
            "stdout": result.stdout, "stderr": result.stderr}


def path_block(source):
    match = re.search(r"\n(?:lxqt_query_qt\(|if \(NOT DEFINED QT_PLUGINS_DIR\))", source)
    if not match:
        raise RuntimeError("The source plugin path block differs")
    end = source.index("\ninstall(TARGETS qtlxqt", match.start())
    return source[match.start():end]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--host-tools", type=Path, required=True)
    parser.add_argument("--qtpaths", type=Path, required=True)
    parser.add_argument("--cmake", type=Path, required=True)
    parser.add_argument("--patch", type=Path, required=True)
    parser.add_argument("--work", type=Path, required=True)
    args = parser.parse_args()
    if hashlib.sha256(args.archive.read_bytes()).hexdigest() != SOURCE_SHA256:
        parser.error("The original lxqt-qtplugin 2.4.0 archive differs")
    if args.work.exists():
        parser.error("The work directory must not exist")
    module = args.host_tools / "share/cmake/lxqt2-build-tools/modules/LXQtQueryQt.cmake"
    module_text = module.read_text()
    function = module_text[module_text.index("function(lxqt_query_qt "):]
    if not function.rstrip().endswith("endfunction()"):
        parser.error("The original LXQt query function differs")
    args.work.mkdir(parents=True)
    with tarfile.open(args.archive) as archive:
        archive.extractall(args.work, filter="data")
    root = args.work / "lxqt-qtplugin-2.4.0"
    original = (root / "src/CMakeLists.txt").read_text()
    patch = run([str(args.patch), "--batch", "--fuzz=0", "-p0", "-i",
                 str(Path(__file__).resolve().parent / "recipes/x11/lxqt-qtplugin/patches/patch-src_CMakeLists.txt")], root)
    if patch["status"]:
        raise RuntimeError("The source patch failed: " + repr(patch))
    candidate = (root / "src/CMakeLists.txt").read_text()
    query = run([str(args.qtpaths), "--query", "QT_INSTALL_PLUGINS"], args.work)
    if query["status"]:
        raise RuntimeError("The real native Qt query failed: " + repr(query))
    host_plugins = query["stdout"].strip()
    if not host_plugins.startswith("/") or host_plugins == TARGET_PLUGINS:
        raise RuntimeError("This causal cross test needs a distinct native plugin path")
    results = []
    for label, source, override, query_exe, expected in [
        ("baseline-native", original, None, args.qtpaths, host_plugins),
        ("candidate-native", candidate, None, args.qtpaths, host_plugins),
        ("baseline-cross-ignores-override", original, TARGET_PLUGINS, args.qtpaths, host_plugins),
        ("candidate-cross", candidate, TARGET_PLUGINS, args.qtpaths, TARGET_PLUGINS),
        ("candidate-empty-refusal", candidate, "", args.qtpaths, None),
        ("baseline-query-failure", original, None, Path("/usr/bin/false"), None),
        ("candidate-query-failure", candidate, None, Path("/usr/bin/false"), None),
        ("candidate-explicit-without-query", candidate, TARGET_PLUGINS, Path("/usr/bin/false"), TARGET_PLUGINS),
    ]:
        script = args.work / (label + ".cmake")
        output = args.work / (label + ".txt")
        script.write_text(function + path_block(source) +
                          '\nfile(WRITE "${RESULT_FILE}" "${QT_PLUGINS_DIR}")\n')
        command = [str(args.cmake), "-DQUERY_EXECUTABLE:FILEPATH=" + str(query_exe),
                   "-DRESULT_FILE:FILEPATH=" + str(output)]
        if override is not None:
            command.append("-DQT_PLUGINS_DIR:PATH=" + override)
        command += ["-P", str(script)]
        result = run(command, args.work)
        result["case"] = label
        if expected is None:
            if not result["status"] or output.exists():
                raise RuntimeError("The invalid path/query was accepted: " + repr(result))
        elif result["status"] or output.read_text() != expected:
            raise RuntimeError("The plugin path differs: " + repr(result))
        results.append(result)
    result = {"source_sha256": SOURCE_SHA256,
              "query_module_sha256": hashlib.sha256(module.read_bytes()).hexdigest(),
              "host_plugins": host_plugins, "target_plugins": TARGET_PLUGINS,
              "passed_cases": len(results), "cases": results,
              "scope": "actual-source-CMake-path-block; no target compile or package claim"}
    (args.work / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
