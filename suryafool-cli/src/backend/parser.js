// src/backend/parser.js
// Parse structured JSONL output from backend into application events

import { EventType, isValidEvent } from './events.js';

export class OutputParser {
  constructor() {
    this.buffer = '';
  }

  /**
   * Parse a chunk of output, returning an array of parsed events
   * Handles both JSONL events and plain text fallback
   */
  parse(chunk) {
    this.buffer += chunk;
    const events = [];

    // Split by newlines, keep incomplete line in buffer
    const lines = this.buffer.split('\n');
    this.buffer = lines.pop(); // Keep incomplete line in buffer

    for (const line of lines) {
      const trimmed = line.trim();
      if (!trimmed) continue;

      try {
        const parsed = JSON.parse(trimmed);
        
        // If it's a valid structured event, use it directly
        if (isValidEvent(parsed)) {
          events.push(parsed);
        } else {
          // Unknown JSON structure - treat as generic log
          events.push({ 
            type: EventType.LOG, 
            level: 'info', 
            message: trimmed, 
            timestamp: Date.now() 
          });
        }
      } catch {
        // Not JSON - treat as plain text output
        events.push({ 
          type: EventType.COMMAND_OUTPUT, 
          line: trimmed, 
          timestamp: Date.now() 
        });
      }
    }

    return events;
  }

  /**
   * Flush any remaining buffer content
   * Tries to parse the buffer as a complete JSON line first,
   * falls back to treating it as plain text
   */
  flush() {
    const remaining = this.buffer.trim();
    this.buffer = '';
    if (!remaining) return [];

    // Try to parse as JSON first
    try {
      const parsed = JSON.parse(remaining);
      if (isValidEvent(parsed)) {
        return [parsed];
      }
      // Unknown JSON structure - treat as generic log
      return [{ type: EventType.LOG, level: 'info', message: remaining, timestamp: Date.now() }];
    } catch {
      // Not JSON - treat as plain text output
      return [{ type: EventType.COMMAND_OUTPUT, line: remaining, timestamp: Date.now() }];
    }
  }
}

export default OutputParser;