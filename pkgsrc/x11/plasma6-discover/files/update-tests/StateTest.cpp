/*
 * SPDX-License-Identifier: GPL-2.0-only OR GPL-3.0-only OR LicenseRef-KDE-Accepted-GPL
 * SPDX-FileCopyrightText: 2026 EmberBSD contributors
 */
#include "EmberUpdateState.h"

#include <QJsonArray>
#include <QJsonDocument>
#include <QSaveFile>
#include <QTemporaryDir>
#include <QTest>

class StateTest : public QObject
{
    Q_OBJECT
    QTemporaryDir m_dir;
    QString file() const { return m_dir.filePath(QStringLiteral("state.json")); }

    QJsonObject record(QString status, QJsonValue generation, QJsonArray packages = {}) const
    {
        return {{"schema", "emberbsd.update-state.v1"}, {"status", status}, {"checked_at", 1730000000},
                {"available", QJsonObject{{"os_generation", generation}, {"packages", packages}}},
                {"reboot_required", false}, {"os_hold", QJsonValue::Null}, {"last_error", QJsonValue::Null},
                {"running_slot", "A"}, {"confirmed_slot", "A"}};
    }

    void write(const QJsonObject &s)
    {
        QSaveFile out(file());
        QVERIFY(out.open(QIODevice::WriteOnly));
        const auto bytes = QJsonDocument(s).toJson();
        QCOMPARE(out.write(bytes), bytes.size());
        QVERIFY(out.commit());
    }

private Q_SLOTS:
    void init() { QFile::remove(file()); }

    void disabledAndFirstCheck()
    {
        EmberUpdateState state(nullptr, file());
        QVERIFY(!state.canApply());
        QVERIFY(state.value().isEmpty());
        QVERIFY(!state.description().isEmpty());

        auto s = record("idle", QJsonValue::Null);
        s["checked_at"] = QJsonValue::Null;
        write(s);
        QTRY_COMPARE(state.value(), s);
        QVERIFY(!state.needsReboot());
        QVERIFY(!state.canApply());
    }

    void resumeAndFailure()
    {
        auto s = record("ready", 12);
        s["reboot_required"] = true;
        write(s);
        EmberUpdateState state(nullptr, file());
        QVERIFY(state.needsReboot());
        QVERIFY(!state.canApply());
        s["reboot_required"] = false;
        s["status"] = "trial";
        s["running_slot"] = "B";
        write(s);
        QTRY_COMPARE(state.value(), s);
        QVERIFY(!state.needsReboot());
        QVERIFY(!state.canApply());
        s["status"] = "error";
        s["last_error"] = "Failed to verify generation 12";
        write(s);
        QTRY_VERIFY(state.canApply());
        QVERIFY(state.description().contains(s["last_error"].toString()));
        QVERIFY(QFile::remove(file()));
        QTRY_VERIFY(state.value().isEmpty());
        QVERIFY(!state.canApply());
    }

    void customKernelAndPackages()
    {
        auto s = record("available", 13);
        s["os_hold"] = "custom-kernel";
        write(s);
        EmberUpdateState state(nullptr, file());
        QVERIFY(!state.canApply());
        const QJsonArray packages{"editor-1.2", "libone-2.0", "libtwo-3.0", "app-4.0"};
        s["available"] = QJsonObject{{"os_generation", 13}, {"packages", packages}};
        write(s);
        QTRY_VERIFY(state.canApply());
        QVERIFY(state.description(true).contains("app-4.0"));
        for (auto mode : {"checking", "preparing", "trial"}) {
            s["status"] = mode;
            write(s);
            QTRY_COMPARE(state.value(), s);
            QVERIFY(!state.canApply());
        }
    }

    void invalidRecordClearsActions()
    {
        auto s = record("available", 9);
        write(s);
        EmberUpdateState state(nullptr, file());
        QVERIFY(state.canApply());
        s["reboot_required"] = "true";
        write(s);
        QTRY_VERIFY(state.value().isEmpty());
        QVERIFY(!state.canApply());
        QVERIFY(!state.needsReboot());
        auto invalid = record("available", 2.5);
        QVERIFY(EmberUpdateState::parse(QJsonDocument(invalid).toJson()).isEmpty());
    }
};

QTEST_GUILESS_MAIN(StateTest)
#include "StateTest.moc"
