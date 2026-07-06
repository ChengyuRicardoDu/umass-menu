"""每日入口：抓取 → 入库 → 翻译新菜名 → 生成中文菜单页。

用法：py -m umass_menu.main [--render-only]
    --render-only  跳过抓取和翻译，只用库里已有数据重新生成页面（改样式后用）
"""
import datetime
import subprocess
import sys
import traceback

from . import config, db, fetcher, render, translator


def log(msg):
    ts = datetime.datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)


def publish(date_iso):
    """commit 并 push 到 GitHub，触发 Pages 更新。失败不影响本地页面。"""
    if not config.AUTO_PUBLISH:
        return
    def git(*args, check=True):
        return subprocess.run(["git", *args], cwd=config.BASE_DIR,
                              capture_output=True, text=True,
                              encoding="utf-8", check=check)
    try:
        status = git("status", "--porcelain").stdout.strip()
        if not status:
            log("没有变化，无需发布。")
            return
        git("add", "-A")
        git("commit", "-m", f"menu {date_iso}")
        git("push")
        log("已发布到 GitHub Pages。")
    except subprocess.CalledProcessError as e:
        log(f"发布失败（本地页面不受影响，可稍后手动 git push）：{e.stderr[:200]}")


def render_only():
    """只重新生成今天的页面（营业时间仍需请求一次）。"""
    date_iso = datetime.date.today().isoformat()
    conn = db.connect()
    in_menu = {r["hall"] for r in conn.execute(
        "SELECT DISTINCT hall FROM menu_records WHERE date = ?", (date_iso,))}
    if not in_menu:
        log(f"库里没有 {date_iso} 的菜单记录，请先完整运行一次。")
        return 1
    try:
        halls = [h for h in fetcher.open_locations() if h["name"] in in_menu]
    except Exception:
        halls = [{"name": h, "hours": ""} for h in sorted(in_menu)]
    out = render.render(conn, date_iso, halls)
    log(f"菜单页已重新生成：{out}")
    conn.close()
    publish(date_iso)
    return 0


def run():
    today = datetime.date.today()
    date_iso = today.isoformat()
    date_us = today.strftime("%m/%d/%Y")

    log(f"抓取 {date_iso} 开放食堂菜单 ...")
    halls, menus = fetcher.fetch_all(date_us)
    if not halls:
        log("没有拿到任何菜单数据（食堂全部关闭，或接口变动）。")
        return 1
    log(f"开放且有菜单的餐厅：{', '.join(h['name'] for h in halls)}")

    conn = db.connect()
    n_records = 0
    with conn:
        for hall, meals in menus.items():
            for meal, stations in meals.items():
                for station, dishes in stations.items():
                    for dish in dishes:
                        dish_id = db.upsert_dish(conn, dish, date_iso)
                        db.add_menu_record(conn, date_iso, hall, meal, station, dish_id)
                        n_records += 1
    log(f"入库 {n_records} 条菜单记录。")

    todo = db.untranslated_names(conn)
    if todo:
        log(f"待翻译菜名 {len(todo)} 个，开始翻译 ...")
        mapping = translator.translate(todo, log=log)
        with conn:
            db.save_translations(conn, mapping)
        log(f"本次翻译完成 {len(mapping)}/{len(todo)} 个。")
    else:
        log("所有菜名均已有缓存译名。")

    out = render.render(conn, date_iso, halls)
    log(f"菜单页已生成：{out}")
    conn.close()
    publish(date_iso)
    return 0


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    try:
        if "--render-only" in sys.argv[1:]:
            sys.exit(render_only())
        sys.exit(run())
    except Exception:
        traceback.print_exc()
        sys.exit(1)
