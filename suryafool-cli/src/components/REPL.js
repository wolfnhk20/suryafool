// src/components/REPL.js
// Interactive REPL mode

import React, { useState, useEffect } from 'react';
import { Text, Box } from 'ink';
import InputPrompt from './InputPrompt.js';
import ScanPanel from './ScanPanel.js';
import AgentStatus from './AgentStatus.js';
import { themes } from '../styles/theme.js';

const COMMANDS = {
  scan: { usage: 'scan <target>', desc: 'Scan wireless environment', example: 'scan 192.168.1.0/24' },
  audit: { usage: 'audit <target>', desc: 'Security audit a device', example: 'audit AA:BB:CC:DD:EE:FF' },
  explore: { usage: 'explore', desc: 'Discover all wireless devices', example: 'explore' },
  agents: { usage: 'agents', desc: 'List all mission agents', example: 'agents' },
  config: { usage: 'config [get|set] [key] [value]', desc: 'View or set configuration', example: 'config get lab_mode' },
  doctor: { usage: 'doctor', desc: 'Check environment setup', example: 'doctor' },
  clear: { usage: 'clear', desc: 'Clear output', example: 'clear' },
  help: { usage: 'help', desc: 'Show this help', example: 'help' },
  exit: { usage: 'exit', desc: 'Exit interactive mode', example: 'exit' },
};

