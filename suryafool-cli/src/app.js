// src/app.js
import React, { useEffect, useRef, useState } from 'react';
import { FullScreenBox } from 'fullscreen-ink';
import { Text, Box, useInput } from 'ink';
import { StateProvider, useState as useAppState, useDispatch } from './state/context.js';
import Header from './components/Header.js';
import Footer from './components/Footer.js';
import TabPanel from './components/TabPanel.js';
import CommandBar from './components/CommandBar.js';
import HelpOverlay from './components/HelpOverlay.js';
import ModalLayer from './components/ModalLayer.js';
import Console from './components/Console.js';
import { themes } from './styles/theme.js';
import BackendManager from './backend/backend.js';
import { EventType } from './backend/events.js';
import { runBloom } from './animations/bloom.js';

// Phase 2 / 2.5 commands route to cli.phase2 instead of bootstrap.agent.
const PHASE2_COMMANDS = new Set(['capabilities', 'scenarios', 'providers', 'run', 'show', 'report']);

function AppContent({ initialCommand, initialArgs, flags, theme: themeName }) {
  const t = themes[themeName] || themes.cyberpunk;
  const appState = useAppState();
  const dispatch = useDispatch();
  const [commandInput, setCommandInput] = useState('');
  const [glyphState, setGlyphState] = useState('static');
  const backendRef = useRef(null);
  const isExecutingRef = useRef(false);
  const hasShownStartupMessage = useRef(false);

  // Initialize backend manager once
  if (!backendRef.current) {
    backendRef.current = new BackendManager();
  }

  // Startup bloom animation (non-blocking)
  useEffect(() => {
    const bloom = runBloom(setGlyphState, 1000);
    return bloom.cancel;
  }, []);

  // Show startup message once
  useEffect(() => {
    if (!hasShownStartupMessage.current) {
      hasShownStartupMessage.current = true;
      dispatch({
        type: 'ADD_LOG',
        payload: {
          level: 'info',
          message: 'Suryafool initialized. Backend not yet wired up.',
          timestamp: Date.now(),
        },
      });
      dispatch({
        type: 'ADD_LOG',
        payload: {
          level: 'info',
          message: 'This UI is a foundation layer. Backend/agent code is pending.',
          timestamp: Date.now(),
        },
      });
    }
  }, [dispatch]);

  // Keyboard shortcuts
  useInput((input, key) => {
    if (input === '?' || (key.ctrl && input === 'h')) {
      if (appState.modal?.type === 'help') {
        dispatch({ type: 'CLEAR_MODAL' });
      } else {
        dispatch({ type: 'SET_MODAL', payload: { type: 'help', title: 'Help', message: '' } });
      }
    }
    if (key.ctrl && input === 'l') {
      dispatch({ type: 'CLEAR_LOGS' });
    }
    if (input === 'q' && key.ctrl) {
      process.exit(0);
    }
  });

  // Handle initial command (from CLI args)
  useEffect(() => {
    if (initialCommand) {
      setCommandInput(initialCommand);
    }
  }, [initialCommand, initialArgs]);

  // Execute command when commandInput changes
  useEffect(() => {
    if (commandInput && !isExecutingRef.current) {
      isExecutingRef.current = true;

      // Parse command and args
      const parts = commandInput.trim().split(/\s+/);
      const command = parts[0];
      const args = parts.slice(1);

      if (command) {
        // Handle built-in UI commands locally (no backend needed)
        if (command === 'clear' || command === 'cls') {
          dispatch({ type: 'CLEAR_LOGS' });
          dispatch({ type: 'ADD_LOG', payload: { level: 'info', message: 'Console cleared.', timestamp: Date.now() } });
          setCommandInput('');
          isExecutingRef.current = false;
          return;
        }

        if (command === 'help') {
          dispatch({ type: 'SET_MODAL', payload: { type: 'help', title: 'Help', message: '' } });
          setCommandInput('');
          isExecutingRef.current = false;
          return;
        }

        if (command === 'exit' || command === 'quit') {
          process.exit(0);
        }

        // Add to history
        dispatch({ type: 'PUSH_HISTORY', payload: { command, args, time: new Date() } });
        dispatch({ type: 'SET_CURRENT_COMMAND', payload: { command, args } });
        dispatch({ type: 'SET_COMMAND_STATUS', payload: 'running' });

        dispatch({
          type: 'ADD_LOG',
          payload: {
            level: 'info',
            message: `Executing: ${command} ${args.join(' ')}`,
            timestamp: Date.now(),
          },
        });

        // Execute command via backend with structured event handling
        const usePhase2 = PHASE2_COMMANDS.has(command);
        const argsForBackend = usePhase2 ? ['--json', ...args] : args;
        backendRef.current.run(command, argsForBackend, {
          onEvent: (event) => handleBackendEvent(event, command),
          timeout: 300000, // 5 minute timeout
          module: usePhase2 ? 'cli.phase2' : 'bootstrap.agent',
        }).then((output) => {
          dispatch({
            type: 'ADD_LOG',
            payload: { level: 'success', message: `[${command}] Mission complete`, timestamp: Date.now() },
          });
          dispatch({ type: 'SET_COMMAND_STATUS', payload: 'completed' });
          // Brief completion bloom
          runBloom(setGlyphState, 600);
        }).catch((error) => {
          // Show a single, clean error message - no stack trace spam
          const shortMsg = error.message.split('\n')[0].substring(0, 120);
          dispatch({
            type: 'ADD_LOG',
            payload: { level: 'error', message: `[${command}] ${shortMsg}`, timestamp: Date.now() },
          });
          dispatch({ type: 'SET_COMMAND_STATUS', payload: 'failed' });
        }).finally(() => {
          isExecutingRef.current = false;
        });
      }

      // Clear input after execution
      setCommandInput('');
    }
  }, [commandInput, dispatch]);

  /**
   * Handle structured backend events
   */
  const handleBackendEvent = (event, commandContext) => {
    const ts = Date.now();
    switch (event.type) {
      case EventType.COMMAND_STARTED:
        dispatch({ type: 'ADD_LOG', payload: { level: 'info', message: `Starting: ${event.command} ${event.args.join(' ')}`, timestamp: ts } });
        break;

      case EventType.COMMAND_OUTPUT:
        dispatch({ type: 'ADD_LOG', payload: { level: 'info', message: event.line, timestamp: ts } });
        break;

      case EventType.COMMAND_PROGRESS:
        dispatch({ type: 'SET_PROGRESS', payload: event.progress });
        if (event.message) {
          dispatch({ type: 'ADD_LOG', payload: { level: 'info', message: `${event.phase || 'Progress'}: ${event.message}`, timestamp: ts } });
        }
        break;

      case EventType.COMMAND_COMPLETED:
        dispatch({ type: 'ADD_LOG', payload: { level: 'success', message: `Command ${event.command} completed successfully`, timestamp: ts } });
        break;

      case EventType.COMMAND_FAILED:
        dispatch({ type: 'ADD_LOG', payload: { level: 'error', message: `Command ${event.command} failed: ${event.error}`, timestamp: ts } });
        break;

      case EventType.FINDING_CREATED:
        dispatch({ type: 'ADD_FINDING', payload: event.finding });
        dispatch({ type: 'ADD_LOG', payload: { level: 'success', message: `Finding: ${JSON.stringify(event.finding)}`, timestamp: ts } });
        break;

      case EventType.EVIDENCE_CREATED:
        // Phase 2.7.8 — live evidence feed. Store only the structured record
        // (compact rendering lives in EvidenceFeed); mirror a one-line console
        // notice without dumping raw metadata.
        if (event.evidence && typeof event.evidence === 'object') {
          dispatch({ type: 'ADD_EVIDENCE', payload: event.evidence });
          const kind = event.evidence.kind || event.evidence.target_entity_id || 'evidence';
          const summary = event.evidence.summary || 'captured';
          dispatch({ type: 'ADD_LOG', payload: { level: 'success', message: `Evidence [${kind}]: ${summary}`, timestamp: ts } });
        }
        break;

      case EventType.SCAN_PROGRESS:
        dispatch({ type: 'SET_PROGRESS', payload: event.progress });
        if (event.message) {
          dispatch({ type: 'ADD_LOG', payload: { level: 'info', message: `Scan ${event.phase}: ${event.message}`, timestamp: ts } });
        }
        break;

      case EventType.AGENT_STATUS:
        dispatch({ type: 'AGENT_STATUS', payload: event.agent });
        dispatch({ type: 'ADD_LOG', payload: { level: 'info', message: `Agent ${event.agent}: ${event.status}`, timestamp: ts } });
        break;

      case EventType.VULN_FOUND:
        dispatch({ type: 'ADD_FINDING', payload: { type: 'vulnerability', ...event.vulnerability } });
        dispatch({ type: 'ADD_LOG', payload: { level: 'warning', message: `Vulnerability found: ${JSON.stringify(event.vulnerability)}`, timestamp: ts } });
        break;

      case EventType.LOG:
        dispatch({ type: 'ADD_LOG', payload: { level: event.level || 'info', message: event.message, timestamp: ts } });
        break;

      case EventType.ERROR:
        dispatch({ type: 'ADD_LOG', payload: { level: 'error', message: event.message, timestamp: ts } });
        break;

      default:
        if (event.line) {
          dispatch({ type: 'ADD_LOG', payload: { level: 'info', message: event.line, timestamp: ts } });
        }
        break;
    }
  };

  const isHelpOpen = appState.modal?.type === 'help';
  const isAnyModalOpen = !!appState.modal;

  return (
    <FullScreenBox flexDirection="column">
      <Header theme={themeName} commandStatus={appState.commandStatus} glyphState={glyphState} />
      <Box flexGrow={1} flexDirection="row">
        <Box flexGrow={5} flexDirection="column" width="55%">
          <TabPanel theme={themeName} />
        </Box>
        <Box flexGrow={4} flexDirection="column" width="45%">
          <Console theme={themeName} />
        </Box>
      </Box>
      <Footer theme={themeName} />
      <CommandBar
        theme={themeName}
        onCommand={setCommandInput}
        disabled={isExecutingRef.current}
        commandStatus={appState.commandStatus}
      />
      {isAnyModalOpen && null}
      {isHelpOpen && <HelpOverlay theme={themeName} />}
      {!isHelpOpen && appState.modal && <ModalLayer theme={themeName} />}
    </FullScreenBox>
  );
}

function App(props) {
  return (
    <StateProvider initial={props.initialState}>
      <AppContent
        initialCommand={props.command}
        initialArgs={props.args}
        flags={props.flags}
        theme={props.theme}
      />
    </StateProvider>
  );
}

export default App;