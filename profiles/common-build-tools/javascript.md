# Common JavaScript source modules

A pkgsrc recipe owns its module's upstream archive, version, checksums,
license, patches and package metadata. Include `../../mk/emberbsd-javascript.mk`
after setting `JS_MODULE_NAME` and the normal pkgsrc fields. The helper installs
the validated source at `${PREFIX}/lib/node_modules/<name>` and uses no Node
interpreter or online package installer during the build.

Declare each runtime dependency once as
`JS_MODULE_DEPENDS+= javascript-name=pkg-pattern:../../category/recipe`.
The helper emits the corresponding pkgsrc `DEPENDS` entry and verifies its
JavaScript name against `package.json` after patches. Required peer and
optional dependencies are included; optional peers remain optional. It rejects
nested `node_modules`, source symlinks, missing/extra dependency declarations
and a package name or version different from its owner recipe. A recipe that
needs a different installation or build behavior may use its own explicit
implementation rather than bypassing these checks.

A mandatory peer supplied by a consuming runtime may be declared with
`JS_MODULE_EXTERNAL_PEERS+= name`. The validator requires this name in
`peerDependencies`, rejects optional or duplicate peers and overlap with normal
or optional dependencies, and records the selection in `BUILD_DEFS`. The
installed `package.json` retains the upstream version range. Each consumer
must validate that range against its selected runtime or installed module;
missing, unknown or incompatible peers are errors. This declaration does not
install a peer in the host prefix or prove target compatibility.

Node's normal resolver finds sibling modules in `lib/node_modules`, including
scoped package names. Each source dependency therefore remains owned by one
common recipe and package. Source-only module packaging does not validate the
ABI, consumer API compatibility or target runtime behavior.

The shared `javascript-projection.py` inspects one installed prefix and its
pkgdb. Give it selected module roots and explicit external runtime versions.
It returns the installed source-module closure with package ownership and
source metadata, including the recorded SHA256 of the recipe distinfo file.
That value is not the checksum of an individual downloaded archive. It checks
each declared package dependency with the selected
`pkg_admin` and validates JavaScript and mandatory peer ranges with the prefix
common `semver` module. It does not choose, download or install
versions. Unknown peers, missing owners, unsafe module files and incompatible
ranges fail. Consumers can copy only the returned source modules and must keep
external target runtimes outside the host prefix.
