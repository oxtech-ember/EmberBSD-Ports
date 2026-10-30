#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
"""Check standalone and opt-in embedder outputs from selected Node js2c."""
import argparse
from pathlib import Path
import subprocess
import tempfile


def run(args, *, ok=True):
    result = subprocess.run(args, capture_output=True, text=True, check=False)
    if (result.returncode == 0) != ok:
        raise AssertionError(f"unexpected exit {result.returncode}: {result.stderr}")
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--js2c", type=Path, required=True)
    parser.add_argument("--baseline-js2c", type=Path, required=True)
    parser.add_argument("--python", type=Path, required=True)
    parser.add_argument("--electron-js2c", type=Path, required=True)
    parser.add_argument("--process-lifetime", action="store_true")
    args = parser.parse_args()
    for value in (args.js2c, args.baseline_js2c, args.python, args.electron_js2c):
        if not value.is_absolute() or not value.is_file():
            parser.error(f"expected an absolute file path: {value}")

    with tempfile.TemporaryDirectory(prefix="node-js2c-test-") as directory:
        root = Path(directory)
        app = root / "internal/electron/js2c/node_init.js"
        app.parent.mkdir(parents=True)
        app.write_text("module.exports = 42;\n")
        run([str(args.python), str(args.electron_js2c), str(args.js2c),
             str(root), "electron_natives.cc", "internal/electron/js2c/node_init.js"])
        generated = (root / "electron_natives.cc").read_text()
        assert '{"internal/electron/js2c/node_init", BuiltinSource' in generated
        assert "LoadEmbedderJavaScriptSource" in generated
        assert "EmbedderRegisterExternalReferencesForInternalizedBuiltinCode" in generated
        assert "config_raw" not in generated

        bad = root / "bad.mjs"
        bad.write_text("export default 1;\n")
        failed_output = root / "invalid.cc"
        failure = run([str(args.js2c), str(failed_output), str(bad), "--only-js",
                       "--root", str(root)], ok=False)
        assert "--only-js requires" in failure.stderr
        assert not failed_output.exists()

        js = root / "internal/test.js"
        js.write_text("module.exports = 1;\n")
        config = root / "config.gypi"
        config.write_text("{}")
        outputs = []
        for name, binary in (("original.cc", args.baseline_js2c),
                             ("modified.cc", args.js2c)):
            output = root / name
            run([str(binary), str(output), str(js), str(bad), str(config),
                 "--root", str(root)])
            outputs.append(output.read_bytes())
        assert outputs[0] == outputs[1]
        assert b"LoadJavaScriptSource" in outputs[1]
        assert b"LoadEmbedderJavaScriptSource" not in outputs[1]
        if args.process_lifetime:
            for name, inputs, flags in (
                ("lifetime-node.cc", [str(js), str(bad), str(config)], []),
                ("lifetime-embedder.cc", [str(app)], ["--only-js"]),
            ):
                output = root / name
                run([str(args.js2c), str(output), *inputs, *flags,
                     "--process-lifetime", "--root", str(root)])
                text = output.read_text()
                assert "global_source_map = *new ThreadsafeCopyOnWrite<BuiltinSourceMap>{" in text
                assert "_resource = *new StaticExternal" in text
        print("JS2C embedder output, invalid input and standalone equivalence: PASS")


if __name__ == "__main__":
    main()
