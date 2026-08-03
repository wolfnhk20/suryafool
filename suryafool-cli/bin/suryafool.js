#!/usr/bin/env node

import { hideBin } from 'yargs/helpers';
import { fork } from 'child_process';
import { fileURLToPath } from 'url';

const __dirname = fileURLToPath(new URL('.', import.meta.url));

async function main() {
  const yargs = (await import('yargs')).default;
  const argv = yargs(hideBin(process.argv))
    .scriptName('suryafool')
    .usage('Usage: $0 <command> [options]')
    .command('scan <target>', 'Scan wireless environment')
    .command('audit <target>', 'Security audit a device')
    .command('explore', 'Discover all wireless devices')
    .command('agents', 'List all mission agents')
    .command('config [get|set] [key] [value]', 'View or set configuration')
    .command('doctor', 'Check environment setup')
    .option('interactive', { type: 'boolean', default: false, alias: 'i', desc: 'Enter interactive REPL mode' })
    .option('clean', { type: 'boolean', default: false, desc: 'Use clean/minimal theme' })
    .option('hacker-mode', { type: 'boolean', default: true, desc: 'Use cyberpunk theme (default)' })
    .option('no-animation', { type: 'boolean', default: false, alias: 'no-anim', desc: 'Disable animations' })
    .help('help')
    .version('version')
    .strict()
    .argv;

  // Spawn the bundled app with --experimental-require-module flag
  const child = fork(
    fileURLToPath(new URL('./run.mjs', import.meta.url)),
    [],
    {
      env: {
        ...process.env,
        SURYAFOOL_ARGS: JSON.stringify(argv),
      },
      execArgv: ['--experimental-require-module'],
      stdio: 'inherit',
    }
  );

  child.on('exit', (code) => process.exit(code));
}

main().catch(console.error);