---
name: dindoor-gouwo
description: 轻量级本地 SQLite 知识库（狗窝）by dindoor，支持内容存入、全文检索、分类管理。自动清洗数据、提取关键词。当用户说"把这些内容存到狗窝"或"从狗窝查询"信息时使用。
metadata: {"clawdbot":{"emoji":"🐶","requires": ["python3", "sqlite3"]}}
---

# 🐶 狗窝 - 本地知识库

轻量级本地 SQLite 知识库，干净简洁，快速高效。用于存储和检索个人知识、笔记、联系方式、重要通知。

## 特性

- ✅ **自动数据清洗** - 去除多余空行空格，压缩体积，保持整洁
- ✅ **自动关键词提取** - 基于词频统计，自动过滤中文停用词
- ✅ **FTS 全文检索** - SQLite 内置全文搜索，快速准确
- ✅ **分类标签** - 支持给内容添加分类，方便筛选管理
- ✅ **内容更新** - 支持更新已有条目，不用删除重录
- ✅ **查看全文** - 搜索结果支持直接查看完整内容
- ✅ **零依赖** - 只需要 Python 标准库，不需要额外安装包

## 命令说明

| 命令 | 用法 | 说明 |
|------|------|------|
| `add` | `add "内容" [关键词] [分类]` | 添加内容到狗窝，关键词自动提取 |
| `search` | `search "关键词"` | FTS 全文搜索相关内容 |
| `get` | `get <id>` | 获取条目的完整内容 |
| `update` | `update <id> "新内容" [关键词]` | 更新已有内容 |
| `list` | `list [分类]` | 列出所有内容，可按分类筛选 |
| `delete` | `delete <id>` | 删除指定ID条目 |
| `stats` | `stats` | 显示数据库统计信息 |
| `help` | `help` | 显示帮助 |

## 使用示例

```bash
# 添加内容，自动提取关键词
python3 skills/gouwo/scripts/gouwo.py add "麟德智造3匹机组仅售3300元" "麟德智造,价格,机组" "产品"

# 搜索内容
python3 skills/gouwo/scripts/gouwo.py search "价格"

# 查看完整内容
python3 skills/gouwo/scripts/gouwo.py get 1

# 列出"产品"分类下的所有内容
python3 skills/gouwo/scripts/gouwo.py list 产品

# 查看统计
python3 skills/gouwo/scripts/gouwo.py stats
```

## 数据存储

- 数据库位置：`data/gouwo.db`（相对于工作目录）
- 数据表：`knowledge` + FTS 虚拟表 `knowledge_fts`
- 自动维护全文索引，增删改自动更新

## AI 代理使用说明

当用户说：
- **"把这些内容存到狗窝"** - 调用 `add` 命令存储，自动清洗和提取关键词
- **"从狗窝查询xxx"** - 调用 `search` 命令搜索，返回结果
- **"从狗窝列出所有"** - 调用 `list` 命令

关键词用户不指定则自动提取，分类用户不说则留空。

## 作者

Created by Claude @ OpenClaw
