/**
 * Temi 自然语言控制工具
 * 将中文自然语言指令解析为 Temi 命令，通过 HTTP sidecar 执行
 *
 * Sidecar 已实现的端点（server.py）：
 *   POST /goto, /speak, /stop, /turn, /tilt, /move, /ask,
 *        /wakeup, /follow-start, /follow-stop,
 *        /detection-start, /detection-stop,
 *        /save-location, /delete-location,
 *        /detect-person, /rfid-scan, /monitor-focus, /gesture
 *   GET  /status
 */

import type { OpenClawPluginApi } from 'openclaw/plugin-sdk';
import { z } from 'zod';
import { getConfigFromApi } from '../../config.js';
import { temiClient } from './client.js';
import { registerZodTool } from '../../util/register-tool.js';
import { TemiNLP } from './nlp.js';

const SUGGESTIONS = [
  '试试说：「说 你好」',
  '试试说：「去 入口」',
  '试试说：「停下」',
  '试试说：「转一圈」',
  '试试说：「拍照」',
  '试试说：「电量」',
];

const Input = z.object({
  instruction: z.string().describe(
    'Temi 机器人的自然语言控制指令。支持：\n' +
    '· 说话：「说 XXX」「告诉 XXX」\n' +
    '· 提问：「问 XXX」（等待回答）\n' +
    '· 导航：「去 XXX」「到 XXX」（地点：入口、充电桩、工位区等）\n' +
    '· 旋转：「左转」「右转」「转一圈」「转 N 度」\n' +
    '· 倾斜：「抬头」「低头」「倾斜 N 度」\n' +
    '· 移动：「前进」「后退」「向左」「向右」\n' +
    '· 停止：「停下」「停止」「别动」\n' +
    '· 唤醒：「唤醒」\n' +
    '· 跟随：「跟着我」「停止跟随」\n' +
    '· 检测：「打开检测」「关闭检测」\n' +
    '· 拍照：「拍照」「拍张照」\n' +
    '· 状态：「电量」「状态」\n' +
    '· 位置：「记住这里，叫 XXX」「删除位置 XXX」'
  ),
});

const Output = z.object({
  ok: z.boolean(),
  mock: z.boolean(),
  action: z.string().optional(),
  message: z.string().optional(),
  error: z.string().optional(),
  suggestions: z.array(z.string()).optional(),
});

const nlp = new TemiNLP();

/** 动作 → sidecar HTTP 端点映射（全部使用真实端点） */
const SUPPORTED_ACTIONS: Array<{
  actions: string[];
  method: 'post' | 'get';
  path: string;
  body?: (params: Record<string, unknown>) => Record<string, unknown>;
}> = [
  // 说话
  { actions: ['speak'],           method: 'post', path: '/speak' },
  // 提问（等待回答）
  { actions: ['ask'],             method: 'post', path: '/ask' },
  // 导航
  { actions: ['goto'],            method: 'post', path: '/goto' },
  // 旋转
  { actions: ['turn'],            method: 'post', path: '/turn',
    body: p => ({ degrees: p.degrees ?? 90, speed: p.speed ?? 0.5 }) },
  { actions: ['turnLeft'],       method: 'post', path: '/turn',
    body: p => ({ degrees: -(Math.abs(Number(p.degrees)) || 90), speed: 0.5 }) },
  { actions: ['turnRight'],       method: 'post', path: '/turn',
    body: p => ({ degrees: Math.abs(Number(p.degrees)) || 90, speed: 0.5 }) },
  // 倾斜
  { actions: ['tilt'],            method: 'post', path: '/tilt',
    body: p => ({ degrees: p.degrees ?? 15, speed: 0.5 }) },
  { actions: ['tiltUp'],         method: 'post', path: '/tilt',
    body: p => ({ degrees: Math.abs(Number(p.degrees)) || 15, speed: 0.5 }) },
  { actions: ['tiltDown'],       method: 'post', path: '/tilt',
    body: p => ({ degrees: -(Math.abs(Number(p.degrees)) || 15), speed: 0.5 }) },
  // 移动（skidJoy）
  { actions: ['moveForward'],     method: 'post', path: '/move', body: () => ({ x: 1, y: 0 }) },
  { actions: ['moveBackward'],    method: 'post', path: '/move', body: () => ({ x: -1, y: 0 }) },
  { actions: ['moveLeft'],        method: 'post', path: '/move', body: () => ({ x: 0, y: 1 }) },
  { actions: ['moveRight'],       method: 'post', path: '/move', body: () => ({ x: 0, y: -1 }) },
  // 停止
  { actions: ['stop'],            method: 'post', path: '/stop', body: () => ({ immediate: true }) },
  // 唤醒
  { actions: ['wakeup'],          method: 'post', path: '/wakeup' },
  // 跟随
  { actions: ['beWithMe'],       method: 'post', path: '/follow-start' },
  { actions: ['stopFollow'],      method: 'post', path: '/follow-stop' },
  // 检测
  { actions: ['startDetecting'],  method: 'post', path: '/detection-start' },
  { actions: ['stopDetecting'],   method: 'post', path: '/detection-stop' },
  // 位置管理
  { actions: ['saveLocation'],    method: 'post', path: '/save-location',
    body: p => ({ name: String(p.locationName ?? p.name ?? '') }) },
  { actions: ['deleteLocation'], method: 'post', path: '/delete-location',
    body: p => ({ name: String(p.locationName ?? p.name ?? '') }) },
  // 状态查询
  { actions: ['status'],          method: 'get',  path: '/status' },
];

