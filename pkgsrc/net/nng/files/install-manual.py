"""Install man(1) pages using the upstream NNG 2 reference and symbol index."""
import os
import re
import subprocess
import sys
from pathlib import Path


def chapter_name(path):
    group, stem = path.parent.name, path.stem
    if group == "tools" and stem == "nngcat":
        return "nngcat", 1
    if group == "overview" and stem == "index":
        return "nng", 7
    if group == "api":
        return ("libnng" if stem == "index" else "nng-api-" + stem), 3
    if group in ("proto", "tran"):
        return ("nng-" + group if stem == "index" else "nng_" + stem), 7
    return None


def reference_pages(source):
    docs = source / "docs/ref"
    chapters = {}
    for path in sorted(docs.glob("*/*.md")):
        key = chapter_name(path)
        if key is not None:
            if key in chapters:
                raise ValueError(f"duplicate chapter {key}")
            chapters[key] = path
    headers = "\n".join(path.read_text() for path in (source / "include/nng").glob("*.h"))
    functions = set(re.findall(r"\b(nng_[a-zA-Z0-9_]+)\s*\(", headers))
    refs = re.findall(r"^\[\x60(nng_\w+)\x60\]: \.\./([^#\s]+)", (docs / "xref.md").read_text(), re.M)
    aliases = {}
    for symbol, relative in refs:
        chapter = chapter_name(Path(relative))
        if chapter not in chapters:
            raise ValueError(f"unknown chapter for {symbol}: {relative}")
        alias = (symbol, 3 if symbol in functions else 5)
        if alias not in chapters and aliases.setdefault(alias, chapter) != chapter:
            raise ValueError(f"conflicting index entries for {symbol}")
    return chapters, aliases


def manual_name(directory, key):
    name, section = key
    return directory / f"man{section}" / f"{name}.{section}"


def markdown(path):
    text = path.read_text().replace("{{#include ../xref.md}}", "")
    # mdBook discards hidden index terms and keeps the text of visible terms.
    text = re.sub(r"\{\{hi:[^}]+\}\}", "", text)
    text = re.sub(r"\{\{ii?:([^}]+)\}\}", r"\1", text)
    return re.sub(r"\[(\x60[^\x60\n]+\x60)\](?![\[(])", r"\1", text)


def main(source, output, formatter):
    chapters, aliases = reference_pages(source)
    for key, path in chapters.items():
        name, section = key
        dest = manual_name(output, key)
        dest.parent.mkdir(parents=True, exist_ok=True)
        command = [formatter, "-s", "-t", "man", "-M", f"title: {name}",
                   "-M", f"section: {section}", "-M", "source: NNG", "-o", str(dest)]
        subprocess.run(command, input=markdown(path), text=True, check=True)
    for alias, chapter in aliases.items():
        dest = manual_name(output, alias)
        dest.parent.mkdir(parents=True, exist_ok=True)
        target = manual_name(output, chapter)
        dest.symlink_to(os.path.relpath(target, dest.parent))


if __name__ == "__main__":
    main(Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3])
