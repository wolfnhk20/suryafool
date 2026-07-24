# Product Requirements Document: Suryafool

**Version:** 1.0
**Domain:** Agentic AI, Wireless Systems, IoT, Security Research
**Product Type:** Universal Agentic Wireless Platform
**Primary Users:** Hardware enthusiasts, makers, researchers, students and security researchers

---

# 1. Product Summary

**Suryafool is a universal agentic wireless platform that gives autonomous AI agents the ability to explore, understand, investigate and interact with the wireless world through modular radio hardware, including conducting autonomous security research and penetration testing within explicitly authorized environments.**

The core vision is simple:

> Give AI agents access to the invisible wireless world around us.

Instead of requiring a human to manually operate separate tools for Wi-Fi, Bluetooth, BLE, sub-GHz radio, NFC, RFID, infrared and future SDR capabilities, Suryafool provides a unified agentic layer capable of deciding:

* What is present?
* Which wireless technology is involved?
* What tools should be used?
* What should be investigated next?
* Are multiple observations related?
* How does an unknown device behave?
* What changed in the environment?
* Can an authorized system be interacted with?
* Does an authorized target expose a security weakness?
* What should the agents try next?

The long-term goal is to create a general-purpose **operating layer between autonomous AI agents and wireless systems**.

---

# 2. Vision

Modern physical environments are filled with wireless communication.

A single room may contain:

* Wi-Fi networks
* Bluetooth devices
* BLE advertisements
* NFC interfaces
* RFID systems
* Infrared-controlled appliances
* Sub-GHz remotes
* Proprietary IoT protocols
* Unknown RF transmissions

However, exploring this environment currently requires specialized hardware, protocol-specific tools and significant technical knowledge.

Existing wireless multi-tools provide access to several protocols but remain primarily human-operated.

AI assistants can reason about wireless systems but cannot independently perceive or interact with the physical wireless environment.

Suryafool bridges these two worlds.

```text
                ARTIFICIAL INTELLIGENCE

                         ↓

                AGENTIC REASONING

                         ↓

               SURYAFOOL PLATFORM

                         ↓

               CAPABILITY LAYER

                         ↓

       Wi-Fi  BLE  RF  NFC  RFID  IR  SDR

                         ↓

                 WIRELESS WORLD
```

The user should eventually be able to provide Suryafool with an objective rather than a sequence of commands.

Examples:

> "Explore everything around me."

> "What wireless devices are present in this authorized lab?"

> "Figure out how this remote works."

> "Investigate this unknown signal."

> "What changed in this environment since yesterday?"

> "Why did this IoT device stop communicating?"

> "Audit this device for wireless security weaknesses."

> "Within this isolated cyber-range, find a permitted way into the target."

Suryafool determines how to approach the objective.

---

# 3. Problem Statement

Wireless technologies exist as fragmented ecosystems.

Different technologies require different:

* Hardware
* Drivers
* Libraries
* Protocol knowledge
* Capture formats
* Analysis tools
* Security tools
* User workflows

A hardware enthusiast exploring an unknown environment must first know what technology they are dealing with and then manually select the appropriate hardware and software.

Traditional tools answer questions such as:

> "Show me nearby BLE devices."

Suryafool aims to answer broader questions:

> "What is happening wirelessly around me?"

Traditional tools execute commands.

Suryafool conducts **missions**.

The platform must therefore solve five fundamental problems:

1. Give agents standardized access to heterogeneous wireless hardware.
2. Allow agents to autonomously select appropriate tools.
3. Maintain persistent knowledge about wireless environments.
4. Correlate information across otherwise isolated protocols.
5. Enable controlled autonomous interaction and security experimentation within explicit authorization boundaries.

---

# 4. Product Philosophy

Suryafool should not be built as:

> An AI-powered Flipper Zero clone.

Nor should it be built as:

> An autonomous hacking tool.

The larger concept is:

> **A universal agentic interface to wireless environments.**

Wireless penetration testing is one powerful application of that interface.

The platform should support four major capability pillars:

```text
               SURYAFOOL

                    │

      ┌─────────────┼─────────────┐
      │             │             │
      ▼             ▼             ▼

  EXPLORATION   INVESTIGATION   INTERACTION
                                    │
                                    ▼
                               SECURITY
                                RESEARCH
```

These capabilities should share the same underlying hardware abstraction, memory and agent architecture.

