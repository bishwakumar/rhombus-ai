import type { Reporter, FullConfig, Suite, TestCase, TestResult, FullResult, TestError } from '@playwright/test/reporter';

/**
 * Plain terminal reporter: one line per test, grouped by section, an "ℹ" line with what the
 * test found, the first line of any error, and a short summary.
 */
const C = { green: '\x1b[32m', red: '\x1b[31m', yellow: '\x1b[33m', dim: '\x1b[2m', bold: '\x1b[1m', reset: '\x1b[0m' };

export default class PlainReporter implements Reporter {
  private group = '';
  private counts = { passed: 0, failed: 0, skipped: 0 };
  private failures: string[] = [];

  private errors: string[] = [];

  /** Errors outside any test (e.g. a test file that can't be loaded). Always shown. */
  onError(error: TestError) {
    const text = (error.message ?? error.value ?? 'unknown error').replace(/\x1b\[[0-9;]*m/g, '');
    this.errors.push(text);
    console.log(`\n${C.red}${C.bold}Error before any test could run:${C.reset}\n${C.red}${text}${C.reset}`);
  }

  onBegin(_config: FullConfig, suite: Suite) {
    const n = suite.allTests().filter(t => t.parent.project()?.name === 'journey').length;
    console.log(`\n${C.bold}Rhombus AI: UI journey tests${C.reset} ${C.dim}(${n} tests)${C.reset}`);
  }

  onTestEnd(test: TestCase, result: TestResult) {
    if (test.parent.project()?.name !== 'journey') return;
    const group = test.parent.title;
    if (group && group !== this.group) {
      this.group = group;
      console.log(`\n${C.bold}${group}${C.reset}`);
    }
    const secs = `${C.dim}(${(result.duration / 1000).toFixed(1)}s)${C.reset}`;
    const notes = [...test.annotations, ...((result as any).annotations ?? [])]
      .filter((a: any) => a.type === 'info' && a.description);
    const seen = new Set<string>();

    if (result.status === 'passed') {
      this.counts.passed++;
      console.log(`  ${C.green}✔${C.reset} ${test.title} ${secs}`);
    } else if (result.status === 'skipped') {
      this.counts.skipped++;
      const why = test.annotations.find(a => a.type === 'skip')?.description ?? 'skipped';
      console.log(`  ${C.yellow}–${C.reset} ${test.title} ${C.dim}(skipped: ${why})${C.reset}`);
      return;
    } else {
      this.counts.failed++;
      const msg = (result.error?.message ?? result.status).split('\n')[0].replace(/\x1b\[[0-9;]*m/g, '');
      console.log(`  ${C.red}✘${C.reset} ${test.title} ${secs}`);
      console.log(`    ${C.red}${msg}${C.reset}`);
      this.failures.push(test.title);
    }
    for (const a of notes) {
      if (seen.has(a.description)) continue;
      seen.add(a.description);
      console.log(`    ${C.dim}ℹ ${a.description}${C.reset}`);
    }
  }

  onEnd(result: FullResult) {
    const { passed, failed, skipped } = this.counts;
    const colour = failed ? C.red : C.green;
    console.log(`\n${colour}${C.bold}${passed} passed${C.reset}, ${failed ? C.red : ''}${failed} failed${C.reset}, ` +
                `${skipped} skipped (opt-in)  ${C.dim}${result.status}${C.reset}`);
    if (failed) console.log(`${C.red}Failed: ${this.failures.join('; ')}${C.reset}`);
    if (passed + failed + skipped === 0) {
      console.log(`${C.red}No tests ran.${C.reset} ${this.errors.length ? 'See the error above.' :
        'Check you are in the ui-tests folder and that tests/ and helpers/ are complete.'}`);
    }
    console.log(`${C.dim}Full report with screenshots and video: npm run report${C.reset}\n`);
  }
}
