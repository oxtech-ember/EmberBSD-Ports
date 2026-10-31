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
explicit patch tool. Its receipt identity is the export key: the pinned pkgsrc
commit, the overlay inputs and the patch tool that produce the libfetch
FILESDIR. A matching key selects the export directly; neither preparation nor
`verify-source` reads FILESDIR again or makes another pkgsrc export. New
exports record a FILESDIR snapshot that preparation uses as the expected copy.
The caller owns the export; a different key is refused.
The consumer generates error headers in its object tree;
the prepared source remains read-only. Run `test-source.py` with the selected
Python, SDK source, Git and prepared source paths for its focused verification.
