"""抓取 UMass Dining 数据：营业状态（get_infov2）+ 详细菜单（foodpro-menu-ajax）。"""
import json
import time
import urllib.request
from html.parser import HTMLParser

from . import config


def _get(url):
    req = urllib.request.Request(url, headers={
        "User-Agent": config.USER_AGENT,
        "X-Requested-With": "XMLHttpRequest",
    })
    return urllib.request.urlopen(req, timeout=config.REQUEST_TIMEOUT).read().decode("utf-8")


def open_locations():
    """返回今天开放的餐厅列表：[{tid, name, hours}]。"""
    data = json.loads(_get(config.INFO_URL))
    result = []
    for loc in data:
        opening = (loc.get("opening_hours") or "").strip()
        if not opening or opening.lower() == "closed":
            continue
        if loc["short_name"].strip() in config.EXCLUDED_HALLS:
            continue
        result.append({
            "tid": loc["location_id"],
            "name": loc["short_name"].strip(),
            "hours": f"{opening} – {loc.get('closing_hours', '')}".strip(" –"),
        })
    return result


class _DishParser(HTMLParser):
    """foodpro 返回的每个档口是一段 HTML，菜品在 <a data-dish-name=...> 里。"""

    def __init__(self):
        super().__init__()
        self.dishes = []

    def handle_starttag(self, tag, attrs):
        if tag != "a":
            return
        a = dict(attrs)
        name = (a.get("data-dish-name") or "").strip()
        if not name:
            return
        self.dishes.append({
            "name_en": " ".join(name.split()),
            "calories": (a.get("data-calories") or "").strip(),
            "serving_size": (a.get("data-serving-size") or "").strip(),
            "allergens": (a.get("data-allergens") or "").strip().rstrip(", "),
            "diets": (a.get("data-clean-diet-str") or "").strip(),
            "ingredients": (a.get("data-ingredient-list") or "").strip(),
        })


def fetch_menu(tid, date_str):
    """抓取单个餐厅某天的菜单。

    返回 {meal: {station: [dish_dict, ...]}}；该餐厅无菜单数据时返回 {}。
    date_str 格式 MM/DD/YYYY。
    """
    raw = _get(config.MENU_URL.format(tid=tid, date=date_str))
    data = json.loads(raw)
    if not isinstance(data, dict):
        return {}
    menu = {}
    for meal, stations in data.items():
        if not isinstance(stations, dict):
            continue
        for station, html in stations.items():
            p = _DishParser()
            p.feed(html)
            if p.dishes:
                menu.setdefault(meal.lower(), {})[station.strip()] = p.dishes
    return menu


def fetch_all(date_str):
    """抓取所有开放餐厅的菜单。返回 (halls, menus)。

    halls: [{tid, name, hours}]（只含有菜单数据的）
    menus: {hall_name: {meal: {station: [dish, ...]}}}
    """
    halls, menus = [], {}
    for loc in open_locations():
        try:
            menu = fetch_menu(loc["tid"], date_str)
        except Exception:
            menu = {}
        if menu:
            halls.append(loc)
            menus[loc["name"]] = menu
        time.sleep(config.REQUEST_DELAY)
    return halls, menus
