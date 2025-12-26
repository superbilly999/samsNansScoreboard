(function () {
  const chartRegistry = {};

  function parseData(el, attr, fallback) {
    if (!el) {
      return fallback;
    }
    const raw = el.getAttribute(attr);
    if (!raw) {
      return fallback;
    }
    try {
      return JSON.parse(raw);
    } catch (error) {
      return fallback;
    }
  }

  function destroyChart(key) {
    if (chartRegistry[key]) {
      chartRegistry[key].destroy();
      delete chartRegistry[key];
    }
  }

  function applyDefaults() {
    if (!window.Chart) {
      return;
    }
    Chart.defaults.font.family = '"Space Grotesk", "Trebuchet MS", sans-serif';
    Chart.defaults.color = "#6c635b";
    if (window.ChartZoom) {
      Chart.register(window.ChartZoom);
    }
  }

  function buildTrendChart() {
    const canvas = document.getElementById("trend-chart");
    if (!canvas || !window.Chart) {
      return;
    }

    const labels = parseData(canvas, "data-labels", []);
    const rawDatasets = parseData(canvas, "data-datasets", []);
    const datasets = rawDatasets.map((dataset) => ({
      ...dataset,
      tension: 0.35,
      pointRadius: 3,
      pointHoverRadius: 5,
      pointHitRadius: 10,
      borderWidth: 2,
      fill: false,
    }));

    destroyChart("trend");
    const chart = new Chart(canvas, {
      type: "line",
      data: {
        labels,
        datasets,
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: {
          mode: "nearest",
          intersect: false,
        },
        plugins: {
          legend: {
            position: "bottom",
            labels: {
              usePointStyle: true,
              boxWidth: 10,
            },
          },
          tooltip: {
            callbacks: {
              label: (context) => `${context.dataset.label}: ${context.parsed.y}`,
            },
          },
          zoom: {
            pan: {
              enabled: false,
            },
            zoom: {
              wheel: {
                enabled: false,
              },
              pinch: {
                enabled: false,
              },
              drag: {
                enabled: false,
              },
              mode: "x",
            },
          },
        },
        scales: {
          y: {
            beginAtZero: true,
            grid: {
              color: "#efe4d6",
            },
            ticks: {
              precision: 0,
            },
          },
          x: {
            grid: {
              display: false,
            },
          },
        },
      },
    });
    chartRegistry.trend = chart;
  }

  function buildBarChart() {
    const canvas = document.getElementById("round-bar-chart");
    if (!canvas || !window.Chart) {
      return;
    }

    const labels = parseData(canvas, "data-labels", []);
    const values = parseData(canvas, "data-values", []);
    const colors = parseData(canvas, "data-colors", []);

    destroyChart("roundBar");
    chartRegistry.roundBar = new Chart(canvas, {
      type: "bar",
      data: {
        labels,
        datasets: [
          {
            label: "Last round",
            data: values,
            backgroundColor: colors,
            borderRadius: 8,
            barThickness: 14,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        indexAxis: "y",
        plugins: {
          legend: {
            display: false,
          },
          tooltip: {
            callbacks: {
              label: (context) => `${context.parsed.x} points`,
            },
          },
        },
        scales: {
          x: {
            beginAtZero: true,
            grid: {
              color: "#efe4d6",
            },
            ticks: {
              precision: 0,
            },
          },
          y: {
            grid: {
              display: false,
            },
          },
        },
      },
    });
  }

  function buildInsightCharts() {
    applyDefaults();
    buildTrendChart();
    buildBarChart();
  }

  function handleChartControls(event) {
    const button = event.target.closest("[data-chart-action]");
    if (!button) {
      return;
    }
    const action = button.getAttribute("data-chart-action");
    const chartKey = button.getAttribute("data-chart-target") || "trend";
    const chart = chartRegistry[chartKey];
    if (!chart) {
      return;
    }
    if (action === "zoom-in" && typeof chart.zoom === "function") {
      chart.zoom({ x: 1.2, y: 1 });
    }
    if (action === "zoom-out" && typeof chart.zoom === "function") {
      chart.zoom({ x: 0.8, y: 1 });
    }
    if (action === "reset" && typeof chart.resetZoom === "function") {
      chart.resetZoom();
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", buildInsightCharts);
  } else {
    buildInsightCharts();
  }

  document.body.addEventListener("htmx:afterSwap", buildInsightCharts);
  document.body.addEventListener("click", handleChartControls);
})();
