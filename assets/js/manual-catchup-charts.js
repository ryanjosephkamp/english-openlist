// assets/js/manual-catchup-charts.js
// Interactive charts for the Manual OED Catch-Up Update (May 19, 2026)

console.log('🚀 manual-catchup-charts.js loaded successfully');

document.addEventListener('DOMContentLoaded', function () {
  console.log('✅ DOM ready – rendering interactive charts for manual OED catch-up');

  if (typeof Chart === 'undefined') {
    console.error('Chart.js is required for manual catch-up charts but was not loaded.');
    return;
  }

  // === STARTING LETTER DISTRIBUTION (full valid list) ===
  const startingCtx = document.getElementById('startingLetterChart');
  if (startingCtx) {
    new Chart(startingCtx, {
      type: 'bar',
      data: {
        labels: ['A','B','C','D','E','F','G','H','I','J','K','L','M','N','O','P','Q','R','S','T','U','V','W','X','Y','Z'],
        datasets: [{
          label: 'Word Count',
          data: [19510, 18363, 31791, 23363, 15294, 13021, 11443, 18577, 13142, 2120, 3578, 9967, 27177, 20300, 13499, 35709, 3218, 17659, 34719, 19654, 12267, 5326, 5669, 774, 899, 1641],
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
    console.log('✅ Starting Letter Chart rendered');
  }

  // === WORD LENGTH DISTRIBUTION (full valid list) ===
  const lengthCtx = document.getElementById('wordLengthChart');
  const wordLengthData = [10, 134, 1103, 4265, 9762, 18110, 29967, 41770, 47774, 46229, 41457, 35463, 28704, 22453, 17158, 11403, 7729, 5188, 3537, 2245, 1429, 886, 617, 403, 276, 185, 110, 83, 64, 49, 31, 21, 16, 12, 11, 7, 5, 1, 2, 3, 1, 1, 0, 0, 0, 0, 3, 2, 1];
  if (lengthCtx) {
    new Chart(lengthCtx, {
      type: 'bar',
      data: {
        labels: Array.from({ length: wordLengthData.length }, (_, i) => (i + 1).toString()),
        datasets: [{
          label: 'Word Count',
          data: wordLengthData,
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
    console.log('✅ Word Length Chart rendered');
  }

  console.log('🎉 Both interactive charts rendered successfully for the manual OED catch-up post!');
});