function findEndpoint(action: string) {
  return SUPPORTED_ACTIONS.find(e => e.actions.includes(action)) ?? null;
}

const MOCK_RETURNS: Record<string, Record<string, unknown>> = {
  speak:          { ok: true, message: '（模拟）Temi 说：xxx' },
  ask:            { ok: true },
  goto:           { ok: true, message: '（模拟）Temi 已导航到 xxx' },
  turn:           { ok: true, message: '（模拟）Temi 旋转了 xxx 度' },
  turnLeft:       { ok: true, message: '（模拟）Temi 向左转了' },
  turnRight:      { ok: true, message: '（模拟）Temi 向右转了' },
  tilt:           { ok: true, message: '（模拟）Temi 倾斜了' },
  tiltUp:         { ok: true, message: '（模拟）Temi 抬头了' },
  tiltDown:       { ok: true, message: '（模拟）Temi 低头了' },
  moveForward:    { ok: true, message: '（模拟）Temi 前进了' },
  moveBackward:   { ok: true, message: '（模拟）Temi 后退了' },
  moveLeft:       { ok: true, message: '（模拟）Temi 向左移动了' },
  moveRight:      { ok: true, message: '（模拟）Temi 向右移动了' },
  stop:           { ok: true, message: '（模拟）Temi 已停止' },
  wakeup:         { ok: true },
  beWithMe:       { ok: true, message: '（模拟）Temi 进入跟随模式' },
  stopFollow:     { ok: true, message: '（模拟）Temi 退出跟随模式' },
  startDetecting: { ok: true, message: '（模拟）人员检测已开启' },
  stopDetecting:  { ok: true, message: '（模拟）人员检测已关闭' },
  saveLocation:   { ok: true, message: '（模拟）位置已保存' },
  deleteLocation: { ok: true, message: '（模拟）位置已删除' },
  status:         { connected: true, battery: 87, position: { x: 1.2, y: 0.5 }, is_moving: false },
};

export function registerTemiControl(api: OpenClawPluginApi): void {
  registerZodTool(api, {
    name: 'feishu_classmate_temi_control',
    description:
      '用自然语言控制 Temi 机器人（中文）。支持：「转一圈」「去入口」「说你好」「停下」「前进」「抬头」「跟着我」「记住这里，叫 XXX」「电量」等各种指令。',
    inputSchema: Input,
    outputSchema: Output,
    async execute(input) {
      const cfg = getConfigFromApi(api);
      const parsed = nlp.parse(input.instruction);

      if (!parsed) {
        return {
          ok: false,
          mock: false,
          message: `无法理解指令：「${input.instruction}」`,
          suggestions: SUGGESTIONS,
        };
      }

      const { action, params } = parsed;
      const endpoint = findEndpoint(action);

      if (!endpoint) {
        return {
          ok: false,
          mock: false,
          action,
          message: `不支持的动作：「${action}」`,
          suggestions: SUGGESTIONS,
        };
      }

      const mockReturn = MOCK_RETURNS[action] ?? { ok: true };

      if (endpoint.method === 'get') {
        const res = await temiClient.get(cfg, endpoint.path, { mockReturn });
        const data = res.data as Record<string, unknown>;
        return {
          ok: res.ok,
          mock: res.mock,
          action,
          message: res.mock
            ? `（mock）连接=${data?.connected}，电量=${data?.battery}%，位置=(${data?.position})`
            : `连接正常，电量=${data?.battery}%，位置=(${data?.position})`,
          error: res.error,
        };
      } else {
        const body = endpoint.body ? endpoint.body(params) : {};
        const res = await temiClient.post(cfg, endpoint.path, body, { mockReturn });
        const data = res.data as { message?: string } | undefined;
        return {
          ok: res.ok,
          mock: res.mock,
          action,
          message: data?.message ?? (res.mock ? `（mock）动作 ${action} 已执行` : undefined),
          error: res.error,
        };
      }
    },
  });
}
