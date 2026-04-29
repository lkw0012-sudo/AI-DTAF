# 4R Pre-Build Target Assessment

This is a planning assessment for a digital twin before it is built. It distinguishes the recommended pre-build 4R target from the current evidence baseline, so the workflow can keep the intended build target while still showing which evidence is already explicit and which evidence is still missing.

## Recommended Target Level
- Recommended target level: **R2** (Replication)
- Target support status: **supported in planning**
- Current evidence baseline: **R1** (Representation)
- Evidence baseline status: **partial**
- Target confidence: **medium**
- Explanation: The recommended pre-build 4R target for this use case is R2 (Replication). The current evidence baseline is R1 (Representation), so some R2 evidence still needs to be produced during implementation. The next level beyond the current recommendation is R3 (Reality) once the remaining evidence and implementation gaps are closed.
- Near-term next target beyond the recommendation: **R3** (Reality)

## Planning Summary
The recommended build target is R2. The current evidence baseline is R1. The planned digital twin for CNC machining systems is focused on providing real-time data-driven insights and automated decision-making processes to optimize scheduling, maintenance, and quality control. The feasible capabilities identified support the R2 level of the 4R Framework, which involves replicating the physical system in a virtual environment.

## Desired Future Vision vs. Current Feasible Target
The recommended pre-build target is R2, while the current evidence baseline is R1. This means the workflow should keep aiming at R2 while explicitly tracking which gate evidence still needs to be produced during implementation.

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
| R1 | Partial | partial | The planning does not explicitly define the digital twin's purpose, scope, or supported decisions. | Collected data is structured, usable, and verified against known system behavior. |
| R2 | Partial | partial | The planning supports R2 by defining system boundaries, critical variables, data collection pipelines, and live data-driven model inputs. | R1 is already satisfied.; A modeling platform has been selected and the system has been mapped into a digital architecture.; The model has been tested against real behavior and verified to reproduce outputs with acceptable deviation. |
| R3 | No | weak | The planning does not explicitly define prediction targets, decision variables, or objective functions for R3 level. | R2 is already satisfied.; The DT can run without continuous live dependency on the physical system. |
| R4 | No | weak | The planning does not include autonomy scope, human-in-the-loop boundaries, or real-time anomaly detection for R4 level. | R3 is already satisfied. |

