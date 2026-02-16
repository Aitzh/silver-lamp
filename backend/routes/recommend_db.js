// backend_routes_recommend_db.js - ИСПРАВЛЕННЫЙ роутер рекомендаций
import { Router } from "express";
import sqlite3 from "sqlite3";
import { promisify } from "util";
import path from "path";
import { fileURLToPath } from "url";
import fs from "fs";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const router = Router();

// Путь к БД - используем абсолютный путь или переменную окружения
const DB_PATH = process.env.CONTENT_DB_PATH || path.join(process.cwd(), "content.db");

// Проверяем существование БД
if (!fs.existsSync(DB_PATH)) {
    console.error(`❌ content.db не найден по пути: ${DB_PATH}`);
}

const db = new sqlite3.Database(DB_PATH, (err) => {
    if (err) {
        console.error('❌ Ошибка подключения к content.db:', err.message);
    } else {
        console.log('✅ Подключено к content.db');
    }
});

const dbAll = promisify(db.all.bind(db));
const dbGet = promisify(db.get.bind(db));

// Маппинги фильтров (как в оригинале)
const FILTER_MAPPING = {
    "ЖАНР": "genre", "ЭПОХА": "epoch", "КРИТЕРИЙ": "criteria",
    "АТМОСФЕРА": "mood", "НАСТРОЕНИЕ": "mood", "GENRE": "genre",
    "ERA": "epoch", "EPOCH": "epoch", "CRITERIA": "criteria",
    "VIBE": "mood", "MOOD": "mood", "ДӘУІР": "epoch", "КӨҢІЛ-КҮЙ": "mood"
};

const VALUE_MAPPING = {
    "Драма": "drama", "Комедия": "comedy", "Ужасы": "horror", 
    "Фантастика": "sci-fi", "Боевик": "action", "Триллер": "thriller",
    "Анимация": "animation", "Документальный": "documentary",
    "Криминал": "crime", "Приключения": "adventure", "Семейный": "family",
    "Фэнтези": "fantasy", "История": "history", "Музыкальный": "music",
    "Детектив": "mystery", "Романтика": "romance", "Военный": "war",
    "Вестерн": "western", "Научная фантастика": "sci-fi",
    "Классика": "classics", "Нон-фикшн": "non-fiction", "Роман": "romance",
    "Исторический": "historical", "Философия": "philosophy",
    "Психология": "psychology", "Антиутопия": "dystopian",
    "Поп": "pop", "Рок": "rock", "Джаз": "jazz", "Классическая": "classical",
    "Хип-хоп": "hip-hop", "Техно": "electronic", "Электронная": "electronic",
    "Инди": "indie", "Метал": "metal", "Блюз": "blues", "Кантри": "country",
    "R&B": "r-n-b", "Латиноамериканская": "latin",
    "Новинки": "new_releases", "2020-е": "2020s", "2010-е": "2010s",
    "2000-е": "2000s", "90-е": "90s", "80-е": "80s", "Ретро": "retro",
    "Золотая Классика": "golden_classics", "Бестселлеры 2025": "bestsellers_2025",
    "Жаңалықтар": "new_releases", "2020-шы": "2020s", "2010-шы": "2010s",
    "2000-шы": "2000s", "90-шы": "90s", "80-ші": "80s", 
    "Алтын классика": "golden_classics",
    "Оскар": "oscar", "Культовый": "cult", "Хит проката": "blockbuster",
    "Скрытый шедевр": "hidden_gem", "Артхаус": "arthouse",
    "Высокий рейтинг": "high_rated", "Популярный": "popular",
    "Бестселлер": "bestseller", "Культовая": "cult",
    "Интеллектуальная": "intellectual", "Современная": "modern",
    "Хит": "hit", "Популярная": "popular", "Восходящая звезда": "rising",
    "Андеграунд": "underground", "Энергия": "energetic",
    "Энергичная": "energetic", "Чилл": "chill", "Вечеринка": "party",
    "Фокус": "focus"
};

const EPOCH_YEAR_RANGES = {
    "new_releases": { min: 2023, max: 2025 },
    "bestsellers_2025": { min: 2024, max: 2025 },
    "2020s": { min: 2020, max: 2029 },
    "2010s": { min: 2010, max: 2019 },
    "2000s": { min: 2000, max: 2009 },
    "90s": { min: 1990, max: 1999 },
    "80s": { min: 1980, max: 1989 },
    "golden_classics": { min: 1900, max: 1979 },
    "retro": { min: 1900, max: 1989 }
};

function normalizeValue(value) {
    if (!value) return null;
    const mapped = VALUE_MAPPING[value];
    return (mapped || value).toLowerCase().trim();
}