---

# 5. Core Capability Model

Suryafool should abstract hardware into capabilities.

Agents should reason using operations such as:

```text
DISCOVER

OBSERVE

CAPTURE

IDENTIFY

ANALYZE

COMPARE

CORRELATE

EXPERIMENT

INTERACT

TEST

VERIFY
```

A hardware module may implement one or more capabilities.

For example:

```text
ESP32

Wi-Fi:
DISCOVER
OBSERVE

BLE:
DISCOVER
OBSERVE
INTERACT
```

Another module may expose:

```text
CC1101

Sub-GHz:
OBSERVE
CAPTURE
ANALYZE
INTERACT
```

The agents should not need to understand the hardware implementation unless hardware-specific reasoning is necessary.

---

# 6. Core User Experience

The user launches Suryafool.

The platform discovers connected hardware.

```text
SURYAFOOL ONLINE

Detected capabilities:

Wi-Fi
✓ Discovery
✓ Observation

BLE
✓ Discovery
✓ Advertisement analysis

Sub-GHz
✓ Signal observation
✓ Capture
✓ Transmission

NFC/RFID
✓ Detection
✓ Inspection

Infrared
✓ Capture
✓ Transmission
```

The user then provides a mission.

For example:

> Explore this environment.

The Mission Planner creates an autonomous investigation plan.

```text
MISSION: ENVIRONMENT EXPLORATION

Phase 1
Passive discovery

Phase 2
Signal classification

Phase 3
Device identification

Phase 4
Cross-protocol correlation

Phase 5
Targeted investigation

Phase 6
Environment graph construction
```

The agents execute the mission and modify the plan as new information appears.

---

# 7. Mission System

Suryafool operates around persistent **missions** rather than isolated commands.

A mission contains:

* Objective
* Authorization scope
* Available capabilities
* Observations
* Hypotheses
* Planned actions
* Executed actions
* Evidence
* Agent reasoning state
* Results

The mission may last seconds, minutes or potentially hours.

Agents should be capable of replanning based on newly discovered information.

---

# 8. Mission Types

## 8.1 Explore

Objective:

> Understand the observable wireless environment.

The agents perform broad passive discovery and construct an environment model.

---

## 8.2 Investigate

Objective:

> Understand a specific device, signal or wireless phenomenon.

Agents progressively collect evidence and generate hypotheses.

---

## 8.3 Compare

Objective:

> Determine what changed between two observations of an environment.

Potential findings include:

* New devices
* Missing devices
* Changed identifiers
* New frequencies
* Behavioral changes
* Previously unseen signals

---

## 8.4 Understand

Objective:

> Learn how an authorized device communicates.

The system may guide the user through controlled experiments.

Example:

```text
Please press Button A three times.

Capture completed.

Now press Button B three times.

Analyzing differences...
```

Agents compare observations and attempt to infer behavioral relationships.

---

## 8.5 Diagnose

Objective:

> Investigate why a wireless system is not behaving as expected.

Agents compare historical and current observations and generate diagnostic hypotheses.

---

## 8.6 Automate

Objective:

> Interact with authorized wireless systems to accomplish user-defined tasks.

Automation remains bounded by supported hardware and explicit authorization.

---

## 8.7 Security Research

Objective:

> Investigate the security properties of an authorized wireless system.

This mission may use specialized security analysis capabilities.

---

## 8.8 Autonomous Penetration Testing

Objective:

> Within an explicitly authorized and preferably isolated test environment, autonomously discover and validate security weaknesses.

The system should:

```text
DISCOVER

     ↓

MAP ATTACK SURFACE

     ↓

FORM HYPOTHESES

     ↓

SELECT PERMITTED TEST

     ↓

EXECUTE

     ↓

OBSERVE RESULT

     ↓

VERIFY

     ↓

REPLAN
```

The objective is autonomous security experimentation rather than blindly executing a predetermined list of attacks.

---

# 9. Multi-Agent Architecture

## 9.1 Mission Orchestrator

The central coordination agent.

Responsibilities:

* Interpret mission objectives.
* Delegate tasks.
* Maintain mission state.
* Coordinate specialized agents.
* Handle replanning.
* Determine when objectives have been reached.

---

## 9.2 Discovery Agent

Responsible for broad environmental reconnaissance.

Tasks include:

* Selecting available discovery capabilities.
* Gathering observations.
* Normalizing results.
* Avoiding redundant scans.

