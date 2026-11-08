# Netpbm 11.02.31 and dictionary lookup

Source: [upstream Stable SVN r5432](https://svn.code.sf.net/p/netpbm/code/!svn/bc/5432/stable/),
released 2026-10-25. Upstream distributes Stable through SVN, not release tarballs.
The recipe uses the public, unofficial `jwilk-mirrors/netpbm` Git mirror's immutable
commit `125b3245dabc345d5327cbb62e275a268b139388`; its `git-svn-id` is
`https://svn.code.sf.net/p/netpbm/code/stable@5432 9d0c8265-081b-0410-96cb-a4ca84ce46f8`.
Archive hashes are in `distinfo`. The version and patch input files are compared
with the official SVN revision. Existing pkgsrc-generated manual pages
remain a separately checksummed distfile. Upstream source licenses are preserved.

The common recipe includes the upstream portability patches and the native
generator/cross-script fixes formerly carried in the graphics export profile.

On Darwin, NetBSD and Linux, the default
dictionary for a loaded `libnetpbm.so[.*]` or `libnetpbm*.dylib` is
`../share/netpbm/rgb.txt`, relative to that library's resolved directory. A
private data anchor avoids function PLT/interposition addresses. A missing
dictionary in this layout is an error; it does not read a leftover producer
prefix. Explicit filenames and `RGBDEF` keep their upstream precedence.
Static executables and unsupported loader platforms retain `RGB_DB_PATH`.
The image-name check follows the existing GLib relocation approach; arbitrary
renamed shared libraries are outside this relocation contract.

Run the causal native check with the selected SDK Python and a built library:

```
python3 pkgsrc/graphics/netpbm/tests/relative-rgb.py /absolute/prefix/lib/libnetpbm.so.11
```

It copies the library into a temporary prefix, exercises the actual dictionary
API, and checks both overrides and missing-file refusal. It neither compiles
code nor modifies the supplied installation. Dependencies can still come from
the original native prefix; full signed-package relocation, static-consumer
behavior and target execution require their own acceptance.

The existing native/cross generator and script checks move unchanged into
`tests/netpbm-build-tools-cross.sh` and `tests/netpbm-cross-scripts.sh`.
