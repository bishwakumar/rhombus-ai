// Saves a Rhombus login from a normal Chrome window, for when the automated login is blocked
// (e.g. Google: "This browser or app may not be secure").
//
// 1. Start Chrome with remote debugging (see README), log in to Rhombus there.
// 2. Run: npm run auth:chrome
import { chromium } from '@playwright/test';
import fs from 'node:fs';

const browser = await chromium.connectOverCDP('http://localhost:9222');
const context = browser.contexts()[0];
if (!context) {
  console.error('No Chrome window found. Start Chrome with --remote-debugging-port=9222 and log in first.');
  process.exit(1);
}
fs.mkdirSync('.auth', { recursive: true });
await context.storageState({ path: '.auth/state.json' });
console.log('Session saved to .auth/state.json');
await browser.close();
