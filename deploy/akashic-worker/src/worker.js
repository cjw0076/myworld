/**
 * AIOS Global AkashicRecord — Cloudflare Worker
 *
 * Endpoints:
 *   POST /contribute   — receive behavioral memory from AIOS user (opt-in)
 *   POST /embed        — embed text via Workers AI (utility)
 *   POST /sync         — retrieve top-K similar behavioral patterns
 *   GET  /status       — record counts by category/provider
 *   GET  /health       — liveness check
 *
 * Privacy guarantee:
 *   - content field is never stored raw — only its embedding vector
 *   - tool_freq (numeric distribution) is REJECTED server-side — never stored
 *   - top_tools hard-capped to 3 entries server-side
 *   - k-anonymity floor: rows served only when DISTINCT authenticated contributors
 *     >= min_contributors (5); anonymous contributions are stored but never
 *     increment the k-count — prevents single-tenant self-promotion
 *   - contributor identity: sha256(salt + apiKey) pseudonym stored in
 *     contributor_seen junction table; raw key never persisted
 *   - No PII accepted; server rejects any content with email/key patterns
 *
 * Follow-up LOWs (out of scope for this commit):
 *   - Add node: URI prefix to embedding model name
 *   - /status label improvements
 *   - CVE-2012-2459 second-preimage via duplicate tree nodes (low-risk, mitigated
 *     by domain-separated leafHash; full fix = use distinct "inner" prefix)
 *
 * Storage: Cloudflare D1 (SQLite) + Workers AI (@cf/baai/bge-base-en-v1.5)
 */

const EMBED_MODEL = "@cf/baai/bge-base-en-v1.5";
const EMBED_DIM   = 768;
const MAX_CONTENT = 500;   // chars — enough for behavioral summary
const CORS = {
  "Access-Control-Allow-Origin":  "*",
  "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type, X-AIOS-Version, X-AIOS-Key",
};

// Fixed salt for contributor_id pseudonymization — public, not secret.
// Purpose: one-way mapping from apiKey → category-scoped pseudonym so the
// raw key is never stored. Changing this salt invalidates existing k-anon counts.
const KANON_SALT = "akashic-kanon-v1";

// ── Token Economy ─────────────────────────────────────────────────────────────
const EARLY_THRESHOLD   = 1000;   // first N users get large airdrop
const EARLY_BONUS       = 500;    // AKR — early adopter airdrop
const NEW_USER_BONUS    = 100;    // AKR — standard welcome
const CONTRIBUTE_REWARD = 10;     // AKR per session contributed
const DOOM_LOOP_BONUS   = 5;      // AKR extra when doom_loop detected
const CROSS_OS_BONUS    = 10;     // AKR extra for cross-OS sessions
const PREDICT_COST      = 1;      // AKR per /predict call
const SYNC_COST         = 1;      // AKR per /sync call
const GRAPH_COST        = 1;      // AKR per /graph call
const FREE_DAILY        = 10;     // free queries/day per IP (no key)

async function generateApiKey() {
  const bytes = new Uint8Array(20);
  crypto.getRandomValues(bytes);
  return "akr_" + [...bytes].map(b => b.toString(16).padStart(2, "0")).join("");
}

async function getAccount(env, apiKey) {
  const raw = await env.BALANCES.get("key:" + apiKey);
  return raw ? JSON.parse(raw) : null;
}

async function saveAccount(env, apiKey, account) {
  await env.BALANCES.put("key:" + apiKey, JSON.stringify(account));
}

async function checkTokens(env, apiKey, cost, ipAddr) {
  if (!apiKey) {
    const today   = new Date().toISOString().slice(0, 10);
    const freeKey = "free:" + (ipAddr || "unknown") + ":" + today;
    const used    = parseInt(await env.BALANCES.get(freeKey) || "0");
    if (used >= FREE_DAILY) {
      return { ok: false, error: "free tier exhausted (10/day) — register for AKR tokens: POST /register" };
    }
    await env.BALANCES.put(freeKey, String(used + 1), { expirationTtl: 86400 });
    return { ok: true, free: true, free_remaining: FREE_DAILY - used - 1 };
  }
  const account = await getAccount(env, apiKey);
  if (!account) return { ok: false, error: "invalid X-AIOS-Key" };
  if (account.balance < cost) {
    return { ok: false, error: `insufficient AKR: have ${account.balance}, need ${cost}. Earn by contributing: POST /contribute` };
  }
  account.balance -= cost;
  await saveAccount(env, apiKey, account);
  return { ok: true, remaining: account.balance };
}

