// SPDX-License-Identifier: BSD-2-Clause
// Origin: EmberBSD (AI-assisted), installed Milou drag MIME conversion contract.
#include <QGuiApplication>
#include <QMimeData>
#include <QQmlEngine>
#include <QUrl>
#include <QVariantMap>
#include <cstdio>

int main(int argc, char **argv)
{
    QGuiApplication app(argc, argv);
    QQmlEngine engine;
    QObject *helper = engine.singletonInstance<QObject *>("org.kde.milou", "MouseHelper");
    if (!helper) {
        std::fputs("FAIL: installed Milou singleton unavailable\n", stderr);
        return 2;
    }
    QMimeData data;
    const QString text = QString::fromUtf8("EmberBSD drag café");
    const QString html = QStringLiteral("<b>EmberBSD</b>");
    const QList<QUrl> urls = {QUrl(QStringLiteral("file:///tmp/ember%20file")),
                             QUrl(QStringLiteral("https://example.org/ember?q=1"))};
    const QByteArray binary("\0\x7fX", 3);
    data.setText(text);
    data.setHtml(html);
    data.setUrls(urls);
    data.setData(QStringLiteral("application/x-ember-fixture"), binary);
    QVariantMap result;
    if (!QMetaObject::invokeMethod(helper, "generateMimeDataMap", Qt::DirectConnection,
            Q_RETURN_ARG(QVariantMap, result), Q_ARG(QMimeData *, &data))) {
        std::fputs("FAIL: installed MIME method invocation\n", stderr);
        return 2;
    }
    const QVariant uriValue = result.value(QStringLiteral("text/uri-list"));
    if (uriValue.metaType() != QMetaType::fromType<QVariantList>()) {
        std::fprintf(stderr, "FAIL: URI list overwritten; expected QVariantList, got %s\n",
                     uriValue.typeName());
        return 3;
    }
    const QVariantList converted = uriValue.toList();
    if (converted.size() != urls.size() || converted[0].toUrl() != urls[0]
        || converted[1].toUrl() != urls[1]
        || result.value(QStringLiteral("text/plain")).toString() != text
        || result.value(QStringLiteral("text/html")).toString() != html
        || result.value(QStringLiteral("application/x-ember-fixture")).toByteArray() != binary
        || result.size() != 4) {
        std::fputs("FAIL: MIME values changed during conversion\n", stderr);
        return 3;
    }
    std::puts("PASS: installed Milou preserves URL list, UTF-8 text, HTML and opaque bytes");
    return 0;
}
