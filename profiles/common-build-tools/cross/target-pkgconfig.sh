#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Keep build-host paths out of staged target
# package metadata.
#
# A cross configure runs pkg-config with PKG_CONFIG_SYSROOT_DIR=CROSS_DESTDIR
# and may also run *-config scripts whose output already names a build
# sysroot (this one or an older tree). Packages copy those flags into .pc,
# *-config, CMake, libtool .la, qmake and Python sysconfig files. Rewrite
# selected sysroot spellings to target paths; normalize cross-tools wrappers
# and .buildlink library paths; neutralize Python build-dir sysconfig keys;
# refuse leftover absolute host/build roots. Non-text staged files are skipped.
set -eu
[ "$#" -ge 2 ] || {
	echo 'Usage: target-pkgconfig.sh DESTDIR SYSROOT [BUILD_DIRECTORY...]' >&2
	exit 2
}
destdir=$1 sysroot=$2
shift 2
for path in "$destdir" "$sysroot" "$@"; do
	case "$path" in
	/?*) ;;
	*) echo "target-pkgconfig: not an absolute path: $path" >&2; exit 2 ;;
	esac
	case "$path" in
	*[!A-Za-z0-9_./+-]*) echo "target-pkgconfig: unsupported path: $path" >&2; exit 2 ;;
	esac
done
[ -d "$destdir" ] || exit 0
sysroot=${sysroot%/}

# Append $2 to list named by $1 if absent (space-separated).
add_unique() {
	eval "case \" \$$1 \" in *\" \$2 \"*) return 0 ;; esac"
	eval "$1=\"\$$1\${$1:+ }\$2\""
}

# Sysroot spellings used for rewrite (selected CROSS_DESTDIR + realpath).
sysroots=
add_unique sysroots "$sysroot"
preal=$(CDPATH= cd -- "$sysroot" 2> /dev/null && pwd -P) || preal=
[ -n "$preal" ] && add_unique sysroots "$preal"

# Extra build directories: fail-closed only (WRKDIR, TOOLDIR, ...).
builddirs=
for path in "$@"; do
	path=${path%/}
	add_unique builddirs "$path"
	preal=$(CDPATH= cd -- "$path" 2> /dev/null && pwd -P) || preal=
	[ -n "$preal" ] && add_unique builddirs "$preal"
done

