/*
 * SPDX-License-Identifier: GPL-2.0-only OR GPL-3.0-only OR LicenseRef-KDE-Accepted-GPL
 * SPDX-FileCopyrightText: 2026 EmberBSD contributors
 *
 * The package list is the SDK client's read-only catalog command.
 * Arguments are fixed. State and cache are this user's XDG directories.
 * Install runs the polkit-authorized helper with one catalog root.
 * Remove is not called.
 *
 * A search that arrives before the catalog stays open. It is completed with
 * the real resources, or with the real error, when the client finishes.
 * An empty result is not emitted before that attempt.
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
#include <QPointer>
#include <QProcess>
#include <QRegularExpression>
#include <QStandardPaths>
#include <QTimer>
#include <utility>

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
        completePending();
        Q_EMIT fetchingUpdatesProgressChanged();
        return;
    }
    m_ready = false;
    m_error.clear();
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
            QVector<EmberBSDResource *> created;
            const QString releaseId = root.value(QStringLiteral("release_id")).toString();
            for (const QJsonValue &value : root.value(QStringLiteral("packages")).toArray()) {
                const QJsonObject package = value.toObject();
                if (package.value(QStringLiteral("base")).toString().isEmpty() || package.value(QStringLiteral("pkgname")).toString().isEmpty())
                    continue;
                bool desktop = false;
                if (package.value(QStringLiteral("role")).toString() == QLatin1String("desktop")) {
                    for (const QJsonValue &desktopValue : package.value(QStringLiteral("desktops")).toArray()) {
                        auto *resource = new EmberBSDResource(package, desktopValue.toObject(), releaseId, this);
                        if (resource->isDesktop()) {
                            created.append(resource);
                            desktop = true;
                        } else {
                            delete resource;
                        }
                    }
                }
                if (!desktop)
                    created.append(new EmberBSDResource(package, {}, releaseId, this));
            }
            const auto retired = m_resources;
            m_resources = created;
            for (EmberBSDResource *resource : retired) {
                Q_EMIT resourceRemoved(resource);
                resource->deleteLater();
            }
            m_error.clear();
            m_binding = root.value(QStringLiteral("desktop_binding")).toString();
            m_desktopCount = 0;
            for (EmberBSDResource *resource : m_resources) {
                if (resource->isDesktop())
                    ++m_desktopCount;
            }
            const QJsonObject counts = root.value(QStringLiteral("counts")).toObject();
            qInfo().noquote() << QStringLiteral("emberbsd-desktop") << releaseId
                              << QStringLiteral("desktop") << m_desktopCount
                              << QStringLiteral("packages") << counts.value(QStringLiteral("total")).toInt()
                              << QStringLiteral("binding") << m_binding;
        }
    }
    m_ready = true;
    completePending();
    Q_EMIT contentsChanged();
    Q_EMIT fetchingUpdatesProgressChanged();
}

void EmberBSDBackend::completePending()
{
    if (!m_ready)
        return;
    const auto pending = std::exchange(m_pending, {});
    for (const PendingSearch &item : pending) {
        if (!item.stream)
            continue;
        item.stream->deliver(match(item.filter));
    }
}

QVector<StreamResult> EmberBSDBackend::match(const Filters &filter) const
{
    QVector<StreamResult> found;
    const bool allPackages = filter.category && filter.category->matchesCategoryName(QStringLiteral("packages"));
    const bool components = filter.category && filter.category->matchesCategoryName(QStringLiteral("components"));
    for (EmberBSDResource *resource : m_resources) {
        if (!filter.resourceUrl.isEmpty() && resource->url() != filter.resourceUrl)
            continue;
        if (components) {
            if (!resource->isComponent())
                continue;
        } else if (!allPackages && !resource->isDesktop()) {
            continue;
        }
        if (!filter.search.isEmpty() && !resource->matchesText(filter.search))
            continue;
        if (filter.shouldFilter(resource))
            found.append(StreamResult(resource));
    }
    return found;
}

ResultsStream *EmberBSDBackend::search(const Filters &filter)
{
    auto *stream = new EmberBSDResultsStream;
    m_pending.append(PendingSearch{stream, filter});
    QTimer::singleShot(0, this, [this] {
        completePending();
    });
    return stream;
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
    if (!m_ready)
        return new InlineMessage(InlineMessage::Information, QStringLiteral("package-x-generic"), i18n("Reading the signed package catalog."));
    if (m_desktopCount == 0) {
        const QString message = m_binding == QLatin1String("unavailable")
            ? i18n("Installed desktop files could not be read. Application cards are omitted. Packages stay in All packages.")
            : i18n("No installed desktop application matched the signed catalog. Packages stay in All packages.");
        return new InlineMessage(InlineMessage::Information, QStringLiteral("package-x-generic"), message);
    }
    return nullptr;
}

Transaction *EmberBSDBackend::refused(AbstractResource *app, Transaction::Role role)
{
    return new RefusedTransaction(app, role);
}

void EmberBSDBackend::installFinished()
{
    m_installing = false;
}

void EmberBSDBackend::reportInstall(const QString &text)
{
    const QString detail = text.trimmed();
    if (!detail.isEmpty())
        Q_EMIT passiveMessage(detail.left(800));
}

namespace {
const QRegularExpression packageRootPattern(QStringLiteral("^[A-Za-z0-9][A-Za-z0-9._+-]*(?:/[A-Za-z0-9][A-Za-z0-9._+-]*)+$"));

bool catalogRoot(const QString &root)
{
    return packageRootPattern.match(root).hasMatch() && !root.split(QLatin1Char('/')).contains(QStringLiteral(".."));
}
}

/*
 * pkexec runs the helper as root. This user process cannot stop it. Thus the
 * transaction is not cancellable. The authorization dialog has its own
 * cancel, which ends the helper with a refusal.
 *
 * The backend owns the transaction. Catalog resources are replaced on each
 * reload, so a resource is not a safe owner. A terminal status lets Discover
 * delete the transaction later. finish() releases the backend on every
 * terminal path, including destruction before the process callback.
 */
