import { spawn } from "node:child_process";
import { createReadStream } from "node:fs";
import { stat } from "node:fs/promises";
import { createServer } from "node:http";
import { extname, resolve, sep } from "node:path";
import { fileURLToPath } from "node:url";

const projectRoot = resolve(fileURLToPath(new URL("../..", import.meta.url)));
const publicRoot = resolve(projectRoot, "artifacts/ricerve-admin/dist/public");
const apiEntry = resolve(projectRoot, "artifacts/api-server/dist/index.mjs");
const publicPort = Number(process.env.PORT || 3000);
const apiPort = Number(process.env.RICERVE_API_PORT || (publicPort === 3001 ? 3002 : 3001));
const apiOrigin = `http://127.0.0.1:${apiPort}`;

const mimeTypes = {
  ".css": "text/css; charset=utf-8",
  ".gif": "image/gif",
  ".html": "text/html; charset=utf-8",
  ".ico": "image/x-icon",
  ".jpeg": "image/jpeg",
  ".jpg": "image/jpeg",
  ".js": "text/javascript; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".png": "image/png",
  ".svg": "image/svg+xml",
  ".txt": "text/plain; charset=utf-8",
  ".webp": "image/webp",
  ".woff": "font/woff",
  ".woff2": "font/woff2",
};

const apiProcess = spawn(process.execPath, [apiEntry], {
  cwd: projectRoot,
  env: { ...process.env, PORT: String(apiPort) },
  stdio: "inherit",
});

async function waitForApi() {
  for (let attempt = 0; attempt < 40; attempt += 1) {
    if (apiProcess.exitCode !== null) {
      throw new Error(`Admin API exited with code ${apiProcess.exitCode}`);
    }
    try {
      const response = await fetch(`${apiOrigin}/api/healthz`);
      if (response.ok) return;
    } catch {
      // The API process may need a moment to bind its internal port.
    }
    await new Promise((resolveDelay) => setTimeout(resolveDelay, 250));
  }
  throw new Error("Admin API did not become ready within 10 seconds");
}

async function proxyApi(request, response) {
  const headers = new Headers();
  for (const [name, value] of Object.entries(request.headers)) {
    if (["connection", "content-length", "host", "transfer-encoding"].includes(name)) continue;
    if (Array.isArray(value)) headers.set(name, value.join(", "));
    else if (value !== undefined) headers.set(name, value);
  }
  const hasBody = !["GET", "HEAD"].includes(request.method || "GET");
  const chunks = [];
  if (hasBody) {
    for await (const chunk of request) chunks.push(chunk);
  }
  const upstream = await fetch(
    `${apiOrigin}${request.url || "/api"}`,
    {
      method: request.method,
      headers,
      body: chunks.length ? Buffer.concat(chunks) : undefined,
    },
  );
  const responseHeaders = {};
  upstream.headers.forEach((value, name) => {
    if (!["connection", "transfer-encoding"].includes(name)) responseHeaders[name] = value;
  });
  response.writeHead(upstream.status, responseHeaders);
  if (request.method === "HEAD") {
    response.end();
    return;
  }
  response.end(Buffer.from(await upstream.arrayBuffer()));
}

async function serveStatic(request, response) {
  let pathname;
  try {
    pathname = decodeURIComponent(new URL(request.url || "/", "http://localhost").pathname);
  } catch {
    response.writeHead(400).end("Invalid URL");
    return;
  }
  let filePath = resolve(publicRoot, `.${pathname}`);
  if (filePath !== publicRoot && !filePath.startsWith(`${publicRoot}${sep}`)) {
    response.writeHead(403).end("Forbidden");
    return;
  }
  try {
    const file = await stat(filePath);
    if (!file.isFile()) filePath = resolve(publicRoot, "index.html");
  } catch {
    filePath = resolve(publicRoot, "index.html");
  }
  try {
    const file = await stat(filePath);
    response.writeHead(200, {
      "content-length": file.size,
      "content-type": mimeTypes[extname(filePath)] || "application/octet-stream",
      "x-content-type-options": "nosniff",
    });
    if (request.method === "HEAD") {
      response.end();
      return;
    }
    createReadStream(filePath).pipe(response);
  } catch {
    response.writeHead(500).end("Admin frontend build is missing; run the build command first.");
  }
}

const server = createServer((request, response) => {
  const pathname = new URL(request.url || "/", "http://localhost").pathname;
  const handler = pathname === "/api" || pathname.startsWith("/api/")
    ? proxyApi(request, response)
    : serveStatic(request, response);
  handler.catch((error) => {
    console.error("Admin server request failed:", error?.name || "Error");
    if (!response.headersSent) response.writeHead(502);
    response.end("Admin service unavailable");
  });
});

await waitForApi();
server.listen(publicPort, "0.0.0.0", () => {
  console.log(`Ricerve admin app listening on port ${publicPort}`);
});

function shutdown() {
  server.close(() => process.exit(0));
  apiProcess.kill("SIGTERM");
  setTimeout(() => process.exit(1), 5000).unref();
}

process.on("SIGINT", shutdown);
process.on("SIGTERM", shutdown);
