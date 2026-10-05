// Minimal API client: Node's built-in fetch, no dependencies.
export const API = process.env.RHOMBUS_API ?? 'https://api.rhombusai.com';
export const PROJECT = process.env.RHOMBUS_PROJECT_ID ?? '5248';

const token = (process.env.RHOMBUS_TOKEN ?? '').replace(/^Bearer\s+/i, '').trim();
const cookie = (process.env.RHOMBUS_COOKIE ?? '').trim();
export const hasLogin = Boolean(token || cookie);

/** Headers for a request. auth: 'valid' (your login), 'none', or 'invalid' (a made-up token). */
function headers(auth) {
  const h = { Accept: 'application/json' };
  if (auth === 'valid') {
    if (token) h.Authorization = `Bearer ${token}`;
    if (cookie) h.Cookie = cookie;
  } else if (auth === 'invalid') {
    h.Authorization = 'Bearer invalid.token.value';
  }
  return h;
}

/** GET a path; returns { status, body, text, ms }. Never throws on HTTP errors. */
export async function get(path, { auth = 'valid' } = {}) {
  const started = performance.now();
  const res = await fetch(`${API}${path}`, { headers: headers(auth) });
  const text = await res.text();
  let body = null;
  try { body = JSON.parse(text); } catch { /* not JSON */ }
  return { status: res.status, body, text, ms: Math.round(performance.now() - started) };
}

/**
 * A refusal must come from the Rhombus API itself (a JSON body), not from a proxy or network
 * filter that also answers 403. Checking the status code alone would pass for the wrong reason.
 */
export function assertApiRefusal(assert, r, allowed) {
  assert.ok(allowed.includes(r.status), `expected ${allowed.join('/')}, got ${r.status}: ${r.text.slice(0, 120)}`);
  assert.ok(r.body !== null && typeof r.body === 'object',
    `refusal is not a JSON API response (proxy or network error?): ${r.text.slice(0, 120)}`);
}
