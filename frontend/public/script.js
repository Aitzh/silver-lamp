/* --- COFFEE BOOKS AI - Frontend Script (FIXED) --- */

/* --- 1. CONFIG & STATE --- */
let currentLang = localStorage.getItem('currentLang') || 'ru';  
let currentCategory = 'books';
let isAuthenticated = false;

/* --- 2. DATABASE (АКТУАЛЬНЫЕ ДАННЫЕ ИЗ БД) --- */
const database = {
    ru: {
        nav: { books: "Книги", movies: "Фильмы", music: "Музыка" },
        static: {
            subtitle: "Умная рекомендация на основе ваших предпочтений",
            coffeeLabel: "ВАШ НАПИТОК",
            btnText: "Подобрать коллекцию",
            footer: '',
            loading: "Подбираем идеальную коллекцию...",
            emptyTitle: "Ничего не найдено",
            emptyText: "Попробуйте изменить фильтры или напиток",
            errorTitle: "Упс! Что-то пошло не так",
            errorText: "Попробуйте еще раз через несколько секунд",
            sessionExpired: "Сессия истекла. Войдите снова.",
            authRequired: "Требуется авторизация"
        },
        data: {
            books: [
                { 
                    title: "ЖАНР", 
                    type: "single", 
                    items: ["Фэнтези", "Научная фантастика", "Детектив", "Триллер", "Классика", "Нон-фикшн", "Роман", "Приключения", "Исторический", "Философия", "Психология", "Антиутопия"] 
                },
                { 
                    title: "ЭПОХА", 
                    type: "single", 
                    items: ["Бестселлеры 2025", "2020-е", "2010-е", "2000-е", "90-е", "80-е", "Золотая Классика", "Ретро"] 
                },
                { 
                    title: "КРИТЕРИЙ", 
                    type: "single", 
                    items: ["Бестселлер", "Классика", "Культовая", "Скрытый шедевр", "Интеллектуальная", "Современная", "Популярная"] 
                }
            ],
            movies: [
                { 
                    title: "ЖАНР", 
                    type: "single", 
                    items: ["Драма", "Комедия", "Ужасы", "Фантастика", "Боевик", "Триллер", "Анимация", "Документальный", "Криминал", "Приключения", "Семейный", "Фэнтези", "История", "Музыкальный", "Детектив", "Романтика", "Военный", "Вестерн"] 
                },
                { 
                    title: "ЭПОХА", 
                    type: "single", 
                    items: ["Новинки", "2010-е", "2000-е", "90-е", "Ретро"] 
                },
                { 
                    title: "КРИТЕРИЙ", 
                    type: "single", 
                    items: ["Оскар", "Высокий рейтинг", "Скрытый шедевр", "Популярный"] 
                }
            ],
            music: [
                { 
                    title: "ЖАНР", 
                    type: "single", 
                    items: ["Поп", "Рок", "Классическая", "Джаз", "Хип-хоп", "Техно", "Инди", "Метал", "Блюз", "Кантри", "R&B", "Латиноамериканская"] 
                },
                { 
                    title: "НАСТРОЕНИЕ", 
                    type: "single", 
                    items: ["Энергия", "Чилл", "Вечеринка", "Фокус"] 
                },
                { 
                    title: "КРИТЕРИЙ", 
                    type: "single", 
                    items: ["Хит", "Популярная", "Восходящая звезда", "Андеграунд"] 
                }
            ]
        }
    },
    en: {
        nav: { books: "Books", movies: "Movies", music: "Music" },
        static: {
            subtitle: "Smart recommendations based on your preferences",
            coffeeLabel: "YOUR DRINK",
            btnText: "Curate Collection",
            footer: "",
            loading: "Curating your perfect collection...",
            emptyTitle: "Nothing Found",
            emptyText: "Try adjusting your filters or coffee choice",
            errorTitle: "Oops! Something went wrong",
            errorText: "Please try again in a few seconds",
            sessionExpired: "Session expired. Please log in again.",
            authRequired: "Authorization required"
        },
        data: {
            books: [
                { 
                    title: "GENRE", 
                    type: "single", 
                    items: ["Fantasy", "Sci-Fi", "Mystery", "Thriller", "Classics", "Non-fiction", "Romance", "Adventure", "Historical", "Philosophy", "Psychology", "Dystopian"] 
                },
                { 
                    title: "ERA", 
                    type: "single", 
                    items: ["Bestsellers 2025", "2020s", "2010s", "2000s", "90s", "80s", "Golden Classics", "Retro"] 
                },
                { 
                    title: "CRITERIA", 
                    type: "single", 
                    items: ["Bestseller", "Classic", "Cult", "Hidden Gem", "Intellectual", "Modern", "Popular"] 
                }
            ],
            movies: [
                { 
                    title: "GENRE", 
                    type: "single", 
                    items: ["Drama", "Comedy", "Horror", "Sci-Fi", "Action", "Thriller", "Animation", "Documentary", "Crime", "Adventure", "Family", "Fantasy", "History", "Music", "Mystery", "Romance", "War", "Western"] 
                },
                { 
                    title: "ERA", 
                    type: "single", 
                    items: ["New Releases", "2010s", "2000s", "90s", "Retro"] 
                },
                { 
                    title: "CRITERIA", 
                    type: "single", 
                    items: ["Oscar", "High Rated", "Hidden Gem", "Popular"] 
                }
            ],
            music: [
                { 
                    title: "GENRE", 
                    type: "single", 
                    items: ["Pop", "Rock", "Classical", "Jazz", "Hip-Hop", "Electronic", "Indie", "Metal", "Blues", "Country", "R&B", "Latin"] 
                },
                { 
                    title: "VIBE", 
                    type: "single", 
                    items: ["Energetic", "Chill", "Party", "Focus"] 
                },
                { 
                    title: "CRITERIA", 
                    type: "single", 
                    items: ["Hit", "Popular", "Rising Star", "Underground"] 
                }
            ]
        }
    },
    kz: {
        nav: { books: "Кітаптар", movies: "Фильмдер", music: "Музыка" },
        static: {
            subtitle: "Сіздің қалауыңызға негізделген ақылды ұсыныстар",
            coffeeLabel: "СІЗДІҢ ТАҢДАУ",
            btnText: "Жинақ құру",
            footer: "",
            loading: "Сізге арналған жинақ жасалуда...",
            emptyTitle: "Ештеңе табылмады",
            emptyText: "Фильтрлерді немесе сусынды өзгертіп көріңіз",
            errorTitle: "Қате орын алды",
            errorText: "Бірнеше секундтан кейін қайталап көріңіз",
            sessionExpired: "Сессия аяқталды. Қайта кіріңіз.",
            authRequired: "Авторизация қажет"
        },
        data: {
            books: [
                { 
                    title: "ЖАНР", 
                    type: "single", 
                    items: ["Фэнтези", "Ғылыми фантастика", "Детектив", "Триллер", "Классика", "Нон-фикшн", "Роман", "Шытырман", "Тарихи", "Философия", "Психология", "Антиутопия"] 
                },
                { 
                    title: "ДӘУІР", 
                    type: "single", 
                    items: ["Бестселлерлер 2025", "2020-шы", "2010-шы", "2000-шы", "90-шы", "80-ші", "Алтын классика", "Ретро"] 
                },
                { 
                    title: "КРИТЕРИЙ", 
                    type: "single", 
                    items: ["Бестселлер", "Классика", "Культтық", "Жасырын шедевр", "Интеллектуалды", "Заманауи", "Танымал"] 
                }
            ],
            movies: [
                { 
                    title: "ЖАНР", 
                    type: "single", 
                    items: ["Драма", "Комедия", "Қорқынышты", "Фантастика", "Боевик", "Триллер", "Анимация", "Деректі", "Криминал", "Шытырман", "Отбасылық", "Фэнтези", "Тарихи", "Музыкалық", "Детектив", "Романтика", "Соғыс", "Вестерн"] 
                },
                { 
                    title: "ДӘУІР", 
                    type: "single", 
                    items: ["Жаңалықтар", "2010-шы", "2000-шы", "90-шы", "Ретро"] 
                },
                { 
                    title: "КРИТЕРИЙ", 
                    type: "single", 
                    items: ["Оскар", "Жоғары рейтинг", "Жасырын шедевр", "Танымал"] 
                }
            ],
            music: [
                { 
                    title: "ЖАНР", 
                    type: "single", 
                    items: ["Поп", "Рок", "Классикалық", "Джаз", "Хип-хоп", "Электронды", "Инди", "Метал", "Блюз", "Кантри", "R&B", "Латын"] 
                },
                { 
                    title: "КӨҢІЛ-КҮЙ", 
                    type: "single", 
                    items: ["Энергия", "Демалыс", "Мереке", "Фокус"] 
                },
                { 
                    title: "КРИТЕРИЙ", 
                    type: "single", 
                    items: ["Хит", "Танымал", "Көтерілуші жұлдыз", "Андеграунд"] 
                }
            ]
        }
    }
};

