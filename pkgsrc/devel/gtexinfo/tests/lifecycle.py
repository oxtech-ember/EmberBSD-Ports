#!/usr/bin/env python3
"""Exercise a built native registrar in a new private Info directory."""
import argparse
import gzip
import pathlib
import subprocess


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('binary', type=pathlib.Path)
    parser.add_argument('work', type=pathlib.Path)
    args = parser.parse_args()
    binary = args.binary.resolve(strict=True)
    args.work.mkdir()
    work = args.work.resolve()

    def run(*arguments, success=True):
        result = subprocess.run([str(binary), *map(str, arguments)], text=True,
                                capture_output=True, timeout=30)
        assert (result.returncode == 0) == success, result
        return result.stdout

    assert '7.3' in run('--version').splitlines()[0]
    directory = work / 'dir'
    directory.write_text('This is the top of the INFO tree.\n\x1f\n'
                         'File: dir, Node: Top\n\n* Menu:\n\n'
                         'Other manuals\n* Other: (other). Keep this entry.\n')
    document = (b'This is a small Info document.\nINFO-DIR-SECTION Tools\n'
                b'START-INFO-DIR-ENTRY\n* Example: (example). Test manual.\n'
                b'END-INFO-DIR-ENTRY\n\x1f\nFile: example.info, Node: Top\n\nExample.\n')
    info = work / 'example.info'
    info.write_bytes(document)
    run('--info-dir=' + str(work), info)
    added = directory.read_text()
    assert added.count('* Example:') == 1 and '* Other: (other).' in added
    run('--info-dir=' + str(work), info)
    assert directory.read_text() == added
    run('--info-dir=' + str(work), '--delete', info)
    removed = directory.read_text()
    assert '* Example:' not in removed and '* Other: (other).' in removed
    run('--info-dir=' + str(work), '--delete', info)
    assert directory.read_text() == removed
    compressed = work / 'example.info.gz'
    compressed.write_bytes(gzip.compress(document, mtime=0))
    run('--info-dir=' + str(work), compressed)
    assert directory.read_text().count('* Example:') == 1
    run('--info-dir=' + str(work), '--delete', compressed)
    assert '* Example:' not in directory.read_text()
    assert '* Other: (other).' in directory.read_text()
    run('--this-option-does-not-exist', success=False)
    print('7 lifecycle checks pass: add, idempotent add, remove, repeated remove, '
          'compressed add/remove, unrelated entry preservation, invalid option')


if __name__ == '__main__':
    main()
