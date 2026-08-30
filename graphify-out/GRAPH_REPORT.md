# Graph Report - suryafool  (2026-08-30)

## Corpus Check
- 181 files · ~139,103 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 2757 nodes · 7479 edges · 221 communities (186 shown, 35 thin omitted)
- Extraction: 73% EXTRACTED · 27% INFERRED · 0% AMBIGUOUS · INFERRED: 1983 edges (avg confidence: 0.5)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `20871abd`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- checks.py
- theme.js
- devDependencies
- changed-files-store.ts
- tools/index.ts
- _RateLimitedLLM
- compilerOptions
- instructions
- binary.js
- _engine_with_scope
- command
- agent
- edit
- write
- bash
- read
- build-error-resolver
- code-reviewer
- cpp-build-resolver
- cpp-reviewer
- database-reviewer
- doc-updater
- docs-lookup
- e2e-runner
- go-build-resolver
- go-reviewer
- java-build-resolver
- java-reviewer
- kotlin-reviewer
- php-reviewer
- planner
- python-reviewer
- refactor-cleaner
- rust-reviewer
- security-reviewer
- tdd-guide
- build-fix
- code-review
- e2e
- go-build
- go-review
- go-test
- orchestrate
- plan
- refactor-clean
- security
- tdd
- test-coverage
- update-codemaps
- update-docs
- TestPhaseRegression
- build_scenario
- ECC - OpenCode Instructions
- Migration Guide: Claude Code to OpenCode
- projects
- Environment
- Bootstrap Agent - Initial Implementation
- test_phase283_ir.py
- suryafool
- Eval Command
- OpenCode ECC Plugin
- CLI_BEAUTIFY.md
- Review Checklist
- Refactor Clean Command
- Orchestrate Command
- Review Checklist
- Common Rust Errors
- Documentation Types
- Verification Checklist
- AGENTS.md — Suryafool
- E2E Command
- Go Build Command
- TDD Cycle for Go
- Instinct Export Command
- Instinct Import Command
- TDD Cycle for Rust
- Setup Package Manager Command
- Your Task
- Test Coverage Command
- Suryafool
- CONTEXT.md — Suryafool (Root)
- Check Categories
- Report Format
- Update Codemaps Command
- Output Format
- Output Format
- Security Scan Command
- Analysis Process
- PROJECT.md — Suryafool Complete Project Reference
- Build Fix Command
- Harness Audit Command
- Checkpoint Command
- Loop Start Command
- Loop Status Command
- Model Route Command
- Quality Gate Command
- Evolve Command
- PRD.md
- Instinct Status Command
- _engine_with_scope
- 9. Multi-Agent Architecture
- Projects Command
- Promote Command
- instinct-export
- _engine_with_scope
- Capability
- graphify.js
- run.mjs
- IrSignal
- `llm.py` — LLM Factory + Rate Limiter
- TestUnsupportedCapabilityBehavior
- CONTEXT.md — bootstrap/
- dependencies
- package.json
- keywords
- scripts
- Suryafool — Bootstrap / Environment Agent
- 8. Mission Types
- default_registry
- bootstrap-agent-not-installed.md
- Run
- CONTEXT.md — docs/
- test_phase284_zigbee.py
- _engine_with_scope
- 16. MVP
- TestRegression
- TestContractAudit
- BleDevice
- _tmp_runs_dir
- TestPhaseRegression
- _tmp_runs_dir
- performed_capability_keys
- TestPairHandler
- _engine_with_scope
- TestJoinFailure
- ActionRequest
- _engine_with_scope
- TestGattWriteHandler
- phase2.py
- run_full_agent
- _engine_with_scope
- agent.py
- animations/index.js
- TestContractFields
- ecc-hooks.ts
- TabPanel.js
- test_phase279_integration.py
- AnimationEngine
- security-audit.ts
- dependency-analyzer.ts
- CONTEXT.md — policy/
- provisioning_guardian.py
- CONTEXT.md — capabilities/
- CONTEXT.md — cli/
- CONTEXT.md — engine/
- CONTEXT.md — simulator/
- _safe_active_scope
- format-code.ts
- lint-check.ts
- CONTEXT.md — reports/
- Event
- git-summary.ts
- test_phase2_cmds.cjs
- test_phase2_wiring.cjs
- setup-pm
- default_exploration_plan
- Confidence
- reducer.js
- Scanner
- app.js
- TestFailedCaptureNoFalsePositive
- Any
- _engine_with_scope
- _engine_with_scope
- TestRegression
- TestNewDomainRegistration
- instinct-import
- TestDeterminism
- TestFailedCaptureNoEvidence
- TestRegression
- TestNewCapabilityMetadata
- TestPhase27FreezeRegression
- _run_all
- opencode.json
- Path
- TestEntitySubstrate
- learn
- .with_tiers
- action_wifi_capture_handshake
- .enabled
- _tmp_runs_dir
- AGENTS.md
- _tmp_runs_dir
- _tmp_runs_dir
- .with_cumulative_tier
- .test_same_seed_same_observations
- promote
- _tmp_runs_dir
- _tmp_runs_dir
- _tmp_runs_dir
- test_phase273_ble_gatt.py
- _tmp_runs_dir
- _tmp_runs_dir
- _tmp_runs_dir
- .snapshot
- TestRegressionContract
- _tmp_runs_dir

## God Nodes (most connected - your core abstractions)
1. `ActionRequest` - 332 edges
2. `Run` - 216 edges
3. `RunLogger` - 208 edges
4. `RunEngine` - 208 edges
5. `PolicyEngine` - 206 edges
6. `Environment` - 206 edges
7. `AuthorizationScope` - 205 edges
8. `ActionRisk` - 192 edges
9. `RunStatus` - 190 edges
10. `PolicyDecisionKind` - 187 edges

## Surprising Connections (you probably didn't know these)
- `run_full_agent()` --calls--> `Rule`  [INFERRED]
  bootstrap/agent.py → policy/policy.py
- `Capability` --uses--> `ActionRisk`  [INFERRED]
  capabilities/base.py → core/mission.py
- `Capability` --uses--> `Observation`  [INFERRED]
  capabilities/base.py → core/observation.py
- `_FakeTmpPath` --uses--> `Capability`  [INFERRED]
  tests/test_phase26_authorization.py → capabilities/base.py
- `TestAuthorizationScopeSerialization` --uses--> `Capability`  [INFERRED]
  tests/test_phase26_authorization.py → capabilities/base.py

## Import Cycles
- None detected.

