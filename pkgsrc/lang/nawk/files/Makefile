# /****************************************************************
# Copyright (C) Lucent Technologies 1997
# All Rights Reserved
#
# Permission to use, copy, modify, and distribute this software and
# its documentation for any purpose and without fee is hereby
# granted, provided that the above copyright notice appear in all
# copies and that both that the copyright notice and this
# permission notice and warranty disclaimer appear in supporting
# documentation, and that the name Lucent Technologies or any of
# its entities not be used in advertising or publicity pertaining
# to distribution of the software without specific, written prior
# permission.
#
# LUCENT DISCLAIMS ALL WARRANTIES WITH REGARD TO THIS SOFTWARE,
# INCLUDING ALL IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS.
# IN NO EVENT SHALL LUCENT OR ANY OF ITS ENTITIES BE LIABLE FOR ANY
# SPECIAL, INDIRECT OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER
# IN AN ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION,
# ARISING OUT OF OR IN CONNECTION WITH THE USE OR PERFORMANCE OF
# THIS SOFTWARE.
# ****************************************************************/

# Origin: NetBSD pkgsrc; EmberBSD (AI-assisted) bundled-source adaptation.
# Both bootstrap and ordinary nawk use these exact source and parser files.
# Regenerate parser outputs only with ../regenerate.py and selected SDK tools.
CC?= cc
CFLAGS?= -O2
LDFLAGS?=
OFILES= awkgram.tab.o b.o main.o parse.o proctab.o tran.o lib.o run.o lex.o
.SUFFIXES: .c .o

a.out: $(OFILES)
	$(CC) $(CFLAGS) $(LDFLAGS) $(OFILES) -lm -o $@

$(OFILES): awk.h awkgram.tab.h proto.h

.c.o:
	$(CC) $(CFLAGS) -c $< -o $@

clean:
	rm -f a.out $(OFILES)
