# Dashboard · 飞书同学

单页静态仪表盘,展示 6 张卡片:Tool 用量 / Tool 成功率 / Projects+Gantt KPI / 器材状态 / 投稿管线 / 近期失败归档。

## Mock 模式(零配置,立刻能看)

```bash
# 从仓库根目录起一个静态 server
python3 -m http.server 9100
```

浏览器打开 <http://localhost:9100/dashboard/?mock=1>

## Live 模式(连真 Bitable)

运行仓库根目录下:
```bash
# 1) 确保 ~/.openclaw/openclaw.json 里有 channels.feishu.appId + appSecret
# 2) 确保 ~/.openclaw/state/feishu-classmate.json 里有 bitable app_token + tableIds
# 3) 起 dashboard server
node dashboard/server.mjs --port 9100
```

或者手动在页面 console 注入:
```js
window.__DASHBOARD_CONFIG__ = {
  appToken: 'bascn...',
  tableIds: { tool_trace:'tbl...', projects:'tbl...', gantt:'tbl...', equipment:'tbl...', submissions:'tbl...', failure_archive:'tbl...' },
  token: '<tenant_access_token>'
};
location.reload();
```

## 卡片说明

| 卡片 | 数据源 | 图表 |
|---|---|---|
| 📊 本周 Tool 调用量 | `ToolTrace` (过去 7 天) | 水平柱 · top 12 |
| ✅ Tool 成功率 | `ToolTrace` (总体) | 柱 · < 70% 红色 |
| 📈 项目 & 节点 | `Projects` + `Gantt` | KPI 数字 |
| 🔧 器材状态 | `Equipment` | 环形图 |
| 📚 投稿管线 | `Submissions` | 柱 |
| ⚠️ 近期失败归档 | `FailureArchive` | 列表 · 最新 5 |

## 截图

Mock 模式的截图见 `assets/dashboard-mock.png`(TODO · 截图工具未内置)。

## 安全说明

- `api.js` 从浏览器直接请求飞书 Open API,需要带 `tenant_access_token`。
- 任何人拿到这个 token 就能读你的 Bitable,**别把 live 模式暴露到公网**。
- 生产建议:把 dashboard 挂到内网 SSO 后面,或只在本机 `127.0.0.1` 访问。
