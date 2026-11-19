#!/usr/bin/env python3
"""Check the equal-radius connection points in the bundled ECC83 demo."""

from argparse import ArgumentParser
from xml.etree import ElementTree


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("netlist", help="kicadxml export of ecc83-pp.kicad_sch")
    args = parser.parse_args()
    nets = ElementTree.parse(args.netlist).findall("./nets/net")
    # C1.2 and U1.4 are at (86.36, 60.96) and (60.96, 86.36) mm.
    # They belong to different nets despite being equidistant from the origin.
    expected = {
        "GND": {"C1.2", "P1.1", "P2.2", "P3.2", "R2.2", "R3.2", "R4.2"},
        "Net-(P4-PM)": {"P4.2", "U1.4", "U1.5"},
    }
    for name, pins in expected.items():
        matches = [net for net in nets if net.get("name") == name]
        if len(matches) != 1:
            raise SystemExit(f"{name}: expected one net, found {len(matches)}")
        actual = {f"{node.attrib['ref']}.{node.attrib['pin']}"
                  for node in matches[0].findall("node")}
        if actual != pins:
            raise SystemExit(f"{name}: expected {sorted(pins)}, found {sorted(actual)}")


if __name__ == "__main__":
    main()
