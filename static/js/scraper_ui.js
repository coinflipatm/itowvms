// static/js/scraper_ui.js
// Handles UI logic for TowBook Importer modal

document.addEventListener('DOMContentLoaded', function() {
    const scrapeForm = document.getElementById('scrapeForm');
    if (!scrapeForm) return;
    
    scrapeForm.addEventListener('submit', function(e) {
        e.preventDefault();
        const username = document.getElementById('towbookUsername').value;
        const password = document.getElementById('towbookPassword').value;
        const startDate = document.getElementById('scrapeStartDate').value;
        const endDate = document.getElementById('scrapeEndDate').value;
        
        const statusContainer = document.getElementById('scraping-status-container');
        const statusText = document.getElementById('scraping-status');
        const progressBar = document.getElementById('scraping-progress');
        const messageDiv = document.getElementById('scraping-message');
        
        statusContainer.style.display = 'block';
        statusText.textContent = 'Importing data...';
        progressBar.value = 0;
        messageDiv.textContent = '';
        
        fetch('/api/start-scraping', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password, start_date: startDate, end_date: endDate })
        })
        .then(response => response.json().then(data => ({ status: response.status, data })))
        .then(({ status, data }) => {
            if (status === 202 && data.scraper_id) {
                const scraperId = data.scraper_id;
                const poll = setInterval(() => {
                    fetch(`/api/scraping-progress/${scraperId}`)
                    .then(res => res.json())
                    .then(progress => {
                        statusText.textContent = progress.status;
                        progressBar.value = progress.percentage;
                        if (!progress.is_running) {
                            clearInterval(poll);
                            if (progress.error) {
                                statusText.textContent = 'Import failed.';
                                messageDiv.textContent = progress.error;
                            } else {
                                statusText.textContent = 'Import complete!';
                                progressBar.value = 100;
                                messageDiv.textContent = data.message || 'Import finished.';
                            }
                        }
                    })
                    .catch(err => {
                        clearInterval(poll);
                        statusText.textContent = 'Import failed.';
                        messageDiv.textContent = err.message || 'Error fetching progress.';
                    });
                }, 1000);
            } else if (data.status === 'completed') {
                statusText.textContent = 'Import complete!';
                progressBar.value = 100;
                messageDiv.textContent = data.message || 'Import finished.';
            } else {
                statusText.textContent = 'Import failed.';
                messageDiv.textContent = data.error || data.message || 'Unknown error.';
            }
        })
        .catch(error => {
            statusText.textContent = 'Import failed.';
            messageDiv.textContent = error.message || 'Unknown error.';
        });
    });
});
