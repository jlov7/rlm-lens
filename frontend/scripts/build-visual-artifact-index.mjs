import fs from 'node:fs/promises';
import path from 'node:path';

const repoRoot = path.resolve(process.cwd(), '..');
const snapshotDir = path.resolve(process.cwd(), 'e2e', 'visual.spec.ts-snapshots');
const artifactDir = path.resolve(repoRoot, 'output', 'playwright');
const outFile = path.resolve(repoRoot, 'output', 'playwright', 'visual-artifacts.md');

async function listFiles(dir, extFilter) {
  try {
    const items = await fs.readdir(dir, { withFileTypes: true });
    return items
      .filter((entry) => entry.isFile() && extFilter(entry.name))
      .map((entry) => path.join(dir, entry.name))
      .sort();
  } catch {
    return [];
  }
}

const snapshotFiles = await listFiles(snapshotDir, (name) => name.endsWith('.png'));
const debugFiles = await listFiles(artifactDir, (name) => name.endsWith('.json'));

await fs.mkdir(path.dirname(outFile), { recursive: true });

const lines = [
  '# Visual Artifact Index',
  '',
  `Generated: ${new Date().toISOString()}`,
  '',
  '## Snapshot Baselines',
  '',
];

if (snapshotFiles.length === 0) {
  lines.push('- None found.');
} else {
  for (const file of snapshotFiles) {
    lines.push(`- ${path.relative(repoRoot, file)}`);
  }
}

lines.push('', '## Debug Artifacts', '');
if (debugFiles.length === 0) {
  lines.push('- None found.');
} else {
  for (const file of debugFiles) {
    lines.push(`- ${path.relative(repoRoot, file)}`);
  }
}

lines.push('');
await fs.writeFile(outFile, `${lines.join('\n')}\n`, 'utf-8');
console.log(`Wrote ${path.relative(repoRoot, outFile)}`);
