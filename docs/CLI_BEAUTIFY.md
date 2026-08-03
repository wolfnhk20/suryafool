# CLI_BEAUTIFY.md — Suryafool CLI UX & npm Distribution Spec

## Overview

Transform Suryafool from a Python-only tool into a visually stunning, npm-distributable CLI with cyberpunk aesthetics, theatrical animations, and dual interaction modes.

---

## Architecture

suryafool-cli/                    # Node.js CLI layer
├── package.json                  # npm package config
├── postinstall.js                # Cross-platform binary fetcher
├── bin/
│   └── suryafool.js              # Entry point (#!/usr/bin/env node)
├── src/
│   ├── app.js                    # Main Ink app
│   ├── components/
│   │   ├── BootSequence.jsx      # Animated boot screen
│   │   ├── MatrixRain.jsx        # Matrix rain background effect
│   │   ├── Logo.jsx              # Animated ASCII art logo
│   │   ├── ScanPanel.jsx         # Live scan results display
│   │   ├── AgentStatus.jsx       # Agent progress tracker
│   │   ├── ProgressWidget.jsx    # Animated progress bars
│   │   ├── DeviceTable.jsx       # Found devices table
│   │   ├── VulnCard.jsx          # Vulnerability display card
│   │   ├── InputPrompt.jsx       # Cyberpunk-styled input
│   │   ├── REPL.jsx              # Interactive session mode
│   │   ├── HelpPanel.jsx         # Command reference
│   │   └── ConfigPanel.jsx       # Settings view
│   ├── animations/
│   │   ├── engine.js             # Core animation engine
│   │   ├── matrix.js             # Matrix rain effect
│   │   ├── typewriter.js         # Typing effect for output
│   │   ├── scanner.js            # Scanning line animation
│   │   ├── glitch.js             # Glitch text effect
│   │   ├── neon.js               # Neon pulse effect
│   │   └── sounds.js             # Terminal bell/SFX (optional)
│   ├── backend/
│   │   ├── binary.js             # Python binary wrapper
│   │   ├── process.js            # Child process manager
│   │   └── parser.js             # Parse Python output → UI events
│   ├── commands/
│   │   ├── scan.js               # suryafool scan
│   │   ├── audit.js              # suryafool audit <target>
│   │   ├── explore.js            # suryafool explore
│   │   ├── agents.js             # suryafool agents list/status
│   │   ├── config.js             # suryafool config
│   │   ├── doctor.js             # suryafool doctor
│   │   └── interactive.js        # suryafool --interactive
│   ├── styles/
│   │   ├── theme.js              # Color palette, neon definitions
│   │   ├── cyberpunk.js          # Cyberpunk theme
│   │   └── clean.js              # Clean/minimal theme
│   └── utils/
│       ├── platform.js           # OS detection
│       ├── config.js             # Config file management
│       └── logger.js             # Event logging
├── scripts/
│   └── fetch-binary.js           # Download correct platform binary
└── dist/                         # Compiled/bundled output

---

## Color Theme — Cyberpunk

