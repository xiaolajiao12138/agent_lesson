# Antigravity IDE 插件导出与跨设备迁移指南

> **环境确认**：针对 **Antigravity IDE**（基于 Code-OSS 内核），本次已从本机的 Antigravity 插件存储库中精准提取出当前已安装并激活的全部 **25 个核心插件**。

---

## 插件存储位置说明

* **本机实际存储路径**：`C:\Users\Administrator\.antigravity\extensions`
* **新电脑目标路径**：`C:\Users\<新电脑用户名>\.antigravity\extensions`

---

## 25 个已导出插件全景清单

| 类别 | 插件标识 (ID) | 版本 | 功能与用途 |
| :--- | :--- | :--- | :--- |
| **AI 编程助手** | `alibaba-cloud.tongyi-lingma` | 2.6.2 | 通义灵码 AI 代码生成与补全 |
| | `marscode.marscode-extension` | 1.4.14 | 字节跳动 MarsCode 豆包 AI 编程助手 |
| **Python 开发** | `ms-python.python` | 2026.4.0 | Python 语言核心支持 |
| | `ms-python.debugpy` | 2026.6.0 | Python 官方调试器 |
| | `ms-python.vscode-python-envs` | 1.20.1 | Python 虚拟环境/Conda 环境切换管理 |
| | `meta.pyrefly` | 1.1.1 | Meta 官方 Pyrefly 快速类型检查与分析工具 |
| **Vue & 前端** | `vue.volar` | 3.3.5 | Vue 3 官方语言工具 (Vue Language Features) |
| | `vue.vscode-typescript-vue-plugin` | 1.8.27 | TypeScript Vue 插件支持 |
| | `octref.vetur` | 0.37.3 | Vue 2 开发与语法支持 |
| | `esbenp.prettier-vscode` | 12.4.0 | Prettier 代码格式化工具 |
| | `rvest.vs-code-prettier-eslint` | 6.0.0 | Prettier + ESLint 联合格式化 |
| | `formulahendry.auto-close-tag` | 0.5.15 | HTML/XML 标签自动闭合 |
| **C / C++ 链** | `ms-vscode.cpptools` | 1.28.3 | C/C++ 智能感知、调试支持 |
| | `ms-vscode.cpptools-extension-pack`| 1.3.1 | C/C++ 官方工具扩展包 |
| | `ms-vscode.cpptools-themes` | 2.0.0 | C/C++ 语法着色主题 |
| | `ms-vscode.cmake-tools` | 1.23.52 | CMake 构建与调试工具 |
| | `llvm-vs-code-extensions.vscode-clangd` | 0.6.0 | 基于 LLVM Clangd 的极速 C/C++ 语言引擎 |
| **其他语言** | `golang.go` | 0.54.0 | Google Go 语言开发扩展 |
| | `shopify.ruby-lsp` | 0.10.4 | Shopify Ruby 语言服务扩展 |
| **版本管理** | `eamodio.gitlens` | 18.2.0 | GitLens Git 提交历史与 blame 超强可视化 |
| | `donjayamanne.githistory` | 0.6.20 | Git History 分支图表查看器 |
| **编辑器体验**| `ms-ceintl.vscode-language-pack-zh-hans` | 1.106.0 | 简体中文语言包 |
| | `coenraads.bracket-pair-colorizer-2` | 0.2.4 | 彩色配对括号高亮 |
| | `fabiospampinato.vscode-highlight` | 2.1.0 | 文本与代码关键字高亮 |
| | `naumovs.color-highlight` | 2.8.0 | CSS/十六进制颜色代码实时着色预览 |

---

## 跨电脑迁移方案（三种可选）

### 方案一：【最推荐】离线物理复制法（100%成功，零网络依赖）

很多时候新电脑下载插件可能会因为网络受限、版本更新或者源不稳定而失败。物理拷贝直接克隆整个插件库，是最稳妥的方式：

1. **在当前电脑提取**：
   * 双击运行本目录下的 `backup_to_here.bat`，脚本会自动把当前电脑的插件复制到本文件夹下的 `extensions_offline` 目录。
   * 或者手动复制当前电脑的 `C:\Users\Administrator\.antigravity\extensions` 文件夹到 U 盘。
2. **拷贝到新电脑**：
   * 将整个 `antigravity-extensions-backup` 文件夹拷到新电脑。
3. **在新电脑上还原**：
   * 在新电脑上双击运行 `restore_to_antigravity.bat`。
   * 脚本会自动将插件解压/复制到新电脑的 `%USERPROFILE%\.antigravity\extensions`。
4. **启动编辑器**：
   * 打开新电脑上的 Antigravity IDE，所有 25 个插件立即可用，无需重新下载！

---

### 方案二：在线批量命令行安装（新电脑联网顺畅时）

如果你的新电脑网络畅通，可以通过命令行直接从插件市场在线安装：

1. 将本文件夹拷贝到新电脑。
2. 双击运行 `install_antigravity_extensions.bat`。
3. 脚本会自动调用命令行工具，逐个静默下载并安装这 25 个插件。

---

### 方案三：手动搜索安装

在新电脑的 Antigravity IDE 中：
1. 按下快捷键 `Ctrl + Shift + X` 打开插件面板。
2. 打开本文件夹下的 `antigravity_extensions.txt`。
3. 复制插件 ID（如 `alibaba-cloud.tongyi-lingma`）粘贴到搜索框，点击 **Install（安装）** 即可。

