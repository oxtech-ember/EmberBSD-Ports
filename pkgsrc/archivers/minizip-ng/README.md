# minizip-ng compatibility sources

The compatibility callbacks in `patches/patch-compat_ioapi.c` and
`files/iowin32.{c,h}` originate in zlib 1.3.2 `contrib/minizip`. The donor
sources refer to `MiniZip_info.txt`, which is absent from that release. The
unmodified `files/MiniZip64_info.txt` is the attribution and background notice
included with that release. It and minizip-ng's own `LICENSE` are installed
under `share/licenses/minizip-ng`.
