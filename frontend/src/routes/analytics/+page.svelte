<script>
    import { onMount } from 'svelte';
    import { browser } from '$app/environment';
    import { Chart, registerables } from 'chart.js';

    if (browser) {
        Chart.register(...registerables);
    }

    // --- Состояния ---
    let tickets = $state([]);
    let isLoading = $state(true);

    // --- Настройки графиков ---
    let timeChartMode = $state('regular'); // 'regular' or 'stacked'
    let showTrend = $state(false);
    let showThreshold = $state(false);
    let thresholdValue = $state(10);

    // Видимость секций
    let isStatsVisible = $state(false);
    let isSentimentVisible = $state(false);
    let isDevicesVisible = $state(false);
    let isCompaniesVisible = $state(false);
    let isDynamicsVisible = $state(false);

    // Refs
    let statsSection = $state();
    let sentimentSection = $state();
    let devicesSection = $state();
    let companiesSection = $state();
    let dynamicsSection = $state();

    // Инстансы графиков
    let sentimentChartInstance = null;
    let devicesChartInstance = null;
    let companiesChartInstance = null;
    let dynamicsChartInstance = null;

    // --- Жизненный цикл ---
    onMount(async () => {
        try {
            const response = await fetch('/api/get_tickets');
            tickets = await response.json();
        } catch (e) {
            console.error(e);
        } finally {
            isLoading = false;
        }
    });

    // Observer Effect
    $effect(() => {
        if (isLoading) return;
        const observer = new IntersectionObserver(
            (entries) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        const id = entry.target.id;
                        if (id === 'stats') isStatsVisible = true;
                        if (id === 'sentiment') isSentimentVisible = true;
                        if (id === 'devices') isDevicesVisible = true;
                        if (id === 'companies') isCompaniesVisible = true;
                        if (id === 'dynamics') isDynamicsVisible = true;
                        observer.unobserve(entry.target);
                    }
                });
            },
            { threshold: 0.1 }
        );
        
        if (statsSection) observer.observe(statsSection);
        if (sentimentSection) observer.observe(sentimentSection);
        if (devicesSection) observer.observe(devicesSection);
        if (companiesSection) observer.observe(companiesSection);
        if (dynamicsSection) observer.observe(dynamicsSection);

        return () => observer.disconnect();
    });

    // --- Обработка данных ---

    // 1. Статистика
    let totalTickets = $derived(tickets.length);
    let positivePercent = $derived(() => {
        if (!tickets.length) return 0;
        const count = tickets.filter(t => t.sentiment === 'позитивный').length;
        return Math.round((count / tickets.length) * 100);
    });

    // 2. Круговая диаграмма (Настроение)
    let sentimentData = $derived({
        labels: ['Позитивный', 'Негативный', 'Нейтральный'],
        datasets: [{
            data: [
                tickets.filter(t => t.sentiment === 'позитивный').length,
                tickets.filter(t => t.sentiment === 'негативный').length,
                tickets.filter(t => t.sentiment === 'нейтральный').length
            ],
            backgroundColor: ['#67c23a', '#f56c6c', '#909399'],
            borderWidth: 0,
            hoverOffset: 15 // Эффект "выпрыгивания" при наведении
        }]
    });

    // 3. График приборов
    let devicesData = $derived(() => {
        const counts = {};
        tickets.forEach(t => {
            counts[t.device_type] = (counts[t.device_type] || 0) + 1;
        });
        // Сортировка и срез ТОП-5
        const sorted = Object.entries(counts).sort((a, b) => b[1] - a[1]).slice(0, 5);
        
        return {
            labels: sorted.map(i => i[0]),
            datasets: [{
                label: 'Кол-во',
                data: sorted.map(i => i[1]),
                backgroundColor: [
                    'rgba(59, 130, 246, 0.7)',
                    'rgba(16, 185, 129, 0.7)',
                    'rgba(245, 158, 11, 0.7)',
                    'rgba(239, 68, 68, 0.7)',
                    'rgba(139, 92, 246, 0.7)'
                ],
                borderWidth: 0,
                borderRadius: 6
            }]
        };
    });

    // 4. График предприятий
    let companiesData = $derived(() => {
        const counts = {};
        tickets.forEach(t => {
            counts[t.object] = (counts[t.object] || 0) + 1;
        });
        const sorted = Object.entries(counts).sort((a, b) => b[1] - a[1]).slice(0, 5);
        
        return {
            labels: sorted.map(i => i[0]),
            datasets: [{
                label: 'Кол-во',
                data: sorted.map(i => i[1]),
                backgroundColor: 'rgba(16, 185, 129, 0.7)', // Бирюзовый
                borderWidth: 0,
                borderRadius: 6
            }]
        };
    });

    // 5. Данные для временного графика
    let dynamicsData = $derived(() => {
        const counts = {};
        
        tickets.forEach(t => {
            const key = t.date.split(' ')[0].slice(5); // MM-DD
            if (!counts[key]) counts[key] = { total: 0, позитивный: 0, негативный: 0, нейтральный: 0 };
            counts[key].total++;
            counts[key][t.sentiment]++;
        });

        const sortedLabels = Object.keys(counts).sort();
        const values = sortedLabels.map(l => counts[l].total);

        let datasets = [];

        if (timeChartMode === 'regular') {
            datasets.push({
                label: 'Обращения',
                data: values,
                borderColor: '#3b82f6',
                backgroundColor: 'rgba(59, 130, 246, 0.1)',
                fill: true,
                tension: 0.4, // Плавность
            });
        } else {
            // Стековый режим
            const sentiments = [
                { key: 'позитивный', color: '#67c23a', bg: 'rgba(103, 194, 58, 0.7)' },
                { key: 'негативный', color: '#f56c6c', bg: 'rgba(245, 108, 108, 0.7)' },
                { key: 'нейтральный', color: '#909399', bg: 'rgba(144, 147, 153, 0.7)' }
            ];

            sentiments.forEach(s => {
                datasets.push({
                    label: s.key.charAt(0).toUpperCase() + s.key.slice(1),
                    data: sortedLabels.map(l => counts[l][s.key]),
                    backgroundColor: s.bg,
                    borderColor: s.color,
                    borderWidth: 1,
                    fill: true,
                    tension: 0.4, // ИСПРАВЛЕНИЕ: Добавляем плавность для стекового режима
                });
            });
        }

        // Линия тренда
        if (showTrend && values.length > 1) {
            const n = values.length;
            let sumX = 0, sumY = 0, sumXY = 0, sumX2 = 0;
            
            values.forEach((y, x) => {
                sumX += x; sumY += y; sumXY += x * y; sumX2 += x * x;
            });

            const slope = (n * sumXY - sumX * sumY) / (n * sumX2 - sumX * sumX);
            const intercept = (sumY - slope * sumX) / n;
            const trendData = values.map((_, x) => slope * x + intercept);

            datasets.push({
                label: 'Тренд',
                data: trendData,
                borderColor: '#f59e0b',
                borderWidth: 2,
                borderDash: [5, 5],
                pointRadius: 0,
                fill: false,
                type: 'line'
            });
        }

        // Линия порога
        if (showThreshold) {
            datasets.push({
                label: 'Порог нагрузки',
                data: Array(values.length).fill(thresholdValue),
                borderColor: '#ef4444',
                borderWidth: 2,
                borderDash: [10, 5],
                pointRadius: 0,
                fill: false,
                type: 'line'
            });
        }

        return { labels: sortedLabels, datasets };
    });

    // --- Chart Rendering Effects ---
    
    $effect(() => {
        if (isSentimentVisible && sentimentSection) {
            if (sentimentChartInstance) sentimentChartInstance.destroy();
            const ctx = sentimentSection.querySelector('canvas');
            if (ctx) {
                sentimentChartInstance = new Chart(ctx, {
                    type: 'doughnut',
                    data: sentimentData,
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        cutout: '60%',
                        plugins: {
                            legend: { position: 'bottom', labels: { boxWidth: 12, padding: 20 } }
                        },
                        animation: { animateScale: true, duration: 800 }
                    }
                });
            }
        }
    });

    $effect(() => {
        if (isDevicesVisible && devicesSection) {
            if (devicesChartInstance) devicesChartInstance.destroy();
            const ctx = devicesSection.querySelector('canvas');
            if (ctx) {
                devicesChartInstance = new Chart(ctx, {
                    type: 'bar',
                    data: devicesData(),
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        scales: { x: { grid: { display: false } }, y: { grid: { color: 'rgba(0,0,0,0.05)' } } },
                        plugins: { legend: { display: false } },
                        animation: { duration: 800 }
                    }
                });
            }
        }
    });

    $effect(() => {
        if (isCompaniesVisible && companiesSection) {
            if (companiesChartInstance) companiesChartInstance.destroy();
            const ctx = companiesSection.querySelector('canvas');
            if (ctx) {
                companiesChartInstance = new Chart(ctx, {
                    type: 'bar',
                    data: companiesData(),
                    options: {
                        indexAxis: 'y', // Горизонтальная
                        responsive: true,
                        maintainAspectRatio: false,
                        scales: { x: { grid: { display: false } }, y: { grid: { display: false } } },
                        plugins: { legend: { display: false } },
                        animation: { duration: 800, delay: 200 }
                    }
                });
            }
        }
    });

    $effect(() => {
        if (isDynamicsVisible && dynamicsSection) {
            if (dynamicsChartInstance) dynamicsChartInstance.destroy();
            const ctx = dynamicsSection.querySelector('canvas');
            if (ctx) {
                dynamicsChartInstance = new Chart(ctx, {
                    type: 'line',
                    data: dynamicsData(),
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        interaction: { mode: 'index', intersect: false },
                        scales: {
                            y: { 
                                beginAtZero: true,
                                stacked: timeChartMode === 'stacked',
                                grid: { color: 'rgba(0,0,0,0.05)' }
                            },
                            x: { grid: { display: false } }
                        },
                        plugins: {
                            legend: { display: true, position: 'bottom' },
                            tooltip: {
                                backgroundColor: 'rgba(0,0,0,0.8)',
                                titleFont: { size: 14 },
                                bodyFont: { size: 12 },
                                padding: 10,
                                cornerRadius: 8
                            }
                        },
                        animation: { duration: 500 }
                    }
                });
            }
        }
    });
