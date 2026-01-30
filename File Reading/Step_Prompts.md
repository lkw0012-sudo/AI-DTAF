# Step by Step Prompts for Claude Sonnet 4

## Step 0: Use Case Suitability

Prompt:

Analyze the following Manufacturing sector and identify the most common challenges and key problems across major business areas such as operations, demand forecasting, technology integration, customer engagement, and regulatory compliance. For each area, list the typical issues organizations face, explain their root causes, and describe their impact on business performance. Where relevant, highlight recent trends or disruptions that have intensified these challenges. Structure your response by business area, and provide concise, actionable insights that could inform strategic decision-making.

## Step 1: Digital Twin Business Requirements Generator

	

	Prompt:

	Instructions

Please provide a comprehensive business requirements specification for a digital twin solution based on the problem statement below. Structure your response to include all relevant contextual information that would help identify required capabilities from the Digital Twin Capabilities Periodic Table.

Problem Statement

We need a digital twin of our CNC machining systems to provide accurate, data-driven insight into Quality, Cost, and Time before production begins. The digital twin must determine whether we have the capability and capacity to run a given job, optimize scheduling based on available equipment, and automate key decision-making processes that currently rely on manual judgment. It should continuously monitor degradation of cutting tools, spindles, and coolant, predict remaining useful life, and assess how component wear will impact part quality and throughput. By integrating real-time machine data with predictive simulation, the digital twin will enable proactive maintenance, reduce cycle time, extend asset life, and ensure that every job is run on the right machine, at the right time, with predictable and efficient performance.

Generate a detailed response that includes:

1\. Business Context

* Industry sector and specific domain (e.g., manufacturing, energy, healthcare)  
* Scale of operations (number of assets, locations, etc.)  
* Current operational environment and key constraints  
* Primary stakeholders and their roles in a table  
  2\. Problem Analysis  
* Root causes of the current challenges  
* Quantifiable business impact of the problem (financial, operational, safety, etc.)  
* Current approaches and their limitations in a table  
* Critical decision points affected by this problem  
  3\. Digital Twin Objectives  
* Primary business goals for the digital twin solution  
* Key performance indicators (KPIs) to measure success in a table  
* Required timeframe for implementation and value realization  
* Strategic alignment with broader organizational initiatives  
  4\. Operational Requirements  
* Real-time vs. batch processing needs  
* Data update frequency requirements  
* Decision-making processes to be supported  
* Integration with existing systems and workflows  
* Level of automation desired  
  5\. Data Requirements  
* Types of data needed (operational, historical, contextual, etc.)  
* Data sources available (sensors, enterprise systems, etc.)  
* Data quality and completeness assessment  
* Data volume, velocity, and variety considerations  
* Any special requirements around data governance or compliance  
  6\. User Experience Requirements  
* Primary users and their roles  
* Visualization and interaction needs  
* Alert and notification requirements  
* Collaboration and knowledge sharing aspects  
* Mobile/remote access requirements  
  7\. Technical Considerations  
* Existing technology infrastructure  
* Deployment environment preferences (edge, cloud, hybrid)  
* Security and compliance requirements  
* Scalability needs for future expansion  
* Performance expectations  
  8\. Implementation Approach  
* Phasing and prioritization recommendations  
* Key risks and mitigations  
* Success criteria  
* Organizational readiness considerations  
  Your specification should be detailed enough to serve as a foundation for identifying the specific capabilities needed from the Digital Twin Capabilities Periodic Table in a subsequent analysis.  
  Please use Claude artifacts.


## Step 2: Digital Twin Capability Selector

Prompt:  
Instructions

Based on the detailed business requirements specification from the previous step, please identify and justify the specific capabilities from the Digital Twin Capabilities Periodic Table that would be required to support this digital twin use case.

Analysis Tasks

1\. Capability Mapping

For each of the six capability categories in the Digital Twin Capabilities Periodic Table, identify which specific capabilities would be required for this use case and present the results in a table:

Data Services (DS)

* List and explain required capabilities (e.g., DS.AI, DS.ST, DS.TR, etc.)  
* Justify each selection based on the business requirements  
* Note deployment considerations (edge, fog, cloud) for each capability  
  Integration (IR)  
* List and explain required capabilities (e.g., IR.ET, IR.EG, IR.IO, etc.)  
* Justify each selection based on the business requirements  
* Identify key systems that would need integration  
  Intelligence (IC)  
* List and explain required capabilities (e.g., IC.SR, IC.PR, IC.AI, etc.)  
* Justify each selection based on the business requirements  
* Highlight critical intelligence capabilities for business value  
  User Experience (UX)  
