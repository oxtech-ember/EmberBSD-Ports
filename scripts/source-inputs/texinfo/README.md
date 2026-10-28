# Common Texinfo source for the OS C-only consumer

Prepare the `devel/gtexinfo` source from the current Ports export, including
all recipe patches. This prepared source is for the OS C-only producer; it is
not a complete Perl test tree and must not be used as a full Perl/text input.
The upstream Perl test fixture directory
`tta/perl/t/results/init_files_tests/add_lower_case_redirection_file_names`
contains case-colliding filenames and is omitted so preparation works on
case-insensitive filesystems. The regular Ports package retains its own full
upstream archive and package build. This omission does not change the patch set.

```sh
"$HOST_PREFIX/bin/python3.15" -B scripts/source-inputs/texinfo/source.py \
  --sdk-source "$SDK_SOURCE" --git "$GIT" prepare \
  --archive "$DISTFILES/texinfo-7.3.tar.xz" --patch "$HOST_PREFIX/bin/gpatch" \
  --output "$WORK/texinfo-source" --scoped-identity
"$HOST_PREFIX/bin/python3.15" -B scripts/source-inputs/texinfo/source.py \
  --sdk-source "$SDK_SOURCE" --git "$GIT" verify-source \
  --source "$WORK/texinfo-source" --patch "$HOST_PREFIX/bin/gpatch"
```

The output must not exist. Verification checks recipe identity, all patches,
and the prepared tree. When source inputs or the owner change, also supply the
current `--archive` to compare the effective payload. The generated configure
is authoritative: the preparation mirrors the recipe's `configure.ac` time
adjustment, and consumers copying the tree must preserve or restore it. This
operation neither builds nor installs Texinfo.
