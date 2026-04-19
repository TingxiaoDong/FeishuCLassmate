---
name: escalate-permission-errors-with-admin-action-plan
description: When encountering Feishu/Lark API permission errors, provide a clear step-by-step action plan for the admin, not just a URL.
category: communication
---

## Escalate Permission Errors with Admin Action Plan

When Feishu API returns permission/scope errors (code 99991672, etc.):

1. **Provide context**: Name the specific permission that's missing
2. **Give admin action steps** (numbered):
   - Click the authorization link
   - Log in with admin account
   - Click "Authorize" / "允许"
   - Return here and mention "已授权" to continue
3. **Explain consequence**: What feature will be unlocked after authorization
4. **Keep message brief**: Admin needs clear instructions, not lengthy explanation

**Example response:**
> ⚠️ 权限不足：需要管理员授权「联系人基础信息（只读）」
> 
> **管理员操作步骤：**
> 1. 打开：https://open.feishu.cn/app/xxx/auth?...  
> 2. 点击「授权」
> 3. 完成后告诉我「已授权」
> 
> 授权后我可正常查询学生信息。

**Anti-pattern:** Just pasting the URL without explanation of what to do with it or why it's needed.
