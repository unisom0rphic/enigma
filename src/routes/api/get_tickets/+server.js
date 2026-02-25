// src/routes/api/get_tickets/+server.js
import { json } from '@sveltejs/kit';

export async function GET() {
    // Имитация задержки сервера (опционально)
    await new Promise(resolve => setTimeout(resolve, 300));

    const tickets = [
        {
            id: 1,
            date: '2023-10-25 14:30',
            name: 'Иванов Иван Иванович', // Переименовали fio -> name
            object: 'Котельная №3',
            phone: '+7 (900) 123-45-67',
            email: 'ivanov@gas.ru',
            factory_numbers: 'ГН-001234',
            device_type: 'Сигма-1',
            sentiment: 'негативный',
            issue: 'Прибор не включается, издаёт странные звуки. Срочно нужен мастер.'
        },
        {
            id: 2,
            date: '2023-10-25 15:00',
            name: 'Петров Петр Петрович',
            object: 'Газпром трансгаз',
            phone: '+7 (900) 765-43-21',
            email: 'petrov@corp.ru',
            factory_numbers: 'ГН-556677',
            device_type: 'Орт-2',
            sentiment: 'позитивный',
            issue: 'Хотелось бы уточнить сроки поверки оборудования. Заранее спасибо.'
        },
        {
            id: 3,
            date: '2023-10-26 09:15',
            name: 'Сидорова Анна Павловна',
            object: 'Завод "Авангард"',
            phone: '+7 (950) 111-22-33',
            email: 'sidorova@avangard.com',
            factory_numbers: 'ГН-998877',
            device_type: 'Сигма-1',
            sentiment: 'нейтральный',
            issue: 'Запрос на техническую документацию.'
        },
        {
            id: 4,
            date: '2023-10-26 11:45',
            name: 'Козлов Дмитрий Сергеевич',
            object: 'ТЭЦ-5',
            phone: '+7 (922) 555-66-77',
            email: 'kozlov@energy.net',
            factory_numbers: 'ГН-112233',
            device_type: 'Метан-3',
            sentiment: 'негативный',
            issue: 'Показания некорректны, завышает процент метана.'
        }
    ];

    return json(tickets);
}