/* --- 3. AUTH FUNCTIONS (НОВОЕ!) --- */

/**
 * Получить токен сессии из localStorage
 */
function getSessionToken() {
    return localStorage.getItem('sessionToken');
}

/**
 * Проверка авторизации при загрузке страницы
 */
async function checkAuth() {
    const sessionToken = getSessionToken();
    
    if (!sessionToken) {
        console.log('🔒 Нет токена сессии, редирект на вход');
        redirectToLogin();
        return false;
    }
    
    try {
        const response = await fetch('/access/status', {
            headers: { 
                'X-Session-Token': sessionToken 
            }
        });
        
        const data = await response.json();
        
        if (!data.authenticated) {
            console.log('🔒 Сессия недействительна:', data);
            clearSession();
            redirectToLogin();
            return false;
        }
        
        console.log('✅ Авторизация подтверждена. Осталось:', data.timeRemainingFormatted);
        isAuthenticated = true;
        
        // Показываем время до окончания сессии (опционально)
        showSessionInfo(data);
        
        return true;
        
    } catch (err) {
        console.error('❌ Ошибка проверки авторизации:', err);
        // При ошибке сети не разлогиниваем - может быть временная проблема
        return true; // Позволяем продолжить, API проверит токен
    }
}

/**
 * Очистка данных сессии
 */
