window.NutriCharts = (() => {
    // Global defaults for premium glassmorphic look
    Chart.defaults.font.family = "'Outfit', sans-serif";
    Chart.defaults.color = "#94a3b8"; // muted text
    Chart.defaults.plugins.tooltip.backgroundColor = "rgba(15, 23, 42, 0.9)";
    Chart.defaults.plugins.tooltip.titleColor = "#f8fafc";
    Chart.defaults.plugins.tooltip.bodyColor = "#cbd5e1";
    Chart.defaults.plugins.tooltip.padding = 12;
    Chart.defaults.plugins.tooltip.cornerRadius = 8;
    Chart.defaults.plugins.tooltip.displayColors = false;

    // Custom plugin to draw the horizontal threshold line
    const thresholdLinePlugin = {
        id: 'thresholdLine',
        beforeDraw(chart, args, options) {
            if (!chart.config.options.thresholdValue) return;
            const threshold = chart.config.options.thresholdValue;
            const { ctx, chartArea: { top, right, bottom, left }, scales: { y } } = chart;
            
            // Check if threshold is within the current visible scale
            if (threshold >= y.min && threshold <= y.max) {
                const yPos = y.getPixelForValue(threshold);
                ctx.save();
                ctx.beginPath();
                ctx.moveTo(left, yPos);
                ctx.lineTo(right, yPos);
                ctx.lineWidth = 2;
                ctx.strokeStyle = "rgba(244, 63, 94, 0.5)"; // --accent-rose
                ctx.setLineDash([5, 5]);
                ctx.stroke();
                ctx.restore();
            }
        }
    };

    // Helper to destroy existing chart instance on a canvas if it exists
    const prepareCanvas = (canvasId) => {
        const canvas = document.getElementById(canvasId);
        if (!canvas) return null;
        // Chart.js attaches the instance to the canvas
        const existingChart = Chart.getChart(canvasId);
        if (existingChart) existingChart.destroy();
        return canvas;
    };

    const renderBarChart = (canvasId, data, color = "#21543d", threshold = null, overLimitColor = "#f43f5e") => {
        const canvas = prepareCanvas(canvasId);
        if (!canvas || !data.length) return;

        const labels = data.map(d => d.label);
        const values = data.map(d => d.value);

        // Map colors conditionally if threshold exists
        const backgroundColors = values.map(val => (threshold !== null && val > threshold) ? overLimitColor : color);

        new Chart(canvas, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Amount',
                    data: values,
                    backgroundColor: backgroundColors,
                    borderRadius: 4,
                    barPercentage: 0.6
                }]
            },
            options: {
                thresholdValue: threshold,
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    x: {
                        grid: { display: false, drawBorder: false }
                    },
                    y: {
                        beginAtZero: true,
                        grid: { color: "rgba(255,255,255,0.05)", drawBorder: false },
                        suggestedMax: threshold ? threshold * 1.2 : undefined
                    }
                },
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            label: (context) => `Value: ${context.parsed.y}`
                        }
                    }
                }
            },
            plugins: [thresholdLinePlugin]
        });
    };

    const renderLineChart = (canvasId, data, color = "#235a82") => {
        const canvas = prepareCanvas(canvasId);
        if (!canvas || !data.length) return;

        const labels = data.map(d => d.label);
        const values = data.map(d => d.value);

        new Chart(canvas, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Score',
                    data: values,
                    borderColor: color,
                    backgroundColor: color,
                    tension: 0.3, // smooth curves
                    borderWidth: 3,
                    pointRadius: 4,
                    pointHoverRadius: 6
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    x: {
                        grid: { display: false, drawBorder: false }
                    },
                    y: {
                        beginAtZero: true,
                        grid: { color: "rgba(255,255,255,0.05)", drawBorder: false }
                    }
                },
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            label: (context) => `Score: ${context.parsed.y}`
                        }
                    }
                }
            }
        });
    };

    const renderDonutChart = (canvasId, data, colors) => {
        const canvas = prepareCanvas(canvasId);
        if (!canvas || !data.length) return;

        const labels = data.map(d => d.label);
        const values = data.map(d => d.value);

        new Chart(canvas, {
            type: 'doughnut',
            data: {
                labels: labels,
                datasets: [{
                    data: values,
                    backgroundColor: colors,
                    borderWidth: 0,
                    hoverOffset: 4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: '70%', // Donut hole size
                plugins: {
                    legend: {
                        position: 'right',
                        labels: {
                            color: '#94a3b8',
                            font: { family: "'Outfit', sans-serif", size: 12 },
                            usePointStyle: true,
                            padding: 20
                        }
                    },
                    tooltip: {
                        callbacks: {
                            label: (context) => ` ${context.label}: ${context.parsed}`
                        }
                    }
                }
            }
        });
    };

    return { renderBarChart, renderLineChart, renderDonutChart };
})();
