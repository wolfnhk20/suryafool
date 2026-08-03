// src/backend/parser.js
// Parse structured JSON output from Python backend into UI events

export class OutputParser {
  constructor() {
    this.buffer = '';
  }

  parse(line) {
    this.buffer += line;
    const events = [];

    // Try to parse JSON lines from Python output
    const lines = this.buffer.split('\n');
    this.buffer = lines.pop(); // Keep incomplete line in buffer

    for (const l of lines) {
      const trimmed = l.trim();
      if (!trimmed) continue;

      try {
        const event = JSON.parse(trimmed);
        events.push(this.mapEvent(event));
      } catch {
        // Not JSON — treat as plain text output
        events.push({ type: 'text', content: l });
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

export default OutputParser;