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
- Target acceptance: pending for the reconstructed source set. Host bootstrap
  tests and EmberBSD GCC16 execution are separate scopes.
