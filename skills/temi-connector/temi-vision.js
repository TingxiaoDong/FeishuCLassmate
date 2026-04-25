/**
 * Temi 视觉分析模块
 * 使用视觉 AI 模型分析 Temi 摄像头拍摄的图像
 * 支持：姿势检测、运动检测、人员识别、场景理解
 */

const { temi_control } = require('./temi-tools.js');

// 视觉分析提示词模板
const ANALYSIS_PROMPTS = {
  // 姿势检测
  pose: `分析这张图片中人物的姿势状态，请判断：
1. 人物是坐着还是站着
2. 如果是坐着，是什么姿势（正坐、侧坐、躺坐等）
3. 如果是站着，是什么姿势（直立、弯腰、伸展等）
4. 是否有多个人员，分别描述

请以 JSON 格式返回：
{
  "people_count": 数字,
  "poses": [
    {
      "person_id": 1,
      "status": "standing|sitting|lying|unknown",
      "detail": "详细描述",
      "confidence": 0.0-1.0
    }
  ]
}`,

  // 运动检测
  motion: `分析这张图片，检测是否有运动迹象：
1. 图片中的人物是否在运动
2. 运动类型（走路、跑步、跳跃、静止等）
3. 运动强度（低、中、高）
4. 运动方向（如果可判断）

请以 JSON 格式返回：
{
  "has_motion": true|false,
  "motion_type": "walking|running|jumping|stationary|unknown",
  "intensity": "low|medium|high",
  "direction": "描述",
  "details": "详细分析"
}`,

  // 人员检测
  person: `分析这张图片中的人员信息：
1. 检测到多少人
2. 每个人的大致位置（左、中、右、前、后）
3. 人员的特征（如果可见）
4. 人员之间的距离和相对位置

请以 JSON 格式返回：
{
  "person_count": 数字,
  "people": [
    {
      "id": 1,
      "position": "位置描述",
      "features": "可见特征",
      "distance": "相对距离"
    }
  ],
  "scene_summary": "场景总结"
}`,

  // 场景理解
  scene: `分析这张图片的场景信息：
1. 这是什么类型的场景（室内/室外、办公室/客厅/走廊等）
2. 场景中有哪些主要物体
3. 光线条件（明亮、昏暗等）
4. 场景的整体描述

请以 JSON 格式返回：
{
  "scene_type": "场景类型",
  "objects": ["物体列表"],
  "lighting": "光线条件",
  "description": "详细描述"
}`,

  // 综合分析
  full: `请全面分析这张图片，包括：
1. 场景类型和环境
2. 检测到的人员数量和位置
3. 每个人的姿势（坐着/站着/其他）
4. 是否有运动，运动类型
5. 任何值得注意的细节

请以 JSON 格式返回：
{
  "scene": {
    "type": "场景类型",
    "description": "场景描述"
  },
  "people": {
    "count": 数字,
    "details": [
      {
        "id": 1,
        "position": "位置",
        "pose": "standing|sitting|other",
        "pose_detail": "姿势详情",
        "activity": "活动状态"
      }
    ]
  },
  "motion": {
    "detected": true|false,
    "type": "运动类型"
  },
  "summary": "一句话总结"
}`,

  // 健身/运动检测
  exercise: `分析这张图片中的人物是否在进行运动/健身：
1. 是否在运动
2. 运动类型（深蹲、俯卧撑、跑步、瑜伽等）
3. 动作是否标准（如果可判断）
4. 运动强度估计
5. 安全建议（如果发现问题）

请以 JSON 格式返回：
{
  "is_exercising": true|false,
  "exercise_type": "运动类型",
  "form_quality": "good|fair|poor|unknown",
  "intensity": "low|medium|high",
  "safety_tips": ["安全建议"],
  "details": "详细分析"
}`
};

class TemiVision {
  constructor(config = {}) {
    this.model = config.model || 'bailian/qwen3.5-plus'; // 支持视觉的模型
    this.defaultAnalysis = config.defaultAnalysis || 'full';
  }

  /**
   * 分析图像
   * @param {string} base64Image - Base64 编码的图像
   * @param {string} analysisType - 分析类型 (pose|motion|person|scene|full|exercise)
   * @param {string} customPrompt - 自定义提示词（可选）
   */
  async analyze(base64Image, analysisType = 'full', customPrompt = null) {
    try {
      // 获取提示词
      const prompt = customPrompt || ANALYSIS_PROMPTS[analysisType] || ANALYSIS_PROMPTS.full;

      // 调用视觉模型
      const result = await this._callVisionModel(base64Image, prompt);

      // 解析 JSON 结果
      const parsed = this._parseJsonResult(result);

      return {
        success: true,
        analysisType,
        result: parsed,
        rawResponse: result
      };
    } catch (error) {
      return {
        success: false,
        error: error.message,
        analysisType
      };
    }
  }