## Communities (221 total, 35 thin omitted)

### Community 0 - "checks.py"
Cohesion: 0.14
Nodes (23): check(), check_all(), CheckResult, filter_manifest(), bootstrap/checks.py  Read-only check() implementations for each manifest depende, Return only the manifest entries that apply to the given OS.      An entry witho, Run the check_cmd for a manifest entry and evaluate success.      Accepts either, Filter the manifest for the current OS, then run check() for every     applicabl (+15 more)

### Community 1 - "theme.js"
Cohesion: 0.16
Nodes (6): AGENTS, AgentStatus(), InputPrompt(), COMMANDS, ScanPanel(), themes

### Community 2 - "devDependencies"
Cohesion: 0.13
Nodes (15): @babel/core, @babel/preset-env, @babel/preset-react, esbuild, ink-testing-library, devDependencies, @babel/core, @babel/preset-env (+7 more)

### Community 3 - "changed-files-store.ts"
Cohesion: 0.20
Nodes (11): addToTree(), buildTree(), changes, ChangeType, getChangedPaths(), hasChanges(), recordChange(), toRelative() (+3 more)

### Community 4 - "tools/index.ts"
Cohesion: 0.20
Nodes (4): checkCoverageTool, CoverageResult, CoverageSummary, runTestsTool

### Community 5 - "_RateLimitedLLM"
Cohesion: 0.10
Nodes (12): _build_default_limiter(), _build_openai_compatible(), get_llm(), get_rate_limiter(), ProviderConfig, _RateLimitedLLM, core/llm.py  LLM factory with OpenRouter (primary) + OpenCode Zen (fallback) f, Wrapper around a LangChain chat model with rate limiting. (+4 more)

### Community 6 - "compilerOptions"
Cohesion: 0.07
Nodes (27): compilerOptions, declaration, declarationMap, esModuleInterop, forceConsistentCasingInFileNames, isolatedModules, lib, module (+19 more)

### Community 7 - "instructions"
Cohesion: 0.13
Nodes (15): instructions, AGENTS.md, CONTRIBUTING.md, instructions/INSTRUCTIONS.md, skills/api-design/SKILL.md, skills/backend-patterns/SKILL.md, skills/coding-standards/SKILL.md, skills/e2e-testing/SKILL.md (+7 more)

### Community 8 - "binary.js"
Cohesion: 0.05
Nodes (39): __dirname, main(), postinstall(), spinnerFrames, startSpinner(), stopSpinner(), postinstall(), spinnerFrames (+31 more)

### Community 9 - "_engine_with_scope"
Cohesion: 0.12
Nodes (8): _engine_with_scope(), _read(), _safe_active_scope(), _select(), _tag(), TestEvidenceKindAndProvenance, TestPhaseRegression, TestSelectSuccess

### Community 10 - "command"
Cohesion: 0.11
Nodes (19): description, template, command, checkpoint, eval, evolve, instinct-status, skill-create (+11 more)

### Community 11 - "agent"
Cohesion: 0.22
Nodes (9): agent, build, rust-build-resolver, description, mode, description, mode, prompt (+1 more)

### Community 12 - "edit"
Cohesion: 0.25
Nodes (8): kotlin-build-resolver, tools, description, mode, prompt, tools, changed-files, edit

### Community 13 - "write"
Cohesion: 0.33
Nodes (6): architect, description, mode, prompt, tools, write

### Community 14 - "bash"
Cohesion: 0.33
Nodes (6): harness-optimizer, description, mode, prompt, tools, bash

### Community 15 - "read"
Cohesion: 0.33
Nodes (6): loop-operator, description, mode, prompt, tools, read

### Community 16 - "build-error-resolver"
Cohesion: 0.40
Nodes (5): build-error-resolver, description, mode, prompt, tools

### Community 17 - "code-reviewer"
Cohesion: 0.40
Nodes (5): code-reviewer, description, mode, prompt, tools

### Community 18 - "cpp-build-resolver"
Cohesion: 0.40
Nodes (5): cpp-build-resolver, description, mode, prompt, tools

### Community 19 - "cpp-reviewer"
Cohesion: 0.40
Nodes (5): cpp-reviewer, description, mode, prompt, tools

### Community 20 - "database-reviewer"
Cohesion: 0.40
Nodes (5): database-reviewer, description, mode, prompt, tools

### Community 21 - "doc-updater"
Cohesion: 0.40
Nodes (5): doc-updater, description, mode, prompt, tools

### Community 22 - "docs-lookup"
Cohesion: 0.40
Nodes (5): docs-lookup, description, mode, prompt, tools

### Community 23 - "e2e-runner"
Cohesion: 0.40
Nodes (5): e2e-runner, description, mode, prompt, tools

### Community 24 - "go-build-resolver"
Cohesion: 0.40
Nodes (5): go-build-resolver, description, mode, prompt, tools

### Community 25 - "go-reviewer"
Cohesion: 0.40
Nodes (5): go-reviewer, description, mode, prompt, tools

### Community 26 - "java-build-resolver"
Cohesion: 0.40
Nodes (5): java-build-resolver, description, mode, prompt, tools

### Community 27 - "java-reviewer"
Cohesion: 0.40
Nodes (5): java-reviewer, description, mode, prompt, tools

### Community 28 - "kotlin-reviewer"
Cohesion: 0.40
Nodes (5): kotlin-reviewer, description, mode, prompt, tools

### Community 29 - "php-reviewer"
Cohesion: 0.40
Nodes (5): php-reviewer, description, mode, prompt, tools

### Community 30 - "planner"
Cohesion: 0.40
Nodes (5): planner, description, mode, prompt, tools

### Community 31 - "python-reviewer"
Cohesion: 0.40
Nodes (5): python-reviewer, description, mode, prompt, tools

### Community 32 - "refactor-cleaner"
Cohesion: 0.40
Nodes (5): refactor-cleaner, description, mode, prompt, tools

### Community 33 - "rust-reviewer"
Cohesion: 0.40
Nodes (5): rust-reviewer, description, mode, prompt, tools

### Community 34 - "security-reviewer"
Cohesion: 0.40
Nodes (5): security-reviewer, description, mode, prompt, tools

### Community 35 - "tdd-guide"
Cohesion: 0.40
Nodes (5): tdd-guide, description, mode, prompt, tools

### Community 36 - "build-fix"
Cohesion: 0.40
Nodes (5): agent, description, subtask, template, build-fix

### Community 37 - "code-review"
Cohesion: 0.40
Nodes (5): agent, description, subtask, template, code-review