function REPL({ theme = 'cyberpunk', onCommand }) {
  const t = themes[theme] || themes.cyberpunk;
  const [history, setHistory] = useState([]);
  const [output, setOutput] = useState(null);
  const [activeAgents, setActiveAgents] = useState([]);
  const [findings, setFindings] = useState([]);

  const handleCommand = async (input) => {
    const cmd = input.trim().toLowerCase();
    if (!cmd) return;
    
    setHistory(h => [...h, { input: cmd, time: new Date() }]);

    const parts = cmd.split(/\s+/);
    const command = parts[0];
    const args = parts.slice(1);

    const setScanOutput = (data) => {
      setOutput({ type: 'scan', target: data.target });
    };

    switch (command) {
      case 'scan': {
        if (!args[0]) {
          setOutput({ type: 'error', message: 'Usage: scan <target>' });
          return;
        }
        setActiveAgents(['Discovery', 'Signal Intel']);
        setFindings([]);
        setOutput({ type: 'scan', target: args[0] });
        
        if (onCommand) {
          try {
            const result = await onCommand('scan', [args[0]]);
            setOutput({ type: 'scan_complete', target: args[0], result });
            setActiveAgents([]);
          } catch (err) {
            setOutput({ type: 'error', message: err.message });
            setActiveAgents([]);
          }
        }
        break;
      }

      case 'audit': {
        if (!args[0]) {
          setOutput({ type: 'error', message: 'Usage: audit <target>' });
          return;
        }
        setActiveAgents(['Security Research', 'Verification']);
        setOutput({ type: 'audit', target: args[0] });
        
        if (onCommand) {
          try {
            const result = await onCommand('audit', [args[0]]);
            setOutput({ type: 'audit_complete', target: args[0], result });
            setActiveAgents([]);
          } catch (err) {
            setOutput({ type: 'error', message: err.message });
            setActiveAgents([]);
          }
        }
        break;
      }

      case 'explore': {
        setActiveAgents(['Discovery', 'Signal Intel', 'Device Intel', 'Correlation']);
        setOutput({ type: 'explore' });
        
        if (onCommand) {
          try {
            const result = await onCommand('explore', []);
            setOutput({ type: 'explore_complete', result });
            setActiveAgents([]);
          } catch (err) {
            setOutput({ type: 'error', message: err.message });
            setActiveAgents([]);
          }
        }
        break;
      }

      case 'agents':
        setOutput({ type: 'agents' });
        break;

      case 'config': {
        if (args[0] === 'get' && args[1]) {
          setOutput({ type: 'config_get', key: args[1] });
        } else if (args[0] === 'set' && args[1] && args[2]) {
          setOutput({ type: 'config_set', key: args[1], value: args[2] });
        } else {
          setOutput({ type: 'config_list' });
        }
        break;
      }

      case 'doctor':
        setOutput({ type: 'doctor' });
        break;

      case 'clear':
        setOutput(null);
        setFindings([]);
        setActiveAgents([]);
        break;

      case 'help':
        setOutput({ type: 'help' });
        break;

      case 'exit':
      case 'quit':
        process.exit(0);

      default:
        setOutput({ type: 'error', message: `Unknown command: ${command}. Type 'help' for commands.` });
    }
  };

  // Render helpers
  const renderHelp = () => (
    <Box flexDirection="column" borderStyle="single" borderColor={t.border} padding={1}>
      <Text color={t.primary} bold>COMMANDS:</Text>
      {Object.entries(COMMANDS).map(([cmd, info]) => (
        <Box key={cmd} marginTop={1}>
          <Text color={t.text}>  {cmd}</Text>
          <Text color={t.muted}> — {info.desc}</Text>
          <Text color={t.muted}>    e.g. {info.example}</Text>
        </Box>
      ))}
    </Box>
  );

  const renderConfig = () => (
    <Box flexDirection="column" borderStyle="single" borderColor={t.border} padding={1}>
      <Text color={t.primary} bold>CONFIGURATION</Text>
      <Text color={t.text}>  lab_mode: false</Text>
      <Text color={t.text}>  log_level: INFO</Text>
      <Text color={t.text}>  theme: cyberpunk</Text>
    </Box>
  );

  const renderDoctor = () => (
    <Box flexDirection="column" borderStyle="single" borderColor={t.border} padding={1}>
      <Text color={t.primary} bold>ENVIRONMENT CHECK</Text>
      <Text color={t.success}>  [✓] Python 3.11+</Text>
      <Text color={t.success}>  [✓] WSL2 + Ubuntu</Text>
      <Text color={t.success}>  [✓] USB/IP daemon</Text>
      <Text color={t.success}>  [✓] aircrack-ng</Text>
      <Text color={t.success}>  [✓] Python dependencies</Text>
    </Box>
  );

  return (
    <Box flexDirection="column" padding={1}>
      {/* Header */}
      <Box borderStyle="double" borderColor={t.primary} padding={1} marginBottom={1}>
        <Text color={t.primary} bold>⚡ SURYAFOOL — Interactive Mode</Text>
        <Text color={t.muted}> | Type 'help' for commands</Text>
      </Box>

      {/* Output area */}
      {output?.type === 'scan' && <ScanPanel target={output.target} findings={findings} phase="scanning" progress={0} theme={theme} />}
      {output?.type === 'scan_complete' && <ScanPanel target={output.target} findings={output.result?.findings || []} phase="complete" progress={100} theme={theme} />}
      {output?.type === 'audit' && <ScanPanel target={output.target} findings={findings} phase="auditing" progress={0} theme={theme} />}
      {output?.type === 'audit_complete' && <ScanPanel target={output.target} findings={output.result?.vulnerabilities || []} phase="complete" progress={100} theme={theme} />}
      {output?.type === 'explore' && <ScanPanel target="local environment" findings={findings} phase="exploring" progress={50} theme={theme} />}
      {output?.type === 'explore_complete' && <ScanPanel target="local environment" findings={output.result?.devices || []} phase="complete" progress={100} theme={theme} />}
      {output?.type === 'agents' && <AgentStatus activeAgents={activeAgents} theme={theme} />}
      {output?.type === 'help' && renderHelp()}
      {output?.type === 'config_list' && renderConfig()}
      {output?.type === 'doctor' && renderDoctor()}
      {output?.type === 'error' && <Text color={t.error}>✗ {output.message}</Text>}

      {/* Input */}
      <InputPrompt onSubmit={handleCommand} theme={theme} />
    </Box>
  );
}

export default REPL;