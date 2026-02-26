<script>
    import { onMount } from 'svelte';

    // --- Состояния ---
    let tickets = $state([]);
    let isLoading = $state(true);
    let currentPage = $state(1);
    
    // --- Состояния для фильтров и Dropdowns ---
    let selectedSentiments = $state([]);
    let isSentimentDropdownOpen = $state(false);
    // Новое состояние для меню экспорта
    let isExportDropdownOpen = $state(false); 

    const sentimentOptions = ['позитивный', 'негативный', 'нейтральный'];

    function toggleSelection(array, item) {
        const index = array.indexOf(item);
        if (index === -1) {
            array.push(item);
        } else {
            array.splice(index, 1);
        }
    }

    const itemsPerPage = 15;

    // --- Состояния фильтров поиска ---
    let searchField = $state('name');
    let searchValue = $state('');

    const fieldOptions = [
        { value: 'name', label: 'Имя (ФИО)' },
        { value: 'email', label: 'Email' },
        { value: 'date', label: 'Дата' },
        { value: 'phone', label: 'Телефон' },
        { value: 'object', label: 'Объект' },
        { value: 'factory_numbers', label: 'Зав. номер' },
        { value: 'issue', label: 'Суть вопроса' }
    ];

    // --- Жизненный цикл ---
    onMount(async () => {
        try {
            const response = await fetch('/api/get_tickets');
            tickets = await response.json();
        } catch (error) {
            console.error('Ошибка загрузки данных:', error);
        } finally {
            isLoading = false;
        }
    });

    // --- Логика фильтрации ---
    let filteredTickets = $derived(() => {
        const term = searchValue.toLowerCase().trim();
        
        return tickets.filter(t => {
            const fieldValue = t[searchField];
            const stringVal = String(fieldValue || '').toLowerCase();
            const matchesSearch = !term || stringVal.includes(term);

            const matchesSentiment = selectedSentiments.length === 0 || 
                selectedSentiments.includes(t.sentiment);

            return matchesSearch && matchesSentiment;
        });
    });

    // --- Пагинация ---
    let totalPages = $derived(Math.ceil(filteredTickets().length / itemsPerPage));
    
    let paginatedTickets = $derived(() => {
        const start = (currentPage - 1) * itemsPerPage;
        const end = start + itemsPerPage;
        return filteredTickets().slice(start, end);
    });

    $effect(() => {
        searchField, searchValue;
        currentPage = 1;
    });

    // --- Хелперы UI ---
    function getSentimentClass(sentiment) {
        switch (sentiment) {
            case 'позитивный': return 'sentiment-positive';
            case 'негативный': return 'sentiment-negative';
            default: return 'sentiment-neutral';
        }
    }

    // --- Логика Экспорта ---
    // ВАЖНО: экспорт напрямую в .xlsx добавляет 30-50Кб к размеру бандла,
    // поэтому принято решение временно отказаться от него 

    // Хелпер для скачивания файла
    function downloadFile(content, filename, mimeType) {
        const blob = new Blob([content], { type: mimeType });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a); // Для Firefox
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }

    // Экспорт в JSON
    function exportJSON() {
        const data = filteredTickets(); // Берем все отфильтрованные
        const jsonString = JSON.stringify(data, null, 2);
        downloadFile(jsonString, 'tickets_export.json', 'application/json');
        isExportDropdownOpen = false;
    }

    // Экспорт в CSV
    function exportCSV() {
        const data = filteredTickets();
        if (data.length === 0) {
            alert('Нет данных для экспорта');
            return;
        }

        // Определяем заголовки на основе "сырых" ключей
        // Можно взять ключи из первого объекта, но лучше задать явно для порядка колонок
        const headers = [
            'id', 'date', 'name', 'object', 'phone', 'phone_type', 
            'email', 'device_type', 'factory_numbers', 'sentiment', 'issue'
        ];

        // Формируем строки CSV
        const csvRows = [];

        // Добавляем строку заголовков
        csvRows.push(headers.join(';')); // Используем ; как разделитель, так Excel корректнее открывает на RU локали

        // Добавляем данные
        for (const row of data) {
            const values = headers.map(header => {
                const value = row[header] === null || row[header] === undefined ? '' : row[header];
                // Экранируем кавычки и оборачиваем в кавычки, если есть разделитель или перенос строки
                const stringValue = String(value);
                if (stringValue.includes(';') || stringValue.includes('"') || stringValue.includes('\n')) {
                    return `"${stringValue.replace(/"/g, '""')}"`;
                }
                return stringValue;
            });
            csvRows.push(values.join(';'));
        }

        const csvString = csvRows.join('\n');
        // Добавляем BOM для корректного отображения кириллицы в Excel
        const bom = '\uFEFF'; 
        downloadFile(bom + csvString, 'tickets_export.csv', 'text/csv;charset=utf-8;');
        isExportDropdownOpen = false;
    }
</script>

<svelte:head>
    <title>Служба поддержки | Тикеты</title>
</svelte:head>

