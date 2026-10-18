# NNG source provenance

NNG 1.12.3 is the maintained stable release used for KiCad IPC.
The source keeps the MIT license and upstream copyright notices.

| Input | Pin |
| --- | --- |
| Archive | `https://github.com/nanomsg/nng/archive/refs/tags/v1.12.3.tar.gz` |
| Commit | `73f715235967afc783e0b99c52d015dc10897fda` |
| SHA256 | `036a925790034efdeef8a6803f3e4402c3ab509383326f8bc2f15ecee75a2fa2` |

`patches/drain-before-free.patch` adapts three upstream commits by Garrett D'Amore:

- [Separate AIO shutdown from deallocation](https://github.com/nanomsg/nng/commit/8fa3b2aa8e9191669f137be39ba61ad39243483a).
- [Drain AIO, task and reap subsystems](https://github.com/nanomsg/nng/commit/71e459eea31e9e47c0ce64a78e32b242d357f9a0).
- [Reset the reaper on reinitialization](https://github.com/nanomsg/nng/commit/2c98a72d5135a09bcb860eed06b3029d27b7c797).

The adaptation retains stable 1.x implicit initialization, private initialization
signatures and prepared-task completion rules. The upstream sleep/finalization
tests retain their cancellation and reap assertions. Repeated finalization is
valid in 1.x and needs no 2.x `nng_init()` call. A queue also drains before its
individual release, including release after failed thread initialization.
The stop assertion remains active. The reaper exit flag resets before a new
worker starts, so sequential library lifecycles keep their cleanup worker.

The change affects private lifecycle code. It preserves the public headers,
ABI major 1, protocol implementations, compatibility API and feature defaults.
The Windows reaper call uses the same renamed private drain function.
Native source validation, ordinary package validation and target execution
have separate acceptance boundaries.
