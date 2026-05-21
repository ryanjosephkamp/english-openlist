// assets/js/manual-catchup-charts.js
console.log('🚀 manual-catchup-charts.js loaded');

document.addEventListener('DOMContentLoaded', function () {
  console.log('✅ DOM ready – rendering interactive charts');

  // Starting Letter Chart
  new Chart(document.getElementById('startingLetterChart'), {
    type: 'bar',
    data: {
      labels: ['A','B','C','D','E','F','G','H','I','J','K','L','M','N','O','P','Q','R','S','T','U','V','W','X','Y','Z'],
      datasets: [{
        label: 'Word Count',
        data: [19510,18363,31791,23363,15294,13021,11443,18577,13142,2120,3578,9967,27177,20300,13499,35709,3218,17659,34719,19654,12267,5326,5669,774,899,1641],
        backgroundColor: 'rgba(59, 130, 246, 0.85)',
        borderColor: 'rgba(59, 130, 246, 1)',
        borderWidth: 1
      }]
    },
    options: {
      responsive: true,
      plugins: { legend: { display: false } },
      scales: { y: { beginAtZero: true, title: { display: true, text: 'Number of Words' }}}
    }
  });

  // Word Length Chart
  new Chart(document.getElementById('wordLengthChart'), {
    type: 'bar',
    data: {
      labels: Array.from({length: 47}, (_, i) => (i+1).toString()),
      datasets: [{
        label: 'Word Count',
        data: [10,134,1103,4265,9762,18110,29967,41770,47774,46229,41457,35463,28704,22453,17158,11403,7729,5188,3537,2245,1429,886,617,403,276,185,110,83,64,49,31,21,16,12,11,7,5,1,2,3,1,1,0,0,0,0,3,2,1],
        backgroundColor: 'rgba(16, 185, 129, 0.85)',
        borderColor: 'rgba(16, 185, 129, 1)',
        borderWidth: 1
      }]
    },
    options: {
      responsive: true,
      plugins: { legend: { display: false } },
      scales: {
        x: { title: { display: true, text: 'Word Length (characters)' }},
        y: { beginAtZero: true, title: { display: true, text: 'Number of Words' }}
      }
    }
  });

  console.log('🎉 Both interactive charts rendered successfully!');
});
