# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted).
"""Chromium-only unstable feature policy for the selected common stable Rust."""
SUPPORTED_RELEASE = '1.99.1'


def apply(environment, verbose_version):
    """Return a scoped producer environment without modifying the caller's map.

    The caller obtains verbose_version from the selected native rustc -vV.
    Ordinary crates retain -Zallow-features=; allocator exceptions are explicit
    in the ordered source patch. This is not another toolchain or release channel.
    """
    lines = verbose_version.splitlines()
    fields = {}
    for line in lines[1:]:
        if ': ' in line:
            key, value = line.split(': ', 1)
            if key in fields:
                raise ValueError('duplicate Rust version field: ' + key)
            fields[key] = value
    if (not lines or not lines[0].startswith('rustc ' + SUPPORTED_RELEASE + ' (') or
            fields.get('release') != SUPPORTED_RELEASE or fields.get('binary') != 'rustc'):
        raise ValueError('Chromium unstable policy requires selected stable Rust ' + SUPPORTED_RELEASE)
    selected = dict(environment)
    selected['RUSTC_BOOTSTRAP'] = '1'
    return selected, lines[0]
