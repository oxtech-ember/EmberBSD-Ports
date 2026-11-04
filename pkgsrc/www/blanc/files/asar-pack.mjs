#!/usr/bin/env node
// SPDX-License-Identifier: BSD-2-Clause
// Copyright (c) 2026 EmberBSD contributors.
// Origin: EmberBSD (AI-assisted). This invokes the pinned upstream ASAR tool.

import path from 'node:path';
import { pathToFileURL } from 'node:url';

const [asarModule, appRoot, outputPath] = process.argv.slice(2);
if (!asarModule || !appRoot || !outputPath) {
  throw new Error('Usage: asar-pack.mjs asar-module app-root output-asar');
}

const { createPackage, listPackage, extractFile } = await import(pathToFileURL(asarModule).href);
await createPackage(appRoot, outputPath);
const files = listPackage(outputPath, { isPack: true }).map((entry) =>
  entry.replace(/^pack\s*:\s*/, '').replace(/^\/+/, ''),
);
const result = { files };
if (files.includes('package.json') && files.includes('src/main/main.js')) {
  result.packageMetadata = JSON.parse(extractFile(outputPath, 'package.json').toString('utf8'));
  result.tabSource = extractFile(outputPath, 'src/main/tab-view.js').toString('utf8');
  result.mainSource = extractFile(outputPath, 'src/main/main.js').toString('utf8');
  result.identitySource = extractFile(outputPath, 'src/main/app-identity.js').toString('utf8');
}
process.stdout.write(JSON.stringify(result) + '\n');
