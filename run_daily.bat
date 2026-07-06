@echo off
rem UMass 中文菜单：每日抓取 + 翻译 + 生成页面（供 Windows 任务计划调用）
cd /d D:\UMASS_Dinning
if not exist logs mkdir logs
py -m umass_menu.main >> logs\daily.log 2>&1