<div class="container">
    <header>
        <h1>Обращения граждан ({filteredTickets().length})</h1>
    </header>

    <!-- Панель поиска -->
    <div class="search-panel">
        <div class="filters-row">
            <!-- 1. Поиск -->
            <div class="search-wrapper">
                <select bind:value={searchField} class="field-select">
                    {#each fieldOptions as opt}
                        <option value={opt.value}>{opt.label}</option>
                    {/each}
                </select>
                
                <input 
                    type="text" 
                    placeholder={fieldOptions.find(o => o.value === searchField)?.label || 'Поиск...'}
                    bind:value={searchValue}
                    class="search-input"
                />
            </div>

            <!-- 2. Фильтр настроения -->
            <div class="dropdown-container">
                <button 
                    class="dropdown-trigger"
                    onclick={() => isSentimentDropdownOpen = !isSentimentDropdownOpen}
                >
                    Настроение {selectedSentiments.length > 0 ? `(${selectedSentiments.length})` : ''}
                    <span class="arrow">▼</span>
                </button>

                {#if isSentimentDropdownOpen}
                    <div class="dropdown-menu">
                        {#each sentimentOptions as sentiment}
                            <label class="checkbox-label">
                                <input 
                                    type="checkbox" 
                                    checked={selectedSentiments.includes(sentiment)}
                                    onchange={() => toggleSelection(selectedSentiments, sentiment)}
                                />
                                <span class="sentiment-badge {getSentimentClass(sentiment)}">
                                    {sentiment}
                                </span>
                            </label>
                        {/each}
                    </div>
                {/if}
            </div> 
            
            <!-- 3. Кнопка Аналитика -->
            <a href="/analytics" class="btn-white">Аналитика</a>

            <!-- 4. Кнопка Экспорт -->
            <div class="dropdown-container">
                <button 
                    class="btn-white dropdown-trigger-alt"
                    onclick={() => isExportDropdownOpen = !isExportDropdownOpen}>
                    Экспорт
                    <span class="arrow">▼</span>
                </button>

                {#if isExportDropdownOpen}
                    <div class="dropdown-menu">
                        <button class="dropdown-item" onclick={exportCSV}>
                            .CSV
                        </button>
                        <button class="dropdown-item" onclick={exportJSON}>
                            .JSON
                        </button>
                        <!-- placeholder для будущего xlsx -->
                        <!-- <button class="dropdown-item" disabled>.XLSX (Скоро)</button> -->
                    </div>
                {/if}
            </div>
        </div>

        <div class="hint">
            Например: выберите "Дата" и введите "2023-10-25". Используйте фильтр настроения для отсева по тону.
        </div>
    </div>

    {#if isLoading}
        <div class="loader">Загрузка данных...</div>
    {:else if tickets.length === 0}
        <div class="empty">Нет данных</div>
    {:else}
        <div class="table-wrapper">
            <table class="tickets-table">
                <thead>
                    <tr>
                        <th>Дата</th>
                        <th>ФИО</th>
                        <th>Объект</th>
                        <th>Телефон</th>
                        <th>Email</th>
                        <th>Прибор</th>
                        <th>Окрас</th>
                        <th>Вопрос</th>
                    </tr>
                </thead>
                <tbody>
                    {#each paginatedTickets() as ticket (ticket.id)}
                        <tr>
                            <td>{ticket.date}</td>
                            <td>{ticket.name}</td>
                            <td>{ticket.object}</td>
                            <td>
                                <span class="sub-info">({ticket.phone_type})</span><br>
                                {ticket.phone}
                            </td>
                            <td>{ticket.email}</td>
                            <td>
                                <div>{ticket.device_type}</div>
                                <div class="subtext">№ {ticket.factory_numbers}</div>
                            </td>
                            <td>
                                <span class="sentiment-badge {getSentimentClass(ticket.sentiment)}">
                                    {ticket.sentiment}
                                </span>
                            </td>
                            <td class="issue-cell">{ticket.issue}</td>
                        </tr>
                    {/each}
                </tbody>
            </table>
        </div>

        <footer class="pagination">
            <span>Страница {currentPage} из {totalPages || 1}</span>
            <div class="btn-group">
                <button onclick={() => currentPage--} disabled={currentPage === 1}>Назад</button>
                <button onclick={() => currentPage++} disabled={currentPage >= totalPages}>Вперед</button>
            </div>
        </footer>
    {/if}
</div>

<style>
    /* --- Layout --- */
    .container { max-width: 1500px; margin: 0 auto; padding: 2rem; }
    header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 1rem;
        flex-wrap: wrap;
        gap: 1rem;
    }

    h1 {
        margin: 0;
        font-size: 1.5rem;
        color: #2c3e50;
    }

    /* --- Search Panel --- */
    .search-panel {
        background: #fff;
        padding: 1.5rem;
        border-radius: 8px;
        margin-bottom: 1.5rem;
        box-shadow: 0 2px 8px rgba(0,0,0,0.05);
        border: 1px solid #e4e7ed;
    }

    .search-wrapper {
        display: flex;
        gap: 0;
        border-radius: 6px;
        overflow: hidden;
        box-shadow: 0 0 0 1px #dcdfe6;
        max-width: 600px;
    }

    .field-select {
        background-color: #f5f7fa;
        border: none;
        border-right: 1px solid #dcdfe6;
        padding: 0.75rem 1rem;
        font-size: 0.95rem;
        color: #333;
        cursor: pointer;
        outline: none;
        min-width: 140px;
    }

    .search-input {
        flex: 1;
        border: none;
        padding: 0.75rem 1rem;
        font-size: 0.95rem;
        color: #333;
        outline: none;
        background: #fff;
    }

    .search-input::placeholder { color: #a8abb2; }

    .hint {
        margin-top: 0.75rem;
        font-size: 0.8rem;
        color: #909399;
    }

    /* --- Table --- */
    .table-wrapper { overflow-x: auto; background: white; border-radius: 8px; box-shadow: 0 2px 12px rgba(0,0,0,0.05); }
    .tickets-table { width: 100%; border-collapse: collapse; min-width: 1000px; }
    th, td { padding: 10px 16px; text-align: left; border-bottom: 1px solid #ebeef5; font-size: 0.9rem; }
    th { background-color: #f5f7fa; color: #606266; font-weight: 600; white-space: nowrap; }
    tr:hover { background-color: #f5f7fa; }
    
    .subtext { font-size: 0.8rem; color: #909399; margin-top: 2px; }
    .sub-info { font-size: 0.75rem; color: #909399; }
    .issue-cell { max-width: 300px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }

    /* --- Badges --- */
    .sentiment-badge {
        padding: 4px 8px;
        border-radius: 12px;
        font-size: 0.75rem;
        font-weight: 600;
        text-transform: capitalize;
        display: inline-block;
    }
    .sentiment-positive { background-color: #e1f3d8; color: #67c23a; }
    .sentiment-negative { background-color: #fde2e2; color: #f56c6c; }
    .sentiment-neutral { background-color: #e9e9eb; color: #909399; }

    /* --- Pagination --- */
    .pagination { display: flex; justify-content: space-between; align-items: center; margin-top: 1.5rem; }
    
    /* --- Buttons General --- */
    .btn-group button, .pagination button {
        background-color: #409eff; 
        color: white; 
        border: none; 
        padding: 8px 16px; 
        border-radius: 4px; 
        cursor: pointer; 
        margin-left: 10px; 
        transition: opacity 0.2s;
    }
    button:disabled { opacity: 0.6; cursor: not-allowed; }
    button:hover:not(:disabled) { opacity: 0.9; }

    /* --- Filters Layout --- */
    .filters-row {
        display: flex;
        gap: 1rem;
        align-items: center;
        flex-wrap: wrap;
    }

    /* Стиль белой кнопки (используется для Аналитики и Экспорта) */
    .btn-white {
        background-color: #ffffff;
        color: #333;
        text-decoration: none;
        padding: 0.5rem 1rem;
        border-radius: 6px;
        border: 1px solid #dcdfe6;
        box-shadow: 0 2px 4px rgba(0,0,0,0.04);
        transition: all 0.2s;
        white-space: nowrap; 
        height: 42px; 
        display: flex;
        align-items: center;
        justify-content: center;
        box-sizing: border-box;
        cursor: pointer;
        gap: 0.5rem; /* Для стрелочки */
    }

    .btn-white:hover {
        background-color: #f5f7fa;
        border-color: #c0c4cc;
    }

    /* --- Dropdown Styles --- */
    .dropdown-container { position: relative; }
    
    /* Триггер для фильтра настроения */
    .dropdown-trigger {
        padding: 0.75rem 1rem;
        background: #fff;
        border: 1px solid #dcdfe6;
        border-radius: 4px;
        cursor: pointer;
        display: flex;
        align-items: center;
        gap: 0.5rem;
        min-width: 150px;
        justify-content: space-between;
        color: #333;
        height: 42px;
        box-sizing: border-box;
    }
    
    .arrow { font-size: 0.7rem; color: #909399; }

    .dropdown-menu {
        position: absolute;
        top: 110%;
        left: 0;
        background: #fff;
        border: 1px solid #dcdfe6;
        border-radius: 4px;
        padding: 0.5rem;
        z-index: 10;
        box-shadow: 0 2px 12px rgba(0,0,0,0.1);
        display: flex;
        flex-direction: column;
        gap: 0.25rem; /* Чуть меньше отступ для пунктов */
        min-width: 140px;
    }

    /* Стили для пунктов меню экспорта */
    .dropdown-item {
        background: none;
        border: none;
        padding: 0.5rem 0.75rem;
        text-align: left;
        cursor: pointer;
        font-size: 0.9rem;
        color: #333;
        border-radius: 4px;
        transition: background 0.2s;
        margin: 0; /* сброс дефолтных отступов */
    }

    .dropdown-item:hover {
        background-color: #f5f7fa;
        color: #409eff;
    }

    .checkbox-label {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        cursor: pointer;
        padding: 2px;
    }
</style>

<svelte:document 
    onclick={(e) => {
        // Закрываем все дропдауны, если клик был вне их контейнеров
        if (!e.target.closest('.dropdown-container')) {
            isSentimentDropdownOpen = false;
            isExportDropdownOpen = false;
        }
    } 
}/>