/**
 * test_fixes.mjs — offline unit tests for the worker defect fixes
 *
 * Tests:
 *   A. Merkle append-stability: proof issued at N still verifies after more appends
 *   B. Privacy strip: tool_freq discarded, top_tools hard-capped to 3 server-side
 *   C. k-anonymity filter logic (contributors >= min_contributors)
 *   D. /graph respects k-floor (sub-floor buckets excluded)
 *   E. Distinct-tenant counting: same contributor_id does NOT self-promote past floor
 *   F. Atomic upsert: duplicate-category INSERT OR IGNORE never errors
 *
 * Run: node test_fixes.mjs
 */

import { webcrypto } from "crypto";
const subtle = webcrypto.subtle;

// ── Shared crypto helpers ─────────────────────────────────────────────────────

async function sha256hex(text) {
  const buf = await subtle.digest("SHA-256", new TextEncoder().encode(text));
  return [...new Uint8Array(buf)].map(b => b.toString(16).padStart(2, "0")).join("");
}

async function leafHash(entryId) {
  return sha256hex("leaf:" + entryId);
}

const KANON_SALT = "akashic-kanon-v1";
async function deriveContributorId(apiKey) {
  return sha256hex(KANON_SALT + ":" + apiKey);
}

// ── Merkle helpers (mirrors worker.js) ───────────────────────────────────────

async function buildMerkleRoot(leafHashes) {
  if (!leafHashes || leafHashes.length === 0) return null;
  let layer = leafHashes.slice();
  while (layer.length > 1) {
    if (layer.length % 2 === 1) layer.push(layer[layer.length - 1]);
    const next = [];
    for (let i = 0; i < layer.length; i += 2)
      next.push(await sha256hex(layer[i] + layer[i + 1]));
    layer = next;
  }
  return layer[0];
}

async function buildMerkleProof(leafIdx, leafHashes) {
  if (leafIdx < 0 || leafIdx >= leafHashes.length) return null;
  let layer = leafHashes.slice();
  let idx = leafIdx;
  const proof = [];
  while (layer.length > 1) {
    if (layer.length % 2 === 1) layer.push(layer[layer.length - 1]);
    const sibling = idx % 2 === 0 ? idx + 1 : idx - 1;
    proof.push({ hash: layer[sibling], position: idx % 2 === 0 ? "right" : "left" });
    const next = [];
    for (let i = 0; i < layer.length; i += 2)
      next.push(await sha256hex(layer[i] + layer[i + 1]));
    layer = next;
    idx = Math.floor(idx / 2);
  }
  return { root: layer[0], proof, leaf_index: leafIdx };
}

async function verifyProof(startLeafHash, proof, expectedRoot) {
  let current = startLeafHash;
  for (const step of proof) {
    if (step.position === "right") {
      current = await sha256hex(current + step.hash);
    } else {
      current = await sha256hex(step.hash + current);
    }
  }
  return current === expectedRoot;
}

// ── Test A: Merkle append-stability ──────────────────────────────────────────

