---
name: robot-checkpoint
description: |
  机器人策略 checkpoint 归档、元数据注释、A/B 对比与部署状态跟踪。所有 bitable
  操作走 `feishu_bitable_app_table_record`,本 skill 只做对话编排、metric 对比
  呈现与业务校验。

  **触发词**: "保存这个 checkpoint"、"归档权重"、"compare policy X vs Y"、
  "比较 ckpt_v2 和 ckpt_v3"、"deploy v3 checkpoint"、"上生产"、"标记废弃"。
---

# 策略 Checkpoint Skill

## 前置:拿数据布局

```
feishu_classmate_data_layout()
  → { app_token, tables: { ..., checkpoints?, training_runs? } }
```

`tables.checkpoints` 不存在 → 提示 admin 跑 `setup-bitable`,停止。

## 场景 A:归档一个 checkpoint

示例: `保存这个 checkpoint: run_17340... tag=v1.2-best, s3://bucket/ckpt/best.pt, success=0.87, reward=842`

1. **校验 run_id 存在**(否则是野 checkpoint,拒绝):
   ```
   feishu_bitable_app_table_record({ action:"list", table_id: <training_runs>,
     filter: "CurrentValue.[run_id]=\"run_17340...\"" })
   ```
   找不到 → 引导先去 [training-run-tracker](../training-run-tracker/SKILL.md) 登记
2. 追问缺失字段:`eval_env`、`evaluated_on_real`(布尔),`deploy_status` 默认 `开发`
3. **create Checkpoints**:
   ```
   feishu_bitable_app_table_record({ action:"create", table_id: <checkpoints>, fields: {
     ckpt_id: "ckpt_<Date.now()>_<rand6>", run_id: "run_17340...",
     tag: "v1.2-best", artifact_url: "https://s3.../best.pt",  // 必须 http(s)
     eval_env: "PickCube-real", success_rate: 0.87, avg_reward: 842,
     evaluated_on_real: false, deploy_status: "开发",
     notes: "<学生原话>", saved_at: Date.now() }})
   ```
4. 回复 `ckpt_id` + 建议下一步(A/B 对比 / 升级到测试)

## 场景 B:A/B 对比两个 checkpoint

示例: `比较 ckpt_v2 和 ckpt_v3`

1. **一次 OR filter 拉两行**:
   ```
   filter: "OR(CurrentValue.[ckpt_id]=\"ckpt_v2\", CurrentValue.[ckpt_id]=\"ckpt_v3\")"
   ```
2. 只拿到 1 条 → 报错"找不到 ckpt_xxx"
3. **警告不可比**:两条 `eval_env` 不同 → 先警告"评测环境不同,对比仅供参考",继续
4. **输出 markdown 对比表**(Agent 本地拼,不调 tool):

   | metric | ckpt_v2 | ckpt_v3 | winner |
   |---|---|---|---|
   | success_rate | 0.82 | 0.87 | **ckpt_v3** ↑ |
   | avg_reward | 812 | 842 | **ckpt_v3** ↑ |
   | evaluated_on_real | ❌ | ✅ | ckpt_v3 |
   | deploy_status | 开发 | 测试 | — |

5. 末尾结论: "ckpt_v3 在 2/2 主指标占优,建议推到测试/生产"
6. 学生追一句 `上生产` → 进入场景 C

## 场景 C:更新部署状态

示例: `deploy ckpt_v3 到生产` / `ckpt_v2 废弃`

1. 定位 record_id: filter `ckpt_id="ckpt_v3"`
2. **业务规则**:
   - 推到 `生产` 前必须 `evaluated_on_real == true`,否则反问"没真机验证过,force 上生产吗?"
   - 同一 `eval_env` 已有 `deploy_status=生产` 的 ckpt → 先降级为 `已废弃`:
     ```
     filter: "AND(CurrentValue.[eval_env]=\"...\", CurrentValue.[deploy_status]=\"生产\")"
     → 对每条 update { deploy_status: "已废弃" }
     ```
3. **update 目标**: `fields: { deploy_status: "生产", notes: "<追加部署时间戳>" }`
4. 回复 + 建议在广播群通知团队

## 需要新建的多维表

### Checkpoints

| 字段 | 类型 | 说明 |
|---|---|---|
| `ckpt_id` | Text (pk) | `ckpt_<ts>_<rand>` |
| `run_id` | Text | FK → TrainingRuns.run_id (由 [training-run-tracker](../training-run-tracker/SKILL.md) 管理) |
| `tag` | Text | 语义 tag,e.g. `v1.2.3-best` |
| `artifact_url` | Url | S3/OSS/本地路径链接 |
| `eval_env` | Text | 评测环境名 |
| `success_rate` | Number (0.00%) | 0~1 小数 |
| `avg_reward` | Number (0.00) | — |
| `evaluated_on_real` | Checkbox | 是否真机测过 |
| `deploy_status` | SingleSelect | 枚举见下 |
| `notes` | Text | — |
| `saved_at` | DateTime | 毫秒 |

## 枚举值强约束

| 字段 | 有效值 |
|---|---|
| `deploy_status` | `开发`、`测试`、`生产`、`已废弃` |
| `evaluated_on_real` | `true` / `false` (Checkbox) |

`success_rate` 一律存 `0~1` 小数(bitable formatter 显示百分比)。学生给 `87%` / `87` 统一归一化到 `0.87`。

## 失败降级

- `tables.checkpoints` 不存在 → 引导 admin 跑 `setup-bitable`
- `artifact_url` 非 http(s) 开头 → 提示补全前缀;坚持本地路径 → 退而求其次存到 `notes`,`artifact_url` 留空
- A/B 对比两条都不存在 → 列最近 5 个 ckpt 让学生选
- `code 1254xxx` (枚举错) → 自查 `deploy_status` 表,重试一次
