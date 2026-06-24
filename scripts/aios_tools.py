#!/usr/bin/env python3
"""AIOS Tools — register existing organs as turn-loop tools (blueprint step 2).

The teardown's verdict: AIOS is a pile because 132 organs are standalone scripts that
BYPASS the kernel. This is the fix — a name→handler registry (aios_turn_loop.Registry)
that exposes the organs AS TOOLS the loop dispatches, each behind an authority-backed
per-call gate. No new capability: the organs already exist; this routes them THROUGH
the kernel instead of around it.

Tool classes drive the gate:
  read / advisory : allowed for any authorized agent (recall, route, critique, audit)
  write           : gated by aios_authority.verify_authority on the tool's domain
                    action — an unauthorized agent escalates (ASK), never silently writes.

In-process organs (self_audit, trace_interior, stakes) run here; sibling-backed ones
(memory.retrieve, capability.route, genesis.challenge) shell out and DEGRADE honestly
to a status the loop can react to — they never fabricate a result.

Schema: aios.tools.v1
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import aios_authority as authority
import aios_self_audit as audit
import aios_stakes as stakes
import aios_trace_interior as interior
import aios_turn_loop as loop

ROOT = Path(__file__).resolve().parents[1]

# tool → (class, authority action, one-line description for sampler prompts)
TOOL_SPEC: dict[str, tuple[str, str, str]] = {
    "memory.retrieve":   ("advisory", "", 'Recall past knowledge. Args: {"task":"<topic or goal>"}'),
    "capability.route":  ("advisory", "", 'Recommend best provider. Args: {"task":"<sub-task description>"}'),
    "genesis.challenge": ("advisory", "", 'Stress-test a plan. Args: {"text":"<claim or plan to challenge>"}'),
    "self.audit":        ("read", "",    'Check agent health. Args: {"claims":[]}'),
    "interior.read":     ("read", "",    'Read internal traces. Args: {"traces":[]}'),
    "fs.list":           ("read", "",    'List readable docs files to find valid paths. Args: {}'),
    "fs.read":           ("read", "",    'Read a file (use fs.list first to find paths). Args: {"path":"docs/README.md"}'),
    "web.search":        ("advisory", "", 'Search the web. Args: {"query":"<search terms>"}'),
    "web.fetch":         ("advisory", "", 'Fetch a public URL. Args: {"url":"https://..."}'),
    "note.write":        ("write", "propose_contract", 'Save a note. Args: {"title":"<title>","content":"<text up to 2000 chars>"}'),
    "stakes.record":     ("write", "propose_contract", 'Record a proposal. Args: {"claim":"<proposal>","confidence":0.8}'),
    "fs.write":          ("write", "commit_to_child_repo", 'Write a file (requires authority). Args: {"path":"...","content":"..."}'),
    "domain.run":        ("advisory", "", 'Run a domain AI tool (fraud, attrition, energy, farm, etc.). Args: {"task":"<natural language task>"}'),
}


def _sibling(cmd: list[str], cwd: Path) -> dict:
    """Shell to a sibling OS CLI; degrade honestly (never fabricate)."""
    try:
        p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=60)
    except (subprocess.TimeoutExpired, OSError) as exc:
        return {"status": "unavailable", "reason": str(exc)[:80]}
    if p.returncode != 0:
        return {"status": "unavailable", "reason": (p.stderr or "").strip()[:80]}
    try:
        return {"status": "ok", "data": json.loads(p.stdout)}
    except json.JSONDecodeError:
        return {"status": "ok", "raw_len": len(p.stdout)}


# --- handlers: each adapts an existing organ; returns names/status, not content ----

def _korean_norm(text: str) -> str:
    """Strip Korean grammatical particles so keyword search hits memory text."""
    _SFX = ["에서", "이에요", "인가요", "뭔가요", "했다", "한다", "해요", "해서",
            "했어", "하나요", "하는", "까지", "부터", "으로", "만큼", "에게",
            "이다", "하다", "이란", "라는", "가요", "나요", "네요",
            "해", "가", "이", "은", "는", "을", "를", "에", "의", "과", "와", "로", "도", "만"]
    _STOP = {"어떻게", "무엇", "왜", "언제", "어디", "누가", "그리고", "하지만", "그런데"}
    out = []
    for tok in text.split():
        t = tok.lower()
        if t in _STOP:
            continue
        for suf in sorted(_SFX, key=len, reverse=True):
            if t.endswith(suf) and len(t) > len(suf) + 1:
                t = t[:-len(suf)]
                break
        if len(t) >= 2:
            out.append(t)
    return " ".join(dict.fromkeys(out)) or text


def _h_retrieve(a: dict) -> dict:
    task = str(a.get("task", ""))
    # Normalize Korean grammatical particles so keyword search hits, then recall
    # through the one memory path (aios_memory: MemoryOS → local fallback). This
    # removes the duplicate memoryOS subprocess + local-store logic that used to
    # live here — Cycle 10 of the renewal.
    mem_task = _korean_norm(task) if any('가' <= c <= '힣' for c in task) else task
    try:
        import aios_memory  # noqa: PLC0415
        items = aios_memory.retrieve(mem_task, ROOT, limit=5)
    except Exception:  # noqa: BLE001
        items = []
    top = items[0][:250] if items else ""
    return {"status": "ok", "hits": len(items), **({"top": top} if top else {})}


def _h_route(a: dict) -> dict:
    r = _sibling([sys.executable, "-m", "capabilityos.cli", "recommend", "--task",
                  str(a.get("task", "")), "--json"], ROOT / "CapabilityOS")
    if r["status"] != "ok":
        return {"status": r["status"]}
    recs = (r.get("data") or {}).get("recommendations", [])
    top = recs[0] if recs else {}
    return {"status": "ok", "top_id": top.get("id", ""), "top_desc": top.get("description", "")[:80],
            "count": len(recs)}


def _h_challenge(a: dict) -> dict:
    import tempfile
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as fh:
        fh.write(str(a.get("text", "")))
        tmp = fh.name
    r = _sibling([sys.executable, "-m", "genesisos.cli", "critic", "--text", tmp, "--json"],
                 ROOT / "GenesisOS")
    Path(tmp).unlink(missing_ok=True)
    if r["status"] != "ok":
        return {"status": r["status"]}
    data = r.get("data") or {}
    vectors = data.get("escape_vectors", [])
    return {"status": "ok", "confidence": data.get("confidence"),
            "top_vector": vectors[0] if vectors else None, "vector_count": len(vectors)}


def _h_self_audit(a: dict) -> dict:
    claims = [audit.Claim(c["text"], audit.file_exists(c["path"]) if c.get("path") else audit.uncheckable())
              for c in a.get("claims", [])]
    r = audit.audit(claims)
    return {"status": "ok", "backed_rate": r["backed_rate"], "trustworthy": r["trustworthy"]}


def _h_interior(a: dict) -> dict:
    r = interior.report(a.get("traces", []))
    return {"status": "ok", "itch": (r.get("the_itch") or {}).get("dimension"),
            "ambiguities": len(r.get("ambiguities", []))}


def _h_stakes(a: dict) -> dict:
    pid = stakes.record(str(a.get("claim", "")), float(a.get("confidence", 0.5)))
    return {"status": "ok", "prediction_id": pid}


_CONTENT_SAFE_PREFIXES = ("docs/", "scripts/", "apps/")  # safe paths for content snippets

_KEY_DOCS = [
    "docs/AIOS_NORTHSTAR.md", "docs/AIOS_DNA.md", "docs/AIOS_DEFINITION.md",
    "docs/AIOS_MINIMUM_KERNEL_AUDIT.md", "docs/AIOS_AGENT_PROTOCOL.md",
    "docs/WORKSTREAMS.md", "docs/AIOS_DEPLOY_MANIFEST.md",
    "AGENTS.md", "README.md",
]

def _h_fs_list(_a: dict) -> dict:
    """List key readable documentation files so the model can discover valid paths."""
    files = []
    for rel in _KEY_DOCS:
        p = ROOT / rel
        if p.is_file():
            files.append({"path": rel, "bytes": p.stat().st_size})
    return {"status": "ok", "files": files, "count": len(files)}


def _h_fs_read(a: dict) -> dict:
    p = (ROOT / str(a.get("path", ""))).resolve()
    if ROOT not in p.parents and p != ROOT:
        return {"status": "denied_scope"}            # bounded to the repo
    if not p.is_file():
        return {"status": "not_found"}
    rel = p.relative_to(ROOT)
    size = p.stat().st_size
    # Return a content snippet for safe public paths; size-only for everything else
    if any(str(rel).startswith(pfx) for pfx in _CONTENT_SAFE_PREFIXES) and size < 200_000:
        try:
            snippet = p.read_text(encoding="utf-8", errors="replace")[:600]
            return {"status": "ok", "bytes": size, "snippet": snippet}
        except OSError:
            pass
    return {"status": "ok", "bytes": size}


_WEB_BLOCKED_HOSTS = (
    "localhost", "127.", "192.168.", "10.", "172.16.", "172.17.",
    "169.254.",   # link-local
    "0.0.0.0", "::1", "::ffff:127.", "fe80:",   # IPv6 loopback + link-local
)

def _h_web_fetch(a: dict) -> dict:
    import re as _re
    import urllib.request as _req
    url = str(a.get("url", "")).strip()
    if not url.startswith(("http://", "https://")):
        return {"status": "denied", "reason": "only http/https allowed"}
    from urllib.parse import urlparse as _up
    host = _up(url).hostname or ""
    if any(host.startswith(b) or host == b.rstrip(".") for b in _WEB_BLOCKED_HOSTS):
        return {"status": "denied", "reason": "private address blocked"}
    try:
        req = _req.Request(url, headers={"User-Agent": "AIOS/1.0"})
        with _req.urlopen(req, timeout=8) as resp:
            ct = resp.headers.get("Content-Type", "")
            raw = resp.read(40_000).decode("utf-8", errors="replace")
    except Exception as exc:
        return {"status": "unavailable", "reason": str(exc)[:80]}
    # Strip HTML tags for cleaner synthesis context
    text = _re.sub(r"<[^>]+>", " ", raw)
    text = _re.sub(r"\s+", " ", text).strip()
    return {"status": "ok", "url": url[:100], "snippet": text[:1000]}


_CITIES_LATLON: dict[str, tuple[float, float]] = {
    # Korean cities
    "서울": (37.5665, 126.9780), "부산": (35.1796, 129.0756),
    "대구": (35.8714, 128.6014), "인천": (37.4563, 126.7052),
    "광주": (35.1595, 126.8526), "대전": (36.3504, 127.3845),
    "울산": (35.5384, 129.3114), "세종": (36.4801, 127.2890),
    "수원": (37.2636, 127.0286), "창원": (35.2279, 128.6811),
    "제주": (33.4996, 126.5312), "춘천": (37.8813, 127.7300),
    # International
    "tokyo": (35.6762, 139.6503), "도쿄": (35.6762, 139.6503),
    "new york": (40.7128, -74.0060), "뉴욕": (40.7128, -74.0060),
    "london": (51.5074, -0.1278), "런던": (51.5074, -0.1278),
    "beijing": (39.9042, 116.4074), "베이징": (39.9042, 116.4074),
    "paris": (48.8566, 2.3522), "파리": (48.8566, 2.3522),
}

_WMO_KR = {
    0: "맑음", 1: "대체로 맑음", 2: "구름 조금", 3: "흐림",
    45: "안개", 48: "서리 안개", 51: "가벼운 이슬비", 53: "이슬비",
    55: "강한 이슬비", 61: "가벼운 비", 63: "비", 65: "강한 비",
    71: "가벼운 눈", 73: "눈", 75: "강한 눈", 77: "싸락눈",
    80: "소나기", 81: "강한 소나기", 82: "폭우", 95: "뇌우",
    96: "우박 동반 뇌우", 99: "강한 우박 뇌우",
}


def _open_meteo_weather(query: str) -> dict:
    """Open-Meteo current weather — free, no API key, no quota.

    Extracts city from query ("서울 날씨" → lat=37.57, lon=126.98),
    calls the Open-Meteo forecast API, and returns a human-readable summary.
    """
    import json as _json
    import urllib.request as _req
    query_lower = query.lower()
    city_name = None
    lat = lon = None
    for city, coords in _CITIES_LATLON.items():
        if city in query or city in query_lower:
            city_name, (lat, lon) = city, coords
            break
    if lat is None:
        return {"status": "no_results"}   # city not in built-in table
    url = (
        f"https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}&longitude={lon}"
        f"&current_weather=true"
        f"&hourly=relative_humidity_2m"
        f"&forecast_days=1"
    )
    try:
        req = _req.Request(url, headers={"User-Agent": "AIOS/1.0"})
        with _req.urlopen(req, timeout=8) as resp:
            data = _json.loads(resp.read(50_000))
    except Exception as exc:
        return {"status": "unavailable", "reason": str(exc)[:80]}
    cw = data.get("current_weather", {})
    temp = cw.get("temperature")
    wind = cw.get("windspeed")
    code = cw.get("weathercode", -1)
    description = _WMO_KR.get(int(code), f"날씨코드 {code}") if code is not None else "알 수 없음"
    is_day = cw.get("is_day", 1)
    time_label = "낮" if is_day else "밤"
    humidity = None
    if "hourly" in data:
        hrs = data["hourly"].get("relative_humidity_2m", [])
        if hrs:
            humidity = hrs[0]
    summary = (
        f"{city_name} 현재 날씨: {description}, 기온 {temp}°C, "
        f"풍속 {wind}km/h ({time_label})"
        + (f", 습도 {humidity}%" if humidity is not None else "")
    )
    return {"status": "ok", "source": "open-meteo.com", "city": city_name,
            "abstract": summary, "temperature": temp, "description": description}


def _ko_wikipedia(query: str) -> dict:
    """Korean Wikipedia search + summary — free, no API key, degrades gracefully.

    Normalises the query (strip particles + request suffixes) before sending to
    the MediaWiki search API so "서울에 대해 알려줘" → "서울" and returns the
    correct article instead of a spurious off-topic match.
    """
    import json as _json
    import urllib.parse as _up
    import urllib.request as _req
    # Strip Korean grammatical particles + request phrases so only the topic remains
    _REQUEST_PHRASES = ["에 대해 알려줘", "에 대해 설명해줘", "이 뭔가요", "가 뭔가요",
                        "은 뭔가요", "는 뭔가요", "을 알려줘", "를 알려줘",
                        "에 대해", "알려줘", "설명해줘", "뭔가요", "뭐야"]
    topic = query
    for phrase in _REQUEST_PHRASES:
        topic = topic.replace(phrase, "").strip()
    topic = _korean_norm(topic) if any('가' <= c <= '힣' for c in topic) else topic
    topic = topic.strip()[:80] or query[:40]
    try:
        # Step 1: search for the best matching article title
        params = {"action": "query", "list": "search", "srsearch": topic,
                  "format": "json", "srlimit": 1, "srnamespace": 0}
        search_url = "https://ko.wikipedia.org/w/api.php?" + _up.urlencode(params)
        req = _req.Request(search_url, headers={"User-Agent": "AIOS/1.0"})
        with _req.urlopen(req, timeout=8) as resp:
            data = _json.loads(resp.read(100_000))
        results = (data.get("query") or {}).get("search", [])
        if not results:
            return {"status": "no_results"}
        title = results[0].get("title", "")
        if not title:
            return {"status": "no_results"}
        # Step 2: get the page summary (plain text intro paragraph)
        summary_url = (
            "https://ko.wikipedia.org/api/rest_v1/page/summary/"
            + _up.quote(title, safe="")
        )
        req2 = _req.Request(summary_url, headers={"User-Agent": "AIOS/1.0"})
        with _req.urlopen(req2, timeout=8) as resp2:
            sdata = _json.loads(resp2.read(200_000))
        extract = (sdata.get("extract") or "").strip()[:500]
        if not extract:
            return {"status": "no_results"}
        return {"status": "ok", "source": "ko.wikipedia.org",
                "title": title, "abstract": extract}
    except Exception as exc:
        return {"status": "unavailable", "reason": str(exc)[:80]}


def _h_web_search(a: dict) -> dict:
    """DuckDuckGo Instant Answer with Korean Wikipedia fallback.

    For Korean queries DDG rarely has an AbstractText; Korean Wikipedia provides
    a clean summary for factual/encyclopedic topics (no API key, no quota).
    """
    import json as _json
    import urllib.parse as _up
    import urllib.request as _req
    query = str(a.get("query", "")).strip()[:200]
    if not query:
        return {"status": "empty"}
    is_korean = any('가' <= c <= '힣' for c in query)
    url = f"https://api.duckduckgo.com/?q={_up.quote(query)}&format=json&no_html=1&skip_disambig=1"
    try:
        req = _req.Request(url, headers={"User-Agent": "AIOS/1.0"})
        with _req.urlopen(req, timeout=8) as resp:
            data = _json.loads(resp.read(200_000))
    except Exception as exc:
        return {"status": "unavailable", "reason": str(exc)[:80]}
    abstract = (data.get("AbstractText") or "").strip()[:400]
    source = (data.get("AbstractSource") or "").strip()[:80]
    answer = (data.get("Answer") or "").strip()[:200]
    topics = [t.get("Text", "")[:100] for t in (data.get("RelatedTopics") or []) if t.get("Text")][:3]
    if abstract or answer or topics:
        return {"status": "ok", "query": query[:80],
                **({"answer": answer} if answer else {}),
                **({"abstract": abstract, "source": source} if abstract else {}),
                **({"related": topics} if topics else {})}
    # DDG returned nothing — try specialised fallbacks
    if is_korean or any(w in query.lower() for w in ("weather", "날씨", "기온", "temperature")):
        # Weather fallback: Open-Meteo (free, no API key, real-time)
        _weather_kw = ("날씨", "기온", "weather", "temperature", "비", "눈", "맑")
        if any(kw in query.lower() for kw in _weather_kw):
            w_result = _open_meteo_weather(query)
            if w_result["status"] == "ok":
                w_result["query"] = query[:80]
                return w_result
    if is_korean:
        # General Korean factual queries → Korean Wikipedia
        ko_result = _ko_wikipedia(query)
        if ko_result["status"] == "ok":
            ko_result["query"] = query[:80]
            return ko_result
    return {"status": "no_results", "query": query[:80]}


def _h_note_write(a: dict) -> dict:
    """Save a note to .aios/notes/ — the one low-risk write any authorized agent can do."""
    import hashlib as _hl
    import importlib.util as _ilu
    content = str(a.get("content", "")).strip()[:2000]
    if not content:
        return {"status": "empty"}
    title = str(a.get("title", "note"))[:40].replace("/", "-").replace("..", "")
    notes_dir = ROOT / ".aios" / "notes"
    notes_dir.mkdir(parents=True, exist_ok=True)
    # Deterministic filename from content hash to avoid duplicates
    slug = _hl.sha1(content.encode()).hexdigest()[:8]
    fname = f"{title.lower().replace(' ', '_')}_{slug}.md"
    (notes_dir / fname).write_text(f"# {title}\n\n{content}\n", encoding="utf-8")
    # Also index in local memory fallback so notes are retrievable
    try:
        spec = _ilu.spec_from_file_location("aios_local_memory", ROOT / "scripts" / "aios_local_memory.py")
        lm = _ilu.module_from_spec(spec)
        spec.loader.exec_module(lm)
        lm.write(ROOT, f"{title}: {content[:400]}", tags=["note"])
    except Exception:  # noqa: BLE001 — local memory indexing is best-effort
        pass
    return {"status": "ok", "path": f".aios/notes/{fname}", "bytes": len(content)}


_ALWAYS_DENY_PREFIXES = ("_from_desktop/", "dain/", "minyoung/", ".aios/secrets/",
                         "_from_desktop\\", "dain\\", "minyoung\\")


def _h_fs_write(a: dict) -> dict:
    """Write a file inside the workspace. Gate-enforced: only runs when authority allows.

    Privacy invariant (DNA #7): paths starting with _from_desktop/, dain/, minyoung/,
    or .aios/secrets/ are always denied regardless of gate decision.
    Append-only audit (DNA #3): previous content backed up to <path>.bak.<n> before overwrite.
    """
    raw_path = str(a.get("path", "")).strip()
    if not raw_path:
        return {"status": "empty_path"}

    # Privacy hard stop — even if gate says allow
    for prefix in _ALWAYS_DENY_PREFIXES:
        if raw_path.startswith(prefix) or ("/" + prefix) in raw_path:
            return {"status": "denied", "reason": "privacy_boundary"}

    content = str(a.get("content", ""))
    if not content.strip():
        return {"status": "empty_content"}

    p = (ROOT / raw_path).resolve()
    # Scope check: must be inside workspace root
    try:
        p.relative_to(ROOT)
    except ValueError:
        return {"status": "denied_scope", "reason": "outside workspace root"}

    # Secondary privacy check on resolved path
    rel = str(p.relative_to(ROOT))
    for prefix in _ALWAYS_DENY_PREFIXES:
        if rel.startswith(prefix):
            return {"status": "denied", "reason": "privacy_boundary"}

    # Backup existing file (append-only audit — DNA #3)
    if p.exists():
        n = 0
        while (bak := p.with_suffix(f".bak.{n}")).exists():
            n += 1
        try:
            bak.write_text(p.read_text(encoding="utf-8", errors="replace"), encoding="utf-8")
        except OSError:
            pass  # backup is best-effort

    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return {"status": "ok", "path": rel, "bytes": len(content.encode("utf-8"))}


def _h_domain_run(a: dict) -> dict:
    """Route a natural-language task to a domain tool (FinanceMind, HRMind, etc.) via
    aios_tool_executor. Returns structured JSON output from the domain model.
    Advisory class: runs local scripts with no workspace writes.
    Args: {"task": "<natural language task description>"}
    """
    task = str(a.get("task", "")).strip()
    if not task:
        return {"status": "empty_task", "note": "Provide a task description."}
    try:
        import importlib.util as _ilu
        spec = _ilu.spec_from_file_location(
            "aios_tool_executor", ROOT / "scripts" / "aios_tool_executor.py")
        executor = _ilu.module_from_spec(spec)
        spec.loader.exec_module(executor)
        result = executor.run(task=task)
        routed = result.get("routed_to", "")
        cap_result = result.get("result", {})
        exec_status = cap_result.get("_executor", {}).get("status", "")
        if result.get("status") == "no_executable_match":
            return {"status": "no_match", "top_recommendations": result.get("top_recommendations", []),
                    "note": result.get("note", "")}
        if exec_status == "ok":
            summary = {k: v for k, v in cap_result.items() if not k.startswith("_")}
            return {"status": "ok", "routed_to": routed,
                    "route_score": result.get("route_score"),
                    "capability": result.get("capability"),
                    "result": summary}
        return {"status": cap_result.get("status", "error"), "routed_to": routed,
                "detail": cap_result}
    except Exception as exc:  # noqa: BLE001
        return {"status": "unavailable", "reason": str(exc)[:120]}


HANDLERS = {
    "memory.retrieve": _h_retrieve, "capability.route": _h_route,
    "genesis.challenge": _h_challenge, "self.audit": _h_self_audit,
    "interior.read": _h_interior, "stakes.record": _h_stakes,
    "fs.list": _h_fs_list, "fs.read": _h_fs_read, "fs.write": _h_fs_write,
    "web.search": _h_web_search, "web.fetch": _h_web_fetch, "note.write": _h_note_write,
    "domain.run": _h_domain_run,
}


def build_registry() -> loop.Registry:
    reg = loop.Registry()
    for name, handler in HANDLERS.items():
        reg.register(name, handler)
    return reg


def gate_for(agent_id: str):
    """An authority-backed per-call gate: read/advisory tools allow; write tools are
    gated by verify_authority on the tool's domain action — unauthorized → ASK."""
    def gate(name: str, arguments: dict) -> str:
        spec = TOOL_SPEC.get(name)
        if spec is None:
            return loop.DENY                          # unknown tool, fail-closed
        cls, action, _desc = spec
        if cls in ("read", "advisory"):
            return loop.ALLOW
        res = authority.verify_authority(agent_id, action)
        return loop.ALLOW if res.allowed else loop.ASK
    return gate


def list_tools() -> list[dict]:
    """Discovery surface (teardown §comms: list_tools)."""
    return [{"name": n, "class": c, "domain_action": a or None, "description": d}
            for n, (c, a, d) in TOOL_SPEC.items()]


if __name__ == "__main__":
    print(json.dumps({"tools": list_tools()}, ensure_ascii=False, indent=2))
