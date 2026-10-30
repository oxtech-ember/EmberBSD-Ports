#!/bin/bash
# Build pkgpaths in order into the native Darwin SDK prefix with a clean env and SDK-only PATH.
# usage: EMBERBSD_ROOT=... X=.../pkgsrc [ACT="build install"] native-chain.sh cat/pkg ...
set -o pipefail
B=${EMBERBSD_ROOT:?set EMBERBSD_ROOT}; W=${EMBERBSD_WORK:-$B/work/bootstrap-work}; P=${EMBERBSD_SDK_PREFIX:-$B/sdk-native/llvm}; X=${X:?set X to the exported pkgsrc tree}
# Drop stale metadata-only work dirs (old .depends cookies cause false cycles).
case "${ACT:-build install}" in show-*) ;; *) for d in $W/obj/*/*/work; do [ -f $d/.depends ] && [ ! -f $d/.extract_done ] && rm -rf "$d"; done ;; esac
E=(env -i TMPDIR=$W USER=$USER PATH=$W/tools HOME=$HOME LOGNAME=$USER LC_ALL=C MAKECONF=$W/mk.conf GIT_OPTIONAL_LOCKS=0 GIT_NO_LAZY_FETCH=1 SHELL=$P/bin/mksh CONFIG_SHELL=$P/bin/mksh TZ=UTC PATH_SEPARATOR=:)
for pkg in "$@"; do
  echo "=== $(date '+%F %T') START $pkg (${ACT:-build install})"
  "${E[@]}" $P/bin/bmake -m $W/bound-mk SHELL=$P/bin/mksh MAKECONF=$W/mk.conf EMBERBSD_DARWIN_BOOTSTRAP=yes -C $X/$pkg ${ACT:-build install}; rc=$?
  if [ $rc -ne 0 ]; then echo "=== $(date '+%F %T') FAIL $pkg rc=$rc"; exit 1; fi
  case " ${ACT:-build install} " in *" install "*|*" replace "*)
    n=$("${E[@]}" $P/bin/bmake -m $W/bound-mk SHELL=$P/bin/mksh MAKECONF=$W/mk.conf EMBERBSD_DARWIN_BOOTSTRAP=yes -C $X/$pkg show-var VARNAME=PKGNAME)
    $P/sbin/pkg_info -K $P/pkgdb -qe "$n" || { echo "=== $(date '+%F %T') FAIL $pkg: $n not installed"; exit 1; };;
  esac
  echo "=== $(date '+%F %T') DONE $pkg"
done
