/**
 * Умный кеш с TTL и автоочисткой
 */
class SmartCache {
    constructor(ttl = 600000) { // По умолчанию 10 минут
        this.cache = new Map();
        this.ttl = ttl;
        this.maxSize = 1000; // Максимум 1000 записей
        
        // Автоочистка каждые 5 минут
        this.cleanupInterval = setInterval(() => this.cleanup(), 300000);
    }

    /**
     * Сохранить значение в кеш
     */
    set(key, value) {
        // Если кеш переполнен — очищаем старые записи
        if (this.cache.size >= this.maxSize) {
            this.cleanup();
        }

        this.cache.set(key, {
            value,
            expires: Date.now() + this.ttl,
            hits: 0
        });
    }

    /**
     * Получить значение из кеша
     */
    get(key) {
        const item = this.cache.get(key);
        
        if (!item) return null;
        
        // Проверяем истек ли срок
        if (Date.now() > item.expires) {
            this.cache.delete(key);
            return null;
        }
        
        // Увеличиваем счетчик обращений (для аналитики)
        item.hits++;
        
        return item.value;
    }

    /**
     * Проверить наличие ключа
     */
    has(key) {
        return this.get(key) !== null;
    }

    /**
     * Удалить запись
     */
    delete(key) {
        return this.cache.delete(key);
    }

    /**
     * Очистить весь кеш
     */
    clear() {
        this.cache.clear();
        console.log("🧹 Кеш полностью очищен");
    }

    /**
     * Автоматическая очистка просроченных записей
     */
    cleanup() {
        const now = Date.now();
        let removed = 0;

        for (const [key, item] of this.cache.entries()) {
            if (now > item.expires) {
                this.cache.delete(key);
                removed++;
            }
        }

        if (removed > 0) {
            console.log(`🧹 Очищено ${removed} просроченных записей из кеша`);
        }
    }

    /**
     * Получить статистику кеша
     */
    getStats() {
        let totalHits = 0;
        let expiredCount = 0;
        const now = Date.now();

        for (const item of this.cache.values()) {
            totalHits += item.hits;
            if (now > item.expires) expiredCount++;
        }

        return {
            size: this.cache.size,
            maxSize: this.maxSize,
            totalHits,
            expiredCount,
            hitRate: totalHits / Math.max(this.cache.size, 1)
        };
    }

    /**
     * Остановить автоочистку (важно для graceful shutdown)
     */
    destroy() {
        clearInterval(this.cleanupInterval);
        this.clear();
    }
}

export const cache = new SmartCache(600000); // 10 минут TTL

// Graceful shutdown
process.on('SIGTERM', () => {
    console.log('♻️ Остановка кеша...');
    cache.destroy();
});