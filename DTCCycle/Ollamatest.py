#!/usr/bin/env python3
"""

Runs the Digital Twin Consortium CPT prompt workflow (Steps 0–4)

Prereqs:
  - Install Ollama
  - Pull model:  ollama pull qwen2.5:7b

"""

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import urljoin
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError


# -----------------------------
# DTC prompts (as provided)
# -----------------------------

STEP0_PROMPT = """Analyze the following [Blank] sector and identify the most common challenges and key problems across major business areas such as operations, demand forecasting, technology integration, customer engagement, and regulatory compliance. For each area, list the typical issues organizations face, explain their root causes, and describe their impact on business performance. Where relevant, highlight recent trends or disruptions that have intensified these challenges. Structure your response by business area, and provide concise, actionable insights that could inform strategic decision-making."""

STEP1_PROMPT = """Instructions
Please provide a comprehensive business requirements specification for a digital twin solution based on the problem statement below. Structure your response to include all relevant contextual information that would help identify required capabilities from the Digital Twin Capabilities Periodic Table.
Problem Statement
[Blank]
Generate a detailed response that includes:
1. Business Context
Industry sector and specific domain (e.g., manufacturing, energy, healthcare)
Scale of operations (number of assets, locations, etc.)
Current operational environment and key constraints
Primary stakeholders and their roles in a table
2. Problem Analysis
Root causes of the current challenges
Quantifiable business impact of the problem (financial, operational, safety, etc.)
Current approaches and their limitations in a table
Critical decision points affected by this problem
3. Digital Twin Objectives
Primary business goals for the digital twin solution
Key performance indicators (KPIs) to measure success in a table
Required timeframe for implementation and value realization
Strategic alignment with broader organizational initiatives
4. Operational Requirements
Real-time vs. batch processing needs
Data update frequency requirements
Decision-making processes to be supported
Integration with existing systems and workflows
Level of automation desired
5. Data Requirements
Types of data needed (operational, historical, contextual, etc.)
Data sources available (sensors, enterprise systems, etc.)
Data quality and completeness assessment
Data volume, velocity, and variety considerations
Any special requirements around data governance or compliance
6. User Experience Requirements
Primary users and their roles
Visualization and interaction needs
Alert and notification requirements
Collaboration and knowledge sharing aspects
Mobile/remote access requirements
7. Technical Considerations
Existing technology infrastructure
Deployment environment preferences (edge, cloud, hybrid)
Security and compliance requirements
Scalability needs for future expansion
Performance expectations
8. Implementation Approach
Phasing and prioritization recommendations
Key risks and mitigations
Success criteria
Organizational readiness considerations
Your specification should be detailed enough to serve as a foundation for identifying the specific capabilities needed from the Digital Twin Capabilities Periodic Table in a subsequent analysis.
Please use Claude artifacts."""

