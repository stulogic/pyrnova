// Static site generator for the Pyrnova public website (State 1).
// Node standard library only. Produces a fully static site under dist/.
// No server code, no forms, no data-collection endpoints are emitted.
import { mkdir, rm, writeFile, copyFile } from 'node:fs/promises';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { renderPage, routes, robotsTxt, sitemapXml } from './src/site.mjs';

const root = dirname(fileURLToPath(import.meta.url));
const outDir = join(root, 'dist');
const origin = process.env.SITE_ORIGIN || 'https://pyrnova.com';

async function build() {
  await rm(outDir, { recursive: true, force: true });
  await mkdir(outDir, { recursive: true });

  // One static HTML file per route. "/" -> index.html; "/x/" -> x/index.html.
  for (const path of routes) {
    const html = renderPage(path, { origin });
    if (!html) throw new Error(`No content for route ${path}`);
    const rel = path === '/' ? 'index.html' : join(path.replace(/^\/|\/$/g, ''), 'index.html');
    const dest = join(outDir, rel);
    await mkdir(dirname(dest), { recursive: true });
    await writeFile(dest, html, 'utf8');
  }

  await copyFile(join(root, 'assets', 'site.css'), join(outDir, 'site.css'));
  await copyFile(join(root, 'assets', 'favicon.svg'), join(outDir, 'favicon.svg'));
  await writeFile(join(outDir, 'robots.txt'), robotsTxt(origin), 'utf8');
  await writeFile(join(outDir, 'sitemap.xml'), sitemapXml(origin), 'utf8');

  console.log(`Built ${routes.length} pages to ${outDir} (origin ${origin}).`);
}

build().catch((err) => {
  console.error(err);
  process.exit(1);
});