```javascript
// styles/theme.js
const themes = {
  cyberpunk: {
    primary:      '#00ffff',  // Cyan neon
    secondary:    '#ff00ff',  // Magenta
    accent:       '#ffff00',  // Yellow warning
    success:      '#00ff41',  // Matrix green
    error:        '#ff0040',  // Neon red
    muted:        '#444466',  // Dim purple-gray
    background:   '#0a0a1a',  // Deep dark
    border:       '#1a1a3a',  // Subtle border
    text:         '#e0e0ff',  // Light blue-white
    highlight:    '#ff6600',  // Orange highlight
    glow:         'cyan',     // Glow color for effects
  },
  clean: {
    primary:      '#4a9eff',  // Blue
    secondary:    '#9b59b6',  // Purple
    accent:       '#f39c12',  // Amber
    success:      '#2ecc71',  // Green
    error:        '#e74c3c',  // Red
    muted:        '#7f8c8d',  // Gray
    background:   '#1e1e2e',  // Dark
    border:       '#3a3a5a',  // Border
    text:         '#d0d0e0',  // Light
    highlight:    '#e67e22',  // Orange
    glow:         'blue',     // Glow
  }
};
Animation Engine
Core Engine (animations/engine.js)
class AnimationEngine {
  constructor(options = {}) {
    this.frameRate = options.frameRate || 30;
    this.running = false;
    this.layers = [];
  }

  addLayer(layer) {
    this.layers.push(layer);
  }

  removeLayer(layer) {
    this.layers = this.layers.filter(l => l !== layer);
  }

  async start() {
    this.running = true;
    while (this.running) {
      const frame = this.layers
        .filter(l => l.active)
        .map(l => l.render())
        .join('\n');
      process.stdout.write('\x1b[H' + frame); // Clear and redraw
      await this.sleep(1000 / this.frameRate);
    }
  }

  stop() {
    this.running = false;
  }

  sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  // Transition effects
  async fadeIn(content, duration = 1000) { /* ... */ }
  async fadeOut(content, duration = 1000) { /* ... */ }
  async slideIn(content, direction = 'left', duration = 500) { /* ... */ }
  async typewrite(text, speed = 30) { /* ... */ }
  async glitch(text, intensity = 3) { /* ... */ }
}

module.exports = AnimationEngine;
Matrix Rain (animations/matrix.js)
const { gradient } = require('gradient-string');
const themes = require('../styles/theme');

class MatrixRain {
  constructor(columns = 80) {
    this.columns = columns;
    this.drops = Array(columns).fill(1);
    this.chars = 'アイウエオカキクケコサシスセソタチツテトナニヌネノハヒフヘホマミムメモヤユヨラリルレロワヲン';
    this.theme = themes.cyberpunk;
  }

  render() {
    const green = gradient(this.theme.success, this.theme.muted);
    let output = '';
    for (let i = 0; i < this.columns; i++) {
      const char = this.chars[Math.floor(Math.random() * this.chars.length)];
      output += this.drops[i] > 0 ? green(char) : ' ';
      if (this.drops[i] > 0 && Math.random() > 0.975) {
        this.drops[i] = 0;
      }
      this.drops[i]++;
    }
    return output;
  }

  static async animate(duration = 5000, columns = process.stdout.columns || 80) {
    const rain = new MatrixRain(columns);
    const startTime = Date.now();
    process.stdout.write('\x1b[?25l'); // Hide cursor
    while (Date.now() - startTime < duration) {
      process.stdout.write('\r' + rain.render());
      await new Promise(r => setTimeout(r, 50));
    }
    process.stdout.write('\x1b[?25h'); // Show cursor
  }
}

module.exports = MatrixRain;
Typewriter Effect (animations/typewriter.js)
const chalk = require('chalk');

async function typewrite(text, options = {}) {
  const {
    speed = 30,
    color = chalk.cyan,
    cursor = '█',
    sound = false
  } = options;

  process.stdout.write('\x1b[?25l'); // Hide cursor

  for (const char of text) {
    process.stdout.write(color(char));
    if (sound) process.stdout.write('\x07'); // Terminal bell
    await new Promise(r => setTimeout(r, speed));
  }

  process.stdout.write('\x1b[?25h'); // Show cursor
  console.log();
}

async function typewriteLines(lines, options = {}) {
  for (const line of lines) {
    await typewrite(line, options);
  }
}

module.exports = { typewrite, typewriteLines };
Glitch Effect (animations/glitch.js)
const chalk = require('chalk');
const themes = require('../styles/theme');

async function glitchText(text, options = {}) {
  const { intensity = 3, duration = 500, theme = themes.cyberpunk } = options;
  const glitchChars = '!@#$%^&*()_+-=[]{}|;:,.<>?/~`';
  const original = text.split('');
  const iterations = Math.floor(duration / 50);

  for (let i = 0; i < iterations; i++) {
    const glitched = original.map((char, idx) => {
      if (Math.random() < intensity / 10) {
        const replacement = glitchChars[Math.floor(Math.random() * glitchChars.length)];
        return Math.random() > 0.5
          ? chalk.red(replacement)
          : chalk.hex(theme.secondary)(replacement);
      }
      return chalk.hex(theme.primary)(char);
    }).join('');

    process.stdout.write('\r' + glitched);
    await new Promise(r => setTimeout(r, 50));
  }

  process.stdout.write('\r' + chalk.hex(theme.primary)(text));
}

module.exports = { glitchText };
Boot Sequence
// components/BootSequence.jsx
const React = require('react');
const { useState, useEffect } = require('ink');
const Gradient = require('ink-gradient');
const Box = require('ink-box');
const chalk = require('chalk');
const { typewrite, typewriteLines } = require('../animations/typewriter');
const { glitchText } = require('../animations/glitch');
const MatrixRain = require('../animations/matrix');
const themes = require('../styles/theme');

