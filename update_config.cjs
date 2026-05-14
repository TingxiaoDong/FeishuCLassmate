const fs = require('fs');
const os = require('os');
const path = require('path');

const configPath = path.join(os.homedir(), '.openclaw', 'config.json');
let config = {};
if (fs.existsSync(configPath)) {
    config = JSON.parse(fs.readFileSync(configPath, 'utf8'));
}

if (!config.plugins) config.plugins = {};
if (!config.plugins.entries) config.plugins.entries = {};
if (!config.plugins.entries['feishu-classmate']) config.plugins.entries['feishu-classmate'] = {};
if (!config.plugins.entries['feishu-classmate'].config) config.plugins.entries['feishu-classmate'].config = {};

config.plugins.entries['feishu-classmate'].config.feishu = {
    appId: "cli_a96b727740381bd7",
    appSecret: "N2jbLZZP5xiQJpJBiBEMmb65duym7ZK7",
    domain: "feishu"
};

config.plugins.entries['feishu-classmate'].config.labInfo = {
    name: "Our Lab",
    supervisorName: "Prof. Zhang",
    broadcastChatId: "oc_test123",
    memberCount: 6
};

config.plugins.entries['feishu-classmate'].config.temi = {
    sidecarUrl: "http://127.0.0.1:8091",
    mockMode: true
};

config.plugins.entries['feishu-classmate'].config.schedules = {
    ganttCheckCron: "0 9 * * *",
    equipmentPatrolCron: "30 8 * * *",
    idleLoopCron: "0 22 * * 1-5"
};

fs.writeFileSync(configPath, JSON.stringify(config, null, 2), 'utf8');
console.log("Config updated.");
