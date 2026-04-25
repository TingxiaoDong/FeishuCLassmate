/**
 * Temi OpenClaw 工具函数
 * 提供 temi_control 和 temi_status 工具供 Agent 调用
 */

const TemiConnector = require('./temi-connect.js');
const TemiNLP = require('./temi-nlp.js');

// 单例连接器
let temiInstance = null;
let nlpInstance = null;

/**
 * 获取连接器实例
 */
function getConnector() {
  if (!temiInstance) {
    const config = {
      host: process.env.TEMI_HOST || '192.168.1.100',
      port: parseInt(process.env.TEMI_PORT) || 8175,
      autoReconnect: true
    };
    temiInstance = new TemiConnector(config);
  }
  return temiInstance;
}

/**
 * 获取 NLP 实例
 */
function getNLP() {
  if (!nlpInstance) {
    nlpInstance = new TemiNLP();
  }
  return nlpInstance;
}

/**
 * 确保连接
 */
async function ensureConnected() {
  const connector = getConnector();
  if (!connector.connected) {
    await connector.connect();
  }
  return connector;
}

/**
 * 保持长连接 - 不断开
 */
function keepAlive() {
  const connector = getConnector();
  // 确保 autoReconnect 为 true
  connector.autoReconnect = true;
  return connector;
}

/**
 * 工具函数：控制 Temi 机器人
 * 
 * @param {object} options
 * @param {string} options.action - 动作类型
 * @param {object} options.params - 动作参数
 * @param {string} options.id - 命令 ID (可选)
 * @param {string} options.naturalLanguage - 自然语言指令 (可选，将自动解析)
 */
async function temi_control(options = {}) {
  try {
    const connector = await ensureConnected();
    const nlp = getNLP();

    // 如果提供了自然语言，先解析
    if (options.naturalLanguage) {
      const parsed = nlp.parse(options.naturalLanguage);
      if (parsed) {
        options.action = parsed.action;
        options.params = parsed.params;
      } else {
        return {
          status: 'error',
          message: `无法理解指令：${options.naturalLanguage}`,
          suggestions: [
            '试试说："说 你好"',
            '试试说："去 接待台"',
            '试试说："拍照"'
          ]
        };
      }
    }

    if (!options.action) {
      return {
        status: 'error',
        message: '缺少 action 参数或 naturalLanguage 参数'
      };
    }

    // 发送命令
    const result = await connector.sendCommand(options.action, options.params || {}, options.id);
    return result;

  } catch (error) {
    return {
      status: 'error',
      message: error.message,
      action: options.action
    };
  }
}

/**
 * 工具函数：获取机器人状态
 */
async function temi_status() {
  try {
    const connector = getConnector();
    const status = connector.getStatus();
    
    return {
      connected: status.connected,
      host: status.host,
      port: status.port,
      pendingCommands: status.pendingCommands,
      queuedCommands: status.queuedCommands
    };
  } catch (error) {
    return {
      connected: false,
      error: error.message
    };
  }
}

/**
 * 工具函数：连接 Temi
 */
async function temi_connect(host, port) {
  try {
    const connector = getConnector();
    if (host) connector.host = host;
    if (port) connector.port = port;
    
    await connector.connect();
    return { status: 'connected', host: connector.host, port: connector.port };
  } catch (error) {
    return { status: 'error', message: error.message };
  }
}

/**
 * 工具函数：断开连接
 */
async function temi_disconnect() {
  try {
    const connector = getConnector();
    connector.disconnect();
    return { status: 'disconnected' };
  } catch (error) {
    return { status: 'error', message: error.message };
  }
}

// 导出工具函数
module.exports = {
  temi_control,
  temi_status,
  temi_connect,
  temi_disconnect,
  getConnector,
  getNLP
};
