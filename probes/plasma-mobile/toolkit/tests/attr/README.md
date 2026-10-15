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

The normal macOS/GCC16 cross package passes file, interpreter, permission,
PIE, RELRO, RPATH and build-path checks. `libattr.so.1` retains all 14
exported functions from the previous package. The final archive SHA256 is
`c7a0eabf8ba2bd7ff37555297cebe83a4661d4cd91b90fd5a06f462b9a760e80`.
Its upstream archive SHA256 is pinned in the toolkit source manifest.
No package metadata or payload was edited after packaging.

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
It is not an acceptance result. Physical board execution remains pending.

GCC16 `-fanalyzer` processes all 19 selected upstream translation units.
Six fail to compile before the backend adaptation; all 19 compile afterwards.
No path-analyzer finding was added. Cppcheck 2.22 checks the same target
configuration; the changed backend and consumer pass its focused checks.
The wider upstream pass retains style findings and a reviewed alias-analysis
false positive at `walk_tree.c:new_dirname`: `n` and `newname` receive the same
malloc result, and the null check on `newname` guards their use.
GCC's existing char-subscript warnings retain their upstream locations;
the actual AArch64 compiler defines unsigned plain char.
