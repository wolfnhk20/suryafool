# Graph Report - F:\projects\suryafool  (2026-07-28)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 622 nodes · 902 edges · 62 communities (61 shown, 1 thin omitted)
- Extraction: 100% EXTRACTED · 0% INFERRED · 0% AMBIGUOUS · INFERRED: 4 edges (avg confidence: 0.65)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `048d1589`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- Community 0
- Community 1
- Community 2
- Community 3
- Community 4
- Community 5
- Community 6
- Community 7
- Community 8
- Community 9
- Community 10
- Community 11
- Community 12
- Community 13
- Community 14
- Community 15
- Community 16
- Community 17
- Community 18
- Community 19
- Community 20
- Community 21
- Community 22
- Community 23
- Community 24
- Community 25
- Community 26
- Community 27
- Community 28
- Community 29
- Community 30
- Community 31
- Community 32
- Community 33
- Community 34
- Community 35
- Community 36
- Community 37
- Community 38
- Community 39
- Community 40
- Community 41
- Community 42
- Community 43
- Community 44
- Community 45
- Community 46
- Community 47
- Community 48
- Community 49
- Community 50
- Community 51
- Community 52
- Community 53
- Community 54
- Community 55
- Community 56
- Community 57
- Community 60

## God Nodes (most connected - your core abstractions)
1. `agent` - 27 edges
2. `command` - 27 edges
3. `edit` - 26 edges
4. `bash` - 26 edges
5. `read` - 26 edges
6. `write` - 24 edges
7. `compilerOptions` - 18 edges
8. `instructions` - 15 edges
9. `resolve_entry()` - 15 edges
10. `run_full_agent()` - 14 edges

## Surprising Connections (you probably didn't know these)
- `RemediationRecord` --uses--> `LLMResult`  [INFERRED]
  bootstrap/agent.py → core/llm.py
- `propose_remediation_llm()` --calls--> `llm_call()`  [EXTRACTED]
  bootstrap/agent.py → core/llm.py
- `main()` --calls--> `check_all()`  [EXTRACTED]
  check_env.py → bootstrap/checks.py
- `main()` --calls--> `assert_supported()`  [EXTRACTED]
  check_env.py → bootstrap/platform.py
- `CheckResult` --uses--> `OS`  [INFERRED]
  bootstrap/checks.py → bootstrap/platform.py

## Import Cycles
- None detected.

## Communities (62 total, 1 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.05
Nodes (68): deps_satisfied(), load_manifest(), main(), print_results_table(), propose_remediation_llm(), bootstrap/agent.py  Bootstrap / Environment Agent entry point.  Usage:     pytho, Print a Rich status table. Returns True if all checks passed., Read-only mode: run checks, print results, exit. No system changes. (+60 more)

### Community 1 - "Community 1"
Cohesion: 0.06
Nodes (24): cli, main(), AnimationEngine, glitchLines(), glitchText(), MatrixRain, neonFlicker(), neonPulse() (+16 more)

### Community 2 - "Community 2"
Cohesion: 0.05
Nodes (40): chalk, esbuild, gradient-string, ink, ink-box, ink-gradient, ink-text-input, meow (+32 more)

### Community 3 - "Community 3"
Cohesion: 0.08
Nodes (25): metadata, ECCHooksPlugin(), ECCHooksPluginFn, FileEvent, getECCVersion(), PermissionEvent, TodoEvent, ToolArgs (+17 more)

### Community 4 - "Community 4"
Cohesion: 0.06
Nodes (19): checkCoverageTool, CoverageResult, CoverageSummary, formatCodeTool, FormatResult, Formatter, gitSummaryTool, lintCheckTool (+11 more)

### Community 5 - "Community 5"
Cohesion: 0.10
Nodes (12): _build_default_limiter(), _build_openai_compatible(), get_llm(), get_rate_limiter(), ProviderConfig, _RateLimitedLLM, core/llm.py  LLM factory with OpenRouter (primary) + OpenCode Zen (fallback) for, Wrapper around a LangChain chat model with rate limiting. (+4 more)

### Community 6 - "Community 6"
Cohesion: 0.07
Nodes (27): compilerOptions, declaration, declarationMap, esModuleInterop, forceConsistentCasingInFileNames, isolatedModules, lib, module (+19 more)

