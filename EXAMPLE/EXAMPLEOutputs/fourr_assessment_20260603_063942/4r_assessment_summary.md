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
The recommended build target is R1. The current evidence baseline is R1. The planned digital twin for CNC machining systems aims to provide real-time data-driven insights into quality, cost, and time before production begins. The primary focus is on accurate scheduling based on available equipment, predictive maintenance, and tool wear prediction.

## Desired Future Vision vs. Current Feasible Target
The recommended pre-build target is R1. The next level beyond that is R2. Future work beyond the recommendation should stay clearly separated from the current build boundary.

## Feasible capabilities used
- No feasible capability list was available from the DTAF readiness screen.

## 4R Level Support Status
| 4R Level | Supported as Build Target | Evidence Strength | Main Reason | Key Gaps |
|---|---|---|---|---|
| R1 | Partial | partial | The planning evidence supports the foundational aspects required for R1, such as data collection and storage. However, it lacks explicit definitions of purpose, scope, and critical variables. | System boundaries, major components, inputs/outputs, and important states are identified.; A repeatable data collection and storage pipeline exists.; Collected data is structured, usable, and verified against known system behavior. |
| R2 | No | weak | The evidence supports R1 capabilities but lacks explicit replication targets, decision variables, and independent execution. The digital twin can be built to achieve R2 level with additional planning. | R1 is already satisfied.; A modeling platform has been selected and the system has been mapped into a digital architecture.; The model has been tested against real behavior and verified to reproduce outputs with acceptable deviation. |
| R3 | No | weak | The evidence supports R2 capabilities but lacks explicit prediction targets, scenario analysis, and actionable insights. The digital twin can be built to achieve R3 level with additional planning. | R2 is already satisfied.; The DT can run without continuous live dependency on the physical system.; Predictive or scenario-exploration models are implemented. |
| R4 | No | weak | The evidence does not provide clear evidence for R3 capabilities. The digital twin can be built to achieve R4 level with significant additional planning. | R3 is already satisfied.; Autonomy scope, human-in-the-loop boundaries, and override conditions are defined.; The DT can detect anomalies or changing conditions in real time. |

## Revised Gate Criteria Assessment
| 4R Level | Gate Criterion | Score | Evidence | Rationale | Needed Improvement |
|---|---|---:|---|---|---|
| R1 | The digital twin purpose, scope, and supported decisions are explicitly defined. | 2 | No clear statement on the digital twin's purpose or use case. | The planning summary does not explicitly define the DT's purpose and scope. \| evidence found in prior outputs | None |
| R1 | System boundaries, major components, inputs/outputs, and important states are identified. | 1 | System boundaries are identified through data collection sources (sensors, enterprise systems). | While system boundaries are mentioned, they are not fully defined or categorized. \| evidence found in prior outputs | Strengthen with direct, use-case-specific evidence and a reviewable deliverable. |
| R1 | Critical variables are selected without major over-instrumentation or missing context. | 2 | Critical variables are selected but over-instrumentation is a risk. | The planning summary does not explicitly list critical variables without potential over-instrumentation. \| evidence found in prior outputs | None |
| R1 | A repeatable data collection and storage pipeline exists. | 1 | A repeatable data collection and storage pipeline exists through edge computing and cloud services. | Data acquisition and storage are planned but not fully detailed. \| evidence found in prior outputs | Strengthen with direct, use-case-specific evidence and a reviewable deliverable. |
| R1 | Collected data is structured, usable, and verified against known system behavior. | 0 | Collected data is structured but verification against known system behavior is not explicitly mentioned. | While data structures are defined, there is no evidence of validation processes. \| evidence found in prior outputs | Add explicit evidence, data, or design detail before claiming support. |
| R2 | R1 is already satisfied. | 1 | Replication targets are implied through predictive maintenance and tool wear prediction. | While the purpose is not explicitly stated, replication targets are inferred from the use cases. | Strengthen with direct, use-case-specific evidence and a reviewable deliverable. |
| R2 | Replication targets, required outputs, and acceptable error thresholds are defined. | 2 | Decision variables and objective functions are not defined. | The planning summary does not specify what decisions the DT should support. \| evidence found in prior outputs | None |
| R2 | A modeling platform has been selected and the system has been mapped into a digital architecture. | 1 | A modeling platform has been selected (edge computing and cloud services). | Edge and cloud services are planned for model development but not fully detailed. \| evidence found in prior outputs | Strengthen with direct, use-case-specific evidence and a reviewable deliverable. |
| R2 | Live or recorded data can drive model inputs and updates. | 2 | Live or recorded data can drive model inputs and updates. | While data sources are identified, there is no explicit mention of real-time data driving the model. \| evidence found in prior outputs | None |
| R2 | The model has been tested against real behavior and verified to reproduce outputs with acceptable deviation. | 1 | The DT can run without continuous live dependency on the physical system through edge computing. | Edge computing supports independent execution but not fully detailed. \| evidence found in prior outputs | Strengthen with direct, use-case-specific evidence and a reviewable deliverable. |
| R3 | R2 is already satisfied. | 1 | Prediction targets are implied through predictive maintenance and tool wear prediction. | While the purpose is not explicitly stated, prediction targets are inferred from the use cases. | Strengthen with direct, use-case-specific evidence and a reviewable deliverable. |
| R3 | Prediction targets, decision variables, and objective functions are defined. | 2 | Decision variables and objective functions are not defined. | The planning summary does not specify what decisions the DT should support. \| evidence found in prior outputs | None |
| R3 | The DT can run without continuous live dependency on the physical system. | 1 | The DT can run without continuous live dependency on the physical system through edge computing. | Edge computing supports independent execution but not fully detailed. \| evidence found in prior outputs | Strengthen with direct, use-case-specific evidence and a reviewable deliverable. |
| R3 | Predictive or scenario-exploration models are implemented. | 1 | Predictive or scenario-exploration models are implemented. | While predictive models are implied, there is no explicit mention of scenario analysis workflows. \| evidence found in prior outputs | Strengthen with direct, use-case-specific evidence and a reviewable deliverable. |
| R3 | The DT can evaluate what-if conditions and provide actionable recommendations or optimized results. | 1 | The DT can evaluate what-if conditions and provide actionable recommendations or optimized results through edge computing. | Edge computing supports real-time decision support but not fully detailed. \| evidence found in prior outputs | Strengthen with direct, use-case-specific evidence and a reviewable deliverable. |
| R4 | R3 is already satisfied. | 0 | Autonomy scope is not defined. | The planning summary does not specify the autonomy level or human-in-the-loop boundaries. | Add explicit evidence, data, or design detail before claiming support. |
| R4 | Autonomy scope, human-in-the-loop boundaries, and override conditions are defined. | 1 | Human-in-the-loop boundaries are not defined. | The planning summary does not specify how humans will interact with the DT. \| partial evidence found in prior outputs | Strengthen with direct, use-case-specific evidence and a reviewable deliverable. |
| R4 | The DT can detect anomalies or changing conditions in real time. | 1 | The DT can detect anomalies through edge computing. | Edge computing supports anomaly detection but not fully detailed. \| evidence found in prior outputs | Strengthen with direct, use-case-specific evidence and a reviewable deliverable. |
| R4 | The DT can choose among actions based on learned or adaptive logic. | 1 | The DT can choose among actions based on learned or adaptive logic. | While predictive models are implied, there is no explicit mention of decision-making policies. \| evidence found in prior outputs | Strengthen with direct, use-case-specific evidence and a reviewable deliverable. |
| R4 | Past outcomes are stored and used to improve future decisions. | 1 | Past outcomes are stored and used to improve future decisions through edge computing. | Edge computing supports learning from past data but not fully detailed. \| evidence found in prior outputs | Strengthen with direct, use-case-specific evidence and a reviewable deliverable. |
| R4 | The DT can make or execute decisions with acceptable trust and safety controls. | 2 | [step0] Security breaches leading to data loss or unauthorized access. | evidence found in prior outputs | None |