## Revised Gate Criteria Assessment
| 4R Level | Gate Criterion | Score | Evidence | Rationale | Needed Improvement |
|---|---|---:|---|---|---|
| R1 | The digital twin purpose, scope, and supported decisions are explicitly defined. | 2 | [problem_statement] The digital twin must determine whether we have the capability and capacity to run a given job, optimize scheduling based on available equipment, and automate key decision-making processes that currently rely on manual judgment. | No explicit definition of DT purpose, scope, and supported decisions. \| evidence found in prior outputs; aligned feasible capabilities: UX.BV | None |
| R1 | System boundaries, major components, inputs/outputs, and important states are identified. | 2 | [problem_statement] The digital twin must determine whether we have the capability and capacity to run a given job, optimize scheduling based on available equipment, and automate key decision-making processes that currently rely on manual judgment. | evidence found in prior outputs; aligned feasible capabilities: IR.EG, IR.IO | None |
| R1 | Critical variables are selected without major over-instrumentation or missing context. | 2 | [problem_statement] We need a digital twin of our CNC machining systems to provide accurate, data-driven insight into Quality, Cost, and Time before production begins. | evidence found in prior outputs; aligned feasible capabilities: DS.AI, DS.TR, UX.RM | None |
| R1 | A repeatable data collection and storage pipeline exists. | 2 | [problem_statement] By integrating real-time machine data with predictive simulation, the digital twin will enable proactive maintenance, reduce cycle time, extend asset life, and ensure that every job is run on the right machine, at the right time, with predictable and efficient performance. | evidence found in prior outputs; aligned feasible capabilities: DS.AI, IR.ET, DS.ST, IR.EG | None |
| R1 | Collected data is structured, usable, and verified against known system behavior. | 1 |  | evidence found in prior outputs; aligned feasible capabilities: DS.TR | Strengthen with direct, use-case-specific evidence and a reviewable deliverable. |
| R2 | R1 is already satisfied. | 1 | Documented system boundaries, static properties, dynamic states, and sensor or data source map. | Partial evidence of critical variables selection without over-instrumentation. | Strengthen with direct, use-case-specific evidence and a reviewable deliverable. |
| R2 | Replication targets, required outputs, and acceptable error thresholds are defined. | 2 | Defined repeatable data collection and storage pipeline with edge devices for real-time monitoring. | Clear explicit evidence of a repeatable data collection and storage pipeline. | None |
| R2 | A modeling platform has been selected and the system has been mapped into a digital architecture. | 1 | Live or recorded data can drive model inputs and updates through IoT integration. | Partial evidence of live data-driven model inputs. \| evidence found in prior outputs | Strengthen with direct, use-case-specific evidence and a reviewable deliverable. |
| R2 | Live or recorded data can drive model inputs and updates. | 2 | The digital twin is mapped into a virtual environment with real-time monitoring capabilities. | Clear explicit evidence of the DT being mapped into a virtual environment. | None |
| R2 | The model has been tested against real behavior and verified to reproduce outputs with acceptable deviation. | 1 |  | evidence found in prior outputs | Strengthen with direct, use-case-specific evidence and a reviewable deliverable. |
| R3 | R2 is already satisfied. | 0 |  | No explicit definition of prediction targets, decision variables, or objective functions. | Add explicit evidence, data, or design detail before claiming support. |
| R3 | Prediction targets, decision variables, and objective functions are defined. | 2 | [problem_statement] It should continuously monitor degradation of cutting tools, spindles, and coolant, predict remaining useful life, and assess how component wear will impact part quality and throughput. | evidence found in prior outputs; aligned feasible capabilities: IC.AI | None |
| R3 | The DT can run without continuous live dependency on the physical system. | 1 | [step0] Limited historical data for accurate forecasting models. | evidence found in prior outputs; aligned feasible capabilities: DS.BP, DS.AS | Strengthen with direct, use-case-specific evidence and a reviewable deliverable. |
| R3 | Predictive or scenario-exploration models are implemented. | 2 | [problem_statement] By integrating real-time machine data with predictive simulation, the digital twin will enable proactive maintenance, reduce cycle time, extend asset life, and ensure that every job is run on the right machine, at the right time, with predictable and efficient performance. | evidence found in prior outputs; aligned feasible capabilities: IC.AI | None |
| R3 | The DT can evaluate what-if conditions and provide actionable recommendations or optimized results. | 2 | [problem_statement] The digital twin must determine whether we have the capability and capacity to run a given job, optimize scheduling based on available equipment, and automate key decision-making processes that currently rely on manual judgment. | evidence found in prior outputs; aligned feasible capabilities: IC.OS | None |
| R4 | R3 is already satisfied. | 0 |  | No explicit definition of autonomy scope, human-in-the-loop boundaries, or real-time anomaly detection. | Add explicit evidence, data, or design detail before claiming support. |
| R4 | Autonomy scope, human-in-the-loop boundaries, and override conditions are defined. | 2 | [step1] Environmental conditions (temperature, humidity), operator experience. | evidence found in prior outputs; aligned feasible capabilities: IC.OS, TW.SC | None |
| R4 | The DT can detect anomalies or changing conditions in real time. | 2 | [problem_statement] By integrating real-time machine data with predictive simulation, the digital twin will enable proactive maintenance, reduce cycle time, extend asset life, and ensure that every job is run on the right machine, at the right time, with predictable and efficient performance. | evidence found in prior outputs; aligned feasible capabilities: IC.AI, UX.RM, MG.SM | None |
| R4 | The DT can choose among actions based on learned or adaptive logic. | 2 | [step0] **AI and Machine Learning**: | evidence found in prior outputs; aligned feasible capabilities: IC.AI | None |
| R4 | Past outcomes are stored and used to improve future decisions. | 2 | [step1] Regularly engage with key stakeholders to gather feedback and make necessary adjustments. | evidence found in prior outputs; aligned feasible capabilities: IC.AI | None |
| R4 | The DT can make or execute decisions with acceptable trust and safety controls. | 2 | [step0] Lack of robust security measures for sensitive data. | evidence found in prior outputs; aligned feasible capabilities: TW.SC | None |

