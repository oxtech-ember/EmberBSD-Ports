# Exact cwrappers argument vector

Origin: EmberBSD (AI-assisted); the original wrapper retains its NetBSD license.

A caller that needs the exact selected compiler invocation can set
`CWRAPPERS_EMIT_ARGV=1` for one wrapper process. The wrapper applies its usual
configuration and transformations, then writes the executable followed by every
argument as NUL-terminated byte strings to stdout and exits without executing it.
The special `--wrappee-name` query retains its existing behavior. Other values
of `CWRAPPERS_EMIT_ARGV` fail. Normal invocations do not set this variable.

The returned executable may itself be a selected SDK compiler binding; use the
SDK `compiler_bindings.compiler_argv` API and its explicitly selected binding
record to obtain the remaining underlying argument vector. Do not execute the
target merely to obtain parsing flags.

`tests/cwrappers-emit-argv.py` checks the compiled wrapper against the actual
argv received by a fixture wrappee for compile and link invocations, including
spaces and empty arguments. It also checks failure and that emission does not
execute the wrappee. The caller must supply the selected Python, the candidate
wrapper, an existing generated c++ configuration and a new work directory.