</script>

<svelte:head>
    <title>Аналитика | Газовая служба</title>
</svelte:head>

<div class="container">
    <header>
        <a href="/" class="back-link">← Назад к заявкам</a>
        <h1>Аналитика обращений</h1>
    </header>

    {#if isLoading}
        <div class="loader">Загрузка данных...</div>
    {:else}
        <!-- Секция: Статистика -->
        <div id="stats" bind:this={statsSection} class="card stats-row" class:visible={isStatsVisible}>
            <div class="stat-item">
                <div class="stat-value">{totalTickets}</div>
                <div class="stat-label">Всего обращений</div>
            </div>
            <div class="stat-item">
                <div class="stat-value positive">{positivePercent()}%</div>
                <div class="stat-label">Позитивных</div>
            </div>
        </div>

        <!-- Сетка графиков: 3 колонки -->
        <div class="grid-top">
            <!-- График: Настроение -->
            <div id="sentiment" bind:this={sentimentSection} class="card chart-card" class:visible={isSentimentVisible}>
                <h3>Эмоциональный окрас</h3>
                <div class="chart-container">
                    {#if isSentimentVisible}<canvas></canvas>{/if}
                </div>
            </div>

            <!-- График: Приборы (Вернули) -->
            <div id="devices" bind:this={devicesSection} class="card chart-card" class:visible={isDevicesVisible}>
                <h3>Типы приборов (ТОП)</h3>
                <div class="chart-container">
                    {#if isDevicesVisible}<canvas></canvas>{/if}
                </div>
            </div>

            <!-- График: Предприятия -->
            <div id="companies" bind:this={companiesSection} class="card chart-card" class:visible={isCompaniesVisible}>
                <h3>ТОП Предприятий</h3>
                <div class="chart-container">
                    {#if isCompaniesVisible}<canvas></canvas>{/if}
                </div>
            </div>
        </div>

        <!-- График: Динамика (Полная ширина) -->
        <div id="dynamics" bind:this={dynamicsSection} class="card chart-card full-width" class:visible={isDynamicsVisible}>
            <div class="chart-header">
                <h3>Динамика обращений</h3>
                
                <!-- Панель управления -->
                <div class="controls-panel">
                    <div class="toggle-group">
                        <button 
                            class:active={timeChartMode === 'regular'} 
                            onclick={() => timeChartMode = 'regular'}
                        >Обычный</button>
                        <button 
                            class:active={timeChartMode === 'stacked'} 
                            onclick={() => timeChartMode = 'stacked'}
                        >Стековый</button>
                    </div>

                    <label class="checkbox-pill">
                        <input type="checkbox" bind:checked={showTrend} />
                        <span>Тренд</span>
                    </label>

                    <label class="checkbox-pill">
                        <input type="checkbox" bind:checked={showThreshold} />
                        <span>Порог</span>
                    </label>
                    
                    {#if showThreshold}
                        <input type="number" bind:value={thresholdValue} class="threshold-input" min="0" />
                    {/if}
                </div>
            </div>

            <div class="chart-container tall">
                {#if isDynamicsVisible}<canvas></canvas>{/if}
            </div>
        </div>

    {/if}
</div>

<style>
    /* --- Layout --- */
    :global(body) { background-color: #f4f6f9; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 0; }
    .container { max-width: 1200px; margin: 0 auto; padding: 2rem; }
    header { margin-bottom: 2rem; }
    h1 { margin: 0.5rem 0 0; color: #2c3e50; font-size: 1.5rem; }
    .back-link { color: #3b82f6; text-decoration: none; font-size: 0.9rem; font-weight: 500; }

    /* --- Cards & Animation --- */
    .card {
        background: white;
        border-radius: 12px;
        padding: 1.5rem;
        box-shadow: 0 2px 15px rgba(0,0,0,0.04);
        opacity: 0;
        transform: translateY(20px);
        transition: all 0.6s cubic-bezier(0.22, 1, 0.36, 1);
        border: 1px solid rgba(0,0,0,0.03);
    }
    .card.visible {
        opacity: 1;
        transform: translateY(0);
    }

    /* Grid Top Row: 3 columns */
    .grid-top {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 1.5rem;
        margin-top: 1.5rem;
    }

    .full-width { 
        grid-column: 1 / -1; 
        margin-top: 1.5rem;
    }

    /* --- Stats --- */
    .stats-row { display: flex; gap: 2rem; }
    .stat-item { text-align: center; flex: 1; padding: 1rem; background: #fafbfc; border-radius: 8px; }
    .stat-value { font-size: 2rem; font-weight: 700; color: #1f2937; }
    .stat-value.positive { color: #10b981; }
    .stat-label { color: #6b7280; font-size: 0.85rem; margin-top: 0.25rem; text-transform: uppercase; letter-spacing: 0.5px; }

    /* --- Charts --- */
    h3 { margin: 0 0 1rem; font-size: 1.1rem; color: #374151; font-weight: 600; }
    .chart-container { position: relative; height: 250px; }
    .chart-container.tall { height: 350px; }

    /* --- Controls Panel --- */
    .chart-header { 
        display: flex; 
        justify-content: space-between; 
        align-items: center; 
        margin-bottom: 1.5rem;
        flex-wrap: wrap;
        gap: 1rem;
    }

    .controls-panel {
        display: flex;
        align-items: center;
        gap: 0.75rem;
        flex-wrap: wrap;
    }

    .toggle-group {
        display: flex;
        background: #f3f4f6;
        border-radius: 8px;
        padding: 2px;
    }
    
    .toggle-group button {
        background: transparent;
        border: none;
        padding: 6px 12px;
        font-size: 0.8rem;
        cursor: pointer;
        border-radius: 6px;
        color: #6b7280;
        font-weight: 500;
        transition: all 0.2s;
    }

    .toggle-group button.active {
        background: white;
        color: #3b82f6;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }

    .checkbox-pill {
        display: flex;
        align-items: center;
        cursor: pointer;
    }
    
    .checkbox-pill input { display: none; }
    
    .checkbox-pill span {
        padding: 6px 12px;
        background: #f3f4f6;
        border-radius: 6px;
        font-size: 0.8rem;
        color: #6b7280;
        transition: all 0.2s;
        border: 1px solid transparent;
    }

    .checkbox-pill input:checked + span {
        background: #ecfdf5;
        color: #10b981;
        border-color: #d1fae5;
    }

    .threshold-input {
        width: 50px;
        padding: 4px 8px;
        border: 1px solid #e5e7eb;
        border-radius: 4px;
        font-size: 0.8rem;
        text-align: center;
        outline: none;
    }
    
    .threshold-input:focus { border-color: #3b82f6; }

    @media (max-width: 992px) {
        .grid-top { grid-template-columns: 1fr 1fr; }
    }

    @media (max-width: 768px) {
        .grid-top { grid-template-columns: 1fr; }
        .chart-header { flex-direction: column; align-items: flex-start; }
    }
</style>