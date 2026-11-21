# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
"""Generate an independent DOCX, edit it with the installed WordCraft CLI, and reopen it."""
import argparse
import json
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory
from xml.etree import ElementTree as ET
from zipfile import ZipFile, ZIP_DEFLATED

WORD = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS = {"w": WORD}
ROWS = [["Компонент", "Количество"], ["Датчик", "Два"]]
BEFORE = "Проект датчика"
AFTER = "Проект термометра"


def fixture(path):
    ET.register_namespace("w", WORD)
    doc = ET.Element(f"{{{WORD}}}document")

    def element(parent, name):
        return ET.SubElement(parent, f"{{{WORD}}}{name}")

    def paragraph(parent, text):
        element(element(element(parent, "p"), "r"), "t").text = text

    body = element(doc, "body")
    paragraph(body, BEFORE)
    tbl = element(body, "tbl")
    grid = element(tbl, "tblGrid")
    for _ in ROWS[0]:
        element(grid, "gridCol").set(f"{{{WORD}}}w", "2600")
    for cells in ROWS:
        row = element(tbl, "tr")
        for value in cells:
            paragraph(element(row, "tc"), value)
    element(body, "sectPr")
    with ZipFile(path, "w", ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml",
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/></Types>')
        archive.writestr("_rels/.rels",
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>')
        archive.writestr("word/document.xml", ET.tostring(doc, encoding="utf-8", xml_declaration=True))


def inspect(path, title):
    with ZipFile(path) as archive:
        doc = ET.fromstring(archive.read("word/document.xml"))
    def text(node):
        return "".join(t.text or "" for t in node.findall(".//w:t", NS))
    titles = [text(p) for p in doc.findall("w:body/w:p", NS)]
    tables = doc.findall("w:body/w:tbl", NS)
    if title not in titles or len(tables) != 1:
        raise ValueError(f"{path}: paragraphs={titles!r}, tables={len(tables)}")
    rows = [[text(cell) for cell in row.findall("w:tc", NS)] for row in tables[0].findall("w:tr", NS)]
    if rows != ROWS:
        raise ValueError(f"{path}: table changed to {rows!r}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cli", default="wordcraft-cli")
    parser.add_argument("--fixture", type=Path)
    args = parser.parse_args()
    if args.fixture:
        fixture(args.fixture)
        inspect(args.fixture, BEFORE)
    else:
        with TemporaryDirectory() as work:
            source, edited, reopened = (Path(work) / (name + ".docx") for name in ("source", "edited", "reopened"))
            fixture(source)
            inspect(source, BEFORE)
            command = "edit.replaceAll=" + json.dumps({"text": BEFORE, "with": AFTER}, ensure_ascii=False)
            subprocess.run([args.cli, "run", "--file", source, "--cmd", command, "--save", edited], check=True)
            inspect(edited, AFTER)
            subprocess.run([args.cli, "convert", edited, reopened], check=True)
            inspect(reopened, AFTER)
            print("Edited and reopened DOCX: Cyrillic title and all four table cells verified")