async function searchWithFallback(dbType, filters, excludeIds = []) {
    const appliedFilters = [];
    let yearRange = null;
    
    for (const [filterKey, filterValue] of Object.entries(filters)) {
        const dbColumn = FILTER_MAPPING[filterKey];
        const normalizedValue = normalizeValue(filterValue);
        
        if (dbColumn && normalizedValue) {
            if (dbColumn === 'epoch' && EPOCH_YEAR_RANGES[normalizedValue]) {
                yearRange = EPOCH_YEAR_RANGES[normalizedValue];
            }
            appliedFilters.push({ column: dbColumn, value: normalizedValue });
        }
    }
    
    let excludeClause = "";
    let excludeParams = [];
    if (excludeIds.length > 0) {
        const placeholders = excludeIds.map(() => "?").join(",");
        excludeClause = ` AND id NOT IN (${placeholders})`;
        excludeParams = excludeIds;
    }
    
    // Стратегия 1: AND все фильтры
    if (appliedFilters.length > 0) {
        let query = `SELECT * FROM content WHERE type = ?`;
        const params = [dbType];
        
        if (yearRange) {
            query += ` AND year >= ? AND year <= ?`;
            params.push(yearRange.min, yearRange.max);
        }
        
        appliedFilters.forEach(f => {
            if (f.column !== 'epoch') {
                query += ` AND LOWER(${f.column}) = LOWER(?)`;
                params.push(f.value);
            }
        });
        
        query += excludeClause + ` ORDER BY RANDOM() LIMIT 50`;
        const results = await dbAll(query, [...params, ...excludeParams]);
        
        if (results.length >= 10) return results.slice(0, 10);
    }
    
    // Стратегия 2: OR фильтры
    if (appliedFilters.length > 1) {
        let query = `SELECT * FROM content WHERE type = ?`;
        const params = [dbType];
        
        if (yearRange) {
            query += ` AND year >= ? AND year <= ?`;
            params.push(yearRange.min, yearRange.max);
        }
        
        query += excludeClause;
        params.push(...excludeParams);
        
        const conditions = appliedFilters
            .filter(f => f.column !== 'epoch')
            .map(f => {
                params.push(f.value);
                return `LOWER(${f.column}) = LOWER(?)`;
            });
        
        if (conditions.length > 0) {
            query += ` AND (${conditions.join(" OR ")}) ORDER BY RANDOM() LIMIT 50`;
            const results = await dbAll(query, params);
            if (results.length > 0) return results.slice(0, 10);
        }
    }
    
    // Стратегия 3: Fallback
    let query = `SELECT * FROM content WHERE type = ?`;
    const params = [dbType];
    
    if (yearRange) {
        query += ` AND year >= ? AND year <= ?`;
        params.push(yearRange.min, yearRange.max);
    }
    
    query += excludeClause + ` ORDER BY RANDOM() LIMIT 10`;
    return await dbAll(query, [...params, ...excludeParams]);
}

function getDescriptionByLang(item, lang) {
    if (lang === 'en' && item.description_en) return item.description_en;
    if ((lang === 'kk' || lang === 'kz') && item.description_kk) return item.description_kk;
    if (lang === 'ru' && item.description_ru) return item.description_ru;
    return item.description || "Great choice!";
}

router.post("/:type", async (req, res) => {
    try {
        const { type } = req.params;
        const { filters = {}, excludeIds = [], lang = 'ru' } = req.body;
        
        console.log(`🔍 [${type}] Запрос, язык: ${lang}`);
        
        if (!["movies", "books", "music"].includes(type)) {
            return res.status(400).json({ error: "Invalid type" });
        }
        
        const dbType = type === "movies" ? "movie" : type === "books" ? "book" : "music";
        const results = await searchWithFallback(dbType, filters, excludeIds);
        
        if (results.length === 0) {
            return res.json({ recommendations: [], message: "No content found" });
        }
        
        const recommendations = results.map(item => ({
            id: item.id,
            source_id: item.source_id,
            title: item.title,
            image: item.image_url,
            year: item.year,
            rating: item.rating,
            why: getDescriptionByLang(item, lang),
            ...(type === "movies" && { genre: item.genre }),
            ...(type === "books" && { author: item.creator }),
            ...(type === "music" && { artist: item.creator })
        }));
        
        res.json({ recommendations, count: recommendations.length, lang });
        
    } catch (err) {
        console.error(`❌ [${req.params.type}] Error:`, err);
        res.status(500).json({ error: "Server error" });
    }
});

router.get("/stats", async (req, res) => {
    try {
        const total = await dbGet("SELECT COUNT(*) as count FROM content");
        const byType = await dbAll("SELECT type, COUNT(*) as count FROM content GROUP BY type");
        
        res.json({
            total: total.count,
            byType: byType.reduce((acc, row) => { acc[row.type] = row.count; return acc; }, {})
        });
    } catch (err) {
        res.status(500).json({ error: "Failed to get stats" });
    }
});

process.on("SIGTERM", () => db.close());

export default router;