* List and explain required capabilities (e.g., UX.BV, UX.AV, UX.RM, etc.)  
* Justify each selection based on the business requirements  
* Consider different user roles and their needs  
  Management (MG)  
* List and explain required capabilities (e.g., MG.DM, MG.SM, MG.EL, etc.)  
* Justify each selection based on the business requirements  
* Consider operational governance needs  
  Trustworthiness (TW)  
* List and explain required capabilities (e.g., TW.SC, TW.PR, TW.SF, etc.)  
* Justify each selection based on the business requirements  
* Highlight critical security or compliance considerations  
  2\. Capability Priority Assessment  
* Classify each identified capability as:  
  * Essential (must have for minimum viable solution)  
  * High Value (important for full business value)  
  * Future Enhancement (beneficial for long-term evolution)

  3\. Digital Twin Capability Periodic Table Visualization

* Create a simple text-based table showing the selected capabilities from the Digital Twin Capabilities Periodic Table  
* For each selected capability, indicate its priority level (Essential, High Value, or Future Enhancement) using the notation: \[E\], \[H\], or \[F\]  
* Use a format like DS.AI \[E\] to indicate the capability ID and its priority level  
  4\. Implementation Considerations  
* Identify any capability gaps or challenges in implementing the required capabilities  
* Recommend potential phasing approach for capability implementation  
* Note any specialized expertise needed for specific capabilities  
  Your analysis should provide a clear roadmap of which Digital Twin Capabilities would be required to successfully implement the solution described in the business requirements.  
  Please use Claude artifacts.

## Step 3: Capability Deep Dives

Prompt:

### \# Part 1