const ASCII_LOGO = `
 ███████╗██╗   ██╗██╗   ██╗███████╗██╗      ██████╗ ██╗    ██╗
 ██╔════╝██║   ██║██║   ██║██╔════╝██║     ██╔═══██╗██║    ██║
 ███████╗██║   ██║██║   ██║███████╗██║     ██║   ██║██║ █╗ ██║
 ╚════██║██║   ██║██║   ██║╚════██║██║     ██║   ██║██║███╗██║
 ███████║╚██████╔╝╚██████╔╝███████║███████╗╚██████╔╝╚███╔███╔╝
 ╚══════╝ ╚═════╝  ╚═════╝ ╚══════╝╚══════╝ ╚═════╝  ╚══╝╚══╝
`;

async function bootSequence(onComplete) {
  const theme = themes.cyberpunk;

  // Phase 1: Matrix rain (2 seconds)
  await MatrixRain.animate(2000);

  // Phase 2: Glitch logo
  process.stdout.write('\x1b[2J\x1b[H'); // Clear screen
  await glitchText(ASCII_LOGO, { intensity: 5, duration: 1000 });

  // Phase 3: Tagline typewrite
  console.log();
  await typewrite('>> INITIALIZING WIRELESS AWARENESS PLATFORM...', {
    speed: 20,
    color: chalk.hex(theme.success)
  });

  // Phase 4: System checks with animated dots
  const checks = [
    'Loading capability registry...',
    'Initializing hardware abstraction layer...',
    'Connecting to LLM providers...',
    'Activating scope guardian...',
    'Loading mission agents...',
    'System ready.'
  ];

  for (const check of checks) {
    await typewrite(`  [✓] ${check}`, {
      speed: 15,
      color: chalk.hex(theme.muted)
    });
    await new Promise(r => setTimeout(r, 200));
  }

  // Phase 5: Final flash
  console.log();
  await glitchText('  SURYAFOOL v0.1.0 — READY', {
    intensity: 2,
    duration: 300
  });

  console.log(chalk.hex(theme.muted)('  ─'.repeat(40)));

  if (onComplete) onComplete();
}

module.exports = { bootSequence, ASCII_LOGO };
Core UI Components
Logo Component (components/Logo.jsx)
const React = require('react');
const { Text, Box } = require('ink');
const Gradient = require('ink-gradient');
const themes = require('../styles/theme');

function Logo({ compact = false, theme = themes.cyberpunk }) {
  if (compact) {
    return (
      <Box flexDirection="column">
        <Gradient colors={[theme.primary, theme.secondary]}>
          <Text bold>⚡ SURYAFOOL</Text>
        </Gradient>
      </Box>
    );
  }

  return (
    <Box flexDirection="column" borderStyle="single" borderColor={theme.border} padding={1}>
      <Gradient colors={[theme.primary, theme.secondary]}>
        <Text bold>
{` ███████╗██╗   ██╗██╗   ██╗███████╗██╗      ██████╗ ██╗    ██╗
 ██╔════╝██║   ██║██║   ██║██╔════╝██║     ██╔═══██╗██║    ██║
 ███████╗██║   ██║██║   ██║███████╗██║     ██║   ██║██║ █╗ ██║
 ╚════██║██║   ██║██║   ██║╚════██║██║     ██║   ██║██║███╗██║
 ███████║╚██████╔╝╚██████╔╝███████║███████╗╚██████╔╝╚███╔███╔╝
 ╚══════╝ ╚═════╝  ╚═════╝ ╚══════╝╚══════╝ ╚═════╝  ╚══╝╚══╝`}
        </Text>
      </Gradient>
      <Text color={theme.muted}>Universal Agentic Wireless Platform</Text>
      <Text color={theme.muted}>v0.1.0</Text>
    </Box>
  );
}

module.exports = Logo;
Scan Panel (components/ScanPanel.jsx)
const React = require('react');
const { useState, useEffect } = require('ink');
const Box = require('ink-box');
const Text = require('ink-text-input');
const chalk = require('chalk');
const themes = require('../styles/theme');

