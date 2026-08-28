// scripts/test_phase2_wiring.cjs
// End-to-end check: spawn the Python Phase 2 CLI as the Node-side BinaryManager would,
// parse the JSONL output, and confirm the events flow into the parser correctly.

const { spawn } = require('child_process');
const path = require('path');

const repoRoot = path.resolve(__dirname, '..');
const proc = spawn('python', ['-m', 'cli.phase2', 'run', '--scenario', 'home', '--seed', '7', '--json'], {
  cwd: repoRoot,
});

let jsonLines = 0;
let firstEvent = null;
let lastEvent = null;

let buf = '';
proc.stdout.on('data', (chunk) => {
  buf += chunk.toString();
  const lines = buf.split('\n');
  buf = lines.pop();
  for (const line of lines) {
    if (!line.trim()) continue;
    try {
      const evt = JSON.parse(line);
      jsonLines += 1;
      if (!firstEvent) firstEvent = evt;
      lastEvent = evt;
    } catch (e) {
      console.error('Non-JSON line:', line.slice(0, 80));
    }
  }
});

proc.on('close', (code) => {
  console.log(`python exit code: ${code}`);
  console.log(`JSONL events parsed: ${jsonLines}`);
  console.log(`first event type: ${firstEvent?.type}`);
  console.log(`last event type:  ${lastEvent?.type}`);
  if (code === 0 && jsonLines > 0) {
    console.log('END-TO-END OK');
    process.exit(0);
  } else {
    console.error('END-TO-END FAILED');
    process.exit(1);
  }
});
