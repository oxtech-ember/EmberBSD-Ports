#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). The export keeps one version of each family.
set -eu
[ "$#" = 2 ] || { echo "Usage: $0 EXPORTED_PKGSRC NEW_WORK" >&2; exit 2; }
pkgsrc=$1 work=$2
bmake=${BMAKE:-bmake}
mkdir "$work"
for kept in lang/python315 lang/lua55 lang/gcc16-libs lang/go127 lang/php85 \
    lang/ruby40 lang/openjdk21 databases/postgresql18-client \
    databases/mariadb118-client security/openssl lang/tcl x11/tk print/poppler-qt6 \
    graphics/opencv graphics/opencv-contrib; do
    [ -d "$pkgsrc/$kept" ] || { echo "Missing kept $kept" >&2; exit 1; }
done
for old in lang/python314 lang/lua54 lang/gcc10-libs lang/go126 lang/php84 \
    lang/ruby34 lang/openjdk17 databases/postgresql17-client \
    databases/mariadb114-client databases/mysql80-client security/libressl \
    lang/tcl90 x11/tk90 print/poppler-qt5 local-robotics/opencv5 \
    graphics/opencv-contrib-face; do
    [ ! -e "$pkgsrc/$old" ] || { echo "Old version $old exported" >&2; exit 1; }
    if grep -Eq "^SUBDIR[+]?=[[:space:]]+${old#*/}\$" "$pkgsrc/${old%/*}/Makefile"; then
        echo "Old version $old listed in ${old%/*}/Makefile" >&2; exit 1
    fi
done
printf 'BSD_PKG_MK=\tyes\n.include "%s/EMBERBSD-DEFAULTS-MK.CONF"\nall:\n' "$pkgsrc" \
    > "$work/Makefile"
reason() {
    "$bmake" -f "$work/Makefile" PKGPATH="$1" -v PKG_FAIL_REASON
}
for old in lang/python314 lang/lua54 lang/gcc15 databases/postgresql17-client \
    databases/mysql80-client security/libressl lang/go126 lang/php84 lang/tcl90 \
    x11/tk90 print/poppler-qt5 local-robotics/opencv5 graphics/opencv-contrib-face; do
    reason "$old" | grep -Fq 'EmberBSD keeps only' ||
        { echo "Guard accepted $old" >&2; exit 1; }
done
for kept in lang/python315 lang/lua55 lang/gcc16-libs databases/postgresql18-server \
    databases/mariadb118-server net/wireshark lang/go127 lang/go-bin lang/php85 \
    lang/tcl x11/tk lang/tclx x11/tktable graphics/opencv graphics/opencv-contrib; do
    [ -z "$(reason "$kept")" ] || { echo "Guard rejected $kept" >&2; exit 1; }
