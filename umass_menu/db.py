"""SQLite 存储：菜品（含翻译缓存）、每日菜单记录、照片。"""
import sqlite3

from . import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS dishes (
    id           INTEGER PRIMARY KEY,
    name_en      TEXT UNIQUE NOT NULL,
    name_zh      TEXT,
    first_seen   TEXT NOT NULL,
    last_seen    TEXT,
    calories     TEXT,
    serving_size TEXT,
    allergens    TEXT,
    diets        TEXT,
    ingredients  TEXT,
    is_favorite  INTEGER DEFAULT 0,
    notes        TEXT
);
CREATE TABLE IF NOT EXISTS menu_records (
    id      INTEGER PRIMARY KEY,
    date    TEXT NOT NULL,
    hall    TEXT NOT NULL,
    meal    TEXT NOT NULL,
    station TEXT,
    dish_id INTEGER NOT NULL REFERENCES dishes(id),
    UNIQUE(date, hall, meal, station, dish_id)
);
CREATE TABLE IF NOT EXISTS photos (
    id        INTEGER PRIMARY KEY,
    dish_id   INTEGER NOT NULL REFERENCES dishes(id),
    file_path TEXT NOT NULL,
    taken_at  TEXT
);
CREATE INDEX IF NOT EXISTS idx_menu_date ON menu_records(date);
"""


def connect():
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn


def upsert_dish(conn, dish, today):
    """按英文名去重写入菜品，返回 dish_id。营养信息每次刷新为最新值。"""
    conn.execute(
        """INSERT INTO dishes (name_en, first_seen, last_seen, calories,
               serving_size, allergens, diets, ingredients)
           VALUES (:name_en, :today, :today, :calories, :serving_size,
               :allergens, :diets, :ingredients)
           ON CONFLICT(name_en) DO UPDATE SET
               last_seen = :today,
               calories = :calories, serving_size = :serving_size,
               allergens = :allergens, diets = :diets,
               ingredients = :ingredients""",
        {**dish, "today": today},
    )
    row = conn.execute(
        "SELECT id FROM dishes WHERE name_en = ?", (dish["name_en"],)
    ).fetchone()
    return row["id"]


def add_menu_record(conn, date, hall, meal, station, dish_id):
    conn.execute(
        """INSERT OR IGNORE INTO menu_records (date, hall, meal, station, dish_id)
           VALUES (?, ?, ?, ?, ?)""",
        (date, hall, meal, station, dish_id),
    )


def untranslated_names(conn):
    rows = conn.execute(
        "SELECT name_en FROM dishes WHERE name_zh IS NULL OR name_zh = ''"
    ).fetchall()
    return [r["name_en"] for r in rows]


def save_translations(conn, mapping):
    conn.executemany(
        "UPDATE dishes SET name_zh = ? WHERE name_en = ? AND (name_zh IS NULL OR name_zh = '')",
        [(zh, en) for en, zh in mapping.items()],
    )


def menu_for_date(conn, date):
    return conn.execute(
        """SELECT m.hall, m.meal, m.station,
                  d.name_en, d.name_zh, d.calories, d.serving_size,
                  d.allergens, d.diets, d.first_seen, d.is_favorite
           FROM menu_records m JOIN dishes d ON d.id = m.dish_id
           WHERE m.date = ?
           ORDER BY m.hall, m.meal, m.station, d.name_en""",
        (date,),
    ).fetchall()


def is_first_run(conn, today):
    """库里最早的菜就是今天出现的 → 首次运行，不标注"新菜"。"""
    row = conn.execute("SELECT MIN(first_seen) AS m FROM dishes").fetchone()
    return row["m"] is None or row["m"] == today
