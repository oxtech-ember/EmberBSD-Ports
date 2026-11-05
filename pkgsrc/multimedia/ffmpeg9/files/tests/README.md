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