### Community 38 - "e2e"
Cohesion: 0.40
Nodes (5): e2e, agent, description, subtask, template

### Community 39 - "go-build"
Cohesion: 0.40
Nodes (5): go-build, agent, description, subtask, template

### Community 40 - "go-review"
Cohesion: 0.40
Nodes (5): go-review, agent, description, subtask, template

### Community 41 - "go-test"
Cohesion: 0.40
Nodes (5): go-test, agent, description, subtask, template

### Community 42 - "orchestrate"
Cohesion: 0.40
Nodes (5): orchestrate, agent, description, subtask, template

### Community 43 - "plan"
Cohesion: 0.40
Nodes (5): plan, agent, description, subtask, template

### Community 44 - "refactor-clean"
Cohesion: 0.40
Nodes (5): refactor-clean, agent, description, subtask, template

### Community 45 - "security"
Cohesion: 0.40
Nodes (5): security, agent, description, subtask, template

### Community 46 - "tdd"
Cohesion: 0.40
Nodes (5): tdd, agent, description, subtask, template

### Community 47 - "test-coverage"
Cohesion: 0.40
Nodes (5): test-coverage, agent, description, subtask, template

### Community 48 - "update-codemaps"
Cohesion: 0.40
Nodes (5): update-codemaps, agent, description, subtask, template

### Community 49 - "update-docs"
Cohesion: 0.40
Nodes (5): update-docs, agent, description, subtask, template

### Community 50 - "TestPhaseRegression"
Cohesion: 0.06
Nodes (22): A Zigbee personal area network (PAN)., A device on a Zigbee mesh., ZigbeeNetwork, ZigbeeNode, simulator/rng.py  Deterministic, seedable random generator for reproducible scen, Thin wrapper so callers don't import `random` directly., SeededRNG, _ble() (+14 more)

### Community 51 - "build_scenario"
Cohesion: 0.07
Nodes (3): build_scenario(), Build a scenario by name. Raises KeyError if unknown., TestJoinSuccess

### Community 52 - "ECC - OpenCode Instructions"
Cohesion: 0.06
Nodes (35): After Writing/Editing Code, Agent Orchestration, API Response Format, Available Agents, Before Committing, Build Troubleshooting, Code Quality Checklist, Coding Style (+27 more)

### Community 53 - "Migration Guide: Claude Code to OpenCode"
Cohesion: 0.06
Nodes (31): 1. Install OpenCode, 2. Use the ECC OpenCode Configuration, 3. Run OpenCode, Agent Not Found, Agents, Available Agents, Available Commands, Best Practices (+23 more)

### Community 54 - "projects"
Cohesion: 0.67
Nodes (3): projects, description, template

### Community 55 - "Environment"
Cohesion: 0.07
Nodes (61): Entity, Observation, A logical wireless entity (network, device, tag, signal)., A single structured observation produced by a capability.      `evidence` is the, Environment, action_ble_connect(), action_ble_discover(), action_ble_inspect() (+53 more)

### Community 56 - "Bootstrap Agent - Initial Implementation"
Cohesion: 0.12
Nodes (16): ✅ Automatic Repair for Broken Installations, ✅ Automatic UTF-16LE Decoding, Bootstrap Agent - Initial Implementation, Changelog, CLI v0.1.0 — Cyberpunk TUI (Ink/React), Design Principles Maintained, Features Implemented, Features Implemented (+8 more)

### Community 57 - "test_phase283_ir.py"
Cohesion: 0.08
Nodes (35): ABC, capabilities/base.py  Capability, CapabilityProvider, and the simulator-backed p, capabilities/registry.py  Capability registry — the central source of truth for, Enum, core/confidence.py  Confidence levels for observations and hypotheses., core/events.py  JSONL event types emitted by the Python backend to the CLI. Thes, core/evidence.py  Structured evidence record — the durable output of a capabilit, core/mission.py  Mission, Action, Decision, and Run data structures.  These are (+27 more)

### Community 62 - "Eval Command"
Cohesion: 0.12
Nodes (15): Criterion Breakdown, Eval Command, Evaluation Framework, Evaluation Process, Evaluation Report, Evidence, Grader Types, Overall: [PASS/FAIL] (Score: X/100) (+7 more)

### Community 63 - "OpenCode ECC Plugin"
Cohesion: 0.12
Nodes (15): Agents (26), Commands (26), Configuration, Custom Tools, Features, Hook Event Mapping, Hook Runtime Controls, Installation (+7 more)

### Community 64 - "CLI_BEAUTIFY.md"
Cohesion: 0.13
Nodes (14): 1. Detects platform (linux-x64, macos-arm64, windows-x64, etc.), 2. Downloads correct binary from GitHub releases, 3. Extracts to bin/<platform>/suryafool[.exe], 4. Marks executable on Unix, Architecture, CLI_BEAUTIFY.md — Suryafool CLI UX & npm Distribution Spec, Color Theme — Cyberpunk, npm runs postinstall.js (+6 more)

### Community 65 - "Review Checklist"
Cohesion: 0.14
Nodes (13): Code Organization, Concurrency, Concurrency Issues, Error Handling, Error Handling Issues, Go Review Command, Idiomatic Go, Idiomatic Issues (+5 more)

### Community 66 - "Refactor Clean Command"
Cohesion: 0.14
Nodes (13): Before Removing, Consolidation Phase, Consolidation Strategies, Detection Phase, Identify Duplicates, Manual Checks, Refactor Clean Command, Removal Phase (+5 more)

### Community 67 - "Orchestrate Command"
Cohesion: 0.15
Nodes (12): Available Agents, Coordination Rules, Execution Plan Format, Fan-Out/Fan-In, Orchestrate Command, Orchestration Patterns, Parallel Execution, Phase 1: [Name] (+4 more)

### Community 68 - "Review Checklist"
Cohesion: 0.15
Nodes (12): Code Quality (MEDIUM), Concurrency (HIGH), CRITICAL Issues, Error Handling (HIGH), HIGH Issues, MEDIUM Issues, Ownership (HIGH), Report Format (+4 more)

### Community 69 - "Common Rust Errors"
Cohesion: 0.17
Nodes (11): Borrow Checker, Build Commands, Common Rust Errors, Fix Order, Lifetime Errors, Missing Import, Rust Build Command, Trait Not Implemented (+3 more)

### Community 70 - "Documentation Types"
Cohesion: 0.17
Nodes (11): API Documentation, Avoid, Code Comments, Documentation Quality, Documentation Types, Good Documentation, Guides, README.md (+3 more)

