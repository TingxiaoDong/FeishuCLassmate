---
name: training-run-tracker
description: |
  记录每一次 RL/ML 训练实验,包含算法、超参、tracker 链接(W&B / TensorBoard)
  和最终指标。所有 bitable 操作走 `feishu_bitable_app_table_record`,本 skill 只
  负责对话流程、结构化抽取与字段校验。

  **触发词**: "记一下这次训练"、"new run"、"start experiment"、"开跑 PPO"、
  "记一下实验"、学生粘贴 W&B / TensorBoard / wandb.ai / tensorboard.dev 链接。
---

# 训练实验记录 Skill

## 前置:拿数据布局

```
feishu_classmate_data_layout()
  → { app_token, tables: { projects, training_runs?, ... } }
```

`tables.training_runs` 不存在 → 提示 admin 跑 `setup-bitable`,停止。

## 场景 A:开跑新实验

示例: `记一下这次训练:PPO 跑 HalfCheetah,seed 42,lr=3e-4,wandb.ai/lab/proj/runs/abc`

1. **确认所属项目**:学生没说 `project_id` → list Projects
   (由 [manage-gantt](../manage-gantt/SKILL.md) 管理)让他选 (`feishu_ask_user_question`)
2. **结构化抽取**(LLM 自做):
   ```
   { algorithm, env_name, commit_hash, seed, hyperparams, wandb_url, tb_url }
   ```
   - `algorithm` 归一到枚举,否则 `其他`
   - `commit_hash` 若没给,提示 `git rev-parse --short HEAD`
3. **写 TrainingRuns**:
   ```
   feishu_bitable_app_table_record({ action:"create", table_id: <training_runs>, fields: {
     run_id: "run_<Date.now()>_<rand6>",
     project_id: "<project_id>", student_open_id: [{id:"<ou>"}],
     algorithm: "PPO", env_name: "HalfCheetah-v4", commit_hash: "a1b2c3d", seed: 42,
     hyperparams_json: JSON.stringify({ lr: 3e-4, batch: 64 }),
     wandb_url: "https://wandb.ai/...", tb_url: "",
     status: "训练中", started_at: Date.now() }})
   ```
4. 回复 `run_id` + 提醒"跑完回来说 `<run_id> 完成,reward=...`"

> 背景 cron 提醒(未实装):`training-run-sweeper` 定时扫 `status=训练中` 且 `started_at` > 48h 的 run,主动 ping 学生更新。

## 场景 B:训练结束回填指标

示例: `run_1734... 完成了,final=8450 best=8920 gpu_hours=12.5`

1. filter `run_id="run_1734..."` 拿 record_id
2. **update**:
   ```
   fields: { status: "完成", final_reward: 8450, best_reward: 8920,
     gpu_hours: 12.5, completed_at: Date.now() }
   ```
3. 回复"已归档 ✅,下一步 `保存这个 checkpoint` 把最好权重归档"
   (引导到 [robot-checkpoint](../robot-checkpoint/SKILL.md))

## 场景 C:查询训练历史

`我最近跑了哪些 PPO?`

```
feishu_bitable_app_table_record({ action:"list",
  filter: "AND(CurrentValue.[student_open_id]=[{\"id\":\"ou_xxx\"}], CurrentValue.[algorithm]=\"PPO\")",
  field_names: ["run_id","env_name","final_reward","best_reward","status","started_at"] })
```
按 `started_at` 倒序输出 markdown 表格,≤ 10 行。

## 需要新建的多维表

### TrainingRuns

| 字段 | 类型 | 说明 |
|---|---|---|
| `run_id` | Text (pk) | `run_<ts>_<rand>` |
| `project_id` | Text | FK → Projects.project_id |
| `student_open_id` | User | 实验发起人 |
| `algorithm` | SingleSelect | 枚举见下 |
| `env_name` | Text | e.g. `HalfCheetah-v4` |
| `commit_hash` | Text | 短 hash 7~12 位 |
| `seed` | Number (0) | — |
| `hyperparams_json` | Text (long) | JSON.stringify 后的超参 |
| `wandb_url` | Url | W&B run 链接 |
| `tb_url` | Url | TensorBoard 链接 |
| `final_reward` | Number (0.00) | — |
| `best_reward` | Number (0.00) | — |
| `status` | SingleSelect | 枚举见下 |
| `started_at` | DateTime | 毫秒 |
| `completed_at` | DateTime | 毫秒 |
| `gpu_hours` | Number (0.0) | — |

## 枚举值强约束

| 字段 | 有效值 |
|---|---|
| `algorithm` | `PPO`、`SAC`、`GRPO`、`DQN`、`DDPG`、`其他` |
| `status` | `训练中`、`完成`、`失败`、`中断` |

写错报 `FieldConvFail` (code 125406X),自查后用正确值重试一次。

## 失败降级

- `tables.training_runs` 不存在 → 引导 admin 跑 `setup-bitable`
- 学生给的 `wandb_url` 不是 http(s) 开头 → 先校正再写
- `code 99991672` (缺 scope) → "权限不足,请 admin 联系"
- `hyperparams_json` 超过 bitable 文本长度上限 → 截断前 20 KB 并末尾加 `...[truncated]`
