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
 *   - tool_freq (structural metadata) stored
 *   - No PII accepted; server rejects any content with email/key patterns
 *
 * Storage: Cloudflare D1 (SQLite) + Workers AI (@cf/baai/bge-base-en-v1.5)
 */

const EMBED_MODEL = "@cf/baai/bge-base-en-v1.5";
const EMBED_DIM   = 768;
const MAX_CONTENT = 500;   // chars — enough for behavioral summary
const CORS = {
  "Access-Control-Allow-Origin":  "*",
  "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type, X-AIOS-Version",
};

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

// ── DB schema (run once via /init) ────────────────────────────────────────────
const SCHEMA = `
CREATE TABLE IF NOT EXISTS memories (
  id          TEXT PRIMARY KEY,
  schema_ver  TEXT NOT NULL DEFAULT 'aios.agent_behavior.v1',
  category    TEXT,
  provider    TEXT,
  dataset     TEXT,
  top_tools   TEXT,          -- JSON array of top tool names
  tool_freq   TEXT,          -- JSON object {tool: count}
  embedding   TEXT NOT NULL, -- JSON array [float, ...]  (768-dim)
  confidence  REAL DEFAULT 0.75,
  contributed_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_category ON memories(category);
CREATE INDEX IF NOT EXISTS idx_provider ON memories(provider);
CREATE INDEX IF NOT EXISTS idx_contributed ON memories(contributed_at);
CREATE TABLE IF NOT EXISTS checkpoints (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  root_hash    TEXT NOT NULL,
  entry_count  INTEGER NOT NULL,
  submitted_by TEXT,
  created_at   TEXT NOT NULL
);
`;

// ── Merkle tree (pure JS, no deps) ───────────────────────────────────────────

async function sha256hex(text) {
  const buf = await crypto.subtle.digest("SHA-256",
    new TextEncoder().encode(text));
  return [...new Uint8Array(buf)].map(b => b.toString(16).padStart(2, "0")).join("");
}

async function buildMerkleRoot(ids) {
  // ids → sorted leaves → pairwise hash until root
  if (!ids || ids.length === 0) return null;
  let layer = await Promise.all(ids.slice().sort().map(id => sha256hex(id)));
  while (layer.length > 1) {
    if (layer.length % 2 === 1) layer.push(layer[layer.length - 1]);
    const next = [];
    for (let i = 0; i < layer.length; i += 2)
      next.push(await sha256hex(layer[i] + layer[i + 1]));
    layer = next;
  }
  return layer[0];
}

async function buildMerkleProof(targetId, ids) {
  const sorted = ids.slice().sort();
  let idx = sorted.indexOf(targetId);
  if (idx === -1) return null;
  let layer = await Promise.all(sorted.map(id => sha256hex(id)));
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
  return { root: layer[0], proof, leaf_index: sorted.indexOf(targetId) };
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
  const toolFreq  = body.tool_freq || {};
  const topTools  = (body.top_tools || []).slice(0, 10);
  const confidence= Math.min(1, Math.max(0, Number(body.confidence) || 0.75));

  const VALID_OS  = new Set(["myworld","hivemind","memoryos","capabilityos","genesisos"]);
  const safeOS    = VALID_OS.has(osOrigin) ? osOrigin : "myworld";

  if (!content || !id) return json({ error: "content and id required" }, 400);
  if (hasSensitiveData(content)) return json({ error: "sensitive data detected — rejected" }, 422);

  // Dedup
  const existing = await env.DB.prepare("SELECT id FROM memories WHERE id = ?").bind(id).first();
  if (existing) return json({ status: "duplicate", id });

  // Embed
  const vector = await embed(env.AI, content);
  const now    = new Date().toISOString();

  await env.DB.prepare(`
    INSERT INTO memories (id, category, provider, dataset, os_origin, top_tools, tool_freq, embedding, confidence, contributed_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
  `).bind(
    id, category, provider, dataset, safeOS,
    JSON.stringify(topTools),
    JSON.stringify(toolFreq),
    JSON.stringify(vector),
    confidence,
    now,
  ).run();

  return json({ status: "ok", id, category, provider, os_origin: safeOS, embedded_dim: vector.length });
}