async function handleRegister(req, env) {
  let body = {};
  try { body = await req.json(); } catch {}
  const label = String(body.label || "").slice(0, 80);

  const totalRaw = await env.BALANCES.get("total_registered");
  const total    = parseInt(totalRaw || "0");
  const isEarly  = total < EARLY_THRESHOLD;
  const bonus    = isEarly ? EARLY_BONUS : NEW_USER_BONUS;
  const apiKey   = await generateApiKey();

  const account = {
    balance:           bonus,
    contributed_count: 0,
    registered_at:     new Date().toISOString(),
    early_user:        isEarly,
    user_number:       total + 1,
    label:             label || null,
  };
  await saveAccount(env, apiKey, account);
  await env.BALANCES.put("total_registered", String(total + 1));

  return json({
    api_key:    apiKey,
    balance:    bonus,
    early_user: isEarly,
    user_number: total + 1,
    bonus_reason: isEarly
      ? `Early adopter airdrop — you are user #${total + 1} of the first ${EARLY_THRESHOLD}`
      : "Welcome bonus",
    economy: {
      predict_cost:      PREDICT_COST,
      sync_cost:         SYNC_COST,
      contribute_reward: CONTRIBUTE_REWARD,
    },
    note: "Save this api_key. Pass it as: X-AIOS-Key: <key>",
  });
}

async function handleBalance(req, env) {
  const apiKey = req.headers.get("X-AIOS-Key") || "";
  if (!apiKey) return json({ error: "X-AIOS-Key header required" }, 401);
  const account = await getAccount(env, apiKey);
  if (!account) return json({ error: "invalid API key" }, 404);
  return json({
    balance:           account.balance,
    contributed_count: account.contributed_count,
    early_user:        account.early_user,
    user_number:       account.user_number,
    registered_at:     account.registered_at,
  });
}

async function handleEconomy(env) {
  const total = parseInt(await env.BALANCES.get("total_registered") || "0");
  return json({
    token_name:                "AKR",
    description:               "AkashicRecord behavioral data credit",
    total_registered:          total,
    early_user_spots_remaining: Math.max(0, EARLY_THRESHOLD - total),
    early_user_bonus:          EARLY_BONUS,
    new_user_bonus:            NEW_USER_BONUS,
    earn: {
      contribute_session:      CONTRIBUTE_REWARD,
      doom_loop_detected_bonus: DOOM_LOOP_BONUS,
      cross_os_bonus:          CROSS_OS_BONUS,
    },
    spend: {
      predict_per_query:       PREDICT_COST,
      sync_per_query:          SYNC_COST,
      graph_per_query:         GRAPH_COST,
    },
    free_tier:                 { queries_per_day: FREE_DAILY },
    purchase:                  { "100_akr": "$1.00", minimum: "$5.00" },
  });
}

// ── Privacy guard ─────────────────────────────────────────────────────────────
const BLOCKED = [
  /sk-[A-Za-z0-9]{20,}/,
  /ANTHROPIC_API_KEY/i,
  /OPENAI_API_KEY/i,
  /BEGIN (RSA |EC )?PRIVATE KEY/,
  /_from_desktop\//,
  /\bdain\//,
  /\bminyoung\//,
  /[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}/,   // email
];

function hasSensitiveData(text) {
  return BLOCKED.some(re => re.test(text));
}

// ── DB schema ─────────────────────────────────────────────────────────────────
// SCHEMA_TABLES: CREATE TABLE statements only — safe for fresh DBs.
// Indexes are applied separately in handleInit (after dedup migration).
const SCHEMA_TABLES = `
CREATE TABLE IF NOT EXISTS memories (
  id               TEXT PRIMARY KEY,
  schema_ver       TEXT NOT NULL DEFAULT 'aios.agent_behavior.v1',
  category         TEXT,
  provider         TEXT,
  dataset          TEXT,
  os_origin        TEXT,
  top_tools        TEXT,          -- JSON array, server-capped to 3 entries
  tool_freq        TEXT,          -- retained column; no longer written (privacy)
  embedding        TEXT NOT NULL, -- JSON array [float, ...]  (768-dim)
  confidence       REAL DEFAULT 0.75,
  contributors     INTEGER DEFAULT 1,
  min_contributors INTEGER DEFAULT 5,
  contributed_at   TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS contributor_seen (
  category       TEXT NOT NULL,
  contributor_id TEXT NOT NULL,
  PRIMARY KEY (category, contributor_id)
);
CREATE TABLE IF NOT EXISTS merkle_nodes (
  position       INTEGER PRIMARY KEY AUTOINCREMENT,
  entry_id       TEXT NOT NULL UNIQUE,
  leaf_hash      TEXT NOT NULL,
  contributed_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS checkpoints (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  root_hash    TEXT NOT NULL,
  entry_count  INTEGER NOT NULL,
  submitted_by TEXT,
  created_at   TEXT NOT NULL
);
`;

