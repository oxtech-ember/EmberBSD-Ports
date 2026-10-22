# Flex epsilon-closure traversal

The common build-tools recipe carries Flex 2.6.4nb1. Its local source patch
replaces the recursive `mark_beginning_as_normal` traversal with a heap
worklist. This repairs the unbounded C call-stack consumption described in
[upstream issue 414](https://github.com/westes/flex/issues/414), associated
with CVE-2019-6293. It is a local repair, authored by OpenAI Codex (GPT-6).
The upstream issue remains open.

Each trailing-context state is marked when inserted. Each state enters the
worklist at most once. Normal-state barriers, non-epsilon terminals, cycles
and shared successors preserve their existing behavior. The worklist uses
one additional `int[current_mns]` allocation and constant C stack space.
The production allocator checks size overflow and fails explicitly.

The [recipe](../../profiles/common-build-tools/recipes/devel/flex) retains
the original archive, dependencies and package payload. Its patch checksum
uses pkgsrc's standard removal of NetBSD RCS identifier lines. The recipe
does not disable vulnerability checks or change a vulnerability feed.
Version-only feeds may still report the old advisory for this local package
revision. A release audit must evaluate the exact patch and its evidence.

## Checks

Run these checks on the build host with the actual patched source and GCC16:

```sh
python3 probes/flex-nfa/check.py /absolute/flex-2.6.4/src/nfa.c \
    --cc /usr/pkg/gcc16/bin/gcc
python3 probes/flex-nfa/consumer.py --flex /usr/pkg/bin/flex \
    --cc /usr/pkg/gcc16/bin/gcc
```

The first check extracts the production function. It compares 1006 graph
cases with a separate breadth-first reachability oracle, including a
200000-state valid graph. It also checks explicit rejection of an invalid
state. The unmodified source fails the non-recursion guard. The consumer
generates and compiles a scanner with trailing context, then checks normal,
empty and invalid-token inputs against independent expected results.

Native EmberBSD/amd64 GCC16.2 validation passes:

- Ordinary package build, staged install and package installation.
- All 114 upstream tests, with zero failed or skipped tests.
- All 1007 function checks and three installed scanner cases.
- The KHolidays 6.31 package consumer builds and installs using this Flex.
- GCC `-fanalyzer` on the extracted function and Clang Static Analyzer on
  the configured production translation unit report no findings.
- Cppcheck 2.22 reports the same 11 inherited style findings before and
  after the patch, with no new findings.

Memory-instrumented execution remains unverified. The tested GCC16 root
does not provide libasan or libubsan, and Valgrind is unavailable there.
The sanitizer check failed at link time; it is not a test pass. Cross
packaging and execution on other architectures remain unverified.
