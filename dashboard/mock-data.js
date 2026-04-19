/**
 * Mock dataset — renders the dashboard offline for demos and screenshots.
 * Matches the Bitable field shapes our plugin writes.
 */

const now = Date.now();
const days = (n) => n * 86_400_000;

const mockTools = [];
const toolPool = [
  'feishu_classmate_data_layout',
  'feishu_classmate_supervision_start',
  'feishu_classmate_supervision_tick',
  'feishu_classmate_research_search_works',
  'feishu_classmate_temi_navigate_to',
  'feishu_classmate_temi_speak',
  'feishu_classmate_chat_pick_topic',
  'feishu_classmate_chat_should_engage',
];
for (let i = 0; i < 160; i++) {
  const t = toolPool[Math.floor(Math.random() * toolPool.length)];
  const ok = Math.random() > (t.includes('temi') ? 0.35 : 0.08);
  mockTools.push({
    trace_id: `tr_${i}`,
    tool_name: t,
    ok,
    duration_ms: Math.floor(200 + Math.random() * 1800),
    started_at: now - Math.floor(Math.random() * days(7)),
  });
}

const mockProjects = [
  { project_id: 'p_a', title: 'RLHF Reward Hacking 研究', status: '进行中', updated_at: now - days(1) },
  { project_id: 'p_b', title: 'MuJoCo Manipulation Baseline', status: '进行中', updated_at: now - days(3) },
  { project_id: 'p_c', title: '实验室 SLAM 评测', status: '完成', updated_at: now - days(20) },
  { project_id: 'p_d', title: '多机协同调度', status: '规划中', updated_at: now - days(2) },
  { project_id: 'p_e', title: 'Diffusion Policy 对比', status: '进行中', updated_at: now - days(5) },
];

const mockGantt = [
  { gantt_id: 'g_1', project_id: 'p_a', milestone: '文献调研', status: '完成',   updated_at: now - days(2), due_date: now - days(1) },
  { gantt_id: 'g_2', project_id: 'p_a', milestone: 'baseline 跑通', status: '进行中', updated_at: now - days(1), due_date: now + days(5) },
  { gantt_id: 'g_3', project_id: 'p_b', milestone: '仿真复现', status: '逾期',   updated_at: now - days(4), due_date: now - days(3) },
  { gantt_id: 'g_4', project_id: 'p_d', milestone: '设计 scheduler', status: '进行中', updated_at: now - days(2), due_date: now + days(10) },
  { gantt_id: 'g_5', project_id: 'p_e', milestone: '对比实验结果', status: '完成',   updated_at: now - days(6), due_date: now - days(5) },
  { gantt_id: 'g_6', project_id: 'p_a', milestone: 'paper draft',   status: '未开始', updated_at: now - days(0), due_date: now + days(14) },
];

const mockEquipment = [
  { equipment_id: 'e1', name: '示波器 Tektronix MDO3',   state: '在库' },
  { equipment_id: 'e2', name: '热像仪 FLIR C5',          state: '借出' },
  { equipment_id: 'e3', name: '3D 打印机 Prusa MK4',     state: '维修' },
  { equipment_id: 'e4', name: '显微镜 ZEISS Axio',       state: '在库' },
  { equipment_id: 'e5', name: 'GPU workstation #2',     state: '借出' },
  { equipment_id: 'e6', name: 'OptiTrack 动捕',          state: '在库' },
  { equipment_id: 'e7', name: 'URDF visualization PC',  state: '借出' },
];

const mockSubmissions = [
  { submission_id: 's1', title: 'Paper A',  venue: 'ICRA 2026', status: '审稿中' },
  { submission_id: 's2', title: 'Paper B',  venue: 'CoRL 2026', status: 'major revision' },
  { submission_id: 's3', title: 'Paper C',  venue: 'NeurIPS 2026', status: '已投' },
  { submission_id: 's4', title: 'Paper D',  venue: 'RSS 2026',  status: '已接收' },
  { submission_id: 's5', title: 'Paper E',  venue: 'IROS 2026', status: '准备中' },
];

const mockFailures = [
  {
    failure_id: 'f1',
    title: 'PPO 训练 reward 持续发散',
    category: '训练',
    hours_wasted: 12,
    workaround_or_lesson_md: '初始 lr 设太高(3e-3),降到 3e-4 就稳了。另外 entropy coef 不能给 0,否则塌缩',
  },
  {
    failure_id: 'f2',
    title: 'MuJoCo xml 自碰撞检测失效',
    category: '仿真',
    hours_wasted: 4,
    workaround_or_lesson_md: 'margin 属性默认 0,必须显式设 0.001 以上,不然小接触面直接穿模',
  },
  {
    failure_id: 'f3',
    title: 'Docker container 里 CUDA 看不见 GPU',
    category: '环境配置',
    hours_wasted: 3,
    workaround_or_lesson_md: '主机没装 nvidia-container-toolkit;装完 systemctl restart docker 即可',
  },
  {
    failure_id: 'f4',
    title: 'Diffusion policy 训出 flat action',
    category: '调参',
    hours_wasted: 8,
    workaround_or_lesson_md: 'noise schedule 用了 cosine 但 beta_max 太小,action 都接近 0。换成 linear [1e-4, 0.02]',
  },
  {
    failure_id: 'f5',
    title: '飞书 bitable 写入 99991672',
    category: '部署',
    hours_wasted: 1,
    workaround_or_lesson_md: '应用身份权限开了 tenant 但没发新版本 — 必须创建新版本并发布',
  },
];

export async function loadMockData() {
  // simulate latency so the demo feels realistic
  await new Promise((r) => setTimeout(r, 200));
  return {
    tools: mockTools,
    projects: mockProjects,
    gantt: mockGantt,
    equipment: mockEquipment,
    submissions: mockSubmissions,
    failures: mockFailures,
  };
}