STEP2_PROMPT = """Instructions
Based on the detailed business requirements specification from the previous step, please identify and justify the specific capabilities from the Digital Twin Capabilities Periodic Table that would be required to support this digital twin use case.
Analysis Tasks
1. Capability Mapping
For each of the six capability categories in the Digital Twin Capabilities Periodic Table, identify which specific capabilities would be required for this use case and present the results in a table:
Data Services (DS)
List and explain required capabilities (e.g., DS.AI, DS.ST, DS.TR, etc.)
Justify each selection based on the business requirements
Note deployment considerations (edge, fog, cloud) for each capability
Integration (IR)
List and explain required capabilities (e.g., IR.ET, IR.EG, IR.IO, etc.)
Justify each selection based on the business requirements
Identify key systems that would need integration
Intelligence (IC)
List and explain required capabilities (e.g., IC.SR, IC.PR, IC.AI, etc.)
Justify each selection based on the business requirements
Highlight critical intelligence capabilities for business value
User Experience (UX)
List and explain required capabilities (e.g., UX.BV, UX.AV, UX.RM, etc.)
Justify each selection based on the business requirements
Consider different user roles and their needs
Management (MG)
List and explain required capabilities (e.g., MG.DM, MG.SM, MG.EL, etc.)
Justify each selection based on the business requirements
Consider operational governance needs
Trustworthiness (TW)
List and explain required capabilities (e.g., TW.SC, TW.PR, TW.SF, etc.)
Justify each selection based on the business requirements
Highlight critical security or compliance considerations
2. Capability Priority Assessment
Classify each identified capability as:
Essential (must have for minimum viable solution)
High Value (important for full business value)
Future Enhancement (beneficial for long-term evolution)
3. Digital Twin Capability Periodic Table Visualization
Create a simple text-based table showing the selected capabilities from the Digital Twin Capabilities Periodic Table
For each selected capability, indicate its priority level (Essential, High Value, or Future Enhancement) using the notation: [E], [H], or [F]
Use a format like DS.AI [E] to indicate the capability ID and its priority level
4. Implementation Considerations
Identify any capability gaps or challenges in implementing the required capabilities
Recommend potential phasing approach for capability implementation
Note any specialized expertise needed for specific capabilities
Your analysis should provide a clear roadmap of which Digital Twin Capabilities would be required to successfully implement the solution described in the business requirements.
Please use Claude artifacts."""

STEP3_PART1_PROMPT = """Instructions: Based on the capability analysis from the previous step, please provide a deeper examination of the most critical capabilities identified for this digital twin use case.

Capability Deep Dives

- For the most critical 3-5 capabilities identified in your previous analysis, provide a deeper analysis of:
    - Specific requirements for this use case
    - Success criteria for this capability
    - Recommended technology approaches
    - Potential challenges in implementation

Please use the results of your previous capability mapping and prioritization to determine which capabilities warrant this deeper analysis.

Please use Claude artifacts
"""

STEP3_PART2_PROMPT = """Instructions: Based on the capability analysis from the previous step, please provide a deeper examination of:

(1) the most critical capabilities identified for this digital twin use case, and
(2) all Trustworthiness (TW) capabilities regardless of their priority level.

Capability Deep Dives

- For the most critical 3-5 capabilities identified in your previous analysis, plus ALL Trustworthiness (TW) capabilities, provide a deeper analysis of:
    - Specific requirements for this use case
    - Success criteria for this capability
    - Recommended technology approaches
    - Potential challenges in implementation

Please organize your response with the critical capabilities first, followed by a complete analysis of all Trustworthiness capabilities. For each capability, create a structured deep dive that addresses all four analysis points.

Please use the results of your previous capability mapping and prioritization to determine which non-Trustworthiness capabilities warrant deeper analysis, while ensuring all Trustworthiness capabilities receive detailed examination regardless of their priority level.

Please use Claude artifacts.
"""