\`\`\`prompt

Instructions: Based on the capability analysis from the previous step, please provide a deeper examination of the most critical capabilities identified for this digital twin use case.

Capability Deep Dives

\- For the most critical 3-5 capabilities identified in your previous analysis, provide a deeper analysis of:

    \- Specific requirements for this use case

    \- Success criteria for this capability

    \- Recommended technology approaches

    \- Potential challenges in implementation

Please use the results of your previous capability mapping and prioritization to determine which capabilities warrant this deeper analysis.

Please use Claude artifacts

\`\`\`

### \# Part 2

\`\`\`prompt

Instructions: Based on the capability analysis from the previous step, please provide a deeper examination of:

(1) the most critical capabilities identified for this digital twin use case, and 

(2) all Trustworthiness (TW) capabilities regardless of their priority level.

Capability Deep Dives

\- For the most critical 3-5 capabilities identified in your previous analysis, plus ALL Trustworthiness (TW) capabilities, provide a deeper analysis of:

    \- Specific requirements for this use case

    \- Success criteria for this capability

    \- Recommended technology approaches

    \- Potential challenges in implementation

Please organize your response with the critical capabilities first, followed by a complete analysis of all Trustworthiness capabilities. For each capability, create a structured deep dive that addresses all four analysis points.

Please use the results of your previous capability mapping and prioritization to determine which non-Trustworthiness capabilities warrant deeper analysis, while ensuring all Trustworthiness capabilities receive detailed examination regardless of their priority level.

Please use Claude artifacts.

## Step 4: CPT Table Generator

	Prompt:

	

\# Notes 

\*\*⚠️ IMPORTANT\*\*: This prompt should preferably be run from a project/conversation that contains the complete DT CPT framework artifacts for best results.

\#\# What You'll Get

After sending this prompt to any AI assistant, you'll receive:

✅ \*\*Complete HTML file\*\* \- Ready to save and use  

✅ \*\*Professional appearance\*\* \- Enterprise-quality design matching DTC standards  

✅ \*\*All 60+ capabilities\*\* \- Complete Digital Twin framework coverage  

✅ \*\*Category organization\*\* \- Logical grouping by capability type  

✅ \*\*Responsive design\*\* \- Works on desktop and mobile  

✅ \*\*Self-contained\*\* \- No external dependencies


\#\# Compatible AI Assistants

This prompt works with:

\- \*\*Claude\*\* (Anthropic)

\- \*\*ChatGPT\*\* (OpenAI)

\- \*\*Gemini\*\* (Google)

\- \*\*Llama\*\* (Meta/Various providers)

\- \*\*Other LLMs\*\* with code generation capabilities

\#\# How to Use the Output

1\. \*\*Copy the HTML\*\* \- The AI will provide complete HTML code

2\. \*\*Save as file\*\* \- Save with \`.html\` extension (e.g., \`digital-twin-cpt.html\`)

3\. \*\*Open in browser\*\* \- Double-click to view

4\. \*\*Share freely\*\* \- Works offline, no internet required

\#\# Perfect For

\- \*\*Digital Twin projects\*\* \- Reference during requirements gathering

\- \*\*Stakeholder presentations\*\* \- Visual framework communication

\- \*\*Training materials\*\* \- Educational resources for teams

\- \*\*Documentation\*\* \- Include in project specifications

\- \*\*Vendor evaluations\*\* \- Capability gap analysis

\#\# Key Features

\- \*\*Complete Framework\*\* \- All 60+ capabilities from DTC CPT v1.2

\- \*\*Category Colors\*\* \- Official Digital Twin Consortium color scheme

\- \*\*Professional Layout\*\* \- Enterprise-ready presentation quality

\- \*\*Mobile Responsive\*\* \- Adapts to different screen sizes

\- \*\*Hover Effects\*\* \- Interactive visual feedback

\- \*\*Comprehensive Legend\*\* \- Category explanations and descriptions

\#\# Troubleshooting

If the AI doesn't generate exactly what you need:

\- Try the prompt again (sometimes results vary)

\- Ask for specific corrections (e.g., "fix the DS category colors" or "adjust the mobile layout")

\- Request modifications (e.g., "make the capability blocks larger" or "add more spacing")

\- Ask for specific capability corrections if any are missing or incorrect

This generates the clean, static base periodic table that shows the complete Digital Twin capability framework in a professional format that works across all major AI assistants and aligns with the Digital Twin Consortium's official documentation.

\---

\# Prompt 

\#suggested-llm Anthropic \- Claude

\`\`\`prompt

You are an expert web developer. Generate a complete, self-contained HTML file for the Digital Twin Capabilities Periodic Table v1.2 as a clean, static display showing all 60+ capabilities. The output should include embedded CSS and JavaScript with no external dependencies.

\#\# REQUIREMENTS:

\#\#\# Visual Standards:

\- Use the complete 60+ capability framework with proper positioning

\- Apply these category colors exactly:

  \- DS (Data Services): background \#D1DCEA, border \#7A9BC4, text \#13386D

  \- IR (Integration): background \#FAEAD5, border \#D4A571, text \#945911  

  \- IC (Intelligence & Cognition): background \#E3DDEC, border \#A18DB5, text \#4E3D6F

  \- UX (User Experience): background \#EEEEEE, border \#999999, text \#404040

  \- MG (Management): background \#D5E3E1, border \#7FA596, text \#295548

  \- TW (Trustworthiness): background \#EDD9D5, border \#C78275, text \#792D21

\#\#\# Layout Requirements:

\- Display all capabilities at full opacity (no fading or hiding)

\- Use CSS Grid with exactly 8 columns and 8 rows

\- Follow the exact grid positioning specified below (true periodic table format)

\- Include proper capability positioning as specified below

\- Add legend showing all 6 categories with color samples

\- Make responsive for mobile devices (stack to 4 columns on mobile, maintaining relative positioning)

\- Include smooth CSS transitions for hover effects

\- Minimum height of 80px per capability block

\#\#\# Content Requirements:

\- Page title: "Digital Twin Capabilities Periodic Table v1.2"

\- Subtitle: "Complete Framework of 60+ Core Capabilities"

\- No interactive buttons or controls (static display only)

\- Include all capability blocks with correct IDs and names

\- Professional typography using system fonts

\- Clean spacing and modern design

\- Center the content on the page

\#\#\# CRITICAL \- Exact Grid Positioning:

Use these exact positions for each capability in an 8x8 grid:

\*\*Row 1:\*\*

\- Row 1, Col 1: DS.AI "Data Acquisition & Ingestion"

\- Row 1, Col 2: DS.SG "Synthetic Data Generation" 

\- Row 1, Col 3: IR.ET "Enterprise System Integration"

\- Row 1, Col 4: IC.SR "Search"

\- Row 1, Col 5: IC.PR "Prediction"

\- Row 1, Col 6: UX.BV "Basic Visualization"

\- Row 1, Col 7: UX.DB "Dashboards"

\*\*Row 2:\*\*

\- Row 2, Col 1: DS.ST "Data Streaming"

\- Row 2, Col 2: DS.ON "Ontology Management"

\- Row 2, Col 3: IR.EG "Eng. System Integration"

\- Row 2, Col 4: IC.CC "Command & Control"

\- Row 2, Col 5: IC.AI "Artificial Intelligence"

\- Row 2, Col 6: UX.AV "Advanced Visualization"

\- Row 2, Col 7: UX.CI "Continuous Intelligence"

\*\*Row 3:\*\*

\- Row 3, Col 1: DS.TR "Data Transformation"

\- Row 3, Col 2: DS.RP "Digital Twin (DT) Model Repository"

\- Row 3, Col 3: IR.IO "OT/IoT System Integration"

\- Row 3, Col 4: IC.OS "Orchestration"

\- Row 3, Col 5: IC.PS "Prescriptive Recommendations"

\- Row 3, Col 6: UX.RM "Real-time Monitoring"

\- Row 3, Col 7: UX.BI "Business Intelligence"

\*\*Row 4:\*\*

\- Row 4, Col 1: DS.CX "Data Contextualization"

\- Row 4, Col 2: DS.IR "DT Instance Repository"

\- Row 4, Col 3: IR.DT "Digital Twin Integration"

\- Row 4, Col 4: IC.AL "Alerts & Notifications"

\- Row 4, Col 5: IC.FL "Federated Learning"

\- Row 4, Col 6: IC.BR "Business Rules"

\- Row 4, Col 7: UX.ER "Entity Relationship Visualization"

\- Row 4, Col 8: UX.BP "BPM & Workflow"

\*\*Row 5:\*\*

\- Row 5, Col 1: DS.BP "Batch Processing"

\- Row 5, Col 2: DS.DS "Domain Specific Data Management"

\- Row 5, Col 3: IR.CL "Collab Platform Integration"

\- Row 5, Col 4: IC.RP "Reporting"

\- Row 5, Col 5: IC.SM "Simulation"

\- Row 5, Col 6: IC.DL "Distributed Ledger & Smart Contracts"

\- Row 5, Col 7: UX.XR "Extended Reality (AV/VR/MR)"

\- Row 5, Col 8: UX.GE "Gaming Engine Visualization"

\*\*Row 6:\*\*

\- Row 6, Col 1: DS.RT "Real-time Processing"

\- Row 6, Col 2: DS.SA "Data Storage & Archive Services"

\- Row 6, Col 3: IR.AS "API Services"

\- Row 6, Col 4: IC.AA "Data Analysis & Analytics"

\- Row 6, Col 5: IC.MA "Mathematical Analytics"

\- Row 6, Col 6: IC.CS "Composition"

\- Row 6, Col 7: UX.GM "Gamification"

\- Row 6, Col 8: UX.3R "3D Rendering"

\*\*Row 7:\*\*

\- Row 7, Col 1: DS.AS "Asynchronous Integration"

\- Row 7, Col 2: DS.SR "Simulation Model Repository"

\- Row 7, Col 3: MG.DM "Device Management"

\- Row 7, Col 4: MG.EL "Event Logging"

\- Row 7, Col 5: TW.EX "Data Encryption"

\- Row 7, Col 6: TW.SC "Security"

\- Row 7, Col 7: TW.SF "Safety"

\- Row 7, Col 8: TW.RP "Responsibility"

\*\*Row 8:\*\*

\- Row 8, Col 1: DS.AG "Data Aggregation"

\- Row 8, Col 2: DS.AR "AI Model Repository"

\- Row 8, Col 3: MG.SM "System Monitoring"

\- Row 8, Col 4: MG.DG "Data Governance"

\- Row 8, Col 5: TW.DS "Device Security"

\- Row 8, Col 6: TW.PR "Privacy"

\- Row 8, Col 7: TW.RL "Reliability"

\- Row 8, Col 8: TW.RS "Resilience"

\#\#\# Technical Requirements:

\- Single HTML file with embedded CSS and JavaScript

\- Use CSS Grid with exactly 8 columns and 8 rows for the main periodic table

\- Position each capability exactly as specified in the grid coordinates above

\- No external dependencies, CDN links, or external files

\- Fast loading and responsive design

\- Works offline after download

\- Compatible with all modern browsers (Chrome, Firefox, Safari, Edge)

\- Include hover effects for better interactivity

\- Clean, modern design with proper spacing matching the official DTC layout

\- Print-friendly layout

\#\#\# Structure Requirements:

\- Use semantic HTML5 structure

\- Include proper meta tags for viewport and charset

\- Use CSS classes for styling categories

\- Add JavaScript to populate the grid dynamically from capability arrays

\- Include a comprehensive legend section at the bottom

\- Add category descriptions in the legend

\- Include version information and attribution

\#\#\# Category Descriptions for Legend:

\- DS: "Enables data access, ingestion and data management across the platform from the edge to the cloud"

\- IR: "Enables data access to existing internal and external enterprise systems and applications"  

\- IC: "Provides an environment for the development and deployment of industrial digital twin solutions"

\- UX: "Provides the user with the ability to interact with digital twins and visualize its data"

\- MG: "System and ecosystem management capabilities"

\- TW: "Security, privacy, safety, reliability and resilience capabilities"

Generate the complete HTML file code that I can copy and save as a .html file.

\`\`\`

