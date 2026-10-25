#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD; real pkgtools regression, no synthetic package records.
set -eu
[ "$#" = 3 ] || { echo 'Usage: package-lifecycle.sh BUNDLE NEW_DESTROOT NEW_PACKAGE_OUTPUT' >&2; exit 2; }
: "${PKG_INFO:?Select absolute native pkg_info}"
: "${PKG_DELETE:?Select absolute native pkg_delete}"
: "${PKG_ADMIN:?Select absolute native pkg_admin}"
for tool in "$PKG_INFO" "$PKG_DELETE" "$PKG_ADMIN"; do case "$tool" in /*) ;; *) exit 2;; esac; done
recovery=${RECOVER_STALE_OWNERSHIP:-0}
case "$recovery" in 0|1) ;; *) echo 'RECOVER_STALE_OWNERSHIP must be 0 or 1' >&2; exit 2;; esac
bundle=$1 destroot=$2 packages=$3
here=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd -P)
sh "$here/../cross/package.sh" "$bundle" "$destroot" "$packages"
physical_db=$destroot/var/db/pkg
while IFS= read -r name; do
  contents=$physical_db/$name/+CONTENTS
  test -f "$contents"
  for pattern in $(cat "$bundle/$name/DEPENDENCIES"); do
    selected=$("$PKG_INFO" -K "$physical_db" -e "$pattern")
    test -n "$selected"
    grep -Fx "@pkgdep $pattern" "$contents" >/dev/null
    grep -Fx "@blddep $selected" "$contents" >/dev/null
  done
done < "$bundle/package-order.txt"
"$PKG_ADMIN" -K "$physical_db" dump | LC_ALL=C sort > "$packages/owners-installed.txt"
awk '{names[NR]=$0} END {for (i=NR; i>0; i--) print names[i]}' "$bundle/package-order.txt" > "$packages/remove-order.txt"
while IFS= read -r name; do
  "$PKG_DELETE" -P "$destroot" -K /var/db/pkg "$name"
  test ! -d "$physical_db/$name"
  while IFS= read -r path; do
    case "$path" in ''|@*) continue;; esac
    test ! -e "$destroot/usr/pkg/$path" && test ! -L "$destroot/usr/pkg/$path"
  done < "$bundle/$name/PLIST"
done < "$packages/remove-order.txt"
if "$PKG_INFO" -K "$physical_db" -a > "$packages/records-after-delete.txt"; then :; else test "$?" = 1; fi
test ! -s "$packages/records-after-delete.txt"
"$PKG_ADMIN" -K "$physical_db" dump > "$packages/owners-after-delete.txt"
mode=strict
if test -s "$packages/owners-after-delete.txt"; then
  if test "$recovery" != 1; then
    echo 'FAIL stale ownership after alternate-root deletion; select corrected common pkgtools' >&2
    exit 1
  fi
  # Explicit recovery for recorded old native pkg_delete. All real package
  # records and owned payloads are absent above. Reconstruct from +CONTENTS;
  # never delete a database manually or disable collision/dependency checks.
  "$PKG_ADMIN" -K "$physical_db" rebuild > "$packages/rebuild.log" 2>&1
  mode=explicit-stale-index-recovery
fi
"$PKG_ADMIN" -K "$physical_db" dump > "$packages/owners-after-recovery.txt"
test ! -s "$packages/owners-after-recovery.txt"
while IFS= read -r name; do
  "$PKG_ADD" -P "$destroot" -K /var/db/pkg "$packages/$name.tgz"
  test -f "$physical_db/$name/+CONTENTS"
done < "$bundle/package-order.txt"
"$PKG_ADMIN" -K "$physical_db" dump | LC_ALL=C sort > "$packages/owners-reinstalled.txt"
cmp "$packages/owners-installed.txt" "$packages/owners-reinstalled.txt"
# Create a genuine second package owning one existing payload file. A failed
# install must preserve the original bytes, ownership map and registrations.
first=$(sed -n '1p' "$bundle/package-order.txt")
conflict=sdr-conflict-fixture-1.0
fixture=$packages/conflict-fixture
mkdir "$fixture"
owned=
while IFS= read -r path; do
  case "$path" in ''|@*) continue;; esac
  if test -f "$bundle/$first/stage/usr/pkg/$path" && test ! -L "$bundle/$first/stage/usr/pkg/$path"; then owned=$path; break; fi
done < "$bundle/$first/PLIST"
test -n "$owned"
mkdir -p "$fixture/payload/$(dirname "$owned")"
cp "$bundle/$first/stage/usr/pkg/$owned" "$fixture/payload/$owned"
printf '@name %s\n%s\n' "$conflict" "$owned" > "$fixture/PLIST"
printf 'Deliberate ownership conflict regression\n' > "$fixture/DESCR"
sed -n '/^OPSYS=/p; /^OS_VERSION=/p; /^MACHINE_ARCH=/p; /^PKGTOOLS_VERSION=/p' "$bundle/$first/BUILD_INFO" > "$fixture/BUILD_INFO"
"$PKG_CREATE" -K "$physical_db" -u root -g wheel -p "$fixture/payload" -I /usr/pkg -c '-Deliberate conflict fixture' -d "$fixture/DESCR" -f "$fixture/PLIST" -B "$fixture/BUILD_INFO" "$fixture/conflict.tgz"
before=$("$SHA256" -q "$destroot/usr/pkg/$owned")
if "$PKG_ADD" -P "$destroot" -K /var/db/pkg "$fixture/conflict.tgz" > "$fixture/rejection.log" 2>&1; then
  echo 'FAIL real duplicate owner was accepted' >&2; exit 1
fi
grep -F "conflicting PLIST with $first:" "$fixture/rejection.log" >/dev/null
test ! -d "$physical_db/$conflict"
test "$before" = "$("$SHA256" -q "$destroot/usr/pkg/$owned")"
"$PKG_ADMIN" -K "$physical_db" dump | LC_ALL=C sort > "$packages/owners-after-conflict.txt"
cmp "$packages/owners-reinstalled.txt" "$packages/owners-after-conflict.txt"
printf 'PASS mode=%s: creation, dependency records, isolated remove/reinstall and real conflict rejection\n' "$mode"
echo 'Target execution, device enumeration and physical reception remain separate checks.'
