#!/usr/bin/env python3
import argparse
import ast
import ctypes
import html
import json
import os
import platform
import re
import time
import socket
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any
from urllib.parse import urljoin, urlparse, urlunparse
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

DETERMINISTIC_COMPLETION_FIELDS = {
    "seed": 42,
    "top_p": 0.1,
}

OLLAMA_RUNTIME_OPTIONS: Dict[str, Any] = {}

MODEL_SELECTION_TIERS = [
    {
        "label": "low-memory",
        "primary": "qwen2.5:3b",
        "models": ["qwen2.5:3b", "phi3.5:3.8b", "gemma2:2b"],
        "reason": "limited RAM or CPU; favors responsiveness and successful local runs",
    },
    {
        "label": "safe-balanced",
        "primary": "qwen2.5:7b",
        "models": ["qwen2.5:7b", "llama3.1:8b", "mistral:7b"],
        "reason": "default safe local profile; good quality while leaving resources for the user",
    },
    {
        "label": "high",
        "primary": "qwen2.5:14b",
        "models": ["qwen2.5:14b", "mistral-nemo:12b"],
        "reason": "opt-in higher quality profile for systems where temporary slowdown is acceptable",
    },
    {
        "label": "workstation",
        "primary": "qwen2.5:32b",
        "models": ["qwen2.5:32b"],
        "reason": "explicit performance profile only; can consume substantial local resources",
    },
]


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


def read_json(path: Path) -> Any:
    return json.loads(read_text(path))


