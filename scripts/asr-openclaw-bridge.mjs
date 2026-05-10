#!/usr/bin/env node
/**
 * Receives Temi sidecar ASR webhook POSTs and runs one OpenClaw agent turn.
 *
 * Prerequisites: OpenClaw gateway healthy (`openclaw health`), same machine or PATH has `openclaw`.
 *
 * Run:
 *   node scripts/asr-openclaw-bridge.mjs
 *
 * Sidecar (same secret optional):
 *   export TEMI_ASR_WEBHOOK_URL=http://127.0.0.1:19889/
 *   export TEMI_ASR_WEBHOOK_SECRET=your-secret   # optional, must match bridge
 *
 * Env:
 *   ASR_BRIDGE_HOST (default 127.0.0.1)
 *   ASR_BRIDGE_PORT (default 19889)
 *   TEMI_ASR_WEBHOOK_SECRET — if set, require header X-Temi-ASR-Secret
 *   OPENCLAW_BIN (default openclaw)
 *   OPENCLAW_ASR_AGENT (default main)
 *   OPENCLAW_ASR_CHANNEL (default feishu)
 *   OPENCLAW_ASR_SESSION_ID — optional --session-id
 *   OPENCLAW_ASR_DELIVER — 1 to pass --deliver (needs reply routing in OpenClaw)
 *   OPENCLAW_ASR_REPLY_TO / OPENCLAW_ASR_REPLY_CHANNEL — optional delivery overrides
 *   OPENCLAW_ASR_TIMEOUT_MS (default 600000)
 *   OPENCLAW_ASR_SPEAK_BASE — e.g. http://127.0.0.1:8091 → POST /speak with agent reply (truncated 500 chars)
 */

import http from "node:http";
import { spawn } from "node:child_process";

function extractAsrText(body) {
  if (typeof body?.text === "string" && body.text.trim()) return body.text.trim();
  const raw = body?.raw;
  if (raw && typeof raw === "object") {
    for (const k of ["text", "transcript", "asrText", "asr_text"]) {
      const v = raw[k];
      if (typeof v === "string" && v.trim()) return v.trim();
    }
  }
  return "";
}

function extractAssistantText(agentJson) {
  const pay = agentJson?.result?.payloads;
  if (Array.isArray(pay)) {
    const parts = pay.map((p) => (typeof p?.text === "string" ? p.text : "")).filter(Boolean);
    if (parts.length) return parts.join("\n").trim();
  }
  const vis = agentJson?.result?.meta?.finalAssistantVisibleText;
  if (typeof vis === "string" && vis.trim()) return vis.trim();
  return "";
}

function runOpenclawAgent(message, env) {
  const bin = env.OPENCLAW_BIN || "openclaw";
  const args = [
    "agent",
    "--agent",
    env.OPENCLAW_ASR_AGENT || "main",
    "--channel",
    env.OPENCLAW_ASR_CHANNEL || "feishu",
    "--message",
    message,
    "--json",
  ];
  if (env.OPENCLAW_ASR_SESSION_ID?.trim()) {
    args.push("--session-id", env.OPENCLAW_ASR_SESSION_ID.trim());
  }
  const deliver = ["1", "true", "yes"].includes(
    String(env.OPENCLAW_ASR_DELIVER || "").toLowerCase(),
  );
  if (deliver) {
    args.push("--deliver");
    if (env.OPENCLAW_ASR_REPLY_TO?.trim()) {
      args.push("--reply-to", env.OPENCLAW_ASR_REPLY_TO.trim());
      if (env.OPENCLAW_ASR_REPLY_CHANNEL?.trim()) {
        args.push("--reply-channel", env.OPENCLAW_ASR_REPLY_CHANNEL.trim());
      }
    }
  }

  const timeoutMs = Number(env.OPENCLAW_ASR_TIMEOUT_MS || 600_000) || 600_000;

  return new Promise((resolve, reject) => {
    const child = spawn(bin, args, {
      stdio: ["ignore", "pipe", "pipe"],
      env: { ...process.env },
    });
    let out = "";
    let err = "";
    const t = setTimeout(() => {
      child.kill("SIGTERM");
      reject(new Error(`openclaw agent timeout after ${timeoutMs}ms`));
    }, timeoutMs);
    child.stdout?.on("data", (c) => {
      out += c;
    });
    child.stderr?.on("data", (c) => {
      err += c;
    });
    child.on("error", (e) => {
      clearTimeout(t);
      reject(e);
    });
    child.on("close", (code) => {
      clearTimeout(t);
      if (code !== 0) {
        reject(new Error(`openclaw exit ${code}: ${err.slice(-4000)}`));
        return;
      }
      try {
        const json = JSON.parse(out);
        resolve(json);
      } catch (e) {
        reject(new Error(`invalid JSON from openclaw: ${e.message}; stderr=${err.slice(0, 2000)}`));
      }
    });
  });
}

