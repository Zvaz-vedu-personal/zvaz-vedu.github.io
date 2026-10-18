// Content for /js/sheets-progress-bar.js
document.addEventListener('DOMContentLoaded', function() {
    // --- Configuration ---
    const registrationInfoDivs = document.querySelectorAll('.registration-info, #registration-info');
    
    registrationInfoDivs.forEach(registrationInfoDiv => {
        const sheetUrl = registrationInfoDiv.dataset.sheetUrl;
        
        const rawParticipants = registrationInfoDiv.dataset.maxParticipants || registrationInfoDiv.dataset.participants;
        const targetCount = rawParticipants ? parseInt(rawParticipants, 10) : 100;

        // --- Element References ---
        const progressBarTrack = registrationInfoDiv.querySelector('.progress-bar-track-pill');
        const progressBarFill = progressBarTrack ? progressBarTrack.querySelector('.progress-bar-fill-pill') : null;
        const progressBarCountText = progressBarTrack ? progressBarTrack.querySelector('.progress-bar-count-text') : null;
        const bentoRegistrationText = document.getElementById('bento-registration-text') || registrationInfoDiv.querySelector('.bento-registration-text');

        // --- Validation ---
        if (!progressBarTrack || !progressBarFill || !progressBarCountText) {
            console.error("Required progress bar HTML elements not found (.progress-bar-track-pill, .progress-bar-fill-pill, .progress-bar-count-text).");
            registrationInfoDiv.textContent = 'Error loading progress bar.';
            return;
        }

        if (!sheetUrl || sheetUrl.trim() === '') {
            console.error("Google Sheet URL not provided or is empty in data-sheet-url attribute.");
            progressBarCountText.textContent = `Error: URL missing.`;
            progressBarFill.style.backgroundColor = 'red';
            progressBarTrack.style.backgroundColor = 'transparent';
            progressBarTrack.style.boxShadow = 'none';
            progressBarTrack.style.overflow = 'visible';
            progressBarTrack.style.height = 'auto';
            progressBarTrack.style.padding = '0';
            progressBarTrack.style.borderRadius = '0';
            progressBarCountText.style.color = 'red';
            progressBarCountText.style.position = 'static';
            progressBarCountText.style.textAlign = 'center';
            progressBarCountText.style.width = '100%';
            progressBarCountText.style.transform = 'none';
            if (bentoRegistrationText) bentoRegistrationText.textContent = `Chyba načítání`;
            return;
        }

        if (isNaN(targetCount) || targetCount <= 0) {
            console.error("Invalid targetCount specified. Must be a positive number.");
            progressBarCountText.textContent = `Error: Invalid target.`;
            progressBarFill.style.backgroundColor = 'red';
            progressBarTrack.style.backgroundColor = 'transparent';
            progressBarTrack.style.boxShadow = 'none';
            progressBarTrack.style.overflow = 'visible';
            progressBarTrack.style.height = 'auto';
            progressBarTrack.style.padding = '0';
            progressBarTrack.style.borderRadius = '0';
            progressBarCountText.style.color = 'red';
            progressBarCountText.style.position = 'static';
            progressBarCountText.style.textAlign = 'center';
            progressBarCountText.style.width = '100%';
            progressBarCountText.style.transform = 'none';
            if (bentoRegistrationText) bentoRegistrationText.textContent = `Chyba cílové hodnoty`;
            return;
        }

        // --- Helper Functions ---
        function getCsvExportUrl(url) {
            try {
                const urlObj = new URL(url);
                if (urlObj.pathname.endsWith('/pubhtml')) {
                    urlObj.pathname = urlObj.pathname.replace('/pubhtml', '/pub');
                }
                urlObj.searchParams.set('output', 'csv');
                return urlObj.toString();
            } catch (e) {
                console.error("Failed to parse sheet URL:", e.message, url);
                return null;
            }
        }

        async function fetchLineCountAndAnimateBar(csvUrl, target, fillElement, textElement, bentoTextElement) {
            textElement.textContent = `Načítám...`; 
            textElement.style.justifyContent = 'flex-end';
            textElement.style.left = 'auto';
            textElement.style.right = '15px';
            textElement.style.width = 'auto';
            fillElement.style.width = '0%';
            if (bentoTextElement) bentoTextElement.textContent = 'účastníků'; 

            try {
                const response = await fetch(csvUrl);

                if (!response.ok) {
                    textElement.textContent = `Error (${response.status})`;
                    fillElement.style.backgroundColor = 'red';
                    fillElement.style.width = '100%';
                    textElement.style.color = 'white';
                    textElement.style.justifyContent = 'center';
                    textElement.style.left = '0';
                    textElement.style.right = '0';
                    textElement.style.width = '100%';
                    if (bentoTextElement) bentoTextElement.textContent = `Chyba načítání`; 
                    return;
                }

                const csvText = await response.text();
                
                const firstLine = csvText.split(/\r\n|\n|\r/)[0];
                const a1ValueRaw = firstLine ? firstLine.split(',')[0] : "0";
                
                const participantCount = parseInt(a1ValueRaw.replace(/(^"|"$)/g, '').trim(), 10);

                if (isNaN(participantCount)) {
                    throw new Error("Hodnota v buňce A1 není platné číslo.");
                }

                let percentage = (participantCount / target) * 100;
                if (percentage > 100) percentage = 100;
                if (percentage < 0) percentage = 0;

                textElement.textContent = `${participantCount}/${target}`;

                requestAnimationFrame(() => {
                    requestAnimationFrame(() => {
                        fillElement.style.width = `${percentage}%`;
                    });
                });

                if (participantCount >= target) {
                    fillElement.style.backgroundColor = '#e63946'; // Red for full capacity
                    fillElement.style.boxShadow = '0 0 15px rgba(230, 57, 70, 0.6)';
                    fillElement.classList.add('registration-full-pulse');

                    textElement.textContent = `Všech ${target} míst obsazeno!`;
                    textElement.style.fontWeight = 'bold';
                    textElement.style.color = 'white';
                    textElement.style.justifyContent = 'center';
                    textElement.style.left = '0';
                    textElement.style.right = '0';
                    textElement.style.width = '100%';

                    if (bentoTextElement) bentoTextElement.textContent = `Děkujeme za velký zájem!`; 
                } else if (percentage >= 85) {
                    fillElement.style.backgroundColor = '#e63946'; // Red for 85%+ capacity
                    fillElement.style.boxShadow = '0 0 10px rgba(230, 57, 70, 0.4)';
                    fillElement.classList.remove('registration-full-pulse');
                    
                    textElement.style.fontWeight = 'bold';
                    textElement.style.color = '';
                    textElement.style.justifyContent = 'flex-end';
                    textElement.style.left = 'auto';
                    textElement.style.right = '15px';
                    textElement.style.width = 'auto';

                    if (bentoTextElement) bentoTextElement.textContent = `účastníků`;
                } else {
                    fillElement.style.backgroundColor = '';
                    fillElement.style.boxShadow = '';
                    fillElement.classList.remove('registration-full-pulse');
                    textElement.style.fontWeight = '';
                    textElement.style.color = '';
                    textElement.style.justifyContent = 'flex-end';
                    textElement.style.left = 'auto';
                    textElement.style.right = '15px';
                    textElement.style.width = 'auto';

                    if (bentoTextElement) bentoTextElement.textContent = `účastníků`;
                }

            } catch (error) {
                console.error("Failed to fetch or process data:", error);
                textElement.textContent = `Chyba`;
                fillElement.style.backgroundColor = 'red';
                fillElement.style.width = '100%';
                textElement.style.color = 'white';
                textElement.style.justifyContent = 'center';
                textElement.style.left = '0';
                textElement.style.right = '0';
                textElement.style.width = '100%';
                if (bentoTextElement) bentoTextElement.textContent = `Chyba načítání`; 
            }
        }

        const csvUrl = getCsvExportUrl(sheetUrl);

        if (csvUrl) {
            fetchLineCountAndAnimateBar(csvUrl, targetCount, progressBarFill, progressBarCountText, bentoRegistrationText);
        } else {
            progressBarCountText.textContent = `Neplatná URL`;
            progressBarFill.style.backgroundColor = 'red';
            progressBarFill.style.width = '100%';
            progressBarCountText.style.color = 'white';
            progressBarCountText.style.position = 'static';
            progressBarCountText.style.textAlign = 'center';
            progressBarCountText.style.width = '100%';
            progressBarCountText.style.transform = 'none';

            progressBarTrack.style.backgroundColor = 'transparent';
            progressBarTrack.style.boxShadow = 'none';
            progressBarTrack.style.overflow = 'visible';
            progressBarTrack.style.height = 'auto';
            progressBarTrack.style.padding = '0';
            progressBarTrack.style.borderRadius = '0';
            if (bentoRegistrationText) bentoRegistrationText.textContent = `Chyba URL`;
        }
    });

    if (typeof eventTimeStr !== 'undefined') {
        const eventTime = new Date(eventTimeStr).getTime();
        const countdownEl = document.getElementById("countdown-display");
        
        function updateCountdown() {
          const now = new Date().getTime();
          const diff = eventTime - now;         
          const d = Math.floor(diff / (1000 * 60 * 60 * 24));
          const h = Math.floor((diff % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
          const m = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
          const s = Math.floor((diff % (1000 * 60)) / 1000);
        
          if(countdownEl) {
              countdownEl.innerHTML = `
                <div class="countdown-row">
                    <div class="countdown-block">
                    <span class="count-number">${d}</span>
                    <span class="count-label">dnů</span>
                    </div>
                    <span class="count-separator">:</span>
                    <div class="countdown-block">
                    <span class="count-number">${h}</span>
                    <span class="count-label">hodin</span>
                    </div>
                    <span class="count-separator">:</span>
                    <div class="countdown-block">
                    <span class="count-number">${m}</span>
                    <span class="count-label">minut</span>
                    </div>
                    <span class="count-separator">:</span>
                    <div class="countdown-block">
                    <span class="count-number">${s}</span>
                    <span class="count-label">sekund</span>
                    </div>
                </div>
                `;
          }
        }
        
        setInterval(updateCountdown, 1000); 
    }
});