### Community 7 - "Community 7"
Cohesion: 0.08
Nodes (24): default_agent, instructions, permission, mcp_*, plugin, $schema, skills, paths (+16 more)

### Community 8 - "Community 8"
Cohesion: 0.13
Nodes (11): adm-zip, adm-zip, BinaryManager, chalk, postinstall(), spinnerFrames, startSpinner(), stopSpinner() (+3 more)

### Community 9 - "Community 9"
Cohesion: 0.15
Nodes (7): CONFIG_DIR, CONFIG_FILE, DEFAULT_CONFIG, getConfig(), loadConfig(), saveConfig(), setConfig()

### Community 10 - "Community 10"
Cohesion: 0.15
Nodes (13): description, template, command, checkpoint, instinct-export, instinct-status, promote, description (+5 more)

### Community 11 - "Community 11"
Cohesion: 0.22
Nodes (9): agent, build, rust-build-resolver, description, mode, description, mode, prompt (+1 more)

### Community 12 - "Community 12"
Cohesion: 0.25
Nodes (8): kotlin-build-resolver, tools, description, mode, prompt, tools, changed-files, edit

### Community 13 - "Community 13"
Cohesion: 0.33
Nodes (6): architect, description, mode, prompt, tools, write

### Community 14 - "Community 14"
Cohesion: 0.33
Nodes (6): harness-optimizer, description, mode, prompt, tools, bash

### Community 15 - "Community 15"
Cohesion: 0.33
Nodes (6): loop-operator, description, mode, prompt, tools, read

### Community 16 - "Community 16"
Cohesion: 0.40
Nodes (5): build-error-resolver, description, mode, prompt, tools

### Community 17 - "Community 17"
Cohesion: 0.40
Nodes (5): code-reviewer, description, mode, prompt, tools

### Community 18 - "Community 18"
Cohesion: 0.40
Nodes (5): cpp-build-resolver, description, mode, prompt, tools

### Community 19 - "Community 19"
Cohesion: 0.40
Nodes (5): cpp-reviewer, description, mode, prompt, tools

### Community 20 - "Community 20"
Cohesion: 0.40
Nodes (5): database-reviewer, description, mode, prompt, tools

### Community 21 - "Community 21"
Cohesion: 0.40
Nodes (5): doc-updater, description, mode, prompt, tools

### Community 22 - "Community 22"
Cohesion: 0.40
Nodes (5): docs-lookup, description, mode, prompt, tools

### Community 23 - "Community 23"
Cohesion: 0.40
Nodes (5): e2e-runner, description, mode, prompt, tools

### Community 24 - "Community 24"
Cohesion: 0.40
Nodes (5): go-build-resolver, description, mode, prompt, tools

### Community 25 - "Community 25"
Cohesion: 0.40
Nodes (5): go-reviewer, description, mode, prompt, tools

### Community 26 - "Community 26"
Cohesion: 0.40
Nodes (5): java-build-resolver, description, mode, prompt, tools

### Community 27 - "Community 27"
Cohesion: 0.40
Nodes (5): java-reviewer, description, mode, prompt, tools

### Community 28 - "Community 28"
Cohesion: 0.40
Nodes (5): kotlin-reviewer, description, mode, prompt, tools

### Community 29 - "Community 29"
Cohesion: 0.40
Nodes (5): php-reviewer, description, mode, prompt, tools

### Community 30 - "Community 30"
Cohesion: 0.40
Nodes (5): planner, description, mode, prompt, tools

### Community 31 - "Community 31"
Cohesion: 0.40
Nodes (5): python-reviewer, description, mode, prompt, tools

### Community 32 - "Community 32"
Cohesion: 0.40
Nodes (5): refactor-cleaner, description, mode, prompt, tools

### Community 33 - "Community 33"
Cohesion: 0.40
Nodes (5): rust-reviewer, description, mode, prompt, tools

### Community 34 - "Community 34"
Cohesion: 0.40
Nodes (5): security-reviewer, description, mode, prompt, tools

### Community 35 - "Community 35"
Cohesion: 0.40
Nodes (5): tdd-guide, description, mode, prompt, tools

### Community 36 - "Community 36"
Cohesion: 0.40
Nodes (5): agent, description, subtask, template, build-fix

