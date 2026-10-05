import { describe, test } from 'node:test';
import assert from 'node:assert/strict';
import { get, PROJECT, hasLogin, assertApiRefusal } from './client.mjs';

const ROLES = ['admin', 'editor', 'member', 'viewer', 'owner'];
const needsLogin = hasLogin ? {} : { skip: 'Set RHOMBUS_TOKEN in .env' };
const nodesPath = `/api/dataset/analyzer/v2/projects/${PROJECT}/nodes`;
const nodeOf = (body, type) => body.map(n => n.metadata.node).find(n => n.data.transformationType === type);

describe('Project and pipeline: positive', () => {
  test('project context returns this project and your roles', needsLogin, async (t) => {
    const r = await get(`/api/dataset/projects/${PROJECT}/context`);
    assert.equal(r.status, 200, r.text.slice(0, 200));
    assert.equal(r.body.id, Number(PROJECT));
    assert.equal(typeof r.body.organization_id, 'number');
    assert.ok(ROLES.includes(r.body.org_role), `unexpected org_role ${r.body.org_role}`);
    assert.ok(ROLES.includes(r.body.project_role), `unexpected project_role ${r.body.project_role}`);
    assert.ok(r.ms < 5000, `slow response: ${r.ms} ms`);
    t.diagnostic(`200 in ${r.ms} ms; project ${r.body.id}, role ${r.body.project_role}`);
  });

  test('pipeline is Data Input → AI cleaning step → output, connected in order', needsLogin, async (t) => {
    const r = await get(nodesPath);
    assert.equal(r.status, 200, r.text.slice(0, 200));
    assert.ok(Array.isArray(r.body), 'expected a list of nodes');
    const types = r.body.map(n => n.metadata.node.data.transformationType);
    const input = nodeOf(r.body, 'input'), llm = nodeOf(r.body, 'llm'), output = nodeOf(r.body, 'output');
    assert.ok(input && llm && output, `expected input, llm and output nodes; found: ${types.join(', ')}`);

    const lp = llm.data.transformationParams ?? {};
    assert.equal(lp.mode, 'code', `llm params: ${Object.keys(lp).join(', ')}`);
    assert.match(lp.code ?? '', /output_df\s*=/, 'generated code does not produce output_df');

    const edges = r.body.flatMap(n => n.metadata.edges ?? []);
    const pairs = edges.map(e => `${e.source}→${e.target}`);
    assert.ok(edges.some(e => e.source === input.id && e.target === llm.id), `no input→llm edge; edges: ${pairs.join(', ')}`);
    assert.ok(edges.some(e => e.source === llm.id && e.target === output.id), `no llm→output edge; edges: ${pairs.join(', ')}`);
    t.diagnostic(`nodes: ${types.join(' → ')}; AI step "${llm.data.description}"`);
  });

  test('last run kept the 8 cleaned columns', needsLogin, async (t) => {
    const r = await get(nodesPath);
    const llm = nodeOf(r.body, 'llm');
    assert.deepEqual(llm.data.lastRunColumns,
      ['order_id', 'customer_name', 'email', 'order_date', 'amount_usd', 'quantity', 'country', 'status']);
    t.diagnostic(`columns: ${llm.data.lastRunColumns.join(', ')}`);
  });
});

describe('Project and pipeline: negative (security)', () => {
  test('project context without a login is refused, nothing leaked', async (t) => {
    const r = await get(`/api/dataset/projects/${PROJECT}/context`, { auth: 'none' });
    assertApiRefusal(assert, r, [401, 403]);
    assert.ok(!/organization_id|project_role/.test(r.text), 'response contains project data');
    t.diagnostic(`refused with ${r.status}`);
  });

  test('project context with an invalid token is refused, nothing leaked', async (t) => {
    const r = await get(`/api/dataset/projects/${PROJECT}/context`, { auth: 'invalid' });
    assertApiRefusal(assert, r, [401, 403]);
    assert.ok(!/organization_id|project_role/.test(r.text), 'response contains project data');
    t.diagnostic(`refused with ${r.status}`);
  });

  test('pipeline without a login is refused, no code leaked', async (t) => {
    const r = await get(nodesPath, { auth: 'none' });
    assertApiRefusal(assert, r, [401, 403]);
    assert.ok(!/transformationParams|input_df_1/.test(r.text), 'response contains pipeline code');
    t.diagnostic(`refused with ${r.status}`);
  });

  test("a project you don't belong to is refused", needsLogin, async (t) => {
    // One request, expecting a refusal. If this ever returns data, stop and report it privately.
    const other = process.env.OTHER_PROJECT_ID ?? '1';
    const r = await get(`/api/dataset/projects/${other}/context`);
    assertApiRefusal(assert, r, [403, 404]);
    assert.ok(!/project_role/.test(r.text), "response contains another project's data");
    t.diagnostic(`project ${other}: refused with ${r.status}`);
  });
});

// Known issues: these tests confirm each bug is STILL PRESENT, so they pass while it exists.
// If Rhombus fixes it, the test fails with a message saying so: update the finding and the test.
describe('Project and pipeline: known issues', () => {
  test('F10: amount_usd and quantity stored as numbers, though the code makes them text', needsLogin, async (t) => {
    const r = await get(nodesPath);
    const llm = nodeOf(r.body, 'llm');
    const types = Object.fromEntries(llm.data.lastRunColumns.map((c, i) => [c, llm.data.lastRunDtypes[i]]));
    assert.match(llm.data.transformationParams.code, /astype\(str\)/, 'code no longer converts to text');
    assert.ok(types.amount_usd !== 'object' || types.quantity !== 'object',
      'F10 appears FIXED: both columns are now stored as text. Update findings-log.md and this test');
    t.diagnostic(`code: .astype(str); stored as amount_usd=${types.amount_usd}, quantity=${types.quantity}`);
  });

  test('F30: output node has lost its GCS destination settings', needsLogin, async (t) => {
    const r = await get(nodesPath);
    const op = nodeOf(r.body, 'output').data.transformationParams ?? {};
    assert.ok(!op.format_type || !op.destination_id,
      `F30 appears FIXED: destination settings are back (${JSON.stringify(op)}). Update findings-log.md and this test`);
    t.diagnostic(`output settings: ${JSON.stringify(op)}`);
  });
});
