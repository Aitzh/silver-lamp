// server.js - ИСПРАВЛЕННЫЙ ГЛАВНЫЙ СЕРВЕР Coffee Books AI
import express from "express";
import cookieParser from "cookie-parser";
import "dotenv/config";
import path from "path";
import { fileURLToPath } from "url";
import sqlite3 from "sqlite3";
import { promisify } from "util";
import crypto from "crypto";
import fs from "fs";

// Получаем __dirname для ES modules
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Конфигурация
const config = {
    port: process.env.PORT || 3000,
    googleBooks: { key: process.env.GOOGLE_BOOKS_API_KEY?.trim() },
    openRouter: { 
        key: process.env.OPENROUTER_API_KEY?.trim(),
        model: process.env.OPENROUTER_MODEL?.trim() || "tngtech/deepseek-r1t2-chimera:free"
    },
    tmdb: { key: process.env.TMDB_API_KEY?.trim() },
    spotify: {
        clientId: process.env.SPOTIFY_CLIENT_ID?.trim(),
        clientSecret: process.env.SPOTIFY_CLIENT_SECRET?.trim()
    }
};

const app = express();

// --- MIDDLEWARE ---
app.use(express.json());
app.use(cookieParser());

// --- DATABASE ---
const ACCESS_DB = process.env.ACCESS_DB_PATH || path.join(__dirname, "access.db");

// Проверяем/создаём БД
if (!fs.existsSync(ACCESS_DB)) {
    console.warn(`⚠️ База данных не найдена: ${ACCESS_DB}`);
    console.warn(`   Запустите: python setup_access_database.py`);
}

const db = new sqlite3.Database(ACCESS_DB, (err) => {
    if (err) {
        console.error('❌ Ошибка подключения к access.db:', err.message);
    } else {
        console.log('✅ Подключено к access.db');
    }
});

const dbAll = promisify(db.all.bind(db));
const dbGet = promisify(db.get.bind(db));
const dbRun = (...args) => new Promise((resolve, reject) => {
    db.run(...args, function(err) {
        if (err) reject(err);
        else resolve(this);
    });
});

// --- RATE LIMITING ---
const rateLimitStore = new Map();

function rateLimitMiddleware(maxAttempts, windowMs) {
    return (req, res, next) => {
        const ip = req.ip || req.connection.remoteAddress;
        const now = Date.now();
        
        // Очистка старых записей
        for (const [key, data] of rateLimitStore.entries()) {
            if (now - data.timestamp > windowMs) {
                rateLimitStore.delete(key);
            }
        }
        
        const key = `${ip}:${req.path}`;
        const attempts = rateLimitStore.get(key);
        
        if (!attempts) {
            rateLimitStore.set(key, { count: 1, timestamp: now });
            return next();
        }
        
        if (now - attempts.timestamp > windowMs) {
            rateLimitStore.set(key, { count: 1, timestamp: now });
            return next();
        }
        
        if (attempts.count >= maxAttempts) {
            return res.status(429).json({ 
                error: "Слишком много попыток. Подождите немного.",
                retryAfter: Math.ceil((windowMs - (now - attempts.timestamp)) / 1000)
            });
        }
        
        attempts.count++;
        next();
    };
}

// --- УТИЛИТЫ ---
function generateSessionToken() {
    return crypto.randomBytes(32).toString('hex');
}

async function logActivity(sessionToken, action, details, ipAddress) {
    try {
        await dbRun(`
            INSERT INTO activity_logs 
            (session_token, action, details, ip_address)
            VALUES (?, ?, ?, ?)
        `, [sessionToken, action, details, ipAddress]);
    } catch (err) {
        console.error('❌ Log error:', err);
    }
}

function formatTime(seconds) {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    
    if (hours > 24) {
        const days = Math.floor(hours / 24);
        return `${days} дн. ${hours % 24} ч.`;
    }
    if (hours > 0) {
        return `${hours} ч. ${minutes} мин.`;
    }
    return `${minutes} мин.`;
}

// --- СТАТИЧЕСКИЕ ФАЙЛЫ ---
// Публичные файлы (без авторизации)
app.get('/login.html', (req, res) => {
    res.sendFile(path.join(__dirname, 'frontend/public/login.html'));
});

app.get('/style.css', (req, res) => {
    res.sendFile(path.join(__dirname, 'frontend/public/style.css'));
});

app.get('/script.js', (req, res) => {
    res.sendFile(path.join(__dirname, 'frontend/public/script.js'));
});

// MineChess маршрут
app.get('/minechess', async (req, res) => {
    // Проверяем авторизацию для MineChess
    const sessionToken = req.cookies?.sessionToken || 
                        req.headers['x-session-token'] ||
                        req.query.token;
    
    if (!sessionToken) {
        return res.sendFile(path.join(__dirname, "frontend/public/login.html"));
    }
    
    try {
        const session = await dbGet(`
            SELECT * FROM user_sessions 
            WHERE session_token = ? 
            AND is_active = 1 
            AND expires_at > datetime('now')
        `, [sessionToken]);
        
        if (!session) {
            return res.sendFile(path.join(__dirname, "frontend/public/login.html"));
        }
        
        res.sendFile(path.join(__dirname, "frontend/public/minechess.html"));
        
    } catch (err) {
        console.error('❌ Ошибка проверки сессии:', err);
        res.sendFile(path.join(__dirname, "frontend/public/login.html"));
    }
});