### Community 37 - "Community 37"
Cohesion: 0.40
Nodes (5): agent, description, subtask, template, code-review

### Community 38 - "Community 38"
Cohesion: 0.40
Nodes (5): e2e, agent, description, subtask, template

### Community 39 - "Community 39"
Cohesion: 0.40
Nodes (5): go-build, agent, description, subtask, template

### Community 40 - "Community 40"
Cohesion: 0.40
Nodes (5): go-review, agent, description, subtask, template

### Community 41 - "Community 41"
Cohesion: 0.40
Nodes (5): go-test, agent, description, subtask, template

### Community 42 - "Community 42"
Cohesion: 0.40
Nodes (5): orchestrate, agent, description, subtask, template

### Community 43 - "Community 43"
Cohesion: 0.40
Nodes (5): plan, agent, description, subtask, template

### Community 44 - "Community 44"
Cohesion: 0.40
Nodes (5): refactor-clean, agent, description, subtask, template

### Community 45 - "Community 45"
Cohesion: 0.40
Nodes (5): security, agent, description, subtask, template

### Community 46 - "Community 46"
Cohesion: 0.40
Nodes (5): tdd, agent, description, subtask, template

### Community 47 - "Community 47"
Cohesion: 0.40
Nodes (5): test-coverage, agent, description, subtask, template

### Community 48 - "Community 48"
Cohesion: 0.40
Nodes (5): update-codemaps, agent, description, subtask, template

### Community 49 - "Community 49"
Cohesion: 0.40
Nodes (5): update-docs, agent, description, subtask, template

### Community 50 - "Community 50"
Cohesion: 0.67
Nodes (3): eval, description, template

### Community 51 - "Community 51"
Cohesion: 0.67
Nodes (3): evolve, description, template

### Community 52 - "Community 52"
Cohesion: 0.67
Nodes (3): instinct-import, description, template

### Community 53 - "Community 53"
Cohesion: 0.67
Nodes (3): learn, description, template

### Community 54 - "Community 54"
Cohesion: 0.67
Nodes (3): projects, description, template

### Community 55 - "Community 55"
Cohesion: 0.67
Nodes (3): setup-pm, description, template

### Community 56 - "Community 56"
Cohesion: 0.67
Nodes (3): skill-create, description, template

### Community 57 - "Community 57"
Cohesion: 0.67
Nodes (3): verify, description, template

## Knowledge Gaps
- **264 isolated node(s):** `metadata`, `$schema`, `default_agent`, `AGENTS.md`, `CONTRIBUTING.md` (+259 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **1 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `agent` connect `Community 11` to `Community 7`, `Community 12`, `Community 13`, `Community 14`, `Community 15`, `Community 16`, `Community 17`, `Community 18`, `Community 19`, `Community 20`, `Community 21`, `Community 22`, `Community 23`, `Community 24`, `Community 25`, `Community 26`, `Community 27`, `Community 28`, `Community 29`, `Community 30`, `Community 31`, `Community 32`, `Community 33`, `Community 34`, `Community 35`?**
  _High betweenness centrality (0.121) - this node is a cross-community bridge._
- **Why does `command` connect `Community 10` to `Community 7`, `Community 36`, `Community 37`, `Community 38`, `Community 39`, `Community 40`, `Community 41`, `Community 42`, `Community 43`, `Community 44`, `Community 45`, `Community 46`, `Community 47`, `Community 48`, `Community 49`, `Community 50`, `Community 51`, `Community 52`, `Community 53`, `Community 54`, `Community 55`, `Community 56`, `Community 57`?**
  _High betweenness centrality (0.116) - this node is a cross-community bridge._
- **Why does `BinaryManager` connect `Community 8` to `Community 1`?**
  _High betweenness centrality (0.021) - this node is a cross-community bridge._
- **What connects `metadata`, `$schema`, `default_agent` to the rest of the system?**
  _264 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Community 0` be split into smaller, more focused modules?**
  _Cohesion score 0.051929824561403506 - nodes in this community are weakly interconnected._
- **Should `Community 1` be split into smaller, more focused modules?**
  _Cohesion score 0.061018437225636525 - nodes in this community are weakly interconnected._
- **Should `Community 2` be split into smaller, more focused modules?**
  _Cohesion score 0.04878048780487805 - nodes in this community are weakly interconnected._