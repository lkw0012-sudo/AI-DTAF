#!/usr/bin/env python3
"""
REQUIRED files (in the same folder as this script):
  - cpt.md
  - DTCstep0.md
  - DTCstep1.md
  - DTCstep2.md
  - DTCstep3_part1.md
  - DTCstep3_part2.md

Prereqs:
  - Install Ollama
  - Pull model:  ollama pull qwen2.5:7b
"""

import argparse
import json
import re
import time
import socket
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any
from urllib.parse import urljoin
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError


# -----------------------------
# Fixed formatting
# -----------------------------

OUTPUT_FORMATTING = "Markdown with clear headings, bullet lists, and tables where requested."

ARTIFACTS_HINT = (
    "\n\nNote on formatting: When the prompt says 'Please use Claude artifacts', "
    "treat that as 'use clean, structured Markdown with clear section headings; "
    "use fenced code blocks for any code/HTML; and tables where requested.'"
)


# -----------------------------
# CPT deterministic table spec
# -----------------------------

CAPS = [
    (1, 1, "DS.AI", "Data Acquisition & Ingestion"),
    (1, 2, "DS.SG", "Synthetic Data Generation"),
    (1, 3, "IR.ET", "Enterprise System Integration"),
    (1, 4, "IC.SR", "Search"),
    (1, 5, "IC.PR", "Prediction"),
    (1, 6, "UX.BV", "Basic Visualization"),
    (1, 7, "UX.DB", "Dashboards"),

    (2, 1, "DS.ST", "Data Streaming"),
    (2, 2, "DS.ON", "Ontology Management"),
    (2, 3, "IR.EG", "Eng. System Integration"),
    (2, 4, "IC.CC", "Command & Control"),
    (2, 5, "IC.AI", "Artificial Intelligence"),
    (2, 6, "UX.AV", "Advanced Visualization"),
    (2, 7, "UX.CI", "Continuous Intelligence"),

    (3, 1, "DS.TR", "Data Transformation"),
    (3, 2, "DS.RP", "Digital Twin (DT) Model Repository"),
    (3, 3, "IR.IO", "OT/IoT System Integration"),
    (3, 4, "IC.OS", "Orchestration"),
    (3, 5, "IC.PS", "Prescriptive Recommendations"),
    (3, 6, "UX.RM", "Real-time Monitoring"),
    (3, 7, "UX.BI", "Business Intelligence"),

    (4, 1, "DS.CX", "Data Contextualization"),
    (4, 2, "DS.IR", "DT Instance Repository"),
    (4, 3, "IR.DT", "Digital Twin Integration"),
    (4, 4, "IC.AL", "Alerts & Notifications"),
    (4, 5, "IC.FL", "Federated Learning"),
    (4, 6, "IC.BR", "Business Rules"),
    (4, 7, "UX.ER", "Entity Relationship Visualization"),
    (4, 8, "UX.BP", "BPM & Workflow"),

    (5, 1, "DS.BP", "Batch Processing"),
    (5, 2, "DS.DS", "Domain Specific Data Management"),
    (5, 3, "IR.CL", "Collab Platform Integration"),
    (5, 4, "IC.RP", "Reporting"),
    (5, 5, "IC.SM", "Simulation"),
    (5, 6, "IC.DL", "Distributed Ledger & Smart Contracts"),
    (5, 7, "UX.XR", "Extended Reality (AV/VR/MR)"),
    (5, 8, "UX.GE", "Gaming Engine Visualization"),

    (6, 1, "DS.RT", "Real-time Processing"),
    (6, 2, "DS.SA", "Data Storage & Archive Services"),
    (6, 3, "IR.AS", "API Services"),
    (6, 4, "IC.AA", "Data Analysis & Analytics"),
    (6, 5, "IC.MA", "Mathematical Analytics"),
    (6, 6, "IC.CS", "Composition"),
    (6, 7, "UX.GM", "Gamification"),
    (6, 8, "UX.3R", "3D Rendering"),

    (7, 1, "DS.AS", "Asynchronous Integration"),
    (7, 2, "DS.SR", "Simulation Model Repository"),
    (7, 3, "MG.DM", "Device Management"),
    (7, 4, "MG.EL", "Event Logging"),
    (7, 5, "TW.EX", "Data Encryption"),
    (7, 6, "TW.SC", "Security"),
    (7, 7, "TW.SF", "Safety"),
    (7, 8, "TW.RP", "Responsibility"),

    (8, 1, "DS.AG", "Data Aggregation"),
    (8, 2, "DS.AR", "AI Model Repository"),
    (8, 3, "MG.SM", "System Monitoring"),
    (8, 4, "MG.DG", "Data Governance"),
    (8, 5, "TW.DS", "Device Security"),
    (8, 6, "TW.PR", "Privacy"),
    (8, 7, "TW.RL", "Reliability"),
    (8, 8, "TW.RS", "Resilience"),
]