class InstallTransaction : public Transaction
{
public:
    InstallTransaction(EmberBSDBackend *backend, EmberBSDResource *app)
        : Transaction(backend, app, InstallRole, {}, true)
        , m_backend(backend)
        , m_root(app->packageRoot())
        , m_base(app->packageName())
        , m_version(app->availableVersion())
    {
        setCancellable(false);
        setStatus(QueuedStatus);
        QTimer::singleShot(0, this, [this] {
            start();
        });
    }

    ~InstallTransaction() override
    {
        release(m_process);
        finish();
    }

    void cancel() override
    {
    }

    QString name() const override
    {
        return i18n("Install");
    }

private:
    void start()
    {
        if (!m_backend) {
            fail(QString());
            return;
        }
        QProcess *process = m_process = new QProcess(this);
        process->setProgram(QStringLiteral("/usr/pkg/bin/pkexec"));
        process->setArguments({QStringLiteral("/usr/pkg/libexec/emberbsd-discover-install"), m_root});
        connect(process, &QProcess::readyReadStandardError, this, [this, process] {
            const QString text = QString::fromUtf8(process->readAllStandardError());
            m_detail += text;
            if (!m_committing && text.contains(QLatin1String("Install:"))) {
                m_committing = true;
                setStatus(CommittingStatus);
                setProgress(60);
            } else if (!m_committing) {
                setStatus(DownloadingStatus);
                setProgress(25);
            }
        });
        connect(process, &QProcess::finished, this, [this](int code, QProcess::ExitStatus status) {
            m_process = nullptr;
            if (status != QProcess::NormalExit || code != 0) {
                if (code == 126 || code == 127 || m_detail.contains(QLatin1String("not authorized"), Qt::CaseInsensitive)
                    || m_detail.contains(QLatin1String("dismissed"), Qt::CaseInsensitive)
                    || m_detail.contains(QLatin1String("Authorization"), Qt::CaseInsensitive))
                    m_detail = i18n("Authorization was denied.");
                fail(m_detail);
                return;
            }
            confirmInstalled();
        });
        connect(process, &QProcess::errorOccurred, this, [this, process](QProcess::ProcessError) {
            // A crash still reports Running here; finished() handles it.
            if (process->state() == QProcess::NotRunning) {
                m_process = nullptr;
                fail(process->errorString());
            }
        });
        setStatus(DownloadingStatus);
        setProgress(10);
        process->start();
    }

    void confirmInstalled()
    {
        QProcess *check = m_process = new QProcess(this);
        connect(check, &QProcess::finished, this, [this, check](int code, QProcess::ExitStatus) {
            m_process = nullptr;
            const QString installed = QString::fromUtf8(check->readAllStandardOutput()).trimmed();
            check->deleteLater();
            const QString expected = m_base + QLatin1Char('-') + m_version;
            if (code != 0 || installed != expected) {
                fail(i18n("The package database does not list %1.", expected));
                return;
            }
            const QPointer<EmberBSDBackend> backend = m_backend;
            finish();
            setProgress(100);
            setStatus(DoneStatus);
            if (backend)
                backend->checkForUpdates();
        });
        connect(check, &QProcess::errorOccurred, this, [this, check](QProcess::ProcessError) {
            if (check->state() == QProcess::NotRunning) {
                m_process = nullptr;
                check->deleteLater();
                fail(check->errorString());
            }
        });
        check->start(QStringLiteral("/usr/sbin/pkg_info"), {QStringLiteral("-e"), m_base});
    }

    // Every error path ends here: release the backend, then the terminal status.
    void fail(const QString &text)
    {
        m_detail = text;
        if (m_backend)
            m_backend->reportInstall(m_detail);
        finish();
        setStatus(DoneWithErrorStatus);
    }

    // A running process must outlive this transaction. pkexec runs as root
    // and ignores a signal from this user, so ~QProcess would block.
    void release(QProcess *process)
    {
        if (!process)
            return;
        disconnect(process, nullptr, this, nullptr);
        if (process->state() != QProcess::NotRunning) {
            process->setParent(nullptr);
            connect(process, &QProcess::finished, process, &QObject::deleteLater);
        }
    }

    void finish()
    {
        if (m_finished)
            return;
        m_finished = true;
        if (m_backend)
            m_backend->installFinished();
        m_backend = nullptr;
    }

    QPointer<EmberBSDBackend> m_backend;
    QProcess *m_process = nullptr;
    QString m_root;
    QString m_base;
    QString m_version;
    QString m_detail;
    bool m_committing = false;
    bool m_finished = false;
};

Transaction *EmberBSDBackend::installApplication(AbstractResource *app, const AddonList &)
{
    auto *resource = qobject_cast<EmberBSDResource *>(app);
    // A running reload (m_process) replaces every resource. Install and reload never overlap.
    if (!resource || m_installing || m_process || resource->catalogAction() != QLatin1String("available") || !catalogRoot(resource->packageRoot()))
        return refused(app, Transaction::InstallRole);
    m_installing = true;
    return new InstallTransaction(this, resource);
}

Transaction *EmberBSDBackend::removeApplication(AbstractResource *app)
{
    return refused(app, Transaction::RemoveRole);
}

void EmberBSDBackend::checkForUpdates()
{
    // A reload replaces every resource. The transaction reloads at its end.
    if (m_installing)
        return;
    reload();
}

#include "EmberBSDBackend.moc"
#include "moc_EmberBSDBackend.cpp"
