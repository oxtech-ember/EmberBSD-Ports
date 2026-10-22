#!/usr/bin/env python3
"""Generate, compile and run a scanner that uses fixed trailing context."""
import argparse
import pathlib
import subprocess
import tempfile

p = argparse.ArgumentParser()
p.add_argument('--flex', required=True)
p.add_argument('--cc', required=True)
a = p.parse_args()
rules = r'''%option noyywrap nodefault
%{
#include <stdio.h>
%}
%%
[a-z]+/[0-9] { printf("WORD:%s\n", yytext); }
[a-z]+       { printf("TEXT:%s\n", yytext); }
[0-9]+       { printf("INT:%s\n", yytext); }
[ \t\r\n]+   ;
.            { return 2; }
%%
int main(void) { return yylex(); }
'''
with tempfile.TemporaryDirectory(prefix='flex-consumer-') as directory:
    directory = pathlib.Path(directory)
    scanner = directory / 'scanner.l'
    generated = directory / 'scanner.c'
    binary = directory / 'scanner'
    scanner.write_text(rules)
    subprocess.run([a.flex, '-o', str(generated), str(scanner)], check=True)
    subprocess.run([a.cc, '-O2', str(generated), '-o', str(binary)], check=True)
    cases = [(b'alpha123 beta\n', 0, b'WORD:alpha\nINT:123\nTEXT:beta\n'),
             (b'', 0, b''), (b'?', 2, b'')]
    for data, status, expected in cases:
        result = subprocess.run([str(binary)], input=data, capture_output=True, timeout=10)
        assert (result.returncode, result.stdout) == (status, expected), result
    print('PASS: 3 installed scanner cases (trailing context, empty, invalid token)')
