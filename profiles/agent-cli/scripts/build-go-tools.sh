#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Cross-builds the agent CLI Go tools
# for NetBSD/aarch64 with the host Go toolchain. Static binaries, no
# runtime dependencies.
set -eu
[ "$#" -eq 1 ] || { echo 'Usage: build-go-tools.sh OUTPUT_PREFIX' >&2; exit 2; }
prefix=$1
case "$prefix" in /*) ;; *) echo 'Absolute prefix required' >&2; exit 2 ;; esac
command -v go >/dev/null || { echo 'host go required' >&2; exit 2; }
mkdir -p "$prefix/bin"
export CGO_ENABLED=0 GOOS=netbsd GOARCH=arm64 GOSUMDB=off
export GOPROXY=${GOPROXY:-https://proxy.golang.org,direct}
# Forward-only pins; bump tags upstream, never downgrade.
go install github.com/mikefarah/yq/v4@v4.54.1
go install mvdan.cc/sh/v3/cmd/shfmt@v3.14.1
go install github.com/cli/cli/v2/cmd/gh@v2.102.0
gobin=$(go env GOPATH)/bin/netbsd_arm64
for tool in yq shfmt gh; do
	cp "$gobin/$tool" "$prefix/bin/"
done
# miller's module path lacks the /v6 suffix required by `go install`.
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
curl -fsSL -o "$work/miller.tar.gz" \
	https://github.com/johnkerl/miller/archive/refs/tags/v6.9.0.tar.gz
tar -xzf "$work/miller.tar.gz" -C "$work"
(cd "$work/miller-6.9.0" && go build -o "$prefix/bin/mlr" ./cmd/mlr)
echo "Built: $prefix/bin"
