# UMass Dining 中文菜单助手 — 项目策划

> 目标：每天自动抓取 UMass Amherst 当天开放食堂的菜单，翻译成中文，
> 支持给喜欢的菜上传照片，逐步积累成一份可视化的个人中文菜单库。

## 1. 数据源调研结论（2026-07-06 已实测验证）

UMass Dining 手机 App 背后有公开的 JSON 接口，**无需网页爬虫**：

| 接口 | 用途 | 验证结果 |
|------|------|----------|
| `https://umassdining.com/uapp/get_infov2` | 所有餐厅列表 + 当天营业状态 + 内嵌当日菜单（按餐段组织的菜名） | ✅ 可用。今日开放：Worcester Commons、Hampshire DC、Harvest Market（暑期） |
| `https://umassdining.com/uapp/get_menu?tid=<id>` | 单个食堂的详细菜单（含营养/过敏原等字段） | ⚠️ 暑期部分食堂返回空，开学后需复测；MVP 用 get_infov2 即可 |

主要食堂 ID：Worcester=1，Franklin=2，Hampshire=3，Berkshire=4。

- `opening_hours` 为 "Closed" 即当天关闭 → 天然满足"只抓开放食堂"。
- 官网菜单页面是 JS 动态渲染的，直接解析 HTML 不可行，进一步说明走 API 是正确路线。
- 注意：这是非官方接口，学校可能调整。抓取脚本要做好失败报警。

## 2. 系统架构

```
每日定时任务 (Windows 任务计划程序, 每天 ~7:00)
    │
    ▼
fetcher.py ──→ get_infov2 ──→ 过滤当天开放的食堂
    │
    ▼
translator.py ──→ 查本地翻译缓存 (dishes 表)
    │                 ├─ 已有译名 → 直接复用（食堂菜单高度轮换，重复率极高）
    │                 └─ 新菜名 → 调 Claude Haiku API 批量翻译 → 写入缓存
    ▼
SQLite (dining.db)
    │
    ▼
Web 界面 (FastAPI + Jinja2, 本机 + 手机局域网访问)
    ├─ 今日菜单（中英对照，按食堂/餐段/档口分组，新菜高亮 = 特色菜提醒）
    ├─ 照片上传（手机浏览器打开局域网地址，点菜名直接传图）
    └─ 我的菜单画廊（有照片/收藏的菜，可搜索中英文名）
```

## 3. 数据模型（SQLite）

```sql
dishes        (id, name_en UNIQUE, name_zh, first_seen DATE, is_favorite, notes)
menu_records  (id, date, hall, meal, station, dish_id → dishes)
photos        (id, dish_id → dishes, file_path, taken_at)
```

- 菜名去重是核心：同一道菜反复出现只翻译一次，翻译成本随时间趋近于零。
- `first_seen` 即"新菜检测"：当天菜单里 `first_seen = 今天` 的就是没见过的特色菜。

## 4. 翻译策略

- **推荐 Claude Haiku API**：菜名翻译需要意译能力（"Mango Lassi French Toast" →
  "芒果拉西法式吐司"），机器翻译常出错（"Ranch Wrap" 会被译成"牧场包裹"）。
- 每天新菜名预计只有几个到几十个，批量一次请求，月成本几乎可以忽略（< $0.1）。
- 缓存表允许手动修正：发现译得不好可以直接改 `name_zh`，之后永久生效。

## 5. 分阶段路线图

| 阶段 | 内容 | 产出 |
|------|------|------|
| **P1 MVP** | 抓取 + 翻译缓存 + SQLite + 生成当日中英对照菜单页 + 定时任务 | 每天早上自动有一份中文菜单可看 |
| **P2 浏览** | FastAPI Web 界面：按日期/食堂/餐段浏览、中英文搜索、新菜高亮 | 特色菜第一时间知道 |
| **P3 照片** | 手机局域网上传照片、绑定到菜、画廊页 | 可视化菜单成形 |
| **P4 增强(可选)** | 每日推送（邮件/Windows 通知/微信 Server酱）、收藏提醒"你喜欢的菜今天 Hampshire 有" | 完全自动化 |

## 6. 技术栈

- Python 3.11+，依赖：`requests`、`fastapi`、`uvicorn`、`jinja2`、`anthropic`
- 存储：SQLite 单文件 + `photos/` 目录存原图（个人项目无需数据库服务）
- 定时：Windows 任务计划程序（schtasks），失败时写日志并弹通知

## 7. 风险与对策

| 风险 | 对策 |
|------|------|
| 非官方 API 变动/失效 | 抓取失败即通知；备选方案为 Playwright 渲染官网页面解析 |
| 暑期数据少 | 现在正好用暑期开发调试，9 月开学后全量数据自然接入 |
| 手机上传需同一 WiFi | 校园网下电脑手机通常同网段；不行则退化为拍照存 OneDrive 指定文件夹、程序定期扫描关联 |
