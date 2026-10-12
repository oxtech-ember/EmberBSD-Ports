# SPDX-License-Identifier: BSD-2-Clause
use strict;
use warnings;
use Test::More tests => 4;
use EmberProbe;
is(EmberProbe::roundtrip(0), 0, 'zero through installed XS ABI');
is(EmberProbe::roundtrip(42), 42, 'integer through installed XS ABI');
is(EmberProbe::roundtrip(4294967297), 4294967297, 'UV exceeds 32 bits');
eval { EmberProbe::reject() };
like($@, qr/Ember XS exception/, 'XS exception propagates to Perl');
