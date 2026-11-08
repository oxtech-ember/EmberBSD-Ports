#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.

"""The install transaction releases the backend on every terminal path.

Discover deletes a transaction after a terminal status. The helper runs as
root through pkexec, so this user process cannot cancel it. The transaction
is never cancellable. The backend owns it, because a reload replaces every
resource. Every error path goes through fail(), which calls finish() before
the terminal status. The destructor detaches a running process and calls
finish() too, so m_installing never stays set.
"""

import pathlib
import re
import unittest

SOURCE = (pathlib.Path(__file__).resolve().parent / "EmberBSDBackend" / "EmberBSDBackend.cpp").read_text()
START = SOURCE.index("class InstallTransaction")
END = SOURCE.index("Transaction *EmberBSDBackend::installApplication")
TRANSACTION = SOURCE[START:END]


def method(name):
    """Return the body text of one InstallTransaction method."""
    start = TRANSACTION.index(name + "(")
    opening = TRANSACTION.index("{", start)
    depth, index = 0, opening
    while True:
        char = TRANSACTION[index]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return TRANSACTION[opening:index + 1]
        index += 1


def lambdas(body):
    """Split one method body at each connect() so each handler stands alone."""
    return [part for part in re.split(r"\n\s*connect\(", body) if part.strip()]


class InstallTransactionLifecycle(unittest.TestCase):
    def test_transaction_is_never_cancellable(self):
        self.assertIn("setCancellable(false);", TRANSACTION)
        self.assertNotIn("setCancellable(true)", TRANSACTION)
        self.assertNotIn("m_cancel", TRANSACTION)
        self.assertNotIn("->kill()", TRANSACTION)
        self.assertNotIn("->terminate()", TRANSACTION)
        self.assertRegex(TRANSACTION, r"void cancel\(\) override\s*\{\s*\}")

    def test_backend_owns_the_transaction(self):
        self.assertIn(": Transaction(backend, app, InstallRole", TRANSACTION)
        self.assertIn("QPointer<EmberBSDBackend> m_backend;", TRANSACTION)

    def test_destructor_detaches_the_process_and_releases_the_backend(self):
        self.assertRegex(TRANSACTION, r"~InstallTransaction\(\) override\s*\{\s*release\(m_process\);\s*finish\(\);\s*\}")
        release = method("void release")
        self.assertIn("disconnect(process, nullptr, this, nullptr);", release)
        self.assertIn("process->setParent(nullptr);", release)
        self.assertIn("connect(process, &QProcess::finished, process, &QObject::deleteLater);", release)

    def test_finish_is_idempotent(self):
        self.assertRegex(TRANSACTION, r"void finish\(\)\s*\{\s*if \(m_finished\)\s*return;\s*m_finished = true;")

    def test_fail_releases_before_the_error_status(self):
        fail = method("void fail")
        self.assertRegex(fail, r"finish\(\);\s*setStatus\(DoneWithErrorStatus\);\s*\}$")

    def test_every_terminal_status_outside_fail_is_the_success_path(self):
        outside = TRANSACTION.replace(method("void fail"), "")
        self.assertNotIn("DoneWithErrorStatus", outside)
        self.assertNotIn("CancelledStatus", outside)
        self.assertEqual(outside.count("setStatus(DoneStatus)"), 1)

    def test_success_path_releases_first_and_keeps_only_a_guarded_backend(self):
        confirm = method("void confirmInstalled")
        finished = next(part for part in lambdas(confirm) if "setStatus(DoneStatus)" in part)
        order = [
            finished.index("const QPointer<EmberBSDBackend> backend = m_backend;"),
            finished.index("finish();"),
            finished.index("setStatus(DoneStatus);"),
            finished.index("backend->checkForUpdates();"),
        ]
        self.assertEqual(order, sorted(order))
        after_finish = finished[finished.index("finish();"):]
        self.assertNotIn("m_backend->", after_finish)

    def test_both_processes_handle_errorOccurred(self):
        for name in ("void start", "void confirmInstalled"):
            body = method(name)
            handlers = [part for part in lambdas(body) if part.startswith("process, &QProcess::errorOccurred") or part.startswith("check, &QProcess::errorOccurred")]
            self.assertEqual(len(handlers), 1, name)
            self.assertIn("fail(", handlers[0])
            self.assertIn("m_process = nullptr;", handlers[0])

    def test_reload_waits_for_the_install(self):
        check = SOURCE[SOURCE.index("void EmberBSDBackend::checkForUpdates()"):]
        self.assertRegex(check, r"if \(m_installing\)\s*return;\s*reload\(\);")

    def test_install_is_refused_during_a_reload(self):
        install = SOURCE[END:SOURCE.index("Transaction *EmberBSDBackend::removeApplication")]
        condition = re.search(r"if \((.*?)\)\s*return refused\(app, Transaction::InstallRole\);", install, re.S).group(1)
        self.assertIn("m_installing", condition)
        self.assertIn("m_process", condition)


if __name__ == "__main__":
    unittest.main()