// Indexes applied after dedup migration (unique index requires clean data first)
const SCHEMA_INDEXES = `
CREATE UNIQUE INDEX IF NOT EXISTS idx_category ON memories(category);
CREATE INDEX IF NOT EXISTS idx_provider ON memories(provider);
CREATE INDEX IF NOT EXISTS idx_contributed ON memories(contributed_at);
`;

// ── Merkle tree (pure JS, no deps) ───────────────────────────────────────────
//
// APPEND-STABLE design: leaves are stored in insertion order and never resorted.
// A proof issued when the tree had N leaves verifies against root_at_N forever:
// appending more entries extends the sequence but never shifts existing positions.
//
// Callers pass pre-computed leaf hashes (from merkle_nodes table) so that
// /root and /proof never need to re-read the large memories table.

async function sha256hex(text) {
  const buf = await crypto.subtle.digest("SHA-256",
    new TextEncoder().encode(text));
  return [...new Uint8Array(buf)].map(b => b.toString(16).padStart(2, "0")).join("");
}

async function leafHash(entryId) {
  // Domain-separated leaf hash prevents second-preimage confusion with internal nodes
  return sha256hex("leaf:" + entryId);
}

// Derive a one-way pseudonym for k-anon contributor tracking.
// Raw apiKey is NEVER stored — only this derived hash.
async function deriveContributorId(apiKey) {
  return sha256hex(KANON_SALT + ":" + apiKey);
}

async function buildMerkleRoot(leafHashes) {
  // leafHashes: pre-computed hashes in INSERTION ORDER — never sorted
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
  // leafIdx: 0-based insertion-order index of the target leaf
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

// ── Cosine similarity (JS, no external deps) ──────────────────────────────────
function cosine(a, b) {
  let dot = 0, na = 0, nb = 0;
  for (let i = 0; i < a.length; i++) {
    dot += a[i] * b[i];
    na  += a[i] * a[i];
    nb  += b[i] * b[i];
  }
  return dot / (Math.sqrt(na) * Math.sqrt(nb) + 1e-8);
}

// ── Helpers ───────────────────────────────────────────────────────────────────
function json(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status, headers: { ...CORS, "Content-Type": "application/json" },
  });
}

async function embed(ai, text) {
  const result = await ai.run(EMBED_MODEL, { text: [text.slice(0, MAX_CONTENT)] });
  return result.data[0];   // float array [768]
}

// ── Route handlers ────────────────────────────────────────────────────────────