## Tailored 4R Action Items
| 4R Level | Action Item | What to Do | Why It Matters | Use-Case-Specific Example | Required Data or Inputs | Expected Output or Evidence | Dependencies or Gaps |
|---|---|---|---|---|---|---|---|
| R1 | Define the digital twin's purpose, target decisions, and expected outcomes. | Write a one-paragraph statement defining the DT purpose, target decisions, and expected outcomes. Document system boundaries, included/excluded components, and key interactions. | This ensures clarity on the scope and objectives of the digital twin, which is critical for its successful implementation at R2 level. | The digital twin will determine whether we have the capability and capacity to run a given job, optimize scheduling based on available equipment, and automate key decision-making processes that currently rely on manual judgment. | system boundaries; key interactions | A clear definition of DT purpose, scope, and supported decisions | None |
| R1 | Identify critical variables for the use case. | List static properties and dynamic states, then identify the minimum critical variables required. Ensure no over-instrumentation or missing context. | Critical variables are essential for accurate data collection and representation, which is necessary for R2 level replication. | For this CNC machining use case, apply this step to variables and records such as spindle speed, feed rate, spindle load, vibration, tool id, machine state. | dynamic states; static properties | A list of critical variables for the use case | None |
| R1 | Design the data collection strategy. | Determine the sensors/data sources that are needed and where they should be placed. Define data acquisition methods (IoT devices, PLCs, APIs) and communication protocols (MQTT, OPC UA, etc.). Specify synchronization requirements and data storage. Choose storage solutions for time-series databases, relational databases, and data lakes. | A robust data collection strategy is necessary to ensure reliable and accurate data for R2 level replication. | For this CNC machining use case, apply this step to variables and records such as spindle speed, feed rate, spindle load, vibration, tool id, machine state. | sensor types; communication protocols | A detailed data collection strategy document | None |
| R1 | Develop the initial data representation layer. | Collect the data from the physical system, structure it, remove errors, and organize into a usable format. Verify and validate the data by comparing collected data to known system outputs. | A well-structured and validated data representation is crucial for R2 level replication. | For this CNC machining use case, apply this step to variables and records such as spindle speed, feed rate, spindle load, vibration, tool id, machine state. | collected data; known system outputs | Structured and validated data ready for R2 level replication | None |
| R2 | Define the digital twin's purpose, target decisions, and expected outcomes. | Define which system outputs must be reproduced and set allowable error thresholds. Select a modeling environment and justify why it fits the system behavior. | This ensures that the digital twin can accurately replicate real-world behavior within acceptable error bounds. | The digital twin should predict remaining useful life of cutting tools, spindles, and coolant to optimize maintenance scheduling. The allowable error threshold for these predictions is ±10% deviation from actual values. | error thresholds; modeling environment | A clear definition of the digital twin's purpose, target decisions, and expected outcomes | None |
| R2 | Map physical system to a digital architecture. | Create a digital model that matches both the physical components and digital model together. Define interfaces between components and implement system logic, behavior, and state. | This ensures that the virtual model accurately represents the real-world system. | For this CNC machining use case, apply this step to variables and records such as spindle speed, feed rate, spindle load, vibration, tool id, machine state. | physical components; system logic | A detailed digital architecture map | None |
| R2 | Integrate real data streams. | Connect live or recorded data to model inputs and parameter updates. Align the model with the real-world system by adjusting as necessary. | This ensures that the digital twin can accurately simulate real-world behavior using actual data. | Use real-time data from sensors such as temperature, position, and environmental conditions to update the simulation model. Adjust the model parameters based on observed behaviors in the real system. | live or recorded data; real-world system behavior | A calibrated digital twin that accurately reproduces real-world outputs | None |
| R2 | Run controlled test scenarios. | Run the model and compare the model outputs to the real world system. Adjust the model as necessary to fix any errors found during testing. | This ensures that the digital twin can accurately reproduce real-world behavior under various conditions. | Run simulations using known inputs such as processing times and system behavior, then compare results with actual system performance. Adjust model parameters based on observed deviations. | known system inputs; real-world system outputs | A validated digital twin that accurately reproduces real-world outputs | None |

## Priority Action List
1. Define the digital twin's purpose, target decisions, and expected outcomes.
2. Identify critical variables for the use case.
3. Design the data collection strategy.
4. Develop the initial data representation layer.
5. Define which system outputs must be reproduced and set allowable error thresholds.
6. Select a modeling environment and justify why it fits the system behavior.
7. Map physical system to a digital architecture.
8. Integrate real data streams.
9. Run controlled test scenarios.

## Missing Information or Data Gaps
- Detailed historical data for training predictive models (R3 level).
- Robust security measures and compliance policies (R4 level).

## Future Work Beyond Current 4R Level
- Advance from R1 to R3 by closing the remaining evidence and implementation gaps for the next level.
- Implement prediction targets, decision variables, and objective functions to support R3 level.
- Develop autonomous decision-making capabilities with human-in-the-loop boundaries for R4 level.
