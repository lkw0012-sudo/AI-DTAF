# 4R Pre-Build Target Assessment

This is a planning assessment for a digital twin before it is built. It distinguishes the recommended pre-build 4R target from the current evidence baseline, so the workflow can keep the intended build target while still showing which evidence is already explicit and which evidence is still missing.

## Recommended Target Level
- Recommended target level: **R1** (Representation)
- Target support status: **partial**
- Current evidence baseline: **R1** (Representation)
- Evidence baseline status: **partial**
- Target confidence: **low**
- Explanation: The recommended pre-build 4R target for this use case is R1 (Representation). The next level beyond the current recommendation is R2 (Replication) once the remaining evidence and implementation gaps are closed.
- Near-term next target beyond the recommendation: **R2** (Replication)

## Planning Summary
The recommended build target is R1. The current evidence baseline is R1. The digital twin will provide real-time insights into Quality, Cost, and Time before production begins by determining the capability and capacity to run a given job, optimizing scheduling based on available equipment, and automating key decision-making processes. The current feasible capabilities support R1 (Representation) but need more detailed planning for R2.

## Desired Future Vision vs. Current Feasible Target
The recommended pre-build target is R1. The next level beyond that is R2. Future work beyond the recommendation should stay clearly separated from the current build boundary.

## Feasible capabilities used
| Capability | Priority | Readiness |
|---|---:|---:|
| DS.AI - Data Acquisition & Ingestion | E | 1.00 |
| IR.ET - Enterprise System Integration | E | 1.00 |
| IC.SR - Search | E | 1.00 |
| UX.BV - Basic Visualization | E | 1.00 |
| DS.ST - Data Streaming | E | 1.00 |
| IR.EG - Eng. System Integration | E | 1.00 |
| IC.AI - Artificial Intelligence | E | 1.00 |
| DS.TR - Data Transformation | E | 1.00 |
| IR.IO - OT/IoT System Integration | E | 1.00 |
| IC.OS - Orchestration | E | 1.00 |
| UX.RM - Real-time Monitoring | E | 1.00 |
| DS.BP - Batch Processing | E | 1.00 |
| DS.RT - Real-time Processing | E | 1.00 |
| DS.AS - Asynchronous Integration | E | 1.00 |
| MG.DM - Device Management | E | 1.00 |
| TW.SC - Security | E | 1.00 |
| MG.SM - System Monitoring | E | 1.00 |

## 4R Level Support Status
| 4R Level | Supported as Build Target | Evidence Strength | Main Reason | Key Gaps |
|---|---|---|---|---|
| R1 | Partial | partial | The digital twin purpose is defined, but the detailed system boundaries, components, and data collection processes are not explicitly outlined. | The digital twin purpose, scope, and supported decisions are explicitly defined.; System boundaries, major components, inputs/outputs, and important states are identified.; Critical variables are selected without major over-instrumentation or missing context. |
| R2 | No | weak | The planned digital twin will replicate the CNC machining systems in a virtual environment to produce similar outputs given the same inputs. | None |
| R3 | No | weak | The planned digital twin will run independently of the physical system, predict behavior for scenarios not directly observed, and provide actionable insights. | R2 is already satisfied.; Prediction targets, decision variables, and objective functions are defined.; The DT can run without continuous live dependency on the physical system. |
| R4 | No | weak | The planned digital twin will utilize AI to make autonomous decisions, detect anomalies, and take corrective actions. | R3 is already satisfied.; Autonomy scope, human-in-the-loop boundaries, and override conditions are defined.; The DT can detect anomalies or changing conditions in real time. |

