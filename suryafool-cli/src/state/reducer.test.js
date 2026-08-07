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
});