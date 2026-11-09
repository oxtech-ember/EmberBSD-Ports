#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Keep build-host paths out of staged target
# package metadata.
#
# A cross configure runs pkg-config with PKG_CONFIG_SYSROOT_DIR=CROSS_DESTDIR
# and may also run *-config scripts whose output already names a build
# sysroot (this one or an older tree). Packages copy those flags into .pc
# files, *-config scripts, CMake exports, libtool .la files, qmake mkspecs
# and Python sysconfig data. Rewrite selected sysroot spellings to target
# paths; a file that still names a build directory, another host volume,
# .buildlink or cross-tools after the rewrite is refused.
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

add_unique() {
	# $1 = list name via eval; append $2 if absent
	eval "case \" \$$1 \" in *\" \$2 \"*) return 0 ;; esac"
	eval "$1=\"\$$1 \$2\""
}

sysroots=$sysroot
all=$sysroot
preal=$(CDPATH= cd -- "$sysroot" 2> /dev/null && pwd -P) || preal=
[ -n "$preal" ] && [ "$preal" != "$sysroot" ] && sysroots="$sysroots $preal" && all="$all $preal"
for path in "$@"; do
	path=${path%/}
	all="$all $path"
	preal=$(CDPATH= cd -- "$path" 2> /dev/null && pwd -P) || preal=
	[ -n "$preal" ] && [ "$preal" != "$path" ] && all="$all $preal"
done
# macOS /tmp <-> /private/tmp aliases for every collected root.
_alias=
for root in $sysroots $all; do
	case "$root" in
	/tmp|/*) _alias="$_alias /private$root" ;;
	/private/tmp|/*) _alias="$_alias /tmp${root#/private}" ;;
	esac
done
for root in $_alias; do
	case " $sysroots " in *" $root "*) ;; *)
		case " $all " in *" $root "*) ;; *)
			# Prefer classifying /tmp aliases of the sysroot as sysroots.
			case " $sysroots " in
			*" ${root#/private} "*|*" /tmp${root#/private/tmp} "*|*" /private$root "*)
				sysroots="$sysroots $root" ;;
			esac
			;; esac ;;
	esac
	case " $all " in *" $root "*) ;; *) all="$all $root" ;; esac
done
# Ensure every sysroot spelling is also checked.
for root in $sysroots; do
	case " $all " in *" $root "*) ;; *) all="$all $root" ;; esac
done

sed_quote() {
	printf '%s\n' "$1" | sed -e 's/[.+*^$(){}?|\\[&]/\\&/g'
}

edit=
for root in $sysroots; do
	quoted=$(sed_quote "$root")
	# pkg-config / *-config flag forms.
	edit="$edit -e s#(-I|-L|-isystem[[:space:]]*)$quoted/#\\1/#g"
	# Absolute metadata under the sysroot (CMake, config scripts).
	edit="$edit -e s#$quoted/#/#g"
done
# Host cross-tools wrappers -> tool basename (any build tree).
edit="$edit -e s#/[^[:space:]\"]*/cross-tools/bin/([A-Za-z0-9._+-]+)#\\1#g"

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

while IFS= read -r file; do
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
	bad=0
	for dir in $all; do
		if grep -F -q -- "${dir%/}" "$file"; then
			echo "target-pkgconfig: ${file#"$destdir"} names build directory $dir:" >&2
			grep -F -n -- "${dir%/}" "$file" >&2 || :
			bad=1
		fi
	done
	grep -nE '/\.buildlink/|/cross-tools/|/Volumes/|/private/var/folders/|BigData/EmberBSD' "$file" \
		> "$scratch/hits" || true
	if [ -s "$scratch/hits" ]; then
		: > "$scratch/hits.real"
		while IFS= read -r hit; do
			body=${hit#*:}
			case "$body" in
			[[:space:]]*'#'*) continue ;;
			esac
			printf '%s\n' "$hit" >> "$scratch/hits.real"
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
