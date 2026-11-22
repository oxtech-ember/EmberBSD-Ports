#!@SH@
#
# $NetBSD: mozilla-rootcerts.sh,v 1.22 2024/09/15 10:35:01 wiz Exp $
#
# This script is meant to be used as follows:
#
#	# cd /etc/openssl/certs
#	# mozilla-rootcerts extract
#	# mozilla-rootcerts rehash
#

: ${AWK=@AWK@}
: ${DATADIR=@DATADIR@}
: ${ECHO=@ECHO@}
: ${EXPR=@EXPR@}
: ${LN=@LN@}
: ${LS=@LS@}
: ${MKDIR=@MKDIR@}
: ${OPENSSL=@OPENSSL@}
: ${PREFIX=@PREFIX@}
: ${SSLDIR=@SSLDIR@}
: ${RM=@RM@}

self="${PREFIX}/sbin/mozilla-rootcerts"
certfile="${DATADIR}/certdata.txt"
certdir=${SSLDIR}/certs
destdir=

usage()
{
	${ECHO} 1>&2 "usage: $self [-d destdir] [-f certfile] extract|rehash|install"
	exit $1
}

while [ $# -gt 0 ]; do
	case "$1" in
	-d)	destdir="$2"; shift 2;;
	-f)	certfile="$2"; shift 2 ;;
	--)	shift; break ;;
	-*)	${ECHO} 1>&2 "$self: unknown option -- $1"
		usage 128 ;;
	*)	break ;;
	esac
done

[ $# -eq 1 ] || usage 128

action="$1"; shift

#
#	link_hash pemtype pemfile
#
#	Link a certificate or CRL to its subject name hash value.
#	Each hash is of the form <hash>.<n> for certificates and
#	<hash>.r<n> for CRLs, where n is an integer.  If the hash
#	value already exists, then we need to up the value of n, unless
#	it's a duplicate, in which case we skip the link.  We check
#	for duplicates by comparing fingerprints.
#
# OpenSSL can print policy diagnostics after the requested value for a
# locally restricted certificate. Select the single hash or fingerprint.
openssl_identifier()
{
	kind=$3
	case $kind in
	-hash) set -- "$1" -in "$2" -noout -hash ;;
	-fingerprint) set -- "$1" -in "$2" -noout -sha256 -fingerprint ;;
	*) return 1 ;;
	esac
	output=$("$OPENSSL" "$@") || return 1
	printf '%s\n' "$output" | LC_ALL=C "$AWK" -v kind="$kind" '
		kind == "-hash" { sub(/^issuer name hash=/, "") }
		kind == "-hash" && length($0) == 8 && /^[0-9a-fA-F]+$/ { value = $0; n++ }
		kind == "-fingerprint" && tolower($0) ~ /^sha(2-)?256 fingerprint=/ {
			sub(/^[^=]*=/, "")
			if (split($0, octets, ":") != 32) exit 1
			for (i = 1; i <= 32; i++)
				if (octets[i] !~ /^[0-9a-fA-F][0-9a-fA-F]$/) exit 1
			value = toupper($0)
			n++
		}
		END { if (n != 1) exit 1; print value }
	'
}

link_hash()
{
	_pemtype="$1"; _pemfile="$2"; shift 2

	_hash=$(openssl_identifier "$_pemtype" "$_pemfile" -hash) || return 1
	_fprint=$(openssl_identifier "$_pemtype" "$_pemfile" -fingerprint) || return 1
	_suffix=0
	while [ 1 = 1 ] ; do
		case $_pemtype in
		crl)	_hashfile="$_hash.r$_suffix" ;;
		x509|*)	_hashfile="$_hash.$_suffix" ;;
		esac
		if [ ! -f "$_hashfile" ]; then
			${ECHO} "$_pemfile => $_hashfile"
			"$LN" -sf "$_pemfile" "$_hashfile" || return 1
			break
		fi
		_fprintold=$(openssl_identifier "$_pemtype" "$_hashfile" -fingerprint) || return 1
		if [ "$_fprint" = "$_fprintold" ]; then
			${ECHO} 1>&2 "WARNING: Skipping duplicate certificate $_pemfile"
			return 0
		fi
		_suffix=`${EXPR} $_suffix + 1`
	done
}

