# UMass Dining 中文菜单助手

每天自动抓取 UMass Amherst 当天开放食堂的菜单，翻译成中文并生成一份
中英对照、带营养/过敏原/清真纯素标签的菜单页。完整规划见 [PLAN.md](PLAN.md)。

## 手机访问（GitHub Pages）

**https://chengyuricardodu.github.io/umass-menu/**

- 每天生成页面后自动 `git push` 发布，手机随时随地可打开
- iPhone：Safari 打开 → 分享 → 添加到主屏幕；Android：Chrome → 菜单 → 添加到主屏幕
- 历史菜单：`.../umass-menu/menu_2026-07-06.html`（改日期即可）

## 使用

```powershell
py -m umass_menu.main                # 手动跑一次：抓取 → 翻译 → 生成 → 发布
py -m umass_menu.main --render-only  # 只重新生成页面（改样式后用）
```

生成结果在 `docs\`：`index.html`（当天，即 Pages 首页）和
`menu_YYYY-MM-DD.html`（存档）。不想自动发布时把 `config.AUTO_PUBLISH` 设为 False。

## 自动运行

Windows 任务计划每天 07:00 调用 `run_daily.bat`（电脑需处于开机状态），
日志写入 `logs\daily.log`。

## 翻译

- 默认走 `claude` CLI 无头模式（用 Claude 订阅，无额外费用）
- 设置了 `ANTHROPIC_API_KEY` 环境变量则直接调 Anthropic API（Haiku）
- 所有译名永久缓存在 `data\dining.db` 的 `dishes.name_zh`；
  觉得某个译名不好，直接改这一列即可，之后一直生效

## 数据源（非官方接口，若失效见 PLAN.md 风险预案）

- `https://umassdining.com/uapp/get_infov2` — 全部餐厅 + 当天营业状态
- `https://umassdining.com/foodpro-menu-ajax?tid=<id>&date=<MM/DD/YYYY>`
  — 单餐厅菜单：餐段 → 档口 → 菜品（含营养、过敏原、饮食标签）

## 项目结构

```
umass_menu/
  config.py      配置与中文映射
  fetcher.py     抓取与解析
  db.py          SQLite（菜品=翻译缓存、菜单记录、照片）
  translator.py  Claude 批量翻译（只翻新菜名）
  render.py      生成 HTML 菜单页
  main.py        每日入口（含发布到 GitHub Pages）
data/dining.db   数据库
docs/            生成的菜单页（GitHub Pages 发布目录）
photos/          （三期）菜品照片
```
