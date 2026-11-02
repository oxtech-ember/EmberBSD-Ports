#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
#
# Usage: qt5-qtbase-openssl4.sh QT_DIR HOST_PREFIX NEW_WORK
#
# OpenSSL 4 adds const to the X.509 API and makes ASN1_STRING opaque, so
# QtNetwork 5.15 did not compile against it (qsslsocket_openssl_symbols.cpp
# and qsslcertificate_openssl.cpp). The recipe patches port the OpenSSL 4
# changes of Qt 6 and read ASN1 strings through accessor functions. Build a
# probe against the QtNetwork in QT_DIR (an installed Qt 5 prefix or the
# build tree, with include/ and lib/), check that it was built with OpenSSL
# 4 or newer, and compare what it reads from a certificate made by the
# openssl tool with the values that the certificate was made with: the
# serial number, the names, both kinds of ASN1 time, IPv4 and IPv6
# subject alternative names and the authority key identifier.
# HOST_PREFIX supplies clang++ and openssl.
set -eu
[ "$#" -eq 3 ] || { echo "Usage: $0 QT_DIR HOST_PREFIX NEW_WORK" >&2; exit 2; }
qt=$1 host=$2
case "$3" in /*) ;; *) echo "$0: NEW_WORK must be absolute" >&2; exit 2;; esac
mkdir "$3"
work=$3
cat > "$work/req.cnf" <<'CNF'
[req]
distinguished_name = dn
x509_extensions = ext
[dn]
[ext]
subjectKeyIdentifier = hash
authorityKeyIdentifier = keyid:always
subjectAltName = IP:192.0.2.7, IP:2001:db8::1
CNF
# notBefore is a UTCTime and notAfter, after 2049, a GeneralizedTime.
"$host/bin/openssl" req -x509 -config "$work/req.cnf" -newkey ec \
	-pkeyopt ec_paramgen_curve:P-256 -noenc -keyout "$work/key.pem" \
	-out "$work/cert.pem" -subj /CN=ember-probe -set_serial 0x0a0b0c \
	-not_before 20260102030405Z -not_after 20510607080910Z 2>/dev/null
ski=$("$host/bin/openssl" x509 -in "$work/cert.pem" -noout -ext subjectKeyIdentifier |
	sed -n '2s/[ :]//gp' | tr 'A-F' 'a-f')
cat > "$work/probe.cpp" <<'CPP'
#include <QtCore/QCoreApplication>
#include <QtCore/QDateTime>
#include <QtCore/QStringList>
#include <QtNetwork/QSslCertificate>
#include <QtNetwork/QSslCertificateExtension>
#include <QtNetwork/QSslSocket>
#include <cstdio>

int main(int argc, char **argv)
{
    QCoreApplication app(argc, argv);
    const QList<QSslCertificate> certs = QSslCertificate::fromPath(QString::fromLocal8Bit(argv[1]));
    if (certs.size() != 1)
        return 1;
    const QSslCertificate &c = certs.first();
    QStringList ips = c.subjectAlternativeNames().values(QSsl::IpAddressEntry);
    ips.sort();
    QByteArray keyid;
    for (const QSslCertificateExtension &e : c.extensions())
        if (e.oid() == QLatin1String("2.5.29.35"))
            keyid = e.value().toMap().value(QLatin1String("keyid")).toByteArray();
    std::printf("openssl=%ld\n", QSslSocket::sslLibraryBuildVersionNumber() >> 28);
    std::printf("serial=%s\n", c.serialNumber().constData());
    std::printf("subject=%s\n", qPrintable(c.subjectInfo(QSslCertificate::CommonName).join(QLatin1Char(','))));
    std::printf("issuer=%s\n", qPrintable(c.issuerInfo(QSslCertificate::CommonName).join(QLatin1Char(','))));
    std::printf("from=%s\n", qPrintable(c.effectiveDate().toUTC().toString(Qt::ISODate)));
    std::printf("to=%s\n", qPrintable(c.expiryDate().toUTC().toString(Qt::ISODate)));
    std::printf("ip=%s\n", qPrintable(ips.join(QLatin1Char(','))));
    std::printf("keyid=%s\n", keyid.constData());
    return 0;
}
CPP
"$host/bin/clang++" -std=c++17 -fPIC -I"$qt/include" -I"$qt/include/QtCore" \
	-I"$qt/include/QtNetwork" -o "$work/probe" "$work/probe.cpp" \
	-L"$qt/lib" -Wl,-rpath,"$qt/lib" -lQt5Network -lQt5Core
# A build tree's libraries carry the install names of the prefix.
DYLD_LIBRARY_PATH=$qt/lib LD_LIBRARY_PATH=$qt/lib "$work/probe" "$work/cert.pem" > "$work/out"
cat > "$work/expected" <<OUT
serial=0a:0b:0c
subject=ember-probe
issuer=ember-probe
from=2026-01-02T03:04:05Z
to=2051-06-07T08:09:10Z
ip=192.0.2.7,2001:db8::1
keyid=$ski
OUT
v=$(sed -n 's/^openssl=//p' "$work/out")
[ "${v:-0}" -ge 4 ] || { echo "FAIL: QtNetwork was built with OpenSSL major ${v:-?}, not 4 or newer"; exit 1; }
[ -n "$ski" ] || { echo "FAIL: no subject key identifier in the test certificate"; exit 1; }
if ! sed 1d "$work/out" | diff -u "$work/expected" - ; then
	echo "FAIL: QtNetwork read other certificate values"
	exit 1
fi
echo "PASS: QtNetwork built with OpenSSL $v reads serial, names, times, IP names and key id"