### Community 71 - "Verification Checklist"
Cohesion: 0.17
Nodes (11): Action Items, Build, Code Quality, Details, Security, Summary, Tests, Verification Checklist (+3 more)

### Community 72 - "AGENTS.md — Suryafool"
Cohesion: 0.06
Nodes (35): 1. LLM = diagnosis and interpretation only, 2. Scope Guardian is deterministic, 3. Provisioning Guardian mirrors this for bootstrap, 4. Passive is the default, 5. All agent actions are logged, 6. Platform detection is centralized, 7. Manifest is never LLM-generated, Agent Roster (+27 more)

### Community 73 - "E2E Command"
Cohesion: 0.18
Nodes (10): Artifacts to Capture, Best Practices, E2E Command, Report Format, Selectors, Test Categories, Test Isolation, Test Structure (+2 more)

### Community 74 - "Go Build Command"
Cohesion: 0.18
Nodes (10): Build Commands, Common Go Errors, Fix Order, Go Build Command, Import Errors, Type Errors, Undefined Errors, Verification (+2 more)

### Community 75 - "TDD Cycle for Go"
Cohesion: 0.18
Nodes (10): Go Test Command, Go Testing Commands, Step 1: Define Interface, Step 2: Table-Driven Tests, Step 3: Run Tests (RED), Step 4: Implement (GREEN), Step 5: Benchmark, TDD Cycle for Go (+2 more)

### Community 76 - "Instinct Export Command"
Cohesion: 0.18
Nodes (10): Export All, Export by Category, Export Format, Export High Confidence Only, Export Options, Export Report, Export to Specific Path, Instinct Export Command (+2 more)

### Community 77 - "Instinct Import Command"
Cohesion: 0.18
Nodes (10): Conflict Resolution, File Import, Import Format, Import Process, Import Report, Import Sources, Instinct Import Command, Team Share Import (+2 more)

### Community 78 - "TDD Cycle for Rust"
Cohesion: 0.18
Nodes (10): Rust Test Command, Rust Testing Commands, Step 1: Define Interface, Step 2: Write Tests, Step 3: Run Tests (RED), Step 4: Implement (GREEN), Step 5: Check Coverage, TDD Cycle for Rust (+2 more)

### Community 79 - "Setup Package Manager Command"
Cohesion: 0.18
Nodes (10): Configuration Options, Detection Order, Option 1: Environment Variable, Option 2: Project Config, Option 3: package.json, Option 4: Global Config, Setup Package Manager Command, Supported Package Managers (+2 more)

### Community 80 - "Your Task"
Cohesion: 0.18
Nodes (10): Coverage Requirements, Step 1: Define Interfaces (SCAFFOLD), Step 2: Write Failing Tests (RED), Step 3: Implement Minimal Code (GREEN), Step 4: Refactor (IMPROVE), Step 5: Check Coverage, TDD Command, TDD Cycle (MANDATORY) (+2 more)

### Community 81 - "Test Coverage Command"
Cohesion: 0.18
Nodes (10): Coverage Improvement Plan, Coverage Report Analysis, Coverage Targets, [Function/Component Name], Low Coverage Files, Summary, Test Coverage Command, Test Generation (+2 more)

### Community 82 - "Suryafool"
Cohesion: 0.08
Nodes (24): 1. Clone, 2. Create a virtual environment, 3. Install dependencies, 4. Configure environment, Check-only (no changes made), Contributing, Current capability surface (Phase 2.8), Cyberpunk CLI (`suryafool-cli/`) (+16 more)

### Community 83 - "CONTEXT.md — Suryafool (Root)"
Cohesion: 0.29
Nodes (7): Build Order, CONTEXT.md — Suryafool (Root), Implementation Status, Key Invariants, LLM Provider Stack, Planned Directory Layout (Full), Project Identity

### Community 84 - "Check Categories"
Cohesion: 0.20
Nodes (9): Best Practices (MEDIUM), Check Categories, Code Quality (HIGH), Code Review Command, Decision, Report Format, Security Issues (CRITICAL), Style (LOW) (+1 more)

### Community 85 - "Report Format"
Cohesion: 0.20
Nodes (9): Additional Checks, Critical Issues, High Priority, OWASP Top 10, Recommendations, Report Format, Security Checklist, Security Review Command (+1 more)

### Community 86 - "Update Codemaps Command"
Cohesion: 0.20
Nodes (9): Architecture Map, Codemap Format, Codemap Types, File Map, Generation Process, Module Map, [Module Name], Update Codemaps Command (+1 more)

### Community 87 - "Output Format"
Cohesion: 0.22
Nodes (8): Best Practices Applied, Instinct Format (for continuous-learning-v2), Learn Command, Mistakes to Avoid, Output Format, Patterns Discovered, Suggested Skill Updates, Your Task

### Community 88 - "Output Format"
Cohesion: 0.22
Nodes (8): Dependencies, Estimated Complexity, Implementation Phases, Output Format, Plan Command, Requirements Restatement, Risks, Your Task

### Community 89 - "Security Scan Command"
Cohesion: 0.22
Nodes (8): Arguments, CI Pattern, Deterministic Engine, Links, Output Contract, Review Checklist, Security Scan Command, Usage

### Community 90 - "Analysis Process"
Cohesion: 0.22
Nodes (8): Analysis Process, Output, Skill Create Command, Step 1: Gather Commit Data, Step 2: Identify Patterns, Step 3: Generate SKILL.md, Step 4: Generate Instincts, Your Task

### Community 91 - "PROJECT.md — Suryafool Complete Project Reference"
Cohesion: 0.06
Nodes (35): 10. MISSION DATA MODEL (Planned), 11. CONFIDENCE LEVELS (Mandatory), 12. BUILD & DEV COMMANDS, 13. KEY FILES QUICK REFERENCE, 14. ENVIRONMENT VARIABLES, 15. DEVELOPMENT PRINCIPLES (Ponytail), 16. KNOWN ISSUES & WORKAROUNDS, 17. NEXT MILESTONES (Priority Order) (+27 more)

### Community 92 - "Build Fix Command"
Cohesion: 0.25
Nodes (7): Approach, Build Fix Command, Common Error Fixes, DO:, DON'T:, Verification Steps, Your Task

### Community 93 - "Harness Audit Command"
Cohesion: 0.25
Nodes (7): Arguments, Checklist, Deterministic Engine, Example Result, Harness Audit Command, Output Contract, Usage

