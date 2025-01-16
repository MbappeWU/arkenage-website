# Arken Age 官方网站

这是 Arken Age 游戏的官方网站仓库。网站采用现代化的设计，展示游戏特色并提供游戏体验入口。

## 特性

- 响应式设计，支持各种设备
- 现代化UI界面
- 流畅的动画效果
- 游戏直接访问入口

## 本地开发

1. 克隆仓库：
```bash
git clone https://github.com/yourusername/arkenage-website.git
cd arkenage-website
```

2. 使用本地服务器运行（例如使用 Python）：
```bash
python -m http.server 8000
```

3. 访问 `http://localhost:8000` 查看网站

## 部署

### GitHub Pages 部署

1. 在GitHub仓库设置中启用GitHub Pages
2. 选择 main 分支作为源
3. 网站将在几分钟内部署完成

### 自定义域名设置

1. 在域名提供商处添加以下DNS记录：
   - A记录：指向 GitHub Pages IP
   - CNAME记录：指向 `yourusername.github.io`

2. 在仓库设置中添加自定义域名 `arkenage.com`

## 技术栈

- HTML5
- CSS3
- JavaScript (ES6+)
- 响应式设计

## 贡献

欢迎提交 Pull Requests 来改进网站。在提交之前，请确保：

1. 代码符合现有的代码风格
2. 更新已经经过测试
3. 提交信息清晰明了

## 许可证

MIT License 