## Tailored 4R Action Items
| 4R Level | Action Item | What to Do | Why It Matters | Use-Case-Specific Example | Required Data or Inputs | Expected Output or Evidence | Dependencies or Gaps |
|---|---|---|---|---|---|---|---|
| R1 | Define the purpose, scope, and goal of the digital twin. | Write a one-paragraph statement defining the DT's purpose, target decisions, and expected outcomes. Document system boundaries, included/excluded components, and key interactions. | This ensures clarity on what the digital twin is intended to achieve and helps in aligning all stakeholders with its objectives. | The goal of the digital twin was to create a data-driven platform for CNC machining systems that can predict tool wear, optimize scheduling based on available equipment, and automate key decision-making processes. The expected outcomes include real-time monitoring of machine health, accurate scheduling, and reduced cycle time. | System boundaries; Included/excluded components; Key interactions | A clear statement defining the DT's purpose, scope, and goals, along with documented system boundaries and key interactions. | Ensure that all stakeholders are involved in this process to gather comprehensive input. |
| R1 | Identify critical variables for the use case. | List static properties and dynamic states, then identify the minimum critical variables required. Ensure that over-instrumentation is avoided. | This step ensures that only essential data is collected, reducing complexity and improving efficiency. | For this CNC machining use case, apply this step to variables and records such as spindle speed, feed rate, spindle load, vibration, tool id, machine state. | Static properties; Dynamic states | A list of critical variables that are essential for the digital twin's functionality. | Ensure that all relevant stakeholders provide input on which variables are most important. |
| R1 | Design the data collection strategy. | Determine the sensors/data sources needed and where they should be placed. Define data acquisition methods, communication protocols, synchronization requirements, and storage solutions. | A well-designed data collection strategy ensures that all necessary data is collected in a timely and accurate manner. | For this CNC machining use case, apply this step to variables and records such as spindle speed, feed rate, spindle load, vibration, tool id, machine state. | Sensors; APIs; Communication protocols | A detailed plan for data collection, including sensor placement, communication methods, and storage solutions. | Ensure that all necessary hardware and software are available and properly configured. |
| R1 | Develop the initial data representation layer. | Collect the data from the physical system, structure it, remove errors, and organize into a usable format. Verify and validate the data by comparing collected data to known system outputs. | This ensures that the data is clean, structured, and immediately usable for analysis or modeling. | For this CNC machining use case, apply this step to variables and records such as spindle speed, feed rate, spindle load, vibration, tool id, machine state. | Collected data; Known system outputs | Structured and validated data that is ready for analysis or modeling. | Ensure that all necessary tools and processes are in place to clean and validate the data. |

## Priority Action List
1. Define the purpose, scope, and goal of the digital twin.
2. Identify critical variables for the use case.
3. Design the data collection strategy.
4. Develop the initial data representation layer.

## Missing Information or Data Gaps
- Detailed documentation on system boundaries and key interactions.
- A clear list of static properties and dynamic states.
- Specific details on sensor placement and communication protocols.
- Validation processes for collected data against known outputs.

## Future Work Beyond Current 4R Level
- Advance from R1 to R2 by closing the remaining evidence and implementation gaps for the next level.
- Define prediction targets, decision variables, and objective functions to support R2 level capabilities.
- Implement predictive models and scenario analysis workflows to support R3 level capabilities.
- Integrate control-system connections and real-time anomaly detection for R4 level autonomy.
