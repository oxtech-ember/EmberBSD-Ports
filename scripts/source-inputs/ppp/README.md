# Common PPP source

`source.py prepare` extracts the pinned `net/pppd` archive and applies the
complete package patch set. `verify-source` checks the prepared tree against
the effective package inputs. Select the SDK source, native Git and patch
executables explicitly. The prepared source serves package and native OS
consumers; compiler, platform ABI and runtime validation remain the consumers'
responsibility.
