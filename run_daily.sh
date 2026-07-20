#!/bin/sh
# UMass 中文菜单：每日抓取 + 翻译 + 生成页面（macOS launchd/cron 调用，对应 Windows 的 run_daily.bat）
cd "$(dirname "$0")" || exit 1
mkdir -p logs
# launchd 环境的 PATH 很精简，补上 claude CLI 和 git 的常见位置
PATH="/opt/homebrew/bin:/usr/local/bin:$HOME/.local/bin:$PATH"
export PATH
/Users/chengyudu/miniconda3/bin/python3 -m umass_menu.main >> logs/daily.log 2>&1