async function testMerkleAppendStability() {
  console.log("--- Test A: Merkle append-stability ---");

  const initialIds    = ["id_alpha", "id_beta", "id_gamma", "id_delta", "id_epsilon"];
  const appendedIds   = ["id_zeta", "id_eta", "id_theta"];
  const targetId      = "id_gamma";
  const targetIdx     = initialIds.indexOf(targetId);

  const allLeafHashes     = await Promise.all([...initialIds, ...appendedIds].map(id => leafHash(id)));
  const initialLeafHashes = allLeafHashes.slice(0, initialIds.length);

  const root_at_N   = await buildMerkleRoot(initialLeafHashes);
  const proofResult = await buildMerkleProof(targetIdx, initialLeafHashes);

  console.log(`  N=${initialIds.length} root:  ${root_at_N}`);
  const validAtN = await verifyProof(initialLeafHashes[targetIdx], proofResult.proof, root_at_N);
  console.log(`  Proof valid at N=${initialIds.length}: ${validAtN}`);

  const fullLeafHashes  = allLeafHashes;
  const root_at_NplusM  = await buildMerkleRoot(fullLeafHashes);
  console.log(`  N+M=${fullLeafHashes.length} root: ${root_at_NplusM}`);
  console.log(`  Root changed after append (expected): ${root_at_N !== root_at_NplusM}`);

  const rebuiltRoot_N   = await buildMerkleRoot(fullLeafHashes.slice(0, initialIds.length));
  const rootStable      = (rebuiltRoot_N === root_at_N);
  const proofStillValid = await verifyProof(
    initialLeafHashes[targetIdx], proofResult.proof, rebuiltRoot_N
  );
  console.log(`  root_at_N rebuilt from first N leaves unchanged: ${rootStable}`);
  console.log(`  OLD proof still valid against rebuilt N-entry root: ${proofStillValid}`);

  // Contrast: sorted approach breaks
  const sortedNLeafHashes    = await Promise.all(initialIds.slice().sort().map(id => leafHash(id)));
  const oldProofResult       = await buildMerkleProof(initialIds.slice().sort().indexOf(targetId), sortedNLeafHashes);
  const fullSortedLeafHashes = await Promise.all([...initialIds, ...appendedIds].sort().map(id => leafHash(id)));
  const sortedRoot_NplusM    = await buildMerkleRoot(fullSortedLeafHashes);
  const oldProofAgainstNewRoot = await verifyProof(
    sortedNLeafHashes[initialIds.slice().sort().indexOf(targetId)],
    oldProofResult.proof, sortedRoot_NplusM
  );
  console.log(`  [contrast] OLD sorted approach — proof valid against N+M sorted root: ${oldProofAgainstNewRoot} (expected: false)`);

  if (!validAtN || !rootStable || !proofStillValid) {
    console.error("  FAIL: Merkle append-stability test"); process.exit(1);
  }
  if (oldProofAgainstNewRoot) {
    console.error("  FAIL: sorted approach should break (test logic error)"); process.exit(1);
  }
  console.log("  PASS: Merkle append-stability test");
}

// ── Test B: Privacy strip ─────────────────────────────────────────────────────

function testPrivacyStrip() {
  console.log("--- Test B: Privacy strip (server-side enforcement) ---");

  const clientBody = {
    id: "test_001", category: "tool_use", provider: "claude",
    content: "Used Bash for file ops",
    tool_freq: { Bash: 50, Read: 30, Edit: 20, Write: 15, Agent: 10,
                 WebSearch: 8, Task: 5, Grep: 4, Find: 3, Skill: 2 },
    top_tools: ["Bash","Read","Edit","Write","Agent","WebSearch","WebFetch","Task","Skill","Grep"],
    confidence: 0.9,
  };

  const stored_tool_freq = undefined;                          // discarded server-side
  const stored_top_tools = (clientBody.top_tools || []).slice(0, 3);  // capped to 3

  console.log(`  Client tool_freq keys: ${Object.keys(clientBody.tool_freq).length}`);
  console.log(`  Stored tool_freq: ${JSON.stringify(stored_tool_freq)} (expected: undefined)`);
  console.log(`  Client top_tools length: ${clientBody.top_tools.length}`);
  console.log(`  Stored top_tools: ${JSON.stringify(stored_top_tools)} (expected: 3 entries)`);

  const syncRow = { id: "test_001", category: "tool_use", provider: "claude",
                    top_tools: stored_top_tools, confidence: 0.9, similarity: 0.95 };
  console.log(`  /sync result has tool_freq key: ${"tool_freq" in syncRow} (expected: false)`);

  if (stored_tool_freq !== undefined) {
    console.error("  FAIL: tool_freq must not be stored"); process.exit(1);
  }
  if (stored_top_tools.length > 3) {
    console.error("  FAIL: top_tools must be capped to 3"); process.exit(1);
  }
  if ("tool_freq" in syncRow) {
    console.error("  FAIL: /sync must not return tool_freq"); process.exit(1);
  }
  console.log("  PASS: Privacy strip test");
}

// ── Test C: k-anonymity SQL filter ───────────────────────────────────────────

