/**
 * Temi 自然语言解析器
 * 将用户指令转换为 Temi 控制命令
 */

class TemiNLP {
  constructor() {
    this.locationAliases = {
      '接待台': ['前台', 'reception', '接待处'],
      '会议室': ['meeting room', '开会的地方'],
      '办公室': ['office', '办公区'],
      '门口': ['入口', '大门', 'entrance'],
      '充电站': ['充电', 'charging', 'home']
    };
  }

  parse(input) {
    if (!input || typeof input !== 'string') return null;
    const text = input.trim();

    // 说话
    if (text.includes('说') || text.includes('告诉') || text.includes('播报')) {
      const sentence = text.replace(/.*?(说 | 告诉 | 播报)[:：]?\s*/, '');
      if (sentence) return { action: 'speak', params: { sentence }, confidence: 0.9 };
    }

    // 提问
    if (text.includes('问') || text.includes('提问')) {
      const sentence = text.replace(/.*?(问 | 提问)[:：]?\s*/, '');
      if (sentence) return { action: 'ask', params: { sentence }, confidence: 0.9 };
    }

    // 导航
    if (text.includes('去') || text.includes('到') || text.includes('导航') || text.includes('前往')) {
      const match = text.match(/(去 | 到 | 导航 | 前往)\s*(\w+)/);
      if (match) {
        return { action: 'goto', params: { location: this._resolveLocation(match[2]) }, confidence: 0.9 };
      }
    }

    // 旋转
    if (text.includes('左转') || text.includes('逆时针')) {
      const angleMatch = text.match(/(\d+)/);
      return { action: 'turn', params: { angle: angleMatch ? -parseInt(angleMatch[1]) : -90 }, confidence: 0.9 };
    }
    if (text.includes('右转') || text.includes('顺时针')) {
      const angleMatch = text.match(/(\d+)/);
      return { action: 'turn', params: { angle: angleMatch ? parseInt(angleMatch[1]) : 90 }, confidence: 0.9 };
    }

    // 倾斜
    if (text.includes('抬头') || text.includes('向上')) {
      const angleMatch = text.match(/(\d+)/);
      return { action: 'tilt', params: { angle: angleMatch ? parseInt(angleMatch[1]) : 15 }, confidence: 0.9 };
    }
    if (text.includes('低头') || text.includes('向下')) {
      const angleMatch = text.match(/(\d+)/);
      return { action: 'tilt', params: { angle: angleMatch ? -parseInt(angleMatch[1]) : -15 }, confidence: 0.9 };
    }

    // 停止
    if (text.includes('停下') || text.includes('停止') || text.includes('停') || text.includes('别动')) {
      return { action: 'stop', params: {}, confidence: 0.9 };
    }

    // 移动
    if (text.includes('向前') || text.includes('前进') || text.includes('往前走')) {
      return { action: 'move', params: { x: 0.5, y: 0 }, confidence: 0.9 };
    }
    if (text.includes('向后') || text.includes('后退') || text.includes('往后走')) {
      return { action: 'move', params: { x: -0.5, y: 0 }, confidence: 0.9 };
    }
    if (text.includes('向左') || text.includes('往左')) {
      return { action: 'move', params: { x: 0, y: -0.5 }, confidence: 0.9 };
    }
    if (text.includes('向右') || text.includes('往右')) {
      return { action: 'move', params: { x: 0, y: 0.5 }, confidence: 0.9 };
    }

    // 摄像头
    if (text.includes('打开摄像头') || text.includes('启动摄像头') || text.includes('开摄像头')) {
      return { action: 'startCamera', params: {}, confidence: 0.9 };
    }
    if (text.includes('关闭摄像头') || text.includes('关掉摄像头') || text.includes('关摄像头')) {
      return { action: 'stopCamera', params: {}, confidence: 0.9 };
    }
    if (text.includes('拍照') || text.includes('拍张照') || text.includes('拍个照') || text.includes('照相')) {
      return { action: 'takePicture', params: {}, confidence: 0.9 };
    }

    // 位置管理
    if (text.includes('记住这里') || text.includes('保存位置')) {
      const keywords = ['叫', '为', '叫做', '名为'];
      let locationName = '';
      for (const kw of keywords) {
        const idx = text.indexOf(kw);
        if (idx >= 0) {
          locationName = text.substring(idx + kw.length).trim();
          break;
        }
      }
      if (!locationName) {
        locationName = text.replace(/(记住这里 | 保存位置)/g, '').trim();
      }
      if (locationName) {
        return { action: 'saveLocation', params: { locationName }, confidence: 0.9 };
      }
    }
    if (text.includes('删除位置') || text.includes('忘掉')) {
      let locationName = '';
      if (text.includes('删除位置')) {
        locationName = text.replace(/删除位置/g, '').trim();
      } else if (text.includes('忘掉')) {
        locationName = text.replace(/忘掉/g, '').trim();
      }
      if (locationName) {
        return { action: 'deleteLocation', params: { locationName }, confidence: 0.9 };
      }
    }

    // 跟随
    if (text.includes('跟着我') || text.includes('跟我走') || text.includes('跟随')) {
      return { action: 'beWithMe', params: {}, confidence: 0.9 };
    }

    // 检测模式
    if ((text.includes('打开') || text.includes('启用') || text.includes('开启')) && 
        (text.includes('检测') || text.includes('人员检测'))) {
      return { action: 'setDetectionMode', params: { on: true }, confidence: 0.9 };
    }
    if ((text.includes('关闭') || text.includes('禁用') || text.includes('关掉')) && 
        (text.includes('检测') || text.includes('人员检测'))) {
      return { action: 'setDetectionMode', params: { on: false }, confidence: 0.9 };
    }

    // 跟踪用户
    if ((text.includes('打开') || text.includes('启用') || text.includes('开启')) && 
        (text.includes('跟踪') || text.includes('追踪'))) {
      return { action: 'setTrackUserOn', params: { on: true }, confidence: 0.9 };
    }
    if ((text.includes('关闭') || text.includes('禁用') || text.includes('关掉')) && 
        (text.includes('跟踪') || text.includes('追踪'))) {
      return { action: 'setTrackUserOn', params: { on: false }, confidence: 0.9 };
    }

    // 模糊匹配
    return this._fuzzyMatch(text);
  }

  _fuzzyMatch(text) {
    if (text.includes('说') || text.includes('告诉')) {
      return { action: 'speak', params: { sentence: text.replace(/^(说 | 告诉)\s*/, '') }, confidence: 0.6 };
    }
    if (text.includes('去') || text.includes('到')) {
      return { action: 'goto', params: { location: text.replace(/^(去 | 到 | 前往)\s*/, '') }, confidence: 0.6 };
    }
    if (text.includes('停')) {
      return { action: 'stop', params: {}, confidence: 0.6 };
    }
    if (text.includes('拍照')) {
      return { action: 'takePicture', params: {}, confidence: 0.6 };
    }
    return null;
  }

  _resolveLocation(name) {
    if (!name) return name;
    for (const [canonical, aliases] of Object.entries(this.locationAliases)) {
      if (name === canonical || aliases.some(alias => name.includes(alias))) {
        return canonical;
      }
    }
    return name;
  }

  addLocationAlias(canonical, aliases) {
    if (!this.locationAliases[canonical]) {
      this.locationAliases[canonical] = [];
    }
    this.locationAliases[canonical].push(...aliases);
  }
}

module.exports = TemiNLP;
