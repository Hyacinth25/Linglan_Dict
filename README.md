# 铃兰词典（Linglan Dict）

一个基于 `Tkinter + SQLite` 的本地英语学习桌面应用，主打“查词 + 个人词库 + LLM故事记忆 + 进度追踪”。

项目定位是单机学习工具：界面轻量、可离线查词、支持自定义提示词与账号数据导入导出。

## 主要功能

- 首页查词：输入英文单词查询音标、词性、英文释义、中文释义
- 句子翻译：输入多个单词（句子）时走句子翻译流程
- 个人词库：
  - `正在背（learning）`
  - `背诵完成（finished）`
- 单词管理：
  - 手动添加单词到“正在背”
  - 从 `txt` 批量导入（一行一个单词）
  - 导出“正在背”到 `txt`
- 学习模块：
  - 从“正在背”随机抽词（可设置数量）
  - 调用 LLM 生成英文故事（支持难度设置）
  - 用户填写中文释义后提交
  - LLM判定答案是否可取
  - 连续答对 2 次自动移入“背诵完成”
- 学习记录：
  - 每次提交后保存为 Markdown 历史文件
  - 可在应用内查看历史学习记录
- 设置模块：
  - 主题色（日间/夜间模式）
  - 中文/英文字体、字号
  - API Key 与 Base URL
  - 故事提示词编辑
  - 学习高亮开关与颜色
- 账号数据导入导出：
  - 导出为 `.slaccount`
  - 导入后恢复设置、个人词库、学习历史
- 加载提示语：
  - 从 `tips.txt` 读取
  - 加载时随机显示
  - 左下角逐字显示动画

## 技术栈

- Python 3
- Tkinter（GUI）
- SQLite（词库与学习进度）
- `urllib` 调用 OpenAI 兼容接口
- `argostranslate`（句子翻译）
- `python-dotenv`（可选，读取 `.env`）

当前应用版本见 `app_version.py`。

## 目录结构（核心）

```text
Linglan_Dict/
├─ main.py                    # 应用入口与主控制器
├─ 启动铃兰词典.bat            # Windows 一键启动
├─ pages/                     # 页面构建与页面行为
│  ├─ home.py
│  ├─ add.py / add_actions.py
│  ├─ study.py / study_actions.py
│  └─ settings.py
├─ services/                  # 业务服务层
│  ├─ database.py             # 词库与个人词库
│  ├─ llm_service.py          # LLM 调用
│  ├─ translation_service.py  # 句子翻译
│  └─ account_service.py      # 账号导入导出
├─ vocabulary.db              # 主词库（运行中使用）
├─ stardict.db                # 初始词库源
├─ study_stories/             # 学习历史（Markdown）
├─ ui_config.json             # UI配置与学习参数
├─ tips.txt                   # 加载提示语
├─ assets/                    # UI素材
├─ offline_assets/            # 离线翻译资源
└─ offline_runtime/           # 离线翻译可写运行目录
```

## 环境要求

- Windows（当前项目主要按 Windows 目录与脚本组织）
- Python 3.10+（建议 3.11 或 3.12）
- 可用的 Tkinter（多数官方 Python 安装自带）

## 安装与启动

### 1) 创建虚拟环境（可选但推荐）

```powershell
python -m venv .venv
.\.venv\Scripts\activate
```

### 2) 安装依赖

```powershell
pip install -r requirements.txt
```

说明：
- `python-dotenv`：可选，不装也能运行（应用会回退到手动读取 `.env`）
- `argostranslate`：句子翻译需要
- `openpyxl`：竞赛记录导出 Excel 需要
- `pyinstaller`：打包发布需要

### 3) 配置 `.env`

在项目根目录创建或编辑 `.env`：

```env
API_KEY=你的API密钥
BASE_URL=https://api.openai.com/v1
```

如果使用第三方 OpenAI 兼容服务，也可以替换 `BASE_URL`。

### 4) 启动应用

方式一（推荐，Windows）：
- 双击 `启动铃兰词典.bat`

方式二（命令行）：

```powershell
python main.py
```

## 使用方法（快速上手）

### 首页

- 在查词框输入英文单词，查看详细释义
- 输入句子时走句子翻译流程

### 添加页

- 单词手动加入“正在背”
- 支持 `txt` 批量导入（每行一个）
- 右键或双击列表项可查询/移出
- 可导出“正在背”到 `正在背单词表.txt`

### 学习页

- 设置抽词数量（5~20）与难度（easy/normal/hard）
- 点击“生成故事”后完成答题
- 点击“提交”触发 LLM 评审
- 连对两次的词会自动移到“背诵完成”
- 可查看历史学习记录

### 设置页

- 调主题色与日/夜模式
- 调中文/英文字体与字号
- 配置 API Key / Base URL
- 编辑故事提示词
- 调整学习词高亮选项
- 打开设置页后自动检查 GitHub Releases 是否有新版本
- 导入/导出账号文件（`.slaccount`）

## 数据文件说明

- `vocabulary.db`：应用实际使用词库（含个人词库表）
- `stardict.db`：初始化词库源，首次启动可能复制数据
- `study_stories/*.md`：每次学习提交后的历史记录
- `ui_config.json`：主题、字体、学习参数、提示词等配置
- `tips.txt`：加载时随机展示的提示语（支持自定义增删）

## 常见问题（FAQ）

### 1) 启动后提示 API 或网络错误

- 检查 `.env` 的 `API_KEY`、`BASE_URL`
- 检查网络连通性
- 若使用代理/网关，请确认接口兼容 `chat/completions`

### 2) 句子翻译不可用

- 先确认安装了 `argostranslate`
- 确认离线资源目录存在并完整：
  - `offline_assets/argos_packages`
  - `offline_assets/stanza_resources`

### 3) 导入单词后有些没加进去

- 词库不存在的单词会被跳过
- 已在“背诵完成”的单词不会重复加入“正在背”
- 已在“正在背”的单词会计为已存在

### 4) 如何自定义加载提示语

- 编辑根目录 `tips.txt`
- 一行写一条提示语
- 应用在加载时会随机抽取并显示

## 备注

- GitHub 发布流程见 `docs/release.md`。
- `vocabulary.db` 属于大型发布资产，不提交到源码仓库；打包发布时由 `tools/package_release.ps1` 放入 Release 压缩包。
