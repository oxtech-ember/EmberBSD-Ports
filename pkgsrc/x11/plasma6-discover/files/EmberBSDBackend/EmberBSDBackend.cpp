/*
 * SPDX-License-Identifier: GPL-2.0-only OR GPL-3.0-only OR LicenseRef-KDE-Accepted-GPL
 * SPDX-FileCopyrightText: 2026 EmberBSD contributors
 *
 * The package list is the SDK client's read-only catalog command.
 * Arguments are fixed. State and cache are this user's XDG directories.
 * Install and remove are not called.
 */

#include "EmberBSDBackend.h"
#include "EmberBSDResource.h"

#include <resources/AbstractResource.h>
#include <resources/StandardBackendUpdater.h>
#include <Transaction/Transaction.h>

#include <KLocalizedString>
#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>
#include <QProcess>
#include <QStandardPaths>

DISCOVER_BACKEND_PLUGIN(EmberBSDBackend)

namespace {
const QString python = QStringLiteral("/usr/pkg/bin/python3.15");
const QString client = QStringLiteral("/usr/local/libexec/ember-sdk.pyz");
const QString config = QStringLiteral("/usr/local/etc/ember-sdk.json");

QString userDirectory(QStandardPaths::StandardLocation location, const QString &name)
{
    const QString base = QStandardPaths::writableLocation(location);
    return base.isEmpty() ? QString() : base + QLatin1Char('/') + name;
}
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
    if (m_process)
        return;
    const QString stateDir = userDirectory(QStandardPaths::GenericStateLocation, QStringLiteral("discover-emberbsd"));
    const QString cacheDir = userDirectory(QStandardPaths::GenericCacheLocation, QStringLiteral("discover-emberbsd"));
    if (stateDir.isEmpty() || cacheDir.isEmpty()) {
        m_error = i18n("No user state directory is available for the signed catalog.");
        m_ready = true;
        Q_EMIT passiveMessage(m_error);
        Q_EMIT fetchingUpdatesProgressChanged();
        return;
    }
    m_ready = false;
    m_error.clear();
    qDeleteAll(m_resources);
    m_resources.clear();
    Q_EMIT fetchingUpdatesProgressChanged();
    m_process = new QProcess(this);
    connect(m_process, &QProcess::finished, this, [this](int code, QProcess::ExitStatus status) {
        const QByteArray output = m_process->readAllStandardOutput();
        const QByteArray errors = m_process->readAllStandardError();
        m_process->deleteLater();
        m_process = nullptr;
        applyCatalog(output, errors, code, status != QProcess::NormalExit);
    });
    m_process->start(python, {client, QStringLiteral("--config"), config, QStringLiteral("--state-dir"), stateDir, QStringLiteral("--cache-dir"), cacheDir, QStringLiteral("catalog")});
}

void EmberBSDBackend::applyCatalog(const QByteArray &output, const QByteArray &errors, int code, bool crashed)
{
    if (crashed || code != 0) {
        const QString detail = QString::fromUtf8(errors).trimmed();
        m_error = detail.isEmpty() ? i18n("The signed catalog client failed.") : detail.left(800);
        Q_EMIT passiveMessage(m_error);
    } else {
        const QJsonObject root = QJsonDocument::fromJson(output).object();
        if (root.value(QStringLiteral("schema")).toString() != QLatin1String("emberbsd.catalog-index.v1")) {
            m_error = i18n("The signed catalog client returned an unexpected index.");
            Q_EMIT passiveMessage(m_error);
        } else {
            const QString releaseId = root.value(QStringLiteral("release_id")).toString();
            const QJsonObject counts = root.value(QStringLiteral("counts")).toObject();
            for (const QJsonValue &value : root.value(QStringLiteral("packages")).toArray()) {
                const QJsonObject package = value.toObject();
                const QString pkgname = package.value(QStringLiteral("pkgname")).toString();
                const QString base = package.value(QStringLiteral("base")).toString();
                if (base.isEmpty() || pkgname.isEmpty())
                    continue;
                m_resources.append(new EmberBSDResource(
                    base,
                    package.value(QStringLiteral("version")).toString(),
                    package.value(QStringLiteral("root")).toString(),
                    package.value(QStringLiteral("role")).toString(),
                    package.value(QStringLiteral("action")).toString(),
                    package.value(QStringLiteral("installed_pkgname")).toString(),
                    static_cast<quint64>(package.value(QStringLiteral("size")).toDouble()),
                    releaseId,
                    this));
            }
            m_summary = i18n("Signed current %1 has %2 packages. %3 are outside the library categories and appear under Applications. %4 libraries stay in All packages and in search. The catalog has no desktop metadata.",
                             releaseId,
                             counts.value(QStringLiteral("total")).toInt(),
                             counts.value(QStringLiteral("package")).toInt(),
                             counts.value(QStringLiteral("library")).toInt());
            qInfo().noquote() << QStringLiteral("emberbsd-catalog") << releaseId
                              << QStringLiteral("total") << counts.value(QStringLiteral("total")).toInt()
                              << QStringLiteral("package") << counts.value(QStringLiteral("package")).toInt()
                              << QStringLiteral("library") << counts.value(QStringLiteral("library")).toInt();
            Q_EMIT passiveMessage(m_summary);
        }
    }
    m_ready = true;
    Q_EMIT contentsChanged();
    Q_EMIT fetchingUpdatesProgressChanged();
}

ResultsStream *EmberBSDBackend::search(const Filters &filter)
{
    QVector<StreamResult> found;
    Filters effective = filter;
    if (!filter.search.isEmpty())
        effective.category.reset();
    for (EmberBSDResource *resource : m_resources) {
        if (filter.search.isEmpty() && resource->isLibrary()) {
            const bool allPackages = filter.category && filter.category->matchesCategoryName(QStringLiteral("packages"));
            if (!allPackages)
                continue;
        }
        if (!filter.search.isEmpty() && !resource->name().contains(filter.search, Qt::CaseInsensitive) && !resource->packageName().contains(filter.search, Qt::CaseInsensitive)
            && !resource->comment().contains(filter.search, Qt::CaseInsensitive)) {
            continue;
        }
        if (effective.shouldFilter(resource))
            found.append(resource);
    }
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
    int count = 0;
    for (EmberBSDResource *resource : m_resources) {
        if (resource->state() == AbstractResource::Upgradeable)
            ++count;
    }
    return count;
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
    return true;
}

InlineMessage *EmberBSDBackend::explainDysfunction() const
{
    if (!m_error.isEmpty())
        return new InlineMessage(InlineMessage::Error, QStringLiteral("dialog-error"), m_error);
    if (!m_summary.isEmpty())
        return new InlineMessage(InlineMessage::Information, QStringLiteral("package-x-generic"), m_summary);
    if (!m_ready)
        return new InlineMessage(InlineMessage::Information, QStringLiteral("package-x-generic"), i18n("Reading the signed package catalog."));
    return nullptr;
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
    reload();
}

#include "EmberBSDBackend.moc"
#include "moc_EmberBSDBackend.cpp"
