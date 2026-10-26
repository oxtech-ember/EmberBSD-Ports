# NetBSD continuous bulk input

The shared libusb1 recipe carries an opt-in NetBSD backend adaptation.
Set `LIBUSB_NETBSD_BULK_READAHEAD` before opening a device handle. The value
is a comma-separated list of exact hexadecimal IN endpoint addresses, for
example `81` or `82,8f`. Endpoint zero, OUT addresses, duplicate addresses,
spaces, prefixes and empty values are rejected. An unset value disables it.
The selection is captured per handle, so later environment changes do not
change an existing handle.

This option is only for continuous streams that fill each USB request.
The ugen queue does not preserve USB short-packet boundaries. A short
transfer can stop its queue and its partial payload is not preserved.
Do not select a finite or request/response endpoint. The
backend enables ugen read-ahead before the first selected bulk input, with
a 1 MiB ring and a 64 KiB request. Input endpoints are configured even when
an earlier output opened the same endpoint-number file. Control, interrupt,
isochronous, OUT and unselected transfers retain their normal path. No
asynchronous cancellation support is added. Setup failures close the owned
endpoint and return the error without a silent fallback. Release and close
invalidate cached endpoint files and read-ahead state. Do not change device
configuration or alternate settings while a stream is active.

The actual backend-function fixture is in
`profiles/sdr-receivers/tests/libusb/netbsd-read-ahead.py`. Pass an absolute
patched `netbsd_usb.c` and a new output directory. Select native GCC16 with
`CC`, optional diagnostic `CFLAGS`, and the Darwin ABI input with `SDKROOT`.
It stubs OS calls, so it does not establish physical USB throughput.
The libiio USB text path requires short-packet-delimited responses and
is unsuitable for this option. This does not establish native IIO streaming.
Target build, package lifecycle and physical receiver acceptance are separate.
