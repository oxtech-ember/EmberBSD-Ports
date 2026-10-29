#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
"""Stored Waf cross-configure answers for Samba library recipes.

Waf's --cross-answers FILE looks up every target probe in FILE. A probe
without an answer is appended as UNKNOWN and configure fails, so a build
never runs anything on a target. Recipes keep one answers file per target
platform in files/cross-answers/PLATFORM.txt. It starts with an identity
header (Waf ignores '#' lines):

    # EmberBSD Waf cross answers 1
    # platform: NetBSD-11.0-aarch64
    # recipe: databases/tdb
    # package: tdb-1.4.15
    # answers-sha256: <SHA-256 of the answer lines>

replay  copies a stored file whose identity matches into the work directory.
store   normalizes the answers a capture configure recorded (Waf with both
        --cross-answers and --cross-execute appends each target answer) and
        writes PLATFORM/<category>_<name>.txt below a capture directory.

Only the standard library is used; run with python -B -E -S.
"""
import hashlib
import os
import re
import sys

MAGIC = '# EmberBSD Waf cross answers 1'
FIELDS = ('platform', 'recipe', 'package', 'answers-sha256')
# Waf's cross_answer() accepts these answer forms.
ANSWER = re.compile(r'(?:OK|YES|NO|FAIL|"[^\n]*"|\'[^\n]*\'|\(\s*-?\d+\s*,\s*"[^\n]*"\s*\))')
PATTERNS = {
    'platform': re.compile(r'[A-Za-z0-9]+-[0-9][A-Za-z0-9._]*-[a-z0-9_]+'),
    'recipe': re.compile(r'[a-z0-9][a-z0-9+_-]*/[A-Za-z0-9][A-Za-z0-9+._-]*'),
    'package': re.compile(r'[A-Za-z0-9][A-Za-z0-9+._-]*-[0-9][A-Za-z0-9._]*'),
}


class AnswersError(Exception):
    """Stored answers are absent, malformed or for another build."""


def body_lines(text):
    """Answer lines of a Waf answers file, validated, comments dropped."""
    seen = {}
    lines = []
    for number, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith('#'):
            continue
        if ':' not in line:
            raise AnswersError(f'line {number}: no answer')
        message, answer = (part.strip() for part in line.split(':', 1))
        if not message:
            raise AnswersError(f'line {number}: empty probe message')
        if answer == 'UNKNOWN':
            raise AnswersError(f'line {number}: unanswered probe: {message}')
        if not ANSWER.fullmatch(answer):
            raise AnswersError(f'line {number}: bad answer format: {answer}')
        normalized = f'{message}: {answer}'
        if message in seen:
            # Waf asks some probes twice; the answers must agree.
            if seen[message] != normalized:
                raise AnswersError(f'conflicting answers for: {message}')
            continue
        seen[message] = normalized
        lines.append(normalized)
    if not lines:
        raise AnswersError('no answers')
    return lines


def digest(lines):
    return hashlib.sha256(''.join(line + '\n' for line in lines).encode('utf-8')).hexdigest()


def identity(platform, recipe, package):
    values = {'platform': platform, 'recipe': recipe, 'package': package}
    for key, value in values.items():
        if not PATTERNS[key].fullmatch(value or ''):
            raise AnswersError(f'invalid {key}: {value!r}')
    return values


def render(ident, lines):
    header = [MAGIC] + [f'# {key}: {ident[key]}' for key in FIELDS[:3]]
    header.append(f'# answers-sha256: {digest(lines)}')
    return ''.join(line + '\n' for line in header + lines)


def parse(text):
    """Return (header fields, answer lines) of a stored file."""
    rows = text.split('\n')
    if rows[0] != MAGIC:
        raise AnswersError('not an EmberBSD Waf answers file')
    header = {}
    for key, row in zip(FIELDS, rows[1:1 + len(FIELDS)]):
        prefix = f'# {key}: '
        if not row.startswith(prefix):
            raise AnswersError(f'header lacks {key}')
        header[key] = row[len(prefix):]
    lines = body_lines('\n'.join(rows[1 + len(FIELDS):]))
    if header['answers-sha256'] != digest(lines):
        raise AnswersError('answers differ from their recorded checksum')
    if text != render(header, lines):
        raise AnswersError('stored answers are not normalized')
    return header, lines


def replay(ident, stored, output):
    if not os.path.isfile(stored):
        raise AnswersError(
            f'No stored Waf cross answers for {ident["platform"]} in {ident["recipe"]}: {stored}; '
            'capture them from an EmberBSD target (profiles/common-media/cross/waf-answers.md)')
    with open(stored, encoding='utf-8') as source:
        header, lines = parse(source.read())
    for key in FIELDS[:3]:
        if header[key] != ident[key]:
            raise AnswersError(f'stored answers are for {key} {header[key]}, not {ident[key]}: {stored}')
    with open(output, 'x', encoding='utf-8') as target:
        target.write(render(ident, lines))


def store(ident, answers, capture_dir, forbidden):
    with open(answers, encoding='utf-8') as source:
        text = source.read()
    lines = body_lines(text)
    for path in forbidden:
        if path and any(path in line for line in lines):
            raise AnswersError(f'captured answers contain a build path: {path}')
    directory = os.path.join(capture_dir, ident['platform'])
    os.makedirs(directory, exist_ok=True)
    name = ident['recipe'].replace('/', '_') + '.txt'
    path = os.path.join(directory, name)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    with os.fdopen(descriptor, 'w', encoding='utf-8') as target:
        target.write(render(ident, lines))
    print(f'Stored {len(lines)} Waf cross answers: {path}')


def main(argv):
    usage = ('usage: waf_answers.py replay PLATFORM RECIPE PACKAGE STORED OUTPUT | '
             'store PLATFORM RECIPE PACKAGE ANSWERS CAPTURE_DIR [FORBIDDEN_PATH...]')
    try:
        if len(argv) == 6 and argv[0] == 'replay':
            replay(identity(*argv[1:4]), argv[4], argv[5])
        elif len(argv) >= 6 and argv[0] == 'store':
            store(identity(*argv[1:4]), argv[4], argv[5], argv[6:])
        else:
            print(usage, file=sys.stderr)
            return 2
    except (AnswersError, OSError, UnicodeError) as error:
        print(f'ERROR: {error}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