function clearSession() {
    localStorage.removeItem('sessionToken');
    localStorage.removeItem('sessionExpiresAt');
    isAuthenticated = false;
}

/**
 * Редирект на страницу входа
 */
function redirectToLogin() {
    window.location.href = '/login.html';
}

/**
 * Показать информацию о сессии (опционально)
 */
function showSessionInfo(data) {
    const attemptsText = document.getElementById('attempts-text');
    if (attemptsText && data.timeRemainingFormatted) {
        // attemptsText.innerText = `Сессия активна: ${data.timeRemainingFormatted}`;
    }
}

/**
 * Обработка 401 ошибки
 */
function handleAuthError() {
    const langData = database[currentLang];
    clearSession();
    showError(langData.static.sessionExpired, langData.static.authRequired);
    
    // Редирект через 2 секунды
    setTimeout(redirectToLogin, 2000);
}

/**
 * Выход из системы
 */
async function logout() {
    const sessionToken = getSessionToken();
    
    if (sessionToken) {
        try {
            await fetch('/access/logout', {
                method: 'POST',
                headers: {
                    'X-Session-Token': sessionToken
                }
            });
        } catch (err) {
            console.error('Ошибка при выходе:', err);
        }
    }
    
    clearSession();
    redirectToLogin();
}

/* --- 4. CORE FUNCTIONS --- */
async function init() {
    // СНАЧАЛА проверяем авторизацию!
    const isAuthed = await checkAuth();
    if (!isAuthed) return;
    const savedTheme = localStorage.getItem('theme') || 'light';
    document.body.setAttribute('data-theme', savedTheme);
    const savedLang = localStorage.getItem('currentLang') || 'ru';
    currentLang = savedLang;
    document.querySelectorAll('.lang-btn').forEach(btn => {
        btn.classList.remove('active');
        if (btn.getAttribute('data-lang') === savedLang) {
            btn.classList.add('active');
        }
    });
    // Если авторизованы - инициализируем интерфейс
    lucide.createIcons();
    updateInterface();
    checkServerHealth();
}

