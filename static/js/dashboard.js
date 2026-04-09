document.addEventListener('DOMContentLoaded', () => {
    /* -------------------------------------------------------------------------- */
    /* 1. View Navigation (Sidebar)                                               */
    /* -------------------------------------------------------------------------- */
    const navItems = document.querySelectorAll('.nav-menu li[data-view]');
    const views = document.querySelectorAll('.view-section');

    navItems.forEach(item => {
        item.addEventListener('click', () => {
            navItems.forEach(n => n.classList.remove('active'));
            item.classList.add('active');
            const targetView = item.getAttribute('data-view');
            views.forEach(v => {
                if(v.id === `view-${targetView}`) {
                    v.classList.remove('hidden');
                    if(targetView === 'history') loadHistory();
                    if(targetView === 'profile') loadProfile();
                } else {
                    v.classList.add('hidden');
                }
            });
        });
    });

    /* -------------------------------------------------------------------------- */
    /* 2. Scanner Input Tabs                                                      */
    /* -------------------------------------------------------------------------- */
    const tabBtns = document.querySelectorAll('.tab-btn');
    const tabContents = document.querySelectorAll('.tab-content');

    tabBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            tabBtns.forEach(b => b.classList.remove('active'));
            tabContents.forEach(c => c.classList.remove('active'));
            btn.classList.add('active');
            document.getElementById(btn.getAttribute('data-target')).classList.add('active');
        });
    });

    /* -------------------------------------------------------------------------- */
    /* 3. Text Search Analysis                                                    */
    /* -------------------------------------------------------------------------- */
    const btnSearch = document.getElementById('btn-search');
    const inputProduct = document.getElementById('product-name-input');

    btnSearch.addEventListener('click', async () => {
        const query = inputProduct.value.trim();
        if(!query) return;
        
        showLoading();
        try {
            const res = await fetch('/api/analyze-name', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ product_name: query })
            });
            const data = await res.json();
            if(data.success) {
                await renderResults(data);
            } else {
                alert(data.error);
                hideLoading();
            }
        } catch(e) {
            alert("Connection error.");
            hideLoading();
        }
    });

    // Enter key support
    inputProduct.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') btnSearch.click();
    });

    /* -------------------------------------------------------------------------- */
    /* 4. Upload Image Analysis                                                   */
    /* -------------------------------------------------------------------------- */
    const uploadZone = document.getElementById('upload-zone');
    const fileInput = document.getElementById('file-upload');
    const uploadPreviewContainer = document.getElementById('upload-preview-container');
    const uploadPreviewImg = document.getElementById('upload-preview');
    const btnCancelUpload = document.getElementById('btn-cancel-upload');
    const btnAnalyzeUpload = document.getElementById('btn-analyze-upload');
    let currentUploadFile = null;

    uploadZone.addEventListener('click', () => fileInput.click());
    fileInput.addEventListener('change', (e) => {
        if(e.target.files.length) handleFile(e.target.files[0]);
    });

    function handleFile(file) {
        currentUploadFile = file;
        uploadPreviewImg.src = URL.createObjectURL(file);
        uploadZone.classList.add('hidden');
        uploadPreviewContainer.classList.remove('hidden');
    }

    btnCancelUpload.addEventListener('click', () => {
        currentUploadFile = null;
        fileInput.value = '';
        uploadPreviewContainer.classList.add('hidden');
        uploadZone.classList.remove('hidden');
    });

    btnAnalyzeUpload.addEventListener('click', async () => {
        if(!currentUploadFile) return;
        showLoading();
        
        const fd = new FormData();
        fd.append('image', currentUploadFile);
        fd.append('input_type', 'upload');

        try {
            const res = await fetch('/api/analyze-image', { method: 'POST', body: fd });
            const data = await res.json();
            if(data.success) {
                await renderResults(data);
            } else {
                alert(data.error);
                hideLoading();
            }
        } catch(e) {
            alert("Connection error.");
            hideLoading();
        }
    });

    /* -------------------------------------------------------------------------- */
    /* 5. Camera Scan Analysis                                                    */
    /* -------------------------------------------------------------------------- */
    const btnStartCamera = document.getElementById('btn-start-camera');
    const btnCapture = document.getElementById('btn-capture');
    const video = document.getElementById('camera-feed');
    const canvas = document.getElementById('camera-canvas');
    let stream = null;

    btnStartCamera.addEventListener('click', async () => {
        try {
            stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: "environment" } });
            video.srcObject = stream;
            video.style.display = 'block';
            btnStartCamera.classList.add('hidden');
            btnCapture.classList.remove('hidden');
        } catch (e) {
            alert("Camera access denied or not available.");
        }
    });

    btnCapture.addEventListener('click', async () => {
        if(!stream) return;
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        canvas.getContext('2d').drawImage(video, 0, 0);
        
        video.pause();
        stream.getTracks().forEach(t => t.stop());
        stream = null;
        
        btnStartCamera.classList.remove('hidden');
        btnCapture.classList.add('hidden');
        btnStartCamera.innerText = "Restart Camera";
        
        canvas.toBlob(async (blob) => {
            showLoading();
            const fd = new FormData();
            fd.append('image', blob, "capture.jpg");
            fd.append('input_type', 'camera');
            
            try {
                const res = await fetch('/api/analyze-image', { method: 'POST', body: fd });
                const data = await res.json();
                if(data.success) {
                    await renderResults(data);
                } else {
                    alert(data.error);
                    hideLoading();
                }
            } catch(e) {
                alert("Connection error.");
                hideLoading();
            }
        }, 'image/jpeg');
    });

    /* -------------------------------------------------------------------------- */
    /* 6. Results Rendering & Translation                                         */
    /* -------------------------------------------------------------------------- */
    const spinner = document.getElementById('loading-spinner');
    const resultsContainer = document.getElementById('results-container');
    const langSelect = document.getElementById('lang-select');
    
    // UI Elements for Results
    const resBrand = document.getElementById('res-brand');
    const resConfCode = document.getElementById('res-confidence');
    const resRiskCard = document.getElementById('risk-card');
    const resRiskIcon = document.getElementById('res-risk-icon');
    const resRisk = document.getElementById('res-risk');
    const resCalories = document.getElementById('res-calories');
    const resSugar = document.getElementById('res-sugar');
    const resSugarLvl = document.getElementById('res-sugar-lvl');
    const chatResponseText = document.getElementById('chat-response-text');
    
    let currentRawChatText = "";

    function showLoading() {
        spinner.classList.remove('hidden');
        resultsContainer.classList.add('hidden');
        // Stop any currently playing audio
        window.speechSynthesis.cancel();
    }

    function hideLoading() {
        spinner.classList.add('hidden');
    }

    async function renderResults(data) {
        // Set basic values
        resBrand.textContent = data.risk_info.display_name;
        resConfCode.textContent = Math.round(data.confidence * 100);
        resCalories.textContent = data.risk_info.calories_per_100ml;
        resSugar.textContent = data.risk_info.sugar_per_100ml + "g";
        resSugarLvl.textContent = data.risk_info.sugar_level;

        // Risk UI updates
        const risk = data.risk_info.risk;
        resRisk.textContent = risk;
        resRiskCard.className = "glass-panel text-center"; // reset
        if (risk === "LOW") { resRiskCard.classList.add("risk-low"); resRiskIcon.textContent = "✅"; }
        else if (risk === "MODERATE") { resRiskCard.classList.add("risk-moderate"); resRiskIcon.textContent = "⚠️"; }
        else { resRiskCard.classList.add("risk-high"); resRiskIcon.getContext = "🔴"; }

        currentRawChatText = data.chat_response;
        await translateTextAndDisplay(currentRawChatText);
        
        hideLoading();
        resultsContainer.classList.remove('hidden');
        
        // Auto-scroll Down
        resultsContainer.scrollIntoView({ behavior: 'smooth' });
    }

    async function translateTextAndDisplay(text) {
        const targetLang = langSelect.value;
        if(targetLang === 'en') {
            chatResponseText.textContent = text;
            return;
        }
        
        try {
            const transRes = await fetch('/api/translate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ text: text, target_lang: targetLang })
            });
            const tData = await transRes.json();
            chatResponseText.textContent = tData.success ? tData.translated_text : text;
        } catch (e) {
            chatResponseText.textContent = text;
        }
    }

    langSelect.addEventListener('change', async () => {
        if(!resultsContainer.classList.contains('hidden') && currentRawChatText) {
            chatResponseText.textContent = "Translating...";
            await translateTextAndDisplay(currentRawChatText);
        }
    });

    /* -------------------------------------------------------------------------- */
    /* 7. Voice Over (Text-to-Speech)                                             */
    /* -------------------------------------------------------------------------- */
    const btnSpeak = document.getElementById('btn-speak');
    btnSpeak.addEventListener('click', () => {
        if(!chatResponseText.textContent) return;
        
        const lang = langSelect.value;
        const msg = new SpeechSynthesisUtterance();
        // Remove markdown artifacts for cleaner speech
        const cleanText = chatResponseText.textContent.replace(/[*_~`]/g, '');
        msg.text = cleanText;
        msg.lang = lang; // Best effort language mapping
        
        // Stop current speech before starting new
        window.speechSynthesis.cancel();
        window.speechSynthesis.speak(msg);
    });

    /* -------------------------------------------------------------------------- */
    /* 8. Load History                                                            */
    /* -------------------------------------------------------------------------- */
    async function loadHistory() {
        const tbody = document.querySelector('#history-table tbody');
        tbody.innerHTML = '<tr><td colspan="4" class="text-center">Loading...</td></tr>';
        try {
            const res = await fetch('/api/history');
            const data = await res.json();
            if(data.success && data.history.length > 0) {
                tbody.innerHTML = '';
                data.history.forEach(item => {
                    const tr = document.createElement('tr');
                    const d = new Date(item.created_at).toLocaleString();
                    const icon = item.input_type === 'image' ? 'ph-image' : (item.input_type === 'camera' ? 'ph-camera' : 'ph-text-t');
                    
                    tr.innerHTML = `
                        <td>${d}</td>
                        <td style="font-weight:bold;">${item.product_name}</td>
                        <td><i class="ph ${icon}"></i> ${item.input_type}</td>
                        <td class="${item.risk_level === 'HIGH' ? 'text-red' : (item.risk_level === 'MODERATE' ? 'text-yellow' : 'text-green')}">${item.risk_level}</td>
                    `;
                    tbody.appendChild(tr);
                });
            } else {
                tbody.innerHTML = '<tr><td colspan="4" class="text-center">No history found.</td></tr>';
            }
        } catch (e) {
            tbody.innerHTML = '<tr><td colspan="4" class="text-center">Error loading history.</td></tr>';
        }
    }

    /* -------------------------------------------------------------------------- */
    /* 9. Load & Save Profile                                                     */
    /* -------------------------------------------------------------------------- */
    async function loadProfile() {
        try {
            const res = await fetch('/api/profile');
            const data = await res.json();
            if(data.success) {
                document.getElementById('prof-fullname').value = data.full_name || '';
                document.getElementById('prof-age').value = data.age || '';
                document.getElementById('prof-conditions').value = data.health_conditions || '';
            }
        } catch (e) {
            console.error(e);
        }
    }

    document.getElementById('btn-save-profile').addEventListener('click', async () => {
        const full_name = document.getElementById('prof-fullname').value;
        const age = document.getElementById('prof-age').value;
        const health_conditions = document.getElementById('prof-conditions').value;
        
        try {
            const res = await fetch('/api/profile', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ full_name, age, health_conditions })
            });
            const data = await res.json();
            if(data.success) {
                const msg = document.getElementById('prof-save-msg');
                document.getElementById('display-name').textContent = full_name;
                msg.style.display = 'inline-block';
                setTimeout(() => msg.style.display = 'none', 3000);
            }
        } catch(e) {
            alert("Error saving profile.");
        }
    });

});
