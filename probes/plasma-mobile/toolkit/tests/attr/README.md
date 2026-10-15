# attr 2.6.0nb1 checks

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
ruby ../attr-package.rb /absolute/attr-2.6.0nb1.tgz
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

The macOS/GCC16 cross package passes ordinary pkgsrc staging checks.
`libattr.so.1` retains all 14 exported functions from the previous package.
The first 2.6.0 archive passed those checks but was rejected on installation:
its helpers retained the host sort wrapper path. Its SHA256 was
`c7a0eabf8ba2bd7ff37555297cebe83a4661d4cd91b90fd5a06f462b9a760e80`.
Revision nb1 selects target sort through the shared cross-pkginstall patch.
The [actual install-script check](../../../../../profiles/common-build-tools/tests/cross-install-scripts.rb)
rejects that control archive and checks directory/configuration lifecycle.
The corrected nb1 archive SHA256 is
`458c855ed11ef2010957faf80376b2cdac0d1826eb66c4b28e13036d9aa5e746`.
Its 40 installed payload files and target helper paths pass on CM5.
No package metadata or payload is edited after packaging.

The public-header installation uses POSIX sed syntax. The old BSD-sed
cross package retained `EXPORT` tokens and fails the consumer's header check.
The new headers compile without defining that private token.
Build the consumer against the previous package's actual DSO:

```sh
ruby build-consumer.rb /absolute/staged/usr/pkg /absolute/extracted-old-package \
    /absolute/target-sysroot /absolute/cross-tools /absolute/new-consumer-output
```

Extract the old package's headers and `libattr.so*` into its own directory.
The builder checks both headers, ELF SONAME and exports before linking.
Copy the new package, compiled consumer and runner to the target.
Install the package normally, then run:

```sh
PKG_INFO=/usr/sbin/pkg_info PKG_ADMIN=/usr/sbin/pkg_admin \
    sh runtime.sh /usr/pkg /absolute/new-runtime-output /absolute/attr-abi-consumer
```

The runner resolves pkgtools through PATH or explicit PKG_INFO/PKG_ADMIN paths.
The runner checks installed files, package metadata, ordinary and recursive
CLI operations, and nofollow get/list/set/remove behavior on a real symlink.
The linked consumer checks file/fd attribute copying and CREATE/REPLACE flags.
Exit 77 means the selected filesystem does not support extended attributes.
It is not an acceptance result. The initial probe distinguishes ENOTSUP,
EOPNOTSUPP and ENOSYS from real access errors. EmberBSD's `vfs_xattr.c`
converts EOPNOTSUPP to the distinct ENOTSUP value for its xattr syscalls.
The root-filesystem run on CM5 reported this unsupported operation.
Installed package files and helpers pass there. On a separate FFS2ea image,
CREATE, duplicate rejection, REPLACE and direct reads pass. Library copying
fails because FFS returns length-prefixed names through `llistxattr`, which
requires NUL-terminated names. The kernel owns that correction.
The libattr runtime and complete CLI acceptance remain pending.

Run the errno regression against the actual consumer source:

```sh
ruby runtime-errors.rb runtime-consumer.c /absolute/staged/usr/pkg /absolute/new-error-check
```

It runs ASan/UBSan with distinct target errno values. Unsupported first calls
return 77. A permission error remains exit 1. No unsupported result is PASS.

Use a separate 4 MiB FFS2ea fixture when the root filesystem lacks xattrs:

```sh
# Root prepares the fixture; the named user runs the library and CLI checks.
sh runtime-ffs.sh /usr/pkg /absolute/new-fixture /absolute/attr-abi-consumer vnd0 developer
```

Select an existing unprivileged account and a free vnode disk. The wrapper
checks `vnconfig -l -m 1` before attachment and creates only a new image.
Its format follows the OS tests `tests/fs/ffs/t_extattr.c` and
`tests/sbin/fsck_ffs/t_extattr.sh`. It copies results out, unmounts and detaches
its device before deleting its image. A failed runtime or cleanup preserves the image.
It does not change the root filesystem. The board run exposed the FFS list-format defect above.
Tmpfs has no xattr vnode operations in the inspected OS source and is not a substitute.

GCC16 `-fanalyzer` processes all 19 selected upstream translation units.

Six fail to compile before the backend adaptation; all 19 compile afterwards.
No path-analyzer finding was added. Cppcheck 2.22 checks the same target
configuration; the changed backend and consumer pass its focused checks.
The wider upstream pass retains style findings and a reviewed alias-analysis
false positive at `walk_tree.c:new_dirname`: `n` and `newname` receive the same
malloc result, and the null check on `newname` guards their use.
GCC's existing char-subscript warnings retain their upstream locations;
the actual AArch64 compiler defines unsigned plain char.
