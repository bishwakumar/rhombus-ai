import { test } from '@playwright/test';

/** Records what a test found; the terminal reporter prints it as an "ℹ" line under the test. */
export function note(text: string) {
  test.info().annotations.push({ type: 'info', description: text });
}
