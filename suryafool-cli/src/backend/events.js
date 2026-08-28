// src/backend/events.js
// Structured JSONL event protocol for backend communication

/**
 * Event types emitted by the backend
 * Each event is a JSON object on its own line (JSONL format)
 */

export const EventType = {
  // Command lifecycle
  COMMAND_STARTED: 'command.started',
  COMMAND_OUTPUT: 'command.output',
  COMMAND_PROGRESS: 'command.progress',
  COMMAND_COMPLETED: 'command.completed',
  COMMAND_FAILED: 'command.failed',
  
  // Findings & scanning
  FINDING_CREATED: 'finding.created',
  SCAN_STARTED: 'scan.started',
  SCAN_PROGRESS: 'scan.progress',
  SCAN_COMPLETED: 'scan.completed',
  
  // Agent status
  AGENT_STATUS: 'agent.status',
  AGENT_STARTED: 'agent.started',
  AGENT_STOPPED: 'agent.stopped',
  
  // Vulnerabilities
  VULN_FOUND: 'vuln.found',

  // Evidence (Phase 2.7.5+ — durable capture records)
  EVIDENCE_CREATED: 'evidence.created',

  // Logs
  LOG: 'log',
  ERROR: 'error',
  
  // LLM
  LLM_RESPONSE: 'llm.response',
};

/**
 * Create a command.started event
 */
export function commandStarted(command, args) {
  return { type: EventType.COMMAND_STARTED, command, args, timestamp: Date.now() };
}

/**
 * Create a command.output event
 */
export function commandOutput(line) {
  return { type: EventType.COMMAND_OUTPUT, line, timestamp: Date.now() };
}

/**
 * Create a command.progress event
 */
export function commandProgress(progress, phase, message) {
  return { type: EventType.COMMAND_PROGRESS, progress, phase, message, timestamp: Date.now() };
}

/**
 * Create a command.completed event
 */
export function commandCompleted(command, result) {
  return { type: EventType.COMMAND_COMPLETED, command, result, timestamp: Date.now() };
}

/**
 * Create a command.failed event
 */
export function commandFailed(command, error) {
  return { type: EventType.COMMAND_FAILED, command, error, timestamp: Date.now() };
}

/**
 * Create a finding.created event
 */
export function findingCreated(finding) {
  return { type: EventType.FINDING_CREATED, finding, timestamp: Date.now() };
}

/**
 * Create a scan.progress event
 */
export function scanProgress(progress, phase, message) {
  return { type: EventType.SCAN_PROGRESS, progress, phase, message, timestamp: Date.now() };
}

/**
 * Create an agent.status event
 */
export function agentStatus(agent, status, metadata) {
  return { type: EventType.AGENT_STATUS, agent, status, metadata, timestamp: Date.now() };
}

/**
 * Create a vuln.found event
 */
export function vulnFound(vulnerability) {
  return { type: EventType.VULN_FOUND, vulnerability, timestamp: Date.now() };
}

/**
 * Create an evidence.created event (Phase 2.7.5+)
 */
export function evidenceCreated(evidence, sourceActionId, runId) {
  return { type: EventType.EVIDENCE_CREATED, evidence, sourceActionId, runId, timestamp: Date.now() };
}

/**
 * Create a log event
 */
export function logEvent(level, message, metadata) {
  return { type: EventType.LOG, level, message, metadata, timestamp: Date.now() };
}

/**
 * Create an error event
 */
export function errorEvent(message, details) {
  return { type: EventType.ERROR, message, details, timestamp: Date.now() };
}

/**
 * Validate if an object is a valid event
 */
export function isValidEvent(obj) {
  return obj && typeof obj === 'object' && typeof obj.type === 'string' && Object.values(EventType).includes(obj.type);
}

export default EventType;