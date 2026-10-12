#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), installed Perl with unchanged upstream tests.
set -eu
[ "$#" = 2 ] || { echo "Usage: $0 UPSTREAM_TEST_TREE NEW_OUTPUT" >&2; exit 2; }
tests=$1 output=$2
for path do
    case "$path" in /*) ;; *) echo 'Absolute paths required' >&2; exit 2 ;; esac
done
PATH=/usr/pkg/bin:/usr/pkg/sbin:/usr/bin:/usr/sbin:/bin:/sbin; export PATH
unset PERL5LIB PERL5OPT PERL_CORE LD_LIBRARY_PATH
mkdir "$output"
uname -a > "$output/system.txt"
pkg_info -e 'perl>=5.44.0' > "$output/package.txt"
sysctl -n kern.boottime > "$output/boot-before.txt"
trap 'sysctl -n kern.boottime > "$output/boot-after.txt"' EXIT
sha256 /usr/pkg/bin/perl > "$output/perl.sha256"
ldd /usr/pkg/bin/perl > "$output/ldd.txt"
/usr/pkg/bin/perl -V > "$output/config.txt"
/usr/pkg/bin/perl -MConfig -MEncode -MDigest::SHA=sha256_hex -e '
    die "version\n" unless $] == 5.044;
    die "target architecture\n" unless $Config{archname} eq "aarch64-netbsd-thread-multi";
    die "compiler\n" unless $Config{cc} eq "/usr/pkg/gcc16/bin/gcc";
    die "shell\n" unless $Config{sh} eq "/bin/sh";
    die "transport\n" if $Config{sysroot} || $Config{hostperl} || $Config{run};
    my $utf8 = encode("UTF-8", chr(0x20ac) . chr(0x1f642));
    die "UTF-8 XS\n" unless unpack("H*", $utf8) eq "e282acf09f9982";
    die "SHA XS\n" unless sha256_hex("abc") eq "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad";
    print "Installed configuration, Encode XS and Digest::SHA XS: PASS\n";
' > "$output/consumer.log"
for selection in ext/Errno:t/Errno.t dist/threads:t/basic.t dist/IO:t/io_xs.t \
    cpan/JSON-PP:t/001_utf8.t dist/Time-HiRes:t/usleep.t; do
    directory=${selection%:*} file=${selection#*:}
    name=$(printf '%s' "$directory" | tr / _)
    sha256 "$tests/$directory/$file" >> "$output/upstream-tests.sha256"
    (cd "$tests/$directory" && timeout -k 5 120 /usr/pkg/bin/prove -v "$file") \
        > "$output/$name.log" 2>&1
    cat "$output/$name.log"
done
sysctl -n kern.boottime > "$output/boot-after.txt"
cmp "$output/boot-before.txt" "$output/boot-after.txt"
cat "$output/consumer.log"
