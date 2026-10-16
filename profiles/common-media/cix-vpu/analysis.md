# Media diagnostic analysis

These checks cover the native M2M header selection, its semaphore cleanup fix
and the four diagnostic C units. They do not audit an entire multimedia stack.
The upstream source pins remain FFmpeg 9.0.2 and gst-plugins-good 1.28.8.
The owning recipes preserve source hashes and upstream licences.

| Check | Scope and observed result |
|---|---|
| GCC 16.2.0 cross compiler | Real EmberBSD/AArch64 headers, source-generated FFmpeg configuration, actual build flags. The three original diagnostics compile with `-Wall -Wextra -Werror -fanalyzer`. The lifecycle regression receives the same checks. |
| GCC `-fanalyzer` | All six imported FFmpeg M2M C modules before and after native selection, plus the changed semaphore module after its fix. No new defect diagnostic. Some buffer paths exceed the analyzer's state limit; `-Wanalyzer-too-complex` remains visible. |
| Clang Static Analyzer 19.1.7 | Actual AArch64 target headers and defines, plus matching Linux before/after configurations. Two upstream findings repeat before/after: a possibly null queue buffer and zero-length `mmap` from invalid driver metadata. They are not hidden or claimed fixed. |
| Cppcheck 2.17.1 | Real compilation databases, target include paths and GCC16 predefined macros. Linux before/after native selection each produce the same 22 findings. AArch64 produces 21 of these findings, including nine dependency-header shift reports. The new diagnostic bodies have no finding; their included FFmpeg/GLib/GStreamer headers produce 11 inherited reports. |
| Valgrind Memcheck 3.24.0 | Linux x86-64, actual patched FFmpeg M2M code, origin tracking and all leak kinds counted as errors. Eight initialization refusals and four semaphore normal/failure cases pass with no suppression. |
| GStreamer Memcheck | The actual upstream V4L2 plugin loads. No invalid access or definite, indirect or possible lost allocation is reported. GLib/GType retains 174,183 reachable bytes in 1,869 blocks. Counting every reachable allocation as an error makes the strict run fail. No suppression or clean-Memcheck claim is made. |

The Clang queue findings depend on state and metadata supplied by a future driver.
Ports owns follow-up analysis with the upstream FFmpeg implementation.
They were already present before this portability patch. The header change does
not alter that queue logic. Missing-device checks cannot exercise mapped buffers.
Cppcheck's remaining reports concern upstream control flow, const/scope style
and dependency inline functions. Full logs retain their locations and identifiers.
No diagnostic category was disabled to obtain a green result.

The semaphore fault was reproduced by actual EmberBSD execution: the first
missing-device decoder unwind received SIGSEGV before returning to the caller.
The unmodified Linux path concealed this because zeroed Linux semaphores happen
to survive `sem_destroy`. A regression against the real old static archive
observes zero initialization calls and one invalid destruction call.
The fixed path initializes once and reports a real `sem_init` error unchanged.
It never destroys a semaphore after failed initialization.

The corrected AArch64 target run passes eight real initialization refusals,
four semaphore lifetime cases and actual GStreamer plugin loading without
a HEVC hardware factory. The guest has no compiler or video device.
This execution and CIX board acceptance remain separate evidence.
NetBSD/AArch64 is not a supported Valgrind execution platform in this setup.
The Linux run verifies equivalent real userland source and POSIX lifetime paths;
it does not check kernel code, CIX firmware, MMIO or physical DMA.