function ScanPanel({ target, findings = [], theme = themes.cyberpunk }) {
  const [progress, setProgress] = useState(0);
  const [phase, setPhase] = useState('initializing');

  useEffect(() => {
    const interval = setInterval(() => {
      setProgress(p => Math.min(p + Math.random() * 5, 100));
    }, 200);
    return () => clearInterval(interval);
  }, []);

  return (
    <Box
      flexDirection="column"
      borderStyle="double"
      borderColor={theme.primary}
      padding={1}
      width="100%"
    >
      {/* Header */}
      <Box justifyContent="space-between">
        <Text color={theme.primary} bold>⚡ SCANNING: {target}</Text>
        <Text color={theme.success}>{Math.floor(progress)}%</Text>
      </Box>

      {/* Progress bar */}
      <Box marginTop={1}>
        <Text color={theme.muted}>[</Text>
        <Text color={theme.primary}>{'█'.repeat(Math.floor(progress / 5))}</Text>
        <Text color={theme.muted}>{'░'.repeat(20 - Math.floor(progress / 5))}</Text>
        <Text color={theme.muted}>]</Text>
      </Box>

      {/* Findings */}
      {findings.length > 0 && (
        <Box flexDirection="column" marginTop={1}>
          <Text color={theme.secondary} bold>FINDINGS:</Text>
          {findings.map((f, i) => (
            <Box key={i} paddingLeft={2}>
              <Text color={f.severity === 'critical' ? theme.error : theme.accent}>
                [{f.severity.toUpperCase()}]
              </Text>
              <Text color={theme.text}> {f.description}</Text>
            </Box>
          ))}
        </Box>
      )}

      {/* Agent status */}
      <Box marginTop={1} borderStyle="single" borderColor={theme.border} padding={1}>
        <Text color={theme.muted}>Agent: </Text>
        <Text color={theme.success}>Signal Intelligence</Text>
        <Text color={theme.muted}> | Phase: </Text>
        <Text color={theme.accent}>{phase}</Text>
      </Box>

### Agent Status (components/AgentStatus.jsx)

```javascript
const React = require('react');
const { Text, Box } = require('ink');
const chalk = require('chalk');
const themes = require('../styles/theme');

const AGENTS = [
  { name: 'Discovery', icon: '🔍', status: 'idle' },
  { name: 'Signal Intel', icon: '📡', status: 'idle' },
  { name: 'Device Intel', icon: '📱', status: 'idle' },
  { name: 'Correlation', icon: '🔗', status: 'idle' },
  { name: 'Experiment', icon: '🧪', status: 'idle' },
  { name: 'Security Research', icon: '🔓', status: 'idle' },
  { name: 'Attack Planning', icon: '⚔️', status: 'idle' },
  { name: 'Verification', icon: '✅', status: 'idle' },
  { name: 'Skeptic', icon: '🤔', status: 'idle' },
  { name: 'Memory', icon: '🧠', status: 'idle' },
  { name: 'Orchestrator', icon: '🎯', status: 'idle' },
];

function AgentStatus({ activeAgents = [], theme = themes.cyberpunk }) {
  return (
    <Box flexDirection="column" borderStyle="single" borderColor={theme.border} padding={1}>
      <Text color={theme.primary} bold>⚡ AGENT STATUS</Text>
      <Box marginTop={1} flexDirection="column">
        {AGENTS.map((agent, i) => {
          const isActive = activeAgents.includes(agent.name);
          const statusColor = isActive ? theme.success : theme.muted;
          const statusText = isActive ? 'ACTIVE' : 'IDLE';
          return (
            <Box key={i} justifyContent="space-between" width="100%">
              <Text>
                <Text color={theme.secondary}>{agent.icon}</Text>
                <Text color={theme.text}> {agent.name}</Text>
              </Text>
              <Text color={statusColor}>[{statusText}]</Text>
            </Box>
          );
        })}
      </Box>
    </Box>
  );
}

module.exports = AgentStatus;
Progress Widget (components/ProgressWidget.jsx)
const React = require('react');
const { Text, Box } = require('ink');
const themes = require('../styles/theme');

function ProgressBar({ progress, width = 30, label = '', theme = themes.cyberpunk }) {
  const filled = Math.floor((progress / 100) * width);
  const empty = width - filled;
  const bar = '█'.repeat(filled) + '░'.repeat(empty);

  return (
    <Box>
      {label && <Text color={theme.muted}>{label} </Text>}
      <Text color={theme.primary}>[</Text>
      <Text color={progress >= 80 ? theme.success : theme.primary}>{bar}</Text>
      <Text color={theme.primary}>]</Text>
      <Text color={theme.accent}> {Math.floor(progress)}%</Text>
    </Box>
  );
}

function Spinner({ text, style = 'dots', theme = themes.cyberpunk }) {
  const frames = {
    dots: ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏'],
    scan: ['/', '-', '\\', '|'],
    pulse: ['░', '▒', '▓', '█', '▓', '▒', '░'],
  };

  const [frame, setFrame] = React.useState(0);

  React.useEffect(() => {
    const interval = setInterval(() => {
      setFrame(f => (f + 1) % frames[style].length);
    }, 80);
    return () => clearInterval(interval);
  }, []);

  return (
    <Box>
      <Text color={theme.primary}>{frames[style][frame]}</Text>
      <Text color={theme.text}> {text}</Text>
    </Box>
  );
}

module.exports = { ProgressBar, Spinner };
Device Table (components/DeviceTable.jsx)
const React = require('react');
const { Text, Box } = require('ink');
const themes = require('../styles/theme');

function DeviceTable({ devices = [], theme = themes.cyberpunk }) {
  if (devices.length === 0) {
    return (
      <Box borderStyle="single" borderColor={theme.border} padding={1}>
        <Text color={theme.muted}>No devices discovered yet.</Text>
      </Box>
    );
  }

  return (
    <Box flexDirection="column" borderStyle="double" borderColor={theme.primary} padding={1}>
      <Text color={theme.primary} bold>📡 DISCOVERED DEVICES ({devices.length})</Text>
      <Box marginTop={1}>
        <Text color={theme.secondary} bold>TYPE       </Text>
        <Text color={theme.secondary} bold>NAME           </Text>
        <Text color={theme.secondary} bold>SIGNAL   </Text>
        <Text color={theme.secondary} bold>RISK</Text>
      </Box>
      <Text color={theme.muted}>{'─'.repeat(55)}</Text>
      {devices.map((device, i) => (
        <Box key={i}>
          <Text color={theme.accent}>{device.type.padEnd(11)}</Text>
          <Text color={theme.text}>{device.name.substring(0, 14).padEnd(15)}</Text>
          <Text color={theme.success}>{device.signal.padEnd(9)}</Text>
          <Text color={device.risk === 'high' ? theme.error : theme.muted}>
            {device.risk}
          </Text>
        </Box>
      ))}
    </Box>
  );
}

module.exports = DeviceTable;
Vulnerability Card (components/VulnCard.jsx)
const React = require('react');
const { Text, Box } = require('ink');
const themes = require('../styles/theme');

function VulnCard({ vuln, theme = themes.cyberpunk }) {
  const severityColors = {
    critical: theme.error,
    high: theme.highlight,
    medium: theme.accent,
    low: theme.muted,
    info: theme.text,
  };

  const color = severityColors[vuln.severity] || theme.muted;

  return (
    <Box
      flexDirection="column"
      borderStyle="single"
      borderColor={color}
      padding={1}
      marginBottom={1}
    >
      <Box justifyContent="space-between">
        <Text color={color} bold>[{vuln.severity.toUpperCase()}]</Text>
        <Text color={theme.muted}>{vuln.cve || 'N/A'}</Text>
      </Box>
      <Text color={theme.text} bold>{vuln.title}</Text>
      <Text color={theme.muted}>{vuln.description}</Text>
      {vuln.fix && (
        <Box marginTop={1}>
          <Text color={theme.success}>FIX: </Text>
          <Text color={theme.text}>{vuln.fix}</Text>
        </Box>
      )}
    </Box>
  );
}

module.exports = VulnCard;
Input Prompt (components/InputPrompt.jsx)
const React = require('react');
const { useState } = require('ink');
const TextInput = require('ink-text-input');
const { Text, Box } = require('ink');
const themes = require('../styles/theme');

function InputPrompt({ onSubmit, placeholder = 'Enter command...', theme = themes.cyberpunk }) {
  const [value, setValue] = useState('');

  return (
    <Box borderStyle="single" borderColor={theme.primary} padding={1}>
      <Text color={theme.primary} bold>⚡ </Text>
      <TextInput
        value={value}
        onChange={setValue}
        onSubmit={(v) => { onSubmit(v); setValue(''); }}
        placeholder={placeholder}
      />
    </Box>
  );
}

module.exports = InputPrompt;
REPL Mode (components/REPL.jsx)
const React = require('react');
const { useState, useEffect } = require('ink');
const { Text, Box } = require('ink');
const InputPrompt = require('./InputPrompt');
const ScanPanel = require('./ScanPanel');
const AgentStatus = require('./AgentStatus');
const themes = require('../styles/theme');

function REPL({ theme = themes.cyberpunk }) {
  const [history, setHistory] = useState([]);
  const [output, setOutput] = useState(null);
  const [activeAgents, setActiveAgents] = useState([]);

  const handleCommand = async (input) => {
    const cmd = input.trim().toLowerCase();
    setHistory(h => [...h, { input, time: new Date() }]);

    // Parse commands
    if (cmd.startsWith('scan ')) {
      const target = cmd.replace('scan ', '');
      setActiveAgents(['Discovery', 'Signal Intel']);
      setOutput({ type: 'scan', target });
    } else if (cmd.startsWith('audit ')) {
      const target = cmd.replace('audit ', '');
      setActiveAgents(['Security Research', 'Verification']);
      setOutput({ type: 'audit', target });
    } else if (cmd === 'agents') {
      setOutput({ type: 'agents' });
    } else if (cmd === 'clear') {
      setOutput(null);
    } else if (cmd === 'help') {
      setOutput({ type: 'help' });
    } else if (cmd === 'exit') {
      process.exit(0);
    } else {
      setOutput({ type: 'error', message: `Unknown command: ${cmd}` });
    }
  };

  return (
    <Box flexDirection="column" padding={1}>
      {/* Header */}
      <Box borderStyle="double" borderColor={theme.primary} padding={1} marginBottom={1}>
        <Text color={theme.primary} bold>⚡ SURYAFOOL — Interactive Mode</Text>
        <Text color={theme.muted}> | Type 'help' for commands</Text>
      </Box>

      {/* Output area */}
      {output?.type === 'scan' && <ScanPanel target={output.target} theme={theme} />}
      {output?.type === 'agents' && <AgentStatus activeAgents={activeAgents} theme={theme} />}
      {output?.type === 'help' && (
        <Box flexDirection="column" borderStyle="single" borderColor={theme.border} padding={1}>
          <Text color={theme.primary} bold>COMMANDS:</Text>
          <Text color={theme.text}>  scan <target>      Scan wireless environment</Text>
          <Text color={theme.text}>  audit <target>     Security audit device</Text>
          <Text color={theme.text}>  explore             Discover all devices</Text>
          <Text color={theme.text}>  agents              Show agent status</Text>
          <Text color={theme.text}>  config              View configuration</Text>
          <Text color={theme.text}>  clear               Clear output</Text>
          <Text color={theme.text}>  exit                Exit interactive mode</Text>
        </Box>
      )}
      {output?.type === 'error' && (
        <Text color={theme.error}>✗ {output.message}</Text>
      )}

      {/* Input */}
      <InputPrompt onSubmit={handleCommand} theme={theme} />
    </Box>
  );
}

module.exports = REPL;
Backend Wrapper
Binary Manager (backend/binary.js)
const { execFileSync, spawn } = require('child_process');
const path = require('path');
const fs = require('fs');
const os = require('os');

class BinaryManager {
  constructor() {
    this.platform = this.detectPlatform();
    this.binaryPath = this.getBinaryPath();
  }

  detectPlatform() {
    const platform = os.platform();
    const arch = os.arch();
    const map = {
      'win32-x64': 'windows-x64',
      'linux-x64': 'linux-x64',
      'linux-arm64': 'linux-arm64',
      'darwin-x64': 'macos-x64',
      'darwin-arm64': 'macos-arm64',
    };
    return map[`${platform}-${arch}`] || `${platform}-${arch}`;
  }

  getBinaryPath() {
    const binaryName = this.platform.startsWith('windows') ? 'suryafool.exe' : 'suryafool';
    return path.join(__dirname, '..', 'bin', this.platform, binaryName);
  }

  isInstalled() {
    return fs.existsSync(this.binaryPath);
  }

  async fetchBinary(version = 'latest') {
    // Called by postinstall script
    const https = require('https');
    const { pipeline } = require('stream');
    const { promisify } = require('util');

    const url = `https://github.com/your-username/suryafool/releases/download/${version}/suryafool-${this.platform}.zip`;
    const zipPath = path.join(__dirname, '..', 'bin', `${this.platform}.zip`);

    // Ensure bin directory exists
    fs.mkdirSync(path.dirname(zipPath), { recursive: true });

    // Download zip
    await new Promise((resolve, reject) => {
      const file = fs.createWriteStream(zipPath);
      https.get(url, (response) => {
        if (response.statusCode === 302) {
          https.get(response.headers.location, (res) => {
            res.pipe(file);
            file.on('finish', () => { file.close(); resolve(); });
          });
        } else {
          response.pipe(file);
          file.on('finish', () => { file.close(); resolve(); });
        }
      }).on('error', reject);
    });

    // Extract zip (platform-specific)
    if (this.platform.startsWith('windows')) {
      execFileSync('powershell', ['-Command', `Expand-Archive -Path "${zipPath}" -DestinationPath "${path.dirname(zipPath)}" -Force`]);
    } else {
      execFileSync('unzip', ['-o', zipPath, '-d', path.dirname(zipPath)]);
    }

    // Cleanup
    fs.unlinkSync(zipPath);

    // Make executable on Unix
    if (!this.platform.startsWith('windows')) {
      fs.chmodSync(this.binaryPath, 0o755);
    }

    return this.binaryPath;
  }

  run(args = [], options = {}) {
    return new Promise((resolve, reject) => {
      const proc = spawn(this.binaryPath, args, {
        stdio: ['pipe', 'pipe', 'pipe'],
        env: { ...process.env, ...options.env },
      });

      let stdout = '';
      let stderr = '';

      proc.stdout.on('data', (data) => {
        const line = data.toString();
        stdout += line;
        if (options.onOutput) options.onOutput(line);
      });

      proc.stderr.on('data', (data) => {
        stderr += data.toString();
      });

      proc.on('close', (code) => {
        if (code === 0) resolve(stdout);
        else reject(new Error(stderr || `Exit code ${code}`));
      });

      proc.on('error', reject);
    });
  }
}

