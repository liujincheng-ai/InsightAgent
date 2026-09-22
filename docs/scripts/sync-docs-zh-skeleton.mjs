import fs from 'node:fs';
import path from 'node:path';

const repoRoot = process.cwd();
const sourceRoot = path.join(repoRoot, 'docs');
const targetRoot = path.join(
  repoRoot,
  'i18n',
  'zh-CN',
  'docusaurus-plugin-content-docs',
  'current',
);
const staticSourceRoot = path.join(repoRoot, 'static');
const staticTargetRoot = path.join(repoRoot, 'i18n', 'zh-CN', 'docusaurus-plugin-content-docs', 'static');

const supportedExtensions = new Set(['.md', '.mdx']);

let created = 0;
let skipped = 0;
let staticCreated = 0;
let staticSkipped = 0;

function walk(dirPath) {
  const entries = fs.readdirSync(dirPath, { withFileTypes: true });

  for (const entry of entries) {
    const sourcePath = path.join(dirPath, entry.name);
    const relativePath = path.relative(sourceRoot, sourcePath);
    const targetPath = path.join(targetRoot, relativePath);

    if (entry.isDirectory()) {
      walk(sourcePath);
      continue;
    }

    if (!supportedExtensions.has(path.extname(entry.name))) {
      continue;
    }

    if (fs.existsSync(targetPath)) {
      skipped += 1;
      continue;
    }

    fs.mkdirSync(path.dirname(targetPath), { recursive: true });
    fs.copyFileSync(sourcePath, targetPath);
    created += 1;
  }
}

function copyStatic(dirPath) {
  const entries = fs.readdirSync(dirPath, { withFileTypes: true });

  for (const entry of entries) {
    const sourcePath = path.join(dirPath, entry.name);
    const relativePath = path.relative(staticSourceRoot, sourcePath);
    const targetPath = path.join(staticTargetRoot, relativePath);

    if (entry.isDirectory()) {
      copyStatic(sourcePath);
      continue;
    }

    if (fs.existsSync(targetPath)) {
      staticSkipped += 1;
      continue;
    }

    fs.mkdirSync(path.dirname(targetPath), { recursive: true });
    fs.copyFileSync(sourcePath, targetPath);
    staticCreated += 1;
  }
}

if (!fs.existsSync(sourceRoot)) {
  console.error(`English docs source directory not found: ${sourceRoot}`);
  process.exit(1);
}

fs.mkdirSync(targetRoot, { recursive: true });
walk(sourceRoot);

if (fs.existsSync(staticSourceRoot)) {
  fs.mkdirSync(staticTargetRoot, { recursive: true });
  copyStatic(staticSourceRoot);
}

console.log(
  `zh-CN docs skeleton sync complete. docs_created=${created}, docs_skipped=${skipped}, static_created=${staticCreated}, static_skipped=${staticSkipped}`,
);