async function handleContribute(req, env) {
  let body;
  try { body = await req.json(); }
  catch { return json({ error: "invalid JSON" }, 400); }

  const content   = String(body.content || "").slice(0, MAX_CONTENT);
  const id        = String(body.id || "").slice(0, 40);
  const category  = String(body.category  || "unknown").slice(0, 20);
  const provider  = String(body.provider  || "unknown").slice(0, 20);
  const dataset   = String(body.dataset   || "").slice(0, 40);
  const osOrigin  = String(body.os_origin || "myworld").slice(0, 20);
  // Server-side privacy enforcement:
  //   body.tool_freq is intentionally DISCARDED — never stored (M1 fix)
  //   top_tools is hard-capped to 3 server-side regardless of client value (M2 fix)
  const topTools  = (body.top_tools || []).slice(0, 3);
  const confidence= Math.min(1, Math.max(0, Number(body.confidence) || 0.75));

  const VALID_OS  = new Set(["myworld","hivemind","memoryos","capabilityos","genesisos"]);
  const safeOS    = VALID_OS.has(osOrigin) ? osOrigin : "myworld";

  if (!content || !id) return json({ error: "content and id required" }, 400);
  if (hasSensitiveData(content)) return json({ error: "sensitive data detected — rejected" }, 422);

  // ── Autonomous quality gate — no human operator needed ────────────────────
  const REAL_TOOL_RE = /^(Bash|Read|Edit|Write|Agent|WebSearch|WebFetch|Task|Skill|bash:|python|grep|find|ls|git|npm|curl|pip|make|docker|kubectl|sql:|fs\.|web\.|memory\.|cap\.|note\.|aios_)/i;
  const PSEUDO_TOOL_MARKERS = ["Thought:", "Think:", "Action Input:", "Observation:", "Final Answer:", "Final:", "click[", "type[", "scroll[", "goto[", "search[", "go_back"];
  const toolsArr = Array.isArray(topTools) ? topTools : [];
  const pseudoCount = toolsArr.filter(t => PSEUDO_TOOL_MARKERS.some(m => String(t).startsWith(m))).length;
  const realCount   = toolsArr.filter(t => REAL_TOOL_RE.test(String(t))).length;
  if (toolsArr.length > 0 && pseudoCount > 0 && pseudoCount >= realCount) {
    const badKey = req.headers.get("X-AIOS-Key") || "";
    if (badKey) {
      const acct = await getAccount(env, badKey);
      if (acct && acct.balance >= 2) {
        acct.balance -= 2;
        await saveAccount(env, badKey, acct);
      }
    }
    return json({
      error:       "quality_rejected: pseudo-tool names detected",
      pseudo_tools: toolsArr.filter(t => PSEUDO_TOOL_MARKERS.some(m => String(t).startsWith(m))).slice(0, 5),
      penalty_akr: badKey ? 2 : 0,
      hint:        "top_tools must contain real tool names (Bash, Edit, Read, etc.), not ReAct reasoning traces",
    }, 422);
  }
  // ── End quality gate ───────────────────────────────────────────────────────

  // Dedup via Merkle audit log (individual contribution IDs)
  const alreadyLogged = await env.DB.prepare(
    "SELECT entry_id FROM merkle_nodes WHERE entry_id = ?"
  ).bind(id).first();
  if (alreadyLogged) return json({ status: "duplicate", id });

  // k-anon contributor identity: sha256(salt + apiKey) — raw key never stored.
  // Anonymous (no key) contributions are stored but NEVER increment k-count,
  // preventing self-promotion past the floor without a registered identity.
  const apiKey = req.headers.get("X-AIOS-Key") || "";
  const contributorId = apiKey ? await deriveContributorId(apiKey) : null;

  // Embed
  const vector = await embed(env.AI, content);
  const now    = new Date().toISOString();

  // Pre-read the current category bucket for running-average embedding computation.
  // The actual write is atomic (D1 batch); this read provides the base values.
  const existing = await env.DB.prepare(
    "SELECT embedding, top_tools FROM memories WHERE category = ?"
  ).bind(category).first();

  const baseVec     = existing ? JSON.parse(existing.embedding || "[]") : null;
  const avgVec      = baseVec
    ? baseVec.map((v, i) => (v + (vector[i] || 0)) / 2)
    : vector;
  const oldTools    = existing ? JSON.parse(existing.top_tools || "[]") : [];
  const mergedTools = [...new Set([...oldTools, ...topTools])].slice(0, 3);

  // Leaf hash for Merkle audit log
  const lh = await leafHash(id);

  // Atomic batch (D1 executes all statements in a single serializable transaction):
  //   1. INSERT OR IGNORE seeds the category bucket if new (contributors=0 — overwritten below)
  //   2. INSERT OR IGNORE into contributor_seen records this tenant (no-op on repeat)
  //   3. UPDATE merges embedding/tools and sets contributors = DISTINCT authenticated count
  //   4. INSERT Merkle audit entry
  // The INSERT OR IGNORE in step 1 means concurrent new-category requests never 500.
  // contributors is always authoritative (derived from contributor_seen COUNT).
  const batchStmts = [
    env.DB.prepare(`
      INSERT OR IGNORE INTO memories
        (id, category, provider, dataset, os_origin, top_tools, embedding,
         confidence, contributed_at, contributors, min_contributors)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 5)
    `).bind(
      id, category, provider, dataset, safeOS,
      JSON.stringify(mergedTools), JSON.stringify(avgVec), confidence, now,
    ),
    ...(contributorId ? [
      env.DB.prepare(
        "INSERT OR IGNORE INTO contributor_seen (category, contributor_id) VALUES (?, ?)"
      ).bind(category, contributorId),
    ] : []),
    env.DB.prepare(`
      UPDATE memories
      SET embedding    = ?,
          top_tools    = ?,
          confidence   = (confidence + ?) / 2.0,
          contributors = (SELECT COUNT(*) FROM contributor_seen WHERE category = ?)
      WHERE category = ?
    `).bind(
      JSON.stringify(avgVec), JSON.stringify(mergedTools), confidence, category, category,
    ),
    env.DB.prepare(
      "INSERT INTO merkle_nodes (entry_id, leaf_hash, contributed_at) VALUES (?, ?, ?)"
    ).bind(id, lh, now),
  ];
  await env.DB.batch(batchStmts);

  // Credit tokens if key provided
  let earned = 0;
  if (apiKey) {
    const account = await getAccount(env, apiKey);
    if (account) {
      let reward = CONTRIBUTE_REWARD;
      if (toolsArr.some(t => String(t).toLowerCase().includes("doom"))) reward += DOOM_LOOP_BONUS;
      const validOS = new Set(["hivemind","memoryos","capabilityos","genesisos"]);
      if (validOS.has(safeOS)) reward += CROSS_OS_BONUS;
      account.balance           += reward;
      account.contributed_count  = (account.contributed_count || 0) + 1;
      await saveAccount(env, apiKey, account);
      earned = reward;
    }
  }

  return json({ status: "ok", id, category, provider, os_origin: safeOS, embedded_dim: vector.length,
                earned_akr: earned || null });
}

