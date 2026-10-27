# Shared TypeScript 7.0.2

This recipe builds the native compiler from upstream commit
`2bd066d87f5bafd315be9f40889d0a60b9e58e0b`. The npm 7.0.2 metadata names that
commit as `gitHead`. The commit belongs to `microsoft/typescript-go`, the source
repository used for this release. The npm metadata still names
`microsoft/TypeScript`; it is not the location of this historical commit.

The [stable npm metadata](https://registry.npmjs.org/typescript/7.0.2) and
[release source](https://github.com/microsoft/typescript-go/tree/2bd066d87f5bafd315be9f40889d0a60b9e58e0b)
are separate pinned inputs. The JavaScript distribution contains no native
compiler. The recipe builds `cmd/tsgo` with the common Go provider and uses
upstream's `noembed` release layout. The standard declarations are installed
beside that binary. The platform package resolves through Node's normal module
lookup; no downloaded optional native package is installed.

The recipe uses the standard pkgsrc Go module framework. All 34 module files
are declared in `go-modules.mk` and `distinfo`; upstream `go.sum` remains intact.
The build uses a file-backed module proxy and `GOTOOLCHAIN=local`. The native
Go tool and target Go environment remain separate in a cross profile.
Upstream's pure Go release selection uses `CGO_ENABLED=0`.

The package retains the complete upstream LICENSE and NOTICE.txt, including
notices for Go dependencies and the standard declaration data. The JavaScript
package also retains its upstream vendor notices.

TypeScript 7 does not provide the TypeScript 6 compiler API at
`lib/typescript.js`. Consumers of that API require a source migration. Do not
install a private old compiler as an automatic fallback. Chromium's CLI
consumers, declaration policy and API consumers require separate checks.
This recipe does not yet establish the full Electron WebUI build.

`bmake test` runs the real Node wrapper and native compiler. It checks the
release version, compilation and execution, strict type-error rejection with
no output, adjacent DOM declarations, and failure when the native binary is
missing. Cross test invocation refuses to run the target binary on the host.
These checks do not cover the complete upstream compiler test suite or target
runtime execution.