# Real /tmp and /var aliases only (macOS /tmp -> /private/tmp, etc.).
# IMPORTANT: case patterns use /tmp/* not /tmp|/* — the latter is (/tmp/|*) and
# matches every path because | separates case alternatives.
_alias=
for root in $sysroots $builddirs; do
	case "$root" in
	/tmp|/tmp/*)
		add_unique _alias "/private$root"
		;;
	/private/tmp|/private/tmp/*)
		add_unique _alias "/tmp${root#/private}"
		;;
	/var|/var/*)
		if [ -d "/private$root" ] || [ -L "/private$root" ]; then
			add_unique _alias "/private$root"
		fi
		;;
	/private/var|/private/var/*)
		add_unique _alias "/var${root#/private}"
		;;
	esac
done
for root in $_alias; do
	# Classify alias with the same family as the path it aliases.
	case "$root" in
	/tmp|/tmp/*|/private/tmp|/private/tmp/*|/var|/var/*|/private/var|/private/var/*)
		# If any existing sysroot shares the non-private twin, keep as sysroot.
		twin=$root
		case "$root" in
		/private/*) twin=/${root#/private/} ;;
		/tmp/*|/var/*) twin=/private$root ;;
		esac
		case " $sysroots " in
		*" $twin "*|*" $root "*) add_unique sysroots "$root" ;;
		*) add_unique builddirs "$root" ;;
		esac
		;;
	esac
done

# Longest-first order so a longer spelling is not partially eaten by a shorter
# alias (e.g. /tmp/x before /private/tmp/x would leave /private/...).
sort_longest_first() {
	# Print words of $1 one per line, longest first.
	printf '%s\n' $1 | awk '{ print length, $0 }' | sort -nr | awk '{ $1=""; sub(/^ /,""); print }'
}

sysroots=$(sort_longest_first "$sysroots" | tr '\n' ' ')
builddirs=$(sort_longest_first "$builddirs" | tr '\n' ' ')
all_check=
for root in $sysroots $builddirs; do
	add_unique all_check "$root"
done
all_check=$(sort_longest_first "$all_check" | tr '\n' ' ')

sed_quote() {
	printf '%s\n' "$1" | sed -e 's/[.+*^$(){}?|\\[&]/\\&/g'
}

# Build sed edits: only sysroot spellings are rewritten to target paths.
# Use anchored boundaries: start of string or a delimiter before the root.
# Also handle --sysroot=<root> with or without a trailing slash.
edit=
for root in $sysroots; do
	quoted=$(sed_quote "$root")
	# --sysroot=<root> first (with or without a trailing path) so a later
	# exact-root rewrite cannot leave a dangling --sysroot=.
	edit="$edit -e s#(^|[[:space:]])--sysroot=$quoted(/[^[:space:]\"]*)?##g"
	# Flag forms (-I/-L/-isystem) with trailing slash.
	edit="$edit -e s#(^|[[:space:]=\"':,;])(-I|-L|-isystem[[:space:]]*)$quoted/#\1\2/#g"
	# Absolute path after a delimiter, with trailing slash.
	edit="$edit -e s#(^|[[:space:]=\"':,;])$quoted/#\1/#g"
	# Exact root token without trailing slash. Omit '=' from the leading
	# delimiter class so --sysroot=<root> is not reduced to --sysroot=.
	edit="$edit -e s#(^|[[:space:]\"':,;])$quoted(\"|[[:space:]]|$|[;',)])#\1\2#g"
done
# cross-tools and target-tools wrappers, including the ICU double-slash form
#   .../cross-tools/bin//usr/bin/ar   -> ar
#   .../target-tools/bin//usr/bin/ar  -> ar  (os-tools stage handoff)
#   .../cross-tools/bin/aarch64--netbsd-ar -> aarch64--netbsd-ar
edit="$edit -e s#/[^[:space:]\"]*/(cross|target)-tools/bin/+([^/[:space:]\"]+/)*([A-Za-z0-9._+-]+)#\\3#g"
# .buildlink shared libraries -> /usr/pkg/lib/<soname> (target PREFIX layout).
# Match only the path token itself: stop at whitespace, quotes, (), ; so
# unquoted if(/path/.buildlink/lib/libX.so) keeps the if( and trailing ).
edit="$edit -e s#/[^[:space:]\"'();]*/\\.buildlink/lib/(lib[A-Za-z0-9._+-]+\\.so[A-Za-z0-9._*]*)#/usr/pkg/lib/\\1#g"

# Host python for sysconfig transforms (fail closed if missing when needed).
_tp_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
_tp_sysconfig_py=$_tp_dir/target-pkgconfig-sysconfig.py
find_host_python() {
	for cand in \
		"${EMBERBSD_CROSS_HOST_PREFIX:+$EMBERBSD_CROSS_HOST_PREFIX/bin/python3.15}" \
		"${EMBERBSD_CROSS_HOST_PREFIX:+$EMBERBSD_CROSS_HOST_PREFIX/bin/python3}" \
		"${TOOLBASE:+$TOOLBASE/bin/python3.15}" \
		"${TOOLBASE:+$TOOLBASE/bin/python3}" \
		python3.15 \
		python3
	do
		[ -n "$cand" ] || continue
		if command -v "$cand" >/dev/null 2>&1; then
			command -v "$cand"
			return 0
		fi
		if [ -x "$cand" ]; then
			printf '%s\n' "$cand"
			return 0
		fi
	done
	return 1
}

# Interpreter whose version matches a staged lib/pythonX.Y tree (for pyc).
find_matching_python() {
	ver=$1
	[ -n "$ver" ] || return 1
	for cand in \
		"${EMBERBSD_CROSS_HOST_PREFIX:+$EMBERBSD_CROSS_HOST_PREFIX/bin/python$ver}" \
		"${TOOLBASE:+$TOOLBASE/bin/python$ver}" \
		"python$ver" \
		"${EMBERBSD_CROSS_HOST_PREFIX:+$EMBERBSD_CROSS_HOST_PREFIX/bin/python3}" \
		"${TOOLBASE:+$TOOLBASE/bin/python3}" \
		python3
	do
		[ -n "$cand" ] || continue
		resolved=
		if command -v "$cand" >/dev/null 2>&1; then
			resolved=$(command -v "$cand")
		elif [ -x "$cand" ]; then
			resolved=$cand
		else
			continue
		fi
		if "$resolved" -c "import sys; raise SystemExit(0 if sys.version_info[:2] == tuple(map(int, '$ver'.split('.'))) else 1)"; then
			printf '%s\n' "$resolved"
			return 0
		fi
	done
	return 1
}
host_python=
if ! host_python=$(find_host_python); then
	host_python=
fi

status=0
scratch=$(mktemp -d "${TMPDIR:-/tmp}/target-pkgconfig.XXXXXX")
trap 'rm -rf "$scratch"' EXIT
find "$destdir" -type f \( \
	-path '*/pkgconfig/*.pc' -o \
	-name '*.la' -o \
	-name '*.cmake' -o \
	-name '*.prl' -o \
	-name '*.pri' -o \
	-path '*/mkspecs/*/qmake.conf' -o \
	-name '_sysconfigdata*.py' -o \
	-name '_sysconfig_vars*.json' -o \
	-path '*/bin/*-config' -o \
	-name 'Makefile.inc' -o \
	-name 'pkgdata.inc' -o \
	-path '*/lib/python*/config-*/Makefile' \
\) | sort > "$scratch/list"

# Return 0 if file looks like text metadata; 1 if binary (skip, leave alone).
is_text_file() {
	LC_ALL=C dd if="$1" bs=4 count=1 2>/dev/null > "$scratch/magic" || return 1
	sig=$(LC_ALL=C od -An -tx1 -N 4 "$scratch/magic" | tr -d " \n")
	case "$sig" in
	7f454c46*|feedface*|cefaedfe*|feedfacf*|cffaedfe*|cafebabe*) return 1 ;;
	esac
	LC_ALL=C dd if="$1" bs=512 count=1 2>/dev/null > "$scratch/head" || return 1
	raw=$(wc -c < "$scratch/head" | tr -d " ")
	nonul=$(LC_ALL=C tr -d "\000" < "$scratch/head" | wc -c | tr -d " ")
	[ "$raw" = "$nonul" ]
}

# Path-bearing line? Used so Description: text mentioning /Volumes is ignored.
path_bearing_line() {
	# Description/Name/Comment/URL prose is ignored unless it also carries flags.
	case "$1" in
	Description:*|Name:*|Comment:*|URL:*|Homepage:*)
		case "$1" in
		*-I/*|*-L/*|*isystem*|*.buildlink*|*cross-tools*|*target-tools*|*sysroot*) return 0 ;;
		esac
		return 1
		;;
	esac
	case "$1" in
	*[Ll]ibs*=*|*[Cc]flags*=*|Libs.*:*|Cflags:*|Requires*:* ) return 0 ;;
	*INTERFACE_*|*LINK_LIBRARIES*|*IMPORTED_LOCATION*|*QMAKE_* ) return 0 ;;
	*AR=*|*CC=*|*CXX=*|*abs_srcdir*|*srcdir*|*host_tool=*|*--sysroot=* ) return 0 ;;
	*-I/*|*-L/*|*isystem* ) return 0 ;;
	*.buildlink*|*cross-tools*|*target-tools*|*sysroot* ) return 0 ;;
	esac
	# Absolute path after = or whitespace/quotes without using nested quotes in patterns.
	printf '%s\n' "$1" | grep -Eq "(^|[[:space:]\"'=])/(usr|opt|home|Volumes|private|tmp|Users|build)" && return 0
	return 1
}


while IFS= read -r file; do
	if ! is_text_file "$file"; then
		echo "target-pkgconfig: skipping binary file ${file#"$destdir"}"
		continue
	fi
	case "$file" in
	*/_sysconfigdata*.py|*/_sysconfig_vars*.json|*/lib/python*/config-*/Makefile)
		# Python sysconfig and lib/python*/config-*/Makefile via host
		# python helper only (no sed). Fail closed if the helper or host
		# python is missing when a sysconfig file is staged. After a
		# successful _sysconfigdata*.py sanitize, regenerate leftover
		# __pycache__ bytecode from the cleaned .py (plist-python.awk
		# lists those .pyc/.pyo files). A failed sanitize does not
		# rewrite or delete bytecode; the stage fails.
		if [ -z "$host_python" ] || [ ! -f "$_tp_sysconfig_py" ]; then
			echo "target-pkgconfig: host python (or target-pkgconfig-sysconfig.py) required to sanitize ${file#"$destdir"}" >&2
			status=1
			continue
		fi
		sys_args=
		for root in $sysroots; do
			sys_args="$sys_args --sysroot $root"
		done
		for root in $builddirs; do
			sys_args="$sys_args --builddir $root"
		done
		set -f
		# shellcheck disable=SC2086
		if ! "$host_python" "$_tp_sysconfig_py" "$file" $sys_args; then
			echo "target-pkgconfig: python sysconfig sanitize failed for ${file#"$destdir"}" >&2
			status=1
			continue
		fi
		set +f
		case "$file" in
		*/_sysconfigdata*.py)
			_sc_ver=${file##*/lib/python}
			_sc_ver=${_sc_ver%%/*}
			_sc_py=
			if ! _sc_py=$(find_matching_python "$_sc_ver"); then
				echo "target-pkgconfig: matching host python $_sc_ver required to regenerate sysconfig bytecode for ${file#"$destdir"}" >&2
				status=1
			else
				set -f
				# shellcheck disable=SC2086
				if ! "$_sc_py" "$_tp_sysconfig_py" --recompile-pyc "$file" --destdir "$destdir" $sys_args; then
					echo "target-pkgconfig: python sysconfig bytecode regenerate failed for ${file#"$destdir"}" >&2
					status=1
				fi
				set +f
			fi
			;;
		esac
		;;
	*)
		set -f
		# shellcheck disable=SC2086
		sed -E $edit "$file" > "$scratch/out"
		set +f
		if ! cmp -s "$scratch/out" "$file"; then
			if [ -w "$file" ]; then
				cat "$scratch/out" > "$file"
			else
				chmod u+w "$file"
				cat "$scratch/out" > "$file"
				chmod u-w "$file"
			fi
			echo "target-pkgconfig: removed build paths from ${file#"$destdir"}"
		fi
		;;
	esac
	bad=0
	# Fail closed on selected roots still present on path-bearing lines.
	for dir in $all_check; do
		if grep -F -n -- "${dir%/}" "$file" > "$scratch/root_hits" 2>/dev/null; then
			: > "$scratch/root_hits.real"
			while IFS= read -r hit; do
				body=${hit#*:}
				_cmt=$body
				while [ -n "$_cmt" ]; do
					case "$_cmt" in
					[[:space:]]*) _cmt=${_cmt#?} ;;
					*) break ;;
					esac
				done
				case "$_cmt" in
				\#*) continue ;;
				esac
				if path_bearing_line "$body"; then
					printf '%s\n' "$hit" >> "$scratch/root_hits.real"
				fi
			done < "$scratch/root_hits"
			if [ -s "$scratch/root_hits.real" ]; then
				echo "target-pkgconfig: ${file#"$destdir"} names build directory $dir:" >&2
				cat "$scratch/root_hits.real" >&2
				bad=1
			fi
		fi
	done
	# Generic host/build markers. Require an absolute-path delimiter or
	# -I/-L before the match so CMake templates like
	# ${CMAKE_NDK_ROOT}/toolchains/.../sysroot stay quiet.
	grep -nE "(^|[[:space:]=\"':,;]|-L|-I|-isystem[[:space:]]*)([^[:space:]\"]*/\.buildlink/|[^[:space:]\"]*/(cross|target)-tools/|/[^[:space:]\"]+/sysroot(/|[[:space:]\"';]|$))|--sysroot=/[^[:space:]\"]+" "$file" > "$scratch/hits" || true
	if [ -s "$scratch/hits" ]; then
		: > "$scratch/hits.real"
		while IFS= read -r hit; do
			body=${hit#*:}
			_cmt=$body
			while [ -n "$_cmt" ]; do
				case "$_cmt" in
				[[:space:]]*) _cmt=${_cmt#?} ;;
				*) break ;;
				esac
			done
			case "$_cmt" in
			\#*) continue ;;
			esac
			if path_bearing_line "$body"; then
				printf '%s\n' "$hit" >> "$scratch/hits.real"
			fi
		done < "$scratch/hits"
		if [ -s "$scratch/hits.real" ]; then
			echo "target-pkgconfig: ${file#"$destdir"} still names a build-host path:" >&2
			cat "$scratch/hits.real" >&2
			bad=1
		fi
	fi
	[ "$bad" = 0 ] || status=1
done < "$scratch/list"
exit "$status"
