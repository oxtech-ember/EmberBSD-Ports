// SPDX-License-Identifier: BSD-2-Clause
// Origin: EmberBSD contributors (AI-assisted).
#include <QCoreApplication>
#include <QDebug>
#include <QJsonDocument>
#include <QJsonObject>
#include <QString>
#include <cstdio>

static QString formatted;
static int messages;
static volatile int returned;

static void recordMessage(QtMsgType type, const QMessageLogContext &context,
                          const QString &message)
{
    formatted = qFormatLogMessage(type, context, message);
    ++messages;
}

extern "C" Q_DECL_EXPORT Q_NEVER_INLINE void ember_qt_backtrace_probe()
{
    qWarning("ember-qt-backtrace-marker");
    returned = 1; // Keep the named frame on the stack until logging returns.
}

int main(int argc, char **argv)
{
    qunsetenv("QT_MESSAGE_PATTERN");
    QCoreApplication application(argc, argv);
    qSetMessagePattern(QStringLiteral("%{message}|%{backtrace depth=16 separator=\";\"}"));
    const QtMessageHandler previous = qInstallMessageHandler(recordMessage);
    ember_qt_backtrace_probe();
    qInstallMessageHandler(previous);
    const bool marker = formatted.contains(QStringLiteral("ember-qt-backtrace-marker"));
    const bool symbol = formatted.contains(QStringLiteral("ember_qt_backtrace_probe"));
    const bool success = messages == 1 && returned == 1 && marker && symbol;
    const QJsonObject result{{QStringLiteral("success"), success},
                             {QStringLiteral("messages"), messages},
                             {QStringLiteral("marker_found"), marker},
                             {QStringLiteral("symbol_found"), symbol},
                             {QStringLiteral("qt_version"), QString::fromLatin1(qVersion())},
                             {QStringLiteral("formatted"), formatted}};
    const QByteArray json = QJsonDocument(result).toJson(QJsonDocument::Compact) + '\n';
    if (std::fwrite(json.constData(), 1, static_cast<std::size_t>(json.size()), stdout)
            != static_cast<std::size_t>(json.size()))
        return 2;
    return success ? 0 : 1;
}
