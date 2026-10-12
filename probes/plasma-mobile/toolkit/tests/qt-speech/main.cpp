// SPDX-License-Identifier: BSD-2-Clause
// Origin: EmberBSD (AI-assisted). Installed plugin and finite synthesis consumer.
#include <QAudioFormat>
#include <QCoreApplication>
#include <QDebug>
#include <QTextToSpeech>
#include <QTimer>
#include <QtEndian>

int main(int argc, char **argv)
{
    QCoreApplication app(argc, argv);
    if (argc != 2)
        return 2;
    const QString engine = QString::fromLocal8Bit(argv[1]);
    qInfo() << "Available engines:" << QTextToSpeech::availableEngines();
    QTextToSpeech speech(engine);
    if (engine == QStringLiteral("ember-missing-engine")) {
        if (speech.state() != QTextToSpeech::Error)
            return 3;
        qInfo() << "PASS: unknown engine refused";
        return 0;
    }
    if (speech.engine() != engine || speech.state() == QTextToSpeech::Error
        || speech.availableLocales().isEmpty() || speech.availableVoices().isEmpty()) {
        qCritical() << "Engine initialization failed:" << speech.errorString();
        return 3;
    }
    const bool synthesize = engine == QStringLiteral("flite");
    const auto capability = synthesize ? QTextToSpeech::Capability::Synthesize
                                      : QTextToSpeech::Capability::Speak;
    if (!speech.engineCapabilities().testFlag(capability))
        return 3;
    bool active = false;
    qsizetype samples = 0;
    quint64 energy = 0;
    QObject::connect(&speech, &QTextToSpeech::errorOccurred, &app,
                     [&](QTextToSpeech::ErrorReason reason, const QString &message) {
        qCritical() << "Speech error:" << reason << message;
        app.exit(4);
    });
    QObject::connect(&speech, &QTextToSpeech::stateChanged, &app,
                     [&](QTextToSpeech::State state) {
        qInfo() << "State:" << state;
        active = active || state == QTextToSpeech::Synthesizing
                        || state == QTextToSpeech::Speaking;
        if (state != QTextToSpeech::Ready || !active)
            return;
        if (synthesize && (samples < 1000 || samples > 480000 || energy < 1000000)) {
            qCritical() << "Missing or invalid speech samples:" << samples << energy;
            app.exit(5);
            return;
        }
        qInfo() << "PASS: engine" << engine << "finished; samples" << samples
                << "energy" << energy;
        app.exit(0);
    });
    QTimer::singleShot(15000, &app, [&] {
        qCritical() << "Speech deadline expired";
        app.exit(6);
    });
    QTimer::singleShot(0, &app, [&] {
        const QString text = QStringLiteral("EmberBSD speech synthesis.");
        if (!synthesize) {
            speech.say(text);
            return;
        }
        speech.synthesize(text, &app, [&](const QAudioFormat &format, const QByteArray &data) {
            if (!format.isValid() || format.channelCount() != 1
                || format.sampleFormat() != QAudioFormat::Int16
                || format.sampleRate() < 8000 || format.sampleRate() > 48000
                || data.size() % 2 != 0) {
                qCritical() << "Unexpected PCM format or size";
                app.exit(7);
                return;
            }
            samples += data.size() / 2;
            for (qsizetype at = 0; at < data.size(); at += 2) {
                const qint64 sample = qFromLittleEndian<qint16>(data.constData() + at);
                energy += static_cast<quint64>(sample * sample);
            }
        });
    });
    return app.exec();
}
