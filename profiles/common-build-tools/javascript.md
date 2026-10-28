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

Node's normal resolver finds sibling modules in `lib/node_modules`, including
scoped package names. Each source dependency therefore remains owned by one
common recipe and package. Source-only module packaging does not validate the
ABI, consumer API compatibility or target runtime behavior.
