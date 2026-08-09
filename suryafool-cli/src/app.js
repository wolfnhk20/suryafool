// src/app.js
import React, { useEffect, useRef, useState } from 'react';
import { FullScreenBox } from 'fullscreen-ink';
import { Text, Box } from 'ink';
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

function AppContent({ initialCommand, initialArgs, flags, theme: themeName }) {
  const theme = themes[themeName] || themes.cyberpunk;
  const appState = useAppState();
  const dispatch = useDispatch();
  const [commandInput, setCommandInput] = useState('');
  const backendRef = useRef(null);

  // Initialize backend manager once
  if (!backendRef.current) {
    backendRef.current = new BackendManager();
  }

  // Handle initial command (from CLI args)
  useEffect(() => {
    if (initialCommand) {
      setCommandInput(initialCommand);
      // We'll let the commandInput useEffect handle execution
    }
  }, [initialCommand, initialArgs]);

  // Execute command when commandInput changes
  useEffect(() => {
    if (commandInput) {
      // Parse command and args
      const parts = commandInput.trim().split(/\s+/);
      const command = parts[0];
      const args = parts.slice(1);
      
      if (command) {
        // Add to history
        dispatch({ type: 'PUSH_HISTORY', payload: { command, args, time: new Date() } });
        
        // Execute command via backend
        backendRef.current.run(command, args, { 
          onOutput: (line) => {
            // Add each line of output to the console logs
            dispatch({ type: 'ADD_LOG', payload: line.trim() });
            
            // TODO: Parse output to update findings, progress, agents based on command type
            // For now, we'll simulate some updates for demo purposes
            if (command === 'doctor') {
              // Simulate doctor command output
              if (line.includes('Environment check completed') || line.includes('healthy')) {
                dispatch({ type: 'ADD_LOG', payload: 'Environment check completed' });
              }
            } else if (command === 'explore' || command === 'scan') {
              // Simulate scan/explore output
              if (line.includes('found') || line.includes('device') || line.includes('network')) {
                dispatch({ type: 'ADD_FINDING', payload: `Device detected: ${line.trim()}` });
                dispatch({ type: 'SET_PROGRESS', payload: Math.min(100, (appState.dashboard?.progress || 0) + 10) });
              }
            } else if (command === 'agents') {
              // Simulate agents output
              if (line.includes('agent') || line.includes('active')) {
                dispatch({ type: 'AGENT_STATUS', payload: [...(appState.agents || []), `Agent-${Date.now()}`] });
              }
            }
          }
        }).then((output) => {
          // Command completed successfully
          dispatch({ type: 'ADD_LOG', payload: `[${command}] Command completed` });
        }).catch((error) => {
          // Command failed
          dispatch({ type: 'ADD_LOG', payload: `[${command}] Error: ${error.message}` });
        });
      }
      
      // Clear input after execution
      setCommandInput('');
    }
  }, [commandInput, dispatch, appState]);

  return (
    <FullScreenBox flexDirection="column">
      <Header theme={themeName} />
      <Box flexGrow={1} flexDirection="row">
        <Box flexGrow={2} flexDirection="column">
          <TabPanel theme={themeName} />
        </Box>
        <Box flexGrow={1}>
          <Console theme={themeName} />
        </Box>
      </Box>
      <Footer theme={themeName} />
      <CommandBar 
        theme={themeName} 
        onCommand={setCommandInput} 
      />
      {appState.modal && appState.modal?.type === 'help' && <HelpOverlay theme={themeName} />}
      {appState.modal && appState.modal?.type !== 'help' && <ModalLayer theme={themeName} />}
    </FullScreenBox>
  );
}

function App(props) {
  return (
    <StateProvider>
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