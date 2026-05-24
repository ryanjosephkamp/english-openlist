// assets/js/daily-update-charts.js
// Interactive charts for automated daily English OpenList update posts.

document.addEventListener('DOMContentLoaded', function () {
  if (typeof Chart === 'undefined') {
    console.error('Chart.js is required for daily update charts but was not loaded.');
    return;
  }

  const dataElement = document.getElementById('daily-chart-data');
  if (!dataElement) {
    return;
  }

  let chartData;
  try {
    chartData = JSON.parse(dataElement.textContent);
  } catch (error) {
    console.error('Could not parse daily chart data.', error);
    return;
  }

  const startingCtx = document.getElementById('dailyStartingLetterChart');
  if (startingCtx && chartData.startingLetter) {
    new Chart(startingCtx, {
      type: 'bar',
      data: {
        labels: chartData.startingLetter.labels,
        datasets: [{
          label: 'Word Count',
          data: chartData.startingLetter.values,
          backgroundColor: 'rgba(59, 130, 246, 0.85)',
          borderColor: 'rgba(59, 130, 246, 1)',
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
          y: {
            beginAtZero: true,
            title: { display: true, text: 'Number of Words' }
          }
        }
      }
    });
  }

  const lengthCtx = document.getElementById('dailyWordLengthChart');
  if (lengthCtx && chartData.wordLength) {
    new Chart(lengthCtx, {
      type: 'bar',
      data: {
        labels: chartData.wordLength.labels,
        datasets: [{
          label: 'Word Count',
          data: chartData.wordLength.values,
          backgroundColor: 'rgba(16, 185, 129, 0.85)',
          borderColor: 'rgba(16, 185, 129, 1)',
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
          x: {
            title: { display: true, text: 'Word Length (characters)' }
          },
          y: {
            beginAtZero: true,
            title: { display: true, text: 'Number of Words' }
          }
        }
      }
    });
  }
});