### Community 94 - "Checkpoint Command"
Cohesion: 0.33
Nodes (5): Checkpoint Command, Checkpoint Format, Checkpoint: [Timestamp], Usage with Verification Loop, Your Task

### Community 95 - "Loop Start Command"
Cohesion: 0.33
Nodes (5): Arguments, Flow, Loop Start Command, Required Safety Checks, Usage

### Community 96 - "Loop Status Command"
Cohesion: 0.33
Nodes (5): Arguments, Loop Status Command, Usage, Watch Mode, What to Report

### Community 97 - "Model Route Command"
Cohesion: 0.33
Nodes (5): Arguments, Model Route Command, Required Output, Routing Heuristic, Usage

### Community 98 - "Quality Gate Command"
Cohesion: 0.33
Nodes (5): Arguments, Notes, Pipeline, Quality Gate Command, Usage

### Community 99 - "Evolve Command"
Cohesion: 0.40
Nodes (4): Behavior Notes, Evolve Command, Supported Args (v2.1), Your Task

### Community 100 - "PRD.md"
Cohesion: 0.08
Nodes (23): 10. Agentic Security Laboratory, 11. Cross-Protocol Attack-Surface Graph, 12. Wireless Environment Graph, 13. Hardware Architecture, 14. Hardware Abstraction Layer, 15. Plugin Architecture, 17. MVP Feature Requirements, 18. Example Demonstration (+15 more)

### Community 101 - "Instinct Status Command"
Cohesion: 0.50
Nodes (3): Behavior Notes, Instinct Status Command, Your Task

### Community 102 - "_engine_with_scope"
Cohesion: 0.17
Nodes (7): _analyze(), _capture(), _engine_with_scope(), _sensitive_active_scope(), _signal(), TestEvidenceKindAndProvenance, _transmit()

### Community 103 - "9. Multi-Agent Architecture"
Cohesion: 0.15
Nodes (13): 9.10 Skeptic Agent, 9.11 Memory Agent, 9.12 Scope Guardian, 9.1 Mission Orchestrator, 9.2 Discovery Agent, 9.3 Signal Intelligence Agent, 9.4 Device Intelligence Agent, 9.5 Correlation Agent (+5 more)

### Community 106 - "instinct-export"
Cohesion: 0.67
Nodes (3): instinct-export, description, template

### Community 107 - "_engine_with_scope"
Cohesion: 0.08
Nodes (22): _device(), _engine_with_scope(), The SimulatorProvider from a sim-backed engine (for direct handler tests)., Active/inspection actions validate targets and args structurally â€” no crash., Valid known target, but not connected yet -> 'not connected' failure., A malformed action (missing address) under an ALLOWING scope must         produc, Cumulative grant STOPS at SAFE_ACTIVE: write (SENSITIVE_ACTIVE) is         still, write is catalogue SENSITIVE_ACTIVE; a request claiming SAFE_ACTIVE         is r (+14 more)

