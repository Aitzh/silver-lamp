import fetch from "node-fetch";

export async function searchBooks(genre, era, startIndex = 0) {
    // 1. Маппинг жанров на английский для точности поиска
    const genreMap = {
        "Фэнтези": "Fantasy",
        "Научная фантастика": "Science Fiction",
        "Детектив": "Mystery",
        "Триллер": "Thriller",
        "Классика": "Classics",
        "Нон-фикшн": "Non-fiction",
        "Роман": "Romance",
        "Приключения": "Adventure"
    };

    // 2. Маппинг эпох
    const eraMap = {
        "Золотая Классика": "classic literature",
        "80-е годы": "1980s",
        "90-е годы": "1990s",
        "2010-е": "2010s",
        "Бестселлеры 2025": "2024 2025 bestseller"
    };

    const searchGenre = genreMap[genre] || genre;
    const searchEra = eraMap[era] || era;

    try {
        // Поиск выполняется на английском (subject + ключевые слова)
        const query = `subject:${searchGenre} ${searchEra}`;
        const url = `https://www.googleapis.com/books/v1/volumes?q=${encodeURIComponent(query)}&startIndex=${startIndex}&maxResults=30&printType=books`;

        const res = await fetch(url);
        const data = await res.json();

        if (!data.items) return [];

        return data.items.map(item => ({
            id: item.id,
            title: item.volumeInfo.title,
            authors: item.volumeInfo.authors?.join(", ") || "Unknown Author",
            image: item.volumeInfo.imageLinks?.thumbnail?.replace('http:', 'https:'),
            description: item.volumeInfo.description || ""
        }));
    } catch (err) {
        console.error("Google Books Error:", err);
        return [];
    }
}