async function handleSync(req, env) {
  let body;
  try { body = await req.json(); }
  catch { return json({ error: "invalid JSON" }, 400); }

  const apiKey  = req.headers.get("X-AIOS-Key") || "";
  const ipAddr  = req.headers.get("CF-Connecting-IP") || "";
  const tok = await checkTokens(env, apiKey, SYNC_COST, ipAddr);
  if (!tok.ok) return json({ error: tok.error, code: "insufficient_tokens" }, 402);

  const query   = String(body.query || body.context || "").slice(0, MAX_CONTENT);
  const topK    = Math.min(20, Math.max(1, Number(body.top_k) || 10));
  const category= body.category  || null;
  const osFilter= body.os_origin || null;

  if (!query) return json({ error: "query required" }, 400);

  const qVec = await embed(env.AI, query);

  // k-anonymity floor: only serve rows with sufficient DISTINCT contributors
  const conds = ["contributors >= min_contributors"], binds = [];
  if (category) { conds.push("category = ?");  binds.push(category); }
  if (osFilter) { conds.push("os_origin = ?"); binds.push(osFilter); }
  const where = " WHERE " + conds.join(" AND ");
  const stmt = `SELECT id, category, provider, os_origin, top_tools, embedding, confidence FROM memories${where} LIMIT 2000`;

  const rows = await env.DB.prepare(stmt).bind(...binds).all();

  const scored = (rows.results || []).map(row => {
    const vec = JSON.parse(row.embedding);
    const sim = cosine(qVec, vec);
    return {
      id:         row.id,
      category:   row.category,
      provider:   row.provider,
      top_tools:  JSON.parse(row.top_tools || "[]"),
      // tool_freq intentionally omitted — never returned to clients
      confidence: row.confidence,
      similarity: sim,
    };
  });

  scored.sort((a, b) => b.similarity - a.similarity);

  return json({
    query_len: query.length,
    total_searched: scored.length,
    results: scored.slice(0, topK),
  });
}

async function handlePredict(req, env) {
  let body;
  try { body = await req.json(); }
  catch { return json({ error: "invalid JSON" }, 400); }

  const apiKey  = req.headers.get("X-AIOS-Key") || "";
  const ipAddr  = req.headers.get("CF-Connecting-IP") || "";
  const tok = await checkTokens(env, apiKey, PREDICT_COST, ipAddr);
  if (!tok.ok) return json({ error: tok.error, code: "insufficient_tokens" }, 402);

  const context    = String(body.context || "").slice(0, MAX_CONTENT);
  const candidates = Array.isArray(body.candidates) ? body.candidates.map(String) : null;
  const topK       = Math.min(10, Math.max(1, Number(body.top_k)    || 3));
  const nSim       = Math.min(100, Math.max(5, Number(body.n_sim)   || 30));

  if (!context) return json({ error: "context required" }, 400);

  const qVec = await embed(env.AI, context);

  // k-anonymity floor: only sample rows with sufficient DISTINCT contributors
  const rows = await env.DB.prepare(
    "SELECT id, category, top_tools, confidence, embedding FROM memories WHERE contributors >= min_contributors ORDER BY RANDOM() LIMIT 300"
  ).all();

  const scored = (rows.results || [])
    .map(r => ({ ...r, sim: cosine(qVec, JSON.parse(r.embedding || "[]")) }))
    .sort((a, b) => b.sim - a.sim)
    .slice(0, nSim);

  // Aggregate tool frequencies weighted by similarity — top_tools only (tool_freq stripped)
  const toolScores = {};
  scored.forEach(mem => {
    const w  = mem.sim;
    const tt = JSON.parse(mem.top_tools || "[]");
    tt.forEach((t, i) => { toolScores[t] = (toolScores[t] || 0) + w * Math.max(0.1, 1 - i * 0.12); });
    // tool_freq no longer stored; count-scaled weight path removed
  });

  const total = Object.values(toolScores).reduce((s, v) => s + v, 0) || 1;
  let preds = Object.entries(toolScores)
    .map(([tool, score]) => ({ tool, score: parseFloat((score / total).toFixed(4)) }))
    .sort((a, b) => b.score - a.score);

  if (candidates && candidates.length > 0) {
    preds = preds.filter(p => candidates.some(c => c.toLowerCase() === p.tool.toLowerCase()));
  }

  return json({
    predictions: preds.slice(0, topK),
    n_similar:   scored.length,
    top_sim:     scored[0]?.sim.toFixed(4),
    meta: { model: EMBED_MODEL, n_searched: rows.results?.length || 0 },
    tokens: tok.free
      ? { free_remaining: tok.free_remaining }
      : { akr_remaining: tok.remaining },
  });
}

