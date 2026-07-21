# 铃兰词典发布流程

这个项目采用“GitHub 托管源码 + GitHub Releases 提供下载包”的方式发布。

## 首次 GitHub 设置

1. 在 GitHub 创建一个空仓库，例如 `Linglan_Dict`。
2. 在 `app_version.py` 里把 `GITHUB_REPO` 改成 `用户名/Linglan_Dict`。
3. 只提交源码和必要资源，不提交本地密钥、用户记录、构建目录和大型数据库。
4. 添加远程仓库并推送：

```powershell
git remote add origin https://github.com/<用户名>/Linglan_Dict.git
git add .
git commit -m "Initial Linglan Dict release setup"
git push -u origin main
```

## 版本号规则

使用语义化版本：

- 修复问题：`0.1.1`
- 增加功能：`0.2.0`
- 数据结构或包结构有重大变化：`1.0.0`

每次发布前，先更新 `app_version.py` 里的 `APP_VERSION`。

## 打包发布文件

在项目根目录运行：

```powershell
.\tools\package_release.ps1
```

脚本会先执行 PyInstaller 打包，然后生成：

```text
release/Linglan_Dict-v<版本号>-windows-x64.zip
```

发布包会包含 `dist/铃兰词典` 里的应用目录，并把本地存在的运行资产放进应用目录：

- `vocabulary.db`
- `offline_assets/`

`README.md` 会放在压缩包根目录，`vocabulary.db` 和 `offline_assets/` 会放在 `铃兰词典/` 目录里，和 exe 保持同一层。`vocabulary.db` 体积太大，不适合提交到源码仓库，所以只放进 GitHub Release 下载包。

如果你已经手动打包好了，只想重新生成 zip：

```powershell
.\tools\package_release.ps1 -SkipBuild
```

## 上传到 GitHub Releases

安装并登录 GitHub CLI 后：

```powershell
gh auth login
git tag v2.0.0
git push origin v2.0.0
gh release create v2.0.0 .\release\Linglan_Dict-v2.0.0-windows-x64.zip --title "铃兰词典 v2.0.0" --notes "首个公开发布版本。"
```

后续每次发版：

```powershell
git add .
git commit -m "Release v0.1.1"
git push origin main
git tag v0.1.1
git push origin v0.1.1
.\tools\package_release.ps1 -Version 0.1.1
gh release create v0.1.1 .\release\Linglan_Dict-v0.1.1-windows-x64.zip --title "铃兰词典 v0.1.1" --notes "这里写本次更新内容。"
```

## 后续应用内更新检查

设置页的“检查更新”功能可以读取：

```text
https://api.github.com/repos/<用户名>/Linglan_Dict/releases/latest
```

拿到最新 Release 的 `tag_name` 后，与 `APP_VERSION` 比较。如果 GitHub 上版本更高，就显示更新说明，并提供打开下载页或下载安装包的按钮。
