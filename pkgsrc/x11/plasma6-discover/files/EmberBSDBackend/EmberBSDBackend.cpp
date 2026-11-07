/*
 * SPDX-License-Identifier: GPL-2.0-only OR GPL-3.0-only OR LicenseRef-KDE-Accepted-GPL
 * SPDX-FileCopyrightText: 2026 EmberBSD contributors
 *
 * The catalog comes from the SDK client plan. The arguments are fixed.
 * The client verifies signed current and reports the install action.
 * This backend does not install or remove packages.
 */

#include "EmberBSDBackend.h"
#include "EmberBSDResource.h"

#include <Category/Category.h>
#include <resources/StandardBackendUpdater.h>
#include <Transaction/Transaction.h>

#include <KLocalizedString>
#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>
#include <QProcess>

DISCOVER_BACKEND_PLUGIN(EmberBSDBackend)

namespace {
const QString python = QStringLiteral("/usr/pkg/bin/python3.15");
const QString client = QStringLiteral("/usr/local/libexec/ember-sdk.pyz");
const QString config = QStringLiteral("/usr/local/etc/ember-sdk.json");
const QString root = QStringLiteral("www/blanc");
}

class RefusedTransaction : public Transaction
{
public:
    RefusedTransaction(AbstractResource *app, Role role)
        : Transaction(app, app, role, {}, true)
    {
        setStatus(DoneWithErrorStatus);
    }
    void cancel() override
    {
    }
    QString name() const override
    {
        return i18n("Unavailable");
    }
};

EmberBSDBackend::EmberBSDBackend(QObject *parent)
    : AbstractResourcesBackend(parent)
    , m_updater(new StandardBackendUpdater(this))
{
    reload();
}

bool EmberBSDBackend::isValid() const
{
    return true;
}

void EmberBSDBackend::reload()
{
    QProcess process;
    process.start(python, {client, QStringLiteral("--config"), config, QStringLiteral("plan"), QStringLiteral("--package"), root});
    if (!process.waitForStarted(5000) || !process.waitForFinished(120000) || process.exitCode() != 0) {
        Q_EMIT passiveMessage(i18n("The signed catalog client did not return a plan."));
        m_ready = true;
        Q_EMIT contentsChanged();
        return;
    }
    const QJsonDocument document = QJsonDocument::fromJson(process.readAllStandardOutput());
    const QJsonArray packages = document.object().value(QStringLiteral("packages")).toArray();
    const QString releaseId = document.object().value(QStringLiteral("release_id")).toString();
    for (const QJsonValue &value : packages) {
        const QJsonObject package = value.toObject();
        if (package.value(QStringLiteral("root")).toString() != root)
            continue;
        const QString pkgname = package.value(QStringLiteral("pkgname")).toString();
        const int split = pkgname.lastIndexOf(QLatin1Char('-'));
        const QString packageId = split > 0 ? pkgname.left(split) : pkgname;
        const QString version = split > 0 ? pkgname.mid(split + 1) : pkgname;
        const bool installed = package.value(QStringLiteral("action")).toString() == QLatin1String("installed");
        const quint64 size = static_cast<quint64>(package.value(QStringLiteral("artifact")).toObject().value(QStringLiteral("size")).toDouble());
        m_browser = new EmberBSDResource(packageId, version, installed, size, releaseId, this);
        break;
    }
    if (!m_browser)
        Q_EMIT passiveMessage(i18n("Signed current has no www/blanc package."));
    m_ready = true;
    Q_EMIT contentsChanged();
}

ResultsStream *EmberBSDBackend::search(const Filters &filter)
{
    QVector<StreamResult> found;
    const bool categoryMatches = !filter.category || filter.category->matchesCategoryName(QStringLiteral("emberbsd"));
    const bool textMatches = filter.search.isEmpty() || (m_browser && (m_browser->name().contains(filter.search, Qt::CaseInsensitive)
                                                                        || m_browser->packageName().contains(filter.search, Qt::CaseInsensitive)));
    if (m_browser && categoryMatches && textMatches && filter.state <= m_browser->state())
        found.append(m_browser);
    return new ResultsStream(QStringLiteral("emberbsd"), found);
}

AbstractReviewsBackend *EmberBSDBackend::reviewsBackend() const
{
    return nullptr;
}

AbstractBackendUpdater *EmberBSDBackend::backendUpdater() const
{
    return m_updater;
}

int EmberBSDBackend::updatesCount() const
{
    return 0;
}

int EmberBSDBackend::fetchingUpdatesProgress() const
{
    return m_ready ? 100 : 0;
}

QString EmberBSDBackend::displayName() const
{
    return QStringLiteral("EmberBSD");
}

bool EmberBSDBackend::hasApplications() const
{
    return m_browser != nullptr;
}

Transaction *EmberBSDBackend::refused(AbstractResource *app, Transaction::Role role)
{
    return new RefusedTransaction(app, role);
}

Transaction *EmberBSDBackend::installApplication(AbstractResource *app, const AddonList &)
{
    return refused(app, Transaction::InstallRole);
}

Transaction *EmberBSDBackend::removeApplication(AbstractResource *app)
{
    return refused(app, Transaction::RemoveRole);
}

void EmberBSDBackend::checkForUpdates()
{
}

#include "EmberBSDBackend.moc"
#include "moc_EmberBSDBackend.cpp"
