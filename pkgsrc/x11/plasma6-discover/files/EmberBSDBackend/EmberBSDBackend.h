/*
 * SPDX-License-Identifier: GPL-2.0-only OR GPL-3.0-only OR LicenseRef-KDE-Accepted-GPL
 * SPDX-FileCopyrightText: 2026 EmberBSD contributors
 */

#pragma once

#include <Transaction/Transaction.h>
#include <resources/AbstractResourcesBackend.h>

#include <QVector>

class EmberBSDResource;
class QProcess;
class StandardBackendUpdater;

class EmberBSDBackend : public AbstractResourcesBackend
{
    Q_OBJECT
public:
    explicit EmberBSDBackend(QObject *parent = nullptr);

    bool isValid() const override;
    ResultsStream *search(const Filters &search) override;
    AbstractReviewsBackend *reviewsBackend() const override;
    AbstractBackendUpdater *backendUpdater() const override;
    int updatesCount() const override;
    int fetchingUpdatesProgress() const override;
    QString displayName() const override;
    bool hasApplications() const override;
    InlineMessage *explainDysfunction() const override;
    Transaction *installApplication(AbstractResource *app, const AddonList &addons) override;
    Transaction *removeApplication(AbstractResource *app) override;
    void checkForUpdates() override;

private:
    void reload();
    void applyCatalog(const QByteArray &output, const QByteArray &errors, int code, bool crashed);
    Transaction *refused(AbstractResource *app, Transaction::Role role);

    QVector<EmberBSDResource *> m_resources;
    StandardBackendUpdater *m_updater = nullptr;
    QProcess *m_process = nullptr;
    QString m_error;
    QString m_summary;
    bool m_ready = false;
};
