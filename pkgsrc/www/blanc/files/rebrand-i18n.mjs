// SPDX-License-Identifier: BSD-2-Clause
// Origin: EmberBSD contributors (AI-assisted). Upstream catalogs remain source inputs.
import fs from 'node:fs';
import path from 'node:path';
import { pathToFileURL } from 'node:url';

const [root, keysPath] = process.argv.slice(2);
if (!root || !keysPath || !path.isAbsolute(root) || !path.isAbsolute(keysPath)) throw Error('absolute catalog root and key list required');
const keys = JSON.parse(fs.readFileSync(keysPath, 'utf8'));
if (!Array.isArray(keys) || new Set(keys).size !== keys.length) throw Error('invalid identity key list');
const languages = {
  en: ['Play the launch animation when Ember Browser opens', 'Shows the Ember Browser icon once when the first start page opens. Skipped when reduced motion is enabled.', 'Usage statistics are not sent by Ember Browser.', 'Updates are managed by system packages. Search suggestions are optional and can be changed in Settings.', 'Ember Browser uses Chromium through Electron. Electron and Chromium are updated with system packages.', 'Ember Browser connects to websites you open. Searches and enabled suggestions go to your selected search provider; DNS uses your configured provider.'],
  de: ['Startanimation beim Öffnen von Ember Browser abspielen', 'Zeigt das Ember-Browser-Symbol einmal auf der ersten Startseite. Bei reduzierter Bewegung wird dies übersprungen.', 'Ember Browser sendet keine Nutzungsstatistiken.', 'Updates werden über Systempakete verwaltet. Suchvorschläge sind optional und in den Einstellungen änderbar.', 'Ember Browser verwendet Chromium über Electron. Electron und Chromium werden über Systempakete aktualisiert.', 'Ember Browser verbindet sich mit geöffneten Websites. Suchen und aktivierte Vorschläge gehen an den gewählten Suchanbieter; DNS nutzt den konfigurierten Anbieter.'],
  es: ['Reproducir la animación al abrir Ember Browser', 'Muestra el icono de Ember Browser una vez en la primera página de inicio. Se omite si se reduce el movimiento.', 'Ember Browser no envía estadísticas de uso.', 'Las actualizaciones se gestionan con paquetes del sistema. Las sugerencias de búsqueda son opcionales y se cambian en Ajustes.', 'Ember Browser usa Chromium mediante Electron. Electron y Chromium se actualizan con paquetes del sistema.', 'Ember Browser se conecta a los sitios que abres. Las búsquedas y sugerencias activadas van al proveedor elegido; DNS usa el proveedor configurado.'],
  fr: ['Afficher l’animation au lancement d’Ember Browser', 'Affiche une fois l’icône d’Ember Browser sur la première page de démarrage. Ignoré si les animations sont réduites.', 'Ember Browser n’envoie pas de statistiques d’utilisation.', 'Les mises à jour sont gérées par les paquets système. Les suggestions de recherche sont facultatives et modifiables dans les réglages.', 'Ember Browser utilise Chromium via Electron. Electron et Chromium sont mis à jour par les paquets système.', 'Ember Browser se connecte aux sites ouverts. Les recherches et suggestions activées vont au moteur choisi ; DNS utilise le fournisseur configuré.'],
  it: ['Riproduci l’animazione quando apri Ember Browser', 'Mostra una volta l’icona di Ember Browser nella prima pagina iniziale. Saltata se il movimento è ridotto.', 'Ember Browser non invia statistiche di utilizzo.', 'Gli aggiornamenti sono gestiti dai pacchetti di sistema. I suggerimenti di ricerca sono facoltativi e modificabili nelle impostazioni.', 'Ember Browser usa Chromium tramite Electron. Electron e Chromium vengono aggiornati con i pacchetti di sistema.', 'Ember Browser si connette ai siti aperti. Ricerche e suggerimenti attivi vanno al provider scelto; DNS usa il provider configurato.'],
  'pt-BR': ['Reproduzir a animação ao abrir o Ember Browser', 'Mostra o ícone do Ember Browser uma vez na primeira página inicial. É ignorada se o movimento reduzido estiver ativo.', 'O Ember Browser não envia estatísticas de uso.', 'Atualizações são gerenciadas pelos pacotes do sistema. Sugestões de pesquisa são opcionais e podem ser alteradas nas configurações.', 'O Ember Browser usa Chromium por meio do Electron. Electron e Chromium são atualizados pelos pacotes do sistema.', 'O Ember Browser se conecta aos sites abertos. Pesquisas e sugestões ativadas vão ao provedor escolhido; DNS usa o provedor configurado.'],
};
const overrides = ['settings.general.launchSunrise.label', 'settings.general.launchSunrise.hint',
  'settings.privacy.usagePing.hint', 'onboarding.privacy.body',
  'settings.help.blancUsesChromiumThrough', 'settings.help.blancConnectsToWebsites'];
for (const [locale, values] of Object.entries(languages)) {
  const file = path.join(root, 'copy/messages', `${locale}.json`);
  const catalog = JSON.parse(fs.readFileSync(file, 'utf8'));
  for (const key of keys) {
    if (typeof catalog[key]?.message === 'string') catalog[key].message = catalog[key].message.replaceAll('Blanc', 'Ember Browser');
  }
  for (let i = 0; i < overrides.length; i++) {
    if (!catalog[overrides[i]]) throw Error(`missing ${locale}/${overrides[i]}`);
    catalog[overrides[i]].message = values[i];
  }
  fs.writeFileSync(file, JSON.stringify(catalog, null, 2) + '\n');
}
const { runAck, runBuild } = await import(pathToFileURL(path.join(root, 'copy/lib/cli.mjs')));
for (const locale of Object.keys(languages).filter(code => code !== 'en')) runAck(root, locale, [...new Set([...keys, ...overrides])]);
runBuild(root);
console.log('Generated derivative interface catalogs from upstream sources.');
