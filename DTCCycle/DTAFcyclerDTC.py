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
    return loaded[key] + "\n\n" + OUTPUT_FORMATTING + ARTIFACTS_HINT


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
        ("1", lambda: build_step1(loaded, problem_statement), 2500, outdir / "step1_business_requirements.md"),
        ("2", lambda: build_step_simple(loaded, "step2"), 2500, outdir / "step2_capability_selector.md"),
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
            temperature=0.2,
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
