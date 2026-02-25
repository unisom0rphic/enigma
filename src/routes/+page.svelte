<script>
    import { onMount } from 'svelte';

    // --- Состояния (State) ---
    let tickets = $state([]);
    let isLoading = $state(true);
    let searchTerm = $state('');
    let currentPage = $state(1);
    const itemsPerPage = 15;

    // --- Жизненный цикл ---
    onMount(async () => {
        try {
            const response = await fetch('/api/get_tickets');
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            tickets = await response.json();
        } catch (error) {
            console.error('Ошибка загрузки данных:', error);
        } finally {
            isLoading = false;
        }
    });

    // --- Производные состояния (Derived) ---
    
    // Фильтрация (Клиентская)
    let filteredTickets = $derived(() => {
        const term = searchTerm.toLowerCase();
        if (!term) return tickets;

        return tickets.filter(t => 
            t.name.toLowerCase().includes(term) || // Поиск по name
            t.object.toLowerCase().includes(term) ||
            t.issue.toLowerCase().includes(term) ||
            t.factory_numbers.toLowerCase().includes(term)
        );
    });

    // Пагинация
    let totalPages = $derived(Math.ceil(filteredTickets().length / itemsPerPage));
    
    let paginatedTickets = $derived(() => {
        const start = (currentPage - 1) * itemsPerPage;
        const end = start + itemsPerPage;
        return filteredTickets().slice(start, end);
    });

    // Сброс страницы при вводе в поиск
    $effect(() => {
        if (searchTerm) {
            currentPage = 1;
        }
    });

    // --- Хелперы ---
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
        <h1>Обращения граждан</h1>
        <div class="controls">
            <input 
                type="text" 
                placeholder="Поиск по ФИО, объекту, номеру..." 
                bind:value={searchTerm}
            />
        </div>
    </header>

    {#if isLoading}
        <div class="loader">Загрузка данных...</div>
    {:else if tickets.length === 0}
        <div class="empty">Нет данных для отображения</div>
    {:else}
        <div class="table-wrapper">
            <table class="tickets-table">
                <thead>
                    <tr>
                        <th>Дата</th>
                        <th>ФИО</th>
                        <th>Объект</th>
                        <th>Телефон / Email</th>
                        <th>Зав. № / Тип</th>
                        <th>Эмоц. окрас</th>
                        <th>Суть вопроса</th>
                    </tr>
                </thead>
                <tbody>
                    {#each paginatedTickets() as ticket (ticket.id)}
                        <tr>
                            <td data-label="Дата">{ticket.date}</td>
                            <!-- Используем ticket.name -->
                            <td data-label="ФИО">{ticket.name}</td>
                            <td data-label="Объект">{ticket.object}</td>
                            <td data-label="Контакты">
                                <div>{ticket.phone}</div>
                                <div class="subtext">{ticket.email}</div>
                            </td>
                            <td data-label="Прибор">
                                <div>{ticket.factory_numbers}</div>
                                <div class="subtext">{ticket.device_type}</div>
                            </td>
                            <td data-label="Окрас">
                                <span class="sentiment-badge {getSentimentClass(ticket.sentiment)}">
                                    {ticket.sentiment}
                                </span>
                            </td>
                            <td data-label="Вопрос" class="issue-cell">{ticket.issue}</td>
                        </tr>
                    {/each}
                </tbody>
            </table>
        </div>

        <footer class="pagination">
            <span>Страница {currentPage} из {totalPages || 1}</span>
            <div class="btn-group">
                <button 
                    onclick={() => currentPage--} 
                    disabled={currentPage === 1}
                >Назад</button>
                
                <button 
                    onclick={() => currentPage++} 
                    disabled={currentPage >= totalPages}
                >Вперед</button>
            </div>
        </footer>
    {/if}
</div>

<style>
    :global(body) {
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Open Sans', 'Helvetica Neue', sans-serif;
        background-color: #f4f6f9;
        margin: 0;
        color: #333;
    }

    .container {
        max-width: 1400px;
        margin: 0 auto;
        padding: 2rem;
    }

    header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 1.5rem;
        flex-wrap: wrap;
        gap: 1rem;
    }

    h1 {
        margin: 0;
        font-size: 1.5rem;
        color: #2c3e50;
    }

    input {
        padding: 0.75rem 1rem;
        border: 1px solid #dcdfe6;
        border-radius: 4px;
        width: 300px;
        font-size: 0.95rem;
        transition: border-color 0.2s;
    }

    input:focus {
        outline: none;
        border-color: #409eff;
    }

    .table-wrapper {
        overflow-x: auto;
        background: white;
        border-radius: 8px;
        box-shadow: 0 2px 12px rgba(0,0,0,0.05);
    }

    .tickets-table {
        width: 100%;
        border-collapse: collapse;
        min-width: 900px;
    }

    th, td {
        padding: 12px 16px;
        text-align: left;
        border-bottom: 1px solid #ebeef5;
        font-size: 0.9rem;
    }

    th {
        background-color: #f5f7fa;
        color: #606266;
        font-weight: 600;
        white-space: nowrap;
    }

    tr:hover {
        background-color: #f5f7fa;
    }

    .subtext {
        font-size: 0.8rem;
        color: #909399;
        margin-top: 4px;
    }

    .sentiment-badge {
        padding: 4px 8px;
        border-radius: 12px;
        font-size: 0.8rem;
        font-weight: 600;
        text-transform: capitalize;
        display: inline-block;
    }

    .sentiment-positive {
        background-color: #e1f3d8;
        color: #67c23a;
    }

    .sentiment-negative {
        background-color: #fde2e2;
        color: #f56c6c;
    }

    .sentiment-neutral {
        background-color: #e9e9eb;
        color: #909399;
    }

    .issue-cell {
        max-width: 300px;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }

    .pagination {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-top: 1.5rem;
        font-size: 0.9rem;
        color: #606266;
    }

    button {
        background-color: #409eff;
        color: white;
        border: none;
        padding: 8px 16px;
        border-radius: 4px;
        cursor: pointer;
        margin-left: 10px;
        transition: background 0.2s;
    }

    button:hover:not(:disabled) {
        background-color: #66b1ff;
    }

    button:disabled {
        background-color: #c0c4cc;
        cursor: not-allowed;
    }

    .loader, .empty {
        text-align: center;
        padding: 3rem;
        color: #909399;
    }
</style>