function updateInterface() {
    const langData = database[currentLang];
    document.getElementById('subtitle').innerText = langData.static.subtitle;
    document.getElementById('coffee-label').innerText = langData.static.coffeeLabel;
    document.getElementById('btn-text').innerText = langData.static.btnText;
    document.getElementById('attempts-text').innerText = langData.static.footer;

    const navSpans = document.querySelectorAll('.nav-item span');
    navSpans.forEach(span => {
        const key = span.getAttribute('data-key');
        if (langData.nav[key]) {
            span.innerText = langData.nav[key];
        }
    });
    renderFilters();
}

function renderFilters() {
    const container = document.getElementById('dynamic-filters');
    container.innerHTML = ''; 
    const sections = database[currentLang].data[currentCategory];
    const VISIBLE_LIMIT = 5; // Сколько чипов показывать сразу
    
    sections.forEach(section => {
        const group = document.createElement('div');
        group.className = 'filter-group';
        const header = document.createElement('div');
        header.className = 'section-header';
        header.innerHTML = `<span class="header-title">${section.title}</span>`;
        const row = document.createElement('div');
        row.className = 'chips-row';

        const chips = [];
        
        section.items.forEach((item, idx) => {
            const chip = document.createElement('button');
            const isMulti = section.type === 'multi';
            const isActive = !isMulti && idx === 0; 
            chip.className = `chip ${isMulti ? 'multi' : ''} ${isActive ? 'active' : ''}`;
            chip.innerText = item;
            chip.setAttribute('role', 'button');
            chip.setAttribute('aria-pressed', isActive);
            chip.setAttribute('tabindex', '0');
            
            // Скрываем чипы после лимита
            if (idx >= VISIBLE_LIMIT) {
                chip.style.display = 'none';
                chip.dataset.hidden = 'true';
            }

            chip.onclick = () => {
                if (isMulti) {
                    chip.classList.toggle('active');
                    chip.setAttribute('aria-pressed', chip.classList.contains('active'));
                } else {
                    row.querySelectorAll('.chip').forEach(c => {
                        c.classList.remove('active');
                        c.setAttribute('aria-pressed', 'false');
                    });
                    chip.classList.add('active');
                    chip.setAttribute('aria-pressed', 'true');
                }
            };
            
            chip.onkeypress = (e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    chip.click();
                }
            };
            
            row.appendChild(chip);
            chips.push(chip);
        });

        // Кнопка "Ещё" если чипов больше лимита
        if (section.items.length > VISIBLE_LIMIT) {
            const hiddenCount = section.items.length - VISIBLE_LIMIT;
            const moreBtn = document.createElement('button');
            moreBtn.className = 'chips-more-btn';
            moreBtn.innerHTML = `<span class="more-label">+ ещё ${hiddenCount}</span>`;
            moreBtn.setAttribute('aria-expanded', 'false');

            moreBtn.onclick = () => {
                const isExpanded = moreBtn.classList.contains('expanded');
                if (!isExpanded) {
                    // Показываем все
                    chips.forEach(c => { if (c.dataset.hidden) c.style.display = ''; });
                    moreBtn.innerHTML = `<span class="more-label">Скрыть</span>`;
                    moreBtn.classList.add('expanded');
                    moreBtn.setAttribute('aria-expanded', 'true');
                } else {
                    // Скрываем снова
                    chips.forEach((c, i) => {
                        if (i >= VISIBLE_LIMIT) {
                            c.style.display = 'none';
                            // Если активный скрытый — активируем первый
                            if (c.classList.contains('active') && section.type !== 'multi') {
                                chips[0].classList.add('active');
                            }
                        }
                    });
                    moreBtn.innerHTML = `<span class="more-label">+ ещё ${hiddenCount}</span>`;
                    moreBtn.classList.remove('expanded');
                    moreBtn.setAttribute('aria-expanded', 'false');
                }
            };

            row.appendChild(moreBtn);
        }

        group.appendChild(header);
        group.appendChild(row);
        container.appendChild(group);
    });
}

/* --- 5. EVENT HANDLERS --- */
function setLang(lang) {
    currentLang = lang;
    localStorage.setItem('currentLang', lang);
    document.querySelectorAll('.lang-btn').forEach(btn => {
        btn.classList.remove('active');
        if (btn.getAttribute('data-lang') === lang) {
            btn.classList.add('active');
        }
    });
    updateInterface();
}

