// server.js - ИСПРАВЛЕННЫЙ (Версия с поддержкой многоразовых кодов)
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
    console.warn(`   Создаю пустую базу...`);
}

const db = new sqlite3.Database(ACCESS_DB, async (err) => {
    if (err) {
        console.error('❌ Ошибка подключения к access.db:', err.message);
    } else {
        console.log('✅ Подключено к access.db');
        // АВТОМАТИЧЕСКАЯ МИГРАЦИЯ ПРИ ЗАПУСКЕ
        // Это чинит базу, если в ней нет колонок для многоразовости
        try {
            const run = promisify(db.run.bind(db));
            
            // Создаем таблицу, если нет
            await run(`
                CREATE TABLE IF NOT EXISTS access_codes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    code TEXT UNIQUE NOT NULL,
                    code_type TEXT NOT NULL CHECK(code_type IN ('1day', '7days', '30days')),
                    duration_hours INTEGER NOT NULL,
                    generated_by TEXT,
                    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_used INTEGER DEFAULT 0,
                    used_at TIMESTAMP,
                    used_by_session TEXT,
                    expires_at TIMESTAMP,
                    notes TEXT,
                    max_activations INTEGER DEFAULT 1,
                    current_activations INTEGER DEFAULT 0
                )
            `);

            // Добавляем колонки, если их нет (игнорируем ошибку, если есть)
            try { await run("ALTER TABLE access_codes ADD COLUMN max_activations INTEGER DEFAULT 1"); console.log("🔧 DB: Добавлена колонка max_activations"); } catch(e) {}
            try { await run("ALTER TABLE access_codes ADD COLUMN current_activations INTEGER DEFAULT 0"); console.log("🔧 DB: Добавлена колонка current_activations"); } catch(e) {}
            
            // Создаем остальные таблицы
            await run(`CREATE TABLE IF NOT EXISTS user_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_token TEXT UNIQUE NOT NULL,
                access_code_id INTEGER,
                ip_address TEXT,
                user_agent TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP NOT NULL,
                is_active INTEGER DEFAULT 1,
                last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                codes_generated_count INTEGER DEFAULT 0,
                FOREIGN KEY (access_code_id) REFERENCES access_codes(id)
            )`);
            
            await run(`CREATE TABLE IF NOT EXISTS activity_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_token TEXT,
                action TEXT NOT NULL,
                details TEXT,
                ip_address TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_token) REFERENCES user_sessions(session_token)
            )`);

        } catch (dbErr) {
            console.error("Ошибка авто-миграции:", dbErr);
        }
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
app.get("/", async (req, res) => {
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
        
        res.sendFile(path.join(__dirname, "frontend/public/index.html"));
        
    } catch (err) {
        console.error('❌ Ошибка проверки сессии:', err);
        res.sendFile(path.join(__dirname, "frontend/public/login.html"));
    }
});

// ============================================================
// === API ДОСТУПА ===
// ============================================================

app.use("/access/verify", rateLimitMiddleware(10, 60000));

// POST /access/verify - ИСПРАВЛЕННАЯ ВЕРСИЯ
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
        
        // 1. Ищем код (без проверки is_used=0, проверяем это вручную ниже)
        const accessCode = await dbGet(`
            SELECT * FROM access_codes WHERE code = ?
        `, [cleanCode]);
        
        if (!accessCode) {
            await logActivity(null, 'code_verify_failed', cleanCode, ipAddress);
            return res.status(401).json({ 
                error: "Код доступа не найден",
                success: false 
            });
        }

        // 2. Логика многоразовости
        const maxActs = accessCode.max_activations || 1; // Если NULL, то 1
        const currentActs = accessCode.current_activations || 0;

        // Если код помечен как использованный И количество активаций достигло лимита
        if (accessCode.is_used === 1 && currentActs >= maxActs) {
             await logActivity(null, 'code_exhausted', cleanCode, ipAddress);
             return res.status(401).json({ 
                error: `Лимит активаций достигнут (${currentActs}/${maxActs})`,
                success: false 
            });
        }
        
        // 3. Проверяем срок действия
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
        
        // 4. Создаём сессию
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
        
        // 5. Обновляем статус кода (Счетчик +1)
        // is_used ставим в 1 ТОЛЬКО если это была последняя активация
        await dbRun(`
            UPDATE access_codes 
            SET current_activations = current_activations + 1,
                is_used = CASE WHEN (current_activations + 1) >= ? THEN 1 ELSE 0 END,
                used_at = CURRENT_TIMESTAMP,
                used_by_session = ?
            WHERE id = ?
        `, [maxActs, sessionToken, accessCode.id]);
        
        await logActivity(sessionToken, 'code_verified', cleanCode, ipAddress);
        
        console.log(`✅ Код подтверждён (${currentActs + 1}/${maxActs}). Сессия: ${sessionToken.slice(0, 8)}...`);
        
        // Cookie
        res.cookie('sessionToken', sessionToken, {
            httpOnly: false,
            maxAge: sessionDurationMs,
            sameSite: 'lax'
        });
        
        res.json({
            success: true,
            sessionToken,
            expiresAt: sessionExpiresAt.toISOString(),
            duration: accessCode.duration_hours,
            codeType: accessCode.code_type,
            remainingActivations: maxActs - (currentActs + 1)
        });
        
    } catch (err) {
        console.error('❌ Verify error:', err);
        res.status(500).json({ 
            error: "Ошибка сервера",
            success: false 
        });
    }
});

