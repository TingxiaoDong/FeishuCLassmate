---
name: simulation-log
description: |
  仿真实验记录、domain randomization 参数归档、sim-to-real gap 跟踪与可复现性
  检查。所有 bitable 操作走 `feishu_bitable_app_table_record`,本 skill 负责对话
  流程、gap 计算与复现校验编排。

  **触发词**: "sim-real gap"、"仿真结果记一下"、"仿真跑完了"、
  "reproducibility check"、"复现检查"、"跑 3 次同 seed"、
  "MuJoCo 跑完"、"IsaacGym 结果"。
---

# 仿真日志 Skill

## 前置:拿数据布局

```
feishu_classmate_data_layout()
  → { app_token, tables: { ..., sim_runs?, checkpoints? } }
```

`tables.sim_runs` 不存在 → 提示 admin 跑 `setup-bitable`,停止。
`ckpt_id` 外键指向 Checkpoints (由 [robot-checkpoint](../robot-checkpoint/SKILL.md) 管理)。

## 场景 A:登记一次仿真实验

示例: `仿真结果记一下: ckpt_v3 在 IsaacGym 上 success=0.92, mass DR ±20%`

1. **校验 ckpt_id** (list Checkpoints);找不到 → 引导先去 robot-checkpoint 归档
2. **结构化字段**(LLM 本地做):
   - `simulator` 归一化到枚举(`isaacgym` → `IsaacGym`)
   - `domain_rand_json` 至少记 `mass_range`、`friction_range`、`lighting_range`
   - `physics_params_json` 记 `timestep`、`solver`、`gravity`
   - `reproduce_command` **必填**,要求完整 `python train.py --cfg ... --seed ...`
3. **算 gap**(Agent 本地): `gap = (sim - real) / sim * 100` (real 空时 gap 为 null)
4. **create SimRuns**:
   ```
   feishu_bitable_app_table_record({ action:"create", table_id: <sim_runs>, fields: {
     sim_id: "sim_<ts>_<rand>", ckpt_id: "ckpt_v3", simulator: "IsaacGym",
     domain_rand_json: JSON.stringify({...}), physics_params_json: JSON.stringify({...}),
     sim_success_rate: 0.92, real_success_rate: null, sim_real_gap_percentage: null,
     reproduce_command: "python train.py ...", findings: "...", created_at: Date.now() }})
   ```

## 场景 B:回填真机指标 + gap 分析

示例: `sim_173... 真机测了,real=0.71`

1. **定位 record_id**: filter `sim_id="sim_173..."`
2. **算 gap**: `(0.92 - 0.71) / 0.92 * 100 = 22.8`
3. **update** `real_success_rate`, `sim_real_gap_percentage`, `findings`(追加)
4. **gap 分析话术**(Agent 回复,不调 tool):
   - gap < 10% → "可考虑上真机生产"
   - 10% ≤ gap < 25% → "扩大 friction/mass range 或加 sensor noise,再跑一轮"
   - gap ≥ 25% → "排查 (1) image augmentation (2) camera intrinsic (3) system identification"
   - `real > sim` → 反常,优先怀疑 real 评测集太容易

## 场景 C:可复现性检查

示例: `reproducibility check sim_173...`

1. 读原 run 的 `reproduce_command`
2. 指导学生手动跑 3 次同 seed(原样复制命令)
3. 学生回传 3 个 success_rate → Agent 算 mean / std / `std/mean`
4. **追加到 findings**: `[repro-check YYYY-MM-DD] 3 次: [...], std/mean=X%, ✅/❌ 可复现`
5. 不可复现排查清单:
   - PyTorch `use_deterministic_algorithms(True)`
   - CUDA `CUBLAS_WORKSPACE_CONFIG=:4096:8`
   - IsaacGym 多 env 并行默认不确定
   - 数据 shuffle 未 seed

## 场景 D:查询某 ckpt 的所有仿真记录

```
feishu_bitable_app_table_record({ action:"list",
  filter: "CurrentValue.[ckpt_id]=\"ckpt_v3\"",
  field_names:["sim_id","simulator","sim_success_rate","real_success_rate",
               "sim_real_gap_percentage","created_at"] })
```
按 `created_at` 倒序输出 markdown 表。

## 需要新建的多维表

### SimRuns

| 字段 | 类型 | 说明 |
|---|---|---|
| `sim_id` | Text (pk) | `sim_<ts>_<rand>` |
| `ckpt_id` | Text | FK → Checkpoints.ckpt_id |
| `simulator` | SingleSelect | 枚举见下 |
| `domain_rand_json` | Text (long) | DR 参数 JSON |
| `physics_params_json` | Text (long) | 物理常量 JSON |
| `sim_success_rate` | Number (0.00%) | 0~1 小数 |
| `real_success_rate` | Number (0.00%) | 可空 |
| `sim_real_gap_percentage` | Number (0.0) | 百分数值本身(22.8) |
| `reproduce_command` | Text | 完整 shell 命令 |
| `findings` | Text | 结论 / 观察 |
| `created_at` | DateTime | 毫秒 |

## 枚举值强约束

| 字段 | 有效值 |
|---|---|
| `simulator` | `MuJoCo`、`IsaacGym`、`PyBullet`、`Gazebo`、`RoboSuite`、`其他` |

`sim_success_rate` / `real_success_rate` 存 `0~1` 小数;
`sim_real_gap_percentage` 存**百分数值本身**(22.8,非 0.228)。

## 失败降级

- `tables.sim_runs` 不存在 → 引导 admin 跑 `setup-bitable`
- 学生没给 `reproduce_command` → **强制追问**,本表核心价值之一,不能留空
- `domain_rand_json` / `physics_params_json` 超长 → 截断到 20 KB 并加 `...[truncated]`
- `code 1254xxx` (枚举错) → 自查后用正确枚举值重试一次
- `code 99991672` (缺 scope) → "权限不足,请 admin 联系"