STEP4_PROMPT = """You are an expert web developer. Generate a complete, self-contained HTML file for the Digital Twin Capabilities Periodic Table v1.2 as a clean, static display showing all 60+ capabilities. The output should include embedded CSS and JavaScript with no external dependencies.

## REQUIREMENTS:
### Visual Standards:
- Use the complete 60+ capability framework with proper positioning
- Apply these category colors exactly:
  - DS (Data Services): background #D1DCEA, border #7A9BC4, text #13386D
  - IR (Integration): background #FAEAD5, border #D4A571, text #945911  
  - IC (Intelligence & Cognition): background #E3DDEC, border #A18DB5, text #4E3D6F
  - UX (User Experience): background #EEEEEE, border #999999, text #404040
  - MG (Management): background #D5E3E1, border #7FA596, text #295548
  - TW (Trustworthiness): background #EDD9D5, border #C78275, text #792D21

### Layout Requirements:
- Display all capabilities at full opacity (no fading or hiding)
- Use CSS Grid with exactly 8 columns and 8 rows
- Follow the exact grid positioning specified below (true periodic table format)
- Include proper capability positioning as specified below
- Add legend showing all 6 categories with color samples
- Make responsive for mobile devices (stack to 4 columns on mobile, maintaining relative positioning)
- Include smooth CSS transitions for hover effects
- Minimum height of 80px per capability block
- Include each of the capabilities priorities that were identified in the Capability Priority Assessment

### Content Requirements:
- Page title: "Digital Twin Capabilities Periodic Table v1.2"
- Subtitle: "Complete Framework of 60+ Core Capabilities"
- No interactive buttons or controls (static display only)
- Include all capability blocks with correct IDs and names
- Professional typography using system fonts
- Clean spacing and modern design
- Center the content on the page
- Include each of the capabilities priorities that were identified in the Capability Priority Assessment

### CRITICAL - Exact Grid Positioning:
Use these exact positions for each capability in an 8x8 grid:

**Row 1:**
- Row 1, Col 1: DS.AI "Data Acquisition & Ingestion"
- Row 1, Col 2: DS.SG "Synthetic Data Generation" 
- Row 1, Col 3: IR.ET "Enterprise System Integration"
- Row 1, Col 4: IC.SR "Search"
- Row 1, Col 5: IC.PR "Prediction"
- Row 1, Col 6: UX.BV "Basic Visualization"
- Row 1, Col 7: UX.DB "Dashboards"

**Row 2:**
- Row 2, Col 1: DS.ST "Data Streaming"
- Row 2, Col 2: DS.ON "Ontology Management"
- Row 2, Col 3: IR.EG "Eng. System Integration"
- Row 2, Col 4: IC.CC "Command & Control"
- Row 2, Col 5: IC.AI "Artificial Intelligence"
- Row 2, Col 6: UX.AV "Advanced Visualization"
- Row 2, Col 7: UX.CI "Continuous Intelligence"

**Row 3:**
- Row 3, Col 1: DS.TR "Data Transformation"
- Row 3, Col 2: DS.RP "Digital Twin (DT) Model Repository"
- Row 3, Col 3: IR.IO "OT/IoT System Integration"
- Row 3, Col 4: IC.OS "Orchestration"
- Row 3, Col 5: IC.PS "Prescriptive Recommendations"
- Row 3, Col 6: UX.RM "Real-time Monitoring"
- Row 3, Col 7: UX.BI "Business Intelligence"

**Row 4:**
- Row 4, Col 1: DS.CX "Data Contextualization"
- Row 4, Col 2: DS.IR "DT Instance Repository"
- Row 4, Col 3: IR.DT "Digital Twin Integration"
- Row 4, Col 4: IC.AL "Alerts & Notifications"
- Row 4, Col 5: IC.FL "Federated Learning"
- Row 4, Col 6: IC.BR "Business Rules"
- Row 4, Col 7: UX.ER "Entity Relationship Visualization"
- Row 4, Col 8: UX.BP "BPM & Workflow"

**Row 5:**
- Row 5, Col 1: DS.BP "Batch Processing"
- Row 5, Col 2: DS.DS "Domain Specific Data Management"
- Row 5, Col 3: IR.CL "Collab Platform Integration"
- Row 5, Col 4: IC.RP "Reporting"
- Row 5, Col 5: IC.SM "Simulation"
- Row 5, Col 6: IC.DL "Distributed Ledger & Smart Contracts"
- Row 5, Col 7: UX.XR "Extended Reality (AV/VR/MR)"
- Row 5, Col 8: UX.GE "Gaming Engine Visualization"

**Row 6:**
- Row 6, Col 1: DS.RT "Real-time Processing"
- Row 6, Col 2: DS.SA "Data Storage & Archive Services"
- Row 6, Col 3: IR.AS "API Services"
- Row 6, Col 4: IC.AA "Data Analysis & Analytics"
- Row 6, Col 5: IC.MA "Mathematical Analytics"
- Row 6, Col 6: IC.CS "Composition"
- Row 6, Col 7: UX.GM "Gamification"
- Row 6, Col 8: UX.3R "3D Rendering"

**Row 7:**
- Row 7, Col 1: DS.AS "Asynchronous Integration"
- Row 7, Col 2: DS.SR "Simulation Model Repository"
- Row 7, Col 3: MG.DM "Device Management"
- Row 7, Col 4: MG.EL "Event Logging"
- Row 7, Col 5: TW.EX "Data Encryption"
- Row 7, Col 6: TW.SC "Security"
- Row 7, Col 7: TW.SF "Safety"
- Row 7, Col 8: TW.RP "Responsibility"

**Row 8:**
- Row 8, Col 1: DS.AG "Data Aggregation"
- Row 8, Col 2: DS.AR "AI Model Repository"
- Row 8, Col 3: MG.SM "System Monitoring"
- Row 8, Col 4: MG.DG "Data Governance"
- Row 8, Col 5: TW.DS "Device Security"
- Row 8, Col 6: TW.PR "Privacy"
- Row 8, Col 7: TW.RL "Reliability"
- Row 8, Col 8: TW.RS "Resilience"

### Technical Requirements:
- Single HTML file with embedded CSS and JavaScript
- Use CSS Grid with exactly 8 columns and 8 rows for the main periodic table
- Position each capability exactly as specified in the grid coordinates above
- No external dependencies, CDN links, or external files
- Fast loading and responsive design
- Works offline after download
- Compatible with all modern browsers (Chrome, Firefox, Safari, Edge)
- Include hover effects for better interactivity
- Clean, modern design with proper spacing matching the official DTC layout
- Print-friendly layout

### Structure Requirements:
- Use semantic HTML5 structure
- Include proper meta tags for viewport and charset
- Use CSS classes for styling categories
- Add JavaScript to populate the grid dynamically from capability arrays
- Include a comprehensive legend section at the bottom
- Add category descriptions in the legend
- Include version information and attribution

### Category Descriptions for Legend:
- DS: "Enables data access, ingestion and data management across the platform from the edge to the cloud"
- IR: "Enables data access to existing internal and external enterprise systems and applications"  
- IC: "Provides an environment for the development and deployment of industrial digital twin solutions"
- UX: "Provides the user with the ability to interact with digital twins and visualize its data"
- MG: "System and ecosystem management capabilities"
- TW: "Security, privacy, safety, reliability and resilience capabilities"

Generate the complete HTML file code that I can copy and save as a .html file.
"""


