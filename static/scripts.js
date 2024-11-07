function analyzeSentiment() {
    const url = document.getElementById('url').value;
    const info = document.getElementById('info').value;
    const resultsContainer = document.getElementById('results-container');
    const resultsList = document.getElementById('results');

    // Reset results
    resultsContainer.style.display = 'none';
    resultsList.innerHTML = '';

    // Send data to server
    fetch('/analyze', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ url: url, info: info })
    })
    .then(response => response.json())
    .then(data => {
        resultsContainer.style.display = 'block';
        for (const [sentiment, percentage] of Object.entries(data)) {
            const listItem = document.createElement('li');
            listItem.textContent = `${sentiment}: ${percentage.toFixed(2)}%`;
            resultsList.appendChild(listItem);
        }
    })
    .catch(error => console.error('Error:', error));
}
