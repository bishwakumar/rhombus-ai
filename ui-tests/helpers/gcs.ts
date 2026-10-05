import { execFileSync } from 'node:child_process';

/** Lists the CSV objects in a bucket using the gcloud CLI (already logged in on this machine). */
export function listCsv(bucket: string): Set<string> {
  try {
    const out = execFileSync('gcloud', ['storage', 'ls', `gs://${bucket}/*.csv`], { encoding: 'utf8' });
    return new Set(out.split('\n').map((s: string) => s.trim()).filter(Boolean));
  } catch {
    return new Set();   // empty bucket
  }
}

/** Outputs that appeared since a snapshot. */
export function newSince(bucket: string, before: Set<string>): string[] {
  return [...listCsv(bucket)].filter(u => !before.has(u));
}

/** First line (header) of a CSV object. */
export function header(url: string): string[] {
  const out = execFileSync('gcloud', ['storage', 'cat', '-r', '0-511', url], { encoding: 'utf8' });
  return out.split('\n')[0].trim().split(',');
}
