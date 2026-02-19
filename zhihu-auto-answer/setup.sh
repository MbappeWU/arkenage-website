#!/bin/bash
# ============================================================
# 知乎自动回答 - 一键部署脚本
# 功能：创建私有仓库 + 推送代码 + 安全配置 Secrets
# ============================================================

set -e

echo "============================================"
echo "  知乎自动回答 - 一键部署"
echo "============================================"
echo ""

# ---------- 检查依赖 ----------
if ! command -v gh &> /dev/null; then
    echo "❌ 需要安装 GitHub CLI (gh)"
    echo "   macOS:  brew install gh"
    echo "   Linux:  https://github.com/cli/cli/blob/trunk/docs/install_linux.md"
    exit 1
fi

if ! gh auth status &> /dev/null; then
    echo "❌ 请先登录 GitHub CLI: gh auth login"
    exit 1
fi

GITHUB_USER=$(gh api user -q '.login')
echo "✅ 已登录 GitHub: $GITHUB_USER"
echo ""

# ---------- 创建私有仓库 ----------
REPO_NAME="zhihu-auto-answer"

if gh repo view "$GITHUB_USER/$REPO_NAME" &> /dev/null; then
    echo "⚠️  仓库 $GITHUB_USER/$REPO_NAME 已存在，跳过创建"
else
    echo "📦 创建私有仓库: $GITHUB_USER/$REPO_NAME ..."
    gh repo create "$REPO_NAME" --private --description "知乎自动回答机器人 - 基于 MiniMax M2.5"
    echo "✅ 私有仓库创建成功"
fi
echo ""

# ---------- 推送代码 ----------
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
TEMP_DIR=$(mktemp -d)

echo "📁 准备代码文件..."
cp -r "$SCRIPT_DIR/.github" "$TEMP_DIR/"
cp -r "$SCRIPT_DIR/src" "$TEMP_DIR/"
cp "$SCRIPT_DIR/requirements.txt" "$TEMP_DIR/"
cp "$SCRIPT_DIR/README.md" "$TEMP_DIR/"

cd "$TEMP_DIR"
git init -b main
git add -A
git commit -m "feat: 初始化知乎自动回答脚本"

git remote add origin "https://github.com/$GITHUB_USER/$REPO_NAME.git"
git push -u origin main --force

echo "✅ 代码推送成功"
echo ""

# ---------- 安全配置 Secrets ----------
echo "============================================"
echo "  🔐 配置 GitHub Secrets（安全输入模式）"
echo "  输入内容不会显示在屏幕上"
echo "============================================"
echo ""

configure_secret() {
    local secret_name=$1
    local description=$2

    echo "▶ $description"
    echo -n "  请输入 $secret_name: "
    read -rs secret_value
    echo ""

    if [ -z "$secret_value" ]; then
        echo "  ⏭ 跳过（为空）"
    else
        echo "$secret_value" | gh secret set "$secret_name" --repo "$GITHUB_USER/$REPO_NAME"
        echo "  ✅ $secret_name 已设置"
    fi
    echo ""
}

configure_secret "MINIMAX_API_KEY"   "MiniMax API 密钥（platform.minimax.io 获取）"
configure_secret "ZHIHU_COOKIE"      "知乎登录 Cookie（F12 → Network → 请求头 → Cookie）"
configure_secret "GMAIL_USER"        "Gmail 邮箱地址（用于接收通知）"
configure_secret "GMAIL_APP_PASSWORD" "Gmail 应用专用密码"

# ---------- 清理临时目录 ----------
rm -rf "$TEMP_DIR"

# ---------- 完成 ----------
echo ""
echo "============================================"
echo "  ✅ 部署完成！"
echo "============================================"
echo ""
echo "  仓库地址:  https://github.com/$GITHUB_USER/$REPO_NAME"
echo "  Actions:   https://github.com/$GITHUB_USER/$REPO_NAME/actions"
echo "  Secrets:   https://github.com/$GITHUB_USER/$REPO_NAME/settings/secrets/actions"
echo ""
echo "  下一步："
echo "  1. 打开 Actions 页面，点击 '知乎自动回答' workflow"
echo "  2. 点击 'Run workflow'，dry_run 选 true，先测试一次"
echo "  3. 确认无误后，dry_run 改为 false 即可自动发布"
echo ""
