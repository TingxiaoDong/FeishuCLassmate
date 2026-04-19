# Deployment Runbook — 飞书同学 (feishu-classmate)

> Operator-facing, week-by-week runbook for deploying the `feishu-classmate`
> OpenClaw plugin into a real lab. This document complements the top-level
> [README.md](./README.md) — the README explains **what the plugin does** and
> the shape of its configuration; this runbook walks an operator who has
> **never run OpenClaw or MetaClaw before** through a full install, from bare
> machine to a working bot answering "你好" in a Feishu group.
>
> If you just want the short version, skim the section titles — every section
> ends with a **Done when** checklist so you can tell when it is safe to move
> on to the next day.

## Table of Contents

1. [Day 0 — Machine setup](#day-0--machine-setup)
2. [Day 1 — Feishu app creation](#day-1--feishu-app-creation)
3. [Day 2 — OpenClaw install and Feishu channel login](#day-2--openclaw-install-and-feishu-channel-login)
4. [Day 3 — MetaClaw (optional)](#day-3--metaclaw-optional)
5. [Day 4 — Plugin install and configuration](#day-4--plugin-install-and-configuration)
6. [Day 5 — First run](#day-5--first-run)
7. [Day 6 — Verification smoke test](#day-6--verification-smoke-test)
8. [Day 7 — Temi sidecar (when robot arrives)](#day-7--temi-sidecar-when-robot-arrives)
9. [Credentials rotation](#credentials-rotation)
10. [Upgrade and rollback](#upgrade-and-rollback)

---

## Day 0 — Machine setup

Target: a Linux or macOS host with outbound internet access and a single
operator shell. All commands below are run as the operator user, not root,
unless otherwise stated. This plugin has been tested on Ubuntu 22.04, Debian
12, and macOS 14 (Sonoma). Windows is not supported for the gateway host;
WSL2 works but is outside the scope of this runbook.

### 0.1 Install Node.js 22 (via nvm or fnm)

The plugin declares `"engines": { "node": ">=22" }` in `package.json`. Do not
use the OS-packaged Node — distro packages lag and you will hit
`SyntaxError: Unexpected token` on modern ESM features.

With `nvm`:

```bash
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash
# reopen shell, then:
nvm install 22
nvm use 22
node --version   # should print v22.x.x
```

With `fnm` (faster, preferred on macOS):

```bash
curl -fsSL https://fnm.vercel.app/install | bash
# reopen shell, then:
fnm install 22
fnm use 22
node --version
```

### 0.2 Install pnpm

```bash
npm install -g pnpm
pnpm --version   # should print 9.x or newer
```

If corporate proxies block the default npm registry, configure
`npm config set registry https://registry.npmmirror.com` before the install.

### 0.3 Install Python 3.10+

Only needed if you plan to run the Temi sidecar (Phase 2). If you are Phase 1
only, you may skip this until Day 7.

On Debian/Ubuntu:

```bash
sudo apt-get install -y python3.10 python3.10-venv python3-pip
```

On macOS (via Homebrew):

```bash
brew install python@3.11
```

Verify:

```bash
python3 --version   # 3.10 or newer
```

### 0.4 Firewall rules

The Temi sidecar listens on TCP port `8091` on the loopback interface by
default. If the plugin and the sidecar run on the same host, no firewall
change is needed — the loopback is never filtered.

If you split the sidecar onto a separate machine (e.g. a lab workstation
with a physical line of sight to the Temi robot), open port 8091 **only
between the gateway host and the sidecar host**. Do not expose 8091 to the
internet — the sidecar has no authentication.

Example with `ufw` on the sidecar host, assuming the gateway host is
`10.0.0.5`:

```bash
sudo ufw allow from 10.0.0.5 to any port 8091 proto tcp
sudo ufw reload
```

### 0.5 MetaClaw LLM keys (optional)

If you plan to activate MetaClaw (Day 3), obtain at least one LLM provider
key ahead of time. MetaClaw itself does not need the key — it is a proxy —
but OpenClaw's `gateway.llm` config does. Anthropic, OpenAI, and DeepSeek
keys all work through the same OpenAI-compatible interface.

Store the key in a local secrets file (`~/.config/feishu-classmate/llm.env`
with mode `0600`). Do not commit it, do not echo it into your shell history.

### 0.6 Done when

- `node --version` prints `v22.x.x` or newer.
- `pnpm --version` prints `9.x.x` or newer.
- `python3 --version` prints `3.10.x` or newer (skip if Phase 1 only).
- Firewall allows gateway to reach sidecar on 8091, if those are different
  hosts.
- LLM key is stored in a file with mode `0600` (skip if not using MetaClaw).

---

## Day 1 — Feishu app creation

You need a Feishu **self-built app** — not a "marketplace app". Self-built
apps are scoped to your own tenant and can be given fine-grained
permissions.

### 1.1 Create the app

1. Open <https://open.feishu.cn/app> in a browser signed in with a Feishu
   account that has administrator rights on the target tenant. (For Lark,
   the equivalent URL is <https://open.larksuite.com/app>.)
2. Click **Create App** (创建应用) and choose **Custom App (Self-built)**
   (自建应用).
3. Set **App Name** to something recognisable (e.g. `飞书同学-LabBot`).
   The display name can be changed later; the internal ID cannot.
4. Upload any square image as the avatar. The lab icon works fine.
5. Submit. You land on the app detail page.

### 1.2 Retrieve App ID and App Secret

1. In the left sidebar, click **Credentials & Basic Info** (凭证与基础信息).
2. Copy the **App ID** — it looks like `cli_a1b2c3d4e5f6g7h8`. This is not
   a secret; it may appear in logs.
3. Copy the **App Secret** (应用凭证). **This IS a secret.** Paste it
   directly into your `.env` file or OpenClaw config; do not email it, do
   not paste it into chat, and do not commit it to git.

### 1.3 Enable permission scopes

1. In the left sidebar, click **Permissions & Scopes** (权限管理).
2. For each scope in the table below, type the scope name into the search
   bar, click the matching entry, and click **Add** (申请权限).

| Scope | Purpose in this plugin |
|-------|------------------------|
| `im:message` | Send DM and card messages |
| `im:chat` | Read and write group chats |
| `im:chat:readonly` | List group members for context |
| `contact:user.base:readonly` | Resolve `open_id` to display name |
| `bitable:app` | Create / read / write Bitable apps and records |
| `docx:document` | Read and append Feishu Docs |
| `drive:drive` | Create new Bitable app in Drive root |

3. After all seven scopes are added, click **Create Version and Publish**
   (创建版本并发布) at the top right. Fill in a version note (e.g.
   `initial deploy`) and submit for tenant review. For self-built apps
   the review is usually approved by the tenant admin in minutes, not
   days.

### 1.4 Enable the bot feature

1. In the left sidebar, click **Add Features** (添加应用能力) → **Bot**
   (机器人) → **Enable**.
2. Note the **bot open_id** (starts with `ou_` or shown as `Bot` — this
   is the ID the plugin will use when sending DMs from its own identity.
   You do not need to copy it; the plugin derives it from the App ID.

### 1.5 Install the app to a test group

1. Create a new Feishu group called `LabBot-Test` with at least one other
   human member (so the bot has someone to talk to).
2. Click the **+** icon in the group → **Add Bot** (添加机器人) → search
   for your app name → **Add** (添加到群聊).
3. Send a test message in the group: `@LabBot hello`. Nothing will reply
   yet — the OpenClaw gateway is not running — but this confirms the
   bot joined.
4. Click the group name → **Group Settings** → **Chat ID** and copy the
   `oc_...` value. You will paste this into `labInfo.broadcastChatId`
   later.

### 1.6 Done when

- App ID in hand (format `cli_...`).
- App Secret in hand, stored in a file with mode `0600`.
- All 7 permission scopes show status "approved".
- App version "v1" is published.
- Bot joined `LabBot-Test` and the chat ID (`oc_...`) is recorded.

---

## Day 2 — OpenClaw install and Feishu channel login

### 2.1 Install the OpenClaw CLI

```bash
npm install -g openclaw@latest
openclaw --version   # should print 2026.4.10 or newer
```

If you see `command not found`, check where npm installs globals
(`npm config get prefix`) and ensure that directory's `bin/` is on your
`PATH`.

### 2.2 Log in to the Feishu channel

```bash
openclaw channels login --channel feishu
```

What happens:

1. OpenClaw prompts for the **App ID** and **App Secret** you collected
   on Day 1. Paste both. They are written to
   `~/.openclaw/credentials/feishu.json` with mode `0600`.
2. The command prints a **QR code** in the terminal. Open the Feishu
   mobile app, tap the **scan** icon, and scan the code. Confirm the
   login on your phone.
3. Under the hood, the command exchanges the QR code for a tenant access
   token, verifies the permission scopes are correct, and opens a
   long-lived event subscription websocket to Feishu. The token is
   cached on disk and auto-refreshed.

### 2.3 Where credentials live

```
~/.openclaw/credentials/feishu.json    # App ID + App Secret + cached tokens
~/.openclaw/credentials/*.json         # other channels, same pattern
~/.openclaw/config.json                # merged plugin config (see Day 4)
~/.openclaw/logs/gateway.log           # rolling gateway log
```

Back these three up before any major change. Losing `feishu.json` means
re-doing the QR login.

### 2.4 Smoke test the channel

```bash
openclaw channels list
```

Should print a row for `feishu` with status `connected`. If it prints
`disconnected`, check `~/.openclaw/logs/gateway.log` for the rejection
reason (most common: one of the seven scopes not approved yet).

### 2.5 Done when

- `openclaw --version` prints `2026.4.10` or newer.
- `openclaw channels list` shows `feishu` as `connected`.
- `ls -l ~/.openclaw/credentials/feishu.json` shows mode `0600`.

---

## Day 3 — MetaClaw (optional)

MetaClaw is an OpenAI-compatible proxy that sits between OpenClaw and your
real LLM provider. In Phase 1 it is **entirely optional** — if you skip
Day 3, OpenClaw talks to your LLM directly and the plugin is fully
functional. MetaClaw becomes necessary only in Phase 3 when you want the
plugin's conversations to feed a reinforcement-learning pipeline.

Skip this section if:

- You want the fastest possible path to a working bot.
- You do not yet have a target LLM API key.
- You are running in an environment where `localhost:30000` is not
  available (e.g. shared container with port conflicts).

### 3.1 Install

```bash
pip install aiming-metaclaw
metaclaw --version
```

### 3.2 Run the setup wizard

```bash
metaclaw setup
```

The wizard asks (in order):

1. **LLM provider**: `anthropic`, `openai`, `deepseek`, or `custom`.
2. **API base URL**: auto-filled based on provider; override for
   enterprise endpoints.
3. **API key**: paste the key from your `~/.config/feishu-classmate/llm.env`
   file. MetaClaw stores it at `~/.metaclaw/config.yaml` with mode `0600`.
4. **Enable RL training?**: choose **no** for Phase 1 / Phase 2. RL only
   makes sense once you have accumulated several weeks of interaction
   data. You can enable it later with
   `metaclaw config set rl.enabled true`.
5. **Data directory**: where training episodes are persisted. Default
   `~/.metaclaw/data` is fine.

### 3.3 Start the proxy

```bash
metaclaw start
# proxy listens on http://127.0.0.1:30000/v1
```

Verify:

```bash
curl -sS http://127.0.0.1:30000/v1/models | head -c 200
```

Should return a JSON list of available models.

### 3.4 Point OpenClaw at MetaClaw

```bash
openclaw config set gateway.llm.baseUrl http://127.0.0.1:30000/v1
openclaw gateway restart
```

### 3.5 What happens if you skip Day 3

- OpenClaw talks directly to `https://api.anthropic.com` (or your
  configured provider).
- Plugin functionality is **identical** — MetaClaw is transparent.
- You will see a warning in `gateway.log`: `MetaClaw proxy unreachable
  at 127.0.0.1:30000, falling back to direct LLM.` This is harmless.
- When you are ready for Phase 3, come back to this section; the plugin
  does not need to be reconfigured.

### 3.6 Done when

- Either `curl http://127.0.0.1:30000/v1/models` returns HTTP 200, or
  you have consciously skipped Day 3 and accepted the warning in logs.

---

## Day 4 — Plugin install and configuration

### 4.1 Build the plugin from source

```bash
cd feishu-classmate
pnpm install
pnpm build
```

`pnpm build` runs `tsdown` and writes the compiled plugin to
`dist/index.mjs`. Rebuild after any change to `src/` or `index.ts`.

### 4.2 Register and enable the plugin

```bash
openclaw plugins add-local ./
openclaw plugins enable feishu-classmate
openclaw plugins list
```

`openclaw plugins list` should now show `feishu-classmate` with status
`enabled`.

### 4.3 Set required config keys

The config schema lives in
[`openclaw.plugin.json`](./openclaw.plugin.json). All keys below are
scoped under `plugins.feishu-classmate.config.` in the OpenClaw config
file. Use `openclaw config set <key> <value>` to write each one.

Minimum required for the bot to reply to a message:

```bash
openclaw config set plugins.feishu-classmate.config.feishu.appId "cli_YOUR_APP_ID"
openclaw config set plugins.feishu-classmate.config.feishu.appSecret "YOUR_APP_SECRET"
openclaw config set plugins.feishu-classmate.config.feishu.domain "feishu"
openclaw config set plugins.feishu-classmate.config.labInfo.name "My Lab"
openclaw config set plugins.feishu-classmate.config.labInfo.supervisorName "Prof. Zhang"
openclaw config set plugins.feishu-classmate.config.labInfo.broadcastChatId "oc_YOUR_CHAT_ID"
```

Optional but recommended:

```bash
openclaw config set plugins.feishu-classmate.config.labInfo.memberCount 6
openclaw config set plugins.feishu-classmate.config.supervision.defaultIntervalMinutes 10
openclaw config set plugins.feishu-classmate.config.supervision.maxDurationHours 8
openclaw config set plugins.feishu-classmate.config.schedules.ganttCheckCron "0 9 * * *"
openclaw config set plugins.feishu-classmate.config.schedules.idleLoopCron "0 22 * * 1-5"
openclaw config set plugins.feishu-classmate.config.temi.sidecarUrl "http://127.0.0.1:8091"
openclaw config set plugins.feishu-classmate.config.temi.mockMode true
```

For complex values (arrays / objects), set them by editing
`~/.openclaw/config.json` directly. Example `specialAreas`:

```json
{
  "plugins": {
    "feishu-classmate": {
      "config": {
        "labInfo": {
          "specialAreas": [
            { "name": "生活仿真区", "narration": "这里是我们的生活仿真实验区。" },
            { "name": "硬件台", "narration": "这里是硬件调试区。" }
          ]
        }
      }
    }
  }
}
```

### 4.4 Done when

- `openclaw plugins list` shows `feishu-classmate` as `enabled`.
- `openclaw config get plugins.feishu-classmate.config.feishu.appId`
  echoes your App ID.
- `dist/index.mjs` exists and is newer than any file under `src/`.

---

## Day 5 — First run

### 5.1 Create the four Bitable tables

```bash
openclaw classmate setup-bitable
```

What happens:

1. The CLI calls `drive:drive` to create a new Bitable app in the
   tenant's Drive root.
2. Four tables — Projects, Gantt, Equipment, Research — are created with
   the schemas from `src/bitable/schema.ts`.
3. The resulting `app_token` and four `table_id` values are written back
   into `plugins.feishu-classmate.config.bitable` automatically.
4. Output looks like:

```
✔ Created Bitable app   LZSk...
✔ Created table  projects    tblA...
✔ Created table  gantt       tblB...
✔ Created table  equipment   tblC...
✔ Created table  research    tblD...
Wrote 5 keys to plugins.feishu-classmate.config.bitable
```

If the command fails with `permission denied`, the `drive:drive` scope
is not approved yet. Return to [Day 1 step 1.3](#13-enable-permission-scopes).

The command is idempotent — if all tables already exist it is a no-op.

### 5.2 Create the four Feishu Docs

The Bitable setup is automatic; the Docs are not. Create them by hand:

1. In Feishu, open **Docs** → **Create** → **Doc**.
2. Name it `Lab Projects (Public)`. Leave the body empty.
3. Click **Share** → set visibility to **Anyone in tenant with link**.
4. Open the Doc. Copy the **doc token** from the URL — the segment
   between `/docx/` and the next `/` or `?`.
5. Repeat for three more Docs: `Lab Projects (Private)`, `Research
   Reports`, `Daily Record`.

Write the four tokens into config:

```bash
openclaw config set plugins.feishu-classmate.config.docs.publicProjects  "docx_TOKEN_1"
openclaw config set plugins.feishu-classmate.config.docs.privateProjects "docx_TOKEN_2"
openclaw config set plugins.feishu-classmate.config.docs.researchReports "docx_TOKEN_3"
openclaw config set plugins.feishu-classmate.config.docs.dailyRecord     "docx_TOKEN_4"
```

### 5.3 Restart the gateway

```bash
openclaw gateway restart
```

The gateway re-reads `config.json`, reloads the plugin, and rehydrates
the cron schedulers (gantt-scheduler, idle-loop). Expect `gateway.log`
to print:

```
[feishu-classmate] plugin loaded
[feishu-classmate] registered 15 tools, 2 services, 1 command
[feishu-classmate] gantt-scheduler armed: cron="0 9 * * *"
[feishu-classmate] idle-loop armed: cron="0 22 * * 1-5"
```

### 5.4 Say hello

Open the `LabBot-Test` group (or DM the bot directly). Send:

```
你好
```

Expected reply within 3–5 seconds (LLM-dependent):

```
你好！我是飞书同学,你们实验室的 AI 助手。今天想聊点什么?
```

If nothing comes back within 15 seconds, tail the gateway log:

```bash
tail -f ~/.openclaw/logs/gateway.log
```

Look for any `ERR` line. The most common first-run failures are (a) the
bot not actually in the group (go back to 1.5), (b) the app version not
published (go back to 1.3), (c) `feishu.appSecret` missing or wrong.

### 5.5 Done when

- A human sends `你好` and receives a natural reply within 15 seconds.
- `gateway.log` shows the `plugin loaded` and `armed` lines.

---

## Day 6 — Verification smoke test

Run the ship-it smoke test:

```bash
./scripts/smoke.sh
```

The script verifies:

- Node and Python versions meet minimums.
- `openclaw` binary exists and version is `>= 2026.4.10`.
- MetaClaw proxy on `127.0.0.1:30000` is reachable (or warn-only if you
  skipped Day 3).
- Temi sidecar at `${TEMI_SIDECAR_URL:-http://127.0.0.1:8091}/` returns
  HTTP 200 (or warn-only if not started — expected in Phase 1).
- The `feishu-classmate` plugin appears in `openclaw plugins list` and
  is enabled.

The script exits non-zero if any **required** check fails. Warnings
(MetaClaw and sidecar) do not fail the run.

Re-run the script after every config change or upgrade. It is
idempotent.

### 6.1 Done when

- `./scripts/smoke.sh` prints a summary with only green checks in the
  required section.

---

## Day 7 — Temi sidecar (when robot arrives)

Skip this day until a physical Temi robot is on the lab LAN. Until then
`temi.mockMode=true` (the Phase 1 default) delivers realistic canned
responses.

### 7.1 Find the robot's IP

Power on the Temi. In the Temi tablet UI: **Settings** → **About** →
**Network** → note the IPv4 address, e.g. `192.168.1.100`.

Confirm reachability from the sidecar host:

```bash
ping -c 3 192.168.1.100
```

### 7.2 Install the sidecar

```bash
cd feishu-classmate/temi-sidecar
pip install -e .
```

or, if you prefer `uv`:

```bash
cd feishu-classmate/temi-sidecar
uv sync
```

### 7.3 Flip mockMode to false

```bash
openclaw config set plugins.feishu-classmate.config.temi.mockMode false
openclaw config set plugins.feishu-classmate.config.temi.sidecarUrl "http://127.0.0.1:8091"
openclaw gateway restart
```

### 7.4 Run the sidecar under systemd

Create `/etc/systemd/system/feishu-classmate-temi.service`:

```ini
[Unit]
Description=Feishu Classmate — Temi sidecar
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=labbot
Group=labbot
WorkingDirectory=/home/labbot/feishu-classmate/temi-sidecar
Environment=TEMI_IP=192.168.1.100
Environment=TEMI_PORT=8175
Environment=SIDECAR_PORT=8091
Environment=TEMI_MOCK=0
Environment=LOG_LEVEL=INFO
ExecStart=/home/labbot/.local/bin/uvicorn server:app --host 127.0.0.1 --port 8091
Restart=on-failure
RestartSec=5s

[Install]
WantedBy=multi-user.target
```

Then:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now feishu-classmate-temi.service
sudo systemctl status feishu-classmate-temi.service
```

Smoke-check the service:

```bash
curl -sS http://127.0.0.1:8091/   # expect {"status":"ok", ...}
curl -sS http://127.0.0.1:8091/status
```

### 7.5 Done when

- `systemctl status feishu-classmate-temi.service` shows `active
  (running)`.
- `curl http://127.0.0.1:8091/status` returns `"connected":true`.
- Sending `机器人去入口` to the bot in Feishu triggers an actual
  physical Temi movement.

---

## Credentials rotation

The repo's `.env.example` contains **real, leaked** Feishu credentials
(`cli_a96b727740381bd7`, secret `wBVWH65YHkBjdKrqzyyZEf6GVCnbBt3b`).
Anyone who has ever browsed GitHub knows them. Rotate before deploying.

### Rotate the Feishu App Secret

1. Go to <https://open.feishu.cn/app>, open your app.
2. **Credentials & Basic Info** → **App Secret** → **Reset**.
3. Copy the new secret immediately — the old one is invalidated on reset
   and there is no recovery.
4. Update OpenClaw config:

   ```bash
   openclaw config set plugins.feishu-classmate.config.feishu.appSecret "NEW_SECRET"
   openclaw gateway restart
   ```

5. Verify the bot still responds to `你好`. If it does not, check
   `gateway.log` for `invalid_token` and re-run the channel login:

   ```bash
   openclaw channels login --channel feishu
   ```

### Rotate the LLM API key (when using MetaClaw)

```bash
metaclaw config set providers.default.apiKey "NEW_KEY"
metaclaw restart
```

No OpenClaw-side restart needed — MetaClaw handles it transparently.

### Rotate on compromise

If you suspect a secret is compromised (e.g. you posted a log file in
Slack without redacting), rotate **both** the Feishu App Secret and the
LLM key immediately. Review `gateway.log` for unexpected API calls
since the suspected compromise window.

---

## Upgrade and rollback

### Upgrade the plugin

```bash
cd feishu-classmate
git fetch --tags
git checkout v0.2.0         # or the target tag
pnpm install
pnpm build
openclaw plugins add-local ./
openclaw plugins enable feishu-classmate
openclaw gateway restart
./scripts/smoke.sh
```

If `pnpm build` fails, do **not** restart the gateway — the previous
`dist/` is still valid. Fix the build, rebuild, then restart.

### Upgrade OpenClaw itself

```bash
npm install -g openclaw@latest
openclaw --version
openclaw gateway restart
./scripts/smoke.sh
```

OpenClaw keeps `~/.openclaw/config.json` and
`~/.openclaw/credentials/` across upgrades — no re-login needed.

### Rollback after a bad upgrade

```bash
cd feishu-classmate
git checkout v0.1.0
pnpm install
pnpm build
openclaw plugins add-local ./
openclaw plugins enable feishu-classmate
openclaw gateway restart
```

### Disable and re-enable

To temporarily take the plugin offline without uninstalling:

```bash
openclaw plugins disable feishu-classmate
openclaw gateway restart
```

To bring it back:

```bash
openclaw plugins enable feishu-classmate
openclaw gateway restart
```

Config and Bitable data persist across disable/enable cycles.

### Full uninstall

```bash
openclaw plugins disable feishu-classmate
openclaw plugins remove feishu-classmate
openclaw gateway restart
```

Bitable tables and Docs remain in Feishu — delete them manually if you
no longer need the data.

---

## Appendix — Runbook flowchart

```
[Day 0 machine]
      |
      v
[Day 1 Feishu app] ---(App ID + Secret + Chat ID)---+
      |                                             |
      v                                             |
[Day 2 OpenClaw install + channel login]            |
      |                                             |
      v                                             |
[Day 3 MetaClaw setup (optional)]                   |
      |                                             |
      v                                             |
[Day 4 plugin install + config] <-------------------+
      |
      v
[Day 5 setup-bitable + create docs + first DM]
      |
      v
[Day 6 ./scripts/smoke.sh all green]
      |
      v
[Day 7 Temi sidecar, when robot arrives]
```

If you get stuck on any step, the fastest first-pass debug is:

```bash
tail -f ~/.openclaw/logs/gateway.log
```

Every error the plugin can emit is logged there with context.
