import fetch from "node-fetch";
import { config } from "../config.js";

/**
 * Поиск фильмов через TMDB API
 * @param {string} genreName - Название жанра (русское)
 * @param {string} era - Временной период
 * @param {string} criteria - Критерий отбора (Оскар, Хит проката и т.д.)
 * @returns {Promise<Array>} - Массив фильмов
 */
export async function searchMovies(genreName, era, criteria) {
    // Маппинг жанров на ID TMDB
    const genreMap = {
        "Драма": 18,
        "Комедия": 35,
        "Ужасы": 27,
        "Фантастика": 878,
        "Вестерн": 37,
        "Анимация": 16,
        "Боевик": 28,
        "Триллер": 53,
        // English variants
        "Drama": 18,
        "Comedy": 35,
        "Horror": 27,
        "Sci-Fi": 878,
        "Western": 37,
        "Animation": 16,
        "Action": 28,
        "Thriller": 53
    };

    // Маппинг эпох на годы выпуска
    const eraMap = {
        "Новинки": { start: "2023", end: "2025" },
        "2010-е": { start: "2010", end: "2019" },
        "2000-е": { start: "2000", end: "2009" },
        "90-е": { start: "1990", end: "1999" },
        "Ретро Классика": { start: "1940", end: "1989" },
        "Любое время": null,
        // English variants
        "New Releases": { start: "2023", end: "2025" },
        "2000s": { start: "2000", end: "2009" },
        "VHS Era (90s)": { start: "1990", end: "1999" },
        "Retro (80s)": { start: "1980", end: "1989" },
        "B&W Classic": { start: "1920", end: "1969" }
    };

    // Маппинг критериев на параметры сортировки
    const criteriaMap = {
        "Оскар": "vote_average.desc",
        "Хит проката": "popularity.desc",
        "Скрытый шедевр": "vote_average.desc",
        "Артхаус": "vote_average.desc",
        // English variants
        "Oscar Winners": "vote_average.desc",
        "Blockbuster": "popularity.desc",
        "Hidden Gem": "vote_average.desc",
        "Arthouse": "vote_average.desc"
    };

    const genreId = genreMap[genreName] || "";
    const period = eraMap[era];
    const sortBy = criteriaMap[criteria] || "popularity.desc";

    try {
        // ✅ ИСПРАВЛЕНО: Полный URL без "..."
        let url = `https://api.themoviedb.org/3/discover/movie?api_key=${config.tmdb.key}&language=en-US&sort_by=${sortBy}&include_adult=false&include_video=false&page=1`;

        // Добавляем жанр если указан
        if (genreId) {
            url += `&with_genres=${genreId}`;
        }

        // Добавляем временной диапазон
        if (period) {
            url += `&primary_release_date.gte=${period.start}-01-01`;
            url += `&primary_release_date.lte=${period.end}-12-31`;
        }

        // Для "Оскара" добавляем фильтр по рейтингу
        if (criteria === "Оскар" || criteria === "Oscar Winners") {
            url += `&vote_average.gte=7.5&vote_count.gte=1000`;
        }

        // Для "Скрытых шедевров" ищем высокий рейтинг + низкая популярность
        if (criteria === "Скрытый шедевр" || criteria === "Hidden Gem") {
            url += `&vote_average.gte=7.0&vote_count.gte=100&popularity.lte=50`;
        }

        console.log(`🎬 TMDB запрос: ${genreName} | ${era} | ${criteria}`);

        const response = await fetch(url);

        if (!response.ok) {
            throw new Error(`TMDB API Error: ${response.status} ${response.statusText}`);
        }

        const data = await response.json();

        if (!data.results || data.results.length === 0) {
            console.log("⚠️ TMDB: Фильмы не найдены");
            return [];
        }

        // Форматируем результаты
        const movies = data.results.map(m => ({
            id: m.id,
            title: m.title,
            year: m.release_date ? m.release_date.split('-')[0] : "—",
            rating: m.vote_average ? m.vote_average.toFixed(1) : "N/A",
            image: m.poster_path 
                ? `https://image.tmdb.org/t/p/w500${m.poster_path}` 
                : null,
            overview: m.overview || ""
        }));

        console.log(`✅ TMDB: Найдено ${movies.length} фильмов`);
        return movies;

    } catch (err) {
        console.error("❌ TMDB Error:", err.message);
        return [];
    }
}