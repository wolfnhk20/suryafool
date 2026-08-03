// src/app.js
// Main Ink application - pure library, no CLI parsing

import React, { useState, useEffect } from 'react';
import { Text, Box } from 'ink';
import Logo from './components/Logo.js';
import ScanPanel from './components/ScanPanel.js';
import AgentStatus from './components/AgentStatus.js';
import REPL from './components/REPL.js';
import { themes } from './styles/theme.js';
import BinaryManager from './backend/binary.js';
import OutputParser from './backend/parser.js';
import { bootSequence } from './components/BootSequence.js';

function App({ command, args, flags, theme: themeName, onCommand }) {
  const [loading, setLoading] = useState(true);
  const [result, setResult] = useState(null);
  const theme = themes[themeName] || themes.cyberpunk;
  const binary = new BinaryManager();
  const parser = new OutputParser();

  useEffect(() => {
    if (!command) {
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
  if (!command) {
    return React.createElement(REPL, { 
      theme: themeName, 
      onCommand: async (cmd, args) => {
        try {
          const output = await binary.run([cmd, ...args], {
            onOutput: (line) => {
              const events = parser.parse(line);
              // Could emit events for real-time UI updates
            }
          });
          return output;
        } catch (err) {
          throw err;
        }
      } 
    });
  }

  // Loading state
  if (loading) {
    return (
      <Box flexDirection="column" padding={1}>
        <Logo compact theme={themeName} />
        <Text color={theme.muted}>Executing: {command} {args.join(' ')}</Text>
      </Box>
    );
  }

  // Result state
  return (
    <Box flexDirection="column" padding={1}>
      <Logo compact theme={themeName} />
      {result?.success ? (
        <Text color={theme.success}>{result.output}</Text>
      ) : (
        <Text color={theme.error}>✗ {result?.error}</Text>
      )}
    </Box>
  );
}

export default App;