import { Router } from "express";
import { callAI } from "../ai/client.js";
import { cache } from "../utils/smartCache.js";
import { searchBooks } from "../services/googleBooks.js";
import { searchMovies } from "../services/tmdb.js";
import { searchTracks } from "../services/spotify.js";

const router = Router();

/**
 * ПОЛНЫЙ МАППИНГ ВСЕХ ФИЛЬТРОВ НА АНГЛИЙСКИЙ
 * Включает русский И казахский языки!
 */
const filterTranslations = {
    // ========== ЖАНРЫ КНИГ ==========
    // Русский
    "Фэнтези": "Fantasy",
    "Научная фантастика": "Science Fiction",
    "Детектив": "Mystery",
    "Триллер": "Thriller",
    "Классика": "Classics",
    "Нон-фикшн": "Non-fiction",
    "Роман": "Romance",
    "Приключения": "Adventure",
    
    // Казахский (книги)
    "Ғылыми фантастика": "Science Fiction",
    "Шытырман": "Adventure",
    
    // ========== ЖАНРЫ ФИЛЬМОВ ==========
    // Русский
    "Драма": "Drama",
    "Комедия": "Comedy",
    "Ужасы": "Horror",
    "Фантастика": "Sci-Fi",
    "Вестерн": "Western",
    "Анимация": "Animation",
    "Боевик": "Action",
    
    // Казахский (фильмы)
    "Қорқынышты": "Horror",
    
    // ========== ЭПОХИ ==========
    // Русский
    "Золотая Классика": "Golden Age",
    "80-е годы": "1980s",
    "90-е годы": "1990s",
    "2010-е": "2010s",
    "Бестселлеры 2025": "Bestsellers 2025",
    "Новинки": "New Releases",
    "2000-е": "2000s",
    "90-е": "1990s",
    "Ретро Классика": "Retro Classic",
    "Любое время": "Any Time",
    
    // Казахский (эпохи)
    "Алтын ғасыр": "Golden Age",
    "80-ші жылдар": "1980s",
    "90-шы жылдар": "1990s",
    "2010-шы жылдар": "2010s",
    "Бестселлерлер 2025": "Bestsellers 2025",
    "Жаңалықтар": "New Releases",
    "2000-шы жылдар": "2000s",
    "Кез келген уақыт": "Any Time",
    
    // ========== АТМОСФЕРА/НАСТРОЕНИЕ ==========
    // Русский
    "Уютная": "Cozy",
    "Вдохновляющая": "Inspiring",
    "Мрачная": "Dark",
    "Философская": "Philosophical",
    "Напряженная": "Tense",
    "Легкая": "Light",
    "Энергия": "Energy",
    "Чилл": "Chill",
    "Грусть": "Sad",
    "Ночной драйв": "Night Drive",
    "Тренировка": "Workout",
    "Фокус": "Focus",
    
    // Казахский (настроение)
    "Ыңғайлы": "Cozy",
    "Шабыттандыратын": "Inspiring",
    "Тұнжыраған": "Dark",
    "Философиялық": "Philosophical",
    "Шиеленісті": "Tense",
    "Жеңіл": "Light",
    "Демалыс": "Chill",
    "Мұңлы": "Sad",
    "Түнгі драйв": "Night Drive",
    "Жаттығу": "Workout",
    
    // ========== КРИТЕРИИ ==========
    // Русский
    "Оскар": "Oscar Winners",
    "Хит проката": "Blockbuster",
    "Скрытый шедевр": "Hidden Gem",
    "Артхаус": "Arthouse",
    
    // Казахский (критерии)
    "Хиттер": "Blockbuster",
    "Жасырын шедевр": "Hidden Gem",
    
    // ========== ЖАНРЫ МУЗЫКИ ==========
    // Русский
    "Поп": "Pop",
    "Рок": "Rock",
    "Классика": "Classical",
    "Джаз": "Jazz",
    "Хип-хоп": "Hip-Hop",
    "Техно": "Techno",
    "Инди": "Indie",
    "Метал": "Metal",
    
    // Английский (для fallback)
    "Fantasy": "Fantasy",
    "Science Fiction": "Science Fiction",
    "Sci-Fi": "Sci-Fi",
    "Mystery": "Mystery",
    "Drama": "Drama",
    "Comedy": "Comedy",
    "Horror": "Horror",
    "Action": "Action",
    "Pop": "Pop",
    "Rock": "Rock",
    "Classical": "Classical",
    "Jazz": "Jazz",
    "Hip-Hop": "Hip-Hop",
    "Techno": "Techno",
    "Indie": "Indie",
    "Metal": "Metal"
};