function switchCategory(cat, el) {
    currentCategory = cat;
    document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
    el.classList.add('active');
    renderFilters();
    document.getElementById('results').innerHTML = '';
}

function selectCoffee(el) {
    document.querySelectorAll('.coffee-card').forEach(c => c.classList.remove('active'));
    el.classList.add('active');
}

function toggleTheme() {
    const body = document.body;
    const isDark = body.getAttribute('data-theme') === 'dark';
    const newTheme = isDark ? 'light' : 'dark';
    body.setAttribute('data-theme', newTheme);
    localStorage.setItem('theme', newTheme); // Сохраняем тему
    lucide.createIcons();
}

function getSelectedFilters() {
    const filters = {};
    document.querySelectorAll('.filter-group').forEach(group => {
        const title = group.querySelector('.header-title').innerText.trim();
        const activeChip = group.querySelector('.chip.active');
        if (activeChip) {
            filters[title] = activeChip.innerText;
        }
    });
    return filters;
}

/* --- 6. API INTERACTION --- */

// ====== ИСТОРИЯ ПРОСМОТРОВ ======
function getHistory() {
    try {
        const history = JSON.parse(localStorage.getItem('coffee_ai_history') || '{}');
        return history[currentCategory] || [];
    } catch (e) {
        console.error('Ошибка чтения истории:', e);
        return [];
    }
}

function saveToHistory(items) {
    try {
        const history = JSON.parse(localStorage.getItem('coffee_ai_history') || '{}');
        
        if (!history[currentCategory]) {
            history[currentCategory] = [];
        }
        
        items.forEach(item => {
            if (item.id && !history[currentCategory].includes(item.id)) {
                history[currentCategory].push(item.id);
            }
        });
        
        // Оставляем только последние 200
        history[currentCategory] = history[currentCategory].slice(-200);
        
        localStorage.setItem('coffee_ai_history', JSON.stringify(history));
        
        console.log(`💾 История сохранена: ${history[currentCategory].length} элементов для ${currentCategory}`);
    } catch (e) {
        console.error('Ошибка сохранения истории:', e);
    }
}

function clearOldHistory() {
    try {
        const history = JSON.parse(localStorage.getItem('coffee_ai_history') || '{}');
        
        if (history[currentCategory] && history[currentCategory].length > 100) {
            console.log('🧹 Частично очищаю историю (оставляю последние 50)');
            history[currentCategory] = history[currentCategory].slice(-50);
            localStorage.setItem('coffee_ai_history', JSON.stringify(history));
        }
    } catch (e) {
        console.error('Ошибка очистки истории:', e);
    }
}

async function checkServerHealth() {
    try {
        const response = await fetch('/health');
        const data = await response.json();
        console.log('✅ Сервер работает:', data);
    } catch (err) {
        console.error('❌ Сервер недоступен:', err);
        showError('Сервер недоступен. Проверьте подключение.');
    }
}

document.getElementById('main-btn').onclick = async function() {
    const btn = this;
    const resultsContainer = document.getElementById('results');
    const langData = database[currentLang];

    btn.classList.add('loading');
    btn.disabled = true;
    
    showLoading();
    resultsContainer.innerHTML = '';

    try {
        const selectedFilters = getSelectedFilters();
        const selectedCoffee = document.querySelector('.coffee-card.active span')?.innerText || 'Espresso';

        // === ПОЛУЧАЕМ ИСТОРИЮ ===
        const historyIds = getHistory();
        console.log(`📜 История: ${historyIds.length} элементов`);

        // === ПОЛУЧАЕМ ТОКЕН СЕССИИ ===
        const sessionToken = getSessionToken();

        console.log('📤 Отправка запроса:', { category: currentCategory, filters: selectedFilters, lang: currentLang, excludeIds: historyIds.length });

        const response = await fetch(`/recommend/${currentCategory}`, {
            method: 'POST',
            headers: { 
                'Content-Type': 'application/json',
                'X-Session-Token': sessionToken  // ДОБАВЛЕНО! Передаём токен
            },
            body: JSON.stringify({
                coffee: selectedCoffee,
                filters: selectedFilters,
                excludeIds: historyIds,
                lang: currentLang
            })
        });

        // === ПРОВЕРКА АВТОРИЗАЦИИ ===
        if (response.status === 401) {
            handleAuthError();
            return;
        }

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || `Server error: ${response.status}`);
        }

        console.log('📥 Получен ответ:', data);

        if (!data.recommendations || data.recommendations.length === 0) {
            // Если ничего не найдено И история большая - очищаем
            if (historyIds.length > 50) {
                clearOldHistory();
                showEmptyState(
                    langData.static.emptyTitle, 
                    'История очищена. Попробуйте ещё раз!'
                );
            } else {
                showEmptyState(langData.static.emptyTitle, langData.static.emptyText);
            }
            return;
        }

        // === СОХРАНЯЕМ В ИСТОРИЮ ===
        saveToHistory(data.recommendations);

        displayResults(data);

        setTimeout(() => {
            resultsContainer.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }, 300);

    } catch (err) {
        console.error('❌ Ошибка:', err);
        showError(langData.static.errorTitle, err.message || langData.static.errorText);
    } finally {
        btn.classList.remove('loading');
        btn.disabled = false;
        hideLoading();
    }
};

