document.addEventListener('DOMContentLoaded', () => {
    // Elements
    const dropZone = document.getElementById('drop-zone');
    const fileInput = document.getElementById('file-input');
    const uploadPanel = document.getElementById('upload-panel');
    const previewContainer = document.getElementById('preview-container');
    const imagePreview = document.getElementById('image-preview');
    const btnCancel = document.getElementById('btn-cancel');
    const btnAnalyze = document.getElementById('btn-analyze');
    
    const loadingPanel = document.getElementById('loading-panel');
    const scanningImage = document.getElementById('scanning-image');
    
    const resultsPanel = document.getElementById('results-panel');
    const btnReset = document.getElementById('btn-reset');
    
    let currentFile = null;

    // --- Drag and Drop Logic ---
    dropZone.addEventListener('click', () => fileInput.click());

    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.classList.add('dragover');
    });

    dropZone.addEventListener('dragleave', () => {
        dropZone.classList.remove('dragover');
    });

    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.classList.remove('dragover');
        if (e.dataTransfer.files.length) {
            handleFile(e.dataTransfer.files[0]);
        }
    });

    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length) {
            handleFile(e.target.files[0]);
        }
    });

    function handleFile(file) {
        if (!file.type.match('image.*')) {
            alert('Please select an image file (PNG, JPG, WEBP)');
            return;
        }
        currentFile = file;
        const reader = new FileReader();
        reader.onload = (e) => {
            imagePreview.src = e.target.result;
            scanningImage.src = e.target.result;
            dropZone.classList.add('hidden');
            previewContainer.classList.remove('hidden');
        };
        reader.readAsDataURL(file);
    }

    // --- Cancel / Reset ---
    btnCancel.addEventListener('click', resetView);
    btnReset.addEventListener('click', resetView);

    function resetView() {
        currentFile = null;
        fileInput.value = '';
        previewContainer.classList.add('hidden');
        dropZone.classList.remove('hidden');
        resultsPanel.classList.add('hidden');
        uploadPanel.classList.remove('hidden');
    }

    // --- Analyze Flow ---
    btnAnalyze.addEventListener('click', async () => {
        if (!currentFile) return;

        // UI Transition to Loading
        uploadPanel.classList.add('hidden');
        loadingPanel.classList.remove('hidden');

        // Prepare File Data
        const formData = new FormData();
        formData.append('image', currentFile);

        try {
            const response = await fetch('/analyze', {
                method: 'POST',
                body: formData
            });
            const data = await response.json();

            if (data.success) {
                // Simulate slightly longer loading for cool effect
                setTimeout(() => {
                    loadingPanel.classList.add('hidden');
                    populateResults(data);
                    resultsPanel.classList.remove('hidden');
                }, 1500);
            } else {
                alert('Analysis failed: ' + data.error);
                resetView();
            }
        } catch (error) {
            console.error(error);
            alert('Error connecting to AI Server.');
            resetView();
        }
    });

    function populateResults(data) {
        // Identity
        document.getElementById('res-brand').textContent = data.brand;
        document.getElementById('res-conf').textContent = Math.round(data.confidence * 100) + '%';

        const riskInfo = data.risk_info;
        const riskCard = document.getElementById('risk-card');
        
        // Remove old risk classes
        riskCard.classList.remove('risk-low', 'risk-moderate', 'risk-high');
        
        // Risk Matrix
        const riskLevel = riskInfo.risk.toUpperCase();
        document.getElementById('res-risk-level').textContent = riskLevel;
        
        if (riskLevel === 'LOW') {
            document.getElementById('res-risk-icon').textContent = '✅';
            riskCard.classList.add('risk-low');
        } else if (riskLevel === 'MODERATE') {
            document.getElementById('res-risk-icon').textContent = '⚠️';
            riskCard.classList.add('risk-moderate');
        } else {
            document.getElementById('res-risk-icon').textContent = '🔴';
            riskCard.classList.add('risk-high');
        }

        // Nutrition
        document.getElementById('res-calories').textContent = riskInfo.calories_per_100ml;
        document.getElementById('res-sugar').textContent = riskInfo.sugar_per_100ml + 'g';
        document.getElementById('res-sugar-lvl').textContent = riskInfo.sugar_level;

        // Warnings
        const warningsList = document.getElementById('res-warnings');
        warningsList.innerHTML = '';
        if (riskInfo.warnings && riskInfo.warnings.length) {
            riskInfo.warnings.forEach(w => {
                const li = document.createElement('li');
                li.textContent = w;
                warningsList.appendChild(li);
            });
        } else {
            warningsList.innerHTML = '<li>None specified</li>';
        }

        // Advice
        document.getElementById('res-advice').textContent = riskInfo.advice;

        // Safe For
        const safeContainer = document.getElementById('safe-for-container');
        const safeList = document.getElementById('res-safe');
        safeList.innerHTML = '';
        if (riskInfo.safe_for && riskInfo.safe_for.length) {
            safeContainer.classList.remove('hidden');
            riskInfo.safe_for.forEach(s => {
                const li = document.createElement('li');
                li.textContent = s;
                safeList.appendChild(li);
            });
        } else {
            safeContainer.classList.add('hidden');
        }
    }
});