async function postSpeak(base, text, voice = "friendly") {
  const url = new URL("/speak", base.endsWith("/") ? base : `${base}/`);
  const body = JSON.stringify({ text: text.slice(0, 500), voice });
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body,
  });
  if (!res.ok) {
    const t = await res.text();
    throw new Error(`speak HTTP ${res.status}: ${t.slice(0, 500)}`);
  }
}

async function handlePost(req, res, env) {
  const secret = env.TEMI_ASR_WEBHOOK_SECRET?.trim();
  if (secret) {
    const got = req.headers["x-temi-asr-secret"];
    if (got !== secret) {
      res.writeHead(401, { "Content-Type": "application/json" });
      res.end(JSON.stringify({ ok: false, error: "unauthorized" }));
      return;
    }
  }

  const chunks = [];
  for await (const c of req) chunks.push(c);
  const raw = Buffer.concat(chunks).toString("utf8");
  let body;
  try {
    body = JSON.parse(raw || "{}");
  } catch {
    res.writeHead(400, { "Content-Type": "application/json" });
    res.end(JSON.stringify({ ok: false, error: "invalid JSON" }));
    return;
  }

  const text = extractAsrText(body);
  if (!text) {
    res.writeHead(200, { "Content-Type": "application/json" });
    res.end(JSON.stringify({ ok: true, skipped: true, reason: "empty ASR text" }));
    return;
  }

  console.log(`[asr-openclaw-bridge] ASR text (${text.length} chars): ${text.slice(0, 120)}…`);

  try {
    const agentJson = await runOpenclawAgent(text, env);
    const reply = extractAssistantText(agentJson);
    const status = agentJson?.status;
    console.log(`[asr-openclaw-bridge] agent status=${status} reply_len=${reply.length}`);

    const speakBase = env.OPENCLAW_ASR_SPEAK_BASE?.trim();
    if (speakBase && reply) {
      await postSpeak(speakBase, reply);
      console.log("[asr-openclaw-bridge] posted /speak to Temi sidecar");
    }

    res.writeHead(200, { "Content-Type": "application/json" });
    res.end(
      JSON.stringify({
        ok: true,
        agentStatus: status,
        replyPreview: reply.slice(0, 200),
        spoken: Boolean(speakBase && reply),
      }),
    );
  } catch (e) {
    console.error("[asr-openclaw-bridge] error:", e.message || e);
    res.writeHead(200, { "Content-Type": "application/json" });
    res.end(JSON.stringify({ ok: false, error: String(e.message || e) }));
  }
}

const env = process.env;
const host = env.ASR_BRIDGE_HOST || "127.0.0.1";
const port = Number(env.ASR_BRIDGE_PORT || 19889) || 19889;

const server = http.createServer((req, res) => {
  if (req.method === "GET" && req.url === "/") {
    res.writeHead(200, { "Content-Type": "application/json" });
    res.end(
      JSON.stringify({
        service: "asr-openclaw-bridge",
        openclawBin: env.OPENCLAW_BIN || "openclaw",
        agent: env.OPENCLAW_ASR_AGENT || "main",
        channel: env.OPENCLAW_ASR_CHANNEL || "feishu",
        secretRequired: Boolean(env.TEMI_ASR_WEBHOOK_SECRET?.trim()),
        speakBase: Boolean(env.OPENCLAW_ASR_SPEAK_BASE?.trim()),
      }),
    );
    return;
  }
  if (req.method === "POST" && (req.url === "/" || req.url === "")) {
    void handlePost(req, res, env);
    return;
  }
  res.writeHead(404);
  res.end();
});

server.listen(port, host, () => {
  console.log(`[asr-openclaw-bridge] listening http://${host}:${port}/ (POST ASR JSON)`);
});