/**
 * Переводит фильтры на английский для API
 * Работает с русским, казахским и английским
 */
function translateFiltersToEnglish(filters) {
    const translated = {};
    
    for (const [key, value] of Object.entries(filters)) {
        // Если значение уже на английском - оставляем как есть
        if (filterTranslations[value]) {
            translated[key] = filterTranslations[value];
            console.log(`   🔄 "${value}" → "${filterTranslations[value]}"`);
        } else {
            // Если перевода нет - оставляем оригинал (на всякий случай)
            translated[key] = value;
            console.log(`   ⚠️ "${value}" - перевод не найден, оставляем как есть`);
        }
    }
    
    return translated;
}

/**
 * Стратегии для разных типов контента
 */
const strategies = {
    books: {
        async search(filters) {
            const englishFilters = translateFiltersToEnglish(filters);
            return searchBooks(
                englishFilters["ЖАНР"] || englishFilters["GENRE"] || "Fiction",
                englishFilters["ЭПОХА"] || englishFilters["ERA"] || "",
                Math.floor(Math.random() * 10)
            );
        },
        
        buildPrompt(filters, items, lang) {
            const englishFilters = translateFiltersToEnglish(filters);
            const mood = englishFilters["АТМОСФЕРА"] || englishFilters["VIBE"] || "interesting";
            const langNames = { ru: "Russian", kz: "Kazakh", en: "English" };
            const targetLang = langNames[lang] || "English";
            
            return `Task: You are a professional book curator. Select exactly 5 books for someone seeking a "${mood}" reading experience.

Books to choose from:
${JSON.stringify(items.slice(0, 15).map(b => ({
    id: String(b.id),
    title: b.title,
    description: b.description?.slice(0, 200) || ""
})))}

CRITICAL RULES:
1. Return ONLY a valid JSON array, nothing else
2. Each item MUST have this exact structure: {"id": "string", "why": "string"}
3. The "why" field must be ONE sentence (max 120 characters) explaining why this book perfectly matches the "${mood}" atmosphere
4. Write "why" in ${targetLang} language
5. Select books that genuinely fit the requested mood
6. NO markdown, NO code blocks, NO explanations - just pure JSON

Example format:
[
  {"id": "abc123", "why": "Захватывающий триллер с неожиданной развязкой"},
  {"id": "def456", "why": "Философская притча о смысле жизни"}
]`;
        },
        
        formatResult(original, aiData, lang) {
            return {
                id: String(original.id),
                title: original.title,
                author: original.authors,
                image: original.image,
                why: aiData.why || original.description?.slice(0, 150) || "Great choice"
            };
        },
        
        fallback(items, lang) {
            const fallbackTexts = {
                ru: "Рекомендовано специально для вас",
                en: "Specially recommended for you",
                kz: "Сіз үшін ұсынылған"
            };
            
            return items.slice(0, 5).map(b => ({
                id: String(b.id),
                title: b.title,
                author: b.authors,
                image: b.image,
                why: b.description?.slice(0, 150) || fallbackTexts[lang] || fallbackTexts.en
            }));
        }
    },

    movies: {
        async search(filters) {
            const englishFilters = translateFiltersToEnglish(filters);
            return searchMovies(
                englishFilters["ЖАНР"] || englishFilters["GENRE"] || "Drama",
                englishFilters["ЭПОХА"] || englishFilters["ERA"] || "New Releases",
                englishFilters["КРИТЕРИЙ"] || englishFilters["CRITERIA"] || "Blockbuster"
            );
        },
        
        buildPrompt(filters, items, lang) {
            const englishFilters = translateFiltersToEnglish(filters);
            const criteria = englishFilters["КРИТЕРИЙ"] || englishFilters["CRITERIA"] || "popular";
            const langNames = { ru: "Russian", kz: "Kazakh", en: "English" };
            const targetLang = langNames[lang] || "English";
            
            return `Task: You are a professional film critic. Select exactly 5 movies that match "${criteria}" criteria.

Movies to choose from:
${JSON.stringify(items.slice(0, 15).map(m => ({
    id: String(m.id),
    title: m.title,
    year: m.year,
    rating: m.rating,
    overview: m.overview?.slice(0, 200) || ""
})))}

CRITICAL RULES:
1. Return ONLY a valid JSON array
2. Each item MUST have: {"id": "string", "why": "string"}
3. The "why" must be ONE sentence (max 120 characters) explaining why this film matches "${criteria}"
4. Write "why" in ${targetLang} language
5. NO markdown, NO code blocks - just JSON

Example:
[
  {"id": "550", "why": "Культовый фильм, изменивший кинематограф"},
  {"id": "680", "why": "Мощная драма о человеческих ценностях"}
]`;
        },
        
        formatResult(original, aiData, lang) {
            return {
                id: String(original.id),
                title: original.title,
                year: original.year,
                rating: original.rating,
                image: original.image,
                why: aiData.why || original.overview?.slice(0, 150) || "Highly rated"
            };
        },
        
        fallback(items, lang) {
            const fallbackTexts = {
                ru: "Популярный выбор зрителей",
                en: "Popular audience choice",
                kz: "Көрермендердің танымал таңдауы"
            };
            
            return items.slice(0, 5).map(m => ({
                id: String(m.id),
                title: m.title,
                year: m.year,
                rating: m.rating,
                image: m.image,
                why: m.overview?.slice(0, 150) || fallbackTexts[lang] || fallbackTexts.en
            }));
        }
    },

    music: {
        async search(filters) {
            const englishFilters = translateFiltersToEnglish(filters);
            const genre = (englishFilters["ЖАНР"] || englishFilters["GENRE"] || ["Pop"])[0] || "Pop";
            return searchTracks(genre.toLowerCase(), Math.floor(Math.random() * 20));
        },
        
        buildPrompt(filters, items, lang) {
            const englishFilters = translateFiltersToEnglish(filters);
            const vibe = englishFilters["НАСТРОЕНИЕ"] || englishFilters["ВАЙБ"] || englishFilters["VIBE"] || "chill";
            const langNames = { ru: "Russian", kz: "Kazakh", en: "English" };
            const targetLang = langNames[lang] || "English";
            
            return `Task: You are a music curator. Select exactly 5 tracks for a "${vibe}" vibe.

Tracks to choose from:
${JSON.stringify(items.slice(0, 15).map(t => ({
    id: String(t.id),
    title: t.title,
    artist: t.artist
})))}

CRITICAL RULES:
1. Return ONLY a valid JSON array
2. Each item MUST have: {"id": "string", "why": "string"}
3. The "why" must be ONE short sentence (max 100 characters) about why it fits "${vibe}"
4. Write "why" in ${targetLang} language
5. NO markdown, NO code blocks

Example:
[
  {"id": "xyz", "why": "Идеальная энергия для тренировки"},
  {"id": "abc", "why": "Расслабляющая мелодия для отдыха"}
]`;
        },
        
        formatResult(original, aiData, lang) {
            return {
                id: String(original.id),
                title: original.title,
                artist: original.artist,
                image: original.image,
                duration: original.duration,
                why: aiData.why || "Perfect track"
            };
        },
        
        fallback(items, lang) {
            const fallbackTexts = {
                ru: "Подобрано для вашего настроения",
                en: "Curated for your mood",
                kz: "Сіздің көңіл-күйіңізге сай"
            };
            
            return items.slice(0, 5).map(t => ({
                id: String(t.id),
                title: t.title,
                artist: t.artist,
                image: t.image,
                duration: t.duration,
                why: fallbackTexts[lang] || fallbackTexts.en
            }));
        }
    }
};