# -----------------------------
# Helpers
# -----------------------------

def ask_input(prompt: str, default: Optional[str] = None) -> str:
    if default is None:
        val = input(prompt).strip()
        while not val:
            val = input(prompt).strip()
        return val
    val = input(f"{prompt} [default: {default}] ").strip()
    return val if val else default

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

def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)

def append_jsonl(path: Path, obj: Dict) -> None:
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")

def write_text(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")

def extract_html(text: str) -> str:
    m = re.search(r"```html\s*(.*?)```", text, flags=re.DOTALL | re.IGNORECASE)
    if m:
        return m.group(1).strip()

    m3 = re.search(r"(<\!doctype.*?</html\s*>)", text, flags=re.DOTALL | re.IGNORECASE)
    if m3:
        return m3.group(1).strip()

    m4 = re.search(r"(<html.*?</html\s*>)", text, flags=re.DOTALL | re.IGNORECASE)
    if m4:
        return m4.group(1).strip()

    m2 = re.search(r"```(?:\w+)?\s*(.*?)```", text, flags=re.DOTALL | re.IGNORECASE)
    if m2:
        candidate = m2.group(1).strip()
        if candidate.lower().startswith("<!doctype") or candidate.lower().startswith("<html"):
            return candidate

    return text.strip()


# -----------------------------
# Ollama client 
# -----------------------------

def _post_json(url: str, payload: Dict, timeout: float) -> Dict:
    data = json.dumps(payload).encode("utf-8")
    req = Request(
        url=url,
        data=data,
        headers={
            "Content-Type": "application/json",
            # Ollama doesn't require auth, but some proxies expect this header to exist.
            "Authorization": "Bearer ollama",
        },
        method="POST",
    )
    try:
        with urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            return json.loads(body)
    except HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace") if hasattr(e, "read") else ""
        raise RuntimeError(f"HTTP {e.code} calling {url}\n{err_body}") from e
    except URLError as e:
        raise RuntimeError(f"Failed to reach {url}: {e}") from e
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Non-JSON response from {url}: {e}") from e

def chat_completions(
    *,
    base_url: str,
    model: str,
    messages: List[Dict[str, str]],
    max_tokens: int,
    temperature: float,
    timeout: float,
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

    resp = _post_json(endpoint, payload, timeout=timeout)

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
    max_tokens: int = 2048,
    temperature: float = 0.2,
) -> str:
    messages.append({"role": "user", "content": user_prompt})
    out = chat_completions(
        base_url=base_url,
        model=model,
        messages=messages,
        max_tokens=max_tokens,
        temperature=temperature,
        timeout=timeout,
    )
    messages.append({"role": "assistant", "content": out})
    return out


# -----------------------------
# Main
# -----------------------------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--base-url",
        default="http://localhost:11434/v1",
        help="Ollama OpenAI-compatible base URL, e.g. http://localhost:11434/v1",
    )
    ap.add_argument(
        "--model",
        default="qwen2.5:7b",
        help="Ollama model name, e.g. qwen2.5:7b",
    )
    ap.add_argument("--outdir", default="", help="Output directory (default: dtc_cpt_run_<timestamp>)")
    ap.add_argument("--timeout", type=float, default=180.0, help="HTTP timeout seconds")
    args = ap.parse_args()

    # Gather [Blank] inputs
    sector = ask_input("Step 0 blank: What sector should be analyzed (e.g., 'manufacturing', 'energy', 'healthcare')? ")
    problem_statement = ask_multiline("Step 1 blank: Paste the problem statement for the digital twin use case:")

    step3_mode = ask_input(
        "Step 3 deep dives: run (1)=Part 1, (2)=Part 2, (b)=both? ",
        default="2"
    ).lower().strip()
    if step3_mode not in {"1", "2", "b"}:
        step3_mode = "2"

    fmt = ask_input(
        "Output formatting preference (e.g., 'Markdown with headings and tables')?",
        default="Markdown with clear headings, bullet lists, and tables where requested."
    )
    artifacts_hint = (
        "\n\nNote on formatting: When the prompt says 'Please use Claude artifacts', "
        "treat that as 'use clean, structured Markdown with clear section headings; "
        "use fenced code blocks for any code/HTML; and tables where requested.'"
    )

    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    outdir = Path(args.outdir) if args.outdir else Path(f"dtc_cpt_run_{ts}")
    ensure_dir(outdir)
    log_path = outdir / "run_log.jsonl"

    # Single conversation context across steps
    messages: List[Dict[str, str]] = [
        {
            "role": "system",
            "content": (
                "You are a precise, structured digital twin analyst and technical writer. "
                "Follow instructions exactly. Use concise, actionable language. "
                "When asked for tables, provide tables. When asked for HTML, provide a complete HTML document."
            ),
        }
    ]
    # ---- Auto-inject shared CPT context from ./cpt.md (same folder as this script)
    script_dir = Path(__file__).resolve().parent
    cpt_md_path = script_dir / "cpt.md"
    if cpt_md_path.exists():
        cpt_context = cpt_md_path.read_text(encoding="utf-8").strip()
        if cpt_context:
            messages.append(
                {
                    "role": "system",
                    "content": (
                        "Additional reference context for the DTC CPT workflow. "
                        "Use this throughout all steps (0–4). "
                        "If it conflicts with the step prompts, follow the step prompts.\n\n"
                        "----- BEGIN CPT CONTEXT (cpt.md) -----\n"
                        f"{cpt_context}\n"
                        "----- END CPT CONTEXT (cpt.md) -----"
                    ),
                }
            )
            print(f"Injected CPT context from: {cpt_md_path}")
        else:
            print(f"Found {cpt_md_path} but it was empty; no context injected.")
    else:
        print(f"No cpt.md found at {cpt_md_path}; continuing without extra context.")

    # ---- Step 0
    step0_filled = STEP0_PROMPT.replace("[Blank]", sector) + "\n\n" + fmt + artifacts_hint
    out0 = run_step(
        base_url=args.base_url,
        model=args.model,
        messages=messages,
        user_prompt=step0_filled,
        timeout=args.timeout,
        max_tokens=1200,
        temperature=0.2,
    )

    write_text(outdir / "step0_use_case_suitability.md", out0)

    append_jsonl(
        log_path,
        {
            "step": 0,
            "time_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "prompt": step0_filled,
            "output_path": "step0_use_case_suitability.md",
        },
)


    # ---- Step 1
    step1_filled = STEP1_PROMPT.replace("[Blank]", problem_statement) + "\n\n" + fmt + artifacts_hint
    out1 = run_step(
        base_url=args.base_url,
        model=args.model,
        messages=messages,
        user_prompt=step1_filled,
        timeout=args.timeout,
        max_tokens=2500,
        temperature=0.2,
)
    write_text(outdir / "step1_business_requirements.md", out1)
    append_jsonl(
    log_path,
    {
        "step": 1,
        "time_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "prompt": step1_filled,
        "output_path": "step1_business_requirements.md",
    },
)

    # ---- Step 2
    step2_full = STEP2_PROMPT + "\n\n" + fmt + artifacts_hint
    out2 = run_step(
        base_url=args.base_url,
        model=args.model,
        messages=messages,
        user_prompt=step2_full,
        timeout=args.timeout,
        max_tokens=2500,
        temperature=0.2,
    )
    write_text(outdir / "step2_capability_selector.md", out2)
    append_jsonl(
    log_path,
    {
        "step": 2,
        "time_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "prompt": step2_full,
        "output_path": "step2_capability_selector.md",
    },
)
    # ---- Step 3
    step3_outputs = []
    if step3_mode in {"1", "b"}:
        step3p1 = STEP3_PART1_PROMPT + "\n\n" + fmt + artifacts_hint
        out3a = run_step(
            base_url=args.base_url,
            model=args.model,
            messages=messages,
            user_prompt=step3p1,
            timeout=args.timeout,
            max_tokens=2200,
            temperature=0.2,
        )
        step3_outputs.append(("part1", out3a))
    if step3_mode in {"2", "b"}:
        step3p2 = STEP3_PART2_PROMPT + "\n\n" + fmt + artifacts_hint
        out3b = run_step(
            base_url=args.base_url,
            model=args.model,
            messages=messages,
            user_prompt=step3p2,
            timeout=args.timeout,
            max_tokens=2600,
            temperature=0.2,
        )
        step3_outputs.append(("part2", out3b))

    combined = []
    for label, text in step3_outputs:
        combined.append(f"# Step 3 ({label})\n\n{text}\n")
    out3 = "\n\n---\n\n".join(combined) if combined else "(No Step 3 output produced.)"
    write_text(outdir / "step3_capability_deep_dives.md", out3)
    append_jsonl(
    log_path,
    {
        "step": 3,
        "time_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "mode": step3_mode,
        "output_path": "step3_capability_deep_dives.md",
    },
)

    # ---- Step 4
    step4_full = STEP4_PROMPT + "\n\nReturn ONLY the HTML (preferably in a single ```html fenced block)."
    out4 = run_step(
        base_url=args.base_url,
        model=args.model,
        messages=messages,
        user_prompt=step4_full,
        timeout=args.timeout,
        max_tokens=10000,
        temperature=0.2,
    )
    html = extract_html(out4)
    write_text(outdir / "step4_cpt_table.html", html)
    append_jsonl(
    log_path,
    {
        "step": 4,
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
    print(f" - {outdir / 'step4_cpt_table.html'}")
    print(f" - {outdir / 'run_log.jsonl'}")


if __name__ == "__main__":
    main()
