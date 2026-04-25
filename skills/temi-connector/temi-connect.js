/**
 * Temi WebSocket 连接器
 * 实现与 Temi 机器人的 WebSocket 通信
 */

const WebSocket = require('ws');
const { v4: uuidv4 } = require('uuid');

class TemiConnector {
  constructor(config = {}) {
    this.host = config.host || '192.168.1.100';
    this.port = config.port || 8175;
    this.autoReconnect = config.autoReconnect !== false;
    this.reconnectInterval = config.reconnectInterval || 5000;
    
    this.ws = null;
    this.connected = false;
    this.commandQueue = [];
    this.pendingCommands = new Map();
    this.eventListeners = new Map();
    this.reconnectTimer = null;
  }

  /**
   * 连接到 Temi 机器人
   */
  async connect() {
    return new Promise((resolve, reject) => {
      const url = `ws://${this.host}:${this.port}`;
      console.log(`[Temi] 正在连接到 ${url}...`);

      try {
        this.ws = new WebSocket(url);

        this.ws.on('open', () => {
          this.connected = true;
          console.log(`[Temi] 已连接到 Temi 机器人`);
          
          // 处理队列中的命令
          this._processQueue();
          resolve({ status: 'connected', host: this.host, port: this.port });
        });

        this.ws.on('message', (data) => {
          this._handleMessage(data.toString());
        });

        this.ws.on('close', () => {
          this.connected = false;
          console.log(`[Temi] 连接已关闭`);
          this._handleDisconnect();
        });

        this.ws.on('error', (error) => {
          console.error(`[Temi] WebSocket 错误:`, error.message);
          if (!this.connected) {
            reject(error);
          }
        });

        // 连接超时
        setTimeout(() => {
          if (!this.connected) {
            reject(new Error('连接超时'));
          }
        }, 10000);

      } catch (error) {
        reject(error);
      }
    });
  }

  /**
   * 断开连接
   */
  disconnect() {
    this.autoReconnect = false;
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    this.connected = false;
    console.log(`[Temi] 已断开连接`);
  }

  /**
   * 发送命令
   */
  async sendCommand(action, params = {}, id = null) {
    const commandId = id || uuidv4();
    
    const command = {
      command: action,
      ...params,
      id: commandId
    };

    return new Promise((resolve, reject) => {
      // 设置超时
      const timeout = setTimeout(() => {
        this.pendingCommands.delete(commandId);
        reject(new Error(`命令超时：${action}`));
      }, 30000);

      this.pendingCommands.set(commandId, { resolve, reject, timeout, action });

      if (this.connected && this.ws.readyState === WebSocket.OPEN) {
        this._send(command);
      } else {
        // 加入队列
        this.commandQueue.push({ command, resolve, reject, timeout });
        if (!this.connected && this.autoReconnect) {
          this._reconnect();
        }
      }
    });
  }

  /**
   * 注册事件监听器
   */
  on(event, callback) {
    if (!this.eventListeners.has(event)) {
      this.eventListeners.set(event, []);
    }
    this.eventListeners.get(event).push(callback);
    return () => this.off(event, callback);
  }

  /**
   * 移除事件监听器
   */
  off(event, callback) {
    const listeners = this.eventListeners.get(event);
    if (listeners) {
      const index = listeners.indexOf(callback);
      if (index > -1) {
        listeners.splice(index, 1);
      }
    }
  }

  /**
   * 获取状态
   */
  getStatus() {
    return {
      connected: this.connected,
      host: this.host,
      port: this.port,
      pendingCommands: this.pendingCommands.size,
      queuedCommands: this.commandQueue.length
    };
  }

  /**
   * 触发事件
   */
  _emit(event, data) {
    const listeners = this.eventListeners.get(event) || [];
    listeners.forEach(cb => {
      try {
        cb(data);
      } catch (e) {
        console.error(`[Temi] 事件回调错误:`, e);
      }
    });
  }

  /**
   * 发送消息
   */
  _send(data) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      const message = typeof data === 'string' ? data : JSON.stringify(data);
      this.ws.send(message);
      console.log(`[Temi] 发送：`, data.command || data.event || 'data');
    }
  }

  /**
   * 处理接收到的消息
   */
  _handleMessage(data) {
    // 处理非 JSON 消息（如 "Temi is ready"）
    if (!data.trim().startsWith('{')) {
      console.log(`[Temi] 接收（文本）:`, data.trim());
      return;
    }
    
    try {
      const message = JSON.parse(data);
      console.log(`[Temi] 接收：`, message.command || message.event || 'data');

      // 处理命令响应
      if (message.id && this.pendingCommands.has(message.id)) {
        const pending = this.pendingCommands.get(message.id);
        clearTimeout(pending.timeout);
        this.pendingCommands.delete(message.id);

        // 处理拍照返回的图像数据
        let responseData = message.data || {};
        if (message.command === 'takePicture') {
          // 检查是否有 imageData 字段（Android 端返回的 Base64）
          if (message.imageData) {
            responseData.image = message.imageData;
            responseData.path = message.path;
          } else if (message.data?.imageData) {
            responseData.image = message.data.imageData;
            responseData.path = message.data.path;
          }
        }

        const result = {
          status: message.status || 'completed',
          command: message.command,
          id: message.id,
          data: responseData
        };

        // 触发命令事件（用于 UI 显示）
        this._emit('command', { action: message.command, params: message, id: message.id });

        if (message.status === 'error') {
          this._emit('error', { action: message.command, message: message.message || message.error });
          pending.reject(new Error(message.message || message.error || '命令执行失败'));
        } else {
          // 特殊处理拍照事件
          if (message.command === 'takePicture' && responseData.image) {
            console.log('[Temi] 收到照片，大小:', responseData.image.length, 'bytes');
            this._emit('photo', { image: responseData.image, path: responseData.path });
          }
          
          this._emit('result', result);
          pending.resolve(result);
        }
      }

      // 触发事件监听器
      if (message.event) {
        const listeners = this.eventListeners.get(message.event) || [];
        listeners.forEach(cb => {
          try {
            cb(message);
          } catch (e) {
            console.error(`[Temi] 事件回调错误:`, e);
          }
        });
      }

    } catch (e) {
      console.error(`[Temi] 消息解析错误:`, e);
    }
  }

  /**
   * 处理断开连接
   */
  _handleDisconnect() {
    if (this.autoReconnect) {
      this._reconnect();
    } else {
      // 拒绝所有待处理命令
      this.pendingCommands.forEach((pending, id) => {
        clearTimeout(pending.timeout);
        pending.reject(new Error('连接断开'));
      });
      this.pendingCommands.clear();
    }
  }

  /**
   * 重新连接
   */
  _reconnect() {
    if (this.reconnectTimer) return;
    
    console.log(`[Temi] 将在 ${this.reconnectInterval/1000} 秒后重新连接...`);
    this.reconnectTimer = setTimeout(() => {
      this.reconnectTimer = null;
      this.connect().catch(() => {
        // 重试将由 _handleDisconnect 处理
      });
    }, this.reconnectInterval);
  }

  /**
   * 处理命令队列
   */
  _processQueue() {
    while (this.commandQueue.length > 0 && this.connected) {
      const { command, resolve, reject, timeout } = this.commandQueue.shift();
      
      if (this.ws.readyState === WebSocket.OPEN) {
        this.pendingCommands.set(command.id, { resolve, reject, timeout, action: command.command });
        this._send(command);
      } else {
        // 重新加入队列
        this.commandQueue.unshift({ command, resolve, reject, timeout });
        break;
      }
    }
  }
}

module.exports = TemiConnector;
