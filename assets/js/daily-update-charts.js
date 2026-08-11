// assets/js/daily-update-charts.js
// Interactive charts for automated daily English OpenList update posts.

(function () {
  function hasUsableSeries(series) {
    return Boolean(
      series &&
      Array.isArray(series.labels) &&
      Array.isArray(series.values) &&
      series.labels.length > 0 &&
      series.labels.length === series.values.length
    );
  }

  function renderChart(canvasId, series, color, xTitle) {
    const canvas = document.getElementById(canvasId);
    if (!canvas || !hasUsableSeries(series) || typeof Chart === 'undefined') {
      return;
    }

    new Chart(canvas, {
      type: 'bar',
      data: {
        labels: series.labels,
        datasets: [{
          label: 'Word Count',
          data: series.values,
          backgroundColor: color.background,
          borderColor: color.border,
          borderWidth: 1
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: { mode: 'index', intersect: false }
        },
        scales: {
          x: xTitle ? { title: { display: true, text: xTitle } } : {},
          y: {
            beginAtZero: true,
            title: { display: true, text: 'Number of Words' }
          }
        }
      }
    });
  }

  document.addEventListener('DOMContentLoaded', function () {
    const dataElement = document.getElementById('daily-chart-data');
    if (!dataElement) {
      return;
    }

    let chartData;
    try {
      chartData = JSON.parse(dataElement.textContent || '{}');
    } catch (error) {
      return;
    }

    if (typeof Chart === 'undefined') {
      return;
    }

    renderChart(
      'dailyStartingLetterChart',
      chartData.startingLetter,
      { background: 'rgba(59, 130, 246, 0.85)', border: 'rgba(59, 130, 246, 1)' },
      'Starting Letter'
    );

    renderChart(
      'dailyWordLengthChart',
      chartData.wordLength,
      { background: 'rgba(16, 185, 129, 0.85)', border: 'rgba(16, 185, 129, 1)' },
      'Word Length (characters)'
    );
  });
}());
