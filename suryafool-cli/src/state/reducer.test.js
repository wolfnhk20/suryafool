import { test, describe } from 'node:test';
import assert from 'node:assert/strict';
import { reducer, initialState } from './reducer.js';

describe('reducer', () => {
  test('SET_TAB changes activeTab', () => {
    const state = reducer(initialState, { type: 'SET_TAB', payload: 'dashboard' });
    assert.equal(state.activeTab, 'dashboard');
  });

  test('ADD_FINDING appends to dashboard.findings', () => {
    const finding = { id: '1', title: 'Test Finding', severity: 'high' };
    const state = reducer(initialState, { type: 'ADD_FINDING', payload: finding });
    assert.equal(state.dashboard.findings.length, 1);
    assert.deepEqual(state.dashboard.findings[0], finding);
  });

  test('ADD_EVIDENCE appends a single evidence record (Phase 2.7.8)', () => {
    const ev = { kind: 'ble_pairing', target_entity_id: 'AA:BB:CC:00:00:01' };
    const state = reducer(initialState, { type: 'ADD_EVIDENCE', payload: ev });
    assert.equal(state.evidence.length, 1);
    assert.deepEqual(state.evidence[0], ev);
  });

  test('ADD_EVIDENCE renders multiple evidence records independently', () => {
    let state = initialState;
    state = reducer(state, { type: 'ADD_EVIDENCE', payload: { kind: 'wifi_eapol_handshake', target_entity_id: '02:00:00:00:00:01' } });
    state = reducer(state, { type: 'ADD_EVIDENCE', payload: { kind: 'ble_secure_write', target_entity_id: 'AA:BB:CC:00:00:01' } });
    state = reducer(state, { type: 'ADD_EVIDENCE', payload: { kind: 'wifi_pmkid', target_entity_id: '02:00:00:00:00:01' } });
    assert.equal(state.evidence.length, 3);
    assert.deepEqual(state.evidence.map((e) => e.kind), ['wifi_eapol_handshake', 'ble_secure_write', 'wifi_pmkid']);
  });

  test('SET_PROGRESS updates dashboard.progress', () => {
    const state = reducer(initialState, { type: 'SET_PROGRESS', payload: 75 });
    assert.equal(state.dashboard.progress, 75);
  });

  test('AGENT_STATUS updates agent list', () => {
    const agents = [{ id: '1', name: 'Agent 1', status: 'active' }];
    const state = reducer(initialState, { type: 'AGENT_STATUS', payload: agents });
    assert.deepEqual(state.agents, agents);
  });

  test('SET_MODAL sets modal state', () => {
    const modal = { type: 'confirm', title: 'Confirm', message: 'Are you sure?' };
    const state = reducer(initialState, { type: 'SET_MODAL', payload: modal });
    assert.deepEqual(state.modal, modal);
  });

  test('CLEAR_MODAL clears modal', () => {
    const modal = { type: 'confirm', title: 'Confirm', message: 'Are you sure?' };
    let state = reducer(initialState, { type: 'SET_MODAL', payload: modal });
    state = reducer(state, { type: 'CLEAR_MODAL' });
    assert.equal(state.modal, null);
  });

  test('SET_THEME changes theme', () => {
    const state = reducer(initialState, { type: 'SET_THEME', payload: 'clean' });
    assert.equal(state.theme, 'clean');
  });

  test('ADD_LOG adds string log entry with metadata', () => {
    const state = reducer(initialState, { type: 'ADD_LOG', payload: 'Test message' });
    assert.equal(state.logs.length, 1);
    assert.equal(state.logs[0].message, 'Test message');
    assert.equal(state.logs[0].level, 'info');
    assert.ok(state.logs[0].timestamp);
  });

  test('ADD_LOG adds object log entry', () => {
    const logEntry = { level: 'error', message: 'Error occurred', timestamp: 12345 };
    const state = reducer(initialState, { type: 'ADD_LOG', payload: logEntry });
    assert.equal(state.logs.length, 1);
    assert.deepEqual(state.logs[0], logEntry);
  });

  test('PUSH_HISTORY adds to command history', () => {
    const cmd = { command: 'scan', args: ['target'], time: new Date() };
    const state = reducer(initialState, { type: 'PUSH_HISTORY', payload: cmd });
    assert.equal(state.commandHistory.length, 1);
    assert.deepEqual(state.commandHistory[0], cmd);
  });

  test('PUSH_HISTORY limits history to 100 entries', () => {
    let state = initialState;
    for (let i = 0; i < 105; i++) {
      state = reducer(state, { type: 'PUSH_HISTORY', payload: { command: `cmd${i}`, args: [], time: new Date() } });
    }
    assert.equal(state.commandHistory.length, 100);
  });

  test('SET_CURRENT_COMMAND sets current command', () => {
    const cmd = { command: 'scan', args: ['target'] };
    const state = reducer(initialState, { type: 'SET_CURRENT_COMMAND', payload: cmd });
    assert.deepEqual(state.currentCommand, cmd);
  });

  test('SET_COMMAND_STATUS updates command status', () => {
    const state = reducer(initialState, { type: 'SET_COMMAND_STATUS', payload: 'running' });
    assert.equal(state.commandStatus, 'running');
  });

  test('CLEAR_LOGS clears the log array', () => {
    let state = reducer(initialState, { type: 'ADD_LOG', payload: 'Test 1' });
    state = reducer(state, { type: 'ADD_LOG', payload: 'Test 2' });
    assert.equal(state.logs.length, 2);
    state = reducer(state, { type: 'CLEAR_LOGS' });
    assert.equal(state.logs.length, 0);
  });

  test('unknown action returns state unchanged', () => {
    const state = reducer(initialState, { type: 'UNKNOWN_ACTION', payload: 'test' });
    assert.deepEqual(state, initialState);
  });

  test('immutability: state is not mutated', () => {
    const state1 = reducer(initialState, { type: 'SET_TAB', payload: 'agents' });
    assert.notStrictEqual(state1, initialState);
    assert.equal(initialState.activeTab, 'dashboard');
  });
});