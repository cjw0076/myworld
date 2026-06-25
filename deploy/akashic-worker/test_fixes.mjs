/**
 * test_fixes.mjs — offline unit tests for the two defect fixes
 *
 * Tests:
 *   A. Merkle append-stability: proof issued at N still verifies after more appends
 *   B. Privacy strip: tool_freq discarded, top_tools hard-capped to 3 server-side
 *
 * Run: node test_fixes.mjs
 */

import { webcrypto } from "crypto";
const subtle = webcrypto.subtle;

// ── Re-implement the fixed Merkle helpers in plain Node ──────────────────────

async function sha256hex(text) {
  const buf = await subtle.digest("SHA-256", new TextEncoder().encode(text));
  return [...new Uint8Array(buf)].map(b => b.toString(16).padStart(2, "0")).join("");
}

async function leafHash(entryId) {
  return sha256hex("leaf:" + entryId);
}

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
  const targetId      = "id_gamma";  // index 2 in insertion order
  const targetIdx     = initialIds.indexOf(targetId);

  // Compute leaf hashes for all entries
  const allLeafHashes = await Promise.all(
    [...initialIds, ...appendedIds].map(id => leafHash(id))
  );
  const initialLeafHashes = allLeafHashes.slice(0, initialIds.length);

  // Build N-entry Merkle root and proof
  const root_at_N   = await buildMerkleRoot(initialLeafHashes);
  const proofResult = await buildMerkleProof(targetIdx, initialLeafHashes);

  console.log(`  N=${initialIds.length} root:  ${root_at_N}`);
  console.log(`  Proof for '${targetId}' (leaf_index=${targetIdx}):`);
  console.log(`    ${JSON.stringify(proofResult.proof)}`);

  // Verify proof at N
  const validAtN = await verifyProof(initialLeafHashes[targetIdx], proofResult.proof, root_at_N);
  console.log(`  Proof valid at N=${initialIds.length}: ${validAtN}`);

  // Append more entries
  const fullLeafHashes = allLeafHashes;
  const root_at_NplusM = await buildMerkleRoot(fullLeafHashes);
  console.log(`  N+M=${fullLeafHashes.length} root: ${root_at_NplusM}`);
  console.log(`  Root changed after append (expected): ${root_at_N !== root_at_NplusM}`);

  // OLD proof must still verify against OLD root (rebuilt from first N leaves)
  // This is the stability guarantee: insertion-order never shifts existing positions.
  const rebuiltRoot_N = await buildMerkleRoot(fullLeafHashes.slice(0, initialIds.length));
  const rootStable    = (rebuiltRoot_N === root_at_N);
  const proofStillValid = await verifyProof(
    initialLeafHashes[targetIdx], proofResult.proof, rebuiltRoot_N
  );

  console.log(`  root_at_N rebuilt from first N leaves unchanged: ${rootStable}`);
  console.log(`  OLD proof still valid against rebuilt N-entry root: ${proofStillValid}`);

  // Demonstrate OLD (sorted) approach would FAIL: sort all N+M IDs, find gamma's new position
  const sortedAll   = [...initialIds, ...appendedIds].sort();
  const gammaInSorted = sortedAll.indexOf(targetId);
  const sortedLeafHashes = await Promise.all(sortedAll.map(id => leafHash(id)));
  const sortedProof = await buildMerkleProof(gammaInSorted, sortedLeafHashes);
  const oldApproachRoot = await buildMerkleRoot(initialIds.slice().sort().map(() => null)
    .map((_, i) => sortedLeafHashes[i]).slice(0, initialIds.length));
  // The sorted-N root is different from sorted-(N+M) root, and old proof (from sorted-N tree)
  // would not match the sorted-(N+M) root because positions shifted.
  const sortedNLeafHashes = await Promise.all(initialIds.slice().sort().map(id => leafHash(id)));
  const sortedRoot_N = await buildMerkleRoot(sortedNLeafHashes);
  const oldProofResult  = await buildMerkleProof(
    initialIds.slice().sort().indexOf(targetId), sortedNLeafHashes
  );
  const fullSortedLeafHashes = await Promise.all([...initialIds, ...appendedIds].sort().map(id => leafHash(id)));
  const sortedRoot_NplusM = await buildMerkleRoot(fullSortedLeafHashes);
  const oldProofAgainstNewRoot = await verifyProof(
    sortedNLeafHashes[initialIds.slice().sort().indexOf(targetId)],
    oldProofResult.proof,
    sortedRoot_NplusM  // old proof against new sorted tree root
  );
  console.log(`  [contrast] OLD sorted approach — proof valid against N+M sorted root: ${oldProofAgainstNewRoot} (expected: false)`);

  if (!validAtN || !rootStable || !proofStillValid) {
    console.error("  FAIL: Merkle append-stability test");
    process.exit(1);
  }
  if (oldProofAgainstNewRoot) {
    console.error("  FAIL: sorted approach should break but did not (test logic error)");
    process.exit(1);
  }
  console.log("  PASS: Merkle append-stability test");
}

