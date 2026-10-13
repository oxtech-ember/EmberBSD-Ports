# Shell profiles

The selected optional shells are **dash**, **mksh** and **zsh**. dash serves
lightweight POSIX scripts, mksh serves interactive device profiles, and zsh
serves desktop interactive profiles. The base `/bin/sh`, root login shell
and boot scripts keep their existing roles.

Ports are checked one shell at a time, with the common GCC16 compiler and
current shared dependencies. Host controls and EmberBSD acceptance have
separate evidence.

| Shell | Selected release | Current evidence |
| --- | --- | --- |
| dash | 0.5.13.5 | [GCC16 control, libedit and source repairs](dash.md) |
| mksh | R59c | Local recipe; its earlier target smoke used the base compiler and does not establish GCC16 package acceptance |
| zsh | 5.9.2 | Pinned pkgsrc recipe; separate current-dependency control pending |

The release manifests contain original URLs and SHA256 values. dash's
release archive from the pkgsrc distfile mirror also matches the original
SHA512 in pinned pkgsrc. A Git snapshot of the same tag has different archive
bytes and is not substituted for the release distfile.

## Prepare packages

Initialize the pinned pkgsrc submodule, then export the reviewed overlays:

```sh
git submodule update --init upstream/pkgsrc
sh profiles/shells/prepare-pkgsrc.sh /absolute/new-pkgsrc
```

The export includes the shared GCC 16.2 selection, current Libtool 2.6.2 and
Automake 1.19, dash patches, and libedit 20260512-3.1 with ncurses 6.6.
It replaces the existing dependency recipe instead of adding an older
parallel provider. The other host tools remain current in the pinned tree:
Autoconf 2.73, M4 1.4.21 and Perl 5.44.0.

On an appropriately prepared EmberBSD package build host:

```sh
cd /absolute/new-pkgsrc/shells/dash
bmake MAKECONF=/absolute/new-pkgsrc/EMBERBSD-SHELLS-MK.CONF package
```

This command describes the target package path. The Linux control builds
recorded here do not establish that package creation, installation or
removal has completed on EmberBSD. Do not replace a system or root shell
as part of a control build.

## Licenses

Preserve upstream licenses and attribution. The pinned dash recipe declares
`modified-bsd AND gnu-gpl-v2`; the profile is not uniformly permissive.
Optional zsh-completions and zsh-autosuggestions retain their own licenses.
The source patch headers identify local AI-assisted adaptations and their
upstream submission status.