def read_required_text(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(f"Missing required file: {path.name} (expected in {path.parent})")
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        raise ValueError(f"Required file is empty: {path.name}")
    return text



UNRELATED_EXAMPLE_TERMS = [
    r"octoprint", r"3d printer", r"printer", r"printing bed", r"print bed", r"extruder", r"thermocouple",
    r"pallet elevator", r"pallet", r"conveyor", r"head install", r"head load", r"head return", r"head buffer",
    r"additive manufacturing", r"fdm", r"simio", r"raspberry pi", r"humidity sensor", r"distance sensor",
    r"customer preferences", r"marketing efforts", r"market conditions"
]
UNRELATED_EXAMPLE_RE = re.compile(r"(" + "|".join(UNRELATED_EXAMPLE_TERMS) + r")", re.I)
NO_EVIDENCE_RE = re.compile(r"\b(no\s+(explicit\s+)?evidence|no\s+clear\s+evidence|not\s+provided|missing\s+evidence|none\b|not\s+available|not\s+implemented|not\s+yet\s+implemented|no\s+predictive\s+models|no\s+real-?time\s+anomaly\s+detection|no\s+real-?time\s+decision-?making|lacks\b|does\s+not\s+provide|not\s+clearly\s+defined)\b", re.I)
PARTIAL_EVIDENCE_RE = re.compile(r"\b(partial|partially|implied|limited|weak|incomplete|suggests|some\s+evidence|not\s+fully|not\s+direct|unclear|not\s+explicit|not\s+detailed|not\s+fully\s+detailed|not\s+yet\s+verified|not\s+yet\s+validated|still\s+needs)\b", re.I)
GENERIC_ACTION_RE = re.compile(r"\b(ensure|check|verify|validate|map|define|build|develop|implement)\b", re.I)

GENERIC_STOPWORDS = {
    'digital','twin','system','systems','provide','providing','accurate','data','driven','insight','before','begins',
    'must','need','needed','should','would','could','will','using','used','based','from','into','with','that','this',
    'their','there','which','about','support','supports','supporting','quality','cost','time','process','processes',
    'real','world','current','future','level','target','build','planned','planning','decision','decisions','making'
}

def normalize_ws(text: Any) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip()


def contains_unrelated_example_text(text: Any, sector: str = "", problem_statement: str = "") -> bool:
    s = str(text or "")
    context = f"{sector} {problem_statement}".lower()
    for match in UNRELATED_EXAMPLE_RE.finditer(s):
        term = match.group(0).lower()
        if term and term not in context:
            return True
    return False


def coerce_preferred_text(value: Any, preferred_keys: Optional[List[str]] = None) -> str:
    preferred_keys = preferred_keys or []
    if value is None:
        return ""
    if isinstance(value, str):
        s = value.strip()
        parsed = None
        if (s.startswith('{') and s.endswith('}')) or (s.startswith('[') and s.endswith(']')):
            for parser in (json.loads, ast.literal_eval):
                try:
                    parsed = parser(s)
                    break
                except Exception:
                    parsed = None
        if parsed is not None:
            value = parsed
        else:
            return s
    if isinstance(value, dict):
        for key in preferred_keys:
            if key in value and str(value.get(key, '')).strip():
                return normalize_ws(value.get(key, ''))
        for v in value.values():
            txt = normalize_ws(v)
            if txt:
                return txt
        return ""
    if isinstance(value, list):
        bits = [normalize_ws(v) for v in value if normalize_ws(v)]
        return '; '.join(bits)
    return normalize_ws(value)


def extract_use_case_focus_terms(sector: str, problem_statement: str, limit: int = 6) -> List[str]:
    text = f"{sector} {problem_statement}".lower()
    tokens = re.findall(r"[a-zA-Z][a-zA-Z0-9\-/]+", text)
    out: List[str] = []
    seen = set()
    for tok in tokens:
        if len(tok) < 4:
            continue
        if tok in GENERIC_STOPWORDS:
            continue
        if tok in seen:
            continue
        seen.add(tok)
        out.append(tok)
        if len(out) >= limit:
            break
    return out


def build_use_case_example(sector: str, problem_statement: str, action_hint: str = "") -> str:
    ps = normalize_ws(problem_statement)
    ps_l = ps.lower()
    action_hint = normalize_ws(action_hint).lower()

    cnc_terms = [
        "spindle speed", "feed rate", "spindle load", "vibration", "tool id", "machine state",
        "job id", "part number", "axis position", "g-code", "cycle time", "inspection results"
    ]
    general_terms = extract_use_case_focus_terms(sector, problem_statement, limit=8)

    if any(k in ps_l for k in ["cnc", "machining", "spindle", "feed rate", "g-code", "tool wear"]):
        if any(k in action_hint for k in ["variable", "state", "signal", "sensor", "data"]):
            preferred = cnc_terms[:6]
        elif any(k in action_hint for k in ["model", "replic", "sync", "scenario", "simulation"]):
            preferred = ["axis position", "machine state", "cycle time", "spindle load", "controller timestamps", "job id"]
        elif any(k in action_hint for k in ["decision", "objective", "prediction", "optimiz"]):
            preferred = ["job feasibility", "machine assignment", "cycle time", "quality risk", "controller logs", "inspection results"]
        else:
            preferred = cnc_terms
        focus_text = ", ".join(preferred[:6])
        return f"For this CNC machining use case, apply this step to variables and records such as {focus_text}."

    if any(k in ps_l for k in ["patient", "hospital", "clinical", "medical", "healthcare"]):
        focus = ["patient state", "device readings", "alarm state", "treatment status", "timestamped events", "clinical records"]
        return f"For this healthcare use case, apply this step to variables and records such as {', '.join(focus[:6])}."

    if any(k in ps_l for k in ["warehouse", "fleet", "logistics", "shipment", "delivery"]):
        focus = ["asset status", "location", "order id", "shipment id", "throughput", "delay events"]
        return f"For this logistics use case, apply this step to variables and records such as {', '.join(focus[:6])}."

    generic = general_terms[:6] if general_terms else ["key variables", "states", "data sources", "timestamps"]
    if any(k in action_hint for k in ["variable", "state", "signal", "sensor", "data"]):
        preferred = generic or ["key variables", "states", "data sources", "timestamps"]
    elif any(k in action_hint for k in ["model", "replic", "sync", "scenario", "simulation"]):
        preferred = generic or ["physical-to-digital mapping", "state transitions", "timing", "output comparison"]
    elif any(k in action_hint for k in ["decision", "objective", "prediction", "optimiz"]):
        preferred = generic or ["decision variables", "objective logic", "comparison cases", "acceptance thresholds"]
    else:
        preferred = generic or ["system components", "states", "data flows", "decision needs"]
    focus_text = ", ".join(preferred[:6])
    return f"For this {sector} use case, apply this step to the specific assets, states, data streams, and decisions described in the use case. Example focus: {focus_text}."


def sanitize_domain_text(text: Any, sector: str, problem_statement: str, replacement_hint: str = "") -> str:
    s = normalize_ws(coerce_preferred_text(text))
    if not s:
        return ""
    if contains_unrelated_example_text(s, sector, problem_statement):
        repl = build_use_case_example(sector, problem_statement, replacement_hint)
        return repl
    return s


def audit_score_with_evidence(
    score: Any,
    evidence: Any,
    rationale: Any,
    sector: str = "",
    problem_statement: str = "",
) -> tuple[int, str, str]:
    try:
        score_int = int(score)
    except Exception:
        score_int = 0
    if score_int not in {0,1,2}:
        score_int = 0
    evidence_s = normalize_ws(evidence)
    rationale_s = normalize_ws(rationale)
    combined = f"{evidence_s} {rationale_s}".strip()
    if contains_unrelated_example_text(evidence_s, sector, problem_statement):
        evidence_s = ""
        score_int = min(score_int, 1)
    if contains_unrelated_example_text(rationale_s, sector, problem_statement):
        rationale_s = normalize_ws(UNRELATED_EXAMPLE_RE.sub('', rationale_s))
        score_int = min(score_int, 1)
    if NO_EVIDENCE_RE.search(combined):
        score_int = 0
    elif PARTIAL_EVIDENCE_RE.search(combined):
        score_int = min(score_int, 1)
    if not evidence_s:
        if NO_EVIDENCE_RE.search(rationale_s) or not rationale_s:
            score_int = 0
        else:
            score_int = min(score_int, 1)
    return score_int, evidence_s, rationale_s


def default_expected_evidence(action_text: str, sector: str, problem_statement: str) -> str:
    txt = action_text.lower()
    if 'data' in txt or 'map' in txt or 'source' in txt:
        return 'A reviewed data-source map, sample records, field definitions, and a traceability table.'
    if 'model' in txt or 'replic' in txt or 'scenario' in txt or 'simulation' in txt:
        return 'A model specification, test-run logs, comparison plots or tables, and calibration notes.'
    if 'threshold' in txt or 'error' in txt or 'accept' in txt:
        return 'A documented threshold table with rationale, example calculations, and review sign-off.'
    return 'A reviewable artifact, test record, or comparison table showing the step was completed for the use case.'


def fourr_postprocess_evaluated(evaluated: Dict[str, Any], sector: str, problem_statement: str) -> Dict[str, Any]:
    evaluated = dict(evaluated or {})
    evaluated['planning_summary'] = sanitize_domain_text(evaluated.get('planning_summary', ''), sector, problem_statement)
    risks = []
    for item in evaluated.get('risks_or_notes', []):
        txt = sanitize_domain_text(item, sector, problem_statement)
        if txt:
            risks.append(txt)
    evaluated['risks_or_notes'] = risks
    levels = evaluated.get('levels', {}) if isinstance(evaluated.get('levels', {}), dict) else {}
    for lid, lvl in levels.items():
        if not isinstance(lvl, dict):
            continue
        lvl['summary'] = sanitize_domain_text(lvl.get('summary', ''), sector, problem_statement)
        new_gates = []
        for gate in lvl.get('gate_scores', []):
            if not isinstance(gate, dict):
                continue
            score, evidence, rationale = audit_score_with_evidence(
                gate.get('score', 0),
                gate.get('evidence', ''),
                gate.get('rationale', ''),
                sector,
                problem_statement,
            )
            evidence = sanitize_domain_text(evidence, sector, problem_statement)
            rationale = sanitize_domain_text(rationale, sector, problem_statement)
            if score == 2 and not evidence:
                score = 1 if rationale else 0
            new_gates.append({
                'criterion': str(gate.get('criterion', '')).strip(),
                'score': score,
                'evidence': evidence,
                'rationale': rationale,
            })
        lvl['gate_scores'] = new_gates
        lvl['action_items_tailored'] = [sanitize_domain_text(x, sector, problem_statement) for x in lvl.get('action_items_tailored', []) if sanitize_domain_text(x, sector, problem_statement)]
    evaluated['levels'] = levels
    return evaluated


def fourr_postprocess_tailored_action_items(tailored: Dict[str, Any], sector: str, problem_statement: str) -> Dict[str, Any]:
    if not isinstance(tailored, dict):
        return {}
    out = dict(tailored)
    out['section1_4r_target_summary'] = sanitize_domain_text(out.get('section1_4r_target_summary', ''), sector, problem_statement)
    out['section2_planning_summary'] = sanitize_domain_text(out.get('section2_planning_summary', ''), sector, problem_statement)
    out['section3_desired_future_vision_vs_current_feasible_target'] = sanitize_domain_text(out.get('section3_desired_future_vision_vs_current_feasible_target', ''), sector, problem_statement)
    items = []
    for item in out.get('section4_tailored_4r_action_items', []):
        if not isinstance(item, dict):
            continue
        action_item = sanitize_domain_text(item.get('action_item', ''), sector, problem_statement)
        what = sanitize_domain_text(item.get('what_to_do', ''), sector, problem_statement, action_item)
        why = sanitize_domain_text(item.get('why_it_matters', ''), sector, problem_statement)
        example = sanitize_domain_text(item.get('use_case_specific_example', ''), sector, problem_statement, action_item)
        if not example:
            example = build_use_case_example(sector, problem_statement, action_item)
        req = [sanitize_domain_text(x, sector, problem_statement) for x in item.get('required_data_or_inputs', []) if sanitize_domain_text(x, sector, problem_statement)]
        expected = sanitize_domain_text(item.get('expected_output_or_evidence', ''), sector, problem_statement)
        if not expected:
            expected = default_expected_evidence(action_item or what, sector, problem_statement)
        deps = sanitize_domain_text(item.get('dependencies_or_gaps', ''), sector, problem_statement)
        items.append({
            'fourr_level': str(item.get('fourr_level', '')).strip(),
            'action_item': action_item,
            'what_to_do': what,
            'why_it_matters': why,
            'use_case_specific_example': example,
            'required_data_or_inputs': req,
            'expected_output_or_evidence': expected,
            'dependencies_or_gaps': deps,
        })
    out['section4_tailored_4r_action_items'] = items
    out['section5_priority_action_list'] = [sanitize_domain_text(x, sector, problem_statement) for x in out.get('section5_priority_action_list', []) if sanitize_domain_text(x, sector, problem_statement)]
    out['section6_missing_information_or_data_gaps'] = [sanitize_domain_text(x, sector, problem_statement) for x in out.get('section6_missing_information_or_data_gaps', []) if sanitize_domain_text(x, sector, problem_statement)]
    out['section7_future_work_beyond_current_level'] = [sanitize_domain_text(x, sector, problem_statement) for x in out.get('section7_future_work_beyond_current_level', []) if sanitize_domain_text(x, sector, problem_statement)]
    return out


def fourr_postprocess_result(result: Dict[str, Any], sector: str, problem_statement: str) -> Dict[str, Any]:
    result = dict(result or {})
    result['sector'] = sector
    result['problem_statement'] = problem_statement
    for key in ['planning_summary', 'target_action_summary', 'tailored_planning_summary', 'desired_future_vision_vs_current_feasible_target']:
        result[key] = sanitize_domain_text(result.get(key, ''), sector, problem_statement)
    result['criteria_supported_for_target'] = [sanitize_domain_text(x, sector, problem_statement) for x in result.get('criteria_supported_for_target', []) if sanitize_domain_text(x, sector, problem_statement)]
    result['gaps_to_reach_target'] = [sanitize_domain_text(x, sector, problem_statement) for x in result.get('gaps_to_reach_target', []) if sanitize_domain_text(x, sector, problem_statement)]
    result['action_items_to_reach_target'] = [sanitize_domain_text(x, sector, problem_statement) for x in result.get('action_items_to_reach_target', []) if sanitize_domain_text(x, sector, problem_statement)]
    result['risks_or_notes'] = [sanitize_domain_text(x, sector, problem_statement) for x in result.get('risks_or_notes', []) if sanitize_domain_text(x, sector, problem_statement)]
    return result


def infer_related_4s_level(action_text: str) -> str:
    txt = action_text.lower()
    if any(k in txt for k in ['predict', 'forecast', 'remaining useful life', 'rul', 'future behavior']):
        return 'S3'
    if any(k in txt for k in ['optimiz', 'prescrib', 'objective function', 'decision rule', 'select actions']):
        return 'S4'
    if any(k in txt for k in ['model', 'mapping', 'map physical', 'representation', 'platform']):
        return 'S1'
    return 'S2'


def extract_fourr_action_titles(fourr_result: Dict[str, Any]) -> List[str]:
    titles: List[str] = []
    tailored = fourr_result.get('tailored_action_items', {}) if isinstance(fourr_result.get('tailored_action_items', {}), dict) else {}
    for row in tailored.get('section4_tailored_4r_action_items', []):
        if isinstance(row, dict):
            title = normalize_ws(row.get('action_item', ''))
            if title:
                titles.append(title)
    if not titles:
        for item in fourr_result.get('action_items_to_reach_target', []):
            title = normalize_ws(item.split(':',1)[0])
            if title:
                titles.append(title)
    return list(dict.fromkeys(titles))


def fourr_level_rank(level: str) -> int:
    return {"R1": 1, "R2": 2, "R3": 3, "R4": 4}.get(str(level).strip().upper(), 99)


def extract_fourr_action_rows(fourr_result: Dict[str, Any], max_level: str = "") -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    tailored = fourr_result.get('tailored_action_items', {}) if isinstance(fourr_result.get('tailored_action_items', {}), dict) else {}
    max_rank = fourr_level_rank(max_level) if str(max_level).strip() else 99
    for row in tailored.get('section4_tailored_4r_action_items', []):
        if not isinstance(row, dict):
            continue
        level = normalize_ws(row.get('fourr_level', ''))
        if level and fourr_level_rank(level) > max_rank:
            continue
        title = normalize_ws(row.get('action_item', ''))
        if not title:
            continue
        rows.append({
            'fourr_level': level,
            'action_item': title,
            'what_to_do': normalize_ws(row.get('what_to_do', '')),
            'why_it_matters': normalize_ws(row.get('why_it_matters', '')),
            'use_case_specific_example': normalize_ws(row.get('use_case_specific_example', '')),
            'required_data_or_inputs': [normalize_ws(x) for x in row.get('required_data_or_inputs', []) if normalize_ws(x)],
            'expected_output_or_evidence': normalize_ws(row.get('expected_output_or_evidence', '')),
            'dependencies_or_gaps': normalize_ws(row.get('dependencies_or_gaps', '')),
        })
    if rows:
        return rows
    for item in fourr_result.get('action_items_to_reach_target', []):
        title = normalize_ws(str(item).split(':', 1)[0])
        if title:
            rows.append({
                'fourr_level': '',
                'action_item': title,
                'what_to_do': normalize_ws(item),
                'why_it_matters': '',
                'use_case_specific_example': '',
                'required_data_or_inputs': [],
                'expected_output_or_evidence': '',
                'dependencies_or_gaps': '',
            })
    return rows


def fours_postprocess_result(result: Dict[str, Any], fourr_result: Dict[str, Any], sector: str, problem_statement: str) -> Dict[str, Any]:
    result = dict(result or {})
    current_4r_target = get_current_4r_target_level_for_dtv(fourr_result)
    level_name_map = {"S1": "Modeling", "S2": "Analyzing", "S3": "Predicting", "S4": "Prescribing"}

    # Force 4S to stay aligned with the recommended 4R target.
    if current_4r_target == "R1":
        result["recommended_4s_level"] = "S1"
        result["recommended_4s_name"] = level_name_map["S1"]
        result["why_s2_is_the_current_target"] = result.get("why_s2_is_the_current_target", "") or "S2 is near-term next work once the use case has an initial model structure, explicit comparison cases, and enough recorded behavior to support analysis."
        result["why_s3_is_future_work"] = result.get("why_s3_is_future_work", "") or "Predictive simulation is future work until the build moves beyond representation into a validated replication boundary."
        result["why_s4_is_future_work"] = result.get("why_s4_is_future_work", "") or "Prescriptive simulation is future work until prediction targets, decision rules, and objective functions are explicitly defined."
        result["current_feasible_simulation_target_vs_future_simulation_vision"] = (
            "The recommended 4R target is R1, so the current feasible simulation target is S1 Modeling. "
            "Near-term work can prepare for S2 Analyzing by defining a model structure, inputs, outputs, and comparison cases, but the current boundary should not be presented as analysis unless R2 replication evidence is in place."
        )
    elif current_4r_target == "R2":
        # Keep the classification at or below S2.
        if str(result.get("recommended_4s_level", "")).strip().upper() not in {"S1", "S2"}:
            result["recommended_4s_level"] = "S2"
            result["recommended_4s_name"] = level_name_map["S2"]
        result["current_feasible_simulation_target_vs_future_simulation_vision"] = (
            "The recommended 4R target is R2, so the current feasible simulation target should focus on S1 Modeling and S2 Analyzing. "
            "The model can represent the system structure and compare recorded or live behavior against virtual behavior, but predictive or prescriptive simulation should remain future work unless higher-level evidence is explicitly defined."
        )
    elif current_4r_target == "R3":
        if str(result.get("recommended_4s_level", "")).strip().upper() not in {"S1", "S2", "S3"}:
            result["recommended_4s_level"] = "S3"
            result["recommended_4s_name"] = level_name_map["S3"]
    elif current_4r_target == "R4":
        if str(result.get("recommended_4s_level", "")).strip().upper() not in {"S1", "S2", "S3", "S4"}:
            result["recommended_4s_level"] = "S4"
            result["recommended_4s_name"] = level_name_map["S4"]

    for key in [
        'section1_4r_context_summary','reason','why_s1_is_included','why_s2_is_the_current_target',
        'why_s3_is_future_work','why_s4_is_future_work','current_feasible_simulation_target_vs_future_simulation_vision'
    ]:
        result[key] = sanitize_domain_text(result.get(key, ''), sector, problem_statement)
    rows = []
    for row in result.get('interpretation_table', []):
        if not isinstance(row, dict):
            continue
        row = dict(row)
        row['use_case_specific_interpretation'] = sanitize_domain_text(row.get('use_case_specific_interpretation', ''), sector, problem_statement, row.get('level_id',''))
        row['required_data_or_model_evidence'] = sanitize_domain_text(row.get('required_data_or_model_evidence', ''), sector, problem_statement)
        row['notes_or_gaps'] = sanitize_domain_text(row.get('notes_or_gaps', ''), sector, problem_statement)
        if not row['use_case_specific_interpretation']:
            row['use_case_specific_interpretation'] = build_use_case_example(sector, problem_statement, row.get('level_name', row.get('level_id','')))
        # Enforce row needed labels to stay aligned with current 4R target.
        lid = str(row.get('level_id', '')).strip().upper()
        if current_4r_target == "R1":
            row['needed'] = 'Yes' if lid == 'S1' else 'Future'
        elif current_4r_target == "R2":
            row['needed'] = 'Yes' if lid in {'S1','S2'} else 'Future'
        rows.append(row)
    result['interpretation_table'] = rows
    links = []
    seen = set()
    for row in result.get('connection_to_4r_action_items', []):
        if not isinstance(row, dict):
            continue
        row = dict(row)
        row['existing_4r_action_item'] = sanitize_domain_text(row.get('existing_4r_action_item', ''), sector, problem_statement)
        row['how_4s_modifies_or_clarifies_the_action_item'] = sanitize_domain_text(row.get('how_4s_modifies_or_clarifies_the_action_item', ''), sector, problem_statement)
        row['use_case_specific_example'] = sanitize_domain_text(row.get('use_case_specific_example', ''), sector, problem_statement, row.get('existing_4r_action_item',''))
        if current_4r_target == "R1":
            row['related_4s_level'] = 'S1'
            if 'near-term next' not in row['how_4s_modifies_or_clarifies_the_action_item'].lower():
                row['how_4s_modifies_or_clarifies_the_action_item'] = 'Keep this action item at S1 modeling for the current boundary. Use it to define the system representation, inputs, outputs, and comparison cases that would later support S2 analysis.'
        key = row['existing_4r_action_item']
        if key and key not in seen:
            seen.add(key)
            links.append(row)
    action_titles = extract_fourr_action_titles(fourr_result)
    target_min = min(5, max(4, len(action_titles))) if action_titles else 0
    for title in action_titles:
        if len(links) >= target_min:
            break
        if title in seen:
            continue
        lvl = infer_related_4s_level(title)
        if current_4r_target == "R1" and lvl not in {"S1"}:
            lvl = "S1"
        elif current_4r_target == "R2" and lvl not in {"S1","S2"}:
            lvl = "S2"
        clarify = 'Use simulation to structure the system representation needed by this action item. At the current boundary this is S1 work, with S2 analysis prepared as near-term next work once comparison cases are defined.' if current_4r_target == "R1" else 'Use simulation to represent and analyze the current system behavior needed by this action item, without expanding into future predictive or prescriptive logic unless that higher level is explicitly supported.'
        links.append({
            'existing_4r_action_item': title,
            'related_4s_level': lvl,
            'how_4s_modifies_or_clarifies_the_action_item': clarify,
            'use_case_specific_example': build_use_case_example(sector, problem_statement, title),
        })
        seen.add(title)
    result['connection_to_4r_action_items'] = links
    result['implementation_guidance'] = [sanitize_domain_text(x, sector, problem_statement) for x in result.get('implementation_guidance', []) if sanitize_domain_text(x, sector, problem_statement)]
    result['gaps_before_advancing_to_higher_4s_levels'] = [sanitize_domain_text(x, sector, problem_statement) for x in result.get('gaps_before_advancing_to_higher_4s_levels', []) if sanitize_domain_text(x, sector, problem_statement)]
    return result

def default_acceptance_for_dtv(text: str, current_target_level: str) -> str:
    txt = text.lower()
    lvl = str(current_target_level).strip().upper()
    if lvl == 'R1':
        if 'state' in txt or 'status' in txt:
            return 'State or status labels match the authoritative source for >=95% of sampled records.'
        if 'data' in txt or 'stream' in txt or 'mapping' in txt or 'schema' in txt or 'timestamp' in txt:
            return 'Missing data rate is <=5% for required streams during pilot collection, and >=95% of sampled records are traceable by timestamp or entity ID.'
        return 'Required variables, schemas, and boundaries are documented and approved, and >=95% of sampled records can be interpreted without manual relabeling.'
    if 'timestamp' in txt or 'latency' in txt or 'sync' in txt or 'alignment' in txt:
        return 'Data latency remains below the agreed update limit and >=95% of sampled records align by timestamp or entity ID.'
    if 'state' in txt or 'transition' in txt:
        return 'State or event transitions match the authoritative source with >=95% accuracy across sampled test cases.'
    if 'cycle' in txt or 'output' in txt or 'model' in txt or 'replic' in txt or 'deviation' in txt:
        return 'Key replicated outputs remain within the agreed deviation threshold, for example <=10% for >=90% of sampled test cases unless the use case requires stricter bounds.'
    if 'data' in txt or 'stream' in txt or 'mapping' in txt:
        return 'Missing data rate is <=5% for required streams and every required field is traceable to a source record, state, or decision.'
    return 'Acceptance criteria are documented with measurable thresholds for correctness, traceability, and representational accuracy.'

def enforce_r1_dtv_boundary(text: Any) -> str:
    s = normalize_ws(text)
    if not s:
        return ""
    low = s.lower()
    if any(k in low for k in ['predictive analytics', 'predict tool', 'remaining useful life', 'virtual model outputs', 'real system outputs', 'predict machine', 'optimization']):
        return 'At the current R1 boundary, focus on whether the selected variables, data sources, schemas, and system boundaries accurately reflect the real system and are useful for the intended decisions.'
    return s


def dtv_postprocess_result(result: Dict[str, Any], fourr_result: Dict[str, Any], sector: str, problem_statement: str, current_target_level: str) -> Dict[str, Any]:
    result = dict(result or {})
    for key in ['section1_4r_context_summary','section2_dtv_role_for_this_use_case','section3_current_target_trust_boundary']:
        result[key] = sanitize_domain_text(result.get(key, ''), sector, problem_statement)
        if str(current_target_level).strip().upper() == 'R1':
            result[key] = enforce_r1_dtv_boundary(result[key]) if key == 'section3_current_target_trust_boundary' else result[key]
    rows = []
    for row in result.get('dtv_development_and_vv_table', []):
        if not isinstance(row, dict):
            continue
        row = dict(row)
        for key in ['existing_4r_action_item','dtv_stage_or_focus_area','what_should_be_verified','what_should_be_validated','evidence_to_collect','suggested_acceptance_criteria','use_case_specific_example']:
            row[key] = sanitize_domain_text(row.get(key, ''), sector, problem_statement, row.get('existing_4r_action_item',''))
            if str(current_target_level).strip().upper() == 'R1' and key in {'what_should_be_validated','use_case_specific_example'}:
                row[key] = enforce_r1_dtv_boundary(row[key])
        if not row['use_case_specific_example']:
            row['use_case_specific_example'] = build_use_case_example(sector, problem_statement, row.get('existing_4r_action_item',''))
        if not row['suggested_acceptance_criteria'] or GENERIC_ACTION_RE.search(row['suggested_acceptance_criteria']):
            row['suggested_acceptance_criteria'] = default_acceptance_for_dtv(' '.join([row['existing_4r_action_item'], row['what_should_be_verified'], row['what_should_be_validated']]), current_target_level)
        if not row['evidence_to_collect']:
            row['evidence_to_collect'] = default_expected_evidence(row.get('existing_4r_action_item',''), sector, problem_statement)
        rows.append(row)
    result['dtv_development_and_vv_table'] = rows
    result['verification_guidance'] = [sanitize_domain_text(x, sector, problem_statement) for x in result.get('verification_guidance', []) if sanitize_domain_text(x, sector, problem_statement)]
    result['validation_guidance'] = [sanitize_domain_text(x, sector, problem_statement) for x in result.get('validation_guidance', []) if sanitize_domain_text(x, sector, problem_statement)]
    if str(current_target_level).strip().upper() == 'R1':
        result['validation_guidance'] = [enforce_r1_dtv_boundary(x) for x in result.get('validation_guidance', [])]
    result['gaps_and_risks'] = [sanitize_domain_text(x, sector, problem_statement) for x in result.get('gaps_and_risks', []) if sanitize_domain_text(x, sector, problem_statement)]
    if not result.get('dtv_aligned_action_items') or any(contains_unrelated_example_text(x, sector, problem_statement) for x in result.get('dtv_aligned_action_items', [])):
        regenerated = []
        for row in rows[:6]:
            regenerated.append(f"{row.get('existing_4r_action_item', 'Check the digital twin step')}: Verify {row.get('what_should_be_verified', '').lower() or 'the component was built correctly'}. Validate {row.get('what_should_be_validated', '').lower() or 'it represents the real system for the intended use'}. Evidence: {row.get('evidence_to_collect', '')}")
        result['dtv_aligned_action_items'] = regenerated
    else:
        result['dtv_aligned_action_items'] = [sanitize_domain_text(x, sector, problem_statement) for x in result.get('dtv_aligned_action_items', []) if sanitize_domain_text(x, sector, problem_statement)]
    result['section9_future_dtv_work_beyond_current_target'] = [sanitize_domain_text(x, sector, problem_statement) for x in result.get('section9_future_dtv_work_beyond_current_target', []) if sanitize_domain_text(x, sector, problem_statement)]
    return result

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

    def priority_from_text(text: str) -> str:
        low = text.lower()
        bracket = re.search(r"[\[(]\s*([ehf])\s*[\])]", text, flags=re.I)
        if bracket:
            return bracket.group(1).upper()

        cells = [c.strip().lower() for c in text.strip().strip("|").split("|")]
        for cell in reversed(cells):
            cleaned = re.sub(r"[*_`]", "", cell).strip()
            if cleaned in {"e", "essential"}:
                return "E"
            if cleaned in {"h", "high", "high value", "high-value"}:
                return "H"
            if cleaned in {"f", "future", "future enhancement", "future-enhancement"}:
                return "F"

        if re.search(r"\bessential\b|\bmust[-\s]?have\b", low):
            return "E"
        if re.search(r"\bhigh[-\s]?value\b", low):
            return "H"
        if re.search(r"\bfuture\b|\benhancement\b|\blater\b", low):
            return "F"
        return ""

    priorities: Dict[str, str] = {}
    lines = md.splitlines()
    cap_pat = re.compile(r"\b([A-Z]{2}\.[A-Z0-9]{2})\b")

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

    # Markdown tables often put the capability code in one cell and the priority
    # in a different cell, optionally bolded. Parse priority from the whole row.
    for line in lines:
        caps_in_line = cap_pat.findall(line)
        if not caps_in_line:
            continue
        pri = priority_from_text(line)
        if not pri:
            continue
        for cap_id in caps_in_line:
            set_pri(priorities, cap_id, pri)

    # Section bullet lists
    section_specs = [
        ("Essential (must have)", "E"),
        ("High Value (important for full business value)", "H"),
        ("Future Enhancement (beneficial for long-term evolution)", "F"),
    ]

    def find_heading_index(heading_text: str) -> Optional[int]:
        expected_priority = priority_from_text(heading_text)
        for i, line in enumerate(lines):
            stripped = line.strip()
            if not stripped.startswith("#"):
                continue
            heading = stripped.lstrip("#").strip()
            if heading.lower() == heading_text.strip().lower():
                return i
            if expected_priority and priority_from_text(heading) == expected_priority:
                return i
        return None

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


def apply_capability_priority_floor(
    priorities: Dict[str, str],
    *,
    sector: str,
    problem_statement: str,
) -> tuple[Dict[str, str], Dict[str, Dict[str, str]]]:
    """Stabilize Step 2's capability profile from explicit use-case language.

    The local model still selects and explains capabilities, but these floors keep
    core capabilities from drifting between priority levels when the user's own
    problem statement clearly requires them.
    """
    out = dict(priorities or {})
    applied: Dict[str, Dict[str, str]] = {}
    text = f"{sector} {problem_statement}".lower()

    def has_any(*patterns: str) -> bool:
        return any(re.search(pattern, text, flags=re.I) for pattern in patterns)

    def promote(cap_id: str, priority: str, reason: str) -> None:
        priority = priority.upper()
        if priority not in {"E", "H", "F"}:
            return
        current = out.get(cap_id, "")
        if {"": 0, "F": 1, "H": 2, "E": 3}.get(priority, 0) > {"": 0, "F": 1, "H": 2, "E": 3}.get(current, 0):
            out[cap_id] = priority
            applied[cap_id] = {
                "from": current,
                "to": priority,
                "reason": reason,
            }

    if has_any(r"\bdata[-\s]?driven\b", r"\breal[-\s]?time\b", r"\bmonitor", r"\bpredict", r"\banaly"):
        promote("DS.AI", "E", "Use case requires data acquisition or data-driven analysis.")
        promote("DS.TR", "E", "Use case requires usable data for analysis, monitoring, prediction, or reporting.")
        promote("UX.BV", "E", "Use case requires basic human-readable outputs or insight.")

    if has_any(r"\breal[-\s]?time\b", r"\bcontinuous", r"\bstream", r"\blow[-\s]?latency\b", r"\bupdates?\b"):
        promote("DS.ST", "E", "Use case requires continuous or real-time data movement.")
        promote("DS.RT", "E", "Use case requires low-latency processing or action.")
        promote("DS.AS", "E", "Use case requires distributing updates or events across services.")
        promote("UX.RM", "E", "Use case requires continuously updated monitoring.")

    if has_any(r"\bsensor", r"\biot\b", r"\bscada\b", r"\bplc\b", r"\bmachine\b", r"\bequipment\b", r"\basset\b", r"\bdevice\b"):
        promote("IR.IO", "E", "Use case involves equipment, devices, sensors, or control-system data.")
        promote("MG.DM", "E", "Use case involves connected equipment, devices, or assets that need lifecycle management.")

    if has_any(r"\berp\b", r"\bmes\b", r"\bcmms\b", r"\beam\b", r"\benterprise\b", r"\bscheduling software\b", r"\bbusiness system"):
        promote("IR.ET", "E", "Use case requires enterprise-system integration.")

    if has_any(r"\bcad\b", r"\bcam\b", r"\bbim\b", r"\bengineering\b", r"\bcnc\b", r"\bmachining\b", r"\bproduction job\b"):
        promote("IR.EG", "E", "Use case references engineering, production, or machining systems.")

    if has_any(r"\bschedule", r"\boptim", r"\borchestrat", r"\bworkflow", r"\bautomate", r"\bdecision[-\s]?making\b"):
        promote("IC.OS", "E", "Use case requires scheduling, optimization, orchestration, or automation.")

    if has_any(r"\bsearch\b", r"\bquery\b", r"\bretrieve\b", r"\binsight\b", r"\bdetermine whether\b", r"\bcapability and capacity\b"):
        promote("IC.SR", "E", "Use case requires finding or retrieving operational evidence for decisions.")

    if has_any(r"\bai\b", r"\bmachine learning\b", r"\bpredict", r"\bforecast", r"\bremaining useful life\b", r"\brul\b", r"\badaptive\b"):
        promote("IC.AI", "E", "Use case explicitly requires AI, learning, prediction, or adaptive reasoning.")
        promote("IC.PR", "H", "Use case includes prediction or forecasting needs.")
        promote("DS.BP", "E", "Use case likely needs historical or batch records to support prediction and validation.")
        promote("DS.SG", "H", "Predictive use cases may benefit from synthetic data for model testing or coverage.")

    if has_any(r"\bsimulation\b", r"\bmodel\b", r"\bwhat[-\s]?if\b", r"\bscenario\b", r"\breplicat"):
        promote("IC.SM", "E", "Use case explicitly requires modeling, simulation, scenario work, or replication.")
        promote("DS.SR", "F", "Simulation-heavy use cases may later need a simulation model repository.")

    if has_any(r"\bmonitor", r"\bhealth\b", r"\bdegradation\b", r"\bmaintenance\b", r"\bavailability\b", r"\bperformance\b"):
        promote("MG.SM", "E", "Use case requires monitoring system, asset, or operational health.")
        promote("UX.DB", "H", "Monitoring use cases benefit from dashboard views for KPIs and status.")

    if has_any(r"\bkpi\b", r"\bquality\b", r"\bcost\b", r"\btime\b", r"\breport", r"\bsummary\b", r"\bthroughput\b"):
        promote("DS.AG", "H", "Use case includes summarized operating, KPI, quality, cost, time, or throughput views.")

    if has_any(r"\bsecurity\b", r"\bprivacy\b", r"\bconfidential", r"\bunauthorized\b", r"\baccess\b", r"\bdata\b"):
        promote("TW.SC", "E", "Use case uses operational data and needs basic digital-twin security.")
    if has_any(r"\bprivacy\b", r"\bpersonal\b", r"\bgdpr\b", r"\bphi\b", r"\bpii\b"):
        promote("TW.PR", "H", "Use case includes privacy-sensitive data or compliance concerns.")

    return out, applied


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


def _get_json(url: str, timeout: float) -> Dict[str, Any]:
    req = Request(
        url=url,
        headers={"Authorization": "Bearer ollama"},
        method="GET",
    )
    with urlopen(req, timeout=timeout) as resp:
        body = resp.read().decode("utf-8", errors="replace")
        return json.loads(body)


def _looks_like_unsupported_payload_field_error(err: Exception) -> bool:
    msg = str(err).lower()
    option_words = ("seed", "top_p", "options", "num_thread", "unsupported", "unknown", "unrecognized", "invalid parameter")
    return "http 400" in msg and any(word in msg for word in option_words)


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

    if temperature <= 0.0:
        payload.update(DETERMINISTIC_COMPLETION_FIELDS)
    if OLLAMA_RUNTIME_OPTIONS:
        payload["options"] = dict(OLLAMA_RUNTIME_OPTIONS)

    try:
        resp = _post_json(endpoint, payload, timeout=timeout, retries=retries)
    except RuntimeError as e:
        if _looks_like_unsupported_payload_field_error(e):
            fallback_payload = {
                k: v for k, v in payload.items()
                if k not in DETERMINISTIC_COMPLETION_FIELDS and k != "options"
            }
            resp = _post_json(endpoint, fallback_payload, timeout=timeout, retries=retries)
        else:
            raise

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
# Hardware-aware model selection
# -----------------------------

def _gb_from_bytes(value: int) -> float:
    return round(float(value) / float(1024 ** 3), 1)


def detect_total_ram_gb() -> Optional[float]:
    if platform.system().lower() == "windows":
        class MEMORYSTATUSEX(ctypes.Structure):
            _fields_ = [
                ("dwLength", ctypes.c_ulong),
                ("dwMemoryLoad", ctypes.c_ulong),
                ("ullTotalPhys", ctypes.c_ulonglong),
                ("ullAvailPhys", ctypes.c_ulonglong),
                ("ullTotalPageFile", ctypes.c_ulonglong),
                ("ullAvailPageFile", ctypes.c_ulonglong),
                ("ullTotalVirtual", ctypes.c_ulonglong),
                ("ullAvailVirtual", ctypes.c_ulonglong),
                ("sullAvailExtendedVirtual", ctypes.c_ulonglong),
            ]

            def __init__(self) -> None:
                super().__init__()
                self.dwLength = ctypes.sizeof(self)

        status = MEMORYSTATUSEX()
        if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
            return _gb_from_bytes(status.ullTotalPhys)

    if hasattr(os, "sysconf"):
        try:
            pages = os.sysconf("SC_PHYS_PAGES")
            page_size = os.sysconf("SC_PAGE_SIZE")
            if isinstance(pages, int) and isinstance(page_size, int):
                return _gb_from_bytes(pages * page_size)
        except (OSError, ValueError):
            pass

    sysctl = shutil.which("sysctl")
    if sysctl:
        try:
            result = subprocess.run(
                [sysctl, "-n", "hw.memsize"],
                capture_output=True,
                text=True,
                timeout=3,
                check=False,
            )
            value = result.stdout.strip()
            if value.isdigit():
                return _gb_from_bytes(int(value))
        except Exception:
            pass

    return None


def _detect_nvidia_vram_gb() -> Optional[float]:
    exe = shutil.which("nvidia-smi")
    if not exe:
        return None

    try:
        result = subprocess.run(
            [exe, "--query-gpu=memory.total", "--format=csv,noheader,nounits"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except Exception:
        return None

    values: List[float] = []
    for line in result.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            values.append(float(line.split()[0]) / 1024.0)
        except ValueError:
            continue

    return round(max(values), 1) if values else None


def _detect_windows_adapter_ram_gb() -> Optional[float]:
    if platform.system().lower() != "windows":
        return None

    exe = shutil.which("wmic")
    if not exe:
        return None

    try:
        result = subprocess.run(
            [exe, "path", "win32_VideoController", "get", "AdapterRAM", "/value"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except Exception:
        return None

    values: List[float] = []
    for match in re.findall(r"AdapterRAM=(\d+)", result.stdout):
        try:
            ram_bytes = int(match)
        except ValueError:
            continue
        if ram_bytes > 0:
            values.append(float(ram_bytes) / float(1024 ** 3))

    return round(max(values), 1) if values else None


def detect_gpu_vram_gb() -> Optional[float]:
    nvidia = _detect_nvidia_vram_gb()
    if nvidia is not None:
        return nvidia
    return _detect_windows_adapter_ram_gb()


def detect_hardware_profile() -> Dict[str, Any]:
    return {
        "system": platform.system() or "unknown",
        "machine": platform.machine() or "unknown",
        "cpu_logical": os.cpu_count() or 1,
        "ram_gb": detect_total_ram_gb(),
        "gpu_vram_gb": detect_gpu_vram_gb(),
    }


def is_apple_silicon(hardware: Dict[str, Any]) -> bool:
    system = str(hardware.get("system") or "").lower()
    machine = str(hardware.get("machine") or "").lower()
    return system == "darwin" and machine in {"arm64", "aarch64"}


def max_tier_for_resource_profile(resource_profile: str) -> int:
    profile = (resource_profile or "safe").strip().lower()
    if profile == "performance":
        return 3
    if profile == "balanced":
        return 2
    return 1


def recommended_model_tier_index(hardware: Dict[str, Any], resource_profile: str = "safe") -> int:
    ram = hardware.get("ram_gb")
    cpu = int(hardware.get("cpu_logical") or 1)
    vram = float(hardware.get("gpu_vram_gb") or 0.0)
    max_tier = max_tier_for_resource_profile(resource_profile)

    if ram is None:
        return min(1, max_tier)

    ram = float(ram)

    if is_apple_silicon(hardware):
        if ram >= 24.0 and cpu >= 8:
            return min(1, max_tier)
        if ram >= 12.0:
            return min(1, max_tier)
        return 0

    detected_tier = 0
    if vram >= 20.0 or (ram >= 96.0 and cpu >= 16):
        detected_tier = 3
    elif vram >= 10.0 or (ram >= 32.0 and cpu >= 8):
        detected_tier = 2
    elif vram >= 6.0 or (ram >= 10.0 and cpu >= 4):
        detected_tier = 1
    return min(detected_tier, max_tier)


def build_ollama_runtime_options(
    *,
    hardware: Dict[str, Any],
    resource_profile: str,
    requested_num_thread: int,
) -> Dict[str, Any]:
    if requested_num_thread < 0:
        return {}
    if requested_num_thread > 0:
        return {"num_thread": max(1, requested_num_thread)}

    cpu = int(hardware.get("cpu_logical") or 1)
    profile = (resource_profile or "safe").strip().lower()
    if cpu <= 2:
        threads = 1
    elif profile == "performance":
        threads = min(max(2, cpu - 2), 12)
    elif profile == "balanced":
        threads = min(max(2, cpu // 2), 8)
    else:
        threads = min(max(2, cpu // 3), 6)
    return {"num_thread": threads}


def ollama_native_api_url(base_url: str, endpoint: str) -> str:
    parsed = urlparse(base_url)
    path = parsed.path.rstrip("/")
    if path.endswith("/v1"):
        path = path[:-3]
    if path.endswith("/api"):
        path = path[:-4]
    path = f"{path}/api/{endpoint.lstrip('/')}"
    return urlunparse(parsed._replace(path=path, params="", query="", fragment=""))


def get_installed_ollama_models(base_url: str, timeout: float) -> List[str]:
    tags_url = ollama_native_api_url(base_url, "tags")
    resp = _get_json(tags_url, timeout=min(max(timeout, 1.0), 5.0))
    models = resp.get("models", [])
    if not isinstance(models, list):
        return []

    names: List[str] = []
    for entry in models:
        if not isinstance(entry, dict):
            continue
        name = str(entry.get("name") or entry.get("model") or "").strip()
        if name:
            names.append(name)
    return names


def _find_installed_model(candidates: List[str], installed_models: List[str]) -> Optional[str]:
    installed_by_lower = {name.lower(): name for name in installed_models}
    for candidate in candidates:
        found = installed_by_lower.get(candidate.lower())
        if found:
            return found

    for candidate in candidates:
        candidate_lower = candidate.lower()
        for installed in installed_models:
            if installed.lower().startswith(candidate_lower):
                return installed

    return None


def choose_auto_model(
    *,
    hardware: Dict[str, Any],
    installed_models: List[str],
    resource_profile: str,
) -> Dict[str, Any]:
    tier_index = recommended_model_tier_index(hardware, resource_profile=resource_profile)
    tier = MODEL_SELECTION_TIERS[tier_index]
    warnings: List[str] = []

    selected = _find_installed_model(tier["models"], installed_models)
    selection_source = "installed_recommended_tier"

    if selected is None and installed_models:
        lower_tier_models: List[str] = []
        for idx in range(tier_index, -1, -1):
            lower_tier_models.extend(MODEL_SELECTION_TIERS[idx]["models"])
        selected = _find_installed_model(lower_tier_models, installed_models)
        selection_source = "installed_lower_or_equal_tier"

    if selected is None:
        selected = str(tier["primary"])
        selection_source = "recommended_not_verified_installed"
        if installed_models:
            warnings.append(
                f"No configured model for the detected tier is installed; using recommended model name {selected}."
            )
        else:
            warnings.append(
                f"Could not verify installed Ollama models; using recommended model name {selected}."
            )

    return {
        "auto": True,
        "selected_model": selected,
        "selection_source": selection_source,
        "resource_profile": resource_profile,
        "recommended_tier": tier["label"],
        "recommended_model": tier["primary"],
        "tier_reason": tier["reason"],
        "hardware": hardware,
        "installed_models_seen": installed_models[:25],
        "warnings": warnings,
    }


def resolve_model_for_hardware(
    *,
    requested_model: str,
    base_url: str,
    timeout: float,
    resource_profile: str,
    requested_num_thread: int,
) -> Dict[str, Any]:
    requested_model = (requested_model or "auto").strip()
    if requested_model.lower() != "auto":
        hardware = detect_hardware_profile()
        return {
            "auto": False,
            "selected_model": requested_model,
            "selection_source": "user_override",
            "resource_profile": resource_profile,
            "recommended_tier": "",
            "recommended_model": "",
            "tier_reason": "User supplied --model, so hardware auto-selection was skipped.",
            "hardware": hardware,
            "installed_models_seen": [],
            "runtime_options": build_ollama_runtime_options(
                hardware=hardware,
                resource_profile=resource_profile,
                requested_num_thread=requested_num_thread,
            ),
            "warnings": [],
        }

    hardware = detect_hardware_profile()
    installed_models: List[str] = []
    warnings: List[str] = []
    try:
        installed_models = get_installed_ollama_models(base_url, timeout=timeout)
    except Exception as e:
        warnings.append(f"Could not query installed Ollama models from {ollama_native_api_url(base_url, 'tags')}: {e}")

    selection = choose_auto_model(
        hardware=hardware,
        installed_models=installed_models,
        resource_profile=resource_profile,
    )
    selection["runtime_options"] = build_ollama_runtime_options(
        hardware=hardware,
        resource_profile=resource_profile,
        requested_num_thread=requested_num_thread,
    )
    selection["warnings"] = warnings + selection.get("warnings", [])
    return selection


def print_model_selection(selection: Dict[str, Any]) -> None:
    hardware = selection.get("hardware", {})
    ram = hardware.get("ram_gb")
    vram = hardware.get("gpu_vram_gb")
    ram_text = f"{ram} GB" if ram is not None else "unknown"
    vram_text = f"{vram} GB" if vram is not None else "unknown"

    print("\nAI model selection:")
    print(f" - Model: {selection.get('selected_model')}")
    if selection.get("auto"):
        print(f" - Mode: auto ({selection.get('recommended_tier')}, resource profile={selection.get('resource_profile')})")
    else:
        print(f" - Mode: user override (resource profile={selection.get('resource_profile')})")
    print(f" - Hardware: RAM={ram_text}, GPU VRAM={vram_text}, logical CPUs={hardware.get('cpu_logical')}")
    if selection.get("runtime_options"):
        print(f" - Ollama runtime options: {selection.get('runtime_options')}")
    if selection.get("tier_reason"):
        print(f" - Reason: {selection.get('tier_reason')}")
    for warning in selection.get("warnings", []):
        print(f"[warn] {warning}")


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
                "Keep the capability rationale generic to the user's stated sector and problem. "
                "Do not introduce example assets, devices, systems, or workflows that were not supplied by the user.\n"
                "Priority tags:\n"
                "- [E] = Essential (must have for core functionality)\n"
                "- [H] = High Value (important for full business value)\n"
                "- [F] = Future Enhancement (beneficial for long-term evolution)\n\n"
                "Every single capability row must end with [E], [H], or [F]. "
                "Do not use words like 'Essential' or 'Important' in place of these tags.\n"
                "Example row format:\n"
                "| **DS.AI** | Data Acquisition & Ingestion | Required for repeatable source-data collection | Data acquisition layer | [E] |"
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

def dtaf_chunks(items: list[str], size: int) -> list[list[str]]:
    if size <= 0:
        size = 4

    return [items[i:i + size] for i in range(0, len(items), size)]
  
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

    Guarantees every capability has at least 3 checklist items.
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

        # NEW: treat 1 or 2 item lists as incomplete
        if len(prereq) < 3:
            fallback = dtaf_fallback_gates(cid, "")
            fallback_items = fallback.get("prerequisites", [])

            for item in fallback_items:
                item = str(item).strip()
                if item and item not in prereq:
                    prereq.append(item)

                if len(prereq) >= 3:
                    break

        # Final backup, just in case fallback itself is short
        while len(prereq) < 3:
            prereq.append(f"You can define the data, access, and implementation needs for {cid}")

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

        out[cid] = {
            "prerequisites": prereq,
            "hard_gates": hard2,
            "notes": str(notes).strip(),
        }

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
        max_tokens=min(8192, 1200 + 900 * len(cap_ids)),
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
) -> Path:
    essential, high = dtaf_select_essential_and_high(priorities)

    # Screen count is based on number of Essential capabilities
    selected = essential[:]

    # Generate question sets
    outdir = dtc_outdir / f"dtaf_addon_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
    ensure_dir(outdir)

    gates: Dict[str, Dict[str, Any]] = {}

    # Main batching setting
    batch_size = 4

    # -----------------------------
    # Generate Essential gates
    # -----------------------------
    if use_llm and selected:
        any_llm_success = False
        any_llm_failure = False

        for batch in dtaf_chunks(selected, batch_size):
            try:
                llm_map = dtaf_generate_gates_with_ollama(
                    base_url=base_url,
                    model=model,
                    timeout=timeout,
                    retries=retries,
                    step1=step1,
                    step2=step2,
                    step3=step3,
                    cap_ids=batch,
                )

                for cid in batch:
                    gates[cid] = {
                        "cap_id": cid,
                        "cap_name": CAP_NAME.get(cid, "(unknown)"),
                        "priority": priorities.get(cid, ""),
                        "prerequisites": llm_map[cid]["prerequisites"],
                        "hard_gates": llm_map[cid]["hard_gates"],
                        "notes": llm_map[cid].get("notes", ""),
                    }

                any_llm_success = True

            except Exception as e:
                any_llm_failure = True
                print(f"[warn] LLM gating failed for batch {batch}; using fallback. Reason: {e}")

                for cid in batch:
                    gates[cid] = dtaf_fallback_gates(cid, priorities.get(cid, ""))

        if any_llm_success and any_llm_failure:
            write_text(outdir / "gating_questions_source.txt", f"ollama_json_batched_size_{batch_size}_partial_fallback")
        elif any_llm_success:
            write_text(outdir / "gating_questions_source.txt", f"ollama_json_batched_size_{batch_size}")
        else:
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

    for cid in selected:
        cap = gates.get(cid) or dtaf_fallback_gates(cid, priorities.get(cid, ""))

        if len(cap.get("prerequisites", [])) < 3:
            fallback = dtaf_fallback_gates(cid, priorities.get(cid, ""))

            for item in fallback.get("prerequisites", []):
                if item not in cap["prerequisites"]:
                    cap["prerequisites"].append(item)

                if len(cap["prerequisites"]) >= 3:
                    break

            if not cap.get("hard_gates"):
                cap["hard_gates"] = [0]

        gates[cid] = cap

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
                answers[cid] = {
                    "have_indices": have,
                    "prerequisites": cap["prerequisites"],
                    "hard_gates": cap["hard_gates"],
                }
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

    # -----------------------------
    # Optionally extend to High Value
    # -----------------------------
    if extend_to_high and len(recommended) < keep:
        remaining = [cid for cid in high if cid not in selected]

        if remaining:
            print(f"\nNot enough feasible Essentials to fill Top {keep}. Screening High Value.\n")

        if use_llm and remaining:
            high_llm_success = False
            high_llm_failure = False

            for batch in dtaf_chunks(remaining, batch_size):
                try:
                    llm_map = dtaf_generate_gates_with_ollama(
                        base_url=base_url,
                        model=model,
                        timeout=timeout,
                        retries=retries,
                        step1=step1,
                        step2=step2,
                        step3=step3,
                        cap_ids=batch,
                    )

                    for cid in batch:
                        gates[cid] = {
                            "cap_id": cid,
                            "cap_name": CAP_NAME.get(cid, "(unknown)"),
                            "priority": priorities.get(cid, ""),
                            "prerequisites": llm_map[cid]["prerequisites"],
                            "hard_gates": llm_map[cid]["hard_gates"],
                            "notes": llm_map[cid].get("notes", ""),
                        }

                    high_llm_success = True

                except Exception as e:
                    high_llm_failure = True
                    print(f"[warn] LLM gating failed for High Value batch {batch}; using fallback. Reason: {e}")

                    for cid in batch:
                        gates[cid] = dtaf_fallback_gates(cid, priorities.get(cid, ""))

            if high_llm_success and high_llm_failure:
                write_text(outdir / "high_value_gating_questions_source.txt", f"ollama_json_batched_size_{batch_size}_partial_fallback")
            elif high_llm_success:
                write_text(outdir / "high_value_gating_questions_source.txt", f"ollama_json_batched_size_{batch_size}")
            else:
                write_text(outdir / "high_value_gating_questions_source.txt", "fallback")

        else:
            for cid in remaining:
                gates[cid] = dtaf_fallback_gates(cid, priorities.get(cid, ""))

            if remaining:
                write_text(outdir / "high_value_gating_questions_source.txt", "fallback")

        if remaining:
            screen_list(remaining)

            results_sorted = sorted(results, key=rank_key)
            recommended = [r for r in results_sorted if r["feasible_now"]][:keep]

    # -----------------------------
    # Save outputs
    # -----------------------------
    write_text(outdir / "gates.json", json.dumps(gates, indent=2))
    write_text(outdir / "answers.json", json.dumps(answers, indent=2))
    write_text(outdir / "screen_results.json", json.dumps(results_sorted, indent=2))

    recommended_payload = {
        "recommended": recommended,
        "screen_results": results_sorted,
        "selected_essential": selected,
        "checklist_batch_size": batch_size,
        "gates": gates,
        "answers": answers,
    }

    write_text(outdir / "recommended.json", json.dumps(recommended_payload, indent=2))

    lines = []
    lines.append("# DTAF Capability Feasibility Checklist Summary\n")
    lines.append(f"- Essential capabilities screened: {len(selected)}")
    lines.append(f"- Batch size: {batch_size}")
    lines.append(f"- Recommendation limit: {keep}\n")

    lines.append("## Recommended capabilities you can do now\n")
    if recommended:
        for r in recommended:
            lines.append(
                f"- **{r['cap_id']} ({r['priority']})** - {r['cap_name']} "
                f"| readiness={r['readiness_score']}"
            )
    else:
        lines.append("- None feasible with current answers.")

    lines.append("\n## Full readiness ranking\n")
    if results_sorted:
        lines.append("| Rank | Capability | Priority | Feasible now | Readiness | Missing hard gates |")
        lines.append("|---:|---|---|---|---:|---|")

        for i, r in enumerate(results_sorted, start=1):
            missing_hard = ", ".join(str(x) for x in r.get("missing_hard_gate_indices", []))
            if not missing_hard:
                missing_hard = "None"

            lines.append(
                f"| {i} | {r['cap_id']} - {r['cap_name']} | {r['priority']} | "
                f"{'Yes' if r['feasible_now'] else 'No'} | {r['readiness_score']} | {missing_hard} |"
            )
    else:
        lines.append("- No checklist results were recorded.")

    write_text(outdir / "summary.md", "\n".join(lines))

    append_jsonl(log_path, {
        "step": "DTAF_addon_post_step4",
        "time_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "output_path": str((outdir / "summary.md").name),
        "batch_size": batch_size,
    })

    print("\nDTAF add-on complete.")
    print(f"Saved: {outdir.resolve()}")
    print(f" - {outdir / 'summary.md'}")
    print(f" - {outdir / 'recommended.json'}")
    print(f" - {outdir / 'gates.json'}")
    print(f" - {outdir / 'screen_results.json'}\n")
    return outdir


# -----------------------------
# 4R assessment add-on
# -----------------------------

def load_4r_kb(path: Path) -> Dict[str, Any]:
    obj = read_json(path)
    if not isinstance(obj, dict):
        raise ValueError("4R knowledge base JSON must be an object at the top level")
    if "levels" not in obj or not isinstance(obj["levels"], list) or not obj["levels"]:
        raise ValueError("4R knowledge base JSON must contain a non-empty 'levels' list")
    return obj


def get_4r_levels_in_order(kb: Dict[str, Any]) -> List[Dict[str, Any]]:
    levels = [lvl for lvl in kb.get("levels", []) if isinstance(lvl, dict) and lvl.get("id")]
    levels.sort(key=lambda x: int(x.get("order", 999)))
    return levels


def compact_4r_kb_for_prompt(kb: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "framework_name": kb.get("framework_name", "4R Framework"),
        "framework_summary": kb.get("framework_summary", ""),
        "assessment_rules": kb.get("assessment_rules", {}),
        "levels": [
            {
                "id": lvl.get("id"),
                "name": lvl.get("name"),
                "order": lvl.get("order"),
                "description": lvl.get("description", ""),
                "minimum_gate_criteria": lvl.get("minimum_gate_criteria", []),
                "diagnostic_checks": lvl.get("diagnostic_checks", []),
                "action_items_to_reach_this_level": lvl.get("action_items_to_reach_this_level", []),
                "evidence_expected": lvl.get("evidence_expected", []),
                "target_if_not_met": lvl.get("target_if_not_met", ""),
            }
            for lvl in get_4r_levels_in_order(kb)
        ],
    }


def read_optional_extra_evidence(path_str: str) -> str:
    if not path_str:
        return ""
    p = Path(path_str)
    if not p.exists():
        raise FileNotFoundError(f"Extra 4R evidence file not found: {p}")
    return read_text(p)


def load_dtaf_4r_inputs(dtaf_outdir: Optional[Path]) -> Dict[str, Any]:
    out = {
        "summary_text": "",
        "recommended": [],
        "screen_results": [],
        "feasible_capabilities": [],
    }
    if dtaf_outdir is None or not dtaf_outdir.exists():
        return out

    summary_path = dtaf_outdir / "summary.md"
    recommended_path = dtaf_outdir / "recommended.json"
    screen_results_path = dtaf_outdir / "screen_results.json"

    def coerce_result_list(data: Any, preferred_keys: List[str]) -> List[Dict[str, Any]]:
        if isinstance(data, list):
            return [x for x in data if isinstance(x, dict)]
        if isinstance(data, dict):
            for key in preferred_keys:
                value = data.get(key)
                if isinstance(value, list):
                    return [x for x in value if isinstance(x, dict)]
        return []

    if summary_path.exists():
        out["summary_text"] = read_text(summary_path)
    if recommended_path.exists():
        try:
            data = read_json(recommended_path)
            out["recommended"] = coerce_result_list(
                data,
                ["recommended", "recommended_capabilities", "feasible_capabilities", "results"],
            )
        except Exception:
            pass
    if screen_results_path.exists():
        try:
            data = read_json(screen_results_path)
            out["screen_results"] = coerce_result_list(
                data,
                ["screen_results", "results", "capabilities", "recommended"],
            )
        except Exception:
            pass

    feasible = [r for r in out["screen_results"] if isinstance(r, dict) and r.get("feasible_now")]
    if not feasible:
        feasible = [r for r in out["recommended"] if isinstance(r, dict)]

    norm = []
    seen = set()
    for r in feasible:
        cid = str(r.get("cap_id", "")).strip()
        if not cid or cid in seen:
            continue
        seen.add(cid)
        norm.append({
            "cap_id": cid,
            "cap_name": str(r.get("cap_name", CAP_NAME.get(cid, ""))).strip(),
            "priority": str(r.get("priority", "")).strip(),
            "feasible_now": bool(r.get("feasible_now", True)),
            "readiness_score": float(r.get("readiness_score", 0.0) or 0.0),
        })

    norm.sort(key=lambda x: (-x["readiness_score"], CAP_ORDER.get(x["cap_id"], 10_000)))
    out["feasible_capabilities"] = norm
    return out



def fourr_sentence_split(text: str) -> List[str]:
    text = (text or "").replace("\r", " ")
    raw = re.split(r"(?<=[.!?])\s+|\n+|(?<=:)\s+", text)
    out: List[str] = []
    seen = set()
    for item in raw:
        s = re.sub(r"\s+", " ", item).strip(" -\t")
        if len(s) < 25:
            continue
        key = s.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(s)
    return out


def fourr_profile_for_criterion(criterion: str) -> Dict[str, Any]:
    c = (criterion or "").lower()
    profiles = [
        {
            "match": ["purpose, scope", "supported decisions"],
            "keywords": ["purpose", "scope", "decision", "supported decisions", "objective", "goal", "outcome", "kpi", "business requirement", "problem statement"],
            "caps": ["IC.PR", "IC.PS", "UX.DB", "UX.BV", "IC.SM"],
        },
        {
            "match": ["system boundaries", "major components", "inputs/outputs", "important states"],
            "keywords": ["boundary", "boundaries", "component", "components", "asset", "equipment", "resource", "process step", "input", "output", "state", "states", "architecture", "workflow", "interface", "subsystem"],
            "caps": ["DS.CX", "IR.EG", "IR.IO", "IC.SM", "UX.ER"],
        },
        {
            "match": ["critical variables are selected", "over-instrumentation", "missing context"],
            "keywords": ["critical variable", "variable", "variables", "parameter", "parameters", "monitor", "measure", "sensor", "degradation", "condition", "performance", "vibration", "temperature", "position", "throughput", "quality", "cycle time", "service level", "utilization"],
            "caps": ["DS.AI", "DS.TR", "UX.RM", "IC.AA"],
        },
        {
            "match": ["repeatable data collection", "storage pipeline"],
            "keywords": ["pipeline", "ingest", "ingestion", "collect", "collection", "stream", "batch", "database", "historian", "storage", "archive", "api", "mqtt", "file drop", "repeatable", "automated", "real-time"],
            "caps": ["DS.AI", "DS.ST", "DS.BP", "DS.SA", "IR.IO", "IR.ET", "IR.EG"],
        },
        {
            "match": ["structured, usable", "verified against known system behavior"],
            "keywords": ["structured", "clean", "normalize", "normalized", "transformation", "wrangling", "contextual", "validated", "validation", "verified", "verification", "compare", "comparison", "reference", "known behavior", "calibration"],
            "caps": ["DS.TR", "DS.CX", "IC.AA", "IC.SM"],
        },
        {
            "match": ["replication targets", "acceptable error thresholds"],
            "keywords": ["replication", "replicate", "acceptable error", "error threshold", "acceptable deviation", "target output", "fidelity", "accuracy", "match real behavior"],
            "caps": ["IC.SM", "IC.MA"],
        },
        {
            "match": ["modeling platform", "digital architecture"],
            "keywords": ["modeling platform", "simulation platform", "platform", "digital architecture", "architecture", "model repository", "simulation model", "digital model"],
            "caps": ["DS.RP", "DS.SR", "IC.SM", "IR.DT", "UX.AV"],
        },
        {
            "match": ["live or recorded data", "drive model inputs"],
            "keywords": ["live data", "recorded data", "playback", "model input", "model inputs", "updates", "synchronization", "streaming", "batch", "historical data"],
            "caps": ["DS.ST", "DS.BP", "IR.IO", "DS.AI", "IC.SM"],
        },
        {
            "match": ["tested against real behavior", "acceptable deviation"],
            "keywords": ["tested", "validated", "verification", "validation", "deviation", "error threshold", "reproduce", "accuracy", "compare to real", "real behavior"],
            "caps": ["IC.SM", "IC.MA", "IC.AA"],
        },
        {
            "match": ["prediction targets", "objective functions"],
            "keywords": ["predict", "prediction", "forecast", "remaining useful life", "rul", "scenario", "objective", "optimization", "decision variable"],
            "caps": ["IC.PR", "IC.PS", "IC.MA", "IC.AI"],
        },
        {
            "match": ["without continuous live dependency"],
            "keywords": ["offline", "historical data", "recorded data", "batch", "asynchronous", "without continuous", "not continuous", "decoupled"],
            "caps": ["DS.BP", "DS.SA", "DS.AS", "IC.SM"],
        },
        {
            "match": ["predictive or scenario-exploration models"],
            "keywords": ["predictive", "what-if", "scenario", "simulation", "model", "forecast", "scenario exploration"],
            "caps": ["IC.PR", "IC.SM", "IC.AI", "IC.MA"],
        },
        {
            "match": ["actionable recommendations", "optimized results"],
            "keywords": ["what-if", "scenario", "recommendation", "recommendations", "optimize", "optimized", "scheduling", "prescriptive", "actionable"],
            "caps": ["IC.PS", "IC.PR", "UX.DB", "UX.BI", "IC.OS"],
        },
        {
            "match": ["autonomy scope", "human-in-the-loop", "override conditions"],
            "keywords": ["autonomy", "human-in-the-loop", "override", "approval", "guardrail", "operator", "escalation"],
            "caps": ["IC.CC", "IC.OS", "IC.BR", "TW.SF", "TW.SC"],
        },
        {
            "match": ["detect anomalies", "real time"],
            "keywords": ["anomaly", "alert", "real-time", "monitoring", "event", "detect", "condition change"],
            "caps": ["UX.RM", "IC.AL", "IC.AI", "MG.EL", "MG.SM"],
        },
        {
            "match": ["choose among actions", "learned or adaptive logic"],
            "keywords": ["choose among actions", "adaptive", "policy", "learned", "learning", "business rules", "decision logic"],
            "caps": ["IC.AI", "IC.BR", "IC.PS", "IC.FL"],
        },
        {
            "match": ["past outcomes are stored", "improve future decisions"],
            "keywords": ["feedback", "history", "outcomes", "stored", "used to improve", "future decisions", "learning loop", "event log"],
            "caps": ["MG.EL", "DS.SA", "DS.AR", "IC.FL", "IC.AI"],
        },
        {
            "match": ["make or execute decisions", "trust and safety controls"],
            "keywords": ["command", "control", "execute", "automation", "safe", "safety", "security", "trust", "override", "governance"],
            "caps": ["IC.CC", "TW.SF", "TW.SC", "TW.RL", "MG.DG"],
        },
    ]
    for profile in profiles:
        if any(m in c for m in profile["match"]):
            return profile
    return {"match": [], "keywords": [], "caps": []}


def fourr_collect_criterion_evidence(
    *,
    criterion: str,
    source_texts: Dict[str, str],
    priorities: Dict[str, str],
    feasible_capabilities: List[Dict[str, Any]],
) -> Dict[str, Any]:
    profile = fourr_profile_for_criterion(criterion)
    keywords = [k.lower() for k in profile.get("keywords", [])]
    target_caps = set(profile.get("caps", []))
    snippets: List[str] = []
    seen = set()

    for source_name, text in source_texts.items():
        if not text:
            continue
        for sent in fourr_sentence_split(text):
            sl = sent.lower()
            hits = sum(1 for kw in keywords if kw and kw in sl)
            if hits <= 0:
                continue
            snippet = f"[{source_name}] {sent[:280]}"
            key = snippet.lower()
            if key in seen:
                continue
            seen.add(key)
            snippets.append(snippet)
            if len(snippets) >= 4:
                break
        if len(snippets) >= 4:
            break

    feasible_ids = []
    for item in feasible_capabilities:
        cid = str(item.get("cap_id", "")).strip()
        if cid in target_caps and cid not in feasible_ids:
            feasible_ids.append(cid)

    selected_ids = []
    for cid, lvl in sorted(priorities.items(), key=lambda x: CAP_ORDER.get(x[0], 10_000)):
        if cid in target_caps and lvl in {"E", "H"} and cid not in selected_ids:
            selected_ids.append(cid)

    if len(snippets) >= 2 or (len(snippets) >= 1 and len(feasible_ids) >= 1):
        strength = "explicit"
    elif len(snippets) >= 1 or len(feasible_ids) >= 1 or len(selected_ids) >= 2:
        strength = "partial"
    else:
        strength = "none"

    return {
        "criterion": criterion,
        "keywords": profile.get("keywords", []),
        "feasible_caps": feasible_ids,
        "selected_caps": selected_ids[:6],
        "snippets": snippets,
        "strength": strength,
    }


def build_4r_criterion_evidence_index(
    *,
    kb: Dict[str, Any],
    sector: str,
    problem_statement: str,
    outputs: Dict[str, str],
    priorities: Dict[str, str],
    dtaf_summary_text: str,
    extra_evidence: str,
    feasible_capabilities: List[Dict[str, Any]],
) -> Dict[str, Dict[str, Any]]:
    source_texts = {
        "sector": sector,
        "problem_statement": problem_statement,
        "step0": outputs.get("0", ""),
        "step1": outputs.get("1", ""),
        "step2": outputs.get("2", ""),
        "step3_part1": outputs.get("3_part1", ""),
        "step3_part2": outputs.get("3_part2", ""),
        "dtaf_summary": dtaf_summary_text,
        "extra_evidence": extra_evidence,
    }
    index: Dict[str, Dict[str, Any]] = {}
    for lvl in get_4r_levels_in_order(kb):
        lid = str(lvl["id"])
        index[lid] = {}
        for criterion in lvl.get("minimum_gate_criteria", []):
            index[lid][criterion] = fourr_collect_criterion_evidence(
                criterion=criterion,
                source_texts=source_texts,
                priorities=priorities,
                feasible_capabilities=feasible_capabilities,
            )
    return index


def fourr_reconcile_evaluation_with_evidence(
    *,
    kb: Dict[str, Any],
    evaluated: Dict[str, Any],
    criterion_evidence_index: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:
    for lvl in get_4r_levels_in_order(kb):
        lid = str(lvl["id"])
        gates = evaluated.get("levels", {}).get(lid, {}).get("gate_scores", [])
        for gate in gates:
            criterion = str(gate.get("criterion", "")).strip()
            if not criterion or criterion.lower().endswith("already satisfied."):
                continue
            evidence_info = criterion_evidence_index.get(lid, {}).get(criterion, {})
            strength = evidence_info.get("strength", "none")
            score = int(gate.get("score", 0))
            snippets = evidence_info.get("snippets", [])
            feasible_caps = evidence_info.get("feasible_caps", [])
            if strength == "explicit" and score < 2:
                gate["score"] = 2
                extra_bits = []
                if snippets:
                    extra_bits.append("evidence found in prior outputs")
                if feasible_caps:
                    extra_bits.append("aligned feasible capabilities: " + ", ".join(feasible_caps[:4]))
                note = "; ".join(extra_bits) if extra_bits else "evidence found in prior outputs"
                gate["rationale"] = ((gate.get("rationale", "").strip() + " | ") if gate.get("rationale") else "") + note
                if not gate.get("evidence") and snippets:
                    gate["evidence"] = snippets[0]
            elif strength == "partial" and score < 1:
                gate["score"] = 1
                note = "partial evidence found in prior outputs"
                gate["rationale"] = ((gate.get("rationale", "").strip() + " | ") if gate.get("rationale") else "") + note
                if not gate.get("evidence") and snippets:
                    gate["evidence"] = snippets[0]
    return evaluated


def build_4r_evidence_bundle(
    *,
    kb: Dict[str, Any],
    sector: str,
    problem_statement: str,
    outputs: Dict[str, str],
    priorities: Dict[str, str],
    dtaf_summary_text: str,
    extra_evidence: str,
    feasible_capabilities: List[Dict[str, Any]],
    screen_results: List[Dict[str, Any]],
    criterion_evidence_index: Dict[str, Dict[str, Any]],
) -> str:
    priority_lines = [f"- {cid}: {lvl}" for cid, lvl in sorted(priorities.items(), key=lambda x: CAP_ORDER.get(x[0], 10_000))]
    feasible_lines = []
    for item in feasible_capabilities[:120]:
        feasible_lines.append(
            f"- {item['cap_id']} ({item.get('priority', '')}) - {item.get('cap_name', '')} | feasible_now={item.get('feasible_now', True)} | readiness={item.get('readiness_score', 0.0):.2f}"
        )

    blocked_lines = []
    for item in screen_results[:200]:
        if isinstance(item, dict) and not item.get("feasible_now"):
            blocked_lines.append(
                f"- {item.get('cap_id', '')} ({item.get('priority', '')}) - {item.get('cap_name', '')} | readiness={float(item.get('readiness_score', 0.0) or 0.0):.2f}"
            )

    parts = [
        "Assessment intent: This is a pre-build planning assessment. There is no current 4R maturity level yet because the digital twin has not been built. Determine the highest 4R target level that the proposed digital twin can realistically be built to, based on the feasible capabilities and planning evidence. Then give action items to reach that target level using those capabilities.",
        "Decision boundary: The DTAF feasible-capability list is authoritative readiness evidence. If feasible capabilities include representation/data capabilities plus model, simulation, live-data, or recorded-data capabilities that support comparing virtual behavior to real or recorded behavior, R2 should normally be treated as the recommended pre-build target while implementation evidence gaps remain tracked separately. R3 requires explicit prediction or scenario-exploration targets plus objective/decision variables. R4 requires explicit autonomy scope, human override boundaries, and trust/safety controls for action execution.",
        f"Sector: {sector}",
        "Problem statement:\n" + problem_statement.strip(),
        "Step 0 output (truncated):\n" + outputs.get("0", "")[:4000],
        "Step 1 output (truncated):\n" + outputs.get("1", "")[:7000],
        "Step 2 output (truncated):\n" + outputs.get("2", "")[:7000],
        "Step 3 output (truncated):\n" + (outputs.get("3_part1", "") + "\n\n" + outputs.get("3_part2", ""))[:9000],
        "Selected DTC priorities:\n" + "\n".join(priority_lines[:120]),
    ]
    if feasible_lines:
        parts.append("Feasible capabilities from the post-Step-4 readiness screen:\n" + "\n".join(feasible_lines))
    if blocked_lines:
        parts.append("Capabilities screened but not currently feasible:\n" + "\n".join(blocked_lines[:80]))
    if dtaf_summary_text.strip():
        parts.append("DTAF readiness summary:\n" + dtaf_summary_text[:5000])
    if extra_evidence.strip():
        parts.append("Additional user-provided 4R evidence:\n" + extra_evidence[:8000])
    return "\n\n".join(parts)


def fourr_safe_json_extract(s: str) -> Dict[str, Any]:
    s = s.strip()
    try:
        return json.loads(s)
    except Exception:
        pass
    m = re.search(r"\{.*\}", s, flags=re.S)
    if not m:
        raise ValueError("Model did not return JSON for the 4R assessment")
    return json.loads(m.group(0))


def fourr_generate_level_scores_with_ollama(
    *,
    base_url: str,
    model: str,
    timeout: float,
    retries: int,
    kb: Dict[str, Any],
    evidence_bundle: str,
) -> Dict[str, Any]:
    kb_compact = compact_4r_kb_for_prompt(kb)
    level_ids = [lvl["id"] for lvl in kb_compact["levels"]]

    messages = [
        {
            "role": "system",
            "content": (
                "Return ONLY JSON. This is a pre-build 4R target assessment for a planned digital twin. "
                "There is no current 4R level because the digital twin has not been built yet. "
                "Use the feasible capabilities and planning evidence to judge which 4R level the planned twin can realistically target. "
                "The evidence bundle includes criterion-specific snippets mined from Step 0 to Step 3. Use those mined snippets first before calling something a gap. "
                "If the earlier outputs already define or describe a criterion, do not list that criterion as a missing gap. "
                "Be conservative, but do not ignore explicit evidence that appears in the prior-step outputs. "
                "Use the scoring rule exactly: 0 = no evidence, 1 = partial or implied evidence, 2 = clear explicit evidence. "
                "Do not assign a 2 unless the evidence clearly and directly supports the gate criterion."
            ),
        },
        {
            "role": "user",
            "content": (
                "Assess the provided evidence against the supplied 4R knowledge base.\n\n"
                "Output JSON EXACTLY in this shape:\n"
                "{\n"
                '  "planning_summary": "...",\n'
                '  "risks_or_notes": ["..."],\n'
                '  "levels": {\n'
                '    "R1": {\n'
                '      "summary": "...",\n'
                '      "supporting_capabilities": ["DS.AI", "UX.BV"],\n'
                '      "gate_scores": [\n'
                '        {"score": 0, "evidence": "...", "rationale": "..."}\n'
                "      ],\n"
                '      "action_items_tailored": ["..."]\n'
                "    },\n"
                '    "R2": {"summary": "...", "supporting_capabilities": [...], "gate_scores": [...], "action_items_tailored": [...]},\n'
                '    "R3": {"summary": "...", "supporting_capabilities": [...], "gate_scores": [...], "action_items_tailored": [...]},\n'
                '    "R4": {"summary": "...", "supporting_capabilities": [...], "gate_scores": [...], "action_items_tailored": [...]}\n'
                "  }\n"
                "}\n\n"
                "Rules:\n"
                "- This is NOT a current maturity assessment. Treat it as a pre-build planning and target-level assessment.\n"
                "- Keep gate_scores in the exact same order as the minimum_gate_criteria listed for each level.\n"
                "- Each gate_scores list must have the same number of items as that level's minimum_gate_criteria.\n"
                "- supporting_capabilities must only include feasible capabilities that directly support the level.\n"
                "- Treat the DTAF feasible-capability list as readiness evidence for what can be built now; do not ignore it when deciding R1 versus R2.\n"
                "- Keep recommended target and current evidence baseline separate: missing implementation artifacts should become action items/gaps, not automatically lower the recommended pre-build target.\n"
                "- Do not recommend R3 or R4 from aspirational language alone. R3 needs explicit prediction/scenario targets and decision variables; R4 needs explicit autonomy scope, override rules, and trust/safety controls.\n"
                "- action_items_tailored should explain what to do to REACH that level using the feasible capabilities and planned architecture.\n"
                "- Keep action items specific, concise, and implementation oriented.\n"
                "- Evidence should be short and quote-like, but paraphrased.\n"
                "- Rationale should be brief and specific.\n"
                "- Note important uncertainty in risks_or_notes.\n\n"
                f"4R knowledge base:\n{json.dumps(kb_compact, indent=2)}\n\n"
                f"Level order: {level_ids}\n\n"
                f"Evidence bundle:\n{evidence_bundle}"
            ),
        },
    ]

    out = chat_completions(
        base_url=base_url,
        model=model,
        messages=messages,
        max_tokens=3800,
        temperature=0.0,
        timeout=timeout,
        retries=retries,
    )
    return fourr_safe_json_extract(out)


def fourr_validate_evaluation(kb: Dict[str, Any], obj: Dict[str, Any]) -> Dict[str, Any]:
    level_defs = get_4r_levels_in_order(kb)
    levels_obj = obj.get("levels", {}) if isinstance(obj, dict) else {}
    out_levels: Dict[str, Any] = {}
    known_caps = set(CAP_NAME.keys())

    for lvl in level_defs:
        lid = str(lvl.get("id"))
        criteria = [str(x).strip() for x in lvl.get("minimum_gate_criteria", []) if str(x).strip()]
        src = levels_obj.get(lid, {}) if isinstance(levels_obj, dict) else {}
        raw_gates = src.get("gate_scores", []) if isinstance(src, dict) else []
        normalized = []

        for i, criterion in enumerate(criteria):
            gate = raw_gates[i] if isinstance(raw_gates, list) and i < len(raw_gates) and isinstance(raw_gates[i], dict) else {}
            score = gate.get("score", 0)
            if isinstance(score, str) and score.isdigit():
                score = int(score)
            if score not in {0, 1, 2}:
                score = 0
            normalized.append({
                "criterion": criterion,
                "score": score,
                "evidence": str(gate.get("evidence", "")).strip(),
                "rationale": str(gate.get("rationale", "")).strip(),
            })

        supporting_caps = src.get("supporting_capabilities", []) if isinstance(src, dict) else []
        if not isinstance(supporting_caps, list):
            supporting_caps = []
        supporting_caps = [str(x).strip() for x in supporting_caps if str(x).strip() in known_caps]
        supporting_caps = list(dict.fromkeys(supporting_caps))

        tailored = src.get("action_items_tailored", []) if isinstance(src, dict) else []
        if not isinstance(tailored, list):
            tailored = []
        tailored = [str(x).strip() for x in tailored if str(x).strip()]
        tailored = tailored[:12]

        out_levels[lid] = {
            "summary": str(src.get("summary", "")).strip() if isinstance(src, dict) else "",
            "supporting_capabilities": supporting_caps,
            "gate_scores": normalized,
            "action_items_tailored": tailored,
        }

    risks = obj.get("risks_or_notes", []) if isinstance(obj, dict) else []
    if not isinstance(risks, list):
        risks = [str(risks)]

    return {
        "planning_summary": str(obj.get("planning_summary", obj.get("evidence_summary", ""))).strip() if isinstance(obj, dict) else "",
        "risks_or_notes": [str(x).strip() for x in risks if str(x).strip()],
        "levels": out_levels,
    }


def fourr_level_support(gate_scores: List[Dict[str, Any]]) -> bool:
    if not gate_scores:
        return False
    scores = [int(g.get("score", 0)) for g in gate_scores]
    all_at_least_partial = all(s >= 1 for s in scores)
    explicit_ratio = sum(1 for s in scores if s == 2) / len(scores)
    return all_at_least_partial and explicit_ratio >= 0.80


def fourr_level_planning_ready(gate_scores: List[Dict[str, Any]]) -> bool:
    """More permissive than current-supported: allows one weak/missing gate if the
    level is otherwise well-supported in planning and is the intended next build step."""
    if not gate_scores:
        return False
    scores = [int(g.get("score", 0)) for g in gate_scores]
    partial_or_better_ratio = sum(1 for s in scores if s >= 1) / len(scores)
    twos = sum(1 for s in scores if s == 2)
    zeros = sum(1 for s in scores if s == 0)
    return partial_or_better_ratio >= 0.80 and twos >= 2 and zeros <= 1


def fourr_confidence_label(gate_scores: List[Dict[str, Any]]) -> str:
    if not gate_scores:
        return "low"
    avg = sum(int(g.get("score", 0)) for g in gate_scores) / len(gate_scores)
    if avg >= 1.75:
        return "high"
    if avg >= 1.25:
        return "medium"
    return "low"




def fourr_target_order(kb: Dict[str, Any], target_id: str) -> int:
    for lvl in get_4r_levels_in_order(kb):
        if str(lvl.get("id")) == str(target_id):
            try:
                return int(lvl.get("order", 999))
            except Exception:
                return 999
    return 999


def fourr_capability_floor_target_id(feasible_capabilities: List[Dict[str, Any]]) -> Optional[str]:
    cap_ids = {
        str(item.get("cap_id", "")).strip()
        for item in feasible_capabilities
        if isinstance(item, dict) and str(item.get("cap_id", "")).strip()
    }
    if not cap_ids:
        return None

    representation_signals = {"DS.AI", "DS.TR", "IR.ET", "IR.IO", "UX.BV", "UX.RM", "MG.DM", "TW.SC"}
    replication_signals = {"IC.SM", "DS.ST", "DS.BP", "DS.RT", "IR.EG", "IR.IO", "DS.AS"}
    has_representation_base = len(cap_ids & representation_signals) >= 4
    has_replication_base = len(cap_ids & replication_signals) >= 2 or "IC.SM" in cap_ids

    if has_representation_base and has_replication_base:
        return "R2"
    return None


def fourr_build_plan_for_target(
    kb: Dict[str, Any],
    evaluated: Dict[str, Any],
    feasible_capabilities: List[Dict[str, Any]],
    target_id: str,
) -> Dict[str, Any]:
    levels = get_4r_levels_in_order(kb)
    target_order = fourr_target_order(kb, target_id)
    cap_map: Dict[str, Dict[str, Any]] = {}
    for item in feasible_capabilities:
        if not isinstance(item, dict):
            continue
        cid = str(item.get("cap_id", "")).strip()
        if not cid:
            continue
        cap_map[cid] = {
            "cap_id": cid,
            "cap_name": str(item.get("cap_name", CAP_NAME.get(cid, ""))).strip(),
            "priority": str(item.get("priority", "")).strip(),
            "readiness_score": float(item.get("readiness_score", 0.0) or 0.0),
        }

    phases: List[Dict[str, Any]] = []
    rolled_up_caps: List[str] = []
    seen_caps = set()

    for lvl in levels:
        try:
            order = int(lvl.get("order", 999))
        except Exception:
            order = 999
        if order > target_order:
            break

        lid = str(lvl.get("id"))
        lvl_eval = evaluated.get("levels", {}).get(lid, {})
        gate_scores = lvl_eval.get("gate_scores", [])
        supported = fourr_level_support(gate_scores)
        partial_count = sum(1 for g in gate_scores if int(g.get("score", 0)) >= 1)
        total_count = len(gate_scores)

        if supported:
            planning_status = "supported in planning evidence"
            task_status = "planning evidence present, implementation still required"
        elif partial_count > 0:
            planning_status = "partially supported in planning evidence"
            task_status = "partially covered in planning evidence, implementation still required"
        else:
            planning_status = "not yet supported in planning evidence"
            task_status = "needs planning and implementation"

        phase_caps = []
        for cid in lvl_eval.get("supporting_capabilities", []):
            if cid in cap_map:
                phase_caps.append(cap_map[cid])
                if cid not in seen_caps:
                    seen_caps.add(cid)
                    rolled_up_caps.append(cid)

        steps = []
        for wf in lvl.get("workflow_steps", []) or []:
            if not isinstance(wf, dict):
                continue
            step_tasks = []
            for task in wf.get("tasks", []) or []:
                if not isinstance(task, dict):
                    continue
                task_text = str(task.get("task_text", "")).strip()
                if not task_text:
                    continue
                step_tasks.append({
                    "task_id": str(task.get("task_id", "")).strip(),
                    "task_text": task_text,
                    "example": str(task.get("example", "")).strip(),
                    "implementation_status": task_status,
                })
            steps.append({
                "step_id": str(wf.get("step_id", "")).strip(),
                "step_title": str(wf.get("step_title", "")).strip(),
                "tasks": step_tasks,
            })

        completion_checks = []
        for gate in gate_scores:
            completion_checks.append({
                "criterion": str(gate.get("criterion", "")).strip(),
                "score": int(gate.get("score", 0)),
                "status": "supported" if int(gate.get("score", 0)) == 2 else ("partial" if int(gate.get("score", 0)) == 1 else "missing"),
                "evidence": str(gate.get("evidence", "")).strip(),
            })

        phases.append({
            "level_id": lid,
            "level_name": str(lvl.get("name", lid)),
            "level_description": str(lvl.get("description", "")).strip(),
            "core_outcome": str(lvl.get("core_outcome", "")).strip(),
            "planning_support_status": planning_status,
            "relevant_capabilities": phase_caps,
            "workflow_steps": steps,
            "completion_checks": completion_checks,
            "tailored_actions": [str(x).strip() for x in lvl_eval.get("action_items_tailored", []) if str(x).strip()],
        })

    cross_cutting_caps = []
    for cid in rolled_up_caps:
        item = cap_map.get(cid)
        if item:
            cross_cutting_caps.append(item)

    return {
        "target_level": str(target_id),
        "target_level_name": next((str(l.get("name", target_id)) for l in levels if str(l.get("id")) == str(target_id)), str(target_id)),
        "phases": phases,
        "cross_cutting_capabilities": cross_cutting_caps,
    }



def fourr_compute_result(
    *,
    kb: Dict[str, Any],
    evaluated: Dict[str, Any],
    feasible_capabilities: List[Dict[str, Any]],
    max_actions: int = 8,
    intended_target_level: Optional[str] = None,
) -> Dict[str, Any]:
    levels = get_4r_levels_in_order(kb)
    level_status: Dict[str, Any] = {}
    highest_feasible_def: Optional[Dict[str, Any]] = None
    highest_current_supported_def: Optional[Dict[str, Any]] = None

    for lvl in levels:
        lid = str(lvl["id"])
        gate_scores = evaluated["levels"][lid]["gate_scores"]
        feasible_supported = fourr_level_support(gate_scores)
        explicit_ratio = (sum(1 for g in gate_scores if int(g.get("score", 0)) == 2) / len(gate_scores)) if gate_scores else 0.0
        current_supported = bool(gate_scores) and all(int(g.get("score", 0)) == 2 for g in gate_scores)
        planning_ready = fourr_level_planning_ready(gate_scores)
        level_status[lid] = {
            "supported": feasible_supported,
            "planning_ready": planning_ready,
            "current_supported": current_supported,
            "explicit_ratio": round(explicit_ratio, 3),
            "partial_or_better": sum(1 for g in gate_scores if int(g.get("score", 0)) >= 1),
            "total": len(gate_scores),
            "supporting_capabilities": evaluated["levels"][lid].get("supporting_capabilities", []),
        }
        if feasible_supported:
            highest_feasible_def = lvl
        else:
            break

    for lvl in levels:
        lid = str(lvl["id"])
        st = level_status.get(lid, {})
        if st.get("current_supported"):
            highest_current_supported_def = lvl
        else:
            break

    if highest_current_supported_def is None:
        evidence_baseline_def = levels[0] if levels else {"id": "R1", "name": "Representation"}
        evidence_baseline_status = "partial"
    else:
        evidence_baseline_def = highest_current_supported_def
        evidence_baseline_status = "supported"

    # Recommended pre-build target: prefer an explicit intended target when provided.
    # Otherwise, allow the next level beyond the evidence baseline when it is planning-ready,
    # even if not yet fully evidenced as implemented.
    baseline_order = fourr_target_order(kb, str(evidence_baseline_def.get("id", "R1")))
    intended_target_level = (str(intended_target_level).strip().upper() if intended_target_level else "")
    valid_level_ids = {str(l.get("id", "")).upper(): l for l in levels}

    recommended_target_def = evidence_baseline_def
    recommended_support_status = evidence_baseline_status

    if intended_target_level and intended_target_level in valid_level_ids:
        intended_def = valid_level_ids[intended_target_level]
        intended_order = fourr_target_order(kb, intended_target_level)
        if intended_order >= baseline_order:
            recommended_target_def = intended_def
            recommended_support_status = "supported in planning" if intended_order > baseline_order else evidence_baseline_status
    else:
        candidate_def = evidence_baseline_def
        for lvl in levels:
            lid = str(lvl.get("id", ""))
            if fourr_target_order(kb, lid) <= baseline_order:
                continue
            st = level_status.get(lid, {})
            if st.get("planning_ready"):
                candidate_def = lvl
                recommended_support_status = "supported in planning"
                break
            else:
                break
        recommended_target_def = candidate_def

    if not intended_target_level:
        capability_floor_target_id = fourr_capability_floor_target_id(feasible_capabilities)
        if capability_floor_target_id and capability_floor_target_id in valid_level_ids:
            current_recommended_order = fourr_target_order(kb, str(recommended_target_def.get("id", "R1")))
            floor_order = fourr_target_order(kb, capability_floor_target_id)
            if floor_order > current_recommended_order:
                recommended_target_def = valid_level_ids[capability_floor_target_id]
                recommended_support_status = "supported in planning by feasible capabilities"
                level_status.setdefault(capability_floor_target_id, {})
                level_status[capability_floor_target_id]["planning_ready"] = True
                level_status[capability_floor_target_id]["capability_floor_applied"] = True

    recommended_target_id = str(recommended_target_def["id"])
    evidence_baseline_id = str(evidence_baseline_def["id"])

    target_eval = evaluated["levels"].get(recommended_target_id, {"gate_scores": [], "supporting_capabilities": [], "action_items_tailored": []})

    criteria_supported = []
    gaps_to_reach = []
    for g in target_eval.get("gate_scores", []):
        criterion = g.get("criterion", "")
        score = int(g.get("score", 0))
        if score == 2:
            criteria_supported.append(criterion)
        elif score == 1:
            gaps_to_reach.append(f"{criterion} (partial evidence)")
        else:
            gaps_to_reach.append(f"{criterion} (no explicit evidence)")

    action_items = [str(x).strip() for x in target_eval.get("action_items_tailored", []) if str(x).strip()]
    if not action_items:
        action_items = [str(x).strip() for x in recommended_target_def.get("action_items_to_reach_this_level", []) if str(x).strip()]
    action_items = action_items[:max_actions]

    capability_alignment = {}
    for lvl in levels:
        lid = str(lvl["id"])
        capability_alignment[lid] = evaluated["levels"].get(lid, {}).get("supporting_capabilities", [])

    build_plan = fourr_build_plan_for_target(
        kb=kb,
        evaluated=evaluated,
        feasible_capabilities=feasible_capabilities,
        target_id=recommended_target_id,
    )

    near_term_next_target_level = None
    near_term_next_target_name = None
    target_order = fourr_target_order(kb, recommended_target_id)
    for lvl in levels:
        try:
            order = int(lvl.get("order", 999))
        except Exception:
            order = 999
        if order == target_order + 1:
            near_term_next_target_level = str(lvl.get("id", "")).strip() or None
            near_term_next_target_name = str(lvl.get("name", near_term_next_target_level or "")).strip() or near_term_next_target_level
            break

    return {
        "assessment_type": "pre_build_4r_target_assessment_with_build_plan",
        "highest_supported_target_level": recommended_target_id if highest_feasible_def is not None else None,
        "highest_supported_target_name": str(highest_feasible_def.get("name")) if highest_feasible_def is not None else None,
        "recommended_target_level": recommended_target_id,
        "recommended_target_name": str(recommended_target_def.get("name", recommended_target_id)),
        "current_supported_target_level": evidence_baseline_id,
        "current_supported_target_name": str(evidence_baseline_def.get("name", evidence_baseline_id)),
        "current_target_support_status": evidence_baseline_status,
        "near_term_next_target_level": near_term_next_target_level,
        "near_term_next_target_name": near_term_next_target_name,
        "feasible_next_target_level": recommended_target_id,
        "feasible_next_target_name": str(recommended_target_def.get("name", recommended_target_id)),
        "target_support_status": recommended_support_status,
        "target_confidence": fourr_confidence_label(target_eval.get("gate_scores", [])),
        "planning_summary": evaluated.get("planning_summary", ""),
        "feasible_capabilities_used": feasible_capabilities,
        "capability_alignment_by_level": capability_alignment,
        "criteria_supported_for_target": criteria_supported,
        "gaps_to_reach_target": gaps_to_reach,
        "action_items_to_reach_target": action_items,
        "build_plan": build_plan,
        "risks_or_notes": evaluated.get("risks_or_notes", []),
        "level_status": level_status,
        "level_evaluations": evaluated["levels"],
    }

def compact_4r_steps_up_to_target(kb: Dict[str, Any], target_id: str) -> List[Dict[str, Any]]:
    levels = get_4r_levels_in_order(kb)
    target_order = fourr_target_order(kb, target_id)
    out: List[Dict[str, Any]] = []
    for lvl in levels:
        try:
            order = int(lvl.get("order", 999))
        except Exception:
            order = 999
        if order > target_order:
            break
        wf_steps = []
        for wf in lvl.get("workflow_steps", []) or []:
            if not isinstance(wf, dict):
                continue
            wf_steps.append({
                "step_id": str(wf.get("step_id", "")).strip(),
                "step_title": str(wf.get("step_title", "")).strip(),
                "tasks": [
                    {
                        "task_id": str(t.get("task_id", "")).strip(),
                        "task_text": str(t.get("task_text", "")).strip(),
                        "example": str(t.get("example", "")).strip(),
                    }
                    for t in (wf.get("tasks", []) or []) if isinstance(t, dict) and str(t.get("task_text", "")).strip()
                ],
            })
        out.append({
            "id": str(lvl.get("id", "")).strip(),
            "name": str(lvl.get("name", "")).strip(),
            "description": str(lvl.get("description", "")).strip(),
            "core_outcome": str(lvl.get("core_outcome", "")).strip(),
            "workflow_steps": wf_steps,
            "minimum_gate_criteria": [str(x).strip() for x in (lvl.get("minimum_gate_criteria", []) or []) if str(x).strip()],
            "action_items_to_reach_this_level": [str(x).strip() for x in (lvl.get("action_items_to_reach_this_level", []) or []) if str(x).strip()],
        })
    return out


def fourr_build_tailored_action_items_prompt(
    *,
    kb: Dict[str, Any],
    sector: str,
    problem_statement: str,
    outputs: Dict[str, str],
    evaluated: Dict[str, Any],
    result: Dict[str, Any],
    dtaf_inputs: Dict[str, Any],
    criterion_evidence_index: Dict[str, Any],
    extra_evidence: str,
) -> str:
    target_id = str(result.get("recommended_target_level", "R1"))
    step_bundle = compact_4r_steps_up_to_target(kb, target_id)
    feasible_caps = result.get("feasible_capabilities_used", []) or []
    feasible_lines = []
    for item in feasible_caps[:120]:
        if not isinstance(item, dict):
            continue
        feasible_lines.append(
            f"- {item.get('cap_id','')} ({item.get('priority','')}) - {item.get('cap_name','')} | readiness={float(item.get('readiness_score',0.0) or 0.0):.2f}"
        )
    lines = [
        f"Use case sector: {sector}",
        "Use case description:\n" + problem_statement.strip(),
        "Target 4R level and justification:\n" + json.dumps({
            "recommended_target_level": result.get("recommended_target_level"),
            "recommended_target_name": result.get("recommended_target_name"),
            "highest_supported_target_level": result.get("highest_supported_target_level"),
            "target_support_status": result.get("target_support_status"),
            "target_confidence": result.get("target_confidence"),
            "planning_summary": result.get("planning_summary", ""),
            "criteria_supported_for_target": result.get("criteria_supported_for_target", []),
            "gaps_to_reach_target": result.get("gaps_to_reach_target", []),
        }, indent=2),
        "Selected digital twin capabilities (feasible capabilities):\n" + ("\n".join(feasible_lines) if feasible_lines else "None"),
        "Available data and system context:\n" + outputs.get("1", "")[:9000],
        "Step 0 context:\n" + outputs.get("0", "")[:3000],
        "Step 2 selected capabilities context:\n" + outputs.get("2", "")[:7000],
        "Step 3 technical/deep-dive context:\n" + (outputs.get("3_part1", "") + "\n\n" + outputs.get("3_part2", ""))[:9000],
        "4R database steps for the required levels:\n" + json.dumps(step_bundle, indent=2),
        "4R evaluation details by level:\n" + json.dumps(evaluated.get("levels", {}), indent=2),
        "Criterion-specific evidence index:\n" + json.dumps(criterion_evidence_index, indent=2)[:12000],
    ]
    if dtaf_inputs.get("summary_text"):
        lines.append("DTAF summary:\n" + str(dtaf_inputs.get("summary_text", ""))[:5000])
    if extra_evidence.strip():
        lines.append("Additional user-provided evidence:\n" + extra_evidence[:5000])
    return "\n\n".join(lines)


def fourr_safe_action_items_extract(s: str) -> Dict[str, Any]:
    s = s.strip()
    try:
        return json.loads(s)
    except Exception:
        pass
    m = re.search(r"\{.*\}", s, flags=re.S)
    if not m:
        raise ValueError("Model did not return JSON for the 4R action items")
    return json.loads(m.group(0))


def fourr_generate_tailored_action_items_with_ollama(
    *,
    base_url: str,
    model: str,
    timeout: float,
    retries: int,
    prompt_bundle: str,
) -> Dict[str, Any]:
    messages = [
        {
            "role": "system",
            "content": (
                "Return ONLY JSON. You are improving a generated 4R Digital Twin Framework output inside a larger Digital Twin Analytical Framework workflow. "
                "Do not redo the 4R classification. Keep the recommended target level unless the evidence clearly contradicts it. "
                "Preserve the useful structure of the current output, but improve the specificity, scoring discipline, and use-case tailoring. "
                "Do not simply repeat database steps or generic framework language. Translate each relevant 4R step into practical implementation guidance for the actual system. "
                "Every example, data reference, and action item must be specific to the provided use case and sector. Remove unrelated examples carried over from other domains or prior case studies. "
                "Use the scoring rule exactly: 0 = not supported, 1 = partially supported or implied, 2 = clearly supported. Do not assign a 2 unless the evidence clearly and directly supports the gate criterion. Weak or vague evidence must stay partial or be marked as a gap."
            ),
        },
        {
            "role": "user",
            "content": (
                "Revise the current 4R output so it becomes a stronger, clearer, and more use-case-specific 4R target assessment and action-item plan.\n\n"
                "Important improvement goals:\n"
                "1. Keep the recommended target level unless the evidence clearly contradicts it.\n"
                "2. Do not redo the entire 4R classification from scratch.\n"
                "3. Preserve the useful structure of the current output, but improve the quality and specificity.\n"
                "4. Make the output specific to the actual use case.\n"
                "5. Replace unrelated examples with system-specific examples from the use case and available data.\n"
                "6. Improve every action item so it answers: what exactly should be done, what data/system/model/interface it involves, why it matters for the target level, what output or evidence should be produced, and what gap remains if needed detail is missing.\n\n"
                "Evidence and scoring rules:\n"
                "- Check consistency between scores, evidence, and rationale.\n"
                "- If the evidence only implies support, score it as partial rather than fully supported.\n"
                "- Do not say a criterion is supported if the evidence does not directly support it.\n"
                "- If the output says R1 is supported, make sure the evidence actually supports purpose, scope, boundaries, variables, data collection, storage, and data quality.\n"
                "- If the use case describes R3 or R4 goals such as prediction, optimization, or automated decision-making, but the feasible target is R1 or R2, clearly explain the distinction between the desired future vision and the current feasible build target.\n\n"
                "Action item improvement rules:\n"
                "- Do not repeat the same action item under multiple 4R levels unless it has a different purpose at each level.\n"
                "- Action items for lower levels must be included before the target level.\n"
                "- Do not include R3 or R4 action items unless they are clearly labeled as future work when the current target is lower.\n"
                "- Every action item must include a use-case-specific example and expected output or evidence.\n"
                "- If data is missing, identify the gap instead of pretending it exists.\n\n"
                "Output JSON EXACTLY in this shape:\n"
                "{\n"
                '  "section1_4r_target_summary": "...",\n'
                '  "section2_planning_summary": "...",\n'
                '  "section3_desired_future_vision_vs_current_feasible_target": "...",\n'
                '  "section4_tailored_4r_action_items": [\n'
                "    {\n"
                '      "fourr_level": "R1",\n'
                '      "action_item": "...",\n'
                '      "what_to_do": "...",\n'
                '      "why_it_matters": "...",\n'
                '      "use_case_specific_example": "...",\n'
                '      "required_data_or_inputs": ["..."],\n'
                '      "expected_output_or_evidence": "...",\n'
                '      "dependencies_or_gaps": "..."\n'
                "    }\n"
                "  ],\n"
                '  "section5_priority_action_list": ["..."],\n'
                '  "section6_missing_information_or_data_gaps": ["..."],\n'
                '  "section7_future_work_beyond_current_level": ["..."]\n'
                "}\n\n"
                "Quality check before finalizing your JSON:\n"
                "- All examples must be specific to the actual use case.\n"
                "- Unrelated examples must be removed.\n"
                "- Scores, evidence, and rationale must remain consistent with the current 4R assessment evidence bundle.\n"
                "- Weak evidence items must stay partial or be listed as gaps.\n"
                "- Action items must be practical, implementation-oriented, and tied to the selected capabilities.\n"
                "- Each action item must explain what evidence should be produced.\n"
                "- The output must clearly separate the current feasible target from future ambitions beyond that level.\n\n"
                f"Inputs:\n{prompt_bundle}"
            ),
        },
    ]
    out = chat_completions(
        base_url=base_url,
        model=model,
        messages=messages,
        max_tokens=4200,
        temperature=0.0,
        timeout=timeout,
        retries=retries,
    )
    return fourr_safe_action_items_extract(out)


def fourr_validate_action_items(obj: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(obj, dict):
        obj = {}
    items = obj.get("section4_tailored_4r_action_items", obj.get("section2_tailored_4r_action_items", []))
    if not isinstance(items, list):
        items = []
    normalized_items = []
    for item in items:
        if not isinstance(item, dict):
            continue
        req = item.get("required_data_or_inputs", [])
        if not isinstance(req, list):
            req = [str(req)] if str(req).strip() else []
        req = [str(x).strip() for x in req if str(x).strip()][:12]
        normalized_items.append({
            "fourr_level": str(item.get("fourr_level", "")).strip(),
            "action_item": str(item.get("action_item", "")).strip(),
            "what_to_do": str(item.get("what_to_do", "")).strip(),
            "why_it_matters": str(item.get("why_it_matters", "")).strip(),
            "use_case_specific_example": str(item.get("use_case_specific_example", "")).strip(),
            "required_data_or_inputs": req,
            "expected_output_or_evidence": str(item.get("expected_output_or_evidence", "")).strip(),
            "dependencies_or_gaps": str(item.get("dependencies_or_gaps", "")).strip(),
        })
    def _norm_list(value: Any) -> List[str]:
        if not isinstance(value, list):
            return []
        return [str(x).strip() for x in value if str(x).strip()][:25]
    return {
        "section1_4r_target_summary": str(obj.get("section1_4r_target_summary", "")).strip(),
        "section2_planning_summary": str(obj.get("section2_planning_summary", "")).strip(),
        "section3_desired_future_vision_vs_current_feasible_target": str(obj.get("section3_desired_future_vision_vs_current_feasible_target", "")).strip(),
        "section4_tailored_4r_action_items": normalized_items,
        "section5_priority_action_list": _norm_list(obj.get("section5_priority_action_list", obj.get("section3_priority_action_list", []))),
        "section6_missing_information_or_data_gaps": _norm_list(obj.get("section6_missing_information_or_data_gaps", obj.get("section4_missing_information_or_data_gaps", []))),
        "section7_future_work_beyond_current_level": _norm_list(obj.get("section7_future_work_beyond_current_level", obj.get("section5_future_work_beyond_current_level", []))),
    }


def fourr_attach_tailored_action_items(
    result: Dict[str, Any],
    tailored: Dict[str, Any],
    max_actions: int,
) -> Dict[str, Any]:
    result = dict(result)
    result["tailored_action_items"] = tailored
    items = tailored.get("section4_tailored_4r_action_items", []) if isinstance(tailored, dict) else []
    short_items: List[str] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        title = str(item.get("action_item", "")).strip()
        what = str(item.get("what_to_do", "")).strip()
        if title and what:
            short_items.append(f"{title}: {what}")
        elif title:
            short_items.append(title)
    if short_items:
        result["action_items_to_reach_target"] = short_items[:max_actions]
    if tailored.get("section6_missing_information_or_data_gaps"):
        result["missing_information_or_data_gaps"] = tailored.get("section6_missing_information_or_data_gaps", [])
    if tailored.get("section1_4r_target_summary"):
        result["target_action_summary"] = tailored.get("section1_4r_target_summary", "")
    if tailored.get("section2_planning_summary"):
        result["tailored_planning_summary"] = tailored.get("section2_planning_summary", "")
    if tailored.get("section3_desired_future_vision_vs_current_feasible_target"):
        result["desired_future_vision_vs_current_feasible_target"] = tailored.get("section3_desired_future_vision_vs_current_feasible_target", "")
    if tailored.get("section5_priority_action_list"):
        result["priority_action_list"] = tailored.get("section5_priority_action_list", [])
    if tailored.get("section7_future_work_beyond_current_level"):
        result["future_work_beyond_current_level"] = tailored.get("section7_future_work_beyond_current_level", [])
    return result

def fourr_result_to_markdown(result: Dict[str, Any], kb: Dict[str, Any]) -> str:
    levels = get_4r_levels_in_order(kb)
    lines = []
    recommended_level = str(result.get("recommended_target_level") or "R1")
    recommended_name = str(result.get("recommended_target_name") or recommended_level)
    current_level = str(result.get("current_supported_target_level") or recommended_level)
    current_name = str(result.get("current_supported_target_name") or current_level)
    next_level = str(result.get("near_term_next_target_level") or "").strip()
    next_name = str(result.get("near_term_next_target_name") or next_level).strip()
    explanation = f"The recommended pre-build 4R target for this use case is {recommended_level} ({recommended_name})."
    if current_level and current_level != recommended_level:
        explanation += f" The current evidence baseline is {current_level} ({current_name}), so some {recommended_level} evidence still needs to be produced during implementation."
    if next_level and next_level not in {recommended_level, current_level}:
        explanation += f" The next level beyond the current recommendation is {next_level} ({next_name}) once the remaining evidence and implementation gaps are closed."

    lines.append("# 4R Pre-Build Target Assessment")
    lines.append("")
    lines.append("This is a planning assessment for a digital twin before it is built. It distinguishes the recommended pre-build 4R target from the current evidence baseline, so the workflow can keep the intended build target while still showing which evidence is already explicit and which evidence is still missing.")
    lines.append("")
    lines.append("## Recommended Target Level")
    lines.append(f"- Recommended target level: **{recommended_level}** ({recommended_name})")
    lines.append(f"- Target support status: **{result.get('target_support_status', '')}**")
    if current_level:
        lines.append(f"- Current evidence baseline: **{current_level}** ({current_name})")
        lines.append(f"- Evidence baseline status: **{result.get('current_target_support_status', '')}**")
    lines.append(f"- Target confidence: **{result.get('target_confidence', '')}**")
    lines.append(f"- Explanation: {explanation}")
    if next_level and next_level != recommended_level:
        lines.append(f"- Near-term next target beyond the recommendation: **{next_level}** ({next_name})")
    lines.append("")

    lines.append("## Planning Summary")
    plan_summary = coerce_preferred_text(result.get("tailored_planning_summary") or result.get("planning_summary") or "", preferred_keys=['planning_summary'])
    if plan_summary:
        if next_level and next_level != current_level:
            lines.append(f"The recommended build target is {recommended_level}. The current evidence baseline is {current_level}. {plan_summary}")
        else:
            lines.append(plan_summary)
    else:
        lines.append(f"The current supported target is {current_level}.")
    lines.append("")

    lines.append("## Desired Future Vision vs. Current Feasible Target")
    if current_level and current_level != recommended_level:
        lines.append(f"The recommended pre-build target is {recommended_level}, while the current evidence baseline is {current_level}. This means the workflow should keep aiming at {recommended_level} while explicitly tracking which gate evidence still needs to be produced during implementation.")
    elif next_level and next_level != recommended_level:
        lines.append(f"The recommended pre-build target is {recommended_level}. The next level beyond that is {next_level}. Future work beyond the recommendation should stay clearly separated from the current build boundary.")
    else:
        lines.append(coerce_preferred_text(result.get("desired_future_vision_vs_current_feasible_target") or "No separate future-vision note was generated.", preferred_keys=['gap_explanation','rationale','future_vision','current_feasible_target']))
    lines.append("")

    lines.append("## Feasible capabilities used")
    if result.get("feasible_capabilities_used"):
        lines.append("| Capability | Priority | Readiness |")
        lines.append("|---|---:|---:|")
        for item in result["feasible_capabilities_used"]:
            cap_label = f"{item.get('cap_id', '')} - {item.get('cap_name', '')}".replace("|", "\\|")
            lines.append(f"| {cap_label} | {item.get('priority', '')} | {float(item.get('readiness_score', 0.0) or 0.0):.2f} |")
    else:
        lines.append("- No feasible capability list was available from the DTAF readiness screen.")
    lines.append("")

    lines.append("## 4R Level Support Status")
    lines.append("| 4R Level | Supported as Build Target | Evidence Strength | Main Reason | Key Gaps |")
    lines.append("|---|---|---|---|---|")
    for lvl in levels:
        lid = str(lvl["id"])
        st = result["level_status"].get(lid, {})
        evidence_strength = "strong" if st.get("current_supported") else ("partial" if st.get("partial_or_better", 0) > 0 else "weak")
        lvl_eval = result.get("level_evaluations", {}).get(lid, {})
        main_reason = (lvl_eval.get("summary", "") or "No strong supporting evidence.").replace("|", "\\|")
        gaps = []
        for g in lvl_eval.get("gate_scores", []):
            if int(g.get("score", 0)) < 2:
                gaps.append(str(g.get("criterion", "")))
        gap_text = "; ".join(gaps[:3]).replace("|", "\\|") if gaps else "None"
        if st.get('current_supported'):
            support_label = 'Yes'
        elif lid == recommended_level and str(result.get('target_support_status','')).lower().startswith('supported in planning'):
            support_label = 'Partial'
        elif st.get('planning_ready') or st.get('partial_or_better', 0) > 0:
            support_label = 'Partial'
        else:
            support_label = 'No'
        lines.append(f"| {lid} | {support_label} | {evidence_strength} | {main_reason} | {gap_text} |")
    lines.append("")

    lines.append("## Revised Gate Criteria Assessment")
    lines.append("| 4R Level | Gate Criterion | Score | Evidence | Rationale | Needed Improvement |")
    lines.append("|---|---|---:|---|---|---|")
    for lvl in levels:
        lid = str(lvl["id"])
        for g in result["level_evaluations"].get(lid, {}).get("gate_scores", []):
            evidence = (g.get("evidence", "") or "").replace("|", "\\|")
            rationale = (g.get("rationale", "") or "").replace("|", "\\|")
            criterion = (g.get("criterion", "") or "").replace("|", "\\|")
            score = int(g.get("score", 0))
            needed = "None" if score == 2 else ("Strengthen with direct, use-case-specific evidence and a reviewable deliverable." if score == 1 else "Add explicit evidence, data, or design detail before claiming support.")
            lines.append(f"| {lid} | {criterion} | {score} | {evidence} | {rationale} | {needed} |")
    lines.append("")

    tailored = result.get("tailored_action_items", {}) if isinstance(result.get("tailored_action_items", {}), dict) else {}
    lines.append("## Tailored 4R Action Items")
    if tailored.get("section4_tailored_4r_action_items"):
        lines.append("| 4R Level | Action Item | What to Do | Why It Matters | Use-Case-Specific Example | Required Data or Inputs | Expected Output or Evidence | Dependencies or Gaps |")
        lines.append("|---|---|---|---|---|---|---|---|")
        for item in tailored.get("section4_tailored_4r_action_items", []):
            req = "; ".join(item.get("required_data_or_inputs", []))
            lines.append(
                f"| {item.get('fourr_level','')} | {item.get('action_item','').replace('|','/')} | {item.get('what_to_do','').replace('|','/')} | {item.get('why_it_matters','').replace('|','/')} | {item.get('use_case_specific_example','').replace('|','/')} | {req.replace('|','/')} | {item.get('expected_output_or_evidence','').replace('|','/')} | {item.get('dependencies_or_gaps','').replace('|','/')} |"
            )
    else:
        if result.get("action_items_to_reach_target"):
            for item in result["action_items_to_reach_target"]:
                lines.append(f"- {item}")
        else:
            lines.append("- No tailored 4R action items were generated.")
    lines.append("")

    lines.append("## Priority Action List")
    if tailored.get("section5_priority_action_list"):
        for i, item in enumerate(tailored.get("section5_priority_action_list", []), 1):
            lines.append(f"{i}. {item}")
    else:
        for i, item in enumerate(result.get("action_items_to_reach_target", []), 1):
            lines.append(f"{i}. {item}")
    lines.append("")

    lines.append("## Missing Information or Data Gaps")
    gaps = tailored.get("section6_missing_information_or_data_gaps", []) or result.get("gaps_to_reach_target", [])
    if gaps:
        for item in gaps:
            lines.append(f"- {item}")
    else:
        lines.append("- None")
    lines.append("")

    future = tailored.get("section7_future_work_beyond_current_level", []) or result.get("future_work_beyond_current_level", [])
    if future or (next_level and next_level != current_level):
        lines.append("## Future Work Beyond Current 4R Level")
        if next_level and next_level != current_level:
            lines.append(f"- Advance from {current_level} to {next_level} by closing the remaining evidence and implementation gaps for the next level.")
        for item in future:
            lines.append(f"- {item}")
        lines.append("")

    return "\n".join(lines).strip() + "\n"

def load_4r_inputs_for_4s(fourr_outdir: Optional[Path]) -> Dict[str, Any]:
    out = {
        "summary_text": "",
        "result": {},
    }
    if fourr_outdir is None or not fourr_outdir.exists():
        return out

    summary_path = fourr_outdir / "4r_assessment_summary.md"
    result_path = fourr_outdir / "4r_assessment_result.json"

    if summary_path.exists():
        out["summary_text"] = read_text(summary_path)
    if result_path.exists():
        try:
            data = read_json(result_path)
            if isinstance(data, dict):
                out["result"] = data
        except Exception:
            pass
    return out


def compact_priorities_for_4s(priorities: Dict[str, str]) -> List[Dict[str, str]]:
    rows = []
    for cid, pri in priorities.items():
        rows.append({
            "cap_id": cid,
            "cap_name": CAP_NAME.get(cid, ""),
            "priority": str(pri).strip(),
        })
    rows.sort(key=lambda x: (CAP_ORDER.get(x["cap_id"], 10_000), x["cap_id"]))
    return rows


def run_4r_assessment_addon(
    *,
    dtc_outdir: Path,
    log_path: Path,
    fourr_kb_path: Path,
    sector: str,
    problem_statement: str,
    outputs: Dict[str, str],
    priorities: Dict[str, str],
    dtaf_outdir: Optional[Path],
    extra_evidence: str,
    base_url: str,
    model: str,
    timeout: float,
    retries: int,
    max_actions: int,
    intended_target_level: Optional[str] = None,
) -> Path:
    kb = load_4r_kb(fourr_kb_path)
    dtaf_inputs = load_dtaf_4r_inputs(dtaf_outdir)
    criterion_evidence_index = build_4r_criterion_evidence_index(
        kb=kb,
        sector=sector,
        problem_statement=problem_statement,
        outputs=outputs,
        priorities=priorities,
        dtaf_summary_text=dtaf_inputs.get("summary_text", ""),
        extra_evidence=extra_evidence,
        feasible_capabilities=dtaf_inputs.get("feasible_capabilities", []),
    )
    evidence_bundle = build_4r_evidence_bundle(
        kb=kb,
        sector=sector,
        problem_statement=problem_statement,
        outputs=outputs,
        priorities=priorities,
        dtaf_summary_text=dtaf_inputs.get("summary_text", ""),
        extra_evidence=extra_evidence,
        feasible_capabilities=dtaf_inputs.get("feasible_capabilities", []),
        screen_results=dtaf_inputs.get("screen_results", []),
        criterion_evidence_index=criterion_evidence_index,
    )

    raw_obj = fourr_generate_level_scores_with_ollama(
        base_url=base_url,
        model=model,
        timeout=timeout,
        retries=retries,
        kb=kb,
        evidence_bundle=evidence_bundle,
    )
    evaluated = fourr_validate_evaluation(kb, raw_obj)
    evaluated = fourr_reconcile_evaluation_with_evidence(
        kb=kb,
        evaluated=evaluated,
        criterion_evidence_index=criterion_evidence_index,
    )
    evaluated = fourr_postprocess_evaluated(evaluated, sector, problem_statement)
    result = fourr_compute_result(
        kb=kb,
        evaluated=evaluated,
        feasible_capabilities=dtaf_inputs.get("feasible_capabilities", []),
        max_actions=max_actions,
        intended_target_level=intended_target_level,
    )
    result = fourr_postprocess_result(result, sector, problem_statement)

    tailored_action_raw: Dict[str, Any] = {}
    tailored_action_items: Dict[str, Any] = {}
    try:
        action_prompt_bundle = fourr_build_tailored_action_items_prompt(
            kb=kb,
            sector=sector,
            problem_statement=problem_statement,
            outputs=outputs,
            evaluated=evaluated,
            result=result,
            dtaf_inputs=dtaf_inputs,
            criterion_evidence_index=criterion_evidence_index,
            extra_evidence=extra_evidence,
        )
        tailored_action_raw = fourr_generate_tailored_action_items_with_ollama(
            base_url=base_url,
            model=model,
            timeout=timeout,
            retries=retries,
            prompt_bundle=action_prompt_bundle,
        )
        tailored_action_items = fourr_validate_action_items(tailored_action_raw)
        tailored_action_items = fourr_postprocess_tailored_action_items(tailored_action_items, sector, problem_statement)
        result = fourr_attach_tailored_action_items(result, tailored_action_items, max_actions=max_actions)
        result = fourr_postprocess_result(result, sector, problem_statement)
    except Exception as e:
        print(f"[warn] tailored 4R action item generation failed: {e}")
        action_prompt_bundle = ""

    outdir = dtc_outdir / f"fourr_assessment_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
    ensure_dir(outdir)
    write_text(outdir / "4r_kb_compact.json", json.dumps(compact_4r_kb_for_prompt(kb), indent=2))
    write_text(outdir / "4r_evidence_bundle.txt", evidence_bundle)
    write_text(outdir / "4r_criterion_evidence_index.json", json.dumps(criterion_evidence_index, indent=2))
    write_text(outdir / "4r_dtaf_inputs.json", json.dumps(dtaf_inputs, indent=2))
    write_text(outdir / "4r_assessment_raw.json", json.dumps(raw_obj, indent=2))
    write_text(outdir / "4r_assessment_evaluated.json", json.dumps(evaluated, indent=2))
    if action_prompt_bundle:
        write_text(outdir / "4r_action_items_prompt_bundle.txt", action_prompt_bundle)
    if tailored_action_raw:
        write_text(outdir / "4r_action_items_raw.json", json.dumps(tailored_action_raw, indent=2))
    if tailored_action_items:
        write_text(outdir / "4r_action_items_validated.json", json.dumps(tailored_action_items, indent=2))
    write_text(outdir / "4r_assessment_result.json", json.dumps(result, indent=2))
    write_text(outdir / "4r_assessment_summary.md", fourr_result_to_markdown(result, kb))

    append_jsonl(
        log_path,
        {
            "step": "4R_assessment_addon",
            "time_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "output_path": str((outdir / "4r_assessment_summary.md").name),
        },
    )

    print("\n4R assessment complete.")
    print(f"Saved: {outdir.resolve()}")
    print(f" - {outdir / '4r_assessment_summary.md'}")
    print(f" - {outdir / '4r_assessment_result.json'}\n")
    return outdir


# -----------------------------
# 4S assessment add-on
# -----------------------------



def load_4s_kb(path: Path) -> Dict[str, Any]:
    obj = read_json(path)
    if not isinstance(obj, dict):
        raise ValueError("4S knowledge base JSON must be an object at the top level")
    if "levels" not in obj or not isinstance(obj["levels"], list) or not obj["levels"]:
        raise ValueError("4S knowledge base JSON must contain a non-empty 'levels' list")
    return obj


def get_4s_levels_in_order(kb: Dict[str, Any]) -> List[Dict[str, Any]]:
    levels = [lvl for lvl in kb.get("levels", []) if isinstance(lvl, dict) and lvl.get("level_id")]
    def sort_key(x: Dict[str, Any]) -> int:
        m = re.search(r"(\d+)", str(x.get("level_id", "")))
        return int(m.group(1)) if m else 999
    levels.sort(key=sort_key)
    return levels


def compact_4s_kb_for_prompt(kb: Dict[str, Any]) -> Dict[str, Any]:
    levels_out = []
    for lvl in get_4s_levels_in_order(kb):
        steps_out = []
        for step in lvl.get("how_to_achieve_level", []):
            if not isinstance(step, dict):
                continue
            substeps = []
            for sub in step.get("sub_steps", []):
                if not isinstance(sub, dict):
                    continue
                substeps.append({
                    "sub_step_number": str(sub.get("sub_step_number", "")).strip(),
                    "sub_step_text": str(sub.get("sub_step_text", "")).strip(),
                    "example": str(sub.get("example", "")).strip(),
                })
            steps_out.append({
                "step_number": str(step.get("step_number", "")).strip(),
                "step_title": str(step.get("step_title", "")).strip(),
                "sub_steps": substeps,
            })
        levels_out.append({
            "level_id": str(lvl.get("level_id", "")).strip(),
            "level_name": str(lvl.get("level_name", "")).strip(),
            "level_summary": str(lvl.get("level_summary", "")).strip(),
            "key_check": str(lvl.get("key_check", "")).strip(),
            "how_to_achieve_level": steps_out,
        })
    return {
        "framework_name": kb.get("framework_name", "4S Framework"),
        "framework_description": kb.get("framework_description", ""),
        "distinction_from_digital_twin": kb.get("distinction_from_digital_twin", ""),
        "levels": levels_out,
    }


def load_4r_inputs_for_4s(fourr_outdir: Optional[Path]) -> Dict[str, Any]:
    out = {
        "summary_text": "",
        "result": {},
    }
    if fourr_outdir is None or not fourr_outdir.exists():
        return out

    summary_path = fourr_outdir / "4r_assessment_summary.md"
    result_path = fourr_outdir / "4r_assessment_result.json"

    if summary_path.exists():
        out["summary_text"] = read_text(summary_path)
    if result_path.exists():
        try:
            data = read_json(result_path)
            if isinstance(data, dict):
                out["result"] = data
        except Exception:
            pass
    return out


def compact_priorities_for_4s(priorities: Dict[str, str]) -> List[Dict[str, str]]:
    rows = []
    for cid, pri in priorities.items():
        rows.append({
            "cap_id": cid,
            "cap_name": CAP_NAME.get(cid, ""),
            "priority": str(pri).strip(),
        })
    rows.sort(key=lambda x: (CAP_ORDER.get(x["cap_id"], 10_000), x["cap_id"]))
    return rows




def build_4s_evidence_bundle(
    *,
    kb: Dict[str, Any],
    sector: str,
    problem_statement: str,
    outputs: Dict[str, str],
    priorities: Dict[str, str],
    dtaf_inputs: Dict[str, Any],
    fourr_inputs: Dict[str, Any],
    extra_evidence: str,
) -> str:
    fourr_result = fourr_inputs.get("result", {}) if isinstance(fourr_inputs, dict) else {}
    selected_caps = compact_priorities_for_4s(priorities)
    feasible_caps = dtaf_inputs.get("feasible_capabilities", []) if isinstance(dtaf_inputs, dict) else []

    parts = []
    parts.append("You are improving a generated 4S Simulation Classification output for a digital twin use case inside a larger Digital Twin Analytical Framework workflow.")
    parts.append("Treat 4S as a simulation classification and interpretation layer after 4R. Do not redo 4R and do not restart the digital twin workflow.")
    parts.append("")
    parts.append("Original use case description:")
    parts.append(f"Sector: {sector}")
    parts.append(problem_statement.strip())
    parts.append("")

    parts.append("Existing 4R classification:")
    if fourr_result:
        parts.append(json.dumps({
            "current_supported_target_level": fourr_result.get("current_supported_target_level"),
            "current_supported_target_name": fourr_result.get("current_supported_target_name"),
            "near_term_next_target_level": fourr_result.get("near_term_next_target_level"),
            "near_term_next_target_name": fourr_result.get("near_term_next_target_name"),
            "recommended_target_level": fourr_result.get("recommended_target_level"),
            "recommended_target_name": fourr_result.get("recommended_target_name"),
            "highest_supported_target_level": fourr_result.get("highest_supported_target_level"),
            "target_support_status": fourr_result.get("target_support_status"),
            "target_confidence": fourr_result.get("target_confidence"),
            "planning_summary": fourr_result.get("planning_summary", ""),
            "desired_future_vision_vs_current_feasible_target": fourr_result.get("desired_future_vision_vs_current_feasible_target", ""),
            "criteria_supported_for_target": fourr_result.get("criteria_supported_for_target", []),
            "gaps_to_reach_target": fourr_result.get("gaps_to_reach_target", []),
            "action_items_to_reach_target": fourr_result.get("action_items_to_reach_target", []),
            "tailored_action_items": fourr_result.get("tailored_action_items", []),
        }, indent=2))
    else:
        parts.append("No 4R result JSON was found. If no 4R result is available, do not redo 4R. Instead note that 4S depends on an existing 4R result.")
    parts.append("")

    parts.append("Selected digital twin capabilities:")
    parts.append(json.dumps({
        "selected_capabilities_from_step2": selected_caps,
        "feasible_capabilities_from_dtaf": feasible_caps,
    }, indent=2))
    parts.append("")

    parts.append("Current 4R action items:")
    if fourr_result.get("tailored_action_items"):
        parts.append(json.dumps(fourr_result.get("tailored_action_items", []), indent=2))
    elif fourr_result.get("action_items_to_reach_target"):
        parts.append(json.dumps(fourr_result.get("action_items_to_reach_target", []), indent=2))
    else:
        parts.append("[]")
    parts.append("")

    parts.append("Available data and system context:")
    parts.append("Step 0 output:\n" + outputs.get("0", "")[:4000])
    parts.append("")
    parts.append("Step 1 output:\n" + outputs.get("1", "")[:7000])
    parts.append("")
    parts.append("Step 2 output:\n" + outputs.get("2", "")[:5000])
    parts.append("")
    parts.append("Step 3 output:\n" + outputs.get("3_combined", outputs.get("3_part1", "") + "\n\n" + outputs.get("3_part2", ""))[:7000])
    if dtaf_inputs.get("summary_text"):
        parts.append("")
        parts.append("DTAF summary:\n" + str(dtaf_inputs.get("summary_text", ""))[:4000])
    if fourr_inputs.get("summary_text"):
        parts.append("")
        parts.append("4R summary:\n" + str(fourr_inputs.get("summary_text", ""))[:5000])
    if extra_evidence:
        parts.append("")
        parts.append("Additional user-provided 4S evidence:\n" + extra_evidence[:8000])

    parts.append("")
    parts.append("Important revision rules:")
    parts.append("- Do not redo the 4R classification.")
    parts.append("- Do not create a full simulation build plan.")
    parts.append("- Treat 4S as a classification and interpretation layer.")
    parts.append("- Use the recommended 4R target from the 4R result as the current simulation boundary. If the recommended 4R target is R1, keep 4S at S1. If it is R2, keep the current 4S target at S1 or S2 unless the evidence clearly supports more.")
    parts.append("- Do not describe S2 using prediction or prescription language.")
    parts.append("- If the use case mentions prediction, optimization, automation, or decision-making, explain that these are future S3 or S4 goals unless the current evidence supports them.")
    parts.append("- Complete the interpretation for S1, S2, S3, and S4. Do not leave S3 or S4 blank.")
    parts.append("- Mark S3 and S4 as Future or Not currently supported when evidence is insufficient.")
    parts.append("- Use domain-specific simulation examples drawn directly from the provided use case, system description, data sources, states, constraints, and decisions. Do not import examples from unrelated sectors.")
    parts.append("- Keep the output aligned with the existing 4R classification and action items.")
    return "\n".join(parts).strip()


def fours_safe_json_extract(s: str) -> Dict[str, Any]:
    s = s.strip()
    try:
        return json.loads(s)
    except Exception:
        pass
    m = re.search(r"\{.*\}", s, flags=re.S)
    if not m:
        raise ValueError("Model did not return JSON for the 4S assessment")
    return json.loads(m.group(0))


def fours_generate_classification_with_ollama(
    *,
    base_url: str,
    model: str,
    timeout: float,
    retries: int,
    kb: Dict[str, Any],
    evidence_bundle: str,
) -> Dict[str, Any]:
    kb_compact = compact_4s_kb_for_prompt(kb)
    messages = [
        {
            "role": "system",
            "content": (
                "Return ONLY JSON. You are improving a generated 4S Simulation Classification output after an existing 4R assessment in a larger Digital Twin Analytical Framework workflow. "
                "Do not redo 4R. Treat 4S as a simulation classification and interpretation layer that explains what simulation capability is needed to support the existing 4R target. "
                "Do not create a full simulation build plan. Do not automatically assign the highest 4S level. Keep the answer tightly aligned to the use case, the 4R result, and the selected capabilities."
            ),
        },
        {
            "role": "user",
            "content": (
                "Revise the 4S output so it is clearer, more internally consistent, and better aligned with the existing 4R classification. Keep the recommendation grounded in the evidence.\n\n"
                "Return JSON with EXACTLY these top-level keys:\n"
                "{\n"
                '  "section1_4r_context_summary": "...",\n'
                '  "recommended_4s_level": "S1|S2|S3|S4",\n'
                '  "recommended_4s_name": "...",\n'
                '  "simulation_required": "Yes|No|Partial",\n'
                '  "reason": "...",\n'
                '  "why_s1_is_included": "...",\n'
                '  "why_s2_is_the_current_target": "...",\n'
                '  "why_s3_is_future_work": "...",\n'
                '  "why_s4_is_future_work": "...",\n'
                '  "current_feasible_simulation_target_vs_future_simulation_vision": "...",\n'
                '  "interpretation_table": [\n'
                '    {\n'
                '      "level_id": "S1",\n'
                '      "level_name": "Modeling",\n'
                '      "needed": "Yes|No|Partial|Future|Not currently supported",\n'
                '      "use_case_specific_interpretation": "...",\n'
                '      "required_data_or_model_evidence": "...",\n'
                '      "notes_or_gaps": "..."\n'
                '    }\n'
                '  ],\n'
                '  "connection_to_4r_action_items": [\n'
                '    {\n'
                '      "existing_4r_action_item": "...",\n'
                '      "related_4s_level": "S1|S2|S3|S4",\n'
                '      "how_4s_modifies_or_clarifies_the_action_item": "...",\n'
                '      "use_case_specific_example": "..."\n'
                '    }\n'
                '  ],\n'
                '  "implementation_guidance": ["..."],\n'
                '  "gaps_before_advancing_to_higher_4s_levels": ["..."]\n'
                "}\n\n"
                "Requirements:\n"
                "- Keep Section 1 as a short 4R context summary.\n"
                "- In Section 2, explain why the recommended 4S level is the current feasible level.\n"
                "- Explain that S1 is included because the system must first be modeled before it can be analyzed.\n"
                "- Do not describe S2 using prediction or prescription language. S2 is for comparison, diagnostics, performance evaluation, sensitivity analysis, or validation against current or recorded system behavior.\n"
                "- If the use case mentions prediction, optimization, automation, or decision-making, explain that these are future S3 or S4 goals unless the current evidence supports them.\n"
                "- Complete the interpretation table for S1, S2, S3, and S4. Do not leave S3 or S4 blank.\n"
                "- Mark S3 and S4 as Future or Not currently supported when evidence is insufficient.\n"
                "- Connect 4S to the existing 4R action items without turning it into a full build plan.\n"
                "- Use domain-specific examples drawn from the provided use case. For S2, use analysis examples that compare simulated or virtual behavior to actual or recorded system behavior under known operating conditions, and avoid examples from unrelated sectors.\n"
                "- Do not use S2 examples that drift into future prediction or prescriptive action selection.\n"
                "- Clearly distinguish the current feasible simulation target from the future simulation vision.\n\n"
                f"4S knowledge base:\n{json.dumps(kb_compact, indent=2)}\n\n"
                f"Workflow evidence bundle:\n{evidence_bundle}\n"
            ),
        },
    ]

    out = chat_completions(
        base_url=base_url,
        model=model,
        messages=messages,
        max_tokens=3600,
        temperature=0.0,
        timeout=timeout,
        retries=retries,
    )
    return fours_safe_json_extract(out)


def fours_validate_result(kb: Dict[str, Any], obj: Dict[str, Any]) -> Dict[str, Any]:
    level_defs = {str(lvl.get("level_id")): lvl for lvl in get_4s_levels_in_order(kb)}
    ordered_ids = [str(lvl.get("level_id")) for lvl in get_4s_levels_in_order(kb) if lvl.get("level_id")]
    valid_ids = set(ordered_ids)
    level_rank = {lid: i for i, lid in enumerate(ordered_ids)}

    result = {
        "section1_4r_context_summary": str(obj.get("section1_4r_context_summary", "")).strip(),
        "recommended_4s_level": str(obj.get("recommended_4s_level", "")).strip(),
        "recommended_4s_name": str(obj.get("recommended_4s_name", "")).strip(),
        "simulation_required": str(obj.get("simulation_required", "Partial")).strip().title(),
        "reason": str(obj.get("reason", "")).strip(),
        "why_s1_is_included": str(obj.get("why_s1_is_included", "")).strip(),
        "why_s2_is_the_current_target": str(obj.get("why_s2_is_the_current_target", "")).strip(),
        "why_s3_is_future_work": str(obj.get("why_s3_is_future_work", "")).strip(),
        "why_s4_is_future_work": str(obj.get("why_s4_is_future_work", "")).strip(),
        "current_feasible_simulation_target_vs_future_simulation_vision": str(obj.get("current_feasible_simulation_target_vs_future_simulation_vision", "")).strip(),
        "interpretation_table": [],
        "connection_to_4r_action_items": [],
        "implementation_guidance": [str(x).strip() for x in obj.get("implementation_guidance", []) if str(x).strip()],
        "gaps_before_advancing_to_higher_4s_levels": [str(x).strip() for x in obj.get("gaps_before_advancing_to_higher_4s_levels", []) if str(x).strip()],
    }

    if result["recommended_4s_level"] not in valid_ids:
        result["recommended_4s_level"] = ordered_ids[0] if ordered_ids else "S1"
    if not result["recommended_4s_name"]:
        result["recommended_4s_name"] = str(level_defs.get(result["recommended_4s_level"], {}).get("level_name", result["recommended_4s_level"]))
    if result["simulation_required"] not in {"Yes", "No", "Partial"}:
        result["simulation_required"] = "Partial"

    allowed_needed = {"Yes", "No", "Partial", "Future", "Not currently supported"}

    def normalize_needed(val: str, lid: str) -> str:
        v = (val or "").strip()
        mapping = {
            "yes": "Yes",
            "no": "No",
            "partial": "Partial",
            "future": "Future",
            "not currently supported": "Not currently supported",
            "unsupported": "Not currently supported",
            "not supported": "Not currently supported",
        }
        norm = mapping.get(v.lower(), v)
        if norm in allowed_needed:
            return norm

        rec_rank = level_rank.get(result["recommended_4s_level"], 0)
        lid_rank = level_rank.get(lid, 0)
        if lid == "S1":
            return "Yes"
        if lid_rank <= rec_rank:
            return "Yes"
        return "Future"

    raw_rows = obj.get("interpretation_table", [])
    row_map: Dict[str, Dict[str, str]] = {}
    if isinstance(raw_rows, list):
        for row in raw_rows:
            if not isinstance(row, dict):
                continue
            lid = str(row.get("level_id", "")).strip()
            if lid not in valid_ids:
                continue
            row_map[lid] = {
                "level_id": lid,
                "level_name": str(row.get("level_name", "")).strip() or str(level_defs[lid].get("level_name", lid)),
                "needed": normalize_needed(str(row.get("needed", "")).strip(), lid),
                "use_case_specific_interpretation": str(row.get("use_case_specific_interpretation", "")).strip(),
                "required_data_or_model_evidence": str(row.get("required_data_or_model_evidence", "")).strip(),
                "notes_or_gaps": str(row.get("notes_or_gaps", "")).strip(),
            }

    for lvl in get_4s_levels_in_order(kb):
        lid = str(lvl.get("level_id"))
        default_needed = normalize_needed("", lid)
        row = row_map.get(lid, {
            "level_id": lid,
            "level_name": str(lvl.get("level_name", lid)),
            "needed": default_needed,
            "use_case_specific_interpretation": "",
            "required_data_or_model_evidence": "",
            "notes_or_gaps": "",
        })
        row["needed"] = normalize_needed(row.get("needed", ""), lid)
        result["interpretation_table"].append(row)

    raw_links = obj.get("connection_to_4r_action_items", [])
    if isinstance(raw_links, list):
        for row in raw_links:
            if not isinstance(row, dict):
                continue
            lid = str(row.get("related_4s_level", "")).strip()
            if lid not in valid_ids:
                lid = result["recommended_4s_level"]
            result["connection_to_4r_action_items"].append({
                "existing_4r_action_item": str(row.get("existing_4r_action_item", "")).strip(),
                "related_4s_level": lid,
                "how_4s_modifies_or_clarifies_the_action_item": str(row.get("how_4s_modifies_or_clarifies_the_action_item", "")).strip(),
                "use_case_specific_example": str(row.get("use_case_specific_example", "")).strip(),
            })

    return result


def fours_result_to_markdown(result: Dict[str, Any], kb: Dict[str, Any], current_target_level: str = "") -> str:
    lines: List[str] = []
    lines.append("# 4S Simulation Classification")
    lines.append("")
    lines.append("This step uses the existing 4R output and selected digital twin capabilities to determine what simulation capability is needed. It does not redo 4R and it does not restart the digital twin development workflow.")
    lines.append("")

    target_level = str(current_target_level).strip().upper()
    target_label = target_level if target_level else "Current Target"
    lines.append("## Section 1: 4R Context Summary")
    lines.append("")
    lines.append(result.get("section1_4r_context_summary", "") or "No 4R context summary was produced.")
    lines.append("")

    lines.append("## Section 2: Recommended 4S Classification")
    lines.append("")
    lines.append(f"- **Recommended 4S level:** {result.get('recommended_4s_level', '')} ({result.get('recommended_4s_name', '')})")
    lines.append(f"- **Simulation required?:** {result.get('simulation_required', 'Partial')}")
    lines.append(f"- **Reason:** {result.get('reason', '')}")
    lines.append(f"- **Why S1 is included:** {result.get('why_s1_is_included', '')}")
    s2_label = "Why S2 is the near-term next target" if str(result.get('recommended_4s_level','')).strip().upper() == 'S1' else "Why S2 is the current target"
    lines.append(f"- **{s2_label}:** {result.get('why_s2_is_the_current_target', '')}")
    lines.append(f"- **Why S3 is future work:** {result.get('why_s3_is_future_work', '')}")
    lines.append(f"- **Why S4 is future work:** {result.get('why_s4_is_future_work', '')}")
    lines.append("")

    if target_level:
        lines.append(f"## Section 3: Current Feasible Simulation Target vs. Future Simulation Vision ({target_label})")
    else:
        lines.append("## Section 3: Current Feasible Simulation Target vs. Future Simulation Vision")
    lines.append("")
    lines.append(result.get("current_feasible_simulation_target_vs_future_simulation_vision", "") or "No current-versus-future simulation interpretation was produced.")
    lines.append("")

    lines.append("## Section 4: 4S Interpretation for This Use Case")
    lines.append("")
    lines.append("| 4S Level | Needed? | Use-Case-Specific Interpretation | Required Data or Model Evidence | Notes or Gaps |")
    lines.append("|---|---|---|---|---|")
    for row in result.get("interpretation_table", []):
        lvl = f"{row.get('level_id', '')} ({row.get('level_name', '')})"
        lines.append(
            f"| {lvl} | {row.get('needed', '')} | {row.get('use_case_specific_interpretation', '').replace('|', '/')} | {row.get('required_data_or_model_evidence', '').replace('|', '/')} | {row.get('notes_or_gaps', '').replace('|', '/')} |"
        )
    lines.append("")

    lines.append("## Section 5: Connection to Existing 4R Action Items")
    lines.append("")
    if result.get("connection_to_4r_action_items"):
        lines.append("| Existing 4R Action Item | Related 4S Level | How 4S Clarifies the Action Item | Use-Case-Specific Example |")
        lines.append("|---|---|---|---|")
        for row in result.get("connection_to_4r_action_items", []):
            lines.append(
                f"| {row.get('existing_4r_action_item', '').replace('|', '/')} | {row.get('related_4s_level', '')} | {row.get('how_4s_modifies_or_clarifies_the_action_item', '').replace('|', '/')} | {row.get('use_case_specific_example', '').replace('|', '/')} |"
            )
    else:
        lines.append("No specific 4R action items were linked to 4S in this run.")
    lines.append("")

    lines.append("## Section 6: Implementation Guidance")
    lines.append("")
    if result.get("implementation_guidance"):
        for item in result.get("implementation_guidance", []):
            lines.append(f"- {item}")
    else:
        lines.append("- No additional 4S implementation guidance was generated.")
    lines.append("")

    lines.append("## Section 7: Gaps Before Advancing to Higher 4S Levels")
    lines.append("")
    if result.get("gaps_before_advancing_to_higher_4s_levels"):
        for item in result.get("gaps_before_advancing_to_higher_4s_levels", []):
            lines.append(f"- {item}")
    else:
        lines.append("- No major gaps were listed for advancing to a higher 4S level.")
    lines.append("")

    return "\n".join(lines).strip() + "\n"


def build_heuristic_4s_raw_obj(
    *,
    kb: Dict[str, Any],
    sector: str,
    problem_statement: str,
    fourr_result: Dict[str, Any],
) -> Dict[str, Any]:
    target = get_current_4r_target_level_for_dtv(fourr_result) or "R1"
    level_map = {"R1": "S1", "R2": "S2", "R3": "S3", "R4": "S4"}
    level_name_map = {"S1": "Modeling", "S2": "Analyzing", "S3": "Predicting", "S4": "Prescribing"}
    rec = level_map.get(target, "S1")
    planning = coerce_preferred_text(fourr_result.get("planning_summary", ""), preferred_keys=["planning_summary"])
    context = f"The existing 4R assessment recommends {target} as the current pre-build target for this use case. {planning}".strip()
    reason_map = {
        "S1": "The current build target mainly requires a structured model of the system, its boundaries, variables, and relationships.",
        "S2": "The current R2 replication target requires the system to be modeled first and then analyzed against recorded or live behavior, so S2 is the appropriate current 4S level.",
        "S3": "The current R3 target requires predictive or scenario-exploration capability beyond basic analysis, so S3 is the appropriate current 4S level.",
        "S4": "The current R4 target requires prescriptive or decision-selecting simulation support, so S4 is the appropriate current 4S level.",
    }
    table = []
    for lid, lname in [("S1","Modeling"),("S2","Analyzing"),("S3","Predicting"),("S4","Prescribing")]:
        needed = "Future"
        if lid == "S1":
            needed = "Yes"
        elif rec == "S2" and lid == "S2":
            needed = "Yes"
        elif rec == "S3" and lid in {"S2","S3"}:
            needed = "Yes"
        elif rec == "S4" and lid in {"S2","S3","S4"}:
            needed = "Yes"
        interp = ""
        evidence = ""
        notes = ""
        if lid == "S1":
            interp = "Represent the system structure, key variables, states, flows, and logic needed for the current use case."
            evidence = "System boundaries, variables, inputs, outputs, and a model structure that matches the intended use."
        elif lid == "S2":
            interp = "Use the model to compare, diagnose, and evaluate how the current system behaves under known or recorded conditions."
            evidence = "Recorded or live data, comparison cases, performance measures, and model-to-system checks."
            notes = "S2 is the current target for an R2 replication-focused twin." if rec == "S2" else "Move to S2 once the model structure and comparison cases are ready."
        elif lid == "S3":
            interp = "Use the model to estimate future outcomes or unobserved scenarios."
            evidence = "Prediction targets, historical outcome data, and validation metrics for predictive performance."
            notes = "Future work until predictive targets and validation metrics are explicitly defined."
        elif lid == "S4":
            interp = "Use the model to recommend settings, actions, or decisions based on objectives and constraints."
            evidence = "Objective functions, decision rules, constraints, and validation criteria for recommended actions."
            notes = "Future work until decision rules, optimization constraints, and trust controls are defined."
        table.append({
            "level_id": lid,
            "level_name": lname,
            "needed": needed,
            "use_case_specific_interpretation": interp,
            "required_data_or_model_evidence": evidence,
            "notes_or_gaps": notes,
        })
    return {
        "section1_4r_context_summary": context,
        "recommended_4s_level": rec,
        "recommended_4s_name": level_name_map[rec],
        "simulation_required": "Yes",
        "reason": reason_map[rec],
        "why_s1_is_included": "S1 is always included because the system must be modeled before it can be analyzed, predicted, or prescribed.",
        "why_s2_is_the_current_target": ("S2 is the current target because the recommended 4R target is R2 and the main simulation need is to analyze and compare modeled behavior to recorded or live system behavior." if rec == "S2" else "S2 is the near-term next target once an initial model structure, inputs, outputs, and comparison cases are defined for the use case."),
        "why_s3_is_future_work": "S3 is future work until explicit prediction targets, historical outcome data, and predictive validation metrics are defined." if rec in {"S1","S2"} else "",
        "why_s4_is_future_work": "S4 is future work until objective functions, decision rules, optimization constraints, and trust controls are defined." if rec in {"S1","S2","S3"} else "",
        "current_feasible_simulation_target_vs_future_simulation_vision": f"The recommended 4R target is {target}, so the current feasible simulation boundary is {rec}. Higher 4S levels should be treated as future work until the required targets, data, rules, and validation evidence are explicitly defined.",
        "interpretation_table": table,
        "connection_to_4r_action_items": [],
        "implementation_guidance": [
            "Use the simulation to support the current 4R target rather than expanding it into a separate build plan.",
            "Keep the simulation examples tied to the actual variables, states, records, and decisions in the use case.",
            "Document the comparison cases, outputs, and acceptance checks that show why the selected 4S level is sufficient for the current 4R target.",
        ],
        "gaps_before_advancing_to_higher_4s_levels": [
            "Prediction targets and labeled outcome history for predictive simulation.",
            "Objective functions, decision rules, and constraints for prescriptive simulation.",
            "Validation metrics showing that higher-level simulation outputs are trustworthy for the intended decisions.",
        ],
    }


def run_4s_assessment_addon(
    *,
    dtc_outdir: Path,
    log_path: Path,
    fours_kb_path: Path,
    sector: str,
    problem_statement: str,
    outputs: Dict[str, str],
    priorities: Dict[str, str],
    dtaf_outdir: Optional[Path],
    fourr_outdir: Optional[Path],
    extra_evidence: str,
    base_url: str,
    model: str,
    timeout: float,
    retries: int,
) -> Path:
    if fourr_outdir is None or not fourr_outdir.exists():
        raise RuntimeError("4S assessment requires an existing 4R result directory. Do not skip 4R if you want to run 4S.")

    kb = load_4s_kb(fours_kb_path)
    dtaf_inputs = load_dtaf_4r_inputs(dtaf_outdir)
    fourr_inputs = load_4r_inputs_for_4s(fourr_outdir)
    evidence_bundle = build_4s_evidence_bundle(
        kb=kb,
        sector=sector,
        problem_statement=problem_statement,
        outputs=outputs,
        priorities=priorities,
        dtaf_inputs=dtaf_inputs,
        fourr_inputs=fourr_inputs,
        extra_evidence=extra_evidence,
    )
    try:
        raw_obj = fours_generate_classification_with_ollama(
            base_url=base_url,
            model=model,
            timeout=timeout,
            retries=retries,
            kb=kb,
            evidence_bundle=evidence_bundle,
        )
    except Exception:
        raw_obj = build_heuristic_4s_raw_obj(
            kb=kb,
            sector=sector,
            problem_statement=problem_statement,
            fourr_result=fourr_inputs.get("result", {}),
        )
    result = fours_validate_result(kb, raw_obj)
    result = fours_postprocess_result(result, fourr_inputs.get("result", {}), sector, problem_statement)

    outdir = dtc_outdir / f"fours_assessment_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
    ensure_dir(outdir)
    write_text(outdir / "4s_kb_compact.json", json.dumps(compact_4s_kb_for_prompt(kb), indent=2))
    write_text(outdir / "4s_inputs.json", json.dumps({
        "dtaf_inputs": dtaf_inputs,
        "fourr_inputs": fourr_inputs,
        "selected_capabilities": compact_priorities_for_4s(priorities),
    }, indent=2))
    write_text(outdir / "4s_evidence_bundle.txt", evidence_bundle)
    write_text(outdir / "4s_assessment_raw.json", json.dumps(raw_obj, indent=2))
    write_text(outdir / "4s_assessment_result.json", json.dumps(result, indent=2))
    current_target_level = get_current_4r_target_level_for_dtv(fourr_inputs.get("result", {}))
    write_text(outdir / "4s_assessment_summary.md", fours_result_to_markdown(result, kb, current_target_level=current_target_level))

    append_jsonl(
        log_path,
        {
            "step": "4S_assessment_addon",
            "time_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "output_path": str((outdir / "4s_assessment_summary.md").name),
        },
    )

    print("\n4S assessment complete.")
    print(f"Saved: {outdir.resolve()}")
    print(f" - {outdir / '4s_assessment_summary.md'}")
    print(f" - {outdir / '4s_assessment_result.json'}\n")
    return outdir


# -----------------------------
# Final HTML report
# -----------------------------

def extract_html_body_content(doc: str) -> str:
    m = re.search(r"<body[^>]*>(.*)</body>", str(doc or ""), flags=re.I | re.S)
    return m.group(1).strip() if m else str(doc or "")


def md_inline(text: str) -> str:
    s = html.escape(str(text or ""))
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
    s = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"\*([^*]+)\*", r"<em>\1</em>", s)
    s = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', s)
    return s


def md_table_to_html(lines: List[str]) -> str:
    rows: List[List[str]] = []
    for line in lines:
        line = line.strip()
        if not line.startswith('|'):
            continue
        rows.append([md_inline(x.strip()) for x in line.strip('|').split('|')])
    if not rows:
        return ''
    headers = rows[0]
    body = rows[1:]
    if len(rows) >= 2:
        sep = ''.join(rows[1]).replace(' ', '')
        if sep and set(sep) <= {'-', ':'}:
            body = rows[2:]
    out = ['<div class="table-wrap"><table>', '<thead><tr>']
    out.extend(f'<th>{h}</th>' for h in headers)
    out.extend(['</tr></thead>', '<tbody>'])
    for row in body:
        out.append('<tr>' + ''.join(f'<td>{c}</td>' for c in row) + '</tr>')
    out.extend(['</tbody></table></div>'])
    return '\n'.join(out)


def markdown_to_html_simple(md: str) -> str:
    lines = str(md or '').splitlines()
    out: List[str] = []
    para: List[str] = []
    ul_open = False
    ol_open = False
    code_open = False
    code_lines: List[str] = []
    i = 0

    def flush_para() -> None:
        nonlocal para
        if para:
            out.append(f"<p>{md_inline(' '.join(x.strip() for x in para))}</p>")
            para = []

    def close_lists() -> None:
        nonlocal ul_open, ol_open
        if ul_open:
            out.append('</ul>')
            ul_open = False
        if ol_open:
            out.append('</ol>')
            ol_open = False

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if stripped.startswith('```'):
            flush_para(); close_lists()
            if code_open:
                out.append('<pre><code>' + html.escape('\n'.join(code_lines)) + '</code></pre>')
                code_lines = []
                code_open = False
            else:
                code_open = True
            i += 1
            continue
        if code_open:
            code_lines.append(line)
            i += 1
            continue
        if stripped.startswith('|'):
            flush_para(); close_lists()
            table_lines: List[str] = []
            while i < len(lines) and lines[i].strip().startswith('|'):
                table_lines.append(lines[i])
                i += 1
            out.append(md_table_to_html(table_lines))
            continue
        if not stripped:
            flush_para(); close_lists(); i += 1; continue
        m = re.match(r'^(#{1,6})\s+(.*)$', stripped)
        if m:
            flush_para(); close_lists()
            level = len(m.group(1))
            out.append(f'<h{level}>{md_inline(m.group(2))}</h{level}>')
            i += 1
            continue
        if re.match(r'^[-*]\s+', stripped):
            flush_para()
            if ol_open:
                out.append('</ol>'); ol_open = False
            if not ul_open:
                out.append('<ul>'); ul_open = True
            item = re.sub(r'^[-*]\s+', '', stripped)
            out.append(f'<li>{md_inline(item)}</li>')
            i += 1
            continue
        if re.match(r'^\d+\.\s+', stripped):
            flush_para()
            if ul_open:
                out.append('</ul>'); ul_open = False
            if not ol_open:
                out.append('<ol>'); ol_open = True
            item = re.sub(r'^\d+\.\s+', '', stripped)
            out.append(f'<li>{md_inline(item)}</li>')
            i += 1
            continue
        if stripped in {'---', '***'}:
            flush_para(); close_lists(); out.append('<hr/>'); i += 1; continue
        para.append(stripped)
        i += 1
    flush_para(); close_lists()
    if code_open:
        out.append('<pre><code>' + html.escape('\n'.join(code_lines)) + '</code></pre>')
    return '\n'.join(out)


def load_json_if_exists(path: Optional[Path]) -> Dict[str, Any]:
    if path is None or not path.exists():
        return {}
    try:
        data = read_json(path)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def supporting_file_rows(outdir: Path, dtaf_outdir: Optional[Path], fourr_outdir: Optional[Path], fours_outdir: Optional[Path], dtv_outdir: Optional[Path]) -> List[tuple[str, str]]:
    rows: List[tuple[str, str]] = []
    base_files = [
        ('Step 0 use-case suitability', 'step0_use_case_suitability.md'),
        ('Step 1 business requirements', 'step1_business_requirements.md'),
        ('Step 2 capability selector', 'step2_capability_selector.md'),
        ('Step 3 capability deep dives', 'step3_capability_deep_dives.md'),
        ('Capability priorities', 'priorities.json'),
        ('Deterministic CPT table', 'step4_cpt_table.html'),
        ('Run log', 'run_log.jsonl'),
    ]
    for label, rel in base_files:
        if (outdir / rel).exists():
            rows.append((label, rel))
    def add_optional(label: str, path: Optional[Path]) -> None:
        if path is None or not path.exists():
            return
        try:
            rel = str(path.relative_to(outdir))
        except Exception:
            rel = path.name
        rows.append((label, rel))
    if dtaf_outdir is not None:
        add_optional('DTAF readiness summary', dtaf_outdir / 'summary.md')
        add_optional('DTAF readiness result', dtaf_outdir / 'recommended.json')
    if fourr_outdir is not None:
        add_optional('4R assessment summary', fourr_outdir / '4r_assessment_summary.md')
        add_optional('4R assessment result', fourr_outdir / '4r_assessment_result.json')
    if fours_outdir is not None:
        add_optional('4S assessment summary', fours_outdir / '4s_assessment_summary.md')
        add_optional('4S assessment result', fours_outdir / '4s_assessment_result.json')
    if dtv_outdir is not None:
        add_optional('DTV assessment summary', dtv_outdir / 'dtv_assessment_summary.md')
        add_optional('DTV assessment result', dtv_outdir / 'dtv_assessment_result.json')
    return rows


def build_overview_cards_html(fourr_result: Dict[str, Any], fours_result: Dict[str, Any], dtv_result: Dict[str, Any], dtaf_data: Dict[str, Any]) -> str:
    cards: List[str] = []
    if fourr_result:
        cards.append(
            '<div class="card">'
            '<h3>4R Build Target</h3>'
            f'<p><strong>Recommended target:</strong> {html.escape(str(fourr_result.get("recommended_target_level", "")))} {html.escape(str(fourr_result.get("recommended_target_name", "")))}</p>'
            f'<p><strong>Current evidence baseline:</strong> {html.escape(str(fourr_result.get("current_supported_target_level", "")))} {html.escape(str(fourr_result.get("current_supported_target_name", "")))}</p>'
            f'<p><strong>Near-term next:</strong> {html.escape(str(fourr_result.get("near_term_next_target_level", "")))} {html.escape(str(fourr_result.get("near_term_next_target_name", "")))}</p>'
            f'<p>{html.escape(str(fourr_result.get("planning_summary", "")))}</p>'
            '</div>'
        )
    if fours_result:
        cards.append(
            '<div class="card">'
            '<h3>4S Simulation Guidance</h3>'
            f'<p><strong>Recommended 4S level:</strong> {html.escape(str(fours_result.get("recommended_4s_level", "")))} {html.escape(str(fours_result.get("recommended_4s_name", "")))}</p>'
            f'<p><strong>Simulation required:</strong> {html.escape(str(fours_result.get("simulation_required", "")))}</p>'
            f'<p>{html.escape(str(fours_result.get("reason", "")))}</p>'
            '</div>'
        )
    if dtv_result:
        cards.append(
            '<div class="card">'
            '<h3>DTV Trust Guidance</h3>'
            f'<p>{html.escape(str(dtv_result.get("section2_dtv_role_for_this_use_case", "")))}</p>'
            '</div>'
        )
    if dtaf_data:
        recs = dtaf_data.get('recommended', [])
        if isinstance(recs, list) and recs:
            top = ', '.join(str(x.get('cap_id', '')) for x in recs[:6] if isinstance(x, dict))
            cards.append(
                '<div class="card">'
                '<h3>Feasible Capabilities</h3>'
                f'<p><strong>Top feasible capabilities:</strong> {html.escape(top)}</p>'
                '<p>Use these capabilities as the implementation-ready set that feeds the 4R, 4S, and DTV layers.</p>'
                '</div>'
            )
    return '<div class="card-grid">' + '\n'.join(cards) + '</div>' if cards else ''


def find_headless_browser() -> Optional[str]:
    candidates: List[str] = []
    for name in ["msedge", "microsoft-edge", "chrome", "google-chrome", "chromium", "chromium-browser"]:
        found = shutil.which(name)
        if found:
            candidates.append(found)

    windows_candidates = [
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    ]
    for raw in windows_candidates:
        if Path(raw).exists():
            candidates.append(raw)

    return candidates[0] if candidates else None


def try_render_html_to_png(html_path: Path, png_path: Path) -> bool:
    if not html_path.exists():
        return False

    browser = find_headless_browser()
    if not browser:
        return False

    html_uri = html_path.resolve().as_uri()
    command_variants = [
        [browser, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--allow-file-access-from-files", "--force-device-scale-factor=1.2", "--window-size=2400,1800", f"--screenshot={str(png_path)}", html_uri],
        [browser, "--headless", "--disable-gpu", "--hide-scrollbars", "--allow-file-access-from-files", "--force-device-scale-factor=1.2", "--window-size=2400,1800", f"--screenshot={str(png_path)}", html_uri],
    ]
    for cmd in command_variants:
        try:
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=30)
            if png_path.exists() and png_path.stat().st_size > 0:
                return True
        except Exception:
            continue
    return False


def build_cpt_visual_html(outdir: Path, step4_path: Path) -> str:
    if not step4_path.exists():
        return '<p>Step 4 capability table was not generated.</p>'

    preview_path = outdir / 'step4_cpt_preview.png'
    preview_generated = preview_path.exists() and preview_path.stat().st_size > 0
    if not preview_generated:
        preview_generated = try_render_html_to_png(step4_path, preview_path)

    if preview_generated:
        return (
            '<div class="cpt-visual">'
            f'<img src="{html.escape(preview_path.name)}" alt="Capability Periodic Table preview generated from the original Step 4 HTML" />'
            '</div>'
            '<p class="small">This preview is generated from the original Step 4 HTML so the periodic table keeps its intended visual style. '
            f'Open <a href="{html.escape(step4_path.name)}">{html.escape(step4_path.name)}</a> if you want the original standalone version.</p>'
        )

    return (
        '<div class="cpt-frame-wrap">'
        f'<iframe class="cpt-frame" src="{html.escape(step4_path.name)}" title="Capability Periodic Table"></iframe>'
        '</div>'
        '<p class="small">A browser screenshot could not be created automatically on this machine, so the original Step 4 HTML is embedded directly to preserve its formatting. '
        f'Open <a href="{html.escape(step4_path.name)}">{html.escape(step4_path.name)}</a> if you prefer the standalone file.</p>'
    )


def generate_final_html_report(*, outdir: Path, sector: str, problem_statement: str, dtaf_outdir: Optional[Path], fourr_outdir: Optional[Path], fours_outdir: Optional[Path], dtv_outdir: Optional[Path]) -> Path:
    step4_path = outdir / 'step4_cpt_table.html'
    cpt_visual_html = build_cpt_visual_html(outdir, step4_path)

    dtaf_summary = read_text(dtaf_outdir / 'summary.md') if dtaf_outdir and (dtaf_outdir / 'summary.md').exists() else ''
    fourr_summary = read_text(fourr_outdir / '4r_assessment_summary.md') if fourr_outdir and (fourr_outdir / '4r_assessment_summary.md').exists() else ''
    fours_summary = read_text(fours_outdir / '4s_assessment_summary.md') if fours_outdir and (fours_outdir / '4s_assessment_summary.md').exists() else ''
    dtv_summary = read_text(dtv_outdir / 'dtv_assessment_summary.md') if dtv_outdir and (dtv_outdir / 'dtv_assessment_summary.md').exists() else ''

    step1 = read_text(outdir / 'step1_business_requirements.md') if (outdir / 'step1_business_requirements.md').exists() else ''
    step2 = read_text(outdir / 'step2_capability_selector.md') if (outdir / 'step2_capability_selector.md').exists() else ''
    step3 = read_text(outdir / 'step3_capability_deep_dives.md') if (outdir / 'step3_capability_deep_dives.md').exists() else ''

    dtaf_json = load_json_if_exists(dtaf_outdir / 'recommended.json' if dtaf_outdir else None)
    fourr_json = load_json_if_exists(fourr_outdir / '4r_assessment_result.json' if fourr_outdir else None)
    fours_json = load_json_if_exists(fours_outdir / '4s_assessment_result.json' if fours_outdir else None)
    dtv_json = load_json_if_exists(dtv_outdir / 'dtv_assessment_result.json' if dtv_outdir else None)

    overview_cards = build_overview_cards_html(fourr_json, fours_json, dtv_json, dtaf_json)
    support_rows = supporting_file_rows(outdir, dtaf_outdir, fourr_outdir, fours_outdir, dtv_outdir)
    preview_rel = 'step4_cpt_preview.png'
    if (outdir / preview_rel).exists():
        support_rows.append(('Step 4 CPT preview image', preview_rel))

    support_html = '<div class="table-wrap"><table><thead><tr><th>Supporting File</th><th>Path</th></tr></thead><tbody>' + ''.join(f'<tr><td>{html.escape(label)}</td><td><a href="{html.escape(path)}">{html.escape(path)}</a></td></tr>' for label, path in support_rows) + '</tbody></table></div>'

    implementation_sections = []
    if dtaf_summary:
        implementation_sections.append('<details open><summary>DTAF Readiness Summary</summary>' + markdown_to_html_simple(dtaf_summary) + '</details>')
    if fourr_summary:
        implementation_sections.append('<details open><summary>4R Build Guidance</summary>' + markdown_to_html_simple(fourr_summary) + '</details>')
    if fours_summary:
        implementation_sections.append('<details><summary>4S Simulation Guidance</summary>' + markdown_to_html_simple(fours_summary) + '</details>')
    if dtv_summary:
        implementation_sections.append('<details><summary>DTV Verification and Validation Guidance</summary>' + markdown_to_html_simple(dtv_summary) + '</details>')
    if not implementation_sections:
        implementation_sections.append('<p>No readiness, 4R, 4S, or DTV summaries were generated.</p>')

    supporting_step_sections = []
    if step1:
        supporting_step_sections.append('<details><summary>Step 1 Business Requirements</summary>' + markdown_to_html_simple(step1) + '</details>')
    if step2:
        supporting_step_sections.append('<details><summary>Step 2 Capability Selection and Prioritization</summary>' + markdown_to_html_simple(step2) + '</details>')
    if step3:
        supporting_step_sections.append('<details><summary>Step 3 Capability Deep Dives</summary>' + markdown_to_html_simple(step3) + '</details>')
    if not supporting_step_sections:
        supporting_step_sections.append('<p>Step 1 to Step 3 supporting summaries were not generated.</p>')

    page = f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>Digital Twin Build Guide</title>
<style>
:root{{color-scheme:light}}
body{{font-family:system-ui,-apple-system,Segoe UI,Roboto,Arial,sans-serif;background:#f8fafc;color:#0f172a;margin:0}}
.container{{max-width:1240px;margin:0 auto;padding:24px}}
.hero{{background:#ffffff;border:1px solid #e2e8f0;border-radius:18px;padding:24px;margin-bottom:20px;box-shadow:0 4px 14px rgba(15,23,42,.05)}}
h1{{margin:0 0 10px;font-size:32px}}
h2{{margin:0 0 12px;font-size:24px}}
h3{{margin:0 0 10px;font-size:18px}}
p,li{{line-height:1.58}}
ul{{margin-top:8px}}
.card-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:16px;margin:16px 0 0}}
.card{{background:#fff;border:1px solid #e2e8f0;border-radius:16px;padding:18px;box-shadow:0 2px 8px rgba(15,23,42,.04)}}
.section{{background:#fff;border:1px solid #e2e8f0;border-radius:18px;padding:22px;margin:18px 0;box-shadow:0 2px 8px rgba(15,23,42,.04)}}
.note{{background:#eff6ff;border-left:4px solid #2563eb;padding:12px 14px;border-radius:8px}}
.table-wrap{{overflow:auto}}
table{{border-collapse:collapse;width:100%;font-size:14px}}
th,td{{border:1px solid #cbd5e1;padding:8px 10px;vertical-align:top}}
th{{background:#f1f5f9;text-align:left}}
code{{background:#f1f5f9;padding:2px 5px;border-radius:4px;overflow-wrap:anywhere}}
pre{{background:#0f172a;color:#e2e8f0;padding:14px;border-radius:12px;overflow:auto}}
details{{margin:12px 0;border:1px solid #e2e8f0;border-radius:12px;padding:12px 14px;background:#fcfdff}}
summary{{cursor:pointer;font-weight:700}}
.small{{color:#475569;font-size:14px}}
a{{color:#2563eb;text-decoration:none}}
a:hover{{text-decoration:underline}}
.cpt-shell{{background:#fff;border:1px solid #e2e8f0;border-radius:16px;padding:16px}}
.cpt-visual{{text-align:center;background:#fff}}
.cpt-visual img{{max-width:100%;height:auto;border:1px solid #e2e8f0;border-radius:12px;box-shadow:0 2px 8px rgba(15,23,42,.05)}}
.cpt-frame-wrap{{border:1px solid #e2e8f0;border-radius:12px;overflow:hidden;background:#fff}}
.cpt-frame{{display:block;width:100%;height:980px;border:0;background:#fff}}
.key-points{{margin:0;padding-left:20px}}
@media print{{
  body{{background:#fff}}
  .container{{max-width:none;padding:12mm}}
  .section,.hero,.card{{box-shadow:none}}
  details{{break-inside:avoid-page}}
  .section{{break-inside:avoid-page}}
  .cpt-frame{{height:720px}}
  a{{color:#0f172a;text-decoration:none}}
}}
</style>
</head>
<body>
<div class="container">
<section class="hero">
<h1>Digital Twin Build Guide</h1>
<p class="small">Primary output generated from the DTC, DTAF, 4R, 4S, and DTV workflow. Use this page as the main deliverable for planning the digital twin. The other generated files serve as supporting artifacts and traceability records.</p>
<div class="note"><strong>Sector:</strong> {html.escape(sector)}<br/><strong>Problem statement:</strong> {html.escape(problem_statement)}</div>
{overview_cards if overview_cards else ''}
</section>

<section class="section">
<h2>How to Use This Guide</h2>
<ul class="key-points">
<li>Start with the overview cards to confirm the feasible capabilities, 4R build target, 4S simulation level, and DTV trust focus.</li>
<li>Use the Capability Periodic Table as the visual anchor for what capabilities were selected and prioritized.</li>
<li>Use the 4R section as the main build path, the 4S section as simulation guidance, and the DTV section as verification and validation guidance.</li>
<li>Open the supporting Step 1 to Step 3 sections only when you need deeper traceability or more detailed rationale.</li>
</ul>
</section>

<section class="section">
<h2>Capability View (Step 4 CPT Table)</h2>
<p class="small">This section preserves the original Step 4 visual as closely as possible. When available, the script generates an image preview from the standalone Step 4 HTML so the periodic table keeps its intended appearance.</p>
<div class="cpt-shell">{cpt_visual_html}</div>
</section>

<section class="section">
<h2>Core Build Guidance</h2>
<p class="small">This section keeps the most important guidance together so a user can move from capability selection to build planning without opening every supporting file.</p>
{''.join(implementation_sections)}
</section>

<section class="section">
<h2>Supporting Analysis from Steps 1 to 3</h2>
<p class="small">These sections provide additional context for business requirements, capability selection, and capability-specific reasoning.</p>
{''.join(supporting_step_sections)}
</section>

<section class="section">
<h2>Supporting Files</h2>
<p class="small">Use the files below as supporting artifacts. This HTML page should be treated as the primary file for review and printing.</p>
{support_html}
</section>
</div>
</body>
</html>'''
    final_path = outdir / 'digital_twin_build_guide.html'
    write_text(final_path, page)
    return final_path


# -----------------------------
# Main
# -----------------------------



# -----------------------------
# DTV assessment add-on
# -----------------------------

def load_dtv_kb(path: Path) -> Dict[str, Any]:
    obj = read_json(path)
    if not isinstance(obj, dict):
        raise ValueError("DTV knowledge base JSON must be an object at the top level")
    if "stages" not in obj or not isinstance(obj["stages"], list) or not obj["stages"]:
        raise ValueError("DTV knowledge base JSON must contain a non-empty 'stages' list")
    return obj


def compact_dtv_kb_for_prompt(kb: Dict[str, Any]) -> Dict[str, Any]:
    stages_out = []
    for stage in kb.get("stages", []):
        if not isinstance(stage, dict):
            continue
        steps_out = []
        for step in stage.get("steps", []):
            if not isinstance(step, dict):
                continue
            subs_out = []
            for sub in step.get("substeps", []):
                if not isinstance(sub, dict):
                    continue
                subs_out.append({
                    "substep_id": str(sub.get("substep_id", "")).strip(),
                    "title": str(sub.get("title", "")).strip(),
                    "description": str(sub.get("description", "")).strip(),
                    "how_to_achieve": str(sub.get("how_to_achieve", "")).strip(),
                    "example": str(sub.get("example", "")).strip(),
                })
            steps_out.append({
                "step_id": str(step.get("step_id", "")).strip(),
                "step_name": str(step.get("step_name", "")).strip(),
                "description": str(step.get("description", "")).strip(),
                "substeps": subs_out,
            })
        stages_out.append({
            "stage_name": str(stage.get("stage_name", "")).strip(),
            "stage_description": str(stage.get("stage_description", "")).strip(),
            "steps": steps_out,
        })
    return {
        "framework_name": kb.get("framework_name", "Digital Twin V"),
        "version": kb.get("version", ""),
        "description": kb.get("description", ""),
        "purpose": kb.get("purpose", ""),
        "stages": stages_out,
        "overall_database_check": kb.get("overall_database_check", {}),
    }


def load_4s_inputs_for_dtv(fours_outdir: Optional[Path]) -> Dict[str, Any]:
    out = {
        "summary_text": "",
        "result": {},
    }
    if fours_outdir is None or not fours_outdir.exists():
        return out

    summary_path = fours_outdir / "4s_assessment_summary.md"
    result_path = fours_outdir / "4s_assessment_result.json"

    if summary_path.exists():
        out["summary_text"] = read_text(summary_path)
    if result_path.exists():
        try:
            data = read_json(result_path)
            if isinstance(data, dict):
                out["result"] = data
        except Exception:
            pass
    return out


def compact_4r_result_for_dtv(fourr_result: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(fourr_result, dict):
        return {}
    return {
        "current_supported_target_level": fourr_result.get("current_supported_target_level"),
        "current_supported_target_name": fourr_result.get("current_supported_target_name"),
        "near_term_next_target_level": fourr_result.get("near_term_next_target_level"),
        "near_term_next_target_name": fourr_result.get("near_term_next_target_name"),
        "recommended_target_level": fourr_result.get("recommended_target_level"),
        "recommended_target_name": fourr_result.get("recommended_target_name"),
        "highest_supported_target_level": fourr_result.get("highest_supported_target_level"),
        "target_support_status": fourr_result.get("target_support_status"),
        "target_confidence": fourr_result.get("target_confidence"),
        "planning_summary": fourr_result.get("planning_summary", ""),
        "criteria_supported_for_target": fourr_result.get("criteria_supported_for_target", []),
        "gaps_to_reach_target": fourr_result.get("gaps_to_reach_target", []),
        "action_items_to_reach_target": fourr_result.get("action_items_to_reach_target", []),
        "tailored_action_items": fourr_result.get("tailored_action_items", {}),
    }

def compact_4s_result_for_dtv(fours_result: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(fours_result, dict):
        return {}
    return {
        "recommended_4s_level": fours_result.get("recommended_4s_level"),
        "recommended_4s_name": fours_result.get("recommended_4s_name"),
        "simulation_required": fours_result.get("simulation_required"),
        "reason": fours_result.get("reason", ""),
        "why_s1_is_included": fours_result.get("why_s1_is_included", ""),
        "why_s2_is_the_current_target": fours_result.get("why_s2_is_the_current_target", ""),
        "why_s3_is_future_work": fours_result.get("why_s3_is_future_work", ""),
        "why_s4_is_future_work": fours_result.get("why_s4_is_future_work", ""),
        "current_feasible_simulation_target_vs_future_simulation_vision": fours_result.get("current_feasible_simulation_target_vs_future_simulation_vision", ""),
        "gaps_before_advancing_to_higher_4s_levels": fours_result.get("gaps_before_advancing_to_higher_4s_levels", []),
    }




def get_current_4r_target_level_for_dtv(fourr_result: Dict[str, Any]) -> str:
    if not isinstance(fourr_result, dict):
        return ""
    for key in ("recommended_target_level", "current_supported_target_level", "highest_supported_target_level", "recommended_target_name"):
        val = str(fourr_result.get(key, "")).strip()
        if val:
            return val
    return ""

def build_fallback_4r_context_summary_for_dtv(fourr_result: Dict[str, Any]) -> str:
    if not isinstance(fourr_result, dict) or not fourr_result:
        return ""
    recommended_level = str(fourr_result.get("recommended_target_level", "")).strip()
    recommended_name = str(fourr_result.get("recommended_target_name", "")).strip()
    baseline_level = str(fourr_result.get("current_supported_target_level", "")).strip()
    baseline_name = str(fourr_result.get("current_supported_target_name", "")).strip()
    next_level = str(fourr_result.get("near_term_next_target_level", "")).strip()
    next_name = str(fourr_result.get("near_term_next_target_name", "")).strip()
    planning = coerce_preferred_text(fourr_result.get("planning_summary", ""), preferred_keys=["planning_summary"])
    pieces = []
    if recommended_level or recommended_name:
        target_txt = recommended_level if not recommended_name or recommended_name == recommended_level else f"{recommended_level} ({recommended_name})"
        pieces.append(f"The recommended pre-build 4R target is {target_txt}.")
    if baseline_level or baseline_name:
        baseline_txt = baseline_level if not baseline_name or baseline_name == baseline_level else f"{baseline_level} ({baseline_name})"
        pieces.append(f"The current evidence baseline is {baseline_txt}.")
    if recommended_level and baseline_level and recommended_level != baseline_level:
        pieces.append(f"DTV should support the {recommended_level} build target while first closing the lower-level trust-evidence gaps needed to reach it reliably.")
    if next_level and next_level != recommended_level:
        next_txt = next_level if not next_name or next_name == next_level else f"{next_level} ({next_name})"
        pieces.append(f"The near-term next target beyond the current recommendation is {next_txt}.")
    if planning:
        pieces.append(planning)
    return " ".join(pieces).strip()

def build_fallback_target_boundary_for_dtv(target_level: str) -> str:
    target_level = str(target_level).strip().upper()
    if target_level == "R1":
        return (
            "The current DTV focus is limited to representation trust evidence: whether the selected variables, data sources, schemas, metadata, and initial representations are implemented correctly and are trustworthy enough for the intended use. "
            "It should not yet claim replication, prediction, or autonomy evidence."
        )
    if target_level == "R2":
        return (
            "The current DTV focus is on R1 and R2 trust evidence: data correctness, data pipeline reliability, physical-to-digital mapping, synchronization, latency, state-transition checks, model calibration, and reproduction of observed system behavior within defined deviation thresholds. "
            "Future predictive, optimization, or autonomous behavior should be treated as future work rather than current trust evidence."
        )
    if target_level == "R3":
        return (
            "The current DTV focus is on R1, R2, and R3 trust evidence: representation correctness, replication accuracy, independent scenario execution, what-if behavior, predictive or decision-support model performance, and documented acceptance criteria for model usefulness in the intended decision context. "
            "Adaptive autonomy or closed-loop relational behavior should still be treated as future work unless explicitly supported by the 4R result."
        )
    if target_level == "R4":
        return (
            "The current DTV focus covers the full R1 to R4 trust boundary, including representation, replication, predictive or decision-support performance, and the additional trust controls needed for adaptive or semi-autonomous relational behavior. "
            "This includes override conditions, human-in-the-loop boundaries, safety constraints, and evidence that the DT can act or recommend actions acceptably in context."
        )
    return "The current DTV focus should align with the active 4R build target and only cover the trust evidence needed for that target and the lower levels it depends on."


def build_dtv_evidence_bundle(
    *,
    kb: Dict[str, Any],
    sector: str,
    problem_statement: str,
    outputs: Dict[str, str],
    priorities: Dict[str, str],
    dtaf_inputs: Dict[str, Any],
    fourr_inputs: Dict[str, Any],
    fours_inputs: Dict[str, Any],
    extra_evidence: str,
) -> str:
    fourr_result = fourr_inputs.get("result", {}) if isinstance(fourr_inputs, dict) else {}
    fours_result = fours_inputs.get("result", {}) if isinstance(fours_inputs, dict) else {}
    current_target_level = get_current_4r_target_level_for_dtv(fourr_result)
    selected_caps = compact_priorities_for_4s(priorities)
    feasible_caps = dtaf_inputs.get("feasible_capabilities", []) if isinstance(dtaf_inputs, dict) else []

    parts: List[str] = []
    parts.append("You are helping implement the Digital Twin V (DTV) framework inside a larger Digital Twin Analytical Framework workflow.")
    parts.append("")
    parts.append("Use case description:")
    parts.append(f"Sector: {sector}")
    parts.append(problem_statement.strip())
    parts.append("")

    parts.append("Existing 4R classification:")
    if fourr_result:
        parts.append(json.dumps(compact_4r_result_for_dtv(fourr_result), indent=2))
        if current_target_level:
            parts.append(f"Current 4R target level to use for DTV guidance: {current_target_level}")
    else:
        parts.append("No 4R result JSON was found. If no 4R result is available, do not redo 4R. Instead note that DTV depends on an existing 4R result.")
    parts.append("")

    parts.append("Selected digital twin capabilities:")
    parts.append(json.dumps({
        "selected_capabilities_from_step2": selected_caps,
        "feasible_capabilities_from_dtaf": feasible_caps,
    }, indent=2))
    parts.append("")

    parts.append("Existing 4R action items:")
    if fourr_result.get("tailored_action_items"):
        parts.append(json.dumps(fourr_result.get("tailored_action_items", {}), indent=2))
    elif fourr_result.get("action_items_to_reach_target"):
        parts.append(json.dumps(fourr_result.get("action_items_to_reach_target", []), indent=2))
    else:
        parts.append("[]")
    parts.append("")

    parts.append("Available data and system context:")
    parts.append("Step 0 output:\n" + outputs.get("0", "")[:4000])
    parts.append("")
    parts.append("Step 1 output:\n" + outputs.get("1", "")[:7000])
    parts.append("")
    parts.append("Step 2 output:\n" + outputs.get("2", "")[:5000])
    parts.append("")
    parts.append("Step 3 output:\n" + outputs.get("3_combined", outputs.get("3_part1", "") + "\n\n" + outputs.get("3_part2", ""))[:7000])

    if dtaf_inputs.get("summary_text"):
        parts.append("")
        parts.append("DTAF summary:\n" + str(dtaf_inputs.get("summary_text", ""))[:4000])

    if fourr_inputs.get("summary_text"):
        parts.append("")
        parts.append("4R summary:\n" + str(fourr_inputs.get("summary_text", ""))[:5000])

    parts.append("")
    parts.append("Optional 4S simulation classification, if available:")
    if fours_result:
        parts.append(json.dumps(compact_4s_result_for_dtv(fours_result), indent=2))
    else:
        parts.append("No 4S result was available for this run.")
    if fours_inputs.get("summary_text"):
        parts.append("")
        parts.append("4S summary:\n" + str(fours_inputs.get("summary_text", ""))[:4000])

    if extra_evidence:
        parts.append("")
        parts.append("Additional user-provided DTV evidence:\n" + extra_evidence[:8000])

    parts.append("")
    parts.append("Definitions:")
    parts.append("- Verification asks whether the digital twin component was built correctly according to the intended design, requirements, data structure, model logic, or interface specification.")
    parts.append("- Validation asks whether the digital twin is useful, accurate, and trustworthy for representing or supporting decisions about the real physical system.")
    parts.append("- Evidence refers to the records, tests, comparisons, metrics, screenshots, logs, model outputs, sensor checks, user feedback, or performance results used to support verification and validation claims.")
    parts.append("")
    parts.append("Important behavior rules:")
    parts.append("- Do not redo the 4R classification.")
    parts.append("- Do not restart the digital twin development process.")
    parts.append("- Treat DTV as a verification, validation, and trust-evidence layer after 4R has already classified the digital twin maturity level.")
    parts.append("- Tie every DTV recommendation directly to the existing 4R action items.")
    parts.append("- Keep the guidance aligned with the current feasible 4R target from the supplied 4R result. Do not fall back to R2 unless the supplied 4R result actually recommends R2.")
    parts.append("- Keep verification and validation clearly separate.")
    parts.append("- Use measurable acceptance criteria wherever possible.")
    parts.append("- For R2 replication-focused cases, emphasize data correctness, physical-to-digital mapping, synchronization, latency, model-output comparison, calibration, and replication accuracy.")
    parts.append("- Do not use prediction, optimization, autonomous decision-making, or prescriptive control language unless it is clearly labeled as future work beyond the current R2 boundary.")
    parts.append("- For each relevant 4R action item, explain what should be verified, what should be validated, what evidence should be collected, and what measurable pass/fail or acceptance criteria could be used.")
    parts.append("- If a step does not require formal validation yet, state that clearly.")
    parts.append("- If the current data or system context is not sufficient for validation, identify the gap.")
    parts.append("- Use sector-specific examples that come directly from the provided use case. Do not borrow examples from other domains unless the user explicitly asks for cross-domain comparison.")
    return "\n".join(parts).strip()


def dtv_safe_json_extract(s: str) -> Dict[str, Any]:
    s = s.strip()
    try:
        return json.loads(s)
    except Exception:
        pass
    m = re.search(r"\{.*\}", s, flags=re.S)
    if not m:
        raise ValueError("Model did not return JSON for the DTV assessment")
    return json.loads(m.group(0))


def dtv_generate_guidance_with_ollama(
    *,
    base_url: str,
    model: str,
    timeout: float,
    retries: int,
    kb: Dict[str, Any],
    evidence_bundle: str,
    current_target_level: str = "",
) -> Dict[str, Any]:
    kb_compact = compact_dtv_kb_for_prompt(kb)
    current_target_level = str(current_target_level).strip().upper()
    target_specific = ""
    if current_target_level == "R2":
        target_specific = (
            "- The current 4R target is R2. Focus DTV on representation and replication trust evidence.\n"
            "- Emphasize data correctness, physical-to-digital mapping, synchronization, latency, state-transition checks, model-output comparison, calibration, and acceptable deviation thresholds.\n"
            "- Put prediction, optimization, autonomous decision-making, or prescriptive control into future work instead of the current trust boundary.\n"
        )
    elif current_target_level == "R3":
        target_specific = (
            "- The current 4R target is R3. Cover the trust evidence needed for R1, R2, and R3.\n"
            "- Include representation and replication evidence, plus independent scenario execution, what-if behavior, predictive or decision-support model checks, calibration, and validation metrics tied to the intended decision use.\n"
            "- Do not drift into R4 autonomy, adaptive control, or relational behavior unless the supplied 4R result explicitly supports it.\n"
        )
    elif current_target_level == "R4":
        target_specific = (
            "- The current 4R target is R4. Cover the trust evidence needed for R1 through R4, including override conditions, human-in-the-loop boundaries, trust controls, and evidence for adaptive or relational behavior where applicable.\n"
        )
    else:
        target_specific = (
            "- Use the supplied 4R result to determine the active trust boundary. Cover the current target level and all lower levels it depends on.\n"
        )

    prompt = f"""
Revise the DTV output so it becomes a stronger, clearer, more evidence-driven verification and validation guide for the use case. Keep the current 4R target unless the provided evidence clearly contradicts it. Do not redo 4R. Do not create a separate development workflow. Improve the DTV output by explaining how each major current-level 4R action item should be verified, validated, and supported with trust evidence.

Return JSON with EXACTLY these top-level keys:
{{
  "section1_4r_context_summary": "...",
  "section2_dtv_role_for_this_use_case": "...",
  "section3_current_target_trust_boundary": "...",
  "dtv_development_and_vv_table": [
    {{
      "existing_4r_action_item": "...",
      "dtv_stage_or_focus_area": "...",
      "what_should_be_verified": "...",
      "what_should_be_validated": "...",
      "evidence_to_collect": "...",
      "suggested_acceptance_criteria": "...",
      "use_case_specific_example": "..."
    }}
  ],
  "verification_guidance": ["..."],
  "validation_guidance": ["..."],
  "gaps_and_risks": ["..."],
  "dtv_aligned_action_items": ["..."],
  "section9_future_dtv_work_beyond_current_target": ["..."]
}}

Revision requirements:
- Keep Section 1 as a short 4R context summary.
- In Section 2, explain DTV's role as a trust-evidence layer for the current 4R target.
- In Section 3, explain what the current DTV guidance should and should not cover for the current target level and its lower-level dependencies.
- In the table, each row must clearly include what should be verified, what should be validated, what evidence should be collected, what measurable acceptance criteria should be used, and a use-case-specific example.
- Remove or revise examples that imply higher-maturity prediction or prescription unless they are clearly labeled as future work.
- Add strong current-target evidence requirements, including checking whether live or recorded system data drives the virtual model correctly, comparing virtual model outputs to real system outputs, checking synchronization and latency, testing state transitions, calibrating model parameters, documenting acceptable error thresholds, and verifying that data streams are traceable to components, states, or decisions.
- Make verification and validation guidance separate and clear.
- Rewrite the final DTV-aligned action items so they are not just repeated 4R titles. Each should say exactly what should be checked and what evidence should be produced.
- Use measurable acceptance criteria whenever possible. Example patterns: timestamp alignment is within the required update interval; missing data rate is below the agreed threshold; measured values match trusted logs within the agreed tolerance; state labels match authoritative logs with the required accuracy; replicated cycle time or service time matches recorded behavior within the agreed deviation; data latency remains below the required limit; every data stream is traceable to a component, state, or decision.
- If the current 4R target is R1, keep validation at the representation boundary: validate that the selected variables, data sources, schemas, and system boundaries accurately reflect the real system and are useful for the intended decisions. Do not treat full virtual-model-output validation as a current requirement at R1.
- Use use-case-specific examples and evidence drawn directly from the provided domain, systems, variables, records, interfaces, and decisions. Do not import examples from unrelated domains.
{target_specific}

DTV knowledge base:
{json.dumps(kb_compact, indent=2)}

Workflow evidence bundle:
{evidence_bundle}
""".strip()

    messages = [
        {
            "role": "system",
            "content": (
                "Return ONLY JSON. You are improving a generated Digital Twin V (DTV) guidance output for a digital twin that already has an existing 4R classification. "
                "Do not redo 4R. Do not create a new workflow. Treat DTV as a verification, validation, and trust-evidence layer that explains how the existing 4R action items should be checked, tested, validated, and supported with evidence."
            ),
        },
        {
            "role": "user",
            "content": prompt,
        },
    ]

    out = chat_completions(
        base_url=base_url,
        model=model,
        messages=messages,
        max_tokens=3200,
        temperature=0.0,
        timeout=timeout,
        retries=retries,
    )
    return dtv_safe_json_extract(out)


def dtv_validate_result(obj: Dict[str, Any]) -> Dict[str, Any]:
    result = {
        "section1_4r_context_summary": str(obj.get("section1_4r_context_summary", "")).strip(),
        "section2_dtv_role_for_this_use_case": str(obj.get("section2_dtv_role_for_this_use_case", "")).strip(),
        "section3_current_target_trust_boundary": str(obj.get("section3_current_target_trust_boundary", obj.get("section3_current_r2_trust_boundary", ""))).strip(),
        "dtv_development_and_vv_table": [],
        "verification_guidance": [str(x).strip() for x in obj.get("verification_guidance", []) if str(x).strip()],
        "validation_guidance": [str(x).strip() for x in obj.get("validation_guidance", []) if str(x).strip()],
        "gaps_and_risks": [str(x).strip() for x in obj.get("gaps_and_risks", []) if str(x).strip()],
        "dtv_aligned_action_items": [str(x).strip() for x in obj.get("dtv_aligned_action_items", []) if str(x).strip()],
        "section9_future_dtv_work_beyond_current_target": [str(x).strip() for x in obj.get("section9_future_dtv_work_beyond_current_target", obj.get("section9_future_dtv_work_beyond_r2", [])) if str(x).strip()],
    }

    raw_rows = obj.get("dtv_development_and_vv_table", [])
    if isinstance(raw_rows, list):
        for row in raw_rows:
            if not isinstance(row, dict):
                continue
            norm = {
                "existing_4r_action_item": str(row.get("existing_4r_action_item", "")).strip(),
                "dtv_stage_or_focus_area": str(row.get("dtv_stage_or_focus_area", "")).strip(),
                "what_should_be_verified": str(row.get("what_should_be_verified", "")).strip(),
                "what_should_be_validated": str(row.get("what_should_be_validated", "")).strip(),
                "evidence_to_collect": str(row.get("evidence_to_collect", "")).strip(),
                "suggested_acceptance_criteria": str(row.get("suggested_acceptance_criteria", "")).strip(),
                "use_case_specific_example": str(row.get("use_case_specific_example", "")).strip(),
            }
            if any(norm.values()):
                result["dtv_development_and_vv_table"].append(norm)

    return result


def dtv_result_to_markdown(result: Dict[str, Any], current_target_level: str = "") -> str:
    lines: List[str] = []
    lines.append("# Digital Twin V (DTV) Guidance")
    lines.append("")
    lines.append("This step uses the existing 4R output to explain how the proposed digital twin should be verified, validated, and trusted for the specific use case. It does not redo 4R and it does not replace the existing 4R development path.")
    lines.append("")
    target_level = str(current_target_level).strip().upper()
    target_label = target_level if target_level else "Current Target"
    lines.append("## Section 1: 4R Context Summary")
    lines.append("")
    lines.append(result.get("section1_4r_context_summary", "") or "No 4R context summary was produced.")
    lines.append("")
    lines.append("## Section 2: DTV Role for This Use Case")
    lines.append("")
    lines.append(result.get("section2_dtv_role_for_this_use_case", "") or "No DTV role description was produced.")
    lines.append("")
    lines.append(f"## Section 3: Current {target_label} Trust Boundary")
    lines.append("")
    lines.append(result.get("section3_current_target_trust_boundary", "") or "No current trust-boundary description was produced.")
    lines.append("")
    lines.append("## Section 4: DTV Development and V&V Table")
    lines.append("")
    if result.get("dtv_development_and_vv_table"):
        lines.append("| Existing 4R Action Item | DTV Stage or Focus Area | What Should Be Verified | What Should Be Validated | Evidence to Collect | Suggested Acceptance Criteria | Use-Case-Specific Example |")
        lines.append("|---|---|---|---|---|---|---|")
        for row in result.get("dtv_development_and_vv_table", []):
            lines.append(
                f"| {row.get('existing_4r_action_item', '').replace('|', '/')} | {row.get('dtv_stage_or_focus_area', '').replace('|', '/')} | {row.get('what_should_be_verified', '').replace('|', '/')} | {row.get('what_should_be_validated', '').replace('|', '/')} | {row.get('evidence_to_collect', '').replace('|', '/')} | {row.get('suggested_acceptance_criteria', '').replace('|', '/')} | {row.get('use_case_specific_example', '').replace('|', '/')} |"
            )
    else:
        lines.append("No DTV development and V&V rows were produced.")
    lines.append("")
    lines.append("## Section 5: Verification Guidance")
    lines.append("")
    if result.get("verification_guidance"):
        for item in result.get("verification_guidance", []):
            lines.append(f"- {item}")
    else:
        lines.append("- No verification guidance was generated.")
    lines.append("")
    lines.append("## Section 6: Validation Guidance")
    lines.append("")
    if result.get("validation_guidance"):
        for item in result.get("validation_guidance", []):
            lines.append(f"- {item}")
    else:
        lines.append("- No validation guidance was generated.")
    lines.append("")
    lines.append("## Section 7: Gaps and Risks")
    lines.append("")
    if result.get("gaps_and_risks"):
        for item in result.get("gaps_and_risks", []):
            lines.append(f"- {item}")
    else:
        lines.append("- No major DTV gaps or risks were listed.")
    lines.append("")
    lines.append("## Section 8: DTV-Aligned Action Items")
    lines.append("")
    if result.get("dtv_aligned_action_items"):
        for item in result.get("dtv_aligned_action_items", []):
            lines.append(f"- {item}")
    else:
        lines.append("- No DTV-aligned action items were generated.")
    lines.append("")
    lines.append(f"## Section 9: Future DTV Work Beyond {target_label}")
    lines.append("")
    if result.get("section9_future_dtv_work_beyond_current_target"):
        for item in result.get("section9_future_dtv_work_beyond_current_target", []):
            lines.append(f"- {item}")
    else:
        lines.append(f"- No future DTV work beyond the current {target_label} boundary was listed.")
    lines.append("")
    return "\n".join(lines).strip() + "\n"



# -----------------------------
# Generic DTV function-extraction and row-generation helpers
# -----------------------------

DTV_GENERIC_RULES: Dict[str, Dict[str, Any]] = {
    "purpose_scope": {
        "stage": "Decomposition: Purpose and Scope",
        "verify": "Verify that the digital twin purpose, scope, supported decisions, and included and excluded system boundaries are explicitly documented and traceable to the selected 4R target.",
        "validate": "Validate that the selected scope and supported decisions are sufficient for the intended operational use case and acceptable to stakeholders.",
        "evidence": ["scope statement", "stakeholder review notes", "decision traceability matrix"],
        "criteria": [
            "all intended decisions are documented",
            "included and excluded system boundaries are approved",
            "stakeholders confirm the digital twin scope is sufficient for intended use",
        ],
    },
    "system_boundary_and_mapping": {
        "stage": "Decomposition: System Boundary and Mapping",
        "verify": "Verify that each required physical or logical system element, state, and interface is correctly mapped into the digital representation.",
        "validate": "Validate that the digital representation reflects the real system structure, relevant states, and key interactions closely enough for the intended use.",
        "evidence": ["physical-to-digital mapping table", "state and interface inventory", "reviewed architecture diagram"],
        "criteria": [
            "all required components and states are mapped",
            "unmapped critical elements are zero",
            "stakeholders approve the mapping as sufficient for the intended decisions",
        ],
    },
    "data_pipeline": {
        "stage": "Development: Data Pipeline and Data Layer",
        "verify": "Verify that each required variable is mapped to a real data source, timestamped correctly, stored in the expected format, and retrievable without corruption.",
        "validate": "Validate that the collected data is sufficient and trustworthy for representing the real system in the intended context of use.",
        "evidence": ["data-source map", "sample records", "timestamp audit", "schema validation results"],
        "criteria": [
            "missing data rate is below the agreed threshold",
            "timestamps align within the required interval",
            "units and naming conventions are consistent",
        ],
    },
    "data_quality": {
        "stage": "Development: Data Quality and Preparation",
        "verify": "Verify that data cleaning, preprocessing, naming, units, and metadata rules are implemented according to the defined schema and ingestion logic.",
        "validate": "Validate that the prepared data is accurate and interpretable enough to support analysis, visualization, or later modeling.",
        "evidence": ["schema validation report", "quality-check logs", "sample before-and-after preprocessing records"],
        "criteria": [
            "required fields are populated above the agreed completeness threshold",
            "invalid records remain below the agreed threshold",
            "quality checks pass for the required variables",
        ],
    },
    "synchronization": {
        "stage": "Development Integration: Data Integration and Synchronization",
        "verify": "Verify that live or recorded data is correctly ingested into the digital twin and updates the correct model variables, states, or interfaces.",
        "validate": "Validate that the digital representation stays sufficiently synchronized with the real system for the intended 4R target.",
        "evidence": ["latency test logs", "timestamp alignment report", "data-to-model mapping table"],
        "criteria": [
            "latency remains below the required limit",
            "timestamp alignment is within the required update interval",
            "all mapped variables update the correct model fields",
        ],
    },
    "replication_accuracy": {
        "stage": "Integration and Testing: Replication Accuracy",
        "verify": "Verify that model inputs, logic, synchronization, and output calculations are implemented according to the digital twin design.",
        "validate": "Validate that the replicated digital twin output matches recorded real-system behavior within agreed tolerances for the intended use.",
        "evidence": ["comparison table", "calibration notes", "test-run logs", "state-transition comparison report"],
        "criteria": [
            "key output deviation is within the agreed threshold",
            "state or event match rate meets the required accuracy",
            "calibration changes are documented and traceable",
        ],
    },
    "interface_and_visualization": {
        "stage": "Development: Interface and Visualization",
        "verify": "Verify that operator-facing views, dashboards, and interfaces display the correct values, labels, timestamps, and status indicators.",
        "validate": "Validate that the interface supports the intended monitoring and decision tasks without misleading users.",
        "evidence": ["interface screenshots", "field-to-source mapping table", "user review notes"],
        "criteria": [
            "displayed values match source data",
            "timestamps are visible and correct",
            "users confirm the interface supports intended decisions",
        ],
    },
    "decision_support_readiness": {
        "stage": "Integration and Testing: Decision Support Readiness",
        "verify": "Verify that the digital twin outputs, thresholds, and business or engineering rules are implemented according to the documented design.",
        "validate": "Validate that the outputs are useful and trustworthy enough to support the intended operational decision in context.",
        "evidence": ["decision traceability table", "reviewed threshold table", "comparison cases", "user evaluation notes"],
        "criteria": [
            "decision-support outputs are traceable to source data and rules",
            "reviewers accept the output as useful for the intended decision",
            "decision logic remains within the documented scope of the current target level",
        ],
    },
    "general": {
        "stage": "Integration and Testing: Action-Specific Verification and Validation",
        "verify": "Verify that the relevant digital twin elements were built according to the documented design, mappings, schemas, or logic.",
        "validate": "Validate that the resulting representation is accurate and useful enough for the intended operational purpose.",
        "evidence": ["review notes", "traceability records", "comparison examples"],
        "criteria": [
            "the implementation matches the documented design",
            "the result is accepted as sufficiently accurate for intended use",
        ],
    },
}


def dtv_compose_list_text(items: Any, fallback: str = "") -> str:
    if isinstance(items, str):
        txt = normalize_ws(items)
        return txt or fallback
    if isinstance(items, list):
        vals = [normalize_ws(x) for x in items if normalize_ws(x)]
        return ", ".join(vals[:6]) if vals else fallback
    return fallback


def dtv_extract_domain_context_fallback(
    *,
    sector: str,
    problem_statement: str,
    fourr_result: Dict[str, Any],
) -> Dict[str, Any]:
    ps = normalize_ws(problem_statement)
    terms = extract_use_case_focus_terms(sector, problem_statement, limit=10)
    action_titles = extract_fourr_action_titles(fourr_result)
    system_type = sector.strip() or "digital twin system"
    primary_decisions: List[str] = []

    lower_ps = ps.lower()
    if "schedule" in lower_ps:
        primary_decisions.append("scheduling decision support")
    if "capability" in lower_ps or "capacity" in lower_ps:
        primary_decisions.append("feasibility and capacity assessment")
    if "quality" in lower_ps or "cost" in lower_ps or "time" in lower_ps:
        primary_decisions.append("quality, cost, and time decision support")
    if "maint" in lower_ps:
        primary_decisions.append("maintenance timing support")
    if not primary_decisions:
        primary_decisions = ["the intended operational decisions"]

    data_sources: List[str] = []
    source_keywords = [
        ("sensor", "sensor streams"),
        ("controller", "controller or equipment logs"),
        ("plc", "control-system data"),
        ("erp", "enterprise records"),
        ("mes", "execution-system records"),
        ("api", "API feeds"),
        ("inspection", "inspection records"),
        ("historical", "historical records"),
    ]
    for key, label in source_keywords:
        if key in lower_ps and label not in data_sources:
            data_sources.append(label)
    if not data_sources:
        data_sources = ["operational records", "sensor or system data streams"]

    future_goals: List[str] = []
    if any(x in lower_ps for x in ["predict", "forecast", "remaining useful life", "rul"]):
        future_goals.append("predictive outputs")
    if any(x in lower_ps for x in ["optimiz", "recommend", "prescrib"]):
        future_goals.append("optimized or recommended actions")
    if any(x in lower_ps for x in ["automate", "autonom", "closed-loop"]):
        future_goals.append("automated decision or control behavior")

    return {
        "domain": sector.strip() or "generic",
        "system_type": system_type,
        "target_4r_level": get_current_4r_target_level_for_dtv(fourr_result),
        "primary_decisions": primary_decisions,
        "physical_components": terms[:6],
        "candidate_variables": terms[:8],
        "data_sources": data_sources,
        "future_goals": future_goals,
        "source_action_titles": action_titles,
    }


def dtv_extract_domain_context_with_ollama(
    *,
    base_url: str,
    model: str,
    timeout: float,
    retries: int,
    sector: str,
    problem_statement: str,
    fourr_result: Dict[str, Any],
) -> Dict[str, Any]:
    target_level = get_current_4r_target_level_for_dtv(fourr_result)
    prompt = f"""
Return JSON only.

Task:
Extract a structured domain-context object for a digital twin use case.

Rules:
- Stay generic. Do not assume any specific sector beyond what is stated.
- Use the actual use case language.
- Keep future-only goals separate from the current boundary.
- If some fields are uncertain, still return your best concise extraction.

Schema:
{{
  "domain": "",
  "system_type": "",
  "target_4r_level": "{target_level}",
  "primary_decisions": [],
  "physical_components": [],
  "candidate_variables": [],
  "data_sources": [],
  "future_goals": []
}}

Sector:
{sector}

Problem statement:
{problem_statement}
""".strip()
    messages = [
        {"role": "system", "content": "Return ONLY JSON. Extract a domain context object for the digital twin use case."},
        {"role": "user", "content": prompt},
    ]
    out = chat_completions(
        base_url=base_url,
        model=model,
        messages=messages,
        max_tokens=1200,
        temperature=0.0,
        timeout=timeout,
        retries=retries,
    )
    obj = dtv_safe_json_extract(out)
    if not isinstance(obj, dict):
        raise ValueError("Domain context extraction did not return a JSON object")
    return {
        "domain": normalize_ws(obj.get("domain", sector)),
        "system_type": normalize_ws(obj.get("system_type", sector or "digital twin system")),
        "target_4r_level": normalize_ws(obj.get("target_4r_level", target_level)),
        "primary_decisions": [normalize_ws(x) for x in obj.get("primary_decisions", []) if normalize_ws(x)],
        "physical_components": [normalize_ws(x) for x in obj.get("physical_components", []) if normalize_ws(x)],
        "candidate_variables": [normalize_ws(x) for x in obj.get("candidate_variables", []) if normalize_ws(x)],
        "data_sources": [normalize_ws(x) for x in obj.get("data_sources", []) if normalize_ws(x)],
        "future_goals": [normalize_ws(x) for x in obj.get("future_goals", []) if normalize_ws(x)],
    }


def dtv_extract_functions_fallback(
    *,
    problem_statement: str,
    current_target_level: str,
    fourr_result: Dict[str, Any],
    domain_context: Dict[str, Any],
) -> Dict[str, Any]:
    action_titles = extract_fourr_action_titles(fourr_result)
    vars_ = domain_context.get("candidate_variables", [])[:6]
    comps = domain_context.get("physical_components", [])[:6]
    decs = domain_context.get("primary_decisions", [])[:4]

    current_functions: List[Dict[str, Any]] = []
    for title in action_titles[:8]:
        current_functions.append({
            "name": normalize_ws(title),
            "purpose": normalize_ws(title),
            "related_system_elements": comps[:4],
            "related_variables": vars_[:6],
            "related_decisions": decs[:3],
        })

    lvl = str(current_target_level).strip().upper()
    if not current_functions:
        current_functions.append({
            "name": "System representation and boundary definition",
            "purpose": "Represent the system, its boundaries, and its key elements for the selected 4R target.",
            "related_system_elements": comps[:4],
            "related_variables": vars_[:6],
            "related_decisions": decs[:3],
        })
        current_functions.append({
            "name": "Data acquisition and data-quality readiness",
            "purpose": "Capture and organize the key variables needed for the intended use case.",
            "related_system_elements": comps[:4],
            "related_variables": vars_[:6],
            "related_decisions": decs[:3],
        })
        if lvl in {"R2", "R3", "R4"}:
            current_functions.append({
                "name": "Synchronized replication of observed system behavior",
                "purpose": "Use live or recorded data to drive the digital twin and compare its outputs to real behavior.",
                "related_system_elements": comps[:4],
                "related_variables": vars_[:6],
                "related_decisions": decs[:3],
            })

    future_functions: List[Dict[str, Any]] = []
    lower_ps = problem_statement.lower()
    if lvl in {"R1", "R2"} and any(x in lower_ps for x in ["predict", "forecast", "remaining useful life", "rul"]):
        future_functions.append({"name": "Predictive or scenario-exploration behavior", "reason_future": "Predictive behavior is beyond the current target boundary."})
    if lvl in {"R1", "R2", "R3"} and any(x in lower_ps for x in ["optimiz", "recommend", "automate", "autonom", "prescrib"]):
        future_functions.append({"name": "Recommended or autonomous action selection", "reason_future": "Prescriptive or adaptive action logic is beyond the current target boundary."})

    return {"current_functions": current_functions, "future_functions": future_functions}


def dtv_extract_functions_with_ollama(
    *,
    base_url: str,
    model: str,
    timeout: float,
    retries: int,
    problem_statement: str,
    current_target_level: str,
    domain_context: Dict[str, Any],
    fourr_result: Dict[str, Any],
) -> Dict[str, Any]:
    prompt = f"""
Return JSON only.

Task:
Extract the major digital twin functions implied by this use case.

Current 4R target: {current_target_level}

Rules:
- Focus on functions relevant to the current 4R target.
- Put future-only functions into a separate "future_functions" list.
- Stay domain-agnostic.
- Use the actual use case language.
- Do not import examples from unrelated domains.

Useful context:
{json.dumps(domain_context, indent=2)}

Existing 4R action items:
{json.dumps(extract_fourr_action_titles(fourr_result), indent=2)}

Schema:
{{
  "current_functions": [
    {{
      "name": "",
      "purpose": "",
      "related_system_elements": [],
      "related_variables": [],
      "related_decisions": []
    }}
  ],
  "future_functions": [
    {{
      "name": "",
      "reason_future": ""
    }}
  ]
}}

Use case:
{problem_statement}
""".strip()
    messages = [
        {"role": "system", "content": "Return ONLY JSON. Extract digital twin functions for later verification and validation guidance."},
        {"role": "user", "content": prompt},
    ]
    out = chat_completions(
        base_url=base_url,
        model=model,
        messages=messages,
        max_tokens=1800,
        temperature=0.0,
        timeout=timeout,
        retries=retries,
    )
    obj = dtv_safe_json_extract(out)
    if not isinstance(obj, dict):
        raise ValueError("Function extraction did not return a JSON object")
    current_functions = []
    for item in obj.get("current_functions", []):
        if not isinstance(item, dict):
            continue
        current_functions.append({
            "name": normalize_ws(item.get("name", "")),
            "purpose": normalize_ws(item.get("purpose", "")),
            "related_system_elements": [normalize_ws(x) for x in item.get("related_system_elements", []) if normalize_ws(x)],
            "related_variables": [normalize_ws(x) for x in item.get("related_variables", []) if normalize_ws(x)],
            "related_decisions": [normalize_ws(x) for x in item.get("related_decisions", []) if normalize_ws(x)],
        })
    future_functions = []
    for item in obj.get("future_functions", []):
        if not isinstance(item, dict):
            continue
        future_functions.append({
            "name": normalize_ws(item.get("name", "")),
            "reason_future": normalize_ws(item.get("reason_future", "")),
        })
    return {"current_functions": current_functions, "future_functions": future_functions}


def classify_dtv_focus_generic(function_name: str, purpose: str) -> str:
    t = f"{function_name} {purpose}".lower()
    if any(x in t for x in ["purpose", "scope", "decision", "boundary"]):
        return "purpose_scope"
    if any(x in t for x in ["mapping", "component", "state", "entity", "boundary"]):
        return "system_boundary_and_mapping"
    if any(x in t for x in ["data", "pipeline", "stream", "storage", "schema", "source", "record"]):
        return "data_pipeline"
    if any(x in t for x in ["quality", "clean", "metadata", "preprocess", "completeness"]):
        return "data_quality"
    if any(x in t for x in ["sync", "latency", "update", "alignment"]):
        return "synchronization"
    if any(x in t for x in ["replication", "comparison", "match", "deviation", "calibration", "reproduce"]):
        return "replication_accuracy"
    if any(x in t for x in ["dashboard", "view", "visual", "interface", "display"]):
        return "interface_and_visualization"
    if any(x in t for x in ["decision", "recommend", "threshold", "alert", "support"]):
        return "decision_support_readiness"
    return "general"


def dtv_match_related_action_items(function_obj: Dict[str, Any], action_titles: List[str], limit: int = 2) -> List[str]:
    name = normalize_ws(function_obj.get("name", "")).lower()
    purpose = normalize_ws(function_obj.get("purpose", "")).lower()
    related_bits = [normalize_ws(x).lower() for x in function_obj.get("related_decisions", []) if normalize_ws(x)]
    related_bits += [normalize_ws(x).lower() for x in function_obj.get("related_variables", []) if normalize_ws(x)]
    related_bits += [normalize_ws(x).lower() for x in function_obj.get("related_system_elements", []) if normalize_ws(x)]
    tokens = set(re.findall(r"[a-zA-Z][a-zA-Z0-9\-/]+", " ".join([name, purpose] + related_bits)))
    ranked = []
    for title in action_titles:
        title_l = title.lower()
        title_tokens = set(re.findall(r"[a-zA-Z][a-zA-Z0-9\-/]+", title_l))
        overlap = len(tokens & title_tokens)
        if overlap:
            ranked.append((overlap, title))
    ranked.sort(reverse=True)
    out = [title for _, title in ranked[:limit]]
    if not out and action_titles:
        out = action_titles[:1]
    return out


def dtv_build_example_from_context(
    *,
    domain_context: Dict[str, Any],
    function_obj: Dict[str, Any],
    focus_area: str,
    current_target_level: str,
) -> str:
    system_type = normalize_ws(domain_context.get("system_type", "")) or "system"
    vars_text = dtv_compose_list_text(function_obj.get("related_variables", []), dtv_compose_list_text(domain_context.get("candidate_variables", []), "key variables"))
    elems_text = dtv_compose_list_text(function_obj.get("related_system_elements", []), dtv_compose_list_text(domain_context.get("physical_components", []), "key system elements"))
    decisions_text = dtv_compose_list_text(function_obj.get("related_decisions", []), dtv_compose_list_text(domain_context.get("primary_decisions", []), "the intended operational decisions"))
    sources_text = dtv_compose_list_text(domain_context.get("data_sources", []), "available operational data sources")
    lvl = str(current_target_level).strip().upper()

    if focus_area == "purpose_scope":
        return f"For this {system_type} use case, confirm that the digital twin scope is sufficient to support {decisions_text} and that the included and excluded boundaries are explicitly agreed."
    if focus_area == "system_boundary_and_mapping":
        return f"For this {system_type} use case, map elements such as {elems_text} into the digital representation and confirm that the required states and interfaces are included."
    if focus_area == "data_pipeline":
        return f"For this {system_type} use case, confirm that variables such as {vars_text} are captured from {sources_text} with consistent timestamps and stored in the expected schema."
    if focus_area == "data_quality":
        return f"For this {system_type} use case, check that records for {vars_text} remain complete, correctly named, and usable for the intended decisions."
    if focus_area == "synchronization":
        return f"For this {system_type} use case, verify that incoming updates from {sources_text} keep the digital twin aligned closely enough for the current {lvl} boundary."
    if focus_area == "replication_accuracy":
        return f"For this {system_type} use case, compare the digital twin output for {vars_text} against recorded real-system behavior and document any deviation and calibration changes."
    if focus_area == "interface_and_visualization":
        return f"For this {system_type} use case, confirm that the interface presents {vars_text} clearly enough for users making {decisions_text}."
    if focus_area == "decision_support_readiness":
        return f"For this {system_type} use case, check that the digital twin outputs are traceable and useful enough to support {decisions_text} within the current {lvl} boundary."
    return f"For this {system_type} use case, apply verification and validation to elements such as {elems_text} and variables such as {vars_text} for {decisions_text}."


def dtv_make_row_from_action_item(
    *,
    action_row: Dict[str, Any],
    domain_context: Dict[str, Any],
    current_target_level: str,
) -> Dict[str, str]:
    title = normalize_ws(action_row.get("action_item", ""))
    what_to_do = normalize_ws(action_row.get("what_to_do", ""))
    why = normalize_ws(action_row.get("why_it_matters", ""))
    focus = classify_dtv_focus_generic(title, what_to_do or why)
    rule = DTV_GENERIC_RULES.get(focus, DTV_GENERIC_RULES["general"])
    decisions_text = dtv_compose_list_text(domain_context.get("primary_decisions", []), "the intended operational decisions")
    expected = normalize_ws(action_row.get("expected_output_or_evidence", ""))
    dependencies = normalize_ws(action_row.get("dependencies_or_gaps", ""))
    example = normalize_ws(action_row.get("use_case_specific_example", ""))
    if not example:
        example = dtv_build_example_from_context(
            domain_context=domain_context,
            function_obj={
                "name": title,
                "purpose": what_to_do or why or title,
                "related_system_elements": domain_context.get("physical_components", []),
                "related_variables": action_row.get("required_data_or_inputs", []) or domain_context.get("candidate_variables", []),
                "related_decisions": domain_context.get("primary_decisions", []),
            },
            focus_area=focus,
            current_target_level=current_target_level,
        )
    verify = rule["verify"]
    validate = rule["validate"]
    if title:
        verify += f" This row supports the 4R action item: {title}."
        validate += f" Confirm that this action item is sufficient for {decisions_text}."
    if what_to_do:
        verify += f" Implementation focus: {what_to_do}"
    if str(current_target_level).strip().upper() == "R1":
        validate = "Validate that the selected variables, data sources, schemas, and system boundaries accurately reflect the real system and are useful enough for the intended decisions, even if full replication validation is not yet applicable."
    evidence_parts = list(rule.get("evidence", []))
    if expected:
        evidence_parts.insert(0, expected)
    if dependencies:
        evidence_parts.append(f"dependency or gap note: {dependencies}")
    evidence_text = "; ".join(dict.fromkeys([normalize_ws(x) for x in evidence_parts if normalize_ws(x)]))
    criteria_text = default_acceptance_for_dtv(title + " " + what_to_do, current_target_level)
    return {
        "existing_4r_action_item": title,
        "dtv_stage_or_focus_area": rule["stage"],
        "what_should_be_verified": verify,
        "what_should_be_validated": validate,
        "evidence_to_collect": evidence_text,
        "suggested_acceptance_criteria": criteria_text,
        "use_case_specific_example": example,
    }


def dtv_make_row_from_function(
    *,
    function_obj: Dict[str, Any],
    domain_context: Dict[str, Any],
    current_target_level: str,
    related_action_titles: List[str],
) -> Dict[str, str]:
    focus = classify_dtv_focus_generic(function_obj.get("name", ""), function_obj.get("purpose", ""))
    rule = DTV_GENERIC_RULES.get(focus, DTV_GENERIC_RULES["general"])
    system_type = normalize_ws(domain_context.get("system_type", "")) or "system"
    decisions_text = dtv_compose_list_text(function_obj.get("related_decisions", []), dtv_compose_list_text(domain_context.get("primary_decisions", []), "the intended operational decisions"))
    variables_text = dtv_compose_list_text(function_obj.get("related_variables", []), dtv_compose_list_text(domain_context.get("candidate_variables", []), "the required variables"))
    sources_text = dtv_compose_list_text(domain_context.get("data_sources", []), "the available data sources")
    elements_text = dtv_compose_list_text(function_obj.get("related_system_elements", []), dtv_compose_list_text(domain_context.get("physical_components", []), "the relevant system elements"))
    verify = rule["verify"].replace("the real system", f"the real {system_type}").replace("the digital twin", "the digital twin")
    validate = rule["validate"].replace("the real system", f"the real {system_type}").replace("the intended operational use case", decisions_text or "the intended operational use case")
    if focus == "data_pipeline":
        verify += f" Focus on variables such as {variables_text} and sources such as {sources_text}."
        validate += f" Confirm that the resulting data can support {decisions_text or 'the intended operational decisions'}."
    elif focus == "system_boundary_and_mapping":
        verify += f" Focus on elements such as {elements_text}."
        validate += f" Confirm that the selected representation supports {decisions_text or 'the intended operational decisions'}."
    elif focus == "replication_accuracy":
        verify += f" Focus on the outputs and state behavior associated with {variables_text}."
        validate += f" Compare the replicated behavior to recorded real-system behavior relevant to {decisions_text or 'the intended operational decisions'}."
    elif focus == "decision_support_readiness":
        verify += f" Focus on the outputs that inform {decisions_text or 'the intended operational decisions'}."

    if str(current_target_level).strip().upper() == "R1":
        validate = "Validate that the selected variables, data sources, schemas, and system boundaries accurately reflect the real system and are useful for the intended decisions."
    evidence = "; ".join(rule["evidence"])
    criteria = "; ".join(rule["criteria"])
    example = dtv_build_example_from_context(
        domain_context=domain_context,
        function_obj=function_obj,
        focus_area=focus,
        current_target_level=current_target_level,
    )
    return {
        "existing_4r_action_item": " / ".join(related_action_titles) if related_action_titles else normalize_ws(function_obj.get("name", "")),
        "dtv_stage_or_focus_area": rule["stage"],
        "what_should_be_verified": verify,
        "what_should_be_validated": validate,
        "evidence_to_collect": evidence,
        "suggested_acceptance_criteria": criteria,
        "use_case_specific_example": example,
    }


def dtv_generate_generic_result(
    *,
    kb: Dict[str, Any],
    sector: str,
    problem_statement: str,
    fourr_result: Dict[str, Any],
    fours_result: Dict[str, Any],
    domain_context: Dict[str, Any],
    functions_payload: Dict[str, Any],
) -> Dict[str, Any]:
    current_target_level = get_current_4r_target_level_for_dtv(fourr_result)
    baseline_level = str(fourr_result.get("current_supported_target_level", "")).strip()
    action_titles = extract_fourr_action_titles(fourr_result)
    action_rows = extract_fourr_action_rows(fourr_result, max_level=current_target_level)
    current_functions = [x for x in functions_payload.get("current_functions", []) if isinstance(x, dict) and normalize_ws(x.get("name", ""))]
    future_functions = [x for x in functions_payload.get("future_functions", []) if isinstance(x, dict) and normalize_ws(x.get("name", ""))]

    rows: List[Dict[str, str]] = []
    if action_rows:
        for action_row in action_rows:
            rows.append(dtv_make_row_from_action_item(action_row=action_row, domain_context=domain_context, current_target_level=current_target_level))
    else:
        for fn in current_functions[:8]:
            related = dtv_match_related_action_items(fn, action_titles, limit=1)
            rows.append(dtv_make_row_from_function(function_obj=fn, domain_context=domain_context, current_target_level=current_target_level, related_action_titles=related))

    current_summary = build_fallback_4r_context_summary_for_dtv(fourr_result)
    trust_boundary = build_fallback_target_boundary_for_dtv(current_target_level)
    system_type = normalize_ws(domain_context.get("system_type", sector or "system"))
    decisions_text = dtv_compose_list_text(domain_context.get("primary_decisions", []), "the intended operational decisions")
    data_sources = dtv_compose_list_text(domain_context.get("data_sources", []), "the available data sources")
    if baseline_level and baseline_level != current_target_level:
        role = (
            f"DTV should act as a verification, validation, and trust-evidence layer that supports the recommended {current_target_level} build target while first closing the lower-level trust-evidence gaps reflected by the current evidence baseline of {baseline_level}. "
            f"For this {system_type} use case, DTV should connect each lower-level and current-level 4R action item to concrete checks, evidence artifacts, and measurable acceptance criteria using data and records from {data_sources} where applicable."
        )
    else:
        role = (
            f"DTV should act as a verification, validation, and trust-evidence layer for the current {current_target_level or 'active'} 4R target. "
            f"For this {system_type} use case, that means connecting each current-level 4R action item to concrete checks, evidence artifacts, and measurable acceptance criteria so the digital twin can be trusted for {decisions_text}."
        )

    verification_guidance = list(dict.fromkeys([row["what_should_be_verified"] for row in rows]))
    validation_guidance = list(dict.fromkeys([row["what_should_be_validated"] for row in rows]))

    gaps = []
    if not domain_context.get("data_sources"):
        gaps.append("The use case does not clearly identify the data sources needed to support verification and validation.")
    if not domain_context.get("candidate_variables"):
        gaps.append("The use case does not clearly define the key variables needed for evidence-driven verification and validation.")
    if current_target_level == "R2":
        gaps.append("Replication cannot be trusted until the modeling platform, physical-to-digital mapping, live or recorded data integration, and controlled comparison cases are documented with acceptable deviation thresholds.")
        gaps.append("Scheduling, optimization, or predictive-maintenance outcomes cannot be validated until the required records, constraints, and comparison datasets are linked to the digital twin inputs and outputs.")
    elif current_target_level == "R1":
        gaps.append("Representation cannot be trusted until the selected variables, data sources, schemas, and system boundaries are explicitly reviewed and shown to support the intended decisions.")
    for action_row in action_rows:
        deps = normalize_ws(action_row.get("dependencies_or_gaps", ""))
        if deps:
            gaps.append(deps)
    for f in future_functions[:6]:
        reason = normalize_ws(f.get("reason_future", ""))
        if reason:
            gaps.append(reason)

    dtv_actions = []
    for row in rows[:12]:
        dtv_actions.append(f"{row['existing_4r_action_item']}: verify {row['what_should_be_verified'].lower()} Evidence: {row['evidence_to_collect']}. Acceptance criteria: {row['suggested_acceptance_criteria']}")

    future_work = []
    for f in future_functions[:8]:
        name = normalize_ws(f.get("name", ""))
        reason = normalize_ws(f.get("reason_future", ""))
        if name:
            future_work.append(f"{name}: {reason}" if reason else name)

    return {
        "section1_4r_context_summary": current_summary,
        "section2_dtv_role_for_this_use_case": role,
        "section3_current_target_trust_boundary": trust_boundary,
        "dtv_development_and_vv_table": rows,
        "verification_guidance": verification_guidance,
        "validation_guidance": validation_guidance,
        "gaps_and_risks": list(dict.fromkeys(gaps)),
        "dtv_aligned_action_items": dtv_actions,
        "section9_future_dtv_work_beyond_current_target": future_work,
    }

def run_dtv_assessment_addon(
    *,
    dtc_outdir: Path,
    log_path: Path,
    dtv_kb_path: Path,
    sector: str,
    problem_statement: str,
    outputs: Dict[str, str],
    priorities: Dict[str, str],
    dtaf_outdir: Optional[Path],
    fourr_outdir: Optional[Path],
    fours_outdir: Optional[Path],
    extra_evidence: str,
    base_url: str,
    model: str,
    timeout: float,
    retries: int,
) -> Path:
    if fourr_outdir is None or not fourr_outdir.exists():
        raise RuntimeError("DTV assessment requires an existing 4R result directory. Do not skip 4R if you want to run DTV.")

    kb = load_dtv_kb(dtv_kb_path)
    dtaf_inputs = load_dtaf_4r_inputs(dtaf_outdir)
    fourr_inputs = load_4r_inputs_for_4s(fourr_outdir)
    fours_inputs = load_4s_inputs_for_dtv(fours_outdir)

    current_target_level = get_current_4r_target_level_for_dtv(fourr_inputs.get("result", {}))

    evidence_bundle = build_dtv_evidence_bundle(
        kb=kb,
        sector=sector,
        problem_statement=problem_statement,
        outputs=outputs,
        priorities=priorities,
        dtaf_inputs=dtaf_inputs,
        fourr_inputs=fourr_inputs,
        fours_inputs=fours_inputs,
        extra_evidence=extra_evidence,
    )

    # Generic, domain-adaptive DTV pipeline:
    # 1) extract domain context
    # 2) extract DT functions relevant to the current 4R boundary
    # 3) generate deterministic DTV rows from generic templates
    raw_obj: Dict[str, Any] = {}
    try:
        domain_context = dtv_extract_domain_context_with_ollama(
            base_url=base_url,
            model=model,
            timeout=timeout,
            retries=retries,
            sector=sector,
            problem_statement=problem_statement,
            fourr_result=fourr_inputs.get("result", {}),
        )
    except Exception:
        domain_context = dtv_extract_domain_context_fallback(
            sector=sector,
            problem_statement=problem_statement,
            fourr_result=fourr_inputs.get("result", {}),
        )

    try:
        function_inventory = dtv_extract_functions_with_ollama(
            base_url=base_url,
            model=model,
            timeout=timeout,
            retries=retries,
            problem_statement=problem_statement,
            current_target_level=current_target_level,
            domain_context=domain_context,
            fourr_result=fourr_inputs.get("result", {}),
        )
    except Exception:
        function_inventory = dtv_extract_functions_fallback(
            problem_statement=problem_statement,
            current_target_level=current_target_level,
            fourr_result=fourr_inputs.get("result", {}),
            domain_context=domain_context,
        )

    raw_obj = {
        "domain_context": domain_context,
        "function_inventory": function_inventory,
    }

    result = dtv_generate_generic_result(
        kb=kb,
        sector=sector,
        problem_statement=problem_statement,
        fourr_result=fourr_inputs.get("result", {}),
        fours_result=fours_inputs.get("result", {}),
        domain_context=domain_context,
        functions_payload=function_inventory,
    )
    result = dtv_validate_result(result)
    if not result.get("section1_4r_context_summary"):
        result["section1_4r_context_summary"] = build_fallback_4r_context_summary_for_dtv(fourr_inputs.get("result", {}))
    if not result.get("section3_current_target_trust_boundary"):
        result["section3_current_target_trust_boundary"] = build_fallback_target_boundary_for_dtv(current_target_level)
    result = dtv_postprocess_result(result, fourr_inputs.get("result", {}), sector, problem_statement, current_target_level)

    outdir = dtc_outdir / f"dtv_assessment_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
    ensure_dir(outdir)
    write_text(outdir / "dtv_kb_compact.json", json.dumps(compact_dtv_kb_for_prompt(kb), indent=2))
    write_text(outdir / "dtv_inputs.json", json.dumps({
        "dtaf_inputs": dtaf_inputs,
        "fourr_inputs": fourr_inputs,
        "fours_inputs": fours_inputs,
        "selected_capabilities": compact_priorities_for_4s(priorities),
    }, indent=2))
    write_text(outdir / "dtv_evidence_bundle.txt", evidence_bundle)
    write_text(outdir / "dtv_domain_context.json", json.dumps(domain_context, indent=2))
    write_text(outdir / "dtv_function_inventory.json", json.dumps(function_inventory, indent=2))
    write_text(outdir / "dtv_assessment_raw.json", json.dumps(raw_obj, indent=2))
    write_text(outdir / "dtv_assessment_result.json", json.dumps(result, indent=2))
    write_text(outdir / "dtv_assessment_summary.md", dtv_result_to_markdown(result, current_target_level=current_target_level))

    append_jsonl(
        log_path,
        {
            "step": "DTV_assessment_addon",
            "time_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "output_path": str((outdir / "dtv_assessment_summary.md").name),
        },
    )

    print("\nDTV assessment complete.")
    print(f"Saved: {outdir.resolve()}")
    print(f" - {outdir / 'dtv_assessment_summary.md'}")
    print(f" - {outdir / 'dtv_assessment_result.json'}\n")
    return outdir


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default="http://localhost:11434/v1",
                    help="Ollama OpenAI-compatible base URL, e.g. http://localhost:11434/v1")
    ap.add_argument("--model", default="auto",
                    help="Ollama model name, or 'auto' to select one from detected hardware and installed Ollama models")
    ap.add_argument("--auto-model-profile", default="safe", choices=["safe", "balanced", "performance"],
                    help="Auto-model resource profile. safe caps auto-selection at 7B-class models; balanced can use 14B-class models; performance can use larger workstation models")
    ap.add_argument("--ollama-num-thread", type=int, default=0,
                    help="CPU threads to request from Ollama. 0 = safe automatic cap; -1 = leave unset")
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
    ap.add_argument("--skip-4r", action="store_true",
                    help="Skip 4R assessment after the DTC and DTAF steps")
    ap.add_argument("--fourr-kb", default="4R_AI_Assessment_Knowledge_Base.json",
                    help="4R assessment knowledge base JSON file in the script folder, unless a full path is provided")
    ap.add_argument("--fourr-extra-evidence", default="",
                    help="Optional extra text or markdown file with evidence for the 4R assessment")
    ap.add_argument("--fourr-max-actions", type=int, default=8,
                    help="Maximum number of suggested action items to include in the 4R assessment output")
    ap.add_argument("--intended-4r-target", default="", choices=["", "R1", "R2", "R3", "R4"],
                    help="Optional intended pre-build 4R target to preserve in planning, even if the current explicit evidence baseline is lower")
    ap.add_argument("--skip-4s", action="store_true",
                    help="Skip 4S assessment after the 4R step")
    ap.add_argument("--fours-kb", default="4S_Framework_Knowledge_Base.json",
                    help="4S framework knowledge base JSON file in the script folder, unless a full path is provided")
    ap.add_argument("--fours-extra-evidence", default="",
                    help="Optional extra text or markdown file with evidence for the 4S assessment")
    ap.add_argument("--skip-dtv", action="store_true",
                    help="Skip DTV assessment after the 4R step")
    ap.add_argument("--dtv-kb", default="DTV_Framework_Knowledge_Base.json",
                    help="DTV framework knowledge base JSON file in the script folder, unless a full path is provided")
    ap.add_argument("--dtv-extra-evidence", default="",
                    help="Optional extra text or markdown file with evidence for the DTV assessment")
    args = ap.parse_args()

    script_dir = Path(__file__).resolve().parent
    loaded = load_required_files(script_dir)

    fourr_kb_path = Path(args.fourr_kb)
    if not fourr_kb_path.is_absolute():
        fourr_kb_path = script_dir / fourr_kb_path

    fours_kb_path = Path(args.fours_kb)
    if not fours_kb_path.is_absolute():
        fours_kb_path = script_dir / fours_kb_path

    dtv_kb_path = Path(args.dtv_kb)
    if not dtv_kb_path.is_absolute():
        dtv_kb_path = script_dir / dtv_kb_path

    # Inputs for blanks
    sector = ask_input_nonempty("Step 0 blank: What sector should be analyzed (e.g., 'manufacturing', 'energy', 'healthcare')? ")
    problem_statement = ask_multiline("Step 1 blank: Paste the problem statement for the digital twin use case:")

    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    outdir = Path(args.outdir) if args.outdir else Path(f"dtc_cpt_run_{ts}")
    ensure_dir(outdir)
    log_path = outdir / "run_log.jsonl"
    dtaf_outdir: Optional[Path] = None
    fourr_outdir: Optional[Path] = None
    fours_outdir: Optional[Path] = None
    dtv_outdir: Optional[Path] = None

    model_selection = resolve_model_for_hardware(
        requested_model=args.model,
        base_url=args.base_url,
        timeout=args.timeout,
        resource_profile=args.auto_model_profile,
        requested_num_thread=args.ollama_num_thread,
    )
    args.model = str(model_selection["selected_model"])
    OLLAMA_RUNTIME_OPTIONS.clear()
    OLLAMA_RUNTIME_OPTIONS.update(model_selection.get("runtime_options", {}))
    print_model_selection(model_selection)
    append_jsonl(
        log_path,
        {
            "step": "run_configuration",
            "time_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "model_selection": model_selection,
            "deterministic_completion_fields": DETERMINISTIC_COMPLETION_FIELDS,
        },
    )

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
                "Keep the analysis generic to the user's stated sector and problem statement. "
                "Do not import assets, technologies, workflows, examples, or assumptions from unrelated domains. "
                "If the use case lacks detail, name the missing information instead of inventing domain specifics."
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
    dtaf_outdir: Optional[Path] = None
    fourr_outdir: Optional[Path] = None
    fours_outdir: Optional[Path] = None
    dtv_outdir: Optional[Path] = None

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
    parsed_priorities = parse_priorities_from_text(step2_text)
    priorities, priority_floor_applied = apply_capability_priority_floor(
        parsed_priorities,
        sector=sector,
        problem_statement=problem_statement,
    )
    priority_counts = {p: sum(1 for v in priorities.values() if v == p) for p in ("E", "H", "F")}
    if not priorities:
        print("[warn] No capability priorities were parsed from Step 2. Step 4 will still render, but no priority badges will be shown.")
    else:
        print(f"Parsed capability priorities: E={priority_counts['E']}, H={priority_counts['H']}, F={priority_counts['F']}")
        if priority_floor_applied:
            print(f"Applied capability priority floors to stabilize {len(priority_floor_applied)} capabilities from explicit use-case language.")
    write_text(outdir / "priorities.json", json.dumps(priorities, indent=2))
    if priority_floor_applied:
        write_text(outdir / "priority_floor_applied.json", json.dumps(priority_floor_applied, indent=2))
    det_html = generate_cpt_html(priorities)
    write_text(outdir / "step4_cpt_table.html", det_html)

    append_jsonl(
        log_path,
        {
            "step": "4_deterministic",
            "time_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "output_path": "step4_cpt_table.html",
            "priority_count": len(priorities),
            "priority_counts": priority_counts,
            "parsed_priority_count": len(parsed_priorities),
            "priority_floor_applied": priority_floor_applied,
            "priority_parse_warning": "" if priorities else "No E/H/F capability priorities parsed from Step 2 output.",
        },
    )

    # -----------------------------
    # Capability Feasibility Checklist Context
    # -----------------------------
    if not args.skip_dtaf:
        try:
            dtaf_outdir = run_dtaf_addon_after_step4(
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

    if not args.skip_4r:
        try:
            extra_evidence = ""
            if args.fourr_extra_evidence:
                extra_path = Path(args.fourr_extra_evidence)
                if not extra_path.is_absolute():
                    extra_path = script_dir / extra_path
                if extra_path.exists():
                    extra_evidence = read_text(extra_path)
                else:
                    extra_evidence = args.fourr_extra_evidence

            fourr_outdir = run_4r_assessment_addon(
                dtc_outdir=outdir,
                log_path=log_path,
                fourr_kb_path=fourr_kb_path,
                sector=sector,
                problem_statement=problem_statement,
                outputs=outputs,
                priorities=priorities,
                dtaf_outdir=dtaf_outdir,
                extra_evidence=extra_evidence,
                base_url=args.base_url,
                model=args.model,
                timeout=args.timeout,
                retries=args.retries,
                max_actions=args.fourr_max_actions,
                intended_target_level=args.intended_4r_target,
            )
        except KeyboardInterrupt:
            print("\n4R assessment interrupted (Ctrl+C). Continuing...")
        except Exception as e:
            print(f"\n[warn] 4R assessment failed: {e}")

    if not args.skip_4s:
        try:
            extra_evidence = ""
            if args.fours_extra_evidence:
                extra_path = Path(args.fours_extra_evidence)
                if not extra_path.is_absolute():
                    extra_path = script_dir / extra_path
                if extra_path.exists():
                    extra_evidence = read_text(extra_path)
                else:
                    extra_evidence = args.fours_extra_evidence

            fours_outdir = run_4s_assessment_addon(
                dtc_outdir=outdir,
                log_path=log_path,
                fours_kb_path=fours_kb_path,
                sector=sector,
                problem_statement=problem_statement,
                outputs=outputs,
                priorities=priorities,
                dtaf_outdir=dtaf_outdir,
                fourr_outdir=fourr_outdir,
                extra_evidence=extra_evidence,
                base_url=args.base_url,
                model=args.model,
                timeout=args.timeout,
                retries=args.retries,
            )
        except KeyboardInterrupt:
            print("\n4S assessment interrupted (Ctrl+C). Continuing...")
        except Exception as e:
            print(f"\n[warn] 4S assessment failed: {e}")

    if not args.skip_dtv:
        try:
            extra_evidence = ""
            if args.dtv_extra_evidence:
                extra_path = Path(args.dtv_extra_evidence)
                if not extra_path.is_absolute():
                    extra_path = script_dir / extra_path
                if extra_path.exists():
                    extra_evidence = read_text(extra_path)
                else:
                    extra_evidence = args.dtv_extra_evidence

            dtv_outdir = run_dtv_assessment_addon(
                dtc_outdir=outdir,
                log_path=log_path,
                dtv_kb_path=dtv_kb_path,
                sector=sector,
                problem_statement=problem_statement,
                outputs=outputs,
                priorities=priorities,
                dtaf_outdir=dtaf_outdir,
                fourr_outdir=fourr_outdir,
                fours_outdir=fours_outdir,
                extra_evidence=extra_evidence,
                base_url=args.base_url,
                model=args.model,
                timeout=args.timeout,
                retries=args.retries,
            )
        except KeyboardInterrupt:
            print("\nDTV assessment interrupted (Ctrl+C). Continuing...")
        except Exception as e:
            print(f"\n[warn] DTV assessment failed: {e}")

    
    final_html_path = generate_final_html_report(
        outdir=outdir,
        sector=sector,
        problem_statement=problem_statement,
        dtaf_outdir=dtaf_outdir,
        fourr_outdir=fourr_outdir,
        fours_outdir=fours_outdir,
        dtv_outdir=dtv_outdir,
    )
    
    append_jsonl(
        log_path,
        {
            "step": "final_html_report",
            "time_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "output_path": final_html_path.name,
        },
    )
    
    print("\nDONE.")
    print(f"Outputs written to: {outdir.resolve()}")
    print("Primary file:")
    print(f" - {final_html_path}")
    print("Supporting files:")
    print(f" - {outdir / 'step0_use_case_suitability.md'}")
    print(f" - {outdir / 'step1_business_requirements.md'}")
    print(f" - {outdir / 'step2_capability_selector.md'}")
    print(f" - {outdir / 'step3_capability_deep_dives.md'}")
    print(f" - {outdir / 'priorities.json'}")
    print(f" - {outdir / 'step4_cpt_table.html'}")
    print(f" - {outdir / 'run_log.jsonl'}")
    if dtaf_outdir is not None:
        print(f" - {dtaf_outdir / 'summary.md'}")
    if fourr_outdir is not None:
        print(f" - {fourr_outdir / '4r_assessment_summary.md'}")
        print(f" - {fourr_outdir / '4r_assessment_result.json'}")
    if fours_outdir is not None:
        print(f" - {fours_outdir / '4s_assessment_summary.md'}")
        print(f" - {fours_outdir / '4s_assessment_result.json'}")
    if dtv_outdir is not None:
        print(f" - {dtv_outdir / 'dtv_assessment_summary.md'}")
        print(f" - {dtv_outdir / 'dtv_assessment_result.json'}")


if __name__ == "__main__":
    main()