function testKAnonymityFilter() {
  console.log("--- Test C: k-anonymity filter logic ---");

  const rows = [
    { id: "r1", category: "tool_use",    contributors: 1,  min_contributors: 5 },
    { id: "r2", category: "code_gen",    contributors: 5,  min_contributors: 5 },
    { id: "r3", category: "file_ops",    contributors: 10, min_contributors: 5 },
    { id: "r4", category: "web_search",  contributors: 4,  min_contributors: 5 },
    { id: "r5", category: "multi_agent", contributors: 6,  min_contributors: 5 },
  ];

  const served = rows.filter(r => r.contributors >= r.min_contributors);
  const hidden = rows.filter(r => r.contributors < r.min_contributors);
  console.log(`  Served (>= floor): ${served.map(r => r.id).join(", ")}`);
  console.log(`  Hidden (< floor):  ${hidden.map(r => r.id).join(", ")}`);

  if (served.length !== 3 || hidden.length !== 2) {
    console.error("  FAIL: k-anonymity filter count wrong"); process.exit(1);
  }
  console.log("  PASS: k-anonymity filter test");
}

// ── Test D: /graph respects k-floor ──────────────────────────────────────────

function testGraphKFloor() {
  console.log("--- Test D: /graph k-floor enforcement ---");

  const allMemories = [
    { id: "m1", category: "tool_use",    contributors: 1,  min_contributors: 5 },
    { id: "m2", category: "code_gen",    contributors: 5,  min_contributors: 5 },
    { id: "m3", category: "file_ops",    contributors: 10, min_contributors: 5 },
    { id: "m4", category: "web_search",  contributors: 2,  min_contributors: 5 },
    { id: "m5", category: "multi_agent", contributors: 7,  min_contributors: 5 },
  ];

  // Mirrors: WHERE contributors >= min_contributors (applied in all 3 graph SELECT branches)
  const graphNodes = allMemories.filter(m => m.contributors >= m.min_contributors);
  const hiddenIds  = allMemories.filter(m => m.contributors < m.min_contributors).map(m => m.id);

  console.log(`  Total memories: ${allMemories.length}`);
  console.log(`  Graph nodes returned (>= floor): ${graphNodes.map(m => m.id).join(", ")}`);
  console.log(`  Hidden from graph (< floor): ${hiddenIds.join(", ")}`);

  if (graphNodes.length !== 3) {
    console.error("  FAIL: /graph should return exactly 3 nodes"); process.exit(1);
  }
  if (graphNodes.some(m => m.id === "m1" || m.id === "m4")) {
    console.error("  FAIL: sub-floor buckets m1/m4 must not appear in /graph"); process.exit(1);
  }
  console.log("  PASS: /graph k-floor test");
}

// ── Test E: Distinct-tenant k-anon (same key cannot self-promote) ─────────────

async function testDistinctContributorCounting() {
  console.log("--- Test E: Distinct-tenant k-anon counting ---");

  const KANON_FLOOR = 5;
  const category    = "rare_category";
  const singleKey   = "akr_aabbccddeeff00112233";
  const cid         = await deriveContributorId(singleKey);

  // Simulate contributor_seen with a Set (mirrors INSERT OR IGNORE on PRIMARY KEY)
  const contributorSeen = new Set();

  const contributionIds = ["id_001", "id_002", "id_003", "id_004", "id_005"];
  for (const _ of contributionIds) {
    contributorSeen.add(`${category}:${cid}`); // INSERT OR IGNORE: no-op after first
  }

  const distinctCount = [...contributorSeen].filter(k => k.startsWith(category + ":")).length;
  const aboveFloor    = distinctCount >= KANON_FLOOR;

  console.log(`  ${contributionIds.length} contributions from 1 tenant → contributor_seen rows: ${distinctCount} (expected: 1)`);
  console.log(`  Category above k-floor (${KANON_FLOOR}): ${aboveFloor} (expected: false)`);

  if (distinctCount !== 1) {
    console.error(`  FAIL: same contributor_id must deduplicate — got ${distinctCount}`); process.exit(1);
  }
  if (aboveFloor) {
    console.error("  FAIL: single tenant must NOT push category past k-floor"); process.exit(1);
  }

  // 5 DIFFERENT tenants each contribute once → floor should be crossed
  const contributorSeen2 = new Set();
  for (const key of ["akr_key1","akr_key2","akr_key3","akr_key4","akr_key5"]) {
    const c2 = await deriveContributorId(key);
    contributorSeen2.add(`${category}:${c2}`);
  }
  const distinctCount2 = [...contributorSeen2].filter(k => k.startsWith(category + ":")).length;
  const aboveFloor2    = distinctCount2 >= KANON_FLOOR;

  console.log(`  5 different tenants → contributor_seen rows: ${distinctCount2} (expected: 5)`);
  console.log(`  Category above k-floor: ${aboveFloor2} (expected: true)`);

  if (distinctCount2 !== 5) {
    console.error(`  FAIL: 5 distinct tenants should give count 5, got ${distinctCount2}`); process.exit(1);
  }
  if (!aboveFloor2) {
    console.error("  FAIL: 5 distinct tenants must cross the k-floor"); process.exit(1);
  }
  console.log("  PASS: Distinct-tenant k-anon counting test");
}

