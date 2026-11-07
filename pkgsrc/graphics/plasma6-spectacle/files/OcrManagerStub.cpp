/*
 * Screenshot builds on this system do not link Tesseract.
 * The public OCR API stays present and reports that recognition is unavailable.
 */

#include "OcrManager.h"

OcrManager *OcrManager::s_instance = nullptr;

OcrWorker::OcrWorker(QObject *parent)
    : QObject(parent)
{
}

void OcrWorker::processImage(const QImage &, TessBaseAPI *)
{
}

OcrManager::OcrManager(QObject *parent)
    : QObject(parent)
    , m_tesseract(nullptr)
    , m_worker(nullptr)
    , m_timeoutTimer(nullptr)
    , m_status(OcrStatus::Error)
    , m_shouldRestoreToConfigured(false)
    , m_initialized(false)
{
}

OcrManager::~OcrManager() = default;

OcrManager *OcrManager::instance()
{
    if (!s_instance) {
        s_instance = new OcrManager(nullptr);
    }
    return s_instance;
}

bool OcrManager::isAvailable() const
{
    return false;
}

OcrManager::OcrStatus OcrManager::status() const
{
    return m_status;
}

QMap<QString, QString> OcrManager::availableLanguagesWithNames() const
{
    return {};
}

void OcrManager::setLanguagesByCode(const QStringList &)
{
}

QString OcrManager::currentLanguageCode() const
{
    return {};
}

void OcrManager::setConfigSyncSuspended(bool suspended)
{
    m_configSyncSuspended = suspended;
}

bool OcrManager::isConfigSyncSuspended() const
{
    return m_configSyncSuspended;
}

void OcrManager::recognizeText(const QImage &)
{
    Q_EMIT textRecognized({}, {}, false);
}

void OcrManager::recognizeTextWithLanguage(const QImage &, const QString &)
{
    Q_EMIT textRecognized({}, {}, false);
}

void OcrManager::handleRecognitionComplete(const QString &, bool)
{
}

#include "moc_OcrManager.cpp"
