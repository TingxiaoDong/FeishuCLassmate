# 无当次 Doc 时的通用五阶段(精简)

用于 **lab-tour-run**:无法取得定制稿时的默认顺序。

1. **开场**: `temi_navigate_to`「入口」→ `temi_detect_person` → LLM 欢迎词 → `temi_speak`
2. **实验室概况**:读 `publicProjects` Doc 摘要 + `labInfo` → `temi_speak`
3. **特色区**:遍历 `labInfo.specialAreas` → 每处 `navigate` + `speak`
4. **工位区**:「工位区」→ `detect_person` → bitable 公开项目 → `speak`
5. **收尾问答**:回「入口」→ `speak` 邀请提问 → RAG 仅限公开资料

安全:Temi 「停」→ `temi_stop`;不外泄保密项目;不明文输出访客 open_id。
