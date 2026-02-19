# 知乎自动回答机器人

基于 Claude API 的知乎自动回答脚本，通过 GitHub Actions 定时执行。

## 功能

- 自动搜索智能座舱相关高潜力问题
- 使用 Claude AI 生成高质量回答（主机厂内部视角人设）
- 质量审查 + 自动改进
- 支持演示模式（dry_run）和自动发布模式
- Gmail 邮件通知
- 定时执行：每周一三五北京时间 20:30

## 配置

需要在 GitHub Secrets 中设置：

| Secret | 说明 |
|--------|------|
| `ANTHROPIC_API_KEY` | Claude API 密钥 |
| `ZHIHU_COOKIE` | 知乎登录 Cookie |
| `GMAIL_USER` | Gmail 邮箱地址 |
| `GMAIL_APP_PASSWORD` | Gmail 应用专用密码 |

## 使用

### 手动触发

在 GitHub Actions 页面点击 "Run workflow"，选择：
- `dry_run`: true（仅生成预览）/ false（自动发布）
- `answers_count`: 回答问题数量（1-3）

### 定时执行

默认每周一三五 UTC 12:30（北京时间 20:30）自动执行演示模式。