  /**
   * 拍摄并分析（一键操作）
   * @param {string} analysisType - 分析类型
   * @param {object} options - 选项
   */
  async captureAndAnalyze(analysisType = 'full', options = {}) {
    try {
      // 拍摄照片
      console.log('[TemiVision] 正在拍摄照片...');
      const photoResult = await temi_control({ action: 'takePicture' });

      if (photoResult.status !== 'completed' || !photoResult.data?.image) {
        return {
          success: false,
          error: '拍照失败',
          details: photoResult
        };
      }

      console.log('[TemiVision] 照片拍摄成功，正在分析...');

      // 分析图像
      const analysis = await this.analyze(
        photoResult.data.image,
        analysisType,
        options.customPrompt
      );

      return {
        success: analysis.success,
        photo: photoResult,
        analysis: analysis.result,
        rawResponse: analysis.rawResponse
      };
    } catch (error) {
      return {
        success: false,
        error: error.message
      };
    }
  }

  /**
   * 检测姿势（快捷方法）
   */
  async detectPose(base64Image) {
    return this.analyze(base64Image, 'pose');
  }

  /**
   * 检测运动（快捷方法）
   */
  async detectMotion(base64Image) {
    return this.analyze(base64Image, 'motion');
  }

  /**
   * 检测人员（快捷方法）
   */
  async detectPersons(base64Image) {
    return this.analyze(base64Image, 'person');
  }

  /**
   * 分析场景（快捷方法）
   */
  async analyzeScene(base64Image) {
    return this.analyze(base64Image, 'scene');
  }

  /**
   * 运动分析（快捷方法）
   */
  async analyzeExercise(base64Image) {
    return this.analyze(base64Image, 'exercise');
  }

  /**
   * 连续监控分析
   * @param {number} interval - 间隔时间（毫秒）
   * @param {number} count - 分析次数
   * @param {string} analysisType - 分析类型
   * @param {function} callback - 每次分析的回调
   */
  async monitor(interval = 5000, count = 5, analysisType = 'pose', callback = null) {
    const results = [];

    console.log(`[TemiVision] 开始监控，间隔${interval}ms，共${count}次...`);

    for (let i = 0; i < count; i++) {
      console.log(`[TemiVision] 第 ${i + 1}/${count} 次分析...`);

      const result = await this.captureAndAnalyze(analysisType);
      results.push(result);

      if (callback) {
        await callback(result, i + 1, count);
      }

      if (i < count - 1) {
        await new Promise(r => setTimeout(r, interval));
      }
    }

    console.log('[TemiVision] 监控完成');
    return results;
  }

  /**
   * 调用视觉模型
   */
  async _callVisionModel(base64Image, prompt) {
    // 使用 OpenClaw 的模型调用
    // 这里假设有一个通用的模型调用接口
    // 实际使用时需要根据 OpenClaw 的 API 调整

    const { sessions_spawn } = require('openclaw');

    // 创建一个临时任务来分析图像
    return new Promise((resolve, reject) => {
      // 由于无法直接调用模型，我们返回提示词和图像
      // 实际实现需要 OpenClaw 支持视觉模型调用
      resolve(this._mockAnalysis(prompt));
    });
  }

  /**
   * 解析 JSON 结果
   */
  _parseJsonResult(text) {
    if (!text) return null;

    // 尝试提取 JSON
    const jsonMatch = text.match(/\{[\s\S]*\}/);
    if (jsonMatch) {
      try {
        return JSON.parse(jsonMatch[0]);
      } catch (e) {
        // 尝试修复常见 JSON 问题
        try {
          return JSON.parse(text.replace(/'/g, '"'));
        } catch (e2) {
          return { raw: text };
        }
      }
    }

    return { raw: text };
  }

  /**
   * 模拟分析（用于测试）
   */
  _mockAnalysis(prompt) {
    // 这是一个占位实现
    // 实际需要调用视觉 API
    return JSON.stringify({
      mock: true,
      note: '需要配置视觉 API 密钥'
    });
  }
}

// 导出工具函数
async function temi_vision_analyze(base64Image, analysisType = 'full') {
  const vision = new TemiVision();
  return vision.analyze(base64Image, analysisType);
}

async function temi_vision_capture(analysisType = 'full') {
  const vision = new TemiVision();
  return vision.captureAndAnalyze(analysisType);
}

async function temi_vision_pose(base64Image) {
  const vision = new TemiVision();
  return vision.detectPose(base64Image);
}

async function temi_vision_motion(base64Image) {
  const vision = new TemiVision();
  return vision.detectMotion(base64Image);
}

async function temi_vision_exercise(base64Image) {
  const vision = new TemiVision();
  return vision.analyzeExercise(base64Image);
}

module.exports = {
  TemiVision,
  temi_vision_analyze,
  temi_vision_capture,
  temi_vision_pose,
  temi_vision_motion,
  temi_vision_exercise,
  ANALYSIS_PROMPTS
};