module.exports = BinaryManager;
Output Parser (backend/parser.js)
// Parse structured JSON output from Python backend into UI events

class OutputParser {
  constructor() {
    this.buffer = '';
  }

  parse(line) {
    this.buffer += line;
    const events = [];

    // Try to parse JSON lines from Python output
    const lines = this.buffer.split('\n');
    this.buffer = lines.pop(); // Keep incomplete line in buffer

    for (const line of lines) {
      try {
        const event = JSON.parse(line);
        events.push(this.mapEvent(event));
      } catch {
        // Not JSON — treat as plain text output
        events.push({ type: 'text', content: line });
      }
    }

    return events;
  }

  mapEvent(event) {
    const mappings = {
      'scan.progress': (e) => ({ type: 'progress', progress: e.progress, phase: e.phase }),
      'scan.found': (e) => ({ type: 'device', device: e.device }),
      'scan.complete': (e) => ({ type: 'scan_complete', findings: e.findings }),
      'agent.status': (e) => ({ type: 'agent_status', agent: e.agent, status: e.status }),
      'vuln.found': (e) => ({ type: 'vulnerability', vuln: e.vulnerability }),
      'log': (e) => ({ type: 'log', level: e.level, message: e.message }),
      'error': (e) => ({ type: 'error', message: e.message }),
      'llm.response': (e) => ({ type: 'llm', response: e.response }),
    };

    const mapper = mappings[event.type];
    return mapper ? mapper(event) : { type: 'unknown', raw: event };
  }
}

