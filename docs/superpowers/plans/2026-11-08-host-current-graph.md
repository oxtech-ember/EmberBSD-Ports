# Host-Current Build Graph Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make a current host package a runtime-only leaf in the build-phase publication graph, using the frozen MAKECONF host `pkg_info` and the cross-bulk current-native rule.

**Architecture:** `--host-current` discovers `PKG_INFO`, `_HOST_PKG_DBDIR`, and the target `_PKG_DBDIR` through `pkgtools/pkg_install` bmake queries. It runs that absolute `pkg_info -K <host db> -e` for each host node. A current host node keeps only `DEPENDS` edges. The host database snapshot is hashed and must not change during the walk. Target nodes, mode-off closure, and `--native-make-variable` stay as they are.

**Tech Stack:** Python 3 exporter, fake bmake and fake `pkg_info` in `scripts/tests/test_export_build_graph.py`, EmberBSD SDK `lock_graph`.

**Spec:** This plan is the approved 18:43 MSK contract. It replaces the rejected receipt and `pkg_admin pmatch` design. Do not amend `540c7709`.

## Global Constraints

- Start from `origin/main` `98a92362`. Do not carry the rejected `--native-installed` code.
- Frozen Ports `4bb17114`, MAKECONF, and `state/389` archives stay byte-for-byte unchanged. `sources.ports` stays `4bb1`.
- Authority is live `pkg_info -e` against the selected host database. No receipt, no `pkg_admin pmatch`, and no soft-edge cut.
- `PKGBASE` is a side query. It is not stored in the hashed metadata dict, so mode-off node input hashes change only by the exporter file digest.
- Preserve `--native-make-variable` and its compiler-rt guard behavior.
- One ordinary commit. Do not push, merge, or open a pull request before independent review. Do not declare the graph ready to publish.

## Approved Behavior

Discovery, in order, with `MAKECONF=` set to the selected file and cwd irrelevant (`< /dev/null` equivalent: no stdin):

1. `bmake -C "$PKGSRCDIR/pkgtools/pkg_install" show-var VARNAME=EMBERBSD_NATIVE_TOOLSET_VERIFIED`
2. The same directory, passing that verified value and `USE_CROSS_COMPILE=no`, `show-var VARNAME=PKG_INFO`
3. The same native query for `VARNAME=_HOST_PKG_DBDIR`
4. The same verified value without `USE_CROSS_COMPILE=no`, `show-var VARNAME=_PKG_DBDIR`

`PKG_INFO` is word-split. It must be an absolute executable plus one absolute `-K` directory. That directory must resolve to `_HOST_PKG_DBDIR` and must not resolve to `_PKG_DBDIR`.

The name snapshot is `pkg_info -a -Q PKGNAME`, sorted by the exporter. It is evidence and the stability check, not the current decision. A second snapshot after the walk must be identical. Blank, whitespace, or duplicate names fail closed.

For each host node, read bmake `PKGBASE` and the already queried `PKGNAME`. If `PKGNAME` matches `PKGBASE-[0-9]*`, the pattern is `PKGBASE>=` plus the suffix after `PKGBASE-`. Otherwise the pattern is the bare `PKGBASE`. `pkg_info -e`: exit 0 current, exit 1 not current, any other status fails the export.

A current host node retains `DEPENDS` edges only. Do not query `BUILD_DEPENDS`, `TOOL_DEPENDS`, `BOOTSTRAP_DEPENDS`, `INDIRECT_BUILD_DEPENDS`, or `INDIRECT_DEPENDS`. In the build phase, `TEST_DEPENDS` still enters the side inventory and does not create a node or an edge. In the all phase, a current host node does not gain test edges.

Shared inputs, present only with the mode: `host-pkg-info-argv`, `host-pkg-info-binary`, `host-pkg-names`. Provenance gains `host current package database`.

## Tasks

- [x] Add failing exporter tests for the seven-edge cycle, current and old host versions, the five countercases, test inventory, and indirect dependencies.
- [x] Implement `--host-current` in `scripts/export-build-graph.py` and document the operator command.
- [x] Re-run `scripts.tests.test_export_build_graph` and confirm the new tests fail before the implementation and pass after it, with the existing suite still green.

## Required Results

- Mode off: full closure, and the seven-edge host bootstrap cycle still fails.
- Old installed versions fail with that same cycle.
- Installed versions at or newer than the tree pass, with every host node the walk can reach and with the runtime `DEPENDS` edges kept.
- Target `-K` is rejected. A target `DEPENDS` cycle still fails. Current coreutils and libtool-base alone do not break the cycle. A `PKGBASE` that is not the version suffix of `PKGNAME` uses the bare pattern. A database change during the walk writes no graph.
