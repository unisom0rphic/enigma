// src/routes/api/get_tickets/+server.js
import { json } from '@sveltejs/kit';

function getRandomElement(arr) {
    return arr[Math.floor(Math.random() * arr.length)];
}

function generateId() {
    return Math.floor(Math.random() * 100000);
}

export async function GET() {
    // Справочники для рандомизации
    const names = ['Иванов И.И.', 'Петров П.П.', 'Сидорова А.А.', 'Козлов Д.С.', 'Смирнов В.В.', 'Попова Е.А.'];
    const objects = ['Котельная №1', 'Газпром трансгаз', 'Завод "Авангард"', 'ТЭЦ-5', 'Больница №3', 'Школа №12'];
    
    // Добавим устройства, которые есть в базе, и "проблемные" названия
    const devices = [
        'СГГ-20', 'СГГ-6М', 'ПГС-10', 'СТГ-1', 
        'Неизвестный прибор XYZ', 'Старый датчик', 'СГГ 2О (опечатка)' // Эти скорее всего вызовут ошибку поиска
    ];

    const sentiments = ['позитивный', 'негативный', 'нейтральный'];
    const issues = [
        'Прибор не включается.',
        'Требуется поверка.',
        'Нет показаний на дисплее.',
        'Сигнализация срабатывает без причины.',
        'Запрос документации.',
        'Необходима замена датчика.'
    ];

    const failReasons = [
        'Документация не найдена на сайте',
        'Не удалось определить тип прибора',
        'Ошибка скачивания PDF',
        'Не удалось извлечь текст из документа'
    ];

    const emailDomains = ['@gas.ru', '@mail.ru', '@yandex.ru', '@corp.com'];
    const phoneTypes = [
        { label: 'Мобильный', prefix: '+7 (9' }, 
        { label: 'Городской', prefix: '+7 (3' }
    ];

    const tickets = [];

    // Генерируем 60 записей
    for (let i = 1; i <= 60; i++) {
        const phoneType = getRandomElement(phoneTypes);
        const phone = phoneType.prefix + Math.floor(Math.random() * 1000000000).toString().slice(0, 9) + ')';
        const domain = getRandomElement(emailDomains);
        const name = getRandomElement(names);
        const device = getRandomElement(devices);
        
        // Логика определения проблемных тикетов
        // Если в названии прибора есть "Неизвестный", "Старый" или "опечатка" - считаем ошибкой
        // Или просто рандомно для 15% случаев
        let manualRequired = false;
        let failReason = null;

        if (device.includes('Неизвестный') || device.includes('Старый') || device.includes('опечатка')) {
            manualRequired = true;
            failReason = 'Тип прибора не найден в базе знаний';
        } else if (Math.random() < 0.15) { 
            manualRequired = true;
            failReason = getRandomElement(failReasons);
        }

        tickets.push({
            id: i,
            date: `2023-10-${(i % 28) + 1} ${Math.floor(Math.random() * 24)}:${Math.floor(Math.random() * 60)}`,
            name: name,
            object: getRandomElement(objects),
            phone: phone,
            email: `${name.split(' ')[0].toLowerCase()}${i}${domain}`,
            factory_numbers: `ГН-${generateId()}`,
            device_type: device,
            sentiment: getRandomElement(sentiments),
            issue: getRandomElement(issues),
            
            // Новые поля
            manual_required: manualRequired,
            fail_reason: failReason,

            // Служебные поля для фильтрации
            email_domain: domain,
            phone_type: phoneType.label
        });
    }

    // Имитация задержки сервера
    await new Promise(resolve => setTimeout(resolve, 500));

    return json(tickets);
}