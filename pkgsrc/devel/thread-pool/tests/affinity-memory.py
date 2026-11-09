#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Extract the actual NetBSD cpuset helpers for a host memory-instrumented test."""
import argparse
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--header", type=Path, required=True)
parser.add_argument("--output", type=Path, required=True)
args = parser.parse_args()
source = args.header.read_text()
start = source.index("namespace detail\n{\n// Both native APIs")
end = source.index("} // namespace detail", start) + len("} // namespace detail")
template = Path(__file__).with_suffix(".cpp.in").read_text()
args.output.write_text(template.replace("@HELPERS@", source[start:end]))
