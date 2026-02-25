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
    let showMovingAverage = $state(false);

    // Состояния видимости (для анимации)
    let isStatsVisible = $state(false);
    let isSentimentVisible = $state(false);
    let isDevicesVisible = $state(false);
    let isDynamicsVisible = $state(false);

    // Refs (привязка к DOM элементам)
    let statsSection = $state();
    let sentimentSection = $state();
    let devicesSection = $state();
    let dynamicsSection = $state();

    // Инстансы графиков
    let sentimentChartInstance = null;
    let devicesChartInstance = null;
    let dynamicsChartInstance = null;

    // --- Загрузка данных ---
    onMount(async () => {
        try {
            const response = await fetch('/api/get_tickets');
            tickets = await response.json();
        } catch (e) {
            console.error(e);
        } finally {
            isLoading = false; // Это триггерит появление элементов в DOM
        }
    });

    // --- ИСПРАВЛЕНИЕ: Observer запускается только когда элементы появятся ---
    $effect(() => {
        // Если данные еще грузятся, элементы не существуют, выходим
        if (isLoading) return;

        // Функция настройки Observer
        const setupObserver = () => {
            const observer = new IntersectionObserver(
                (entries) => {
                    entries.forEach(entry => {
                        if (entry.isIntersecting) {
                            // Определяем, какая секция стала видимой
                            const id = entry.target.id;
                            if (id === 'stats') isStatsVisible = true;
                            if (id === 'sentiment') isSentimentVisible = true;
                            if (id === 'devices') isDevicesVisible = true;
                            if (id === 'dynamics') isDynamicsVisible = true;
                            
                            observer.unobserve(entry.target);
                        }
                    });
                },
                { threshold: 0.1 }
            );

            // Подписываемся на элементы. $state refs обновляются сразу после рендера
            if (statsSection) observer.observe(statsSection);
            if (sentimentSection) observer.observe(sentimentSection);
            if (devicesSection) observer.observe(devicesSection);
            if (dynamicsSection) observer.observe(dynamicsSection);

            return observer;
        };

        const observer = setupObserver();

        // Cleanup функция (выполнится при уничтожении компонента или перезапуске эффекта)
        return () => observer.disconnect();
    });

    // --- Обработка данных ---
    let totalTickets = $derived(tickets.length);
    let positivePercent = $derived(() => {
        if (!tickets.length) return 0;
        const count = tickets.filter(t => t.sentiment === 'позитивный').length;
        return Math.round((count / tickets.length) * 100);
    });

    let sentimentData = $derived({
        labels: ['Позитивный', 'Негативный', 'Нейтральный'],
        datasets: [{
            data: [
                tickets.filter(t => t.sentiment === 'позитивный').length,
                tickets.filter(t => t.sentiment === 'негативный').length,
                tickets.filter(t => t.sentiment === 'нейтральный').length
            ],
            backgroundColor: ['#67c23a', '#f56c6c', '#909399'],
            borderWidth: 0
        }]
    });

    let devicesData = $derived(() => {
        const counts = {};
        tickets.forEach(t => counts[t.device_type] = (counts[t.device_type] || 0) + 1);
        const sorted = Object.entries(counts).sort((a, b) => b[1] - a[1]).slice(0, 5);
        return {
            labels: sorted.map(i => i[0]),
            datasets: [{
                label: 'Кол-во',
                data: sorted.map(i => i[1]),
                backgroundColor: '#409eff',
                borderRadius: 4
            }]
        };
    });

    let dynamicsData = $derived(() => {
        const counts = {};
        tickets.forEach(t => {
            const key = t.date.split(' ')[0].slice(5); // "10-25"
            counts[key] = (counts[key] || 0) + 1;
        });

        const sortedLabels = Object.keys(counts).sort();
        const values = sortedLabels.map(l => counts[l]);

        const movingAvg = values.map((v, i) => i === 0 ? v : (v + values[i-1]) / 2);

        const datasets = [
            {
                label: 'Обращения',
                data: values,
                borderColor: '#409eff',
                backgroundColor: 'rgba(64, 158, 255, 0.1)',
                fill: true,
                tension: 0.4
            }
        ];

        if (showMovingAverage) {
            datasets.push({
                label: 'Скользящее среднее',
                data: movingAvg,
                borderColor: '#e6a23c',
                borderDash: [5, 5],
                borderWidth: 2,
                pointRadius: 0,
                fill: false,
                tension: 0.4
            });
        }

        return { labels: sortedLabels, datasets };
    });

    // --- Рендеринг графиков ---
    
    $effect(() => {
        if (isSentimentVisible && sentimentSection) {
            if (sentimentChartInstance) sentimentChartInstance.destroy();
            const ctx = sentimentSection.querySelector('canvas');
            if (ctx) {
                sentimentChartInstance = new Chart(ctx, {
                    type: 'doughnut',
                    data: sentimentData,
                    options: { responsive: true, maintainAspectRatio: false, animation: { duration: 800 } }
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
                    options: { responsive: true, maintainAspectRatio: false, animation: { duration: 800 } }
                });
            }
        }
    });

    $effect(() => {
        // Перерисовываем график при изменении данных или видимости
        if (isDynamicsVisible && dynamicsSection) {
            if (dynamicsChartInstance) dynamicsChartInstance.destroy();
            const ctx = dynamicsSection.querySelector('canvas');
            if (ctx) {
                dynamicsChartInstance = new Chart(ctx, {
                    type: 'line',
                    data: dynamicsData(),
                    options: { responsive: true, maintainAspectRatio: false, animation: { duration: 500 } }
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
        <!-- Секция: Общая статистика -->
        <!-- bind:this={statsSection} привязывает элемент к переменной -->
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

        <!-- Сетка графиков -->
        <div class="grid">
            
            <!-- График 1: Настроение -->
            <div id="sentiment" bind:this={sentimentSection} class="card chart-card" class:visible={isSentimentVisible}>
                <h3>Эмоциональный окрас</h3>
                <div class="chart-container">
                    {#if isSentimentVisible}
                        <canvas></canvas>
                    {/if}
                </div>
            </div>

            <!-- График 2: Типы приборов -->
            <div id="devices" bind:this={devicesSection} class="card chart-card" class:visible={isDevicesVisible}>
                <h3>Типы приборов (ТОП)</h3>
                <div class="chart-container">
                    {#if isDevicesVisible}
                        <canvas></canvas>
                    {/if}
                </div>
            </div>

            <!-- График 3: Динамика -->
            <div id="dynamics" bind:this={dynamicsSection} class="card chart-card full-width" class:visible={isDynamicsVisible}>
                <div class="chart-header">
                    <h3>Динамика обращений</h3>
                    <label class="toggle-label">
                        <input type="checkbox" bind:checked={showMovingAverage} />
                        Показать скользящее среднее
                    </label>
                </div>
                <div class="chart-container tall">
                    {#if isDynamicsVisible}
                        <canvas></canvas>
                    {/if}
                </div>
            </div>

        </div>
    {/if}
</div>

<style>
    :global(body) { background-color: #f4f6f9; font-family: sans-serif; margin: 0; }
    .container { max-width: 1200px; margin: 0 auto; padding: 2rem; }
    header { margin-bottom: 2rem; }
    h1 { margin: 0.5rem 0 0; color: #2c3e50; }
    .back-link { color: #409eff; text-decoration: none; font-size: 0.9rem; }

    /* Карточки и анимации */
    .card {
        background: white;
        border-radius: 8px;
        padding: 1.5rem;
        box-shadow: 0 2px 12px rgba(0,0,0,0.05);
        opacity: 0;
        transform: translateY(20px);
        transition: opacity 0.6s ease, transform 0.6s ease;
    }
    
    .card.visible {
        opacity: 1;
        transform: translateY(0);
    }

    .grid {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 1.5rem;
    }

    .full-width { grid-column: 1 / -1; }

    /* Статистика */
    .stats-row { display: flex; gap: 2rem; margin-bottom: 1.5rem; }
    .stat-item { text-align: center; flex: 1; }
    .stat-value { font-size: 2rem; font-weight: bold; color: #333; }
    .stat-value.positive { color: #67c23a; }
    .stat-label { color: #909399; font-size: 0.9rem; margin-top: 0.5rem; }

    /* Графики */
    .chart-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem; }
    h3 { margin: 0; font-size: 1.1rem; color: #606266; }
    
    .chart-container { position: relative; height: 250px; }
    .chart-container.tall { height: 350px; }

    .toggle-label {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        font-size: 0.85rem;
        color: #606266;
        cursor: pointer;
    }

    @media (max-width: 768px) {
        .grid { grid-template-columns: 1fr; }
        .stats-row { flex-direction: column; gap: 1rem; }
    }
</style>