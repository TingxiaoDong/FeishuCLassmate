/**
 * Temi NLP — 自然语言指令解析器
 * 将中文自然语言转换为 Temi 控制命令
 *
 * 移植自 temi-connector/temi-nlp.js，适配 feishu-classmate 的工具接口。
 */

export interface ParsedCommand {
  action: string;
  params: Record<string, unknown>;
  confidence: number;
}

const LOCATION_ALIASES: Record<string, string[]> = {
  '入口': ['前台', 'reception', '接待处', '门口', '大门', 'entrance'],
  '餐桌': ['饭厅', '餐厅', 'dining table', '吃饭的地方', '饭桌'],
  '厨房': ['kitchen', '做饭的地方', '后厨', '烹饪区'],
  '充电站': ['充电桩', '充电', 'home', '回家', '充电区'],
};

export class TemiNLP {
  private locationAliases: Record<string, string[]>;

  constructor() {
    this.locationAliases = { ...LOCATION_ALIASES };
  }

  /**
   * 解析自然语言指令
   * @returns ParsedCommand 或 null（无法解析）
   */
  parse(input: string): ParsedCommand | null {
    if (!input || typeof input !== 'string') return null;
    const text = input.trim();

    // ── 说话 ──────────────────────────────────────────────
    if (this.containsAny(text, ['说', '告诉', '播报', '喊', '讲'])) {
      const sentence = text
        .replace(/.*?(?:说|告诉|播报|喊|讲)[:：]?\s*/, '')
        .trim();
      if (sentence) {
        return { action: 'speak', params: { text: sentence, voice: 'friendly' }, confidence: 0.9 };
      }
    }

    // ── 提问（ask）───────────────────────────────────────
    if (this.containsAny(text, ['问', '提问', '问问'])) {
      const sentence = text.replace(/.*?(?:问|提问)[:：]?\s*/, '').trim();
      if (sentence) {
        return { action: 'ask', params: { text: sentence }, confidence: 0.9 };
      }
    }

    // ── 导航（去/到/导航/前往）────────────────────────────
    if (this.containsAny(text, ['去', '到', '导航', '前往', '走过去', '走去'])) {
      const match = text.match(/(?:去|到|导航|前往|走过去|走去)\s*([^\s，,。!！?？]+)/);
      if (match) {
        return {
          action: 'goto',
          params: { location: this.resolveLocation(match[1]) },
          confidence: 0.9,
        };
      }
    }

    // ── 左转 / 逆时针旋转 ─────────────────────────────────
    if (this.containsAny(text, ['左转', '逆时针', '向左转', '往左转'])) {
      const angleMatch = text.match(/(\d+)\s*度/);
      const angle = angleMatch ? -parseInt(angleMatch[1]) : -90;
      return { action: 'turn', params: { angle }, confidence: 0.9 };
    }

    // ── 右转 / 顺时针旋转 ─────────────────────────────────
    if (this.containsAny(text, ['右转', '顺时针', '向右转', '往右转'])) {
      const angleMatch = text.match(/(\d+)\s*度/);
      const angle = angleMatch ? parseInt(angleMatch[1]) : 90;
      return { action: 'turn', params: { angle }, confidence: 0.9 };
    }

    // ── 原地转一圈 ────────────────────────────────────────
    if (text.includes('转一圈') || text.includes('旋转') || text.includes('自转')) {
      return { action: 'turn', params: { angle: 360 }, confidence: 0.9 };
    }

    // ── 抬头 / 向上倾斜 ──────────────────────────────────
    if (this.containsAny(text, ['抬头', '向上', '仰头'])) {
      const angleMatch = text.match(/(\d+)\s*度/);
      return { action: 'tilt', params: { angle: angleMatch ? parseInt(angleMatch[1]) : 15 }, confidence: 0.9 };
    }

    // ── 低头 / 向下倾斜 ──────────────────────────────────
    if (this.containsAny(text, ['低头', '向下', '俯身'])) {
      const angleMatch = text.match(/(\d+)\s*度/);
      return { action: 'tilt', params: { angle: angleMatch ? -parseInt(angleMatch[1]) : -15 }, confidence: 0.9 };
    }

    // ── 停止 ──────────────────────────────────────────────
    if (this.containsAny(text, ['停下', '停止', '停', '别动', '立定', '刹车'])) {
      return { action: 'stop', params: { immediate: true }, confidence: 0.9 };
    }

    // ── 前进 ─────────────────────────────────────────────
    if (this.containsAny(text, ['向前', '前进', '往前走', '往前', '向前走'])) {
      return { action: 'move', params: { x: 0.5, y: 0 }, confidence: 0.9 };
    }

    // ── 后退 ─────────────────────────────────────────────
    if (this.containsAny(text, ['向后', '后退', '往后走', '往后', '后退走'])) {
      return { action: 'move', params: { x: -0.5, y: 0 }, confidence: 0.9 };
    }

    // ── 向左横移 ─────────────────────────────────────────
    if (this.containsAny(text, ['向左', '往左走', '左移'])) {
      return { action: 'move', params: { x: 0, y: -0.5 }, confidence: 0.9 };
    }

    // ── 向右横移 ─────────────────────────────────────────
    if (this.containsAny(text, ['向右', '往右走', '右移'])) {
      return { action: 'move', params: { x: 0, y: 0.5 }, confidence: 0.9 };
    }

    // ── 打开摄像头 ────────────────────────────────────────
    if (this.containsAny(text, ['打开摄像头', '启动摄像头', '开摄像头', '开启摄像头'])) {
      return { action: 'startCamera', params: {}, confidence: 0.9 };
    }

    // ── 关闭摄像头 ────────────────────────────────────────
    if (this.containsAny(text, ['关闭摄像头', '关掉摄像头', '关摄像头', '关掉摄像头'])) {
      return { action: 'stopCamera', params: {}, confidence: 0.9 };
    }

    // ── 拍照 ──────────────────────────────────────────────
    if (this.containsAny(text, ['拍照', '拍张照', '拍个照', '照相', '拍摄'])) {
      return { action: 'takePicture', params: {}, confidence: 0.9 };
    }

    // ── 记住当前位置 ─────────────────────────────────────
    if (text.includes('记住这里') || text.includes('保存位置') || text.includes('记下这个位置')) {
      const locationName = this.extractLocationName(text);
      if (locationName) {
        return { action: 'saveLocation', params: { locationName }, confidence: 0.9 };
      }
    }

    // ── 删除位置 ──────────────────────────────────────────
    if (this.containsAny(text, ['删除位置', '忘掉位置', '删除这个位置'])) {
      const locationName = text.replace(/(?:删除位置|忘掉位置|删除这个位置)/, '').trim();
      if (locationName) {
        return { action: 'deleteLocation', params: { locationName }, confidence: 0.9 };
      }
    }

    // ── 跟随模式 ─────────────────────────────────────────
    if (this.containsAny(text, ['跟着我', '跟我走', '跟随', '跟上来'])) {
      return { action: 'beWithMe', params: {}, confidence: 0.9 };
    }

    // ── 人员检测开关 ─────────────────────────────────────
    if ((text.includes('打开') || text.includes('启用') || text.includes('开启')) &&
        this.containsAny(text, ['检测', '人员检测', '侦测'])) {
      return { action: 'setDetectionMode', params: { on: true }, confidence: 0.8 };
    }
    if ((text.includes('关闭') || text.includes('禁用') || text.includes('关掉')) &&
        this.containsAny(text, ['检测', '人员检测', '侦测'])) {
      return { action: 'setDetectionMode', params: { on: false }, confidence: 0.8 };
    }

    // ── 跟踪用户开关 ─────────────────────────────────────
    if ((text.includes('打开') || text.includes('启用') || text.includes('开启')) &&
        this.containsAny(text, ['跟踪', '追踪'])) {
      return { action: 'setTrackUserOn', params: { on: true }, confidence: 0.8 };
    }
    if ((text.includes('关闭') || text.includes('禁用') || text.includes('关掉')) &&
        this.containsAny(text, ['跟踪', '追踪'])) {
      return { action: 'setTrackUserOn', params: { on: false }, confidence: 0.8 };
    }

    // ── 回到充电桩 ────────────────────────────────────────
    if (this.containsAny(text, ['回充电桩', '回去充电', '回桩', '回home', '回home充电'])) {
      return { action: 'goto', params: { location: '充电桩' }, confidence: 0.9 };
    }

    // ── 模糊匹配兜底 ─────────────────────────────────────
    return this.fuzzyMatch(text);
  }