module.exports = OutputParser;
Commands
Main Entry Point (bin/suryafool.js)
#!/usr/bin/env node

const { render } = require('ink');
const React = require('react');
const meow = require('meow');
const { bootSequence } = require('../src/components/BootSequence');
const App = require('../src/app');

const cli = meow(`
  Usage
    $ suryafool <command> [options]

  Commands
    scan <target>        Scan wireless environment
    audit <target>       Security audit a device
    explore              Discover all wireless devices
    agents               List all mission agents
    config               View or set configuration
    doctor               Check environment setup
    --interactive        Enter interactive REPL mode

  Options
    --clean              Use clean/minimal theme
    --hacker-mode        Use cyberpunk theme (default)
    --no-animation       Disable animations
    --version            Show version
    --help               Show this help
`, {
  importMeta: import.meta,
  flags: {
    interactive: { type: 'boolean', default: false },
    clean: { type: 'boolean', default: false },
    hackerMode: { type: 'boolean', default: true },
    noAnimation: { type: 'boolean', default: false },
  }
});

async function main() {
  const theme = cli.flags.clean ? 'clean' : 'cyberpunk';

  // Boot sequence (skip if --no-animation)
  if (!cli.flags.noAnimation && !cli.input[0]) {
    await bootSequence();
  }

  // Render Ink app
  const { waitUntilExit } = render(
    React.createElement(App, {
      command: cli.input[0],
      args: cli.input.slice(1),
      flags: cli.flags,
      theme,
    })
  );

  await waitUntilExit();
}

