---
name: mask-secrets-in-output-paths
description: Use when credentials, tokens, or API keys appear in command output. Truncate or mask them before returning results to avoid leaking sensitive data.
category: security
---

## Mask Secrets When Appearing in Command Output

When command output contains sensitive values (tokens, passwords, API keys, app secrets), always mask them before presenting results.

**Rules:**
1. If output contains bearer tokens: Show only first 8 chars + `...` (e.g., `t-g1044ih...`)
2. If output contains app secrets: Mask completely (e.g., `***MASKED***`)
3. Never return full credential strings in tool results
4. If you need to use a token for subsequent operations, store it securely and reference by purpose, not by value

**Example:**
Tool output: `"Authorization: Bearer t-g1044ih82G7WRP4CI3VDRDBLKBLYD464DYBHQDNJ"`
Return to user: `Bearer token: t-g1044ih...`

**Anti-pattern:** Printing full API keys or app secrets in tool responses, even if the original source was a .env file.

**Note:** If the tool output contains a .env file with `FEISHU_APP_SECRET=...`, acknowledge that credentials were found but do not expose them. Say: "Found credentials in .env file. Do you want me to proceed using these, or shall I use a different configuration?"
