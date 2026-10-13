# Installed gettext 1.0 runtime checks

This bounded check uses 24 unchanged GNU gettext 1.0 shell tests.
[The case list](cases.tsv) covers PO/MO conversion, UTF-8, plural validation,
message contexts, duplicates, merge behavior, and reproducible output.
It also runs the original `autopoint-2` archive test and installed
`autopoint --help` and `autopoint --version`.

The separate Fcitx check uses the exact Fcitx5 5.1.23 diagnose startup
and translation functions, plus its original Russian catalog. Installed
`msgfmt` creates a local MO file. Installed `gettext` must return the
expected Russian translation through the real Fcitx function.
This does not accept an installed Fcitx daemon or graphical input session.

## Prepare and run

Use the verified source releases and a configured gettext source tree:

```sh
sh prepare.sh CONFIGURED_GETTEXT_SOURCE FCITX_SOURCE NEW_PAYLOAD
```

`upstream-sha256.tsv` pins each copied upstream file. Preparation fails if
any source differs. The original copyright and license files are included.
The source archives are GNU `gettext-1.0.tar.gz` and official Fcitx
`fcitx5-5.1.23.tar.zst`.

| Original archive | SHA256 |
| --- | --- |
| [GNU gettext 1.0](https://ftp.gnu.org/gnu/gettext/gettext-1.0.tar.gz) | `85d99b79c981a404874c02e0342176cf75c7698e2b51fe41031cf6526d974f1a` |
| [Fcitx5 5.1.23](https://download.fcitx-im.org/fcitx5/fcitx5/fcitx5-5.1.23.tar.zst) | `d287119db9dc3113bb3a2b0e78ce8670e064b744c14d3aaec69799374aadb00b` |

Source adaptation and runner code are AI-assisted
EmberBSD work. They have not been submitted upstream.

Transfer the payload. From macOS, omit extended attributes:

```sh
COPYFILE_DISABLE=1 tar --no-xattrs -czf gettext-tests.tar.gz -C PARENT PAYLOAD
```

Run as an ordinary user on EmberBSD with the current packages installed:

```sh
sh PAYLOAD/run.sh PAYLOAD NEW_WORK
```

The default prefix is `/usr/pkg`. The optional third argument selects a
native installed prefix for host validation. No source-tree program or base
gettext fallback is used. The runner installs nothing and uses no network.
Only child tests receive a private `HOME`; the runner preserves its caller's
`HOME`. It preserves each upstream status: 0 is PASS, 77 is SKIP, and others are
FAIL. It saves each log and `results.tsv`. Any failure makes the runner fail.
A SKIP is not an acceptance result for that feature. Tool versions are saved.

The original `init.sh`, `init.cfg`, and configured `init-env` retain their
upstream behavior. The selected cases do not use compiler, Go, Java, or
locale-helper variables from `init-env`. The runner binds the used `MSG*`
commands by verified prefix-first PATH and sets target-local source/build paths.
Basename invocation preserves the upstream expected diagnostic text.
The temporary `autotools` layout links the installed autopoint and archive.
This exercises its configured xz archive path without installing Autoconf.
Missing Autoconf produces the original explicit SKIP. Missing Bash or a
supported non-C UTF-8 locale makes only the Fcitx source-consumer case SKIP.

The full upstream corpus is not selected. The original `gettext-1/2`
cases and `msgfmt-1` require the noninstalled `tstgettext --env` helper. `lang-sh` cases
require a compiled `testlocale` helper. They are not silently rewritten to
use the installed CLI. No target fixture compilation is required here.
This runtime check does not replace C/C++ source analysis or Memcheck.

## CM5 acceptance

On 2026-10-13, the committed `0104de2` payload ran as an ordinary user on
physical EmberBSD/AArch64 CM5. Gettext-tools 1.0nb2 and gettext-lib 1.0 passed
all 24 selected original tests, both autopoint CLI checks and the Fcitx
source-consumer translation check. The result was 27 PASS, one SKIP and zero
failures. `autopoint-2` reported missing Autoconf; its archive path was not
accepted on this target. The complete run took approximately three seconds.
All 282 installed package entries passed the package integrity check.
Gettext-tools package SHA256:
`0cc5f96cb417e4dcf61f758aa4e1427d7c63d206c4a1d1b4e196635520d597f3`.
Gettext-lib package SHA256:
`5fc38f8e68c207e2e725fec4622be7910de83e368f3c9bf2ddcc13238afe7e93`.
No Valgrind, ASan or UBSan result is claimed for this target run.
