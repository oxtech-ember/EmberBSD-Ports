# Local AI CPU Kit Implementation Plan

> Execution: use superpowers:executing-plans in this session. Project instructions
> authorize the implementation, checks, scoped commits, and normal pushes.

**Goal:** Package and demonstrate llama.cpp and whisper.cpp on EmberBSD ARM64.

**Architecture:** pkgsrc owns native package operations; Ports contains only the
pinned base and local recipes. Examples supplies independently verified model
assets and offline smoke scenarios.

**Tech stack:** C/C++, CMake, pkgsrc, POSIX shell, curl, pkg_tools.

**Spec:** [Local AI CPU kit](local-ai-design.md).

## Global constraints

- CPU only; no host-specific tuning or implicit asset downloads.
- All new repository code and documentation is English and uses no Python.
- Models and upstream archives remain outside Git.
- Do not replace system libraries or change the active desktop session.
- Do not infer physical board support from VM results.

## Review focus

- Different bundled GGML versions must coexist without library collisions.
- Download interruption or a wrong hash must not produce a trusted model file.
- Missing models and nonzero inference exits must fail the smoke scenario.
- Server test timeout and cancellation must clean up only the test server.
- Stale build outputs and an unpinned pkgsrc tree must not count as new evidence.

## Tasks

### 1. Native package recipes

Files: `upstream/pkgsrc`, `.gitmodules`, `pkgsrc/local-ai/`,
`scripts/prepare-pkgsrc.py`, `profiles/ai-cpu/README.md`.

- [x] Pin pkgsrc and verify whether upstream already provides either engine.
- [x] Add ordinary Makefile, distinfo, DESCR, and PLIST recipes with exact source
      revisions, CPU settings, selected executables, and license installation.
- [x] Prepare an independent working tree; reject an existing destination or
      a submodule revision that differs from the recorded Git link.
- [x] Build packages natively and fix only demonstrated portability failures.
- [x] Inspect package contents and dependencies; test isolated installation,
      coexistence, executable startup, and removal with pkg_tools.

### 2. Independent model demonstration

Files in EmberBSD-Examples: `ai/local-inference/README.md`, `assets.tsv`,
`fetch-assets.sh`, `smoke.sh`, and scoped shell checks.

- [x] Pin a small GGUF model, a multilingual Whisper model, and a speech sample;
      record provenance, SHA256, size, and license.
- [x] Add explicit downloads and verify reuse, interrupted files, and bad hashes.
- [x] Exercise text generation, WAV transcription, and loopback HTTP inference
      using only local assets; bound server startup and terminate it on exit.
- [x] Test missing input and an engine failure, then record native timing,
      memory, output checks, and exact build/model identities.

### 3. Publish evidence and boundaries

- [x] Update Ports and Examples documentation with tested commands and limits.
- [x] Update the Russian wiki and the existing R1 entry without closing the
      wider agent, image, knowledge, or physical-board work.
- Integration policy: review scoped changes, commit in each owner repository,
  synchronize, and push normally without including unrelated parallel work.
