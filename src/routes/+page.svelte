<script>
    import { onMount } from 'svelte';

    // --- Состояния ---
    let tickets = $state([]);
    let isLoading = $state(true);
    let currentPage = $state(1);
     // --- Состояния для фильтра настроения ---
    let selectedSentiments = $state([]); // Выбранные настроения
    let isSentimentDropdownOpen = $state(false); // Открыт ли dropdown
    const sentimentOptions = ['позитивный', 'негативный', 'нейтральный'];

    // Функция для переключения чекбоксов в массиве
    function toggleSelection(array, item) {
        const index = array.indexOf(item);
        if (index === -1) {
            array.push(item);
        } else {
            array.splice(index, 1);
        }
    }   const itemsPerPage = 15;

    // --- Состояния фильтров ---
    // Какое поле ищем (по умолчанию 'name')
    let searchField = $state('name');
    // Что ищем
    let searchValue = $state('');

    // Карта полей для отображения в селекте
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

    // --- Логика фильтрации (Derived) ---
    let filteredTickets = $derived(() => {
        const term = searchValue.toLowerCase().trim();
        
        return tickets.filter(t => {
            // 1. Логика текстового поиска
            const fieldValue = t[searchField];
            const stringVal = String(fieldValue || '').toLowerCase();
            const matchesSearch = !term || stringVal.includes(term);

            // 2. Логика фильтра по настроению
            // Если массив пуст, считаем, что фильтр не активен
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

    // Сброс страницы при изменении фильтров
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
</script>

<svelte:head>
    <title>Служба поддержки | Тикеты</title>
</svelte:head>

<div class="container">
    <header>
        <h1>Обращения граждан ({filteredTickets().length})</h1>
        <div class="header-actions">
            <a href="/analytics" class="btn-secondary">Аналитика</a>
        </div>
    </header>

    <!-- Панель поиска -->
    <div class="search-panel">
        <div class="filters-row">
            <!-- Левая часть: Выбор поля + Ввод текста -->
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

            <!-- Правая часть: Фильтр настроения -->
            <div class="dropdown-container">
                <button 
                    class="dropdown-trigger"
                    onclick={() => isSentimentDropdownOpen = !isSentimentDropdownOpen}
                >
                    Настроение {selectedSentiments.length > 0 ? `(${selectedSentiments.length})` : '(Все)'}
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
    header { margin-bottom: 1rem; }
    h1 { margin: 0; font-size: 1.5rem; color: #2c3e50; }

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

    /* Select (Dropdown) */
    .field-select {
        background-color: #f5f7fa;
        border: none;
        border-right: 1px solid #dcdfe6;
        padding: 0.75rem 1rem;
        font-size: 0.95rem;
        color: #333; /* ИСПРАВЛЕНИЕ: Темный цвет текста */
        cursor: pointer;
        outline: none;
        min-width: 140px;
    }

    /* Input */
    .search-input {
        flex: 1;
        border: none;
        padding: 0.75rem 1rem;
        font-size: 0.95rem;
        color: #333;
        outline: none;
        background: #fff;
    }

    .search-input::placeholder {
        color: #a8abb2;
    }

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
    button { background-color: #409eff; color: white; border: none; padding: 8px 16px; border-radius: 4px; cursor: pointer; margin-left: 10px; transition: opacity 0.2s; }
    button:disabled { opacity: 0.6; cursor: not-allowed; }
    button:hover:not(:disabled) { opacity: 0.9; }
    /* --- Filters Layout --- */
    .filters-row {
        display: flex;
        gap: 1rem;
        align-items: flex-start;
        flex-wrap: wrap;
    }

    /* --- Dropdown Styles --- */
    .dropdown-container { position: relative; }
    
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
        color: #333; /* Темный цвет текста */
        height: 42px; /* Чтобы совпадало по высоте с инпутом */
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
        gap: 0.5rem;
        min-width: 140px;
    }

    .checkbox-label {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        cursor: pointer;
        padding: 2px;
    }
    .header-actions {
        display: flex;
        gap: 1rem;
        align-items: center;
    }

    .btn-secondary {
        background-color: #6c757d;
        color: white;
        text-decoration: none;
        padding: 0.5rem 1rem;
        border-radius: 4px;
        font-size: 0.9rem;
        transition: background 0.2s;
    }
    .btn-secondary:hover {
        background-color: #5a6268;
    }
</style>

<svelte:document 
    onclick={(e) => {
        if (!e.target.closest('.dropdown-container')) {
            isSentimentDropdownOpen = false;
        }
    } 
}/>