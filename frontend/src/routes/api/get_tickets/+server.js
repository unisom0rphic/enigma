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
    const devices = ['Сигма-1', 'Орт-2', 'Метан-3', 'ПГС-10'];
    const sentiments = ['позитивный', 'негативный', 'нейтральный'];
    const issues = [
        'Прибор не включается.',
        'Требуется поверка.',
        'Нет показаний на дисплее.',
        'Сигнализация срабатывает без причины.',
        'Запрос документации.',
        'Необходима замена датчика.'
    ];
    // Домены для проверки фильтра по Email
    const emailDomains = ['@gas.ru', '@mail.ru', '@yandex.ru', '@corp.com'];
    // Типы телефонов для проверки фильтра
    const phoneTypes = [
        { label: 'Мобильный', prefix: '+7 (9' }, 
        { label: 'Городской', prefix: '+7 (3' }
    ];

    const tickets = [];

    // Генерируем 60 записей
    for (let i = 1; i <= 60; i++) {
        const phoneType = getRandomElement(phoneTypes);
        // Генерируем телефон в зависимости от типа
        const phone = phoneType.prefix + Math.floor(Math.random() * 1000000000).toString().slice(0, 9) + ')';
        const domain = getRandomElement(emailDomains);
        const name = getRandomElement(names);

        tickets.push({
            id: i,
            date: `2023-10-${(i % 28) + 1} ${Math.floor(Math.random() * 24)}:${Math.floor(Math.random() * 60)}`,
            name: name,
            object: getRandomElement(objects),
            phone: phone,
            email: `${name.split(' ')[0].toLowerCase()}${i}${domain}`,
            factory_numbers: `ГН-${generateId()}`,
            device_type: getRandomElement(devices),
            sentiment: getRandomElement(sentiments),
            issue: getRandomElement(issues),
            // Добавляем служебные поля для удобства фильтрации на клиенте
            email_domain: domain,
            phone_type: phoneType.label
        });
    }

    // Имитация задержки
    await new Promise(resolve => setTimeout(resolve, 200));

    return json(tickets);
}