main().catch(console.error);
Main App (src/app.js)
const React = require('react');
const { useState, useEffect } = require('ink');
const { Text, Box } = require('ink');
const Logo = require('./components/Logo');
const ScanPanel = require('./components/ScanPanel');
const AgentStatus = require('./components/AgentStatus');
const REPL = require('./components/REPL');
const themes = require('./styles/theme');
const BinaryManager = require('./backend/binary');
const OutputParser = require('./backend/parser');

function App({ command, args, flags, theme: themeName }) {
  const [loading, setLoading] = useState(true);
  const [result, setResult] = useState(null);
  const theme = themes[themeName];
  const binary = new BinaryManager();
  const parser = new OutputParser();

  useEffect(() => {
    if (flags.interactive || !command) {
      setLoading(false);
      return;
    }

    // Single command mode
    const runCommand = async () => {
      try {
        const output = await binary.run([command, ...args], {
          onOutput: (line) => {
            const events = parser.parse(line);
            // Handle real-time events
          }
        });
        setResult({ success: true, output });
      } catch (err) {
        setResult({ success: false, error: err.message });
      }
      setLoading(false);
    };

    runCommand();
  }, [command, args]);

  // Interactive REPL mode
  if (flags.interactive || !command) {
    return React.createElement(REPL, { theme });
  }

  // Loading state
  if (loading) {
    return (
      <Box flexDirection="column" padding={1}>
        <Logo compact theme={theme} />
        <Text color={theme.muted}>Executing: {command} {args.join(' ')}</Text>
      </Box>
    );
  }

  // Result state
  return (
    <Box flexDirection="column" padding={1}>
      <Logo compact theme={theme} />
      {result?.success ? (
        <Text color={theme.success}>{result.output}</Text>
      ) : (
        <Text color={theme.error}>✗ {result?.error}</Text>
      )}
    </Box>
  );
}