## Revised Gate Criteria Assessment
| 4R Level | Gate Criterion | Score | Evidence | Rationale | Needed Improvement |
|---|---|---:|---|---|---|
| R1 | The digital twin purpose, scope, and supported decisions are explicitly defined. | 0 | No explicit evidence of defining the DT purpose or scope. | The use case statement is implied but not clearly defined. \| evidence found in prior outputs; aligned feasible capabilities: UX.BV | Add explicit evidence, data, or design detail before claiming support. |
| R1 | System boundaries, major components, inputs/outputs, and important states are identified. | 1 | System boundaries and components are identified in Step 1 output. | Partial evidence from Step 1 output. \| evidence found in prior outputs; aligned feasible capabilities: IR.EG, IR.IO | Strengthen with direct, use-case-specific evidence and a reviewable deliverable. |
| R1 | Critical variables are selected without major over-instrumentation or missing context. | 0 | No explicit data collection pipeline or storage strategy mentioned. | Data collection details are implied but not clearly defined. \| evidence found in prior outputs; aligned feasible capabilities: DS.AI, DS.TR, UX.RM | Add explicit evidence, data, or design detail before claiming support. |
| R1 | A repeatable data collection and storage pipeline exists. | 1 | No structured data schema or validation process described. | Data structure and validation processes are implied but not explicitly outlined. \| evidence found in prior outputs; aligned feasible capabilities: DS.AI, IR.ET, DS.ST, IR.EG | Strengthen with direct, use-case-specific evidence and a reviewable deliverable. |
| R1 | Collected data is structured, usable, and verified against known system behavior. | 1 | Some evidence of defining the DT purpose in Step 1 output. | Partial evidence from Step 1 output. \| evidence found in prior outputs; aligned feasible capabilities: DS.TR | Strengthen with direct, use-case-specific evidence and a reviewable deliverable. |
| R2 | R1 is already satisfied. | 2 | The digital twin purpose is defined and supported by feasible capabilities. | Clear evidence from Step 1 output. | None |
| R2 | Replication targets, required outputs, and acceptable error thresholds are defined. | 2 | Integration with existing enterprise systems (ERP, EAM) is planned. | Clear evidence from Step 1 output. | None |
| R2 | A modeling platform has been selected and the system has been mapped into a digital architecture. | 2 | Real-time data acquisition and streaming are feasible capabilities. | Clear evidence from Step 3 output. | None |
| R2 | Live or recorded data can drive model inputs and updates. | 2 | Basic visualization is planned for operations managers. | Clear evidence from Step 1 output. | None |
| R2 | The model has been tested against real behavior and verified to reproduce outputs with acceptable deviation. | 2 | Real-time monitoring of machine health and tool usage is feasible capabilities. | Clear evidence from Step 3 output. | None |
| R3 | R2 is already satisfied. | 0 | No explicit evidence of defining prediction targets or acceptable error thresholds. | The planning does not include detailed predictive models or validation steps. | Add explicit evidence, data, or design detail before claiming support. |
| R3 | Prediction targets, decision variables, and objective functions are defined. | 1 | Artificial intelligence is planned for real-time decision-making. | Partial evidence from Step 3 output. \| evidence found in prior outputs; aligned feasible capabilities: IC.AI | Strengthen with direct, use-case-specific evidence and a reviewable deliverable. |
| R3 | The DT can run without continuous live dependency on the physical system. | 0 | No explicit evidence of running the DT independently without continuous live dependency on physical systems. | The planning does not include detailed validation steps or independent execution capability. \| evidence found in prior outputs; aligned feasible capabilities: DS.BP, DS.AS | Add explicit evidence, data, or design detail before claiming support. |
| R3 | Predictive or scenario-exploration models are implemented. | 1 | Real-time monitoring is planned for machine health and tool usage. | Partial evidence from Step 3 output. \| evidence found in prior outputs; aligned feasible capabilities: IC.AI | Strengthen with direct, use-case-specific evidence and a reviewable deliverable. |
| R3 | The DT can evaluate what-if conditions and provide actionable recommendations or optimized results. | 0 | No explicit evidence of providing actionable insights or recommendations. | The planning does not include detailed decision-making processes or outputs. \| evidence found in prior outputs; aligned feasible capabilities: IC.OS | Add explicit evidence, data, or design detail before claiming support. |
| R4 | R3 is already satisfied. | 0 | No explicit evidence of defining autonomy scope or human-in-the-loop boundaries. | The planning does not include detailed autonomous decision-making processes. | Add explicit evidence, data, or design detail before claiming support. |
| R4 | Autonomy scope, human-in-the-loop boundaries, and override conditions are defined. | 1 | Artificial intelligence is planned for real-time decision-making. | Partial evidence from Step 3 output. \| evidence found in prior outputs; aligned feasible capabilities: IC.OS, TW.SC | Strengthen with direct, use-case-specific evidence and a reviewable deliverable. |
| R4 | The DT can detect anomalies or changing conditions in real time. | 0 | No explicit evidence of detecting anomalies or taking corrective actions in real time. | The planning does not include detailed anomaly detection or response strategies. \| evidence found in prior outputs; aligned feasible capabilities: IC.AI, UX.RM, MG.SM | Add explicit evidence, data, or design detail before claiming support. |
| R4 | The DT can choose among actions based on learned or adaptive logic. | 1 | Real-time monitoring is planned for machine health and tool usage. | Partial evidence from Step 3 output. \| evidence found in prior outputs; aligned feasible capabilities: IC.AI | Strengthen with direct, use-case-specific evidence and a reviewable deliverable. |
| R4 | Past outcomes are stored and used to improve future decisions. | 0 | No explicit evidence of making autonomous decisions with acceptable trust and safety controls. | The planning does not include detailed decision-making processes or outputs. \| evidence found in prior outputs; aligned feasible capabilities: IC.AI | Add explicit evidence, data, or design detail before claiming support. |
| R4 | The DT can make or execute decisions with acceptable trust and safety controls. | 2 | [step0] Lack of robust security measures for sensitive data. | evidence found in prior outputs; aligned feasible capabilities: TW.SC | None |