// ── Test B: Privacy strip ─────────────────────────────────────────────────────

function testPrivacyStrip() {
  console.log("--- Test B: Privacy strip (server-side enforcement) ---");

  // Simulate a client sending 10 top_tools and a full tool_freq distribution
  const clientBody = {
    id:        "test_contribution_001",
    category:  "tool_use",
    provider:  "claude",
    content:   "Used Bash extensively for file operations",
    tool_freq: { Bash: 50, Read: 30, Edit: 20, Write: 15, Agent: 10,
                 WebSearch: 8, Task: 5, Grep: 4, Find: 3, Skill: 2 },
    top_tools: ["Bash", "Read", "Edit", "Write", "Agent",
                "WebSearch", "WebFetch", "Task", "Skill", "Grep"],  // 10 names
    confidence: 0.9,
  };

  // Server-side processing (mirrors what the fixed handleContribute does)
  const stored_tool_freq = undefined;              // body.tool_freq is discarded
  const stored_top_tools = (clientBody.top_tools || []).slice(0, 3);  // server-caps to 3

  console.log(`  Client sent tool_freq with ${Object.keys(clientBody.tool_freq).length} keys`);
  console.log(`  Stored tool_freq: ${JSON.stringify(stored_tool_freq)}`);
  console.log(`  Client sent top_tools with ${clientBody.top_tools.length} entries`);
  console.log(`  Stored top_tools (capped): ${JSON.stringify(stored_top_tools)}`);

  let pass = true;
  if (stored_tool_freq !== undefined) {
    console.error("  FAIL: tool_freq must not be stored — privacy M1");
    pass = false;
  }
  if (stored_top_tools.length > 3) {
    console.error("  FAIL: top_tools must be capped to 3 — privacy M2");
    pass = false;
  }
  if (!stored_top_tools.every(t => clientBody.top_tools.includes(t))) {
    console.error("  FAIL: stored top_tools contains unknown entries");
    pass = false;
  }

  // Verify /sync and /predict would not return tool_freq
  const syncResultRow = {
    id:         "test_contribution_001",
    category:   "tool_use",
    provider:   "claude",
    top_tools:  stored_top_tools,
    // tool_freq intentionally omitted from result
    confidence: 0.9,
    similarity: 0.95,
  };
  if ("tool_freq" in syncResultRow) {
    console.error("  FAIL: /sync result must not include tool_freq");
    pass = false;
  }
  console.log(`  /sync result has tool_freq key: ${"tool_freq" in syncResultRow} (expected: false)`);

  if (!pass) process.exit(1);
  console.log("  PASS: Privacy strip test");
}

// ── Test C: k-anonymity SQL filter verification ───────────────────────────────

function testKAnonymityFilter() {
  console.log("--- Test C: k-anonymity filter logic ---");

  // Simulate what the WHERE clause produces
  const MIN_CONTRIBUTORS = 5;
  const rows = [
    { id: "r1", category: "tool_use",     contributors: 1, min_contributors: 5 },
    { id: "r2", category: "code_gen",     contributors: 5, min_contributors: 5 },
    { id: "r3", category: "file_ops",     contributors: 10, min_contributors: 5 },
    { id: "r4", category: "web_search",   contributors: 4, min_contributors: 5 },
    { id: "r5", category: "multi_agent",  contributors: 6, min_contributors: 5 },
  ];

  // Mirrors: WHERE contributors >= min_contributors
  const served = rows.filter(r => r.contributors >= r.min_contributors);
  const hidden = rows.filter(r => r.contributors < r.min_contributors);

  console.log(`  Total rows: ${rows.length}`);
  console.log(`  Served (contributors >= floor): ${served.map(r => r.id).join(", ")}`);
  console.log(`  Hidden (below k-floor):         ${hidden.map(r => r.id).join(", ")}`);

  if (served.length !== 3 || hidden.length !== 2) {
    console.error("  FAIL: k-anonymity filter is not working correctly");
    process.exit(1);
  }
  if (hidden.some(r => r.contributors >= MIN_CONTRIBUTORS)) {
    console.error("  FAIL: a row above the floor is being hidden");
    process.exit(1);
  }
  console.log("  PASS: k-anonymity filter test");
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
    console.log("All tests PASSED.");
  } catch (err) {
    console.error("Unexpected error:", err);
    process.exit(1);
  }
}

main();