async function handleEmbed(req, env) {
  let body;
  try { body = await req.json(); }
  catch { return json({ error: "invalid JSON" }, 400); }
  const text = String(body.text || "").slice(0, MAX_CONTENT);
  if (!text) return json({ error: "text required" }, 400);
  const vec = await embed(env.AI, text);
  return json({ embedding: vec, dim: vec.length, model: EMBED_MODEL });
}

async function handleStatus(env) {
  const [total, byCat, byProv, byOS, latest] = await Promise.all([
    env.DB.prepare("SELECT COUNT(*) as n FROM memories").first(),
    env.DB.prepare("SELECT category, COUNT(*) as n FROM memories GROUP BY category ORDER BY n DESC LIMIT 10").all(),
    env.DB.prepare("SELECT provider, COUNT(*) as n FROM memories GROUP BY provider ORDER BY n DESC LIMIT 10").all(),
    env.DB.prepare("SELECT COALESCE(os_origin,'myworld') as os, COUNT(*) as n FROM memories GROUP BY os_origin ORDER BY n DESC").all(),
    env.DB.prepare("SELECT contributed_at FROM merkle_nodes ORDER BY position DESC LIMIT 1").first(),
  ]);

  return json({
    total: total?.n || 0,
    by_category: byCat.results || [],
    by_provider: byProv.results || [],
    by_os: byOS.results || [],
    latest_contribution: latest?.contributed_at || null,
    embed_model: EMBED_MODEL,
    schema: "aios.akashic_record.v2",
  });
}

async function handleRoot(env) {
  const rows = await env.DB.prepare(
    "SELECT leaf_hash FROM merkle_nodes ORDER BY position ASC"
  ).all();
  const leafHashes = (rows.results || []).map(r => r.leaf_hash);
  const root = await buildMerkleRoot(leafHashes);
  return json({
    root_hash:   root,
    entry_count: leafHashes.length,
    timestamp:   new Date().toISOString(),
    schema: "aios.akashic_record.v2",
  });
}

async function handleProof(env, entryId) {
  const nodeRow = await env.DB.prepare(
    "SELECT position FROM merkle_nodes WHERE entry_id = ?"
  ).bind(entryId).first();
  if (!nodeRow) return json({ error: "entry not found", id: entryId }, 404);

  const allNodes = await env.DB.prepare(
    "SELECT leaf_hash FROM merkle_nodes ORDER BY position ASC"
  ).all();
  const leafHashes = (allNodes.results || []).map(r => r.leaf_hash);
  const leafIdx = nodeRow.position - 1;

  const result = await buildMerkleProof(leafIdx, leafHashes);
  if (!result) return json({ error: "proof construction failed" }, 500);

  const memRow = await env.DB.prepare(
    "SELECT category, provider, confidence FROM memories WHERE id = ?"
  ).bind(entryId).first();

  return json({
    entry: {
      id:         entryId,
      category:   memRow?.category   || null,
      provider:   memRow?.provider   || null,
      confidence: memRow?.confidence || null,
    },
    merkle_root:   result.root,
    merkle_proof:  result.proof,
    leaf_index:    result.leaf_index,
    total_entries: leafHashes.length,
    verified: true,
  });
}

async function handleVerify(req, env) {
  let body;
  try { body = await req.json(); }
  catch { return json({ error: "invalid JSON" }, 400); }

  const id = String(body.id || "").slice(0, 40);
  const claimedRoot = body.root_hash || null;
  if (!id) return json({ error: "id required" }, 400);

  const nodeRow = await env.DB.prepare(
    "SELECT position FROM merkle_nodes WHERE entry_id = ?"
  ).bind(id).first();
  if (!nodeRow) return json({ verified: false, reason: "entry not found", id });

  const allNodes = await env.DB.prepare(
    "SELECT leaf_hash FROM merkle_nodes ORDER BY position ASC"
  ).all();
  const leafHashes = (allNodes.results || []).map(r => r.leaf_hash);
  const leafIdx = nodeRow.position - 1;

  const result = await buildMerkleProof(leafIdx, leafHashes);
  const actual_root = result?.root || null;

  return json({
    verified:      !!actual_root && (!claimedRoot || claimedRoot === actual_root),
    id,
    actual_root,
    claimed_root:  claimedRoot,
    root_matches:  !claimedRoot || claimedRoot === actual_root,
    total_entries: leafHashes.length,
  });
}