done
# The exported version knobs default to and accept only the kept versions.
for knob in lang/lua/luaversion.mk:LUA_VERSION_DEFAULT:55 \
    lang/lua/luaversion.mk:LUA_VERSIONS_ACCEPTED:55 \
    lang/python/pyversion.mk:PYTHON_VERSIONS_ACCEPTED:315 \
    lang/php/phpversion.mk:PHP_VERSIONS_ACCEPTED:85 \
    mk/pgsql.buildlink3.mk:PGSQL_VERSIONS_ACCEPTED:18 \
    mk/mysql.buildlink3.mk:MYSQL_VERSIONS_ACCEPTED:mariadb118 \
    lang/nodejs/nodeversion.mk:NODE_VERSIONS_ACCEPTED:26 \
    mk/bdb.buildlink3.mk:BDB_DEFAULT:db18; do
    file=${knob%%:*} rest=${knob#*:}
    grep -Eq "^${rest%%:*}[?]=[[:space:]]+${rest#*:}\$" "$pkgsrc/$file" ||
        { echo "$file does not offer only ${rest#*:} in ${rest%%:*}" >&2; exit 1; }
done
# Berkeley DB: db18, plus the built-in db-1.85 interface where there is one.
grep -Eq '^_BDB_PKGS[?]=[[:space:]]+db1 db18$' "$pkgsrc/mk/bdb.buildlink3.mk" ||
    { echo "mk/bdb.buildlink3.mk offers more than db1 and db18" >&2; exit 1; }
# The kept Ruby is the newest upstream release and its distinfo matches.
grep -Eq '^RUBY40_VERSION=[[:space:]]+4[.]0[.]9$' "$pkgsrc/lang/ruby/rubyversion.mk" &&
    grep -Fq 'SHA512 (ruby-4.0.9.tar.xz) = ' "$pkgsrc/lang/ruby40/distinfo" ||
    { echo "lang/ruby40 is not Ruby 4.0.9" >&2; exit 1; }
# Rails 8.1 only: rails.mk offers 8.1.4, and a package that accepts only an
# older Rails fails instead of selecting one.
rails81="devel/ruby-activesupport81 devel/ruby-activemodel81 devel/ruby-activejob81
    databases/ruby-activerecord81 www/ruby-actionview81 www/ruby-actionpack81
    www/ruby-actioncable81 devel/ruby-railties81 devel/ruby-activestorage81
    mail/ruby-actionmailer81 mail/ruby-actionmailbox81 textproc/ruby-actiontext81
    www/ruby-rails81 www/ruby-action_text-trix"
for kept in $rails81; do
    [ -f "$pkgsrc/$kept/PLIST" ] || { echo "Missing kept $kept" >&2; exit 1; }
    [ -z "$(reason "$kept")" ] || { echo "Guard rejected $kept" >&2; exit 1; }
done
for old in www/ruby-rails72 www/ruby-rails80 devel/ruby-railties72 \
    devel/ruby-activesupport80 textproc/ruby-actiontext72 mail/ruby-roadie-rails32 \
    mail/ruby-roadie-rails33 www/ruby-propshaft11; do
    [ ! -e "$pkgsrc/$old" ] || { echo "Old version $old exported" >&2; exit 1; }
    reason "$old" | grep -Fq 'EmberBSD keeps only' ||
        { echo "Guard accepted $old" >&2; exit 1; }
done
for line in 'RUBY_RAILS81_VERSION[?]=[[:space:]]+8[.]1[.]4' \
    'RUBY_RAILS_DEFAULT[?]=[[:space:]]+81' 'RUBY_RAILS_SUPPORTED=[[:space:]]+81' \
    'PKG_FAIL_REASON[+]=[[:space:]]+"EmberBSD keeps only Rails .*'; do
    grep -Eq "^$line\$" "$pkgsrc/lang/ruby/rails.mk" ||
        { echo "lang/ruby/rails.mk lacks $line" >&2; exit 1; }
done
! grep -Eq '^RUBY_RAILS(72|80)_VERSION' "$pkgsrc/lang/ruby/rails.mk" ||
    { echo "lang/ruby/rails.mk offers an old Rails" >&2; exit 1; }
grep -Fq 'SHA512 (rails-8.1.4.gem) = ' "$pkgsrc/www/ruby-rails81/distinfo" ||
    { echo "www/ruby-rails81 is not Rails 8.1.4" >&2; exit 1; }
# with_advisory_lock 7.6.0 runs on Ruby 4.0; its recipe accepted only 3.3 and 3.4.
wal=databases/ruby-with_advisory_lock
! grep -q "^RUBY_VERSIONS_ACCEPTED=" "$pkgsrc/$wal/Makefile" ||
    { echo "$wal accepts only some Ruby versions" >&2; exit 1; }
[ -z "$(reason "$wal")" ] || { echo "Guard rejected $wal" >&2; exit 1; }
# Redmine 6.0 and 6.1 accept only Ruby 3.3 and Rails 7.2; Redmine 7 replaces them.
old_rails=$(find "$pkgsrc" -mindepth 3 -maxdepth 3 -name Makefile \
    ! -path '*/devel/ruby-redmine6[01]/*' \
    -exec grep -lE '^RUBY_RAILS_ACCEPTED=.*(72|80)' {} +) || :
[ -z "$old_rails" ] || { echo "Accept only an old Rails: $old_rails" >&2; exit 1; }
echo 'PASS: the export and the guard keep one version of each family.'
