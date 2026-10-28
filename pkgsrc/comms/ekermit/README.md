# E-Kermit

This common recipe packages the upstream E-Kermit 1.8 Unix sample program and
provides the same patched source to native OS consumers. It is distinct from
the C-Kermit package. The upstream source and its BSD three-clause license are
retained; the patchset carries forward the OS portability changes and corrects
diagnosed handling in the common source.

Version 1.8 corrects the reversed binary and text mode constants from 1.7.
`test-transfer.py` uses two local PTYs to send and receive an ordinary binary
file and an ordinary text file, checking the received bytes. Select the built
host executable and native prefix explicitly. This does not establish target
execution, serial hardware support, or interoperability with other programs.

The OS keeps its own native build and manual, and selects the prepared source
through the [common source helper](../../../scripts/source-inputs/ekermit/README.md).
