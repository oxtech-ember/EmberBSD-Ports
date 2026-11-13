#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Origin: EmberBSD contributors (AI-assisted).
"""Verify that Dawn's indexed toggle table exactly follows its enum order."""
import argparse
from pathlib import Path
import re

parser = argparse.ArgumentParser()
parser.add_argument('prepared_dawn', type=Path)
args = parser.parse_args()
root = args.prepared_dawn / 'src/dawn/native'
header = (root / 'Toggles.h').read_text()
source = (root / 'Toggles.cpp').read_text()
enum = header.split('enum class Toggle {', 1)[1].split('EnumCount,', 1)[0]
enum = re.sub(r'/\*.*?\*/|//[^\n]*', '', enum, flags=re.S)
names = re.findall(r'^\s*(\w+)\s*,\s*$', enum, flags=re.M)
table = source.split('kToggleNameAndInfoList = {{', 1)[1].split('\n}};', 1)[0]
entries = re.findall(r'\{Toggle::(\w+)\s*,', table)
if names != entries:
    for index in range(max(len(names), len(entries))):
        lhs = names[index] if index < len(names) else '<missing>'
        rhs = entries[index] if index < len(entries) else '<missing>'
        if lhs != rhs:
            raise SystemExit(f'toggle order mismatch at {index}: enum={lhs} table={rhs}')
    raise SystemExit('toggle table mismatch')
if 'VulkanUseHostMemoryForMappableBuffers' not in names:
    raise SystemExit('mappable-memory toggle is missing')
print(f'Dawn toggle enum/table PASS ({len(names)} entries)')
