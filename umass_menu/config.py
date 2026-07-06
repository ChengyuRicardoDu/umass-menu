"""全局配置：路径、接口地址、翻译设置、显示映射。"""
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "docs"   # GitHub Pages 从 main 分支 /docs 目录发布
LOG_DIR = BASE_DIR / "logs"
DB_PATH = DATA_DIR / "dining.db"

# 生成页面后自动 git push 发布到 GitHub Pages；关掉则设为 False
AUTO_PUBLISH = True

INFO_URL = "https://umassdining.com/uapp/get_infov2"
MENU_URL = "https://umassdining.com/foodpro-menu-ajax?tid={tid}&date={date}"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) UMassMenuHelper/0.1"
REQUEST_TIMEOUT = 30
REQUEST_DELAY = 1.0  # 相邻请求间隔（秒），对学校服务器客气一点

# 翻译：优先 ANTHROPIC_API_KEY（未设置时走 claude CLI 无头模式，用订阅额度）
CLAUDE_CLI = "claude"
CLAUDE_MODEL = "haiku"
TRANSLATE_CHUNK = 50          # 每次请求翻译的菜名数量
TRANSLATE_TIMEOUT = 240       # 单次翻译请求超时（秒）

# 不抓取的餐厅（离得太远等原因）
EXCLUDED_HALLS = {
    "Charles River Campus of UMass Amherst",  # 在 Newton，离 Amherst 主校区 ~100 英里
}

MEAL_ORDER = ["breakfast", "brunch", "lunch", "dinner", "latenight",
              "grabngo", "daily offerings"]
MEAL_NAMES_ZH = {
    "breakfast": "早餐",
    "brunch": "早午餐",
    "lunch": "午餐",
    "dinner": "晚餐",
    "latenight": "夜宵",
    "grabngo": "即取即走",
    "daily offerings": "全天供应",
}

# 食堂显示顺序（不在列表里的排在后面，按字母序）
HALL_ORDER = [
    "Worcester Commons",
    "Franklin Dining Commons",
    "Hampshire Dining Commons",
    "Berkshire Dining Commons",
    "Harvest Market",
    "People's Organic Coffee",
]

# 常用食堂的中文昵称（显示用，找不到就只显示英文名）
HALL_NAMES_ZH = {
    "Worcester Commons": "沃斯特食堂 Woo",
    "Franklin Dining Commons": "富兰克林食堂 Frank",
    "Hampshire Dining Commons": "汉普食堂 Hamp",
    "Berkshire Dining Commons": "伯克食堂 Berk",
    "Harvest Market": "Harvest 市集餐吧",
}

DIET_TAGS_ZH = {
    "halal": "清真",
    "local": "本地食材",
    "sustainable": "可持续",
    "plant based": "植物基",
    "vegetarian": "素食",
    "vegan": "纯素",
    "whole grain": "全谷物",
    "gluten free": "无麸质",
    "antibiotic free": "无抗生素",
}

ALLERGENS_ZH = {
    "milk": "奶", "dairy": "奶", "eggs": "蛋", "egg": "蛋",
    "soy": "大豆", "soybeans": "大豆", "wheat": "小麦", "gluten": "麸质",
    "peanuts": "花生", "peanut": "花生", "tree nuts": "坚果", "treenuts": "坚果",
    "fish": "鱼", "shellfish": "贝类/甲壳类", "crustacean shellfish": "贝类/甲壳类",
    "sesame": "芝麻", "corn": "玉米", "coconut": "椰子", "sulfites": "亚硫酸盐",
}