## Tailored 4R Action Items
| 4R Level | Action Item | What to Do | Why It Matters | Use-Case-Specific Example | Required Data or Inputs | Expected Output or Evidence | Dependencies or Gaps |
|---|---|---|---|---|---|---|---|
| R1 | Define the digital twin's purpose, scope, and expected outcomes. | Write a detailed statement defining the DT purpose, target decisions, and expected outcomes. This will help in aligning all stakeholders on the goals of the project. | A clear definition is crucial for guiding the development process and ensuring that the digital twin meets the business requirements. | The digital twin aims to determine whether we have the capability and capacity to run a given job, optimize scheduling based on available equipment, and automate key decision-making processes currently relying on manual judgment. | Business requirements specification; Stakeholder interviews | A one-paragraph statement defining the DT purpose, target decisions, and expected outcomes. | Lack of clear business requirements and stakeholder alignment. |
| R1 | Document system boundaries, included/excluded components, and key interactions. | Create a detailed document outlining the system boundaries, including/excluding components, and key interactions. This will help in defining the scope of the digital twin. | A well-defined system boundary is essential for ensuring that all relevant aspects are considered during development. | The CNC machining systems include multiple machines across different locations, with specific components such as cutting tools, spindles, and coolant. The boundaries will exclude internal motor details but include environmental conditions affecting machine performance. | System architecture diagrams; Component lists | A document detailing the system boundaries, included/excluded components, and key interactions. | Lack of detailed component lists and system architecture diagrams. |
| R1 | Identify critical variables for data collection without over-instrumentation or missing context. | Identify the key properties, characteristics, and states that are essential for the digital twin. Ensure that the selected variables are neither overly complex nor insufficient to provide meaningful insights. | Selecting appropriate critical variables is crucial for ensuring that the data collected is relevant and useful for analysis and modeling. | For this CNC machining use case, apply this step to variables and records such as spindle speed, feed rate, spindle load, vibration, tool id, machine state. | Historical data; Technical specifications | A list of critical variables identified for the digital twin. | Lack of historical data and technical specifications. |
| R1 | Design a repeatable data collection strategy. | Define the sensors, APIs, or software sources needed for data acquisition and specify their placement. Determine the communication protocols and synchronization requirements. | A structured data collection strategy ensures that the digital twin can reliably collect relevant data from various sources. | For this CNC machining use case, apply this step to variables and records such as spindle speed, feed rate, spindle load, vibration, tool id, machine state. | Sensor specifications; Communication protocols | A detailed data collection strategy document. | Lack of sensor specifications and communication protocol details. |
| R1 | Develop an initial data representation layer. | Collect the data from the physical system, structure it, remove errors, and organize into a usable format. Verify and validate the data against known system outputs. | A well-structured and validated data representation is essential for ensuring that the digital twin can provide accurate insights. | For this CNC machining use case, apply this step to variables and records such as spindle speed, feed rate, spindle load, vibration, tool id, machine state. | Collected sensor data; Known system outputs | A structured and validated dataset ready for analysis and modeling. | Lack of collected sensor data and known system outputs. |

## Priority Action List
1. Define the digital twin's purpose, scope, and expected outcomes.
2. Document system boundaries, included/excluded components, and key interactions.
3. Identify critical variables for data collection without over-instrumentation or missing context.
4. Design a repeatable data collection strategy.
5. Develop an initial data representation layer.

## Missing Information or Data Gaps
- Lack of clear business requirements and stakeholder alignment.
- Lack of detailed component lists and system architecture diagrams.
- Lack of historical data and technical specifications.
- Lack of sensor specifications and communication protocol details.
- Lack of collected sensor data and known system outputs.

## Future Work Beyond Current 4R Level
- Advance from R1 to R2 by closing the remaining evidence and implementation gaps for the next level.
- Define the replication targets and acceptable error thresholds.
- Select a modeling environment and map physical components to digital counterparts.
- Implement real-time monitoring and validation workflows.
