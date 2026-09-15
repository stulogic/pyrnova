// Minimal local static preview server for rendered acceptance only.
// Serves dist/ read-only on 127.0.0.1. No data is collected or stored.
import { createServer } from 'node:http';
import { readFile, stat } from 'node:fs/promises';
import { join, extname, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = join(dirname(fileURLToPath(import.meta.url)), '..', 'dist');
const port = Number(process.env.PORT || 4318);
const types = {
  '.html': 'text/html; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.svg': 'image/svg+xml',
  '.xml': 'application/xml; charset=utf-8',
  '.txt': 'text/plain; charset=utf-8',
};

async function resolve(pathname) {
  let rel = decodeURIComponent(pathname).replace(/\.\.+/g, '');
  if (rel.endsWith('/')) rel += 'index.html';
  let file = join(root, rel);
  try {
    if ((await stat(file)).isDirectory()) file = join(file, 'index.html');
    return file;
  } catch {
    // Try directory-style route without trailing slash.
    try {
      const alt = join(root, rel, 'index.html');
      await stat(alt);
      return alt;
    } catch {
      return null;
    }
  }
}

createServer(async (req, res) => {
  if (req.method !== 'GET' && req.method !== 'HEAD') {
    res.writeHead(405).end();
    return;
  }
  const url = new URL(req.url, `http://${req.headers.host}`);
  const file = await resolve(url.pathname);
  if (!file) {
    res.writeHead(404, { 'Content-Type': 'text/plain' }).end('Not found');
    return;
  }
  try {
    const body = await readFile(file);
    res.writeHead(200, { 'Content-Type': types[extname(file)] || 'application/octet-stream' });
    res.end(req.method === 'HEAD' ? undefined : body);
  } catch {
    res.writeHead(404, { 'Content-Type': 'text/plain' }).end('Not found');
  }
}).listen(port, '127.0.0.1', () => console.log(`Preview at http://127.0.0.1:${port}/`));