async function handleSync(req, env) {
  let body;
  try { body = await req.json(); }
  catch { return json({ error: "invalid JSON" }, 400); }

  const query   = String(body.query || body.context || "").slice(0, MAX_CONTENT);
  const topK    = Math.min(20, Math.max(1, Number(body.top_k) || 10));
  const category= body.category  || null;
  const osFilter= body.os_origin || null;

  if (!query) return json({ error: "query required" }, 400);

  const qVec = await embed(env.AI, query);

  // Load memories (D1 doesn't have native vector search yet — do it in JS)
  const conds = [], binds = [];
  if (category) { conds.push("category = ?");  binds.push(category); }
  if (osFilter) { conds.push("os_origin = ?"); binds.push(osFilter); }
  const where = conds.length ? " WHERE " + conds.join(" AND ") : "";
  let stmt = `SELECT id, category, provider, os_origin, top_tools, tool_freq, embedding, confidence FROM memories${where} LIMIT 2000`;

  const rows = await env.DB.prepare(stmt).bind(...binds).all();

  const scored = (rows.results || []).map(row => {
    const vec = JSON.parse(row.embedding);
    const sim = cosine(qVec, vec);
    return {
      id: row.id,
      category: row.category,
      provider: row.provider,
      top_tools: JSON.parse(row.top_tools || "[]"),
      tool_freq: JSON.parse(row.tool_freq || "{}"),
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

  const context    = String(body.context || "").slice(0, MAX_CONTENT);
  const candidates = Array.isArray(body.candidates) ? body.candidates.map(String) : null;
  const topK       = Math.min(10, Math.max(1, Number(body.top_k)    || 3));
  const nSim       = Math.min(100, Math.max(5, Number(body.n_sim)   || 30));

  if (!context) return json({ error: "context required" }, 400);

  const qVec = await embed(env.AI, context);

  // Sample memories (random sample for performance; Vectorize would replace this)
  const rows = await env.DB.prepare(
    "SELECT id, category, top_tools, tool_freq, confidence, embedding FROM memories ORDER BY RANDOM() LIMIT 300"
  ).all();

  // Score by similarity, keep top-nSim
  const scored = (rows.results || [])
    .map(r => ({ ...r, sim: cosine(qVec, JSON.parse(r.embedding || "[]")) }))
    .sort((a, b) => b.sim - a.sim)
    .slice(0, nSim);

  // Aggregate tool frequencies weighted by similarity
  const toolScores = {};
  scored.forEach(mem => {
    const w  = mem.sim;
    const tt = JSON.parse(mem.top_tools || "[]");
    const tf = JSON.parse(mem.tool_freq  || "{}");
    // top_tools: position-decayed weight
    tt.forEach((t, i) => { toolScores[t] = (toolScores[t] || 0) + w * Math.max(0.1, 1 - i * 0.12); });
    // tool_freq: count-scaled weight
    Object.entries(tf).forEach(([t, cnt]) => {
      toolScores[t] = (toolScores[t] || 0) + w * (Math.min(cnt, 20) / 20) * 0.5;
    });
  });

  // Normalize
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
    env.DB.prepare("SELECT contributed_at FROM memories ORDER BY contributed_at DESC LIMIT 1").first(),
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
  const rows = await env.DB.prepare("SELECT id, contributed_at FROM memories ORDER BY contributed_at ASC").all();
  const ids = (rows.results || []).map(r => r.id);
  const root = await buildMerkleRoot(ids);
  const latest = ids.length > 0 ? (rows.results[ids.length - 1].contributed_at) : null;
  return json({
    root_hash:   root,
    entry_count: ids.length,
    timestamp:   new Date().toISOString(),
    latest_entry: latest,
    schema: "aios.akashic_record.v1",
  });
}

async function handleProof(env, entryId) {
  const row = await env.DB.prepare(
    "SELECT id, category, provider, top_tools, confidence, contributed_at FROM memories WHERE id = ?"
  ).bind(entryId).first();
  if (!row) return json({ error: "entry not found", id: entryId }, 404);

  const allRows = await env.DB.prepare("SELECT id FROM memories").all();
  const ids = (allRows.results || []).map(r => r.id);
  const result = await buildMerkleProof(entryId, ids);
  if (!result) return json({ error: "proof construction failed" }, 500);

  return json({
    entry: {
      id: row.id,
      category: row.category,
      provider: row.provider,
      top_tools: JSON.parse(row.top_tools || "[]"),
      confidence: row.confidence,
      contributed_at: row.contributed_at,
    },
    merkle_root:  result.root,
    merkle_proof: result.proof,
    leaf_index:   result.leaf_index,
    total_entries: ids.length,
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

  const exists = await env.DB.prepare("SELECT id FROM memories WHERE id = ?").bind(id).first();
  if (!exists) return json({ verified: false, reason: "entry not found", id });

  const allRows = await env.DB.prepare("SELECT id FROM memories").all();
  const ids = (allRows.results || []).map(r => r.id);
  const result = await buildMerkleProof(id, ids);
  const actual_root = result?.root || null;

  return json({
    verified:     !!actual_root && (!claimedRoot || claimedRoot === actual_root),
    id,
    actual_root,
    claimed_root: claimedRoot,
    root_matches: !claimedRoot || claimedRoot === actual_root,
    total_entries: ids.length,
  });
}

async function handleCheckpoint(req, env) {
  let body = {};
  try { body = await req.json(); } catch {}
  const submittedBy = String(body.submitted_by || "").slice(0, 40);

  // Compute current Merkle root
  const rows = await env.DB.prepare("SELECT id FROM memories").all();
  const ids = (rows.results || []).map(r => r.id);
  if (ids.length === 0) return json({ error: "no entries yet" }, 400);
  const root = await buildMerkleRoot(ids);
  const now  = new Date().toISOString();

  await env.DB.prepare(
    "INSERT INTO checkpoints (root_hash, entry_count, submitted_by, created_at) VALUES (?, ?, ?, ?)"
  ).bind(root, ids.length, submittedBy || null, now).run();

  return json({ status: "ok", root_hash: root, entry_count: ids.length, created_at: now });
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

async function handleGraph(env, urlObj) {
  const params   = urlObj.searchParams;
  const limit    = Math.min(300, Math.max(20, parseInt(params.get("limit") || "150")));
  const minSim   = Math.max(0.5, Math.min(0.99, parseFloat(params.get("min_sim") || "0.80")));
  const category = params.get("category") || null;
  const stratify = params.get("stratify") !== "false"; // default true

  let rows;
  if (category) {
    // Single category — random sample
    rows = await env.DB.prepare(
      "SELECT id, category, provider, top_tools, confidence, embedding FROM memories WHERE category = ? ORDER BY RANDOM() LIMIT ?"
    ).bind(category, limit).all();
  } else if (stratify) {
    // Stratified: equal per category so no single category dominates the galaxy
    const cats = await env.DB.prepare(
      "SELECT category, COUNT(*) as n FROM memories GROUP BY category ORDER BY n DESC"
    ).all();
    const catList = (cats.results || []).map(r => r.category).filter(Boolean);
    const perCat  = Math.max(10, Math.floor(limit / Math.max(1, catList.length)));
    const allRows = [];
    for (const cat of catList) {
      const r = await env.DB.prepare(
        "SELECT id, category, provider, top_tools, confidence, embedding FROM memories WHERE category = ? ORDER BY RANDOM() LIMIT ?"
      ).bind(cat, perCat).all();
      allRows.push(...(r.results || []));
    }
    rows = { results: allRows };
  } else {
    rows = await env.DB.prepare(
      "SELECT id, category, provider, top_tools, confidence, embedding FROM memories ORDER BY RANDOM() LIMIT ?"
    ).bind(limit).all();
  }

  const raw  = rows.results || [];

  // Parse and precompute norms (faster pairwise cosine)
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

  // Pairwise cosine — collect all valid pairs, then prune to top-K per node
  const topK   = Math.min(20, Math.max(2, parseInt(params.get("top_k") || "10")));
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

  // Keep top-K strongest neighbors per node, deduplicate symmetric edges
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

  // Strip embeddings before returning
  const nodes = entries.map(({ vec, norm, ...rest }) => rest);

  return json({
    nodes,
    links,
    meta: { total_nodes: nodes.length, total_links: links.length, min_sim: minSim, top_k: topK },
  });
}

async function handleInit(env) {
  // Create tables — safe to call multiple times
  const stmts = SCHEMA.trim().split(";").filter(s => s.trim());
  for (const stmt of stmts) {
    if (stmt.trim()) await env.DB.prepare(stmt).run();
  }
  return json({ status: "schema initialized" });
}

// ── Main entry ────────────────────────────────────────────────────────────────

export default {
  async fetch(request, env) {
    const url    = new URL(request.url);
    const method = request.method.toUpperCase();

    if (method === "OPTIONS") {
      return new Response(null, { status: 204, headers: CORS });
    }

    // Routes
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
      return handleGraph(env, url);
    }

    // Fall through to static assets (index.html, galaxy.html, etc.)
    if (env.ASSETS) return env.ASSETS.fetch(request);

    return json({ error: "not found" }, 404);
  },
};
