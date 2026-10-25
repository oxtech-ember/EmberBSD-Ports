# Thread locale acceptance contract

CJS 140.1 needs the POSIX thread locale selector in EmberBSD libc.
A Ports wrapper cannot replace dispatch through the calling thread's locale.
The [interface probe](tests/thread-locale.c) is a consumer acceptance test.
The selector, its ABI and native libc tests belong to the operating system.

## Required behavior

The probe selects a global C locale and a thread locale with a comma radix.
It checks selection, query, previous-handle returns and `LC_GLOBAL_LOCALE`
restoration. It also checks locale duplication and concurrent thread isolation.
`localeconv()`, `nl_langinfo()` and `strtod()` must use the thread selection.
`setlocale()` must continue to query the global locale.
Selected locale objects are restored before their handles are freed.

`EMBERBSD_TEST_NOOP_USELOCALE` injects a selector that always returns
`LC_GLOBAL_LOCALE`. The same interface checks must reject that build.
No production source uses this fault injection.

## Build and run

Select the compiler, sysroot and all subordinate tools with the
[SDK tool contract](https://github.com/oxtech-ember/EmberBSD-SDK/blob/main/docs/tool-selection.md).
For target acceptance, use the qualified GCC16 cross compiler and matching
EmberBSD sysroot. For host diagnostics, use the qualified native GCC16 SDK.
Do not replace a missing SDK tool with a compiler from the host PATH.

From this directory, use absolute paths for the selected inputs and outputs:

```sh
"${SDK_CC:?}" --sysroot="${SDK_SYSROOT:?}" -std=c11 -Wall -Wextra -Werror \
  -pthread tests/thread-locale.c -o "${PROBE_OUTPUT:?}"
"${SDK_CC:?}" --sysroot="${SDK_SYSROOT:?}" -std=c11 -Wall -Wextra -Werror \
  -pthread -DEMBERBSD_TEST_NOOP_USELOCALE tests/thread-locale.c \
  -o "${PROBE_NOOP_OUTPUT:?}"
```

Run each executable on its matching OS and CPU with `de_DE.UTF-8` as its
argument. Another installed comma-radix locale is also valid.
The normal build must exit 0. The no-op build must exit 1 with a failed
selection check. Exit 77 means the required locale is absent; it is not a pass.
Keep a time limit on each run and retain its output and exit status.

## Acceptance limits

This recovery restores the source contract. It does not supply `uselocale()`.
The current EmberBSD libc lacks that interface, so target compilation and
execution are not accepted. A qualified native GCC16 SDK is also required
before fresh host execution, fault-injection and memory checks can be accepted.
Historical host results do not qualify a different toolchain or target libc.

Static analysis can check this source without generating executable objects.
It does not prove thread-local libc dispatch. Valgrind or ASan/UBSan checks
must accompany execution on a supported platform before runtime acceptance.
The probe does not cover ctype tables, multibyte conversion, locale-allocation
failure paths or the full CJS interpreter. See the separate
[CJS cleanup checks](VALIDATION.md).

The recovered source passed Cppcheck 2.22.0 and Clang Static Analyzer 21.0.0
on Darwin arm64 with macOS 27.0 headers. Both the normal and no-op
configurations had no findings. Cppcheck used its POSIX model, C11 and
Unix64 platform. The path analysis used `--analyze -std=c11 -pthread`
with `-Wall -Wextra -Werror`, without executable output. This source-only
check has no target compilation database and does not validate EmberBSD headers.