module.exports = App;
npm Packaging
package.json
{
  "name": "suryafool",
  "version": "0.1.0",
  "description": "Universal agentic wireless platform — AI-powered security auditing, scanning, and exploit generation",
  "bin": {
    "suryafool": "./bin/suryafool.js"
  },
  "files": [
    "bin/",
    "src/",
    "postinstall.js"
  ],
  "scripts": {
    "postinstall": "node postinstall.js",
    "build": "esbuild bin/suryafool.js --bundle --platform=node --outfile=dist/suryafool.js"
  },
  "dependencies": {
    "ink": "^5.0.0",
    "ink-text-input": "^6.0.0",
    "ink-box": "^1.0.0",
    "ink-gradient": "^6.0.0",
    "react": "^18.0.0",
    "meow": "^13.0.0",
    "chalk": "^5.0.0",
    "ora": "^8.0.0",
    "gradient-string": "^2.0.0",
    "boxen": "^8.0.0",
    "figlet": "^1.8.0"
  },
  "engines": {
    "node": ">=18"
  },
  "keywords": ["wireless", "security", "hacking", "ai", "agents", "penetration-testing"],
  "license": "MIT"
}
postinstall.js
#!/usr/bin/env node

const BinaryManager = require('./src/backend/binary');
const chalk = require('chalk');
const ora = require('ora');

async function postinstall() {
  const binary = new BinaryManager();

  if (binary.isInstalled()) {
    console.log(chalk.green('✓ Suryafool binary already installed.'));
    return;
  }

  const spinner = ora({
    text: `Downloading suryafool for ${binary.platform}...`,
    spinner: 'dots12',
  }).start();

  try {
    await binary.fetchBinary();
    spinner.succeed(`Suryafool installed for ${binary.platform}`);
  } catch (err) {
    spinner.fail('Failed to download binary');
    console.error(chalk.red(err.message));
    console.log(chalk.yellow('\nFallback: Install Python dependencies manually:'));
    console.log(chalk.cyan('  pip install -r requirements.txt'));
    process.exit(1);
  }
}

postinstall();
Installation Flow
# User installs globally
npm install -g suryafool

# npm runs postinstall.js
# postinstall.js:
#   1. Detects platform (linux-x64, macos-arm64, windows-x64, etc.)
#   2. Downloads correct binary from GitHub releases
#   3. Extracts to bin/<platform>/suryafool[.exe]
#   4. Marks executable on Unix

# User runs
suryafool scan 192.168.1.0/24
suryafool --interactive
Python Backend Output Contract
For the Node.js UI to parse events, your Python backend must emit JSON lines:
# Python backend emits structured events
import json

def emit_event(event_type, data):
    print(json.dumps({"type": event_type, **data}), flush=True)

# Usage:
emit_event("scan.progress", {"progress": 45, "phase": "discovering"})
emit_event("scan.found", {"device": {"type": "Wi-Fi", "name": "MyRouter", "signal": "-45dBm", "risk": "medium"}})
emit_event("agent.status", {"agent": "Signal Intel", "status": "active"})
emit_event("vuln.found", {"vulnerability": {"severity": "high", "title": "WPS enabled", "cve": "CVE-2012-XXXX", "description": "...", "fix": "Disable WPS"}})
emit_event("scan.complete", {"findings": [...]})
emit_event("log", {"level": "info", "message": "Starting scan..."})
emit_event("error", {"message": "Connection refused"})
Animation Timing
Effect
Boot sequence
Matrix rain
Logo glitch
Typewriter tagline
Check marks
Scan spinner
Progress bar
Typing effect
Glitch text
Dependencies Summary
Package
ink
ink-text-input
ink-box
ink-gradient
react
meow
chalk
ora
gradient-string
boxen
figlet
Total Node.js footprint: ~500KB + Python binary (~15-30MB)

---