  /**
   * 模糊匹配 — 处理没有明确指令的输入
   */
  private fuzzyMatch(text: string): ParsedCommand | null {
    if (this.containsAny(text, ['说', '告诉', '喊'])) {
      const sentence = text.replace(/^(?:说|告诉|喊)\s*/, '').trim();
      return { action: 'speak', params: { text: sentence || text, voice: 'friendly' }, confidence: 0.6 };
    }
    if (this.containsAny(text, ['去', '到', '导航'])) {
      const location = text.replace(/^(?:去|到|导航)\s*/, '').trim();
      return { action: 'goto', params: { location: this.resolveLocation(location) }, confidence: 0.6 };
    }
    if (this.containsAny(text, ['停', '别动'])) {
      return { action: 'stop', params: { immediate: false }, confidence: 0.6 };
    }
    if (this.containsAny(text, ['拍照', '照'])) {
      return { action: 'takePicture', params: {}, confidence: 0.6 };
    }
    if (text.includes('状态') || text.includes('电量')) {
      return { action: 'status', params: {}, confidence: 0.6 };
    }
    return null;
  }

  /**
   * 将别名地址解析为标准地址
   */
  resolveLocation(name: string): string {
    if (!name) return name;
    for (const [canonical, aliases] of Object.entries(this.locationAliases)) {
      if (name === canonical || aliases.some(alias => name.includes(alias))) {
        return canonical;
      }
    }
    return name;
  }

  /**
   * 添加地点别名
   */
  addLocationAlias(canonical: string, aliases: string[]): void {
    if (!this.locationAliases[canonical]) {
      this.locationAliases[canonical] = [];
    }
    this.locationAliases[canonical].push(...aliases);
  }

  private containsAny(text: string, keywords: string[]): boolean {
    return keywords.some(kw => text.includes(kw));
  }

  private extractLocationName(text: string): string {
    const keywords = ['叫', '为', '叫做', '名为', '名字是', '命名为'];
    for (const kw of keywords) {
      const idx = text.indexOf(kw);
      if (idx >= 0) {
        const name = text.substring(idx + kw.length).trim();
        if (name) return name;
      }
    }
    const cleaned = text
      .replace(/记住这里/, '')
      .replace(/保存位置/, '')
      .replace(/记下这个位置/, '')
      .trim();
    return cleaned;
  }
}
