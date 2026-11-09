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
edit=
for root in $sysroots; do
	quoted=$(sed_quote "$root")
	# Flag forms.
	edit="$edit -e s#(^|[[:space:]=\"':,;])(-I|-L|-isystem[[:space:]]*)$quoted/#\\1\\2/#g"
	# Absolute path after a delimiter or at line start (CMake, assignments).
	edit="$edit -e s#(^|[[:space:]=\"':,;])$quoted/#\\1/#g"
done
# cross-tools wrappers, including the ICU double-slash form
#   .../cross-tools/bin//usr/bin/ar  -> ar
#   .../cross-tools/bin/aarch64--netbsd-ar -> aarch64--netbsd-ar
edit="$edit -e s#/[^[:space:]\"]*/cross-tools/bin/+([^/[:space:]\"]+/)*([A-Za-z0-9._+-]+)#\\2#g"
# .buildlink shared libraries -> /usr/pkg/lib/<soname> (target PREFIX layout).
edit="$edit -e s#[^[:space:]\"]*/\\.buildlink/lib/(lib[A-Za-z0-9._+-]+\\.so[A-Za-z0-9._*]*)#/usr/pkg/lib/\\1#g"
# Python sysconfig build-tree keys -> empty / neutral.
edit="$edit -e s#('abs_srcdir':[[:space:]]*)'[^']*'#\1''#g"
edit="$edit -e s#('abs_builddir':[[:space:]]*)'[^']*'#\1''#g"
edit="$edit -e s#('srcdir':[[:space:]]*)'[^']*'#\1''#g"
edit="$edit -e s#('COVERAGE_INFO':[[:space:]]*)'[^']*'#\1''#g"
edit="$edit -e s#('COVERAGE_REPORT':[[:space:]]*)'[^']*'#\1''#g"
edit="$edit -e s#('RUNSHARED':[[:space:]]*)'[^']*'#\1''#g"
edit="$edit -e s#(\"abs_srcdir\":[[:space:]]*)\"[^\"]*\"#\1\"\"#g"
edit="$edit -e s#(\"abs_builddir\":[[:space:]]*)\"[^\"]*\"#\1\"\"#g"
edit="$edit -e s#(\"srcdir\":[[:space:]]*)\"[^\"]*\"#\1\"\"#g"
edit="$edit -e s#(\"COVERAGE_INFO\":[[:space:]]*)\"[^\"]*\"#\1\"\"#g"
edit="$edit -e s#(\"COVERAGE_REPORT\":[[:space:]]*)\"[^\"]*\"#\1\"\"#g"
edit="$edit -e s#(\"RUNSHARED\":[[:space:]]*)\"[^\"]*\"#\1\"\"#g"

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
	-path '*/bin/*-config' \
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
		*-I/*|*-L/*|*isystem*|*.buildlink*|*cross-tools*|*sysroot*) return 0 ;;
		esac
		return 1
		;;
	esac
	case "$1" in
	*[Ll]ibs*=*|*[Cc]flags*=*|Libs.*:*|Cflags:*|Requires*:* ) return 0 ;;
	*INTERFACE_*|*LINK_LIBRARIES*|*IMPORTED_LOCATION*|*QMAKE_* ) return 0 ;;
	*AR=*|*CC=*|*CXX=*|*abs_srcdir*|*srcdir*|*host_tool=* ) return 0 ;;
	*-I/*|*-L/*|*isystem* ) return 0 ;;
	*.buildlink*|*cross-tools*|*sysroot* ) return 0 ;;
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
	# Python sysconfig: blank any remaining values that still name builder
	# roots, /sysroot/, .buildlink or cross-tools. Line-oriented so nested
	# quotes inside CONFIG_ARGS and similar keys are handled.
	case "$file" in
	*/_sysconfigdata*.py|*/_sysconfig_vars*.json)
		: > "$scratch/sysout"
		while IFS= read -r line || [ -n "$line" ]; do
			poison=0
			case "$line" in
			*/sysroot/*|*.buildlink*|*/cross-tools/*) poison=1 ;;
			esac
			if [ "$poison" = 0 ]; then
				for root in $all_check; do
					case "$line" in
					*"$root"*) poison=1; break ;;
					esac
				done
			fi
			if [ "$poison" = 1 ]; then
				# Blank the value; keep trailing comma when present.
				line=$(printf '%s\n' "$line" | sed -E \
					-e "s/^([[:space:]]*['\"][[:alnum:]_]+['\"][[:space:]]*:[[:space:]]*).*(,[[:space:]]*)?$/\\1''\\2/" \
					-e 's/^([[:space:]]*[[:alnum:]_]+[[:space:]]*:[[:space:]]*).*(,[[:space:]]*)?$/\\1""\\2/')
			fi
			printf '%s\n' "$line" >> "$scratch/sysout"
		done < "$file"
		if ! cmp -s "$scratch/sysout" "$file"; then
			if [ -w "$file" ]; then
				cat "$scratch/sysout" > "$file"
			else
				chmod u+w "$file"
				cat "$scratch/sysout" > "$file"
				chmod u-w "$file"
			fi
			echo "target-pkgconfig: neutralized python sysconfig paths in ${file#"$destdir"}"
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
				case "$body" in
				[[:space:]]*'#'*) continue ;;
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
	grep -nE "(^|[[:space:]=\"':,;]|-L|-I|-isystem[[:space:]]*)([^[:space:]\"]*/\.buildlink/|[^[:space:]\"]*/cross-tools/|/[^[:space:]\"]+/sysroot/)" "$file" > "$scratch/hits" || true
	if [ -s "$scratch/hits" ]; then
		: > "$scratch/hits.real"
		while IFS= read -r hit; do
			body=${hit#*:}
			case "$body" in
			[[:space:]]*'#'*) continue ;;
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