case $action in
rehash)
	# Rebuild only OpenSSL hash links. Keep local PEM links and other names.
	for entry in ./*.*; do
		[ -L "$entry" ] || continue
		name=${entry#./}
		hash=${name%%.*}
		index=${name#*.}
		case $hash in ????????) ;; *) continue ;; esac
		case $hash in *[!0-9A-Fa-f]*) continue ;; esac
		case $index in r*) index=${index#r} ;; esac
		case $index in ''|*[!0-9]*) continue ;; esac
		"$RM" -f "$entry" || exit 1
	done

	for path in ./*.pem; do
		[ -f "$path" ] || continue
		pemfile=${path#./}
		pemtype=
		while read line; do
			case $line in
			"-----BEGIN CERTIFICATE-----"|\
			"-----BEGIN X509 CERTIFICATE-----"|\
			"-----BEGIN TRUSTED CERTIFICATE-----")
				pemtype=x509
				break
				;;
			"-----BEGIN X509 CRL-----")
				pemtype=crl
				break
				;;
			esac
		done < "$pemfile"
		case $pemtype in
		x509|crl)
			link_hash "$pemtype" "$pemfile" || exit 1
			;;
		*)
			${ECHO} 1>&2 "WARNING: $pemfile does not contain a certificate or CRL: skipping"
			continue
			;;
		esac
	done
	;;

extract)
	# A plain PEM trust anchor cannot carry Mozilla's leaf issuance cutoff.
	# Export only unconditional TLS server delegators. Keep the NSS data intact.
	refresh_bundle=0
	if [ -f ca-certificates.crt ] && [ ! -L ca-certificates.crt ]; then
		refresh_bundle=1
	fi
	stage=./.mozilla-rootcerts.$$
	(umask 077 && "$MKDIR" "$stage") || exit 1
	trap '"$RM" -rf "$stage"' EXIT
	trap 'exit 1' HUP INT TERM
	(
		cd "$stage" || exit 1
		LC_ALL=C OPENSSL="$OPENSSL" "$AWK" -v refresh="$refresh_bundle" '
		function fail(message) {
			print "mozilla-rootcerts: " message > "/dev/stderr"
			failed = 1
			exit 1
		}
		function octets(	value, rc) {
			while ((rc = getline) > 0 && $0 != "END") {
				if ($0 !~ /^(\\[0-7][0-7][0-7])+$/)
					fail("invalid octal attribute")
				value = value $0
			}
			if (rc <= 0 || value == "")
				fail("incomplete octal attribute")
			return value
		}
		function finish(	key) {
			if (object != "CKO_CERTIFICATE" && object != "CKO_NSS_TRUST")
				return
			if (issuer == "" || serial == "")
				fail("missing certificate identity")
			key = issuer SUBSEP serial
			if (object == "CKO_CERTIFICATE") {
				if (der == "" || key in seen)
					fail("missing value or duplicate certificate")
				seen[key] = 1
				identity[count] = key
				values[count] = der
				limited[count] = cutoff
				count++
			} else {
				if (key in trust)
					fail("duplicate trust record")
				trust[key] = delegator
			}
		}
		BEGIN { count = 0 }
		$1 == "CKA_CLASS" {
			finish()
			object = $3
			issuer = serial = der = ""
			cutoff = delegator = 0
			next
		}
		object != "CKO_CERTIFICATE" && object != "CKO_NSS_TRUST" { next }
		$1 == "CKA_ISSUER" && $2 == "MULTILINE_OCTAL" { issuer = octets(); next }
		$1 == "CKA_SERIAL_NUMBER" && $2 == "MULTILINE_OCTAL" { serial = octets(); next }
		object == "CKO_CERTIFICATE" && $1 == "CKA_VALUE" && $2 == "MULTILINE_OCTAL" {
			der = octets()
			next
		}
		object == "CKO_CERTIFICATE" && $1 == "CKA_NSS_SERVER_DISTRUST_AFTER" {
			if ($2 != "CK_BBOOL" || $3 != "CK_FALSE")
				cutoff = 1
			next
		}
		object == "CKO_NSS_TRUST" && $1 == "CKA_TRUST_SERVER_AUTH" {
			delegator = ($2 == "CK_TRUST" && $3 == "CKT_NSS_TRUSTED_DELEGATOR")
		}
		END {
			if (failed) exit 1
			finish()
			for (i = 0; i < count; i++) {
				allowed = !limited[i] && trust[identity[i]]
				if (allowed)
					file = "mozilla-rootcert-" i ".pem"
				else if (refresh)
					file = ".removed-" i ".crt"
				else
					continue
				cmd = "\"$OPENSSL\" x509 -inform der -outform pem -text >" file
				data = values[i]
				for (j = 1; j <= length(data); j += 4) {
					byte = 64 * substr(data, j+1, 1) + 8 * substr(data, j+2, 1) + substr(data, j+3, 1)
					printf "%c", byte | cmd
				}
				if (close(cmd) != 0) fail("OpenSSL failed for " file)
				if (allowed) print file
			}
			if (!count) fail("no certificates in input")
		}'
	) < "$certfile" || exit 1

	# Update an existing combined store. Keep certificates added locally to
	# the bundle, including entries without a separate PEM file.
	if [ "$refresh_bundle" -eq 1 ]; then
		# Some earlier Mozilla roots have no certificate object in the
		# current NSS data. Recognize them when only the old bundle remains.
		LC_ALL=C "$AWK" -v stage="$stage" '
			/^#/ || /^[[:space:]]*$/ { next }
			{
				if (length($0) != 64 || $0 ~ /[^[:xdigit:]]/) exit 1
				digest = toupper(substr($0, 1, 2))
				for (i = 3; i <= 63; i += 2)
					digest = digest ":" toupper(substr($0, i, 2))
				file = stage "/.known-" digest
				print "" > file
				if (close(file) != 0) exit 1
			}
		' "$DATADIR/retired-tls-sha256" || exit 1
		# OpenSSL hashes the certificate DER, including when it reads a
		# TRUSTED CERTIFICATE carrying additional local trust attributes.
		for file in ./mozilla-rootcert-*.pem "$stage"/*.pem "$stage"/.removed-*.crt; do
			[ -f "$file" ] || continue
			case $file in ./mozilla-rootcert-*)
				number=${file#./mozilla-rootcert-}
				case ${number%.pem} in ''|*[!0-9]*) continue ;; esac
			esac
			digest=$(openssl_identifier x509 "$file" -fingerprint) || exit 1
			: > "$stage/.known-$digest" || exit 1
			case $file in "$stage"/mozilla-rootcert-*.pem)
				"$LN" "$file" "$stage/.anchor-$digest" || exit 1 ;;
			esac
		done
		LC_ALL=C "$AWK" -v stage="$stage" '
			/^-----BEGIN (X509 |TRUSTED )?CERTIFICATE-----\r?$/ {
				if (file) exit 1
				header = $0
				sub(/\r$/, "", header)
				count++
				file = stage "/.local-" count ".crt"
			}
			file { print > file }
			/^-----END (X509 |TRUSTED )?CERTIFICATE-----\r?$/ {
				end = $0
				sub(/\r$/, "", end)
				sub(/END/, "BEGIN", end)
				if (!file || end != header || close(file) != 0) exit 1
				file = ""
			}
			END { if (file) exit 1 }
		' ca-certificates.crt || exit 1
		: > "$stage/extra.crt" || exit 1
		for file in "$stage"/.local-*.crt; do
			[ -f "$file" ] || continue
			digest=$(openssl_identifier x509 "$file" -fingerprint) || exit 1
			if [ ! -f "$stage/.known-$digest" ]; then
				cat "$file" >> "$stage/extra.crt" || exit 1
			elif [ -f "$stage/.anchor-$digest" ] &&
			    "$AWK" 'NR == 1 { exit ($0 !~ /^-----BEGIN TRUSTED CERTIFICATE-----\r?$/) }' "$file"; then
				# Preserve explicit local restrictions on a retained CA in
				# both the combined file and its numbered certificate.
				if [ -f "$stage/.aux-$digest" ]; then
					cmp -s "$file" "$stage/.aux-$digest" || {
						"$ECHO" "Conflicting local trust attributes for $digest" >&2
						exit 1
					}
				else
					"$LN" "$file" "$stage/.aux-$digest" || exit 1
					cat "$file" > "$stage/.anchor-$digest" || exit 1
				fi
			fi
		done
		(
			for file in "$stage"/*.pem; do
				[ ! -f "$file" ] || cat "$file" || exit 1
			done
			cat "$stage/extra.crt"
		) > "$stage/ca-certificates.crt" || exit 1
		mv -f "$stage/ca-certificates.crt" . || exit 1
	fi

	# Replace only the numbered files owned by this exporter. A second
	# extraction also removes roots that disappeared or acquired a cutoff.
	for file in ./mozilla-rootcert-*.pem; do
		[ -f "$file" ] || [ -L "$file" ] || continue
		number=${file#./mozilla-rootcert-}
		case ${number%.pem} in ''|*[!0-9]*) continue ;; esac
		[ -f "$stage/${file#./}" ] || "$RM" -f "$file" || exit 1
	done
	for file in "$stage"/*.pem; do
		[ -f "$file" ] || continue
		mv -f "$file" . || exit 1
	done
	;;
install)
	# ${WHATEVER}/etc/openssl/certs should exist, but an
	# install/removal cycle of mozilla-rootcerts-openssl might have removed it.
	if [ ! -d $destdir$certdir ]; then
		${ECHO} 1>&2 "WARNING: $destdir$certdir does not exist.  Creating it."
		${MKDIR} -p $destdir$certdir
	fi
	cd $destdir$certdir
	if [ -n "`${LS}`" ]; then
		# \todo Explain why this must fail if the user has
		# installed certificates from other than the mozilla
		# default root set.
		${ECHO} 1>&2 "ERROR: $destdir$certdir already contains certificates, aborting."
		exit 1
	fi
	set -e
	$self extract
	$self rehash
	set +e
	# \todo Explain why if we are willing to write
	# ca-certificates.crt, we are not willing to remove and
	# re-create it.  Arguably install should be idempotent without
	# error.
	if [ -e $destdir$certdir/ca-certificates.crt ]; then
		${ECHO} 1>&2 "ERROR: $destdir$certdir/ca-certificates.crt already exists, aborting."
		exit 1
	fi
	set -e
	# \todo This is appparently for users of gnutls, but it is not
	# clear where it should be and why.  In particular, this file
	# should perhaps be created at package build time and be
	# managed by pkgsrc.
	cat $destdir$certdir/*.pem > $destdir$certdir/ca-certificates.crt
esac
