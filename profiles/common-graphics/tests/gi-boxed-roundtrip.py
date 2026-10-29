#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Check scanner GIR round trips preserve functions on glib:boxed."""
import argparse
import io
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path
p = argparse.ArgumentParser()
p.add_argument('--scanner-root', type=Path, required=True)
p.add_argument('--real-gir', type=Path, required=True)
a = p.parse_args()
sys.path.insert(0, str(a.scanner_root))
from giscanner.girparser import GIRParser
from giscanner.girwriter import GIRWriter
core = 'http://www.gtk.org/introspection/core/1.0'
glib = 'http://www.gtk.org/introspection/glib/1.0'
real = ET.parse(a.real_gir).getroot()
boxed = next(node for node in real.iter('{%s}boxed' % glib)
             if node.get('{%s}name' % glib) and node.findall('{%s}function' % core))
namespace = real.find('{%s}namespace' % core)
minimal = ET.Element(real.tag, real.attrib)
small_ns = ET.SubElement(minimal, namespace.tag, namespace.attrib)
small_ns.append(boxed)
with tempfile.TemporaryDirectory() as tmp:
    source = Path(tmp)/'boxed.gir'
    ET.ElementTree(minimal).write(source, encoding='utf-8', xml_declaration=True)
    def render(path):
        parser = GIRParser(); parser.parse(str(path))
        return GIRWriter(parser.get_namespace()).get_encoded_xml()
    first = render(source)
    reparsed = Path(tmp)/'roundtrip.gir'; reparsed.write_bytes(first)
    second = render(reparsed)
    name = boxed.attrib['{%s}name' % glib]
    expected = [x.attrib['name'] for x in boxed.findall('{%s}function' % core)]
    result = ET.fromstring(second)
    parsed = next(x for x in result.iter('{%s}boxed' % glib) if x.attrib['{%s}name' % glib] == name)
    assert [x.attrib['name'] for x in parsed.findall('{%s}function' % core)] == expected
    assert first == second
    assert render(a.real_gir) == a.real_gir.read_bytes()
print('GI boxed static function minimal and real GIR roundtrip PASS')
