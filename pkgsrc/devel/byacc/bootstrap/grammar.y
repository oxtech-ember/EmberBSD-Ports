/* SPDX-License-Identifier: BSD-2-Clause */
/* Copyright (c) 2026 EmberBSD contributors. */
/* Origin: EmberBSD (AI-assisted). Independent arithmetic oracle fixture. */
%{
#include <stdio.h>
#include <stdlib.h>
int yylex(void);
void yyerror(const char *);
%}
%union { int number; }
%token <number> NUMBER
%type <number> expr
%left '+' '-'
%left '*'
%%
input: /* empty */ | input expr '\n' { printf("%d\n", $2); } ;
expr: NUMBER | expr '+' expr { $$ = $1 + $3; }
    | expr '-' expr { $$ = $1 - $3; }
    | expr '*' expr { $$ = $1 * $3; }
    | '(' expr ')' { $$ = $2; } ;
%%
int yylex(void)
{
    int c;
    do { c = getchar(); } while (c == ' ' || c == '\t');
    if (c >= '0' && c <= '9') {
        yylval.number = c - '0';
        return NUMBER;
    }
    return c == EOF ? 0 : c;
}
void yyerror(const char *message)
{
    (void)message;
    fputs("parse error\n", stderr);
}
int main(void) { return yyparse() == 0 ? 0 : 2; }
