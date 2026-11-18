# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""The --distdir option of the shared source producers.

A producer gets one archive with --archive, or the distfiles directory with
--distdir. With a directory, the producer selects the archive that its recipe
names. The Distdir type keeps the two cases apart.
"""
import os


class Distdir(str):
    """A distfiles directory, given with --distdir."""


def select(archive, name):
    """Return the archive path: ARCHIVE, or NAME in the Distdir ARCHIVE."""
    if not isinstance(archive, Distdir):
        return archive
    if not os.path.isabs(archive) or not os.path.isdir(archive):
        raise ValueError(f'the distfiles directory {archive} is not an absolute directory')
    path = os.path.join(archive, name)
    if not os.path.isfile(path):
        raise ValueError(f'{name} is not in the distfiles directory {archive}')
    return path
