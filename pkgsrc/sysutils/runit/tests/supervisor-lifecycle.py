#!/usr/bin/env python3
"""Exercise runsv restart, TERM shutdown, and duplicate-supervisor handling."""

import argparse
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time


def wait_for(predicate, process, timeout, description):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f"runsv exited early ({process.returncode}) while waiting for {description}")
        value = predicate()
        if value:
            return value
        time.sleep(0.05)
    raise RuntimeError(f"timed out waiting for {description}")


def wait_until(predicate, timeout, description):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(0.05)
    raise RuntimeError(f"timed out waiting for {description}")


def parse_start_records(contents):
    records = []
    for line in contents.splitlines(keepends=True):
        if not line.endswith(b"\n"):
            break
        fields = line.split()
        if len(fields) != 2:
            raise RuntimeError(f"invalid start record: {line!r}")
        try:
            records.append(tuple(int(field) for field in fields))
        except ValueError as error:
            raise RuntimeError(f"invalid start record: {line!r}") from error
    return records


def read_starts(path):
    if not path.exists():
        return []
    return parse_start_records(path.read_bytes())


def pid_exists(pid):
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    return True


def stop_process(process):
    if process.poll() is None:
        try:
            process.kill()
        except ProcessLookupError:
            pass
        try:
            process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            pass


def write_run_fixture(run_script, max_runtime):
    run_script.write_text(
        f"#!{sys.executable}\n"
        "import os\n"
        "import signal\n"
        "import sys\n"
        "import time\n"
        "\n"
        "def append_record(path, value):\n"
        "    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)\n"
        "    try:\n"
        "        os.write(fd, (str(value) + '\\n').encode())\n"
        "    finally:\n"
        "        os.close(fd)\n"
        "\n"
        "def on_term(_signum, _frame):\n"
        "    append_record(os.environ['TEST_TERMS'], os.getpid())\n"
        "    raise SystemExit(0)\n"
        "\n"
        "signal.signal(signal.SIGTERM, on_term)\n"
        "count_path = os.environ['TEST_COUNT']\n"
        "try:\n"
        "    with open(count_path, encoding='ascii') as count_file:\n"
        "        count = int(count_file.read().strip())\n"
        "except FileNotFoundError:\n"
        "    count = 0\n"
        "count += 1\n"
        "with open(count_path, 'w', encoding='ascii') as count_file:\n"
        "    count_file.write(f'{count}\\n')\n"
        "append_record(os.environ['TEST_STARTS'], f'{count} {os.getpid()}')\n"
        "if count == 1:\n"
        "    raise SystemExit(7)\n"
        f"deadline = time.monotonic() + {max_runtime!r}\n"
        "while time.monotonic() < deadline:\n"
        "    time.sleep(min(0.05, max(0.0, deadline - time.monotonic())))\n"
        "raise SystemExit(0)\n"
    )
    run_script.chmod(0o700)


def self_test():
    records = parse_start_records(b"1 123\n2 456")
    if records != [(1, 123)]:
        raise RuntimeError(f"partial start record was consumed: {records!r}")
    try:
        parse_start_records(b"1 123\n2 nope\n")
    except RuntimeError:
        pass
    else:
        raise RuntimeError("malformed complete start record was accepted")

    with tempfile.TemporaryDirectory(prefix="runit-fixture-deadline-") as temporary:
        root = Path(temporary)
        run_script = root / "run"
        starts = root / "starts"
        terms = root / "terms"
        count = root / "count"
        count.write_text("1\n", encoding="ascii")
        write_run_fixture(run_script, max_runtime=0.15)
        env = dict(os.environ)
        env.update(TEST_COUNT=str(count), TEST_STARTS=str(starts), TEST_TERMS=str(terms))
        started = time.monotonic()
        result = subprocess.run(
            [sys.executable, str(run_script)], env=env, stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=2, check=False,
        )
        elapsed = time.monotonic() - started
        observed = read_starts(starts)
        if result.returncode != 0 or elapsed >= 1.5 or len(observed) != 1 or observed[0][0] != 2:
            raise RuntimeError("bounded service fixture did not expire cleanly")


def run_test(runsv):
    if os.geteuid() == 0:
        raise RuntimeError("run this lifecycle test as an ordinary user")

    with tempfile.TemporaryDirectory(prefix="runit-lifecycle-") as temporary:
        root = Path(temporary)
        service = root / "service"
        service.mkdir(mode=0o700)
        starts = root / "starts"
        terms = root / "terms"
        count = root / "count"
        run_script = service / "run"
        write_run_fixture(run_script, max_runtime=15)

        env = dict(os.environ)
        env.update(TEST_COUNT=str(count), TEST_STARTS=str(starts), TEST_TERMS=str(terms))
        supervisor = subprocess.Popen(
            [runsv, str(service)], env=env, stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
            start_new_session=True,
        )
        duplicate = None
        try:
            observed = wait_for(
                lambda: (values if len(values := read_starts(starts)) >= 2 else None),
                supervisor,
                8,
                "service restart",
            )
            if len(observed) < 2 or observed[0][0] != 1 or observed[1][0] != 2:
                raise RuntimeError(f"expected two ordered starts; got {observed!r}")
            child_pid = observed[1][1]
            if child_pid == observed[0][1]:
                raise RuntimeError("restart reused the first child process")

            duplicate = subprocess.Popen(
                [runsv, str(service)], env=env, stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
                start_new_session=True,
            )
            try:
                duplicate_status = duplicate.wait(timeout=4)
            except subprocess.TimeoutExpired as error:
                stop_process(duplicate)
                raise RuntimeError("second runsv did not reject the locked service") from error
            if duplicate_status != 111:
                raise RuntimeError(f"second runsv returned {duplicate_status}, expected 111")

            supervisor.send_signal(signal.SIGTERM)
            try:
                status = supervisor.wait(timeout=6)
            except subprocess.TimeoutExpired as error:
                raise RuntimeError("TERM did not stop runsv") from error
            if status != 0:
                detail = supervisor.stderr.read().decode(errors="replace")
                raise RuntimeError(f"TERM made runsv exit {status}: {detail}")

            wait_until(lambda: not pid_exists(child_pid), 3, "child exit after TERM")
            terminated = set(map(int, terms.read_text().splitlines())) if terms.exists() else set()
            if child_pid not in terminated:
                raise RuntimeError("service child did not record its TERM handler")
        finally:
            if duplicate is not None:
                stop_process(duplicate)
            stop_process(supervisor)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--runsv", help="absolute path to the native runsv executable")
    mode.add_argument("--self-test", action="store_true", help="test the fixture and record parser")
    args = parser.parse_args()
    if args.self_test:
        try:
            self_test()
        except (OSError, RuntimeError, subprocess.TimeoutExpired) as error:
            parser.exit(1, f"FAIL: {error}\n")
        print("PASS: newline-complete records and bounded service fixture")
        return
    executable = Path(args.runsv)
    if not executable.is_absolute() or not executable.is_file() or not os.access(executable, os.X_OK):
        parser.error("--runsv must name an executable absolute path")
    try:
        run_test(str(executable))
    except (OSError, RuntimeError) as error:
        parser.exit(1, f"FAIL: {error}\n")
    print("PASS: runsv restarts the service, rejects a duplicate, and stops child on TERM")


if __name__ == "__main__":
    main()