/* --- 7. UI RENDERING --- */
function displayResults(data) {
    const container = document.getElementById('results');
    if (!container) return;

    const items = data.recommendations || [];
    container.innerHTML = '';
    
    items.forEach((item, index) => {
        const card = document.createElement('div');
        card.className = 'result-card-premium';
        card.style.animationDelay = `${index * 0.1}s`;
        
        card.innerHTML = `
            <div class="result-img-wrapper">
                <img src="${item.image || 'https://via.placeholder.com/180x260?text=No+Image'}" 
                     alt="${item.title}"
                     onerror="this.src='https://via.placeholder.com/180x260?text=No+Image'">
                ${item.rating ? `<div class="rating-badge">★ ${item.rating}</div>` : ''}
            </div>
            <div class="result-info">
                <h3>${escapeHtml(item.title)}</h3>
                ${item.author ? `<p class="result-meta">${escapeHtml(item.author)}</p>` : ''}
                ${item.artist ? `<p class="result-meta">${escapeHtml(item.artist)}</p>` : ''}
                ${item.year && !item.artist ? `<p class="result-meta">${item.year}</p>` : ''}
                <p class="result-description">${escapeHtml(item.why || item.description || '')}</p>
            </div>
        `;
        container.appendChild(card);
    });

    lucide.createIcons();
}

function showLoading() {
    const langData = database[currentLang];
    const message = langData.static.loading;
    
    let loadingDiv = document.getElementById('loading');
    if (!loadingDiv) {
        loadingDiv = document.createElement('div');
        loadingDiv.id = 'loading';
        loadingDiv.innerHTML = `
            <div class="loading-spinner"></div>
            <p class="loading-text">${message}</p>
        `;
        document.body.appendChild(loadingDiv);
    } else {
        const textEl = loadingDiv.querySelector('.loading-text');
        if (textEl) {
            textEl.textContent = message;
        }
    }
    loadingDiv.classList.remove('hidden');
}

function hideLoading() {
    const loadingDiv = document.getElementById('loading');
    if (loadingDiv) {
        loadingDiv.classList.add('hidden');
    }
}

function showEmptyState(title, text) {
    const container = document.getElementById('results');
    container.innerHTML = `
        <div class="empty-state">
            <i data-lucide="inbox" size="64"></i>
            <h3>${title}</h3>
            <p>${text}</p>
        </div>
    `;
    lucide.createIcons();
}

function showError(title, message) {
    const container = document.getElementById('results');
    container.innerHTML = `
        <div class="error-state">
            <i data-lucide="alert-circle" size="64"></i>
            <h3>${title}</h3>
            <p>${message || 'Попробуйте еще раз'}</p>
        </div>
    `;
    lucide.createIcons();
}

/* --- 8. UTILS --- */
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Делаем функции глобальными для onclick в HTML
window.setLang = setLang;
window.switchCategory = switchCategory;
window.selectCoffee = selectCoffee;
window.toggleTheme = toggleTheme;
window.logout = logout;

document.addEventListener('DOMContentLoaded', init);