---

## 9.3 Signal Intelligence Agent

Investigates wireless signals.

Responsibilities:

* Characterize observations.
* Compare repeated captures.
* Detect recurring patterns.
* Identify candidate signal families.
* Request additional observations.

It must maintain clear distinctions between:

```text
CONFIRMED

LIKELY

POSSIBLE

UNKNOWN
```

---

## 9.4 Device Intelligence Agent

Creates logical representations of observed devices.

Example:

```text
PHYSICAL DEVICE HYPOTHESIS #14

Observed interfaces:

Wi-Fi Device #8
BLE Device #19

Correlation confidence: 82%

Evidence:

Similar manufacturer information
Similar observation timing
Consistent signal proximity
```

---

## 9.5 Correlation Agent

Searches for relationships across wireless technologies.

This is one of Suryafool's primary differentiating capabilities.

It attempts to determine whether multiple observations belong to:

* The same physical device
* The same communication system
* Related devices
* The same user-controlled interaction
* The same environmental event

---

## 9.6 Experiment Agent

Designs controlled investigations.

Instead of simply saying:

> "I don't know what this signal means."

The agent asks:

> "What observation would help distinguish between my hypotheses?"

It may then request another capture or suggest a controlled user action.

---

## 9.7 Security Research Agent

Analyzes authorized devices for potential weaknesses.

Responsibilities include:

* Identifying exposed interfaces.
* Mapping observable attack surfaces.
* Matching known classes of weaknesses.
* Recommending appropriate permitted security tests.
* Coordinating with protocol-specific security tools.

---

## 9.8 Attack Planning Agent

Only active during authorized security missions.

Its purpose is to reason about potential security-testing paths.

Conceptually:

```text
TARGET

   │

   ├── Wi-Fi Interface
   │
   ├── BLE Interface
   │
   ├── NFC Interface
   │
   └── Sub-GHz Interface

            ↓

      POSSIBLE TEST PATHS

            ↓

      POLICY VALIDATION

            ↓

       SAFE EXECUTION
```

The agent should adapt when a selected test does not succeed rather than blindly repeating actions.

---

## 9.9 Verification Agent

Security findings must be independently verified where possible.

The Verification Agent determines:

* Whether the observed behavior actually demonstrates the claimed issue.
* Whether the result is reproducible.
* Whether alternative explanations exist.
* What evidence supports the conclusion.

---

## 9.10 Skeptic Agent

Challenges conclusions produced by other agents.

Examples:

> Could these actually be two different devices?

> Is this signal correlation coincidental?

> Did the security test genuinely succeed?

> Could the observed behavior have another explanation?

This reduces overconfident agent conclusions.

---

## 9.11 Memory Agent

Maintains persistent environmental and mission knowledge.

The system should remember:

* Previously observed devices
* Signals
* Frequencies
* Relationships
* Experiments
* Security findings
* Successful and unsuccessful investigation strategies

This enables Suryafool to learn from previous missions.

---

## 9.12 Scope Guardian

Every active operation must pass through the Scope Guardian.

The Scope Guardian is not merely another advisory agent.

It is an enforced policy layer.

Operations are classified as:

```text
PASSIVE

SAFE ACTIVE

SENSITIVE ACTIVE

RESTRICTED
```

The Scope Guardian determines whether an action is allowed based on:

* Defined target
* Mission type
* User authorization
* Environment
* Capability risk
* Previous approvals

Restricted actions outside scope are blocked regardless of what another agent requests.

---

# 10. Agentic Security Laboratory

Suryafool should include a dedicated **Lab Mode** for autonomous security experimentation.

Lab Mode allows users to define an isolated environment containing devices they own or have explicit permission to test.

Example:

```text
LAB: SURYAFOOL TEST RANGE

Authorized targets:

✓ ESP32 Target #1
✓ Test BLE Device
✓ NFC Test Tag
✓ Sub-GHz Development Node

Other observed devices:

NOT AUTHORIZED
```

Agents may actively interact only with approved targets.

This allows aggressive autonomous experimentation to be developed safely without treating every observable nearby device as a target.

---

# 11. Cross-Protocol Attack-Surface Graph

One of the most ambitious Suryafool features is a unified representation of a device's wireless attack surface.

