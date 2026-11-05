# minizip-ng compatibility sources

The compatibility callbacks in `patches/patch-compat_ioapi.c` and
`files/iowin32.{c,h}` originate in zlib 1.3.2 `contrib/minizip`. The donor
sources refer to `MiniZip_info.txt`, which is absent from that release. The
unmodified `files/MiniZip64_info.txt` is the attribution and background notice
included with that release. It and minizip-ng's own `LICENSE` are installed
under `share/licenses/minizip-ng`.

The `classic-zip.c` owner regression exercises the MZ_COMPAT API with synthetic
UTF-8 names, legacy case flags, an empty entry, and an invalid archive. Run it
against the selected native or target `MINIZIP::minizip-ng` provider in a
temporary directory; it creates and removes only synthetic ZIP files.
