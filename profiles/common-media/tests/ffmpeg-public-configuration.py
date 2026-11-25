"""Check the build configuration that FFmpeg exposes in its public API."""

import argparse
import ast
import shlex
from pathlib import Path


def assignment(path, prefix):
    with path.open() as stream:
        for line in stream:
            if line.startswith(prefix):
                return line[len(prefix):].strip()
    raise SystemExit(f"{path.name}: missing {prefix}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("build", type=Path, help="configured FFmpeg build directory")
    parser.add_argument("--forbid-prefix", required=True)
    args = parser.parse_args()
    full = shlex.split(assignment(args.build / "ffbuild/config.mak", "FFMPEG_CONFIGURATION="))
    public = shlex.split(ast.literal_eval(assignment(args.build / "config.h",
                                                    "#define FFMPEG_CONFIGURATION ")))
    if any(args.forbid_prefix in value for value in public):
        raise SystemExit("the public FFmpeg configuration contains the producer path")
    for option in ("--host-cc=", "--host-ld=", "--cc=", "--nm=", "--extra-cflags="):
        if any(value.startswith(option) for value in public):
            raise SystemExit(f"the public FFmpeg configuration contains {option}")
    features = [value for value in full if value.startswith(("--enable-", "--disable-",
                "--arch=", "--cpu=", "--target-os=")) and "/" not in value]
    if not features or any(value not in public for value in features):
        raise SystemExit("the public FFmpeg configuration lost a selected feature or target")
    print(f"FFmpeg reports {len(features)} feature and target options")


if __name__ == "__main__":
    main()