```text
                 PHYSICAL DEVICE

                       │

       ┌───────────────┼───────────────┐

       ▼               ▼               ▼

     Wi-Fi            BLE             NFC

       │               │               │

  Service A       Characteristic    Config Interface

       │               │               │

       └───────────────┼───────────────┘

                       ▼

                ATTACK-SURFACE GRAPH
```

Traditional tools analyze individual protocols.

Suryafool should eventually reason about whether weaknesses across multiple interfaces combine into larger attack paths.

This is a long-term capability rather than an MVP requirement.

---

# 12. Wireless Environment Graph

Suryafool maintains a live graph containing:

```text
ENVIRONMENT

├── Physical Device Hypotheses
│
├── Wireless Interfaces
│
├── Signals
│
├── Frequencies
│
├── Protocols
│
├── Relationships
│
├── Historical Observations
│
├── Experiments
│
└── Security Findings
```

Edges should include confidence and evidence.

For example:

```text
BLE_DEVICE_17

   │

   │ likely_same_device
   │ confidence: 78%

   ▼

WIFI_DEVICE_09
```

The graph becomes Suryafool's evolving model of the wireless environment.

---

# 13. Hardware Architecture

The laptop acts as the primary computational brain.

```text
                    LAPTOP

           Agentic AI Orchestration

                      │

              Suryafool Runtime

                      │

             Capability Registry

                      │

       ┌──────────────┼──────────────┐

       ▼              ▼              ▼

     ESP32          CC1101       NFC/RFID

 Wi-Fi + BLE       Sub-GHz        Module

                                      │

                              IR Tx / Rx Module
```

Target initial hardware budget:

**₹3,000 maximum**

Potential initial hardware:

* ESP32
* CC1101
* NFC/RFID module
* IR transmitter and receiver
* Required antennas/connectors

Software-defined radio support may be added later.

---

# 14. Hardware Abstraction Layer

Hardware should expose standardized capabilities.

Conceptually:

```text
list_capabilities()

discover()

observe()

capture()

analyze()

interact()

test()

verify()
```

Protocol-specific implementations sit underneath these abstractions.

This enables hardware to be upgraded without redesigning the agent architecture.

---

# 15. Plugin Architecture

Suryafool should eventually support external capability providers.

A plugin describes:

```text
PLUGIN

Name

Technology

Hardware requirements

Capabilities

Available operations

Risk classification

Required permissions
```

When a plugin is installed, its capabilities become available to the Mission Planner.

This allows the platform to expand beyond the hardware developed during the final-year project.

---

# 16. MVP

The MVP should prove four things:

### 1. Agents can perceive the wireless environment.

At least two distinct wireless technologies should be supported.

### 2. Agents can autonomously investigate.

The system must perform multi-step exploration based on observations rather than executing only fixed workflows.

### 3. Agents can safely interact with authorized targets.

At least one controlled interaction should be demonstrated.

### 4. Agents can perform an autonomous authorized security investigation.

Within an isolated test environment, agents should discover an intentionally vulnerable target, identify an approved security-testing path, execute a bounded validation and generate evidence-backed findings.

---

# 17. MVP Feature Requirements

Required:

* Mission-based interaction
* Multi-agent orchestration
* Capability registry
* Hardware abstraction
* Wi-Fi support
* BLE support
* At least one external wireless module
* Passive environment exploration
* Persistent mission memory
* Wireless Environment Graph
* Signal/device investigation
* Scope Guardian
* Lab Mode
* Security Research Agent
* Autonomous bounded security-testing workflow
* Evidence-based reporting

Strong stretch goals:

* Sub-GHz investigation
* NFC/RFID integration
* Infrared integration
* Cross-protocol correlation
* Attack-Surface Graph
* Device behavior learning

---

# 18. Example Demonstration

The final demonstration could use an isolated lab containing several owned devices.

The evaluator gives Suryafool the mission:

> "Explore this environment and tell me what you find."

Suryafool:

```text
1. Detects available hardware.

2. Performs passive wireless discovery.

3. Identifies observable devices and signals.

4. Builds an environment graph.

5. Finds an unknown or interesting device.

6. Selects appropriate investigation tools.

7. Requests controlled experiments where needed.

8. Updates its understanding.
```

The evaluator can then switch to an authorized security mission:

> "Assess Target Device A."

Suryafool:

```text
1. Confirms target scope.

2. Maps observable interfaces.

3. Constructs attack-surface hypotheses.

4. Selects an approved validation strategy.

5. Executes permitted tests.

6. Observes the result.

7. Replans if necessary.

8. Independently verifies findings.

9. Generates a security assessment.
```

The important demonstration is not a specific attack.

The important demonstration is that the **agents independently decide how to investigate the target using the wireless capabilities available to them**.

---

# 19. Safety Requirements

Because Suryafool connects autonomous agents to real wireless hardware, safety must be enforced architecturally.

Requirements:

* Passive exploration is the default operating mode.
* Active interactions require explicit mission scope.
* Security testing requires Lab Mode or equivalent explicit authorization.
* Every active tool has a risk classification.
* Restricted capabilities cannot be invoked without the required authorization state.
* All agent actions are logged.
* Users can terminate a mission immediately.
* Agents cannot modify their own scope.
* Scope validation occurs outside the LLM decision layer.

The system should demonstrate how powerful autonomous agents can be given real-world capabilities while remaining constrained by deterministic controls.

---

# 20. Non-Goals

Suryafool is not intended to:

* Automatically attack arbitrary nearby devices.
* Circumvent authorization boundaries.
* Guarantee successful exploitation.
* Replace professional RF laboratory equipment.
* Support every wireless protocol in its first version.
* Run all AI inference directly on embedded hardware.
* Become solely a cybersecurity product.

Security research is one major capability of a broader wireless intelligence platform.

---

# 21. Research Questions

The project should investigate:

1. Can autonomous agents effectively select tools across heterogeneous wireless technologies?

2. Can agents conduct open-ended wireless investigations instead of following predefined workflows?

3. Can observations from different wireless technologies be correlated into a unified environmental model?

4. Can an agent autonomously decide what additional evidence it needs to understand an unknown wireless phenomenon?

5. Can autonomous security agents safely operate under deterministic scope restrictions?

6. Can multiple specialized agents outperform a single general-purpose agent in wireless investigation tasks?

7. Can an agent learn from unsuccessful experiments and dynamically change its investigation strategy?

8. Can cross-protocol reasoning reveal relationships that isolated wireless tools fail to identify?

---

# 22. Success Metrics

Suryafool will be considered successful if the prototype can demonstrate:

* Autonomous hardware capability discovery.
* Multi-protocol wireless exploration.
* Mission planning from natural-language objectives.
* Dynamic tool selection.
* Multi-step autonomous investigation.
* Persistent environmental memory.
* Detection of environmental changes.
* Evidence-backed signal/device hypotheses.
* At least one controlled wireless interaction.
* At least one bounded autonomous security assessment against an authorized lab target.
* Deterministic prevention of out-of-scope active actions.

---

# 23. Future Vision

Future versions of Suryafool may support:

* Software-defined radio
* Additional sub-GHz protocols
* LoRa
* Zigbee
* Thread
* Matter
* Cellular observation capabilities where legally and technically appropriate
* Distributed Suryafool nodes
* Autonomous RF anomaly hunting
* Wireless debugging
* Protocol characterization
* IoT device diagnostics
* Home automation
* Cross-protocol security research
* Wireless digital twins
* Long-running autonomous investigations
* Community-developed hardware plugins
* Specialized agent packs

Multiple Suryafool nodes could eventually collaborate:

```text
SURYAFOOL NODE A
        │
SURYAFOOL NODE B
        │
SURYAFOOL NODE C

        ↓

DISTRIBUTED WIRELESS INTELLIGENCE

        ↓

SHARED ENVIRONMENT MODEL
```

This could transform Suryafool from a single-device platform into a distributed agentic sensing and interaction network.

---

# 24. Final Definition

## Suryafool

**A universal agentic wireless platform that gives autonomous AI agents the ability to perceive, explore, understand, investigate and interact with heterogeneous wireless environments through modular hardware, including safely conducting autonomous penetration testing and security research within explicitly authorized environments.**

The project's fundamental innovation is not Wi-Fi scanning, RF capture, NFC interaction or autonomous hacking individually.

It is the creation of a generalized layer through which AI agents can independently decide:

> **What am I observing?**

> **What does it mean?**

> **What tool should I use next?**

> **What experiment should I perform?**

> **Can I interact with it?**

> **Within my authorization, can I find and validate a weakness?**

> **What did I learn from the result?**

Suryafool is ultimately an attempt to give autonomous AI agents **eyes, ears and hands for the wireless world**.