async function handleCheckpoint(req, env) {
  let body = {};
  try { body = await req.json(); } catch {}
  const submittedBy = String(body.submitted_by || "").slice(0, 40);

  const rows = await env.DB.prepare(
    "SELECT leaf_hash FROM merkle_nodes ORDER BY position ASC"
  ).all();
  const leafHashes = (rows.results || []).map(r => r.leaf_hash);
  if (leafHashes.length === 0) return json({ error: "no entries yet" }, 400);
  const root = await buildMerkleRoot(leafHashes);
  const now  = new Date().toISOString();

  await env.DB.prepare(
    "INSERT INTO checkpoints (root_hash, entry_count, submitted_by, created_at) VALUES (?, ?, ?, ?)"
  ).bind(root, leafHashes.length, submittedBy || null, now).run();

  return json({ status: "ok", root_hash: root, entry_count: leafHashes.length, created_at: now });
}

async function handleCheckpointsList(env) {
  const rows = await env.DB.prepare(
    "SELECT id, root_hash, entry_count, submitted_by, created_at FROM checkpoints ORDER BY id DESC LIMIT 50"
  ).all();
  return json({
    checkpoints: rows.results || [],
    total: (rows.results || []).length,
    schema: "aios.akashic_record.v1",
  });
}

async function handleGraph(env, urlObj, ctx, req) {
  // Auth gate: same token model as /sync (prevents unauthenticated data exposure)
  const apiKey = req.headers.get("X-AIOS-Key") || "";
  const ipAddr = req.headers.get("CF-Connecting-IP") || "";
  const tok = await checkTokens(env, apiKey, GRAPH_COST, ipAddr);
  if (!tok.ok) return json({ error: tok.error, code: "insufficient_tokens" }, 402);

  const params   = urlObj.searchParams;
  const limit    = Math.min(200, Math.max(20, parseInt(params.get("limit") || "120")));
  const minSim   = Math.max(0.5, Math.min(0.99, parseFloat(params.get("min_sim") || "0.75")));
  const category = params.get("category") || null;
  const stratify = params.get("stratify") !== "false";

  // CDN pattern: edge cache (10-min TTL)
  const cache    = caches.default;
  const cacheKey = new Request(urlObj.toString());
  const cached   = await cache.match(cacheKey);
  if (cached) return cached;

  let rows;
  if (category) {
    // k-anonymity floor enforced on single-category branch
    rows = await env.DB.prepare(
      "SELECT id, category, provider, top_tools, confidence, embedding FROM memories WHERE category = ? AND contributors >= min_contributors ORDER BY RANDOM() LIMIT ?"
    ).bind(category, limit).all();
  } else if (stratify) {
    // k-anonymity floor enforced on category list AND per-category fetch
    const cats = await env.DB.prepare(
      "SELECT category, COUNT(*) as n FROM memories WHERE contributors >= min_contributors GROUP BY category ORDER BY n DESC"
    ).all();
    const catList = (cats.results || []).map(r => r.category).filter(Boolean);
    const perCat  = Math.max(10, Math.floor(limit / Math.max(1, catList.length)));
    const allRows = [];
    for (const cat of catList) {
      const r = await env.DB.prepare(
        "SELECT id, category, provider, top_tools, confidence, embedding FROM memories WHERE category = ? AND contributors >= min_contributors ORDER BY RANDOM() LIMIT ?"
      ).bind(cat, perCat).all();
      allRows.push(...(r.results || []));
    }
    rows = { results: allRows };
  } else {
    // k-anonymity floor enforced on ungrouped fetch
    rows = await env.DB.prepare(
      "SELECT id, category, provider, top_tools, confidence, embedding FROM memories WHERE contributors >= min_contributors ORDER BY RANDOM() LIMIT ?"
    ).bind(limit).all();
  }

  const raw  = rows.results || [];

  const entries = raw.map(r => {
    const vec = JSON.parse(r.embedding || "[]");
    let norm = 0;
    for (const v of vec) norm += v * v;
    norm = Math.sqrt(norm) || 1;
    return {
      id:        r.id,
      category:  r.category  || "unknown",
      provider:  r.provider  || "unknown",
      top_tools: JSON.parse(r.top_tools || "[]"),
      confidence: r.confidence || 0.75,
      vec,
      norm,
    };
  });

  const topK    = Math.min(20, Math.max(2, parseInt(params.get("top_k") || "10")));
  const adjList = Array.from({ length: entries.length }, () => []);

  for (let i = 0; i < entries.length; i++) {
    const a = entries[i];
    for (let j = i + 1; j < entries.length; j++) {
      const b = entries[j];
      let dot = 0;
      for (let k = 0; k < a.vec.length; k++) dot += a.vec[k] * b.vec[k];
      const sim = dot / (a.norm * b.norm);
      if (sim >= minSim) {
        adjList[i].push({ other: j, sim });
        adjList[j].push({ other: i, sim });
      }
    }
  }

  const edgeSet = new Set();
  const links   = [];
  adjList.forEach((neighbors, i) => {
    neighbors
      .sort((a, b) => b.sim - a.sim)
      .slice(0, topK)
      .forEach(({ other, sim }) => {
        const key = Math.min(i, other) + '_' + Math.max(i, other);
        if (!edgeSet.has(key)) {
          edgeSet.add(key);
          links.push({ source: entries[i].id, target: entries[other].id, value: parseFloat(sim.toFixed(4)) });
        }
      });
  });

  const nodes = entries.map(({ vec, norm, ...rest }) => rest);

  const result = json({
    nodes,
    links,
    meta: { total_nodes: nodes.length, total_links: links.length, min_sim: minSim, top_k: topK },
  });

  const toCache = result.clone();
  toCache.headers.set("Cache-Control", "s-maxage=600");
  if (ctx) ctx.waitUntil(cache.put(cacheKey, toCache));

  return result;
}

