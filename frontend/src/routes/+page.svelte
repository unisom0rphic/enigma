<script>
    import { onMount } from 'svelte';

    // --- Config ---
    // Обратите внимание: оставляем без слэша в конце, чтобы удобно конкатенировать ID
    const API_BASE = 'http://localhost:8000/api/v1/tickets'; 

    // --- Состояния ---
    let tickets = $state([]);
    let isLoading = $state(true);
    let currentPage = $state(1);
    
    // --- Фильтрация ---
    let showResolved = $state(false); 
    let selectedSentiments = $state([]);
    let isSentimentDropdownOpen = $state(false);
    let isExportDropdownOpen = $state(false); 

    const sentimentOptions = ['positive', 'negative', 'neutral'];

    // --- Модальное окно ---
    let isModalOpen = $state(false);
    let selectedTicket = $state(null);
    let isSaving = $state(false);

    function toggleSelection(array, item) {
        const index = array.indexOf(item);
        if (index === -1) array.push(item);
        else array.splice(index, 1);
    }

    const itemsPerPage = 15;

    // --- Состояния фильтров поиска ---
    let searchField = $state('full_name');
    let searchValue = $state('');

    const fieldOptions = [
        { value: 'full_name', label: 'Имя (ФИО)' },
        { value: 'email', label: 'Email' },
        { value: 'created_at', label: 'Дата' },
        { value: 'phone_num', label: 'Телефон' },
        { value: 'object_name', label: 'Объект' },
        { value: 'device_num', label: 'Зав. номер' },
        { value: 'summary', label: 'Суть вопроса' }
    ];

    // --- Жизненный цикл ---
    onMount(async () => {
        await loadTickets();
    });

    async function loadTickets() {
        isLoading = true;
        try {
            // API: GET /api/v1/tickets/ (добавляем слэш) + query params
            const url = `${API_BASE}/?show_resolved=${showResolved}`;
            const response = await fetch(url);
            if (!response.ok) throw new Error('Network response was not ok');
            tickets = await response.json();
        } catch (error) {
            console.error('Ошибка загрузки данных:', error);
            tickets = []; // Сбрасываем при ошибке
        } finally {
            isLoading = false;
        }
    }

    // Следим за изменением чекбокса
    $effect(() => {
        showResolved;
        loadTickets();
        currentPage = 1;
    });

    // --- Логика фильтрации и СОРТИРОВКИ (Клиентская) ---
    let filteredTickets = $derived(() => {
        const term = searchValue.toLowerCase().trim();
        
        let result = tickets.filter(t => {
            const fieldValue = t[searchField];
            const stringVal = String(fieldValue || '').toLowerCase();
            const matchesSearch = !term || stringVal.includes(term);

            const matchesSentiment = selectedSentiments.length === 0 || 
                selectedSentiments.includes(t.sentiment);

            return matchesSearch && matchesSentiment;
        });

        result.sort((a, b) => {
            if (a.is_important !== b.is_important) return b.is_important ? 1 : -1;
            if (a.manual_required !== b.manual_required) return b.manual_required ? 1 : -1;
            return new Date(b.created_at) - new Date(a.created_at);
        });

        return result;
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
            case 'positive': return 'sentiment-positive';
            case 'negative': return 'sentiment-negative';
            default: return 'sentiment-neutral';
        }
    }
    
    function getSentimentLabel(sentiment) {
        switch(sentiment) {
            case 'positive': return 'Позитивный';
            case 'negative': return 'Негативный';
            default: return 'Нейтральный';
        }
    }

    // --- Действия с Тикетом ---

    function openTicketModal(ticket) {
        selectedTicket = { ...ticket }; 
        isModalOpen = true;
    }

    function closeModal() {
        isModalOpen = false;
        selectedTicket = null;
    }

    // Универсальная функция обновления данных на сервере
    async function updateTicketOnServer(ticketData) {
        const response = await fetch(`${API_BASE}/${ticketData.id}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                full_name: ticketData.full_name,
                phone_num: ticketData.phone_num,
                email: ticketData.email,
                llm_response: ticketData.llm_response
            })
        });
        return response;
    }

    async function saveTicketChanges() {
        if (!selectedTicket) return;
        isSaving = true;
        try {
            const response = await updateTicketOnServer(selectedTicket);
            if (response.ok) {
                const idx = tickets.findIndex(t => t.id === selectedTicket.id);
                if (idx !== -1) tickets[idx] = { ...selectedTicket };
                closeModal();
            } else {
                const errData = await response.json();
                alert(`Ошибка сохранения: ${errData.detail || 'Unknown error'}`);
            }
        } catch (e) {
            console.error(e);
            alert('Ошибка сети при сохранении');
        } finally {
            isSaving = false;
        }
    }

    async function approveAndSend() {
        if (!selectedTicket) return;
        if (!confirm('Отправить ответ пользователю и закрыть тикет?')) return;

        isSaving = true;
        try {
            // 1. Сначала сохраняем изменения (если правили текст)
            const saveResponse = await updateTicketOnServer(selectedTicket);
            if (!saveResponse.ok) {
                alert('Не удалось сохранить изменения перед отправкой.');
                throw new Error('Save failed');
            }

            // 2. Обновляем локальный стейт (чтобы данные были свежие)
            const idx = tickets.findIndex(t => t.id === selectedTicket.id);
            if (idx !== -1) tickets[idx] = { ...selectedTicket };

            // 3. Отправляем approve
            const response = await fetch(`${API_BASE}/${selectedTicket.id}/approve`, {
                method: 'POST'
            });

            if (response.ok) {
                alert('Письмо отправлено!');
                // Удаляем тикет из списка (так как он теперь resolved и скрыт)
                tickets = tickets.filter(t => t.id !== selectedTicket.id);
                closeModal();
            } else {
                const err = await response.json();
                alert(`Ошибка отправки: ${err.detail}`);
            }
        } catch (e) {
            console.error(e);
        } finally {
            isSaving = false;
        }
    }

    async function deleteTicket() {
        if (!selectedTicket) return;
        if (!confirm('Вы уверены, что хотите удалить этот тикет? Это действие необратимо.')) return;

        isSaving = true;
        try {
            const response = await fetch(`${API_BASE}/${selectedTicket.id}`, {
                method: 'DELETE'
            });

            if (response.ok) {
                tickets = tickets.filter(t => t.id !== selectedTicket.id);
                closeModal();
            } else {
                const err = await response.json();
                alert(`Ошибка удаления: ${err.detail}`);
            }
        } catch (e) {
            console.error(e);
        } finally {
            isSaving = false;
        }
    }

    // --- Экспорт ---
    function downloadFile(content, filename, mimeType) {
        const blob = new Blob([content], { type: mimeType });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a); 
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }

    function exportJSON() {
        const data = filteredTickets();
        const jsonString = JSON.stringify(data, null, 2);
        downloadFile(jsonString, 'tickets_export.json', 'application/json');
        isExportDropdownOpen = false;
    }

    function exportCSV() {
        const data = filteredTickets();
        if (data.length === 0) return;

        const headers = Object.keys(data[0]); 
        const csvRows = [];
        csvRows.push(headers.join(';'));

        for (const row of data) {
            const values = headers.map(h => {
                const val = row[h] == null ? '' : String(row[h]);
                return `"${val.replace(/"/g, '""')}"`;
            });
            csvRows.push(values.join(';'));
        }

        downloadFile('\uFEFF' + csvRows.join('\n'), 'tickets_export.csv', 'text/csv;charset=utf-8;');
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

    <!-- Панель поиска (без изменений) -->
    <div class="search-panel">
        <div class="filters-row">
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

            <div class="dropdown-container">
                <button class="dropdown-trigger" onclick={() => isSentimentDropdownOpen = !isSentimentDropdownOpen}>
                    Настроение {selectedSentiments.length > 0 ? `(${selectedSentiments.length})` : ''}
                    <span class="arrow">▼</span>
                </button>
                {#if isSentimentDropdownOpen}
                    <div class="dropdown-menu">
                        {#each sentimentOptions as sentiment}
                            <label class="checkbox-label">
                                <input type="checkbox" checked={selectedSentiments.includes(sentiment)} onchange={() => toggleSelection(selectedSentiments, sentiment)}/>
                                <span class="sentiment-badge {getSentimentClass(sentiment)}">{getSentimentLabel(sentiment)}</span>
                            </label>
                        {/each}
                    </div>
                {/if}
            </div> 
            
            <label class="toggle-resolved">
                <input type="checkbox" bind:checked={showResolved} />
                Показать решенные
            </label>

            <div class="dropdown-container" style="margin-left: auto;">
                <button class="btn-white dropdown-trigger-alt" onclick={() => isExportDropdownOpen = !isExportDropdownOpen}>
                    Экспорт <span class="arrow">▼</span>
                </button>
                {#if isExportDropdownOpen}
                    <div class="dropdown-menu">
                        <button class="dropdown-item" onclick={exportCSV}>.CSV</button>
                        <button class="dropdown-item" onclick={exportJSON}>.JSON</button>
                    </div>
                {/if}
            </div>
        </div>
    </div>

    {#if isLoading}
        <div class="loader">Загрузка данных...</div>
    {:else if tickets.length === 0}
        <div class="empty">{showResolved ? 'Нет данных' : 'Нет активных обращений'}</div>
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
                        <th>Статус</th>
                        <th>Вопрос</th>
                        <th></th>
                    </tr>
                </thead>
                <tbody>
                    {#each paginatedTickets() as ticket (ticket.id)}
                        <tr class:priority-row={ticket.manual_required} class:resolved-row={ticket.is_resolved}>
                            <td>{new Date(ticket.created_at).toLocaleDateString()}</td>
                            <td>{ticket.full_name || '-'}</td>
                            <td>{ticket.object_name || '-'}</td>
                            <td>
                                <span>{ticket.phone_num || '-'}</span>
                            </td>
                            <td>{ticket.email || '-'}</td>
                            <td>
                                <div>{ticket.device_type || '-'}</div>
                                {#if ticket.device_num}
                                    <div class="subtext">№ {ticket.device_num}</div>
                                {/if}
                            </td>
                            <td>
                                {#if ticket.is_resolved}
                                    <span class="status-badge resolved">Решено</span>
                                {:else if ticket.manual_required}
                                    <span class="status-badge manual" title={ticket.summary}>Внимание</span>
                                {:else}
                                    <span class="sentiment-badge {getSentimentClass(ticket.sentiment)}">
                                        {getSentimentLabel(ticket.sentiment)}
                                    </span>
                                {/if}
                            </td>
                            <td class="issue-cell">{ticket.summary}</td>
                            <td>
                                <button class="btn-edit" onclick={() => openTicketModal(ticket)}>
                                    ✎
                                </button>
                            </td>
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

<!-- Modal -->
{#if isModalOpen && selectedTicket}
<div class="modal-overlay" onclick={closeModal}>
    <div class="modal-content" onclick={(e) => e.stopPropagation()}>
        <div class="modal-header">
            <h3>Тикет #{selectedTicket.id.toString().slice(0, 8)}</h3>
            <button class="close-btn" onclick={closeModal}>×</button>
        </div>
        
        <div class="modal-body">
            <div class="form-group">
                <label>ФИО:</label>
                <input type="text" bind:value={selectedTicket.full_name} />
            </div>
            <div class="form-group">
                <label>Email:</label>
                <input type="text" bind:value={selectedTicket.email} />
            </div>
            <div class="form-group">
                <label>Телефон:</label>
                <input type="text" bind:value={selectedTicket.phone_num} />
            </div>

            <hr />

            <div class="form-group">
                <label>Суть вопроса:</label>
                <div class="readonly-box">{selectedTicket.summary}</div>
            </div>

            <div class="form-group">
                <label>Ответ AI (можно редактировать):</label>
                <textarea bind:value={selectedTicket.llm_response} rows="6"></textarea>
            </div>
        </div>

        <div class="modal-footer">
            <!-- Кнопка удаления слева -->
            <button class="btn-danger" onclick={deleteTicket} disabled={isSaving}>
                Удалить
            </button>

            <div style="flex: 1"></div> <!-- Spacer -->

            <button class="btn-secondary" onclick={closeModal}>Отмена</button>
            <button class="btn-primary" onclick={saveTicketChanges} disabled={isSaving}>
                {isSaving ? 'Сохранение...' : 'Сохранить'}
            </button>
            {#if !selectedTicket.is_resolved}
                <button class="btn-success" onclick={approveAndSend} disabled={isSaving}>
                    Отправить и Закрыть
                </button>
            {/if}
        </div>
    </div>
</div>
{/if}

<style>
    /* --- General Layout --- */
    .container { max-width: 1600px; margin: 0 auto; padding: 2rem; font-family: sans-serif; }
    header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.5rem; }
    h1 { margin: 0; font-size: 1.5rem; color: #2c3e50; }

    /* --- Search Panel --- */
    .search-panel { background: #fff; padding: 1.5rem; border-radius: 8px; margin-bottom: 1.5rem; box-shadow: 0 2px 8px rgba(0,0,0,0.05); border: 1px solid #e4e7ed; }
    .filters-row { display: flex; gap: 1rem; align-items: center; flex-wrap: wrap; }
    
    .search-wrapper { display: flex; border-radius: 6px; overflow: hidden; box-shadow: 0 0 0 1px #dcdfe6; flex: 1; max-width: 500px; }
    .field-select { background-color: #f5f7fa; border: none; border-right: 1px solid #dcdfe6; padding: 0.75rem; color: #333; min-width: 130px; }
    .search-input { flex: 1; border: none; padding: 0.75rem; outline: none; }

    .toggle-resolved { display: flex; align-items: center; gap: 0.5rem; cursor: pointer; color: #606266; font-size: 0.9rem; user-select: none; }

    /* --- Buttons --- */
    .btn-white { background: #fff; color: #333; border: 1px solid #dcdfe6; padding: 0.6rem 1rem; border-radius: 6px; cursor: pointer; }
    .btn-edit { background: transparent; border: 1px solid #dcdfe6; color: #606266; padding: 4px 10px; border-radius: 4px; cursor: pointer; }
    .btn-edit:hover { color: #409eff; border-color: #409eff; }

    /* --- Table --- */
    .table-wrapper { overflow-x: auto; background: white; border-radius: 8px; box-shadow: 0 2px 12px rgba(0,0,0,0.05); }
    .tickets-table { width: 100%; border-collapse: collapse; min-width: 1100px; }
    th, td { padding: 12px 16px; text-align: left; border-bottom: 1px solid #ebeef5; font-size: 0.9rem; }
    th { background-color: #f5f7fa; color: #606266; font-weight: 600; }
    
    tr:hover { background-color: #f5f7fa; }
    tr.priority-row { background-color: #fff0f0; }
    tr.priority-row:hover { background-color: #ffe6e6; }
    tr.resolved-row { opacity: 0.6; color: #909399; }

    .subtext { font-size: 0.8rem; color: #909399; margin-top: 2px; }
    .issue-cell { max-width: 300px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }

    /* --- Badges --- */
    .sentiment-badge { padding: 4px 8px; border-radius: 12px; font-size: 0.75rem; font-weight: 600; display: inline-block; }
    .sentiment-positive { background-color: #e1f3d8; color: #67c23a; }
    .sentiment-negative { background-color: #fde2e2; color: #f56c6c; }
    .sentiment-neutral { background-color: #e9e9eb; color: #909399; }

    .status-badge { padding: 4px 8px; border-radius: 12px; font-size: 0.75rem; font-weight: 600; color: white; }
    .status-badge.manual { background-color: #e6a23c; cursor: help; }
    .status-badge.resolved { background-color: #67c23a; }

    /* --- Dropdowns --- */
    .dropdown-container { position: relative; }
    .dropdown-trigger { background: #fff; border: 1px solid #dcdfe6; padding: 0.6rem 1rem; border-radius: 4px; cursor: pointer; display: flex; align-items: center; justify-content: space-between; min-width: 150px; height: 42px; box-sizing: border-box;}
    .dropdown-menu { position: absolute; top: 110%; left: 0; background: #fff; border: 1px solid #ebeef5; border-radius: 4px; padding: 0.5rem; z-index: 10; box-shadow: 0 2px 12px rgba(0,0,0,0.1); min-width: 140px; display: flex; flex-direction: column; gap: 0.25rem; }
    .dropdown-item { background: none; border: none; padding: 0.5rem; text-align: left; cursor: pointer; }
    .dropdown-item:hover { background-color: #f5f7fa; color: #409eff; }

    /* --- Pagination --- */
    .pagination { display: flex; justify-content: space-between; align-items: center; margin-top: 1.5rem; }
    .btn-group button { background-color: #409eff; color: white; border: none; padding: 8px 16px; border-radius: 4px; cursor: pointer; margin-left: 10px; }
    button:disabled { opacity: 0.5; cursor: not-allowed; }

    /* --- Modal --- */
    .modal-overlay { position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.5); display: flex; justify-content: center; align-items: flex-start; padding-top: 5rem; z-index: 1000; }
    .modal-content { background: #fff; border-radius: 8px; width: 600px; max-width: 90%; box-shadow: 0 5px 15px rgba(0,0,0,0.3); display: flex; flex-direction: column; max-height: 90vh; overflow: hidden; }
    
    .modal-header { padding: 1rem 1.5rem; border-bottom: 1px solid #ebeef5; display: flex; justify-content: space-between; align-items: center; }
    .modal-header h3 { margin: 0; font-size: 1.2rem; }
    .close-btn { background: none; border: none; font-size: 1.5rem; cursor: pointer; color: #909399; line-height: 1; }
    
    .modal-body { padding: 1.5rem; overflow-y: auto; flex: 1; }
    .form-group { margin-bottom: 1rem; }
    .form-group label { display: block; margin-bottom: 0.5rem; font-weight: 600; color: #606266; font-size: 0.9rem; }
    .form-group input, .form-group textarea { width: 100%; padding: 0.6rem; border: 1px solid #dcdfe6; border-radius: 4px; font-family: inherit; font-size: 0.95rem; box-sizing: border-box; }
    .form-group input:focus, .form-group textarea:focus { border-color: #409eff; outline: none; }
    .readonly-box { background: #f5f7fa; padding: 0.6rem; border-radius: 4px; color: #606266; font-size: 0.9rem; border: 1px solid #ebeef5; }

    .modal-footer { padding: 1rem 1.5rem; border-top: 1px solid #ebeef5; display: flex; justify-content: flex-end; gap: 0.75rem; background: #fafafa; align-items: center; }
    
    .btn-primary { background-color: #409eff; color: white; border: none; padding: 0.6rem 1.2rem; border-radius: 4px; cursor: pointer; font-weight: 500; }
    .btn-success { background-color: #67c23a; color: white; border: none; padding: 0.6rem 1.2rem; border-radius: 4px; cursor: pointer; font-weight: 500; }
    .btn-secondary { background-color: #fff; border: 1px solid #dcdfe6; color: #606266; padding: 0.6rem 1.2rem; border-radius: 4px; cursor: pointer; font-weight: 500; }
    .btn-danger { background-color: #fff; color: #f56c6c; border: 1px solid #f56c6c; padding: 0.6rem 1.2rem; border-radius: 4px; cursor: pointer; font-weight: 500; }
    
    .btn-primary:hover { background-color: #66b1ff; }
    .btn-success:hover { background-color: #85ce61; }
    .btn-danger:hover { background-color: #f56c6c; color: white; }
</style>

<svelte:document 
    onclick={(e) => {
        if (!e.target.closest('.dropdown-container')) {
            isSentimentDropdownOpen = false;
            isExportDropdownOpen = false;
        }
    } 
}/>