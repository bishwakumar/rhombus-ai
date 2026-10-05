import { Page, Locator } from '@playwright/test';

/**
 * Every UI locator in one place. Built from the labels visible in Rhombus.
 * If one doesn't match, fix it here: run `npm run record`, click the element,
 * and copy the locator Playwright suggests.
 */
export const ui = (page: Page) => ({
  // Top tabs
  canvasTab: page.getByText('Canvas', { exact: true }).first(),
  logsTab: page.getByText('Logs', { exact: true }).first(),
  aiBuilderTab: page.getByText('AI Builder', { exact: true }).first(),
  scheduleTab: page.getByText('Schedule', { exact: true }).first(),

  // Canvas nodes
  node: (title: string): Locator => page.getByText(title, { exact: true }).first(),
  // The ▶ Run button: the app gives it a test ID (it has no visible text or aria-label)
  runButton: page.getByTestId('run-pipeline'),

  // Logs panel
  logEntry: (text: string | RegExp): Locator => page.getByText(text).first(),

  // AI Builder chat
  chatInput: page.getByRole('textbox').last(),

  // Data sources: Data Input node → sources entry → "Third Party Data" panel → "Add Data Sources" → Amazon S3
  sourcesEntry: page.getByText(/third party|data sources|add data/i).first(),
  thirdPartyData: page.getByText('Third Party Data').first(),
  addDataSourcesButton: page.getByRole('button', { name: /add data sources/i }),
  amazonS3Option: page.getByText(/amazon s3/i).first(),
  sourceCard: (name: string): Locator => page.getByText(name, { exact: true }).first(),
  connectedBadge: page.getByText('Connected', { exact: true }).first(),

  // S3 connection form
  bucketField: page.getByLabel(/bucket/i).first(),
  regionField: page.getByText(/region/i).first(),
  connectS3Button: page.getByRole('button', { name: /connect s3 source/i }),

  // Schedules
  addScheduleButton: page.getByRole('button', { name: /add schedule/i }),
  frequencySelect: page.getByText('Frequency').locator('..').getByRole('combobox'),
  frequencyOption: (name: string): Locator => page.getByRole('option', { name, exact: true }),
  createButton: page.getByRole('button', { name: 'Create', exact: true }),
  scheduleCards: page.getByText(/^Schedule for/),
  activeBadge: page.getByText('Active', { exact: true }),
  nextRun: page.getByText(/Next run:/),
});
