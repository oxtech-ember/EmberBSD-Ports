# Explicit common FFmpeg regression

Run `common-regression.py` with the selected host Python, compiler and the
ffprobe built from this recipe. Pass compiler include and link options with
`--cflag=<option>` and `--ldflag=<option>`, and pass the cdsc, rndr, fragment
init and fragment media test paths using the four named options shown by
`--help`. The test compiles `encryption-init-info.c`, exercises list cleanup
under a 256 KiB stack, verifies repeated appends and allocation failure, and
checks the MOV T.35 track and packets using the supplied fixtures. Chromium's
`media/test/data/agtm-metadata-*` fixtures cover those MOV cases; they are test
inputs, not package dependencies. This test is explicit and does not run during
ordinary package builds.

`upstream-regression.py` separately compiles `hdr-avstring-regression.c` with
explicit selected compiler and library flags, then uses the supplied `ffprobe`
with a local loopback RTSP server. It covers HDR saturation with and without
tone mapping, empty and normal replacements, and the eight-redirect limit.
The chosen FFmpeg build must enable the RTSP demuxer and TCP protocol. This
explicit test is not part of ordinary builds.
