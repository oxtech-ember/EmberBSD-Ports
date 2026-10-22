# Current spellchecking sources

Common graphics, media and Plasma source exports use Hunspell 1.7.5 and the
standard upstream US English dictionary from 2026.02.25. Native and cross builds
use the same versions. The existing ncurses UI and package features remain enabled.

The recipe adapts NetBSD pkgsrc
[commit 1bedf455e3e247da842df45adc0f3e8c61f95be4](https://github.com/NetBSD/pkgsrc/commit/1bedf455e3e247da842df45adc0f3e8c61f95be4).
It retains all six current portability patches and their original recipe names.
It uses C++14 and declares the
upstream test target and its Bash tool. It uses the official
[Hunspell 1.7.5 release asset](https://github.com/hunspell/hunspell/releases/tag/v1.7.5).
Its SHA256 is `2e559f0c2a592ba48e421477f58e9bf7e01062277a4a7821afb52fc9401010ae`.
The source archive includes generated release files. The normal recipe still runs
`autoreconf` after applying its portability patches.

The dictionary comes from the official
[en-wl release](https://github.com/en-wl/wordlist/releases/tag/rel-2026.02.25).
`hunspell-en_US-2026.02.25.zip` has SHA256
`ac8e73310e951d88c52c2cf2ba54ceaca34f8486a81630ac8a75dc5f931179f9`.
The package version is `20260225`, so it sorts above the previous `20060207`.
The data interface retains `en_US.aff`, `en_US.dic` and `README_en_US.txt` at their
existing installed paths. The dictionary contains 47,551 UTF-8 entries.

The original README contains the Kevin Atkinson SCOWLv2 permission notice and
the Geoff Kuenning affix-file notice. The latter requires modified source and
binary distributions to be marked. All three files remain unmodified.
The full original notices remain in the installed README. The recipe's existing
unset `LICENSE` metadata is unchanged. No generic license label or license
acceptance-policy change is asserted.

Source checks verify both official archive hashes, all filtered pkgsrc patch
hashes, zero-fuzz application of all six current patches, repeated-patch refusal,
the three-file dictionary inventory and its declared entry count. Real
`pkg_admin pmatch` confirms the package version order. The old `patch-ac`
correctly fails against this release; the current NetBSD replacement retains
its SunPro portability logic with the updated source context.

Package creation, upstream test results, source analysis and installed runtime
acceptance remain separate gates for each target architecture. This source update
does not claim successful tests from the NetBSD maintainer's historical comments.
It does not disable or mark failing tests as successful.
