# Agent CLI toolchain profile

Console toolchain for AI agents driving EmberBSD devices (registry
item E17, first stage: search, data, repositories, transport).
Everything cross-builds on the development host and installs as
packages or static binaries on the board.

## Contents

| Tool | Version | Path |
|---|---|---|
| jq | 1.8.2nb2 | pkgsrc devel/jq |
| SQLite CLI | 3.54.1 | databases/sqlite3 (common-build-tools) |
| rsync | 3.5.0 | pkgsrc net/rsync |
| libarchive (bsdtar) | 3.8.9 | pkgsrc archivers/libarchive |
| git | 2.55.0nb1 | pkgsrc devel/git-base |
| yq | 4.54.1 | Go cross-build (pkgsrc has 4.1.2 — stale, forward-only rule) |
| shfmt | 3.14.1 | Go cross-build |
| miller (mlr) | 6.9.0 | Go cross-build |
| gh | 2.102.0 | Go cross-build |
| graphviz | 15.1.1 | pkgsrc graphics/graphviz |

The Go tools build with the host Go toolchain
(`CGO_ENABLED=0 GOOS=netbsd GOARCH=arm64 go install ...@version`) —
static, dependency-free ARM64 binaries. Versions are pinned upstream
tags; pkgsrc yq is deliberately bypassed as its recipe is behind.

## Build

The private MAKECONF includes the common build-tools cross profile
plus `profiles/agent-cli/mk.conf`; `bmake package` in each recipe
directory produces installable `.tgz` in `PACKAGES/All`. Go tools are
built by `scripts/build-go-tools.sh` into a single staging prefix.

## Validation

See the wiki receipt for the board-level acceptance scenario (JSON/YAML
parsing, CSV reshaping, git operations over SSH, rsync artifact
delivery — all without a PTY).
