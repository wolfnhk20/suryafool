#!/usr/bin/env node

import { hideBin } from 'yargs/helpers';
import { fork } from 'child_process';
import { fileURLToPath } from 'url';
import { readFileSync } from 'fs';
import { findRepoRoot } from '../src/utils/repo-root.js';

const __dirname = fileURLToPath(new URL('.', import.meta.url));

async function main() {
  const yargs = (await import('yargs')).default;
  const yargInstance = yargs(hideBin(process.argv))
    .scriptName('suryafool')
    .usage('Usage: $0 <command> [options]')
    .command('scan <target>', 'Scan wireless environment')
    .command('audit <target>', 'Security audit a device')
    .command('explore', 'Discover all wireless devices')
    .command('agents', 'List all mission agents')
    .command('config [get|set] [key] [value]', 'View or set configuration')
    .command('doctor', 'Check environment setup')
    .help(false)
    .version(false)
    .exitProcess(false)
    .strict()
    .option('interactive', { type: 'boolean', default: false, alias: 'i', desc: 'Enter interactive REPL mode' })
    .option('clean', { type: 'boolean', default: false, desc: 'Use clean/minimal theme' })
    .option('hacker-mode', { type: 'boolean', default: true, desc: 'Use cyberpunk theme (default)' })
    .option('no-animation', { type: 'boolean', default: false, alias: 'no-anim', desc: 'Disable animations' })
    .option('help', { type: 'boolean', alias: 'h', desc: 'Show help' })
    .option('version', { type: 'boolean', alias: 'v', desc: 'Show version number' });
  const argv = yargInstance.argv;

  if (argv.help) {
    yargInstance.showHelp();
    process.exit(0);
  }

  if (argv.version) {
    const pkg = JSON.parse(readFileSync(new URL('../package.json', import.meta.url), 'utf8'));
    console.log(pkg.version);
    process.exit(0);
  }

  // Locate the Suryafool repo root so the child process can chdir into it
  // before importing dist/index.mjs. This lets `python -m bootstrap.agent`
  // resolve its manifest regardless of the user's current directory.
  const repoRoot = findRepoRoot(__dirname) || process.cwd();

  // Spawn the bundled UI in a child process so yargs doesn't interfere with Ink
  const child = fork(
    fileURLToPath(new URL('./run.mjs', import.meta.url)),
    [],
    {
      env: {
        ...process.env,
        SURYAFOOL_ARGS: JSON.stringify(argv),
        SURYAFOOL_REPO_ROOT: repoRoot,
      },
      stdio: 'inherit',
    }
  );

  child.on('exit', (code) => process.exit(code ?? 0));
}

main().catch((err) => {
  console.error('Error:', err.message);
  process.exit(1);
});