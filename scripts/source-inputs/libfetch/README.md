# Common libfetch source

The pkgsrc `net/libfetch` recipe keeps its source in `files/`, without a
distfile. This owner exports the pinned pkgsrc tree with all common overlays,
then publishes that effective FILESDIR as an SDK prepared source tree. The
receipt identifies `net/libfetch` and its effective recipe inputs. It does
not replace the recipe or its patches.

Use the selected SDK and explicit source tools:

```sh
python3 -B scripts/source-inputs/libfetch/source.py --sdk-source /path/to/sdk-source --git /path/to/git prepare --patch /path/to/patch --output /new/libfetch --scoped-identity
python3 -B scripts/source-inputs/libfetch/source.py --sdk-source /path/to/sdk-source --git /path/to/git verify-source --source /new/libfetch
```

An existing shared export can be selected with `--pkgsrc-export` and the same
explicit patch tool. New shared exports record a snapshot of the libfetch FILESDIR; preparation
checks its contents and execute modes without another full pkgsrc export.
A legacy receipt without a snapshot requires a canonical export for comparison.
The caller owns the export; the snapshot detects accidental changes, not an
authenticated or adversarially protected directory.
The consumer generates error headers in its object tree;
the prepared source remains read-only. Run `test-source.py` with the selected
Python, SDK source, Git and prepared source paths for its focused verification.
