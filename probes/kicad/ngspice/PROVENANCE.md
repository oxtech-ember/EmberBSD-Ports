# Provenance

- Upstream: [ngspice](https://ngspice.sourceforge.io/).
- Stable release: [47](https://ngspice.sourceforge.io/download.html), checked
  2026-10-18. Development snapshots are excluded.
- Archive URL and SHA256: [sources.tsv](sources.tsv).
- Copyright and licenses: preserve the complete upstream `COPYING` and
  per-file notices. ngspice combines BSD, GPL, LGPL and other licensed
  components; this probe does not replace those notices with one license.
- Local patches and integration code: EmberBSD, AI-assisted reconstruction
  against the pinned source. Each patch retains the upstream file's license.
  These patches are not represented as upstream-accepted changes.
- New native build: GCC 14.2.0 supplied by the host image; FFTW 3.3.11,
  Readline 8.3 and the matching host terminal runtime. This compiler is used
  only for bootstrap generators and Linux fixture checks.
- Native analyzers: GCC 14.2.0 `-fanalyzer`, Clang 19, Cppcheck 2.22.0 and
  Valgrind 3.24.0. See the README for completed checks and remaining gates.
- Target acceptance: both ordinary GCC16 AArch64 packages `47nb1` passed in a fresh
  EmberBSD guest: installed API18, CLI, KiCad exported divider, BSIM OpenMP,
  exact payload/provider hashes and normal removal/reinstallation.
  The installed library's memory query matches independent HW_PHYSMEM64
  without procfs diagnostics. Exact archive hashes and limits are in the
  [package acceptance record](../../../profiles/common-graphics/cross/ngspice.md).
  The target-memory patch changes only the procfs configure guard. The three
  upstream query modules passed a separate native GCC16 and EmberBSD regression.
- Memory-query source notices: preserve David Robert Nadeau's CC BY 3.0
  attribution and Holger Vogt's modification notice in the unchanged modules.
  The new contract and build helper use BSD-2-Clause. The configure patch
  retains upstream licensing. GCC16 `-fanalyzer`, Clang 19, Cppcheck 2.22.0
  and Valgrind 3.24.0 were used for this bounded follow-up.
