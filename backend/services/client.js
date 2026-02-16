import fetch from "node-fetch";
import { config } from "../config.js";

/**
 * Обертка для вызова OpenRouter API с retry логикой
 * @param {string} prompt - Промпт для ИИ
 * @param {boolean} isJson - Ожидается ли JSON ответ
 * @param {number} maxRetries - Количество попыток при ошибке
 * @returns {Promise<string>} - Ответ от ИИ
 */
export async function callAI(prompt, isJson = true, maxRetries = 2) {
    const apiUrl = "https://openrouter.ai/api/v1/chat/completions";
    
    // Инструкция для JSON формата
    const jsonInstruction = isJson 
        ? "\n\nCRITICAL: Return ONLY a valid JSON array. No markdown code blocks (```), no explanations, no preamble. Just pure JSON starting with [ and ending with ]." 
        : "";

    const fullPrompt = prompt + jsonInstruction;

    // Функция для одной попытки запроса
    async function attemptRequest(retryCount = 0) {
        try {
            console.log(`🤖 OpenRouter запрос (попытка ${retryCount + 1}/${maxRetries + 1})`);

            const response = await fetch(apiUrl, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "Authorization": `Bearer ${config.openRouter.key}`,
                    "HTTP-Referer": process.env.APP_URL || "http://localhost:3000",
                    "X-Title": "Coffee & AI"
                },
                body: JSON.stringify({
                    model: config.openRouter.model,
                    messages: [
                        {
                            role: "system",
                            content: "You are a helpful assistant that provides recommendations. Always follow the output format specified in the user's request."
                        },
                        {
                            role: "user",
                            content: fullPrompt
                        }
                    ],
                    temperature: 0.3, // Низкая для стабильного JSON
                    max_tokens: 2000
                })
            });

            // Обработка ошибок HTTP
            if (!response.ok) {
                const errorText = await response.text();
                console.error(`❌ OpenRouter HTTP Error: ${response.status}`);
                console.error(`Response body: ${errorText}`);
                
                // Если 429 (Rate Limit) или 503 (Service Unavailable) — пытаемся повторить
                if ((response.status === 429 || response.status === 503) && retryCount < maxRetries) {
                    const waitTime = Math.pow(2, retryCount) * 1000; // Exponential backoff
                    console.log(`⏳ Ждем ${waitTime}ms перед повторной попыткой...`);
                    await new Promise(resolve => setTimeout(resolve, waitTime));
                    return attemptRequest(retryCount + 1);
                }
                
                throw new Error(`HTTP ${response.status}: ${errorText.slice(0, 200)}`);
            }

            const data = await response.json();
            
            // Проверка структуры ответа
            if (!data.choices || data.choices.length === 0) {
                throw new Error("OpenRouter вернул пустой массив choices");
            }

            let content = data.choices[0]?.message?.content;

            if (!content) {
                throw new Error("OpenRouter вернул пустой content");
            }

            // Очистка от markdown блоков
            content = content
                .replace(/```json\s*/g, "")
                .replace(/```\s*/g, "")
                .trim();

            // Дополнительная очистка от возможного мусора в начале/конце
            if (isJson) {
                // Находим первую [ или {
                const firstBracket = content.search(/[\[\{]/);
                if (firstBracket !== -1) {
                    content = content.slice(firstBracket);
                }
                
                // Находим последнюю ] или }
                const lastBracket = Math.max(
                    content.lastIndexOf(']'),
                    content.lastIndexOf('}')
                );
                if (lastBracket !== -1) {
                    content = content.slice(0, lastBracket + 1);
                }
            }

            console.log(`✅ OpenRouter успешно ответил (${content.length} символов)`);
            
            // Валидация JSON если требуется
            if (isJson) {
                try {
                    JSON.parse(content);
                } catch (parseError) {
                    console.error("⚠️ OpenRouter вернул невалидный JSON:", content.slice(0, 200));
                    throw new Error("Invalid JSON from AI");
                }
            }

            return content;

        } catch (err) {
            console.error(`❌ OpenRouter Error (попытка ${retryCount + 1}):`, err.message);
            
            // Если есть еще попытки — повторяем
            if (retryCount < maxRetries) {
                const waitTime = Math.pow(2, retryCount) * 1000;
                console.log(`⏳ Ждем ${waitTime}ms перед повторной попыткой...`);
                await new Promise(resolve => setTimeout(resolve, waitTime));
                return attemptRequest(retryCount + 1);
            }
            
            // Если попытки исчерпаны — пробрасываем ошибку
            throw err;
        }
    }

    // Запускаем с нулевой попытки
    return attemptRequest(0);
}

/**
 * Проверка доступности OpenRouter API
 */
export async function checkAPIHealth() {
    try {
        const testPrompt = "Reply with: OK";
        await callAI(testPrompt, false, 0);
        return true;
    } catch (err) {
        console.error("❌ OpenRouter API недоступен:", err.message);
        return false;
    }
}