// --- ГЛАВНАЯ СТРАНИЦА ---
// ИСПРАВЛЕНО: Проверяем токен из ЗАГОЛОВКА или QUERY, не только cookie
app.get("/", async (req, res) => {
    // Проверяем токен из разных источников
    const sessionToken = req.cookies?.sessionToken || 
                        req.headers['x-session-token'] ||
                        req.query.token;
    
    // Если нет токена - отдаём страницу входа напрямую (не редирект!)
    if (!sessionToken) {
        return res.sendFile(path.join(__dirname, "frontend/public/login.html"));
    }
    
    // Проверяем валидность токена
    try {
        const session = await dbGet(`
            SELECT * FROM user_sessions 
            WHERE session_token = ? 
            AND is_active = 1 
            AND expires_at > datetime('now')
        `, [sessionToken]);
        
        if (!session) {
            // Токен невалидный - показываем страницу входа
            return res.sendFile(path.join(__dirname, "frontend/public/login.html"));
        }
        
        // Токен валидный - показываем приложение
        res.sendFile(path.join(__dirname, "frontend/public/index.html"));
        
    } catch (err) {
        console.error('❌ Ошибка проверки сессии:', err);
        res.sendFile(path.join(__dirname, "frontend/public/login.html"));
    }
});

// ============================================================
// === API ДОСТУПА ===
// ============================================================

// Rate limit для проверки кодов
app.use("/access/verify", rateLimitMiddleware(10, 60000));

// POST /access/verify - Проверка кода доступа
app.post("/access/verify", async (req, res) => {
    try {
        const { code } = req.body;
        const ipAddress = req.ip || req.connection.remoteAddress;
        const userAgent = req.headers['user-agent'];
        
        if (!code || typeof code !== 'string') {
            return res.status(400).json({ 
                error: "Введите код доступа",
                success: false 
            });
        }
        
        const cleanCode = code.trim().toUpperCase();
        
        // Валидация формата
        if (!/^[A-Z0-9]{4}-[A-Z0-9]{4}$/.test(cleanCode)) {
            return res.status(400).json({ 
                error: "Неверный формат кода. Используйте: XXXX-XXXX",
                success: false 
            });
        }
        
        console.log(`🔍 Проверка кода: ${cleanCode} (IP: ${ipAddress})`);
        
        // Ищем код
        const accessCode = await dbGet(`
            SELECT * FROM access_codes 
            WHERE code = ? AND is_used = 0
        `, [cleanCode]);
        
        if (!accessCode) {
            await logActivity(null, 'code_verify_failed', cleanCode, ipAddress);
            
            // Проверяем использованный код
            const usedCode = await dbGet(`
                SELECT * FROM access_codes WHERE code = ? AND is_used = 1
            `, [cleanCode]);
            
            if (usedCode) {
                return res.status(401).json({ 
                    error: "Этот код уже был использован",
                    success: false 
                });
            }
            
            return res.status(401).json({ 
                error: "Код доступа не найден",
                success: false 
            });
        }
        
        // Проверяем срок действия
        if (accessCode.expires_at) {
            const now = new Date();
            const expiresAt = new Date(accessCode.expires_at);
            
            if (now > expiresAt) {
                await logActivity(null, 'code_expired', cleanCode, ipAddress);
                return res.status(401).json({ 
                    error: "Срок действия кода истёк",
                    success: false 
                });
            }
        }
        
        // Создаём сессию
        const sessionToken = generateSessionToken();
        const sessionDurationMs = accessCode.duration_hours * 60 * 60 * 1000;
        const sessionExpiresAt = new Date(Date.now() + sessionDurationMs);
        
        await dbRun(`
            INSERT INTO user_sessions 
            (session_token, access_code_id, ip_address, user_agent, expires_at)
            VALUES (?, ?, ?, ?, ?)
        `, [
            sessionToken,
            accessCode.id,
            ipAddress,
            userAgent,
            sessionExpiresAt.toISOString()
        ]);
        
        // Помечаем код использованным
        await dbRun(`
            UPDATE access_codes 
            SET is_used = 1, 
                used_at = CURRENT_TIMESTAMP,
                used_by_session = ?
            WHERE id = ?
        `, [sessionToken, accessCode.id]);
        
        await logActivity(sessionToken, 'code_verified', cleanCode, ipAddress);
        
        console.log(`✅ Код подтверждён. Сессия: ${sessionToken.slice(0, 8)}...`);
        
        // ВАЖНО: Устанавливаем cookie!
        res.cookie('sessionToken', sessionToken, {
            httpOnly: false, // Доступен для JS
            maxAge: sessionDurationMs,
            sameSite: 'lax'
        });
        
        res.json({
            success: true,
            sessionToken,
            expiresAt: sessionExpiresAt.toISOString(),
            duration: accessCode.duration_hours,
            codeType: accessCode.code_type
        });
        
    } catch (err) {
        console.error('❌ Verify error:', err);
        res.status(500).json({ 
            error: "Ошибка сервера",
            success: false 
        });
    }
});