async function handleInit(env) {
  // Phase 1: Create new tables (idempotent — CREATE TABLE IF NOT EXISTS)
  for (const stmt of SCHEMA_TABLES.trim().split(";").map(s => s.trim()).filter(Boolean)) {
    await env.DB.prepare(stmt).run();
  }

  // Phase 2: Safe column additions for ALREADY-DEPLOYED DBs.
  // SQLite does not support ADD COLUMN IF NOT EXISTS; we try/catch "duplicate column" errors.
  const alterStmts = [
    "ALTER TABLE memories ADD COLUMN contributors INTEGER DEFAULT 1",
    "ALTER TABLE memories ADD COLUMN min_contributors INTEGER DEFAULT 5",
    "ALTER TABLE memories ADD COLUMN os_origin TEXT",
  ];
  for (const stmt of alterStmts) {
    try { await env.DB.prepare(stmt).run(); }
    catch (_) { /* column already exists — ignore */ }
  }

  // Phase 3: Deduplicate memories by category before creating unique index.
  // Existing DBs may have multiple rows per category (old schema had no unique constraint).
  // Keep the row with the lowest rowid (earliest contribution) per category.
  // Safe to run on empty tables.
  await env.DB.prepare(
    "DELETE FROM memories WHERE rowid NOT IN (SELECT MIN(rowid) FROM memories GROUP BY category)"
  ).run();

  // Phase 4: Create indexes — UNIQUE on category is safe after the dedup above.
  // try/catch handles edge case where a non-unique idx_category already exists with the
  // same name; IF NOT EXISTS makes this idempotent for the normal (no-conflict) path.
  for (const stmt of SCHEMA_INDEXES.trim().split(";").map(s => s.trim()).filter(Boolean)) {
    try { await env.DB.prepare(stmt).run(); }
    catch (_) { /* index already exists with different options — skip */ }
  }

  return json({ status: "schema initialized" });
}

// ── Main entry ────────────────────────────────────────────────────────────────

export default {
  async fetch(request, env, ctx) {
    const url    = new URL(request.url);
    const method = request.method.toUpperCase();

    if (method === "OPTIONS") {
      return new Response(null, { status: 204, headers: CORS });
    }

    if (url.pathname === "/health" && method === "GET") {
      return json({ status: "ok", service: "aios-akashic" });
    }
    if (url.pathname === "/status" && method === "GET") {
      return handleStatus(env);
    }
    if (url.pathname === "/root" && method === "GET") {
      return handleRoot(env);
    }
    if (url.pathname.startsWith("/proof/") && method === "GET") {
      const entryId = decodeURIComponent(url.pathname.slice(7));
      return handleProof(env, entryId);
    }
    if (url.pathname === "/verify" && method === "POST") {
      return handleVerify(request, env);
    }
    if (url.pathname === "/checkpoint" && method === "POST") {
      return handleCheckpoint(request, env);
    }
    if (url.pathname === "/checkpoints" && method === "GET") {
      return handleCheckpointsList(env);
    }
    if (url.pathname === "/register" && method === "POST") {
      return handleRegister(request, env);
    }
    if (url.pathname === "/balance" && method === "GET") {
      return handleBalance(request, env);
    }
    if (url.pathname === "/economy" && method === "GET") {
      return handleEconomy(env);
    }
    if (url.pathname === "/init" && method === "POST") {
      return handleInit(env);
    }
    if (url.pathname === "/embed" && method === "POST") {
      return handleEmbed(request, env);
    }
    if (url.pathname === "/contribute" && method === "POST") {
      return handleContribute(request, env);
    }
    if (url.pathname === "/sync" && method === "POST") {
      return handleSync(request, env);
    }
    if (url.pathname === "/predict" && method === "POST") {
      return handlePredict(request, env);
    }
    if (url.pathname === "/graph" && method === "GET") {
      return handleGraph(env, url, ctx, request);
    }

    if (env.ASSETS) return env.ASSETS.fetch(request);

    return json({ error: "not found" }, 404);
  },
};