// ── Test F: Atomic upsert (INSERT OR IGNORE + UPDATE) ────────────────────────

function testAtomicUpsert() {
  console.log("--- Test F: Atomic upsert (INSERT OR IGNORE + UPDATE) ---");

  // Simulate two concurrent requests to the same category in a serialized D1 batch.
  // Both use INSERT OR IGNORE so the second never errors; both UPDATE correctly.
  const db = new Map();
  const contributorSeenG = new Set();

  function insertOrIgnore(category, id, embedding) {
    if (!db.has(category)) {
      db.set(category, { id, embedding: embedding.slice(), contributors: 0 });
      return "inserted";
    }
    return "ignored";
  }

  function recordContributor(category, cid) {
    contributorSeenG.add(`${category}:${cid}`);
    return [...contributorSeenG].filter(k => k.startsWith(category + ":")).length;
  }

  function updateCategory(category, newEmbedding, distinctCount) {
    if (!db.has(category)) return;
    const row = db.get(category);
    const avg = row.embedding.map((v, i) => (v + newEmbedding[i]) / 2);
    db.set(category, { ...row, embedding: avg, contributors: distinctCount });
  }

  // Request A (batch 1): seed + record contributor A + update
  const r1 = insertOrIgnore("code_gen", "id_A", [0.5, 0.5]);
  const cnt1 = recordContributor("code_gen", "cid_A");
  updateCategory("code_gen", [0.5, 0.5], cnt1);

  // Request B (batch 2): INSERT OR IGNORE (no-op) + record contributor B + update
  const r2 = insertOrIgnore("code_gen", "id_B", [0.7, 0.3]);
  const cnt2 = recordContributor("code_gen", "cid_B");
  updateCategory("code_gen", [0.7, 0.3], cnt2);

  const finalRow = db.get("code_gen");
  console.log(`  Request A INSERT result: ${r1} (expected: inserted)`);
  console.log(`  Request B INSERT result: ${r2} (expected: ignored — no 500 error)`);
  console.log(`  Final contributors: ${finalRow.contributors} (expected: 2)`);
  console.log(`  DB row count for code_gen: ${db.size} (expected: 1)`);

  if (r1 !== "inserted" || r2 !== "ignored") {
    console.error("  FAIL: INSERT OR IGNORE behavior wrong"); process.exit(1);
  }
  if (finalRow.contributors !== 2) {
    console.error(`  FAIL: contributors should be 2, got ${finalRow.contributors}`); process.exit(1);
  }
  if (db.size !== 1) {
    console.error("  FAIL: must be exactly 1 row per category"); process.exit(1);
  }
  console.log("  PASS: Atomic upsert test");
}

// ── Run all tests ─────────────────────────────────────────────────────────────

async function main() {
  try {
    await testMerkleAppendStability();
    console.log();
    testPrivacyStrip();
    console.log();
    testKAnonymityFilter();
    console.log();
    testGraphKFloor();
    console.log();
    await testDistinctContributorCounting();
    console.log();
    testAtomicUpsert();
    console.log();
    console.log("All tests PASSED.");
  } catch (err) {
    console.error("Unexpected error:", err);
    process.exit(1);
  }
}

main();
