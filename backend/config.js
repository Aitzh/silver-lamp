import "dotenv/config";

export const config = {
    port: process.env.PORT || 3000,
    
    googleBooks: {
        key: process.env.GOOGLE_BOOKS_API_KEY?.trim()
    },

    openRouter: {
        key: process.env.OPENROUTER_API_KEY?.trim(),
        model: process.env.OPENROUTER_MODEL?.trim() || "tngtech/deepseek-r1t2-chimera:free"
    },

    tmdb: {
        key: process.env.TMDB_API_KEY?.trim()
    },

    spotify: {
        clientId: process.env.SPOTIFY_CLIENT_ID?.trim(),
        clientSecret: process.env.SPOTIFY_CLIENT_SECRET?.trim()
    }
};

// Проверка наличия ключей при старте
const missingKeys = [];

if (!config.googleBooks.key) {
    missingKeys.push("GOOGLE_BOOKS_API_KEY");
}

if (!config.openRouter.key) {
    missingKeys.push("OPENROUTER_API_KEY");
}

if (!config.tmdb.key) {
    missingKeys.push("TMDB_API_KEY");
}

if (!config.spotify.clientId || !config.spotify.clientSecret) {
    missingKeys.push("SPOTIFY_CLIENT_ID or SPOTIFY_CLIENT_SECRET");
}

if (missingKeys.length > 0) {
    console.warn("⚠️ Отсутствуют API ключи в .env:");
    missingKeys.forEach(key => console.warn(`   - ${key}`));
    console.warn("Некоторые функции могут не работать!");
} else {
    console.log("✅ Все API ключи загружены");
}