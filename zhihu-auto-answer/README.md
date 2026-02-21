# 知乎自动回答机器人

基于 MiniMax AI + NotebookLM 知识库的知乎自动回答脚本，通过 GitHub Actions 定时执行。

## 架构

```
知乎问题 → NotebookLM知识检索 + 本地素材库 → 角度发现 → 叙事生成 → 质量审查 → 发布
```

- **知识检索层**：优先从 NotebookLM 笔记本动态检索相关素材，本地硬编码素材库作为兜底
- **人设系统**：认知升级者框架 + 一致性约束（技术立场、价值观、人格特征不可动摇）
- **生成流程**：素材匹配 → 角度发现 → 叙事生成（场景→认知冲突→深度思考→开放收尾）

## 配置

需要在 GitHub Secrets 中设置：

| Secret | 说明 | 必需 |
|--------|------|------|
| `MINIMAX_API_KEY` | MiniMax M2.5 API 密钥 | 是 |
| `ZHIHU_COOKIE` | 知乎登录 Cookie | 是 |
| `GMAIL_USER` | Gmail 邮箱地址 | 是 |
| `GMAIL_APP_PASSWORD` | Gmail 应用专用密码 | 是 |
| `NOTEBOOKLM_NOTEBOOK_ID` | NotebookLM 笔记本 ID | 否（不配置则只用本地素材） |
| `NOTEBOOKLM_AUTH_JSON` | NotebookLM 认证 JSON | 否（配合 NOTEBOOK_ID 使用） |

### NotebookLM 配置说明

1. 在 [NotebookLM](https://notebooklm.google.com/) 创建一个笔记本，添加行业素材（文章、笔记等）
2. 在本地安装 `notebooklm-py` 并登录：`pip install notebooklm-py && notebooklm login`
3. 获取笔记本 ID：`notebooklm list`
4. 将笔记本 ID 设为 `NOTEBOOKLM_NOTEBOOK_ID` secret
5. 将 `~/.notebooklm/storage_state.json` 的内容设为 `NOTEBOOKLM_AUTH_JSON` secret

## 使用

### 手动触发

在 GitHub Actions 页面点击 "Run workflow"，选择：
- `dry_run`: true（仅生成预览）/ false（自动发布）
- `answers_count`: 回答问题数量（1-3）

### 定时执行

默认每周一三五 UTC 12:30（北京时间 20:30）自动执行演示模式。
