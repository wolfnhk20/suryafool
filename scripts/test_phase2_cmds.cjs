// scripts/test_phase2_cmds.cjs
// Verify all Phase 2 commands produce parseable JSON.

const { spawn } = require('child_process');
const path = require('path');

const repoRoot = path.resolve(__dirname, '..');

function runPython(args, env = {}) {
  return new Promise((resolve, reject) => {
    const proc = spawn('python', args, {
      cwd: repoRoot,
      env: { ...process.env, ...env },
    });
    let buf = '';
    proc.stdout.on('data', (c) => { buf += c.toString(); });
    proc.on('close', (code) => resolve({ code, out: buf }));
    proc.on('error', reject);
  });
}

(async () => {
  // 1. capabilities --json → JSON array
  const caps = await runPython(['-m', 'cli.phase2', 'capabilities', '--json']);
  const capArr = JSON.parse(caps.out);
  console.log(`capabilities: ${capArr.length} entries, code=${caps.code}`);

  // 2. scenarios --json → JSON array
  const sc = await runPython(['-m', 'cli.phase2', 'scenarios', '--json']);
  const scArr = JSON.parse(sc.out);
  console.log(`scenarios: ${scArr.length} entries, code=${sc.code}`);

  // 3. providers --json → JSON array
  const prv = await runPython(['-m', 'cli.phase2', 'providers', '--json']);
  const prvArr = JSON.parse(prv.out);
  console.log(`providers: ${prvArr.length} entries, code=${prv.code}`);

  // 4. run --json → JSONL events
  const run = await runPython(['-m', 'cli.phase2', 'run', '--scenario', 'lab', '--seed', '5', '--json']);
  const lines = run.out.split('\n').filter(l => l.trim());
  const events = lines.map(l => JSON.parse(l));
  console.log(`run: ${events.length} events, code=${run.code}`);
  const runId = events.find(e => e.run_id)?.run_id || events[0]?.run_id;
  console.log(`run id: ${runId}`);

  // 5. show <run_id> --json → JSON object
  const show = await runPython(['-m', 'cli.phase2', 'show', runId, '--json']);
  const showObj = JSON.parse(show.out);
  console.log(`show: status=${showObj.status}, code=${show.code}`);

  // 6. report <run_id> --json → just writes file, code=0
  const rep = await runPython(['-m', 'cli.phase2', 'report', runId, '--json']);
  console.log(`report: code=${rep.code}`);

  const ok = caps.code === 0 && sc.code === 0 && prv.code === 0 &&
             run.code === 0 && show.code === 0 && rep.code === 0 &&
             capArr.length > 0 && scArr.length > 0 &&
             prvArr.length === 1 &&
             events.length > 0 && showObj.status === 'completed';
  console.log(ok ? 'ALL COMMANDS OK' : 'FAILED');
  process.exit(ok ? 0 : 1);
})();
