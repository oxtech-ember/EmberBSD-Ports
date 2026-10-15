# attr 2.6.0 checks

The toolkit carries the current attr 2.6.0 source archive and its pinned SHA256.
The recipe derives from pkgsrc `fff4deb639a1a640476203c80f752fb77b6cb14b`.
Upstream 2.6.0 includes the old basename declaration patch.
The recipe keeps pkgsrc's man-page names and repairs both dependent aliases.

The private getfattr/setfattr backend uses EmberBSD's native xattr calls.
These two tools are single-threaded. Relative dirfd operations temporarily change
cwd and restore its descriptor and errno. A failed restore terminates the tool.
This backend is not a general threaded xattrat implementation or a new libc API.
The shared libattr implementation and its exported ABI retain upstream ownership.

Physical `setfattr --restore -P` requires openat2. This target reports ENOSYS
for that unsupported operation. It does not silently follow directory symlinks.
Filesystem extended-attribute support is a separate runtime requirement.

Run the archive check on the final normal package:

```sh
ruby ../attr-package.rb /absolute/attr-2.6.0.tgz
```

It checks both renamed regular pages, both symlinks, and their package metadata.
A matching archive and manifest with dangling aliases must fail this check.
The old attr 2.5.2 archive with SHA256
`825535084d1367de54540065a735359ebbfaecff8723770a280ddc421d7981d3`
fails on `man/man3/attr_getf.3`.

Run the host contract against source patched by the recipe:

```sh
ruby host-contract.rb /absolute/patched-attr-source /absolute/new-check-directory
```

The contract compiles the real four backend modules with syscall doubles.
It covers dirfd and cwd selection, absolute paths, nofollow dispatch, empty paths,
invalid flags, errno, failed directory changes, and fatal restore failures.
It also checks attribute names, buffers, sizes, CREATE and REPLACE flags.
ASan and UBSan check this execution on macOS. Valgrind and LeakSanitizer do not
support this host configuration. This contract does not test kernel xattrs.