### Community 108 - "Capability"
Cohesion: 0.05
Nodes (27): Capability, Any, True iff every capability key in `requires` is present in the         observed-c, Execute the action and return a structured Observation., Backend that delegates everything to the wireless simulator., Describes a single capability action.      Phase 2.7.1 metadata (opt-in, all wit, SimulatorProvider, CapabilityRegistry (+19 more)

### Community 111 - "IrSignal"
Cohesion: 0.32
Nodes (3): IrSignal, A captured infrared burst. `protocol` is the decode target of a future     `infr, _ir_protocol_hint()

### Community 112 - "`llm.py` — LLM Factory + Rate Limiter"
Cohesion: 0.18
Nodes (10): CONTEXT.md — core/, Files, `llm.py` — LLM Factory + Rate Limiter, LLMResult, Provider Selection, Public API, Purpose, Rate Limiter (+2 more)

### Community 114 - "CONTEXT.md — bootstrap/"
Cohesion: 0.20
Nodes (10): Agent Loop (implemented in `agent.py`), CONTEXT.md — bootstrap/, Dependencies (Python packages), Elevation Types, Files, Invocation, LLM Responsibilities in This Module, Manifest Schema (+2 more)

### Community 116 - "dependencies"
Cohesion: 0.11
Nodes (19): adm-zip, chalk, fullscreen-ink, gradient-string, ink, ink-text-input, @inkjs/ui, @pppp606/ink-chart (+11 more)

### Community 117 - "package.json"
Cohesion: 0.17
Nodes (11): author, bin, suryafool, description, engines, node, license, main (+3 more)

### Community 118 - "keywords"
Cohesion: 0.33
Nodes (6): agentic, cli, cyberpunk, security, wireless, keywords

### Community 119 - "scripts"
Cohesion: 0.40
Nodes (5): scripts, build, dev, postinstall, prepare

### Community 120 - "Suryafool — Bootstrap / Environment Agent"
Cohesion: 0.22
Nodes (9): 1. Purpose, 2. Critical design rule, 3. Architecture, 4. Dependency manifest, 5. Agent responsibilities (what the LLM actually does), 6. Provisioning Guardian, 7. Tool interface (for implementation), 8. Where this lives (+1 more)

### Community 121 - "8. Mission Types"
Cohesion: 0.22
Nodes (9): 8.1 Explore, 8.2 Investigate, 8.3 Compare, 8.4 Understand, 8.5 Diagnose, 8.6 Automate, 8.7 Security Research, 8.8 Autonomous Penetration Testing (+1 more)

### Community 122 - "default_registry"
Cohesion: 0.12
Nodes (9): default_registry(), _null_env(), Return a registry pre-loaded with default capabilities and the     simulator pro, ir_workflow_plan(), nfc_workflow_plan(), Phase 2.8.1 deterministic plan: a complete stateful Sub-GHz/RF     capture lifec, Phase 2.8.2 deterministic plan: complete stateful NFC/RFID scan ->     select ->, Phase 2.8.3 deterministic plan: complete stateful Infrared     capture -> analyz (+1 more)

### Community 123 - "bootstrap-agent-not-installed.md"
Cohesion: 0.25
Nodes (7): Current Handling, Description, Error Message, Notes, Related Files, Root Cause, Workaround for Development

### Community 124 - "Run"
Cohesion: 0.08
Nodes (109): EvidenceRecord, Any, A single piece of evidence captured by a capability action.      Provenance fiel, ActionRisk, AuthorizationScope, PolicyDecisionKind, Enum, str (+101 more)

### Community 125 - "CONTEXT.md — docs/"
Cohesion: 0.29
Nodes (6): [`ARCHITECTURE.md`](ARCHITECTURE.md), CONTEXT.md — docs/, Files, [`PRD.md`](PRD.md), Purpose, Rules for This Directory

### Community 126 - "test_phase284_zigbee.py"
Cohesion: 0.12
Nodes (16): Path, Return the directory where run artifacts are stored., run_dir(), runs_root(), Phase 2.8.4 deterministic plan: complete stateful Zigbee mesh lifecycle     over, zigbee_workflow_plan(), _engine_with_scope(), _inspect() (+8 more)

### Community 127 - "_engine_with_scope"
Cohesion: 0.16
Nodes (5): _engine_with_scope(), _handshake_req(), _safe_active_scope(), _sensitive_active_scope(), TestJsonlAndHtmlSmoke

### Community 128 - "16. MVP"
Cohesion: 0.40
Nodes (5): 16. MVP, 1. Agents can perceive the wireless environment., 2. Agents can autonomously investigate., 3. Agents can safely interact with authorized targets., 4. Agents can perform an autonomous authorized security investigation.

### Community 131 - "BleDevice"
Cohesion: 0.10
Nodes (16): BleDevice, Original BleDevice positional constructor still builds cleanly â€”         the P, Phase 2.7.1 spec: 'Policy must remain before execution. Rejected     actions mus, Sanity: BleDevice still constructs with original positional args         (Phase, TestBleDeviceNewFields, TestContractMetadataConsumption, TestDeterminism, TestGattWriteAuthorizationGate (+8 more)

### Community 134 - "_tmp_runs_dir"
Cohesion: 0.67
Nodes (3): fixture, Isolate run artifacts under a temp dir for every test., _tmp_runs_dir()

### Community 135 - "performed_capability_keys"
Cohesion: 0.12
Nodes (5): performed_capability_keys(), Return the set of capability keys that have been performed on `env`,     derived, wifi.discovery.discover is observation-only: the simulator's passive         act, TestPerformedCapabilityKeys, Under a PASSIVE-only default scope, capture.handshake and         capture.pmkid

### Community 138 - "TestPairHandler"
Cohesion: 0.21
Nodes (7): action_ble_gatt_pair(), Direct simulator handler calls â€” bypass the engine/policy gate so we     isola, Even if you somehow reached a non-connectable device over BLE,         pairing i, Per-target prereq: ble.discovery.connect must have run on THIS         address f, The happy path: link-layer connect (Phase 2.7) establishes         b.connected=T, Repeated pair calls on an already-paired device succeed without         crashing, TestPairHandler

### Community 139 - "_engine_with_scope"
Cohesion: 0.07
Nodes (14): CapabilityDecision, Any, Result of capability resolution — which provider handles it., PASSIVE only — the conservative default. Equivalent to the         historical Ph, Any, A run.json blob produced before Phase 2.6 (no 'authorization' key,         no 'a, _connect_action(), _engine_with_scope() (+6 more)

### Community 142 - "ActionRequest"
Cohesion: 0.06
Nodes (47): CapabilityProvider, Backend that knows how to execute a set of capability actions., Return True if this provider can execute (capability, action)., ActionRecord, ActionRequest, A request from the orchestrator to execute a capability action., A fully resolved action — request, decision, outcome., PolicyContext (+39 more)

### Community 143 - "_engine_with_scope"
Cohesion: 0.11
Nodes (7): _analyze(), _capture(), _engine_with_scope(), _safe_active_scope(), _signal(), _spectrum(), TestPhaseRegression

### Community 144 - "TestGattWriteHandler"
Cohesion: 0.21
Nodes (6): action_ble_gatt_write(), Per-target prereq: ble.gatt.pair must have run on THIS address         first. A, Even when paired, writing to a characteristic the GATT service         table doe, The happy path: connect (link) -> pair (session) -> secure write.         b.secu, Mirror Phase 2.7's ble.discovery.write semantics: any non-None         value is, TestGattWriteHandler

### Community 145 - "phase2.py"
Cohesion: 0.14
Nodes (25): ArgumentParser, available_providers(), Names of providers the registry factory knows how to construct., _authorization_status_line(), build_parser(), _build_run(), cmd_capabilities(), cmd_providers() (+17 more)

### Community 146 - "run_full_agent"
Cohesion: 0.12
Nodes (22): deps_satisfied(), Full doctor run with hybrid remediation:       1. Check all dependencies., run_full_agent(), Flatten a raw manifest entry into a platform-specific dict by resolving     any, Resolve a manifest field that may be a plain value (str / list) or a     dict ke, resolve_entry(), _resolve_field(), check_and_prompt() (+14 more)

### Community 147 - "_engine_with_scope"
Cohesion: 0.17
Nodes (6): _engine_with_scope(), _pmkid_req(), Execute the per-target prerequisite (handshake) then pmkid through the     engin, _run_handshake_then_pmkid(), _safe_active_scope(), _sensitive_active_scope()

### Community 148 - "agent.py"
Cohesion: 0.14
Nodes (17): load_manifest(), main(), print_results_table(), propose_remediation_llm(), bootstrap/agent.py  Bootstrap / Environment Agent entry point.  Usage:     pytho, Print a Rich status table. Returns True if all checks passed., Read-only mode: run checks, print results, exit. No system changes., Tracks how a dependency was resolved. (+9 more)

### Community 149 - "animations/index.js"
Cohesion: 0.25
Nodes (9): glitchLines(), glitchText(), MatrixRain, neonFlicker(), neonPulse(), typewrite(), typewriteLines(), typewriteWithCursor() (+1 more)

### Community 151 - "ecc-hooks.ts"
Cohesion: 0.20
Nodes (11): metadata, ECCHooksPlugin(), ECCHooksPluginFn, FileEvent, getECCVersion(), PermissionEvent, TodoEvent, ToolArgs (+3 more)

### Community 152 - "TabPanel.js"
Cohesion: 0.21
Nodes (13): AgentsBoard(), CapabilitiesView(), ConfigView(), Console(), EvidenceFeed(), formatEvidenceLine(), ModalLayer(), ScanDashboard() (+5 more)

### Community 153 - "test_phase279_integration.py"
Cohesion: 0.10
Nodes (21): ble_gatt_workflow_plan(), Phase 2.7.2 deterministic plan: a complete Wi-Fi capture lifecycle     over the, Phase 2.7.3 deterministic plan: a complete stateful BLE GATT     lifecycle over, wifi_capture_plan(), Phase 2.7.2 wifi_capture_plan is intact â€” the workflow added in         this s, _ble_discover(), _ble_inspect(), _connect() (+13 more)

### Community 155 - "security-audit.ts"
Cohesion: 0.29
Nodes (8): AuditCheck, AuditResults, NOTE: This tool SCANS for security anti-patterns - it does not introduce them., scanCodeSecurity(), scanDirectory(), scanFile(), scanForSecrets(), securityAuditTool

### Community 156 - "dependency-analyzer.ts"
Cohesion: 0.25
Nodes (3): AnalysisResult, dependencyAnalyzerTool, DependencyInfo

### Community 157 - "CONTEXT.md — policy/"
Cohesion: 0.25
Nodes (7): CONTEXT.md — policy/, Default rules, Extending, Files, Public API, Purpose, Rules

### Community 158 - "provisioning_guardian.py"
Cohesion: 0.43
Nodes (6): ElevationType, _is_windows_admin_required(), _is_wsl_sudo_required(), Enum, str, bootstrap/provisioning_guardian.py  Elevation gate for the Bootstrap Agent.  Ele

### Community 159 - "CONTEXT.md — capabilities/"
Cohesion: 0.12
Nodes (17): Adding a real hardware backend later, CONTEXT.md — capabilities/, Files, Phase 2.7.1 — capability contract metadata, Phase 2.7.1 regression, Phase 2.7.2 regression, Phase 2.7.2 — stateful Wi-Fi capture entries, Phase 2.7.3 regression (+9 more)

### Community 160 - "CONTEXT.md — cli/"
Cohesion: 0.25
Nodes (7): Authorization (Phase 2.6), CLI usage (from repo root), CONTEXT.md — cli/, Files, JSONL contract, Purpose, Rules

### Community 161 - "CONTEXT.md — engine/"
Cohesion: 0.29
Nodes (6): Artifacts (per run), CONTEXT.md — engine/, Files, Flow, Purpose, Rules

### Community 162 - "CONTEXT.md — simulator/"
Cohesion: 0.12
Nodes (16): `action_ir_analyze` (new, SAFE_ACTIVE, produces `ir_analysis` evidence), `action_ir_capture` (new, PASSIVE — observational, no evidence), `action_ir_transmit` (new, SENSITIVE_ACTIVE, produces `ir_transmit` evidence), `action_subghz_analyze` (upgraded — `produces_evidence` False→True), `action_subghz_capture_signal` (new, SAFE_ACTIVE, produces `subghz_capture` evidence), Action surface, CONTEXT.md — simulator/, Files (+8 more)

### Community 163 - "_safe_active_scope"
Cohesion: 0.22
Nodes (5): request.risk=PASSIVE but cap.risk=SAFE_ACTIVE â€” caller         self-disclosed, SAFE_ACTIVE scope does NOT include SENSITIVE_ACTIVE, so the         secure write, Under SAFE_ACTIVE scope, connect+pair ALLOW but ble.gatt.write         REJECTs a, ble.gatt.pair declares requires=('ble.discovery.connect',).         In a fresh l, _safe_active_scope()

### Community 164 - "format-code.ts"
Cohesion: 0.33
Nodes (3): formatCodeTool, FormatResult, Formatter

### Community 165 - "lint-check.ts"
Cohesion: 0.33
Nodes (3): lintCheckTool, Linter, LintResult

### Community 166 - "CONTEXT.md — reports/"
Cohesion: 0.33
Nodes (5): CONTEXT.md — reports/, Files, Purpose, Rules, Sections

### Community 167 - "Event"
Cohesion: 0.32
Nodes (5): emit(), Event, Any, Emit a JSONL event to a writable stream. Safe no-op if stream is None., Any

### Community 169 - "test_phase2_cmds.cjs"
Cohesion: 0.40
Nodes (3): path, repoRoot, { spawn }

### Community 170 - "test_phase2_wiring.cjs"
Cohesion: 0.40
Nodes (4): path, proc, repoRoot, { spawn }

### Community 171 - "setup-pm"
Cohesion: 0.67
Nodes (3): setup-pm, description, template

### Community 179 - "default_exploration_plan"
Cohesion: 0.25
Nodes (3): default_exploration_plan(), A simple, deterministic plan: discover across all four protocols.      Future ph, The original simulator exploration plan is intact: 4 PASSIVE actions.

### Community 180 - "Confidence"
Cohesion: 0.11
Nodes (12): Confidence, str, _FakeTmpPath, make_engine(), A caller declaring risk=RESTRICTED on a catalogue-PASSIVE action         (wifi.d, Selecting scenario='home' (or 'lab') no longer grants any risk tier.         nfc, Callers cannot claim a lower risk than the catalogue declares.          nfc.disc, XSS regression: adversarial strings in run/entity data must be escaped. (+4 more)

### Community 181 - "reducer.js"
Cohesion: 0.47
Nodes (4): StateProvider(), handlers, initialState, reducer()

### Community 183 - "app.js"
Cohesion: 0.18
Nodes (11): BLOOM_FRAMES, runBloom(), App(), AppContent(), PHASE2_COMMANDS, CommandBar(), Footer(), Glyph() (+3 more)

### Community 186 - "_engine_with_scope"
Cohesion: 0.14
Nodes (8): _engine_with_scope(), request.risk=PASSIVE but cap.risk=SAFE_ACTIVE -> the caller         self-disclos, request.risk=SENSITIVE_ACTIVE but cap.risk=SAFE_ACTIVE -> the         caller sel, SAFE_ACTIVE scope does NOT include SENSITIVE_ACTIVE, so pmkid is         REJECTe, Run discover -> inspect (initial) -> handshake -> pmkid ->         inspect (fina, Build a simulator-backed RunEngine authorized with `scope`     (default PASSIVE), _safe_active_scope(), _sensitive_active_scope()

### Community 187 - "_engine_with_scope"
Cohesion: 0.11
Nodes (12): _device(), _engine_with_scope(), Run the ble_gatt_workflow_plan under SENSITIVE_ACTIVE scope and         confirm, Build a simulator-backed RunEngine authorized with `scope` (default     PASSIVE), request.risk=SENSITIVE_ACTIVE but cap.risk=SAFE_ACTIVE â€” caller         self-d, Under a PASSIVE-only default scope, all three active steps (connect,         pai, The cumulative tier boundary is observed precisely: SAFE_ACTIVE         scope pe, Run the full chain: discover -> inspect (initial) -> connect ->         pair -> (+4 more)

### Community 190 - "instinct-import"
Cohesion: 0.67
Nodes (3): instinct-import, description, template

### Community 196 - "_run_all"
Cohesion: 0.40
Nodes (3): Path, Run every test_* method in every Test* class without pytest.      Exits 1 on the, _run_all()

### Community 197 - "opencode.json"
Cohesion: 0.18
Nodes (10): default_agent, permission, mcp_*, plugin, $schema, skills, paths, .opencode/plugins/graphify.js (+2 more)

### Community 199 - "TestEntitySubstrate"
Cohesion: 0.23
Nodes (5): EthernetHost, A host observed on a wired Ethernet segment., A USB device present on the host's bus., UsbDevice, TestEntitySubstrate

### Community 200 - "learn"
Cohesion: 0.67
Nodes (3): learn, description, template

### Community 202 - "action_wifi_capture_handshake"
Cohesion: 0.28
Nodes (4): action_wifi_capture_handshake(), _device_by_addr(), Direct simulator handler calls â€” bypass the engine/policy gate so we     isola, TestHandshakeHandler

### Community 205 - "AGENTS.md"
Cohesion: 0.22
Nodes (5): CONTEXT.md — tests/, Files, Purpose, Rules, Running

### Community 208 - ".with_cumulative_tier"
Cohesion: 0.13
Nodes (11): _build_authorization(), Translate the CLI --allow-risk + --authorization-label pair into an     Authoriz, Allowed set = all tiers at or below `max_tier` severity-wise.         This is wh, _engine_with_scope(), ble.discovery.write declares requires=('ble.discovery.connect',).         In a f, After running the active_inspection plan under SENSITIVE_ACTIVE         scope, e, A successful PASSIVE action execution does NOT cause         performed_capabilit, Under a SAFE_ACTIVE-only scope connect ALLOWs (mutates env notes) but         wr (+3 more)

### Community 210 - "promote"
Cohesion: 0.67
Nodes (3): promote, description, template

### Community 211 - "_tmp_runs_dir"
Cohesion: 0.67
Nodes (3): fixture, Isolate run artifacts under a temp dir for every test., _tmp_runs_dir()

### Community 213 - "_tmp_runs_dir"
Cohesion: 0.67
Nodes (3): fixture, Isolate run artifacts under a temp dir for every test., _tmp_runs_dir()

### Community 214 - "test_phase273_ble_gatt.py"
Cohesion: 0.13
Nodes (9): active_inspection_plan(), Phase 2.7 deterministic plan: a complete active BLE lifecycle over the     `lab`, _connect_target(), fixture, tests/test_phase273_ble_gatt.py  Phase 2.7.3 regression suite â€” stateful BLE G, Run the legacy Phase 2.7 ble.discovery.connect so later gatt tests     start fro, Isolate run artifacts under a temp dir for every test., Phase 2.7 active_inspection_plan is intact â€” the workflow added         in thi (+1 more)

### Community 217 - "_tmp_runs_dir"
Cohesion: 0.67
Nodes (3): fixture, Isolate run artifacts under a temp dir for every test., _tmp_runs_dir()

### Community 221 - "TestRegressionContract"
Cohesion: 0.25
Nodes (4): Phase 2.7/2.7.2/2.7.3/2.8.1/2.8.2 catalogue regression — the four         origin, Every catalogue entry serializes to JSON cleanly (the run record         and rep, Phase 2.6 invariant preserved: authoritative_risk is resolved on         the Act, TestRegressionContract

### Community 233 - "_tmp_runs_dir"
Cohesion: 0.67
Nodes (3): fixture, Isolate run artifacts under a temp dir for every test., _tmp_runs_dir()

## Knowledge Gaps
- **817 isolated node(s):** `metadata`, `$schema`, `default_agent`, `AGENTS.md`, `CONTRIBUTING.md` (+812 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **35 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `ActionRequest` connect `ActionRequest` to `TestRegression`, `TestContractAudit`, `BleDevice`, `TestPhaseRegression`, `performed_capability_keys`, `_engine_with_scope`, `TestPairHandler`, `_engine_with_scope`, `TestJoinFailure`, `_engine_with_scope`, `TestGattWriteHandler`, `_engine_with_scope`, `TestContractFields`, `test_phase279_integration.py`, `_safe_active_scope`, `TestPhaseRegression`, `default_exploration_plan`, `Confidence`, `build_scenario`, `Environment`, `TestFailedCaptureNoFalsePositive`, `test_phase283_ir.py`, `_engine_with_scope`, `_engine_with_scope`, `TestRegression`, `TestNewDomainRegistration`, `TestDeterminism`, `TestFailedCaptureNoEvidence`, `TestRegression`, `TestNewCapabilityMetadata`, `TestPhase27FreezeRegression`, `TestEntitySubstrate`, `action_wifi_capture_handshake`, `.with_cumulative_tier`, `test_phase273_ble_gatt.py`, `TestRegressionContract`, `_engine_with_scope`, `_engine_with_scope`, `Capability`, `TestUnsupportedCapabilityBehavior`, `default_registry`, `Run`, `test_phase284_zigbee.py`, `_engine_with_scope`?**
  _High betweenness centrality (0.068) - this node is a cross-community bridge._
- **Why does `Rule` connect `Capability` to `test_phase283_ir.py`, `run_full_agent`, `Run`, `ActionRequest`?**
  _High betweenness centrality (0.043) - this node is a cross-community bridge._
- **Why does `run_full_agent()` connect `run_full_agent` to `checks.py`, `Capability`, `agent.py`?**
  _High betweenness centrality (0.043) - this node is a cross-community bridge._
- **Are the 168 inferred relationships involving `ActionRequest` (e.g. with `Confidence` and `EvidenceRecord`) actually correct?**
  _`ActionRequest` has 168 INFERRED edges - model-reasoned connections that need verification._
- **Are the 161 inferred relationships involving `Run` (e.g. with `Confidence` and `EvidenceRecord`) actually correct?**
  _`Run` has 161 INFERRED edges - model-reasoned connections that need verification._
- **Are the 159 inferred relationships involving `RunLogger` (e.g. with `Event` and `Run`) actually correct?**
  _`RunLogger` has 159 INFERRED edges - model-reasoned connections that need verification._
- **Are the 165 inferred relationships involving `RunEngine` (e.g. with `CapabilityRegistry` and `ActionRecord`) actually correct?**
  _`RunEngine` has 165 INFERRED edges - model-reasoned connections that need verification._