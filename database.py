import aiosqlite
import logging

logger = logging.getLogger(__name__)
DB_NAME = "zapaleni_stats.db"

async def init_db():
    """Создает таблицу с поддержкой уникальных хэшей для защиты от дубликатов."""
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('''
                    CREATE TABLE IF NOT EXISTS game_stats (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        activity TEXT,
                        gold INTEGER DEFAULT 0,
                        exp INTEGER DEFAULT 0,
                        nebesna INTEGER DEFAULT 0,
                        svaroja INTEGER DEFAULT 0,
                        fragment INTEGER DEFAULT 0,
                        armor_scroll INTEGER DEFAULT 0,
                        weapon_scroll INTEGER DEFAULT 0,
                        report_hash TEXT UNIQUE, 
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
        await db.commit()
    logger.info("База данных инициализирована (Multi-tenant + Идемпотентность).")

async def save_report(user_id: int, activity: str, gold: int, exp: int,
                      nebesna: int, svaroja: int, fragment: int,
                      armor_scroll: int, weapon_scroll: int,
                      report_hash: str, report_date: str) -> bool:
    async with aiosqlite.connect(DB_NAME) as db:
        try:
            await db.execute(
                '''INSERT INTO game_stats 
                   (user_id, activity, gold, exp, nebesna, svaroja, fragment, armor_scroll, weapon_scroll, report_hash, timestamp) 
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                (user_id, activity, gold, exp, nebesna, svaroja, fragment, armor_scroll, weapon_scroll, report_hash, report_date)
            )
            await db.commit()
            return True
        except aiosqlite.IntegrityError:
            return False

async def get_analytics(user_id: int, activity: str, period: str) -> dict:
    """Универсальная аналитика: фильтрует по дате и категории, группирует результат."""
    query = """
            SELECT activity, SUM(gold), SUM(exp), 
                   SUM(nebesna), SUM(svaroja), SUM(fragment), 
                   SUM(armor_scroll), SUM(weapon_scroll) 
            FROM game_stats WHERE user_id = ?
        """
    params = [user_id]

    # Фильтр по периоду (UTC -> смещение +3 часа)
    if period == 'today':
        query += " AND date(timestamp, '+3 hours') = date('now', '+3 hours')"
    elif period == 'yesterday':
        query += " AND date(timestamp, '+3 hours') = date('now', '+3 hours', '-1 day')"
    elif period == 'week':
        query += " AND timestamp >= datetime('now', '+3 hours', '-7 days')"
    elif period == 'month':
        query += " AND timestamp >= datetime('now', '+3 hours', '-30 days')"
    # Для period == 'all' дополнительные условия не нужны

    # Фильтр по категории (если не выбрано "Все")
    if activity != "all":
        query += " AND activity = ?"
        params.append(activity)

    query += " GROUP BY activity"

    results = {}
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute(query, params) as cursor:
            rows = await cursor.fetchall()
            for row in rows:
                results[row[0]] = {
                    "gold": row[1] or 0,
                    "exp": row[2] or 0,
                    "nebesna": row[3] or 0,
                    "svaroja": row[4] or 0,
                    "fragment": row[5] or 0,
                    "armor_scroll": row[6] or 0,
                    "weapon_scroll": row[7] or 0
                }
    return results

def get_weekly_stats():
    return None