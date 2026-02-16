import { Router } from "express";
import sqlite3 from "sqlite3";
import { promisify } from "util";
import crypto from "crypto";
import path from "path";
import { fileURLToPath } from "url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const router = Router();

const ACCESS_DB = process.env.ACCESS_DB_PATH || path.join(__dirname, "access.db");

const db = new sqlite3.Database(ACCESS_DB);
const dbGet = promisify(db.get.bind(db));
const dbAll = promisify(db.all.bind(db));
const dbRun = promisify(db.run.bind(db));

function generateSessionToken() {
    return crypto.randomBytes(32).toString("hex");
}

/* =======================================================
   VERIFY CODE
======================================================= */
router.post("/verify", async (req, res) => {
    try {
        const { code } = req.body;
        if (!code) {
            return res.status(400).json({ success: false, error: "Введите код" });
        }

        const cleanCode = code.trim().toUpperCase();

        const accessCode = await dbGet(`
            SELECT * FROM access_codes
            WHERE code = ?
        `, [cleanCode]);

        if (!accessCode) {
            return res.status(401).json({
                success: false,
                error: "Код не найден"
            });
        }

        // Проверка срока
        if (accessCode.expires_at) {
            if (new Date() > new Date(accessCode.expires_at)) {
                return res.status(401).json({
                    success: false,
                    error: "Срок действия кода истёк"
                });
            }
        }

        // Используем 1 как значение по умолчанию, если max_activations равен NULL
        const maxActs = accessCode.max_activations || 1;
        const currentActs = accessCode.current_activations || 0;

        if (currentActs >= maxActs) {
            return res.status(401).json({
                success: false,
                error: `Лимит активаций достигнут (${currentActs}/${maxActs})`
            });
        }

        // Создаём сессию
        const sessionToken = generateSessionToken();
        const durationMs = accessCode.duration_hours * 60 * 60 * 1000;
        const expiresAt = new Date(Date.now() + durationMs);

        await dbRun(`
            INSERT INTO user_sessions 
            (session_token, access_code_id, expires_at)
            VALUES (?, ?, ?)
        `, [sessionToken, accessCode.id, expiresAt.toISOString()]);

        // Увеличиваем активацию
        // После успешной проверки кода:
        // Увеличиваем активацию
            await dbRun(`
                UPDATE access_codes 
                SET current_activations = current_activations + 1,
                    -- Ставим 1, ТОЛЬКО если это была ПОСЛЕДНЯЯ возможная активация
                    is_used = CASE WHEN (current_activations + 1) >= COALESCE(max_activations, 1) THEN 1 ELSE 0 END,
                    used_at = CURRENT_TIMESTAMP
                WHERE id = ?
            `, [accessCode.id]);

    return res.json({
            success: true,
            sessionToken,
            expiresAt: expiresAt.toISOString(),
            // Используем переменные, которые точно числа
            remainingActivations: maxActs - (currentActs + 1)
    });
    } catch (err) {
        console.error(err);
        return res.status(500).json({
            success: false,
            error: "Ошибка сервера"
        });
    }
});

/* =======================================================
   SESSION STATUS
======================================================= */
router.get("/status", async (req, res) => {
    try {
        const token = req.headers["x-session-token"];
        if (!token) {
            return res.json({ authenticated: false });
        }

        const session = await dbGet(`
            SELECT * FROM user_sessions
            WHERE session_token = ?
        `, [token]);

        if (!session) {
            return res.json({ authenticated: false });
        }

        if (new Date() > new Date(session.expires_at)) {
            return res.json({ authenticated: false, expired: true });
        }

        return res.json({
            authenticated: true,
            expiresAt: session.expires_at
        });

    } catch (err) {
        console.error(err);
        return res.status(500).json({ authenticated: false });
    }
});

/* =======================================================
   ADMIN STATS (НОВАЯ ЛОГИКА)
======================================================= */
router.get("/admin/stats", async (req, res) => {
    try {
        const stats = await dbGet(`
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN current_activations >= max_activations THEN 1 ELSE 0 END) as exhausted,
                SUM(CASE WHEN current_activations < max_activations THEN 1 ELSE 0 END) as active
            FROM access_codes
        `);

        res.json(stats);

    } catch (err) {
        console.error(err);
        res.status(500).json({ error: "Ошибка сервера" });
    }
});

export default router;