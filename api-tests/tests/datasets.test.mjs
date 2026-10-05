import { describe, test } from 'node:test';
import assert from 'node:assert/strict';
import { get, PROJECT, hasLogin, assertApiRefusal } from './client.mjs';

const needsLogin = hasLogin ? {} : { skip: 'Set RHOMBUS_TOKEN in .env' };
const base = `/api/dataset/analyzer/v2/projects/${PROJECT}`;

async function datasets() {
  const r = await get(`${base}/datasets`);
  assert.equal(r.status, 200, r.text.slice(0, 200));
  assert.ok(Array.isArray(r.body) && r.body.length > 0, 'expected at least one dataset');
  return r.body;
}

describe('Datasets and chat: positive', () => {
  test('every dataset belongs to this project and has an id and title', needsLogin, async (t) => {
    const ds = await datasets();
    for (const d of ds) {
      assert.equal(d.project_id, Number(PROJECT));
      assert.equal(typeof d.id, 'number');
      assert.ok(d.title, `dataset ${d.id} has no title`);
    }
    t.diagnostic(`${ds.length} dataset(s): ${ds.map(d => d.title).join(', ')}`);
  });

  test('no credential fields carry values', needsLogin, async (t) => {
    const ds = await datasets();
    for (const d of ds) {
      assert.ok(!d.client_secret, `dataset ${d.id} exposes a client_secret`);
      assert.ok(!d.client_id, `dataset ${d.id} exposes a client_id`);
    }
    t.diagnostic('client_id and client_secret present but empty');
  });

  test('dataset preview respects the limit and describes every column', needsLogin, async (t) => {
    const [d] = await datasets();
    const r = await get(`${base}/datasets/${d.id}/preview?offset=0&limit=5`);
    assert.equal(r.status, 200, r.text.slice(0, 200));
    const df = r.body.output.df;
    assert.ok(df.data.length <= 5, `asked for 5 rows, got ${df.data.length}`);
    assert.ok(Number.isInteger(df.num_rows) && df.num_rows >= df.data.length);
    for (const col of df.columns) {
      assert.ok(col in df.dtypes, `no dtype for column ${col}`);
      assert.ok(col in df.semantic_types, `no semantic type for column ${col}`);
    }
    for (const row of df.data) assert.deepEqual(Object.keys(row).sort(), [...df.columns].sort());
    t.diagnostic(`${df.data.length} of ${df.num_rows} rows, ${df.columns.length} columns`);
  });

  test('chat artifacts live inside rhombus_output and have sizes', needsLogin, async (t) => {
    const r = await get(`${base}/chat/artifacts`);
    assert.equal(r.status, 200, r.text.slice(0, 200));
    assert.ok(Array.isArray(r.body.artifacts));
    for (const a of r.body.artifacts) {
      assert.match(a.path, /^rhombus_output\//);
      assert.equal(typeof a.size_bytes, 'number');
      assert.equal(r.body.artifact_paths[a.key], a.path, `artifact_paths disagrees for ${a.key}`);
    }
    t.diagnostic(`${r.body.artifacts.length} artifact(s)`);
  });
});

describe('Datasets and chat: negative (security)', () => {
  test('dataset list without a login is refused, no storage locations leaked', async (t) => {
    const r = await get(`${base}/datasets`, { auth: 'none' });
    assertApiRefusal(assert, r, [401, 403]);
    assert.ok(!/data_array|\.parquet/.test(r.text), 'response contains dataset storage details');
    t.diagnostic(`refused with ${r.status}`);
  });

  test('dataset preview without a login is refused, no rows leaked', needsLogin, async (t) => {
    const [d] = await datasets();
    const r = await get(`${base}/datasets/${d.id}/preview?offset=0&limit=5`, { auth: 'none' });
    assertApiRefusal(assert, r, [401, 403]);
    assert.ok(!/order_id|"data"\s*:/.test(r.text), 'response contains dataset rows');
    t.diagnostic(`refused with ${r.status}`);
  });
});

describe('Datasets and chat: known issues (confirmed still present)', () => {
  test('F15: datasets are named "placeholder_file" instead of their real file name', needsLogin, async (t) => {
    const ds = await datasets();
    const placeholders = ds.filter(d => d.file === 'placeholder_file');
    assert.ok(placeholders.length > 0,
      'F15 appears FIXED: no dataset is named placeholder_file any more. Update findings-log.md and this test');
    t.diagnostic(`${placeholders.length} of ${ds.length} dataset(s) named placeholder_file`);
  });
});
