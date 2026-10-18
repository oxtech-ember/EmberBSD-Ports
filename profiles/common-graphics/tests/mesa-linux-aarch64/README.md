# Linux/GCC16 Mesa target evidence

These unedited logs record the [MesaLib 26.2.4nb9 acceptance](../../cross/mesa-linux-aarch64.md)
in the E34 EmberBSD/AArch64 VM on 2026-10-18.

- `render.log`: installed llvmpipe, shader rejection, triangle pixels and four EGL lifecycles.
- `upstream.log`: all 39 upstream invocations exit zero; one internal skip and nine disabled NIR cases are reported separately.
- `package-lifecycle.log`: UBSan consumer, wrong-renderer rejection, unchanged old consumer, real loader failure after deletion and successful reinstallation.
- `process-path.log`: genuine target executable-path failure before the repair and success after it, without procfs.

Expected negative controls retain their failure messages. They are required
rejections, not failed acceptance. The full build, host tests, source analysis
and memory logs are retained with the private build artifacts. No target
Valgrind or hardware GPU acceptance is claimed.