/**
 * Универсальный обработчик рекомендаций
 */
router.post("/:type", async (req, res) => {
    try {
        const { type } = req.params;
        const { filters = {}, lang = 'en', coffee } = req.body;
        
        // Валидация типа контента
        if (!strategies[type]) {
            return res.status(404).json({ 
                error: "Unknown content type. Available: books, movies, music" 
            });
        }

        // Генерация ключа кеша (включая язык!)
        const cacheKey = `${type}:${JSON.stringify(filters)}:${lang}`;
        
        // Проверка кеша
        const cached = cache.get(cacheKey);
        if (cached) {
            console.log(`📦 [${type}] Кеш HIT (${lang})`);
            return res.json({ recommendations: cached, cached: true });
        }

        console.log(`🔍 [${type}] Поиск контента (язык интерфейса: ${lang})`);
        console.log(`📋 [${type}] Исходные фильтры:`, filters);
        
        // Получение стратегии
        const strategy = strategies[type];
        
        // КРИТИЧНО: Переводим фильтры на английский ПЕРЕД поиском
        console.log(`🌐 [${type}] Перевод фильтров на английский...`);
        const englishFilters = translateFiltersToEnglish(filters);
        console.log(`✅ [${type}] Переведенные фильтры:`, englishFilters);
        
        // ВАЖНО: Поиск всегда на английском
        const rawItems = await strategy.search(filters);
        
        if (!rawItems || rawItems.length === 0) {
            console.log(`⚠️ [${type}] Контент не найден для фильтров:`, filters);
            return res.json({ 
                recommendations: [], 
                message: "No content found for these filters" 
            });
        }

        console.log(`✅ [${type}] Найдено ${rawItems.length} элементов`);

        let recommendations = [];

        try {
            // Промпт с указанием целевого языка
            const prompt = strategy.buildPrompt(filters, rawItems, lang);
            
            console.log(`🤖 [${type}] Запрос к ИИ (перевод на ${lang})...`);
            const aiResponse = await callAI(prompt, true);
            
            // Парсинг JSON
            let selected = [];
            try {
                selected = JSON.parse(aiResponse);
            } catch {
                const match = aiResponse.match(/\[[\s\S]*?\]/);
                if (match) {
                    selected = JSON.parse(match[0]);
                } else {
                    throw new Error("AI returned invalid JSON");
                }
            }

            if (!Array.isArray(selected) || selected.length === 0) {
                throw new Error("AI returned empty array");
            }

            // Формирование результатов
            recommendations = selected
                .map(aiData => {
                    const original = rawItems.find(item => 
                        String(item.id) === String(aiData.id)
                    );
                    return original ? strategy.formatResult(original, aiData, lang) : null;
                })
                .filter(Boolean)
                .slice(0, 5);

            console.log(`✅ [${type}] ИИ вернул ${recommendations.length} элементов на ${lang}`);

        } catch (aiError) {
            console.error(`⚠️ [${type}] Ошибка ИИ, fallback:`, aiError.message);
            recommendations = strategy.fallback(rawItems, lang);
        }

        // Финальная проверка
        if (recommendations.length === 0) {
            console.log(`⚠️ [${type}] Fallback к базовым результатам`);
            recommendations = strategy.fallback(rawItems, lang);
        }

        // Сохранение в кеш
        cache.set(cacheKey, recommendations);
        
        res.json({ 
            recommendations,
            cached: false,
            count: recommendations.length,
            lang: lang
        });

    } catch (err) {
        console.error(`❌ [${req.params.type}] Router Error:`, err);
        res.status(500).json({ 
            error: "Server error",
            message: process.env.NODE_ENV === 'development' ? err.message : undefined
        });
    }
});

/**
 * Очистка кеша
 */
router.post("/cache/clear", (req, res) => {
    cache.clear();
    res.json({ success: true, message: "Cache cleared" });
});

/**
 * Статистика кеша
 */
router.get("/cache/stats", (req, res) => {
    res.json(cache.getStats());
});

export default router;