// GET /access/status - Статус сессии
app.get("/access/status", async (req, res) => {
    try {
        const sessionToken = req.headers['x-session-token'] || 
                            req.cookies?.sessionToken;
        
        if (!sessionToken) {
            return res.json({ 
                authenticated: false,
                requiresAuth: true 
            });
        }
        
        const session = await dbGet(`
            SELECT 
                s.*,
                c.code_type,
                c.duration_hours
            FROM user_sessions s
            LEFT JOIN access_codes c ON s.access_code_id = c.id
            WHERE s.session_token = ?
        `, [sessionToken]);
        
        if (!session) {
            return res.json({ 
                authenticated: false,
                requiresAuth: true 
            });
        }
        
        const now = new Date();
        const expiresAt = new Date(session.expires_at);
        
        if (!session.is_active || now > expiresAt) {
            await dbRun(`
                UPDATE user_sessions 
                SET is_active = 0 
                WHERE session_token = ?
            `, [sessionToken]);
            
            return res.json({ 
                authenticated: false,
                expired: true,
                requiresAuth: true 
            });
        }
        
        const timeRemaining = Math.floor((expiresAt - now) / 1000);
        
        res.json({
            authenticated: true,
            sessionToken,
            expiresAt: session.expires_at,
            timeRemaining,
            timeRemainingFormatted: formatTime(timeRemaining),
            codeType: session.code_type
        });
        
    } catch (err) {
        console.error('❌ Status error:', err);
        res.status(500).json({ 
            error: "Ошибка сервера",
            authenticated: false 
        });
    }
});

// POST /access/logout - Выход
app.post("/access/logout", async (req, res) => {
    try {
        const sessionToken = req.headers['x-session-token'] || req.cookies?.sessionToken;
        
        if (sessionToken) {
            await dbRun(`
                UPDATE user_sessions 
                SET is_active = 0 
                WHERE session_token = ?
            `, [sessionToken]);
            
            await logActivity(sessionToken, 'logout', null, req.ip);
        }
        
        res.clearCookie('sessionToken');
        res.json({ success: true });
        
    } catch (err) {
        console.error('❌ Logout error:', err);
        res.status(500).json({ error: "Ошибка сервера" });
    }
});

// ============================================================
// === РЕКОМЕНДАЦИИ (импорт из отдельного файла) ===
// ============================================================

// Динамический импорт для recommend_db
let recommendRouter;
try {
    const module = await import('./backend/routes/recommend_db.js');
    recommendRouter = module.default;
    app.use("/recommend", recommendRouter);
    console.log('✅ Модуль recommend_db загружен');
} catch (err) {
    console.warn('⚠️ Модуль recommend_db не найден, используем встроенный');
    
    // Простой fallback
    app.post("/recommend/:type", (req, res) => {
        res.json({
            success: false,
            error: "Модуль рекомендаций не настроен"
        });
    });
}

// ============================================================
// === HEALTH CHECK ===
// ============================================================

app.get("/health", (req, res) => {
    res.json({ 
        status: "ok", 
        timestamp: new Date().toISOString(),
        uptime: process.uptime()
    });
});

// ============================================================
// === ОБРАБОТКА ОШИБОК ===
// ============================================================

app.use((err, req, res, next) => {
    console.error("💥 Server Error:", err);
    res.status(500).json({ error: "Internal server error" });
});

// 404 - отдаём страницу входа для HTML запросов
app.use((req, res) => {
    if (req.accepts('html')) {
        return res.sendFile(path.join(__dirname, "frontend/public/login.html"));
    }
    res.status(404).json({ error: "Not found" });
});

// ============================================================
// === ЗАПУСК ===
// ============================================================

const PORT = config.port;
app.listen(PORT, () => {
    console.log(`\n🚀 ═══════════════════════════════════════════`);
    console.log(`🚀 Coffee Books AI Server`);
    console.log(`🚀 ═══════════════════════════════════════════`);
    console.log(`📍 URL: http://localhost:${PORT}`);
    console.log(`🔒 Авторизация: АКТИВНА`);
    console.log(`\n📦 API статус:`);
    console.log(`   ${config.googleBooks.key ? '✅' : '❌'} Google Books`);
    console.log(`   ${config.tmdb.key ? '✅' : '❌'} TMDB`);
    console.log(`   ${config.spotify.clientId ? '✅' : '❌'} Spotify`);
    console.log(`   ${config.openRouter.key ? '✅' : '❌'} OpenRouter`);
    console.log(`\n🎯 Endpoints:`);
    console.log(`   GET  /              - Главная (с авторизацией)`);
    console.log(`   POST /access/verify - Проверка кода`);
    console.log(`   GET  /access/status - Статус сессии`);
    console.log(`   POST /access/logout - Выход`);
    console.log(`   POST /recommend/:type - Рекомендации`);
    console.log(`   GET  /health        - Health check`);
    console.log(`🚀 ═══════════════════════════════════════════\n`);
});

export { config };