CATEGORY_STYLE = {
    "DS": {"bg": "#D1DCEA", "border": "#7A9BC4", "text": "#13386D"},
    "IR": {"bg": "#FAEAD5", "border": "#D4A571", "text": "#945911"},
    "IC": {"bg": "#E3DDEC", "border": "#A18DB5", "text": "#4E3D6F"},
    "UX": {"bg": "#EEEEEE", "border": "#999999", "text": "#404040"},
    "MG": {"bg": "#D5E3E1", "border": "#7FA596", "text": "#295548"},
    "TW": {"bg": "#EDD9D5", "border": "#C78275", "text": "#792D21"},
}

PRIORITY_LABEL = {"E": "ESSENTIAL", "H": "HIGH VALUE", "F": "FUTURE"}


# -----------------------------
# Helpers
# -----------------------------

def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)

def append_jsonl(path: Path, obj: Dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")

def write_text(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")

def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")

def read_required_text(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(f"Missing required file: {path.name} (expected in {path.parent})")
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        raise ValueError(f"Required file is empty: {path.name}")
    return text

def load_required_files(script_dir: Path) -> Dict[str, str]:
    files = {
        "cpt": script_dir / "cpt.md",
        "step0": script_dir / "DTCstep0.md",
        "step1": script_dir / "DTCstep1.md",
        "step2": script_dir / "DTCstep2.md",
        "step3_part1": script_dir / "DTCstep3_part1.md",
        "step3_part2": script_dir / "DTCstep3_part2.md",
    }
    return {k: read_required_text(p) for k, p in files.items()}

def ask_input_nonempty(prompt: str) -> str:
    val = input(prompt).strip()
    while not val:
        val = input(prompt).strip()
    return val

def ask_multiline(prompt: str, end_token: str = "END") -> str:
    print(prompt)
    print(f"(Paste text, then type {end_token} on its own line and press Enter)\n")
    lines = []
    while True:
        line = input()
        if line.strip() == end_token:
            break
        lines.append(line)
    text = "\n".join(lines).strip()
    while not text:
        print("Input was empty. Try again.")
        return ask_multiline(prompt, end_token=end_token)
    return text


# -----------------------------
# Priority parsing
# -----------------------------

def parse_priorities_from_text(md: str) -> Dict[str, str]:
    """
    Robustly parses priorities from Step 2 output.

    Supports:
    - Inline: DS.AI [E], DS.AI (E), DS.AI - E
    - Section lists under:
        ### Essential (must have)
        ### High Value (important for full business value)
        ### Future Enhancement (beneficial for long-term evolution)

    Conflict handling:
    - Highest priority wins: E > H > F
    """
    def rank(p: str) -> int:
        return {"E": 3, "H": 2, "F": 1}.get(p, 0)

    def set_pri(d: Dict[str, str], cap: str, p: str) -> None:
        cap = cap.strip()
        p = p.strip().upper()
        if cap and p in {"E", "H", "F"}:
            if rank(p) > rank(d.get(cap, "")):
                d[cap] = p

    priorities: Dict[str, str] = {}

    # Inline patterns
    inline_patterns = [
        r"\b([A-Z]{2}\.[A-Z0-9]{2})\s*\[\s*([EHF])\s*\]",
        r"\b([A-Z]{2}\.[A-Z0-9]{2})\s*\(\s*([EHF])\s*\)",
        r"\b([A-Z]{2}\.[A-Z0-9]{2})\s*[-:]\s*([EHF])\b",
        r"\|\s*([A-Z]{2}\.[A-Z0-9]{2})\s*\[\s*([EHF])\s*\]",
    ]
    for pat in inline_patterns:
        for cap_id, level in re.findall(pat, md):
            set_pri(priorities, cap_id, level)

    # Section bullet lists
    section_specs = [
        ("Essential (must have)", "E"),
        ("High Value (important for full business value)", "H"),
        ("Future Enhancement (beneficial for long-term evolution)", "F"),
    ]

    lines = md.splitlines()

    def find_heading_index(heading_text: str) -> Optional[int]:
        needle = "### " + heading_text.strip().lower()
        for i, line in enumerate(lines):
            if line.strip().lower() == needle:
                return i
        return None

    cap_pat = re.compile(r"\b([A-Z]{2}\.[A-Z0-9]{2})\b")

    for heading, pri in section_specs:
        start = find_heading_index(heading)
        if start is None:
            continue
        i = start + 1
        while i < len(lines):
            line = lines[i]
            if line.strip().startswith("### "):
                break
            if line.strip().startswith(("-", "*")):
                for cap_id in cap_pat.findall(line):
                    set_pri(priorities, cap_id, pri)
            i += 1

    return priorities

def generate_cpt_html(priorities: Dict[str, str]) -> str:
    def tile_html(row: int, col: int, cap_id: str, name: str) -> str:
        cat = cap_id.split(".")[0]
        st = CATEGORY_STYLE.get(cat, {"bg": "#fff", "border": "#ccc", "text": "#222"})
        p = priorities.get(cap_id)  # "E"/"H"/"F"/None
        badge = PRIORITY_LABEL.get(p, "—")
        badge_class = {"E": "pE", "H": "pH", "F": "pF"}.get(p, "pN")

        return f"""
        <div class="tile {badge_class}" style="grid-row:{row};grid-column:{col};background:{st['bg']};border-color:{st['border']};color:{st['text']}">
          <div class="badge">{badge}</div>
          <div class="capid">{cap_id}</div>
          <div class="name">{name}</div>
        </div>
        """

    tiles = "\n".join(tile_html(*c) for c in CAPS)

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width,initial-scale=1" />
<title>Digital Twin Capabilities Periodic Table v1.2</title>
<style>
  body{{font-family:system-ui,-apple-system,Segoe UI,Roboto,Arial,sans-serif;margin:0;padding:24px;background:#fafafa;color:#111}}
  .wrap{{max-width:1100px;margin:0 auto}}
  h1{{margin:0 0 6px;font-size:24px}}
  .sub{{margin:0 0 18px;color:#444}}
  .grid{{display:grid;grid-template-columns:repeat(8,1fr);grid-template-rows:repeat(8,minmax(80px,auto));gap:10px}}
  .tile{{border:2px solid;border-radius:10px;padding:10px;position:relative;box-shadow:0 1px 0 rgba(0,0,0,.04);transition:transform .12s ease,box-shadow .12s ease}}
  .tile:hover{{transform:translateY(-2px);box-shadow:0 6px 18px rgba(0,0,0,.08)}}
  .badge{{position:absolute;top:8px;left:8px;font-size:10px;font-weight:800;letter-spacing:.4px;padding:3px 6px;border-radius:6px;background:rgba(255,255,255,.78)}}
  .capid{{font-size:12px;font-weight:900;margin-top:18px}}
  .name{{font-size:12px;line-height:1.2;margin-top:6px;opacity:.95}}

  .pE{{outline:3px solid rgba(46,204,113,.18)}}
  .pH{{outline:3px solid rgba(243,156,18,.18)}}
  .pF{{outline:3px solid rgba(149,165,166,.20)}}
  .pE .badge{{border-left:6px solid #2ecc71}}
  .pH .badge{{border-left:6px solid #f39c12}}
  .pF .badge{{border-left:6px solid #95a5a6}}
  .pN .badge{{border-left:6px solid #bbb}}

  .legend{{margin-top:18px;display:grid;grid-template-columns:repeat(3,1fr);gap:10px}}
  .leg{{border:1px solid #ddd;border-radius:10px;padding:10px;background:#fff}}
  .sw{{display:inline-block;width:14px;height:14px;border-radius:4px;margin-right:8px;vertical-align:middle;border:2px solid transparent}}
  @media (max-width:780px){{ .grid{{grid-template-columns:repeat(4,1fr)}} }}
</style>
</head>
<body>
<div class="wrap">
  <h1>Digital Twin Capabilities Periodic Table v1.2</h1>
  <div class="sub">Complete Framework of 60+ Core Capabilities</div>

  <div class="grid">
    {tiles}
  </div>

  <div class="legend">
    <div class="leg"><span class="sw" style="background:{CATEGORY_STYLE['DS']['bg']};border-color:{CATEGORY_STYLE['DS']['border']}"></span><b>DS</b>: Enables data access, ingestion and data management across the platform from the edge to the cloud</div>
    <div class="leg"><span class="sw" style="background:{CATEGORY_STYLE['IR']['bg']};border-color:{CATEGORY_STYLE['IR']['border']}"></span><b>IR</b>: Enables data access to existing internal and external enterprise systems and applications</div>
    <div class="leg"><span class="sw" style="background:{CATEGORY_STYLE['IC']['bg']};border-color:{CATEGORY_STYLE['IC']['border']}"></span><b>IC</b>: Provides an environment for the development and deployment of industrial digital twin solutions</div>
    <div class="leg"><span class="sw" style="background:{CATEGORY_STYLE['UX']['bg']};border-color:{CATEGORY_STYLE['UX']['border']}"></span><b>UX</b>: Provides the user with the ability to interact with digital twins and visualize its data</div>
    <div class="leg"><span class="sw" style="background:{CATEGORY_STYLE['MG']['bg']};border-color:{CATEGORY_STYLE['MG']['border']}"></span><b>MG</b>: System and ecosystem management capabilities</div>
    <div class="leg"><span class="sw" style="background:{CATEGORY_STYLE['TW']['bg']};border-color:{CATEGORY_STYLE['TW']['border']}"></span><b>TW</b>: Security, privacy, safety, reliability and resilience capabilities</div>
  </div>
</div>
</body>
</html>"""


# -----------------------------
# Ollama client
# -----------------------------

def _post_json(url: str, payload: Dict[str, Any], timeout: float, retries: int = 3, backoff: float = 2.0) -> Dict[str, Any]:
    data = json.dumps(payload).encode("utf-8")
    last_err: Optional[Exception] = None

    for attempt in range(1, retries + 1):
        req = Request(
            url=url,
            data=data,
            headers={"Content-Type": "application/json", "Authorization": "Bearer ollama"},
            method="POST",
        )

        try:
            with urlopen(req, timeout=timeout) as resp:
                body = resp.read().decode("utf-8", errors="replace")
                return json.loads(body)

        except HTTPError as e:
            err_body = e.read().decode("utf-8", errors="replace") if hasattr(e, "read") else ""
            if 400 <= e.code < 500:
                raise RuntimeError(f"HTTP {e.code} calling {url}\n{err_body}") from e
            last_err = RuntimeError(f"HTTP {e.code} calling {url}\n{err_body}")

        except (TimeoutError, socket.timeout):
            last_err = RuntimeError(
                f"Timeout calling {url} (timeout={timeout}s). "
                "Common on first run while Ollama loads the model, or on slower machines."
            )

        except URLError as e:
            reason = getattr(e, "reason", "")
            reason_str = str(reason) if reason else str(e)
            if "timed out" in reason_str.lower():
                last_err = RuntimeError(
                    f"Timeout calling {url} (timeout={timeout}s). "
                    "Common on first run while Ollama loads the model, or on slower machines."
                )
            else:
                raise RuntimeError(f"Failed to reach {url}: {e}") from e

        except json.JSONDecodeError as e:
            raise RuntimeError(f"Non-JSON response from {url}: {e}") from e

        if attempt < retries:
            sleep_s = backoff ** (attempt - 1)
            print(f"[retry] attempt {attempt}/{retries} failed; sleeping {sleep_s:.1f}s then retrying...")
            time.sleep(sleep_s)

    assert last_err is not None
    raise last_err


def chat_completions(
    *,
    base_url: str,
    model: str,
    messages: List[Dict[str, str]],
    max_tokens: int,
    temperature: float,
    timeout: float,
    retries: int = 3,
) -> str:
    base = base_url.rstrip("/") + "/"
    endpoint = urljoin(base, "chat/completions")

    payload = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "stream": False,
    }

    resp = _post_json(endpoint, payload, timeout=timeout, retries=retries)

    try:
        return (resp["choices"][0]["message"].get("content") or "").strip()
    except Exception as e:
        raise RuntimeError(f"Unexpected response format from Ollama: {resp}") from e


def run_step(
    *,
    base_url: str,
    model: str,
    messages: List[Dict[str, str]],
    user_prompt: str,
    timeout: float,
    max_tokens: int,
    temperature: float,
    retries: int,
) -> str:
    messages.append({"role": "user", "content": user_prompt})
    out = chat_completions(
        base_url=base_url,
        model=model,
        messages=messages,
        max_tokens=max_tokens,
        temperature=temperature,
        timeout=timeout,
        retries=retries,
    )
    messages.append({"role": "assistant", "content": out})
    return out


def warmup_model(*, base_url: str, model: str, timeout: float, retries: int = 3) -> None:
    try:
        _ = chat_completions(
            base_url=base_url,
            model=model,
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Say 'ready'."},
            ],
            max_tokens=8,
            temperature=0.0,
            timeout=timeout,
            retries=retries,
        )
    except Exception as e:
        print(f"[warn] warm-up call failed (continuing anyway): {e}")


# -----------------------------
# Prompt builders
# -----------------------------

def build_step0(loaded: Dict[str, str], sector: str) -> str:
    return loaded["step0"].replace("[Blank]", sector) + "\n\n" + OUTPUT_FORMATTING + ARTIFACTS_HINT

def build_step1(loaded: Dict[str, str], problem_statement: str) -> str:
    return loaded["step1"].replace("[Blank]", problem_statement) + "\n\n" + OUTPUT_FORMATTING + ARTIFACTS_HINT

def build_step_simple(loaded: Dict[str, str], key: str) -> str:
        extra = ""
        if key == "step2":
            extra = (
                "\n\nIMPORTANT FORMATTING REQUIREMENT: For every capability row in every table, "
                "you MUST append a priority tag as the final column.\n"
                "Priority tags:\n"
                "- [E] = Essential (must have for core functionality)\n"
                "- [H] = High Value (important for full business value)\n"
                "- [F] = Future Enhancement (beneficial for long-term evolution)\n\n"
                "Every single capability row must end with [E], [H], or [F]. "
                "Do not use words like 'Essential' or 'Important' in place of these tags.\n"
                "Example row format:\n"
                "| **DS.AI** | Data Acquisition & Ingestion | Required for real-time sensor data collection | Edge and Fog | [E] |"
            )
        return loaded[key] + "\n\n" + OUTPUT_FORMATTING + ARTIFACTS_HINT

# -----------------------------
# Post DTC Step4: Deterministic readiness screen
# -----------------------------

DTAF_FILES = {
    "priorities": "priorities.json",
    "step1": "step1_business_requirements.md",
    "step2": "step2_capability_selector.md",
    "step3": "step3_capability_deep_dives.md",
    "step3p1": "step3_part1.md",
    "step3p2": "step3_part2.md",
}

# -----------------------------
# DTAF Readiness questions + prune
# -----------------------------

CAP_NAME = {cap_id: name for _, _, cap_id, name in CAPS}
CAP_ORDER = {cap_id: i for i, (_, _, cap_id, _) in enumerate(CAPS)}

def dtaf_priority_rank(p: str) -> int:
    return {"E": 3, "H": 2, "F": 1}.get((p or "").strip().upper(), 0)

def dtaf_select_essential_and_high(priorities: Dict[str, str]) -> tuple[list[str], list[str]]:
    essential = [cid for cid, lvl in priorities.items() if (lvl or "").strip().upper() == "E"]
    high = [cid for cid, lvl in priorities.items() if (lvl or "").strip().upper() == "H"]
    essential.sort(key=lambda c: CAP_ORDER.get(c, 10_000))
    high.sort(key=lambda c: CAP_ORDER.get(c, 10_000))
    return essential, high

def dtaf_safe_json_extract(s: str) -> Dict[str, Any]:
    s = s.strip()
    try:
        return json.loads(s)
    except Exception:
        pass
    m = re.search(r"\{.*\}", s, flags=re.S)
    if not m:
        raise ValueError("Model did not return JSON.")
    return json.loads(m.group(0))

def dtaf_validate_gates(obj: Dict[str, Any], cap_ids: list[str]) -> Dict[str, Dict[str, Any]]:
    """
    Expected schema:
    {
      "capabilities": {
        "DS.AI": {"prerequisites":[...], "hard_gates":[0,2], "notes":"..."},
        ...
      }
    }
    """
    caps_obj = obj.get("capabilities", {})
    if not isinstance(caps_obj, dict):
        raise ValueError("JSON missing 'capabilities' dict")

    out: Dict[str, Dict[str, Any]] = {}
    for cid in cap_ids:
        entry = caps_obj.get(cid, {})
        if not isinstance(entry, dict):
            entry = {}

        prereq = entry.get("prerequisites", [])
        hard = entry.get("hard_gates", [])
        notes = entry.get("notes", "")

        if not isinstance(prereq, list):
            prereq = []
        prereq = [str(x).strip() for x in prereq if str(x).strip()]
        prereq = list(dict.fromkeys(prereq))  # dedupe

        # enforce size
        if len(prereq) < 1:
            prereq = ["You have the data and access needed to implement this capability"]
        if len(prereq) > 10:
            prereq = prereq[:10]

        if not isinstance(hard, list):
            hard = []
        hard2: list[int] = []
        for x in hard:
            if isinstance(x, int):
                hard2.append(x)
            elif isinstance(x, str) and x.isdigit():
                hard2.append(int(x))
        hard2 = sorted(set([h for h in hard2 if 0 <= h < len(prereq)]))
        if len(hard2) == 0:
            hard2 = [0]
        if len(hard2) > 4:
            hard2 = hard2[:4]

        out[cid] = {"prerequisites": prereq, "hard_gates": hard2, "notes": str(notes).strip()}

    return out

def dtaf_generate_gates_with_ollama(
    *,
    base_url: str,
    model: str,
    timeout: float,
    retries: int,
    step1: str,
    step2: str,
    step3: str,
    cap_ids: list[str],
) -> Dict[str, Dict[str, Any]]:
    cap_list = [{"cap_id": cid, "cap_name": CAP_NAME.get(cid, "")} for cid in cap_ids]

    messages = [
        {"role": "system", "content": "Return ONLY JSON. Generate readiness gating checklists for each capability."},
        {"role": "user", "content": (
            "Generate capability-specific readiness checklists.\n"
            "Rules:\n"
            "- For EACH capability: 3 to 8 prerequisites (max 10), phrased as concrete yes/no checks.\n"
            "- Mark 1 to 4 items as HARD GATES (missing => not feasible now).\n"
            "- Use Step 1/2/3 text to tailor to the use case.\n"
            "- Output JSON exactly:\n"
            "{\n"
            '  "capabilities": {\n'
            '    "DS.AI": {"prerequisites":[...], "hard_gates":[0,2], "notes":"..."},\n'
            "    ...\n"
            "  }\n"
            "}\n\n"
            f"Capability list:\n{json.dumps(cap_list, indent=2)}\n\n"
            f"Step 1:\n{step1[:8000]}\n\n"
            f"Step 2:\n{step2[:8000]}\n\n"
            f"Step 3:\n{step3[:8000]}\n"
        )},
    ]

    out = chat_completions(
        base_url=base_url,
        model=model,
        messages=messages,
        max_tokens=2200,
        temperature=0.0,
        timeout=timeout,
        retries=retries,
    )
    obj = dtaf_safe_json_extract(out)
    return dtaf_validate_gates(obj, cap_ids)

def dtaf_fallback_gates(cap_id: str, priority: str) -> Dict[str, Any]:
    """
    Lightweight fallback (generic by category) if LLM JSON fails.
    """
    cat = cap_id.split(".")[0]
    prereq = []
    hard = [0]
    if cat == "DS":
        prereq = [
            "You can access the needed source data in a repeatable way (not manual retyping)",
            "You can move data into a usable store (files/db/historian) consistently",
            "You can identify assets/jobs with stable IDs to join data later",
        ]
        hard = [0, 1]
    elif cat == "IR":
        prereq = [
            "You have credentials/export/API access to the target system",
            "You can map identifiers between systems (job IDs, part numbers, machine IDs)",
            "Policy/security allows the integration in production",
        ]
        hard = [0, 1]
    elif cat == "IC":
        prereq = [
            "You have enough data to compute/derive the outputs for this capability",
            "You can define success criteria/labels for the analytics",
            "You have a place to run analytics and store results",
        ]
        hard = [0]
    elif cat == "UX":
        prereq = [
            "You have a tool to display the results (dashboard/BI/web/SCADA/Excel)",
            "You know the target user and what decision they will make from the display",
        ]
        hard = [0]
    elif cat in {"MG", "TW"}:
        prereq = [
            "You can meet the required governance/security needs for the data/services",
            "You can monitor and log the pipeline/service health at a basic level",
        ]
        hard = [0]
    else:
        prereq = ["You have the data and access needed to implement this capability"]
        hard = [0]

    return {
        "cap_id": cap_id,
        "cap_name": CAP_NAME.get(cap_id, "(unknown)"),
        "priority": priority,
        "prerequisites": prereq,
        "hard_gates": hard,
        "notes": "(fallback)",
    }

def dtaf_ask_checklist(cap: Dict[str, Any]) -> Optional[List[int]]:
    letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    prereq = cap["prerequisites"]
    hard = set(cap["hard_gates"])

    print(f"\nCapability: {cap['cap_id']} ({cap['priority']}) — {cap['cap_name']}")
    if cap.get("notes"):
        print(f"Notes: {cap['notes']}")

    for i, item in enumerate(prereq):
        mark = "HARD" if i in hard else ""
        print(f"  {letters[i]}) {item}" + (f" [{mark}]" if mark else ""))

    print("Answer with letters you HAVE (e.g., A C). Or: all / none / skip")
    ans = input("A: ").strip().lower()
    if ans == "skip":
        return None
    if ans == "all":
        return list(range(len(prereq)))
    if ans in {"none", ""}:
        return []

    picked = re.findall(r"[a-z]", ans)
    have: List[int] = []
    for ch in picked:
        idx = letters.lower().find(ch)
        if 0 <= idx < len(prereq) and idx not in have:
            have.append(idx)
    return sorted(have)

def dtaf_score(cap: Dict[str, Any], have: List[int]) -> Dict[str, Any]:
    n = len(cap["prerequisites"])
    have_set = set(have)
    missing = [i for i in range(n) if i not in have_set]
    missing_hard = [i for i in cap["hard_gates"] if i not in have_set]
    feasible = len(missing_hard) == 0
    readiness = (len(have_set) / n) if n else 0.0
    return {
        "cap_id": cap["cap_id"],
        "cap_name": cap["cap_name"],
        "priority": cap["priority"],
        "feasible_now": feasible,
        "readiness_score": round(readiness, 3),
        "have_indices": sorted(list(have_set)),
        "missing_indices": missing,
        "missing_hard_gate_indices": missing_hard,
    }

def run_dtaf_addon_after_step4(
    *,
    dtc_outdir: Path,
    log_path: Path,
    priorities: Dict[str, str],
    step1: str,
    step2: str,
    step3: str,
    base_url: str,
    model: str,
    timeout: float,
    retries: int,
    keep: int,
    use_llm: bool,
    extend_to_high: bool,
) -> None:
    essential, high = dtaf_select_essential_and_high(priorities)

    # Screen count is based on number of Essential capabilities
    selected = essential[:]

    # Generate question sets
    outdir = dtc_outdir / f"dtaf_addon_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
    ensure_dir(outdir)

    gates: Dict[str, Dict[str, Any]] = {}

    if use_llm and selected:
        try:
            llm_map = dtaf_generate_gates_with_ollama(
                base_url=base_url,
                model=model,
                timeout=timeout,
                retries=retries,
                step1=step1,
                step2=step2,
                step3=step3,
                cap_ids=selected,
            )
            for cid in selected:
                gates[cid] = {
                    "cap_id": cid,
                    "cap_name": CAP_NAME.get(cid, "(unknown)"),
                    "priority": priorities.get(cid, ""),
                    "prerequisites": llm_map[cid]["prerequisites"],
                    "hard_gates": llm_map[cid]["hard_gates"],
                    "notes": llm_map[cid].get("notes", ""),
                }
            write_text(outdir / "gating_questions_source.txt", "ollama_json")
        except Exception as e:
            print(f"[warn] LLM gating failed; using fallback. Reason: {e}")
            for cid in selected:
                gates[cid] = dtaf_fallback_gates(cid, priorities.get(cid, ""))
            write_text(outdir / "gating_questions_source.txt", "fallback")
    else:
        for cid in selected:
            gates[cid] = dtaf_fallback_gates(cid, priorities.get(cid, ""))
        write_text(outdir / "gating_questions_source.txt", "fallback")

    answers: Dict[str, Any] = {}
    results: List[Dict[str, Any]] = []

    print("\n==============================")
    print("Capability Feasibility Checklist")
    print("==============================")
    print(f"Screening Essential capabilities: {len(selected)}")
    print(f"Ranking all {len(selected)} Essential capabilities by readiness.\n")

    def screen_list(cap_list: list[str]) -> None:
        nonlocal gates, answers, results
        for cid in cap_list:
            cap = gates.get(cid) or dtaf_fallback_gates(cid, priorities.get(cid, ""))
            have = dtaf_ask_checklist(cap)
            if have is None:
                answers[cid] = {"skipped": True}
                results.append({
                    "cap_id": cap["cap_id"],
                    "cap_name": cap["cap_name"],
                    "priority": cap["priority"],
                    "feasible_now": False,
                    "readiness_score": 0.0,
                    "have_indices": [],
                    "missing_indices": list(range(len(cap["prerequisites"]))),
                    "missing_hard_gate_indices": cap["hard_gates"],
                })
            else:
                answers[cid] = {"have_indices": have, "prerequisites": cap["prerequisites"], "hard_gates": cap["hard_gates"]}
                results.append(dtaf_score(cap, have))

    screen_list(selected)

    # Rank
    def rank_key(r: Dict[str, Any]) -> tuple:
        return (
            0 if r["feasible_now"] else 1,
            -r["readiness_score"],
            -dtaf_priority_rank(r["priority"]),
            CAP_ORDER.get(r["cap_id"], 10_000),
        )

    results_sorted = sorted(results, key=rank_key)
    recommended = [r for r in results_sorted if r["feasible_now"]][:keep]

    # Optionally extend to High Value if you need to fill Top-K
    if extend_to_high and len(recommended) < keep:
        remaining = [cid for cid in high if cid not in selected]
        if remaining:
            print(f"\nNot enough feasible Essentials to fill Top {keep}. Screening High Value...\n")

        # Generate gates for high if using LLM (one shot), else fallback
        if use_llm and remaining:
            try:
                llm_map = dtaf_generate_gates_with_ollama(
                    base_url=base_url,
                    model=model,
                    timeout=timeout,
                    retries=retries,
                    step1=step1,
                    step2=step2,
                    step3=step3,
                    cap_ids=remaining,
                )
                for cid in remaining:
                    gates[cid] = {
                        "cap_id": cid,
                        "cap_name": CAP_NAME.get(cid, "(unknown)"),
                        "priority": priorities.get(cid, ""),
                        "prerequisites": llm_map[cid]["prerequisites"],
                        "hard_gates": llm_map[cid]["hard_gates"],
                        "notes": llm_map[cid].get("notes", ""),
                    }
            except Exception:
                for cid in remaining:
                    gates[cid] = dtaf_fallback_gates(cid, priorities.get(cid, ""))

        screen_list(remaining)

        results_sorted = sorted(results, key=rank_key)
        recommended = [r for r in results_sorted if r["feasible_now"]][:keep]

    # Write artifacts
    write_text(outdir / "selected_caps.json", json.dumps(selected, indent=2))
    write_text(outdir / "gating_questions.json", json.dumps(gates, indent=2))
    write_text(outdir / "user_answers.json", json.dumps(answers, indent=2))
    write_text(outdir / "screen_results.json", json.dumps(results_sorted, indent=2))
    write_text(outdir / "recommended.json", json.dumps(recommended, indent=2))

    # Summary
    lines = []
    lines.append("# DTAF Add-on (post Step 4) — Capability Readiness Screen")
    lines.append(f"- DTC outdir: `{dtc_outdir.name}`")
    lines.append(f"- Screened Essentials: **{len(selected)}**")
    lines.append(f"- Feasible capabilities (ranked by readiness): **{len(recommended)}**\n")
    lines.append("## Recommended capabilities you can do now")
    if recommended:
        for r in recommended:
            lines.append(f"- **{r['cap_id']} ({r['priority']})** — {r['cap_name']} | readiness={r['readiness_score']}")
    else:
        lines.append("- *(None feasible with current answers.)*")
    write_text(outdir / "summary.md", "\n".join(lines))

    append_jsonl(
        log_path,
        {
            "step": "DTAF_addon_post_step4",
            "time_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "output_path": str((outdir / "summary.md").name),
        },
    )

    print("\nDTAF add-on complete.")
    print(f"Saved: {outdir.resolve()}")
    print(f" - {outdir / 'summary.md'}")
    print(f" - {outdir / 'recommended.json'}\n")

# -----------------------------
# Main
# -----------------------------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default="http://localhost:11434/v1",
                    help="Ollama OpenAI-compatible base URL, e.g. http://localhost:11434/v1")
    ap.add_argument("--model", default="qwen2.5:7b", help="Ollama model name, e.g. qwen2.5:7b")
    ap.add_argument("--outdir", default="", help="Output directory (default: dtc_cpt_run_<timestamp>)")
    ap.add_argument("--timeout", type=float, default=600.0, help="HTTP timeout seconds")
    ap.add_argument("--retries", type=int, default=3, help="Retries on timeout/transient failure")
    ap.add_argument("--no-warmup", action="store_true", help="Disable model warm-up call before Step 0")
    ap.add_argument("--dtaf-keep", type=int, default=999,
                    help="DTAF add-on: how many feasible capabilities to recommend (default: all)")
    ap.add_argument("--skip-dtaf", action="store_true",
                    help="Skip DTAF add-on readiness questions after Step 4")
    ap.add_argument("--no-dtaf-use-llm", action="store_true",
                    help="Disable Ollama-generated readiness questions and use fallback instead")
    ap.add_argument("--dtaf-extend-to-high", action="store_true",
                    help="If not enough feasible Essential caps, screen High Value caps to fill Top-K")
    args = ap.parse_args()

    script_dir = Path(__file__).resolve().parent
    loaded = load_required_files(script_dir)

    # Inputs for blanks
    sector = ask_input_nonempty("Step 0 blank: What sector should be analyzed (e.g., 'manufacturing', 'energy', 'healthcare')? ")
    problem_statement = ask_multiline("Step 1 blank: Paste the problem statement for the digital twin use case:")

    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    outdir = Path(args.outdir) if args.outdir else Path(f"dtc_cpt_run_{ts}")
    ensure_dir(outdir)
    log_path = outdir / "run_log.jsonl"

    # Conversation context
    messages: List[Dict[str, str]] = [
        {
            "role": "system",
            "content": (
                "You are a precise, structured digital twin analyst and technical writer. "
                "Follow instructions exactly. Use concise, actionable language. "
                "When asked for tables, provide tables."
            ),
        },
        {
            "role": "system",
            "content": (
                "Additional reference context for the DTC CPT workflow. "
                "Use this throughout all steps (0–3). "
                "If it conflicts with the step prompts, follow the step prompts.\n\n"
                "----- BEGIN CPT CONTEXT (cpt.md) -----\n"
                f"{loaded['cpt']}\n"
                "----- END CPT CONTEXT (cpt.md) -----"
            ),
        },
    ]
    print(f"Injected CPT context from: {script_dir / 'cpt.md'}")

    if not args.no_warmup:
        print("Warming up model (first run can take a while on some machines)...")
        warmup_model(base_url=args.base_url, model=args.model, timeout=args.timeout, retries=args.retries)

    # Steps 0–3 (loop)
    plan = [
        ("0", lambda: build_step0(loaded, sector), 1200, outdir / "step0_use_case_suitability.md"),
        ("1", lambda: build_step1(loaded, problem_statement), 2400, outdir / "step1_business_requirements.md"),
        ("2", lambda: build_step_simple(loaded, "step2"), 2400, outdir / "step2_capability_selector.md"),
        ("3_part1", lambda: build_step_simple(loaded, "step3_part1"), 2200, outdir / "step3_part1.md"),
        ("3_part2", lambda: build_step_simple(loaded, "step3_part2"), 2600, outdir / "step3_part2.md"),
    ]

    outputs: Dict[str, str] = {}

    for step_id, builder, max_tokens, out_path in plan:
        prompt_text = builder()
        out = run_step(
            base_url=args.base_url,
            model=args.model,
            messages=messages,
            user_prompt=prompt_text,
            timeout=args.timeout,
            max_tokens=max_tokens,
            temperature=0.0,
            retries=args.retries,
        )
        write_text(out_path, out)
        outputs[step_id] = out

        append_jsonl(
            log_path,
            {
                "step": step_id,
                "time_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                "output_path": out_path.name,
            },
        )

    # Combine Step 3
    combined_step3 = (
        f"# Step 3 (part1)\n\n{read_text(outdir / 'step3_part1.md')}\n\n"
        f"---\n\n"
        f"# Step 3 (part2)\n\n{read_text(outdir / 'step3_part2.md')}\n"
    )
    write_text(outdir / "step3_capability_deep_dives.md", combined_step3)

    # Deterministic Step 4 from Step 2 priorities
    step2_text = outputs.get("2", read_text(outdir / "step2_capability_selector.md"))
    priorities = parse_priorities_from_text(step2_text)
    write_text(outdir / "priorities.json", json.dumps(priorities, indent=2))
    det_html = generate_cpt_html(priorities)
    write_text(outdir / "step4_cpt_table.html", det_html)

    append_jsonl(
        log_path,
        {
            "step": "4_deterministic",
            "time_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "output_path": "step4_cpt_table.html",
        },
    )

    # -----------------------------
    # Capability Feasibility Checklist Context
    # -----------------------------
    if not args.skip_dtaf:
        try:
            run_dtaf_addon_after_step4(
                dtc_outdir=outdir,
                log_path=log_path,
                priorities=priorities,
                step1=outputs.get("1", ""),
                step2=outputs.get("2", ""),
                step3=read_text(outdir / "step3_capability_deep_dives.md") if (outdir / "step3_capability_deep_dives.md").exists() else "",
                base_url=args.base_url,
                model=args.model,
                timeout=args.timeout,
                retries=args.retries,
                keep=args.dtaf_keep,
                use_llm=not args.no_dtaf_use_llm,
                extend_to_high=args.dtaf_extend_to_high,
            )
        except KeyboardInterrupt:
            print("\nDTAF add-on interrupted (Ctrl+C). Continuing...")
        except Exception as e:
            print(f"\n[warn] DTAF add-on failed: {e}")

    print("\nDONE.")
    print(f"Outputs written to: {outdir.resolve()}")
    print("Key files:")
    print(f" - {outdir / 'step0_use_case_suitability.md'}")
    print(f" - {outdir / 'step1_business_requirements.md'}")
    print(f" - {outdir / 'step2_capability_selector.md'}")
    print(f" - {outdir / 'step3_capability_deep_dives.md'}")
    print(f" - {outdir / 'priorities.json'}")
    print(f" - {outdir / 'step4_cpt_table.html'}")
    print(f" - {outdir / 'run_log.jsonl'}")


if __name__ == "__main__":
    main()
