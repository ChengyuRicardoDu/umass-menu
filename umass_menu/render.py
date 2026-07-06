"""把当天菜单渲染成自包含 HTML：按餐段分页签，打开时自动跳到当前餐段。"""
import datetime
import html

from . import config, db

WEEKDAYS = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]

CSS = """
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: "Microsoft YaHei", "PingFang SC", system-ui, sans-serif;
       background: #faf8f5; color: #222; line-height: 1.6; padding-bottom: 40px; }
.wrap { max-width: 860px; margin: 0 auto; padding: 16px; }
header { background: #881c1c; color: #fff; padding: 20px 16px; }
header h1 { font-size: 22px; font-weight: 600; }
header .sub { opacity: .85; font-size: 14px; margin-top: 4px; }
.hours { background: #fff; border: 1px solid #eee; border-radius: 10px;
         padding: 12px 16px; margin: 16px 0; font-size: 14px; }
.hours b { color: #881c1c; }
.newbox { background: #fff7e6; border: 1px solid #f0d9a8; border-radius: 10px;
          padding: 12px 16px; margin: 0 0 16px; font-size: 14px; }
.newbox b { color: #b45309; }
.tabbar { position: sticky; top: 0; z-index: 10; display: flex; gap: 8px;
          background: #faf8f5; padding: 10px 0; margin-bottom: 8px;
          overflow-x: auto; }
.tab { border: 1px solid #ddd; background: #fff; color: #555; cursor: pointer;
       border-radius: 20px; padding: 6px 16px; font-size: 15px;
       white-space: nowrap; font-family: inherit; }
.tab .n { font-size: 12px; opacity: .65; margin-left: 3px; }
.tab.active { background: #881c1c; border-color: #881c1c; color: #fff; }
h2.hall { font-size: 19px; color: #881c1c; margin: 24px 0 4px;
          border-bottom: 2px solid #881c1c; padding-bottom: 6px; }
h2.hall .en { font-size: 13px; color: #999; font-weight: normal; margin-left: 8px; }
h4.station { font-size: 14px; color: #666; margin: 14px 0 6px; }
ul.dishes { list-style: none; }
ul.dishes li { background: #fff; border: 1px solid #eee; border-radius: 8px;
               padding: 8px 12px; margin-bottom: 6px; }
.zh { font-weight: 600; font-size: 15px; }
.en { color: #888; font-size: 13px; margin-left: 6px; }
.meta { margin-top: 2px; font-size: 12px; color: #999; }
.tag { display: inline-block; font-size: 11px; border-radius: 20px;
       padding: 1px 8px; margin-right: 4px; }
.tag.new { background: #dc2626; color: #fff; font-weight: 600; }
.tag.diet { background: #e7f5ec; color: #1a7a42; }
.tag.allergen { background: #fdecec; color: #b91c1c; }
footer { text-align: center; color: #aaa; font-size: 12px; margin-top: 32px; }
"""

# 页签切换 + 按当前时间自动选中餐段（10:30 前早餐，15:30 前午餐，之后晚餐）
JS = """
function showMeal(id){
  document.querySelectorAll('.mealpane').forEach(function(p){
    p.style.display = (p.id === 'meal-' + id) ? '' : 'none';});
  document.querySelectorAll('.tab').forEach(function(t){
    t.classList.toggle('active', t.dataset.meal === id);});
}
document.querySelectorAll('.tab').forEach(function(t){
  t.addEventListener('click', function(){ showMeal(t.dataset.meal); });});
(function(){
  var meals = [].map.call(document.querySelectorAll('.mealpane'),
    function(p){ return p.id.slice(5); });
  if (!meals.length) return;
  var now = new Date(), h = now.getHours() + now.getMinutes() / 60;
  var want = h < 10.5 ? 'breakfast' : (h < 15.5 ? 'lunch' : 'dinner');
  showMeal(meals.indexOf(want) >= 0 ? want : meals[0]);
})();
"""


def _slug(meal):
    return meal.replace(" ", "_")


def _zh_tags(raw, table):
    tags = []
    for part in (raw or "").replace(";", ",").split(","):
        p = part.strip()
        if p:
            tags.append(table.get(p.lower(), p))
    return tags


def _hall_sort_key(hall):
    try:
        return (config.HALL_ORDER.index(hall), "")
    except ValueError:
        return (len(config.HALL_ORDER), hall)


def _meal_sort_key(meal):
    try:
        return config.MEAL_ORDER.index(meal)
    except ValueError:
        return 99