// GET /access/status
app.get("/access/status", async (req, res) => {
    try {
        const sessionToken = req.headers['x-session-token'] || 
                            req.cookies?.sessionToken;
        
        if (!sessionToken) {
            return res.json({ authenticated: false, requiresAuth: true });
        }
        
        const session = await dbGet(`
            SELECT s.*, c.code_type, c.duration_hours
            FROM user_sessions s
            LEFT JOIN access_codes c ON s.access_code_id = c.id
            WHERE s.session_token = ?
        `, [sessionToken]);
        
        if (!session) {
            return res.json({ authenticated: false, requiresAuth: true });
        }
        
        const now = new Date();
        const expiresAt = new Date(session.expires_at);
        
        if (!session.is_active || now > expiresAt) {
            await dbRun(`UPDATE user_sessions SET is_active = 0 WHERE session_token = ?`, [sessionToken]);
            return res.json({ authenticated: false, expired: true, requiresAuth: true });
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
        res.status(500).json({ error: "Ошибка сервера", authenticated: false });
    }
});

// POST /access/logout
app.post("/access/logout", async (req, res) => {
    try {
        const sessionToken = req.headers['x-session-token'] || req.cookies?.sessionToken;
        
        if (sessionToken) {
            await dbRun(`UPDATE user_sessions SET is_active = 0 WHERE session_token = ?`, [sessionToken]);
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
// === РЕКОМЕНДАЦИИ ===
// ============================================================

let recommendRouter;
try {
    const module = await import('./backend/routes/recommend_db.js');
    recommendRouter = module.default;
    app.use("/recommend", recommendRouter);
    console.log('✅ Модуль recommend_db загружен');
} catch (err) {
    console.warn('⚠️ Модуль recommend_db не найден, используем встроенный');
    app.post("/recommend/:type", (req, res) => {
        res.json({ success: false, error: "Модуль рекомендаций не настроен" });
    });
}

// ============================================================
// === ЗАПУСК ===
// ============================================================

app.get("/health", (req, res) => res.json({ status: "ok", timestamp: new Date().toISOString() }));

app.use((err, req, res, next) => {
    console.error("💥 Server Error:", err);
    res.status(500).json({ error: "Internal server error" });
});

app.use((req, res) => {
    if (req.accepts('html')) return res.sendFile(path.join(__dirname, "frontend/public/login.html"));
    res.status(404).json({ error: "Not found" });
});

const PORT = config.port;
app.listen(PORT, () => {
    console.log(`\n🚀 Coffee Books AI Server запущен на порту ${PORT}`);
    console.log(`🔒 Система авторизации обновлена (Многоразовые коды активны)`);
});

export { config };