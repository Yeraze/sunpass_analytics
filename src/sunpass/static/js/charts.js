// Disable datalabels globally — only enable per-chart for doughnuts
Chart.defaults.plugins.datalabels = false;

const CHART_COLORS = [
    '#004b87', '#f7941d', '#2e7d32', '#c62828', '#6a1b9a',
    '#00838f', '#ef6c00', '#4527a0', '#ad1457', '#00695c',
    '#1565c0', '#ff8f00', '#6d4c41', '#546e7a', '#d84315'
];

// Global stable color map: label -> color (loaded once from server)
let STABLE_COLORS = {};

async function loadStableColors() {
    try {
        const response = await fetch('/api/color-map');
        STABLE_COLORS = await response.json();
    } catch (e) {
        console.warn('Could not load color map:', e);
    }
}

function getStableColor(label, fallbackIndex) {
    if (STABLE_COLORS[label]) return STABLE_COLORS[label];
    return CHART_COLORS[fallbackIndex % CHART_COLORS.length];
}

function getStableColors(labels) {
    return labels.map((l, i) => getStableColor(l, i));
}

function createBarChart(canvasId, labels, data, label, horizontal = false) {
    const ctx = document.getElementById(canvasId);
    if (!ctx) return null;

    return new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: label,
                data: data,
                backgroundColor: getStableColors(labels),
                borderWidth: 0,
                borderRadius: 4,
            }]
        },
        options: {
            indexAxis: horizontal ? 'y' : 'x',
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        label: (ctx) => `$${ctx.parsed[horizontal ? 'x' : 'y'].toFixed(2)}`
                    }
                }
            },
            scales: {
                [horizontal ? 'x' : 'y']: {
                    ticks: {
                        callback: (val) => '$' + val.toFixed(0)
                    }
                }
            }
        }
    });
}

function createLineChart(canvasId, labels, data, label) {
    const ctx = document.getElementById(canvasId);
    if (!ctx) return null;

    return new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: label,
                data: data,
                borderColor: '#004b87',
                backgroundColor: 'rgba(0, 75, 135, 0.1)',
                fill: true,
                tension: 0.3,
                pointRadius: 4,
                pointHoverRadius: 6,
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                tooltip: {
                    callbacks: {
                        label: (ctx) => `$${ctx.parsed.y.toFixed(2)}`
                    }
                }
            },
            scales: {
                y: {
                    ticks: {
                        callback: (val) => '$' + val.toFixed(0)
                    }
                }
            }
        }
    });
}

function createPieChart(canvasId, labels, data, label) {
    const ctx = document.getElementById(canvasId);
    if (!ctx) return null;

    const total = data.reduce((a, b) => a + b, 0);

    return new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: labels,
            datasets: [{
                label: label,
                data: data,
                backgroundColor: getStableColors(labels),
                borderWidth: 2,
                borderColor: '#fff',
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                tooltip: {
                    callbacks: {
                        label: (ctx) => `${ctx.label}: $${ctx.parsed.toFixed(2)}`
                    }
                },
                datalabels: {
                    color: '#fff',
                    font: { weight: 'bold', size: 11 },
                    textStrokeColor: 'rgba(0,0,0,0.5)',
                    textStrokeWidth: 2,
                    formatter: (value, ctx) => {
                        const pct = (value / total) * 100;
                        if (pct < 8) return '';
                        const name = ctx.chart.data.labels[ctx.dataIndex];
                        return `${name}\n$${value.toFixed(0)}`;
                    },
                    textAlign: 'center',
                }
            }
        },
        plugins: [ChartDataLabels],
    });
}

function createStackedBarChart(canvasId, labels, datasets) {
    const ctx = document.getElementById(canvasId);
    if (!ctx) return null;

    const chartDatasets = datasets.map((ds, i) => ({
        label: ds.label,
        data: ds.data,
        backgroundColor: getStableColor(ds.label, i),
        borderWidth: 0,
        borderRadius: 2,
    }));

    return new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: chartDatasets,
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: true,
                    position: 'top',
                    onClick: function(e, legendItem, legend) {
                        const index = legendItem.datasetIndex;
                        const ci = legend.chart;
                        const meta = ci.getDatasetMeta(index);
                        meta.hidden = meta.hidden === null ? !ci.data.datasets[index].hidden : null;
                        ci.update();
                    },
                    labels: {
                        usePointStyle: true,
                        pointStyle: 'rect',
                    }
                },
                tooltip: {
                    callbacks: {
                        label: (ctx) => `${ctx.dataset.label}: $${ctx.parsed.y.toFixed(2)}`
                    }
                }
            },
            scales: {
                x: {
                    stacked: true,
                },
                y: {
                    stacked: true,
                    ticks: {
                        callback: (val) => '$' + val.toFixed(0)
                    }
                }
            }
        }
    });
}

async function loadChartData(url, params = {}) {
    const query = new URLSearchParams(params).toString();
    const fullUrl = query ? `${url}?${query}` : url;
    const response = await fetch(fullUrl);
    return await response.json();
}