def _dish_li(row, today, first_run):
    e = html.escape
    zh = row["name_zh"] or row["name_en"]
    parts = [f'<li><span class="zh">{e(zh)}</span>']
    if row["name_zh"]:
        parts.append(f'<span class="en">{e(row["name_en"])}</span>')
    tags = []
    if not first_run and row["first_seen"] == today:
        tags.append('<span class="tag new">新菜</span>')
    for t in _zh_tags(row["diets"], config.DIET_TAGS_ZH):
        tags.append(f'<span class="tag diet">{e(t)}</span>')
    for t in _zh_tags(row["allergens"], config.ALLERGENS_ZH):
        tags.append(f'<span class="tag allergen">含{e(t)}</span>')
    meta = []
    if row["calories"]:
        meta.append(f'{e(row["calories"])} 千卡')
    if row["serving_size"]:
        meta.append(f'份量 {e(row["serving_size"])}')
    if tags or meta:
        parts.append(f'<div class="meta">{"".join(tags)} {e(" · ".join(meta))}</div>')
    parts.append("</li>")
    return "".join(parts)


def render(conn, date_iso, halls):
    """生成当日菜单页，返回输出文件路径。halls: [{name, hours}]。"""
    rows = db.menu_for_date(conn, date_iso)
    first_run = db.is_first_run(conn, date_iso)
    today_dt = datetime.date.fromisoformat(date_iso)
    e = html.escape

    # meal -> hall -> station -> [row]（选餐段，再比食堂）
    grouped = {}
    for r in rows:
        grouped.setdefault(r["meal"], {}).setdefault(r["hall"], {}) \
               .setdefault(r["station"] or "其他", []).append(r)
    meals = sorted(grouped, key=_meal_sort_key)

    new_dishes = sorted({r["name_zh"] or r["name_en"]
                         for r in rows if r["first_seen"] == date_iso}) \
        if not first_run else []

    body = []
    hours_line = " ｜ ".join(
        f'<b>{e(config.HALL_NAMES_ZH.get(h["name"], h["name"]))}</b> {e(h["hours"])}'
        for h in halls)
    body.append(f'<div class="hours">今日开放：{hours_line}</div>')

    if new_dishes:
        shown = "、".join(e(n) for n in new_dishes[:15])
        more = f" 等 {len(new_dishes)} 道" if len(new_dishes) > 15 else ""
        body.append(f'<div class="newbox"><b>今日新菜</b>：{shown}{more}</div>')

    tabs = []
    for meal in meals:
        n = sum(len(d) for stations in grouped[meal].values()
                for d in stations.values())
        label = e(config.MEAL_NAMES_ZH.get(meal, meal))
        tabs.append(f'<button class="tab" data-meal="{_slug(meal)}">'
                    f'{label}<span class="n">{n}</span></button>')
    body.append(f'<div class="tabbar">{"".join(tabs)}</div>')

    for meal in meals:
        body.append(f'<div class="mealpane" id="meal-{_slug(meal)}" style="display:none">')
        for hall in sorted(grouped[meal], key=_hall_sort_key):
            zh_name = config.HALL_NAMES_ZH.get(hall)
            title = (f'{e(zh_name)}<span class="en">{e(hall)}</span>'
                     if zh_name else e(hall))
            body.append(f'<h2 class="hall">{title}</h2>')
            for station, dishes in grouped[meal][hall].items():
                body.append(f'<h4 class="station">{e(station)}</h4><ul class="dishes">')
                body.extend(_dish_li(r, date_iso, first_run) for r in dishes)
                body.append("</ul>")
        body.append("</div>")

    n_pending = sum(1 for r in rows if not r["name_zh"])
    pending = f"（{n_pending} 道菜暂未翻译，下次运行自动补翻）" if n_pending else ""
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

    icon = ('data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" '
            'viewBox="0 0 100 100"><rect width="100" height="100" rx="20" '
            'fill="%23881c1c"/><text x="50" y="72" font-size="60" '
            'text-anchor="middle" fill="white">饭</text></svg>')
    page = f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="theme-color" content="#881c1c">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-title" content="UMass菜单">
<link rel="icon" href='{icon}'>
<title>UMass 今日菜单 {date_iso}</title><style>{CSS}</style></head>
<body><header><div class="wrap">
<h1>UMass 今日中文菜单</h1>
<div class="sub">{date_iso} {WEEKDAYS[today_dt.weekday()]} · 共 {len(rows)} 道菜 {pending}</div>
</div></header><div class="wrap">
{"".join(body)}
<footer>生成于 {now} · 数据来自 umassdining.com</footer>
</div><script>{JS}</script></body></html>"""

    config.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    dated = config.OUTPUT_DIR / f"menu_{date_iso}.html"
    dated.write_text(page, encoding="utf-8")
    # index.html 即 GitHub Pages 首页 = 当天菜单
    (config.OUTPUT_DIR / "index.html").write_text(page, encoding="utf-8")
    return dated
