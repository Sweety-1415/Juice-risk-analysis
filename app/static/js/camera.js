(() => {
    const uploadForm = document.getElementById("uploadScanForm");
    const webcamFeed = document.getElementById("webcamFeed");
    const startCameraBtn = document.getElementById("startCameraBtn");
    const captureBtn = document.getElementById("captureBtn");
    const captureCanvas = document.getElementById("captureCanvas");
    const statusText = document.getElementById("scanStatusText");
    const resultBody = document.getElementById("scanResultBody");
    let stream = null;

    const icon = (color, path) => `
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="${color}" stroke-width="2.5"
            stroke-linecap="round" stroke-linejoin="round" style="flex-shrink:0;margin-top:2px;">
            ${path}
        </svg>`;

    const iconCheck  = `<polyline points="20 6 9 17 4 12"/>`;
    const iconWarn   = `<path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>`;
    const iconBan    = `<circle cx="12" cy="12" r="10"/><line x1="4.93" y1="4.93" x2="19.07" y2="19.07"/>`;
    const iconStar   = `<polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/>`;
    const iconDroplet= `<path d="M12 2.69l5.66 5.66a8 8 0 1 1-11.31 0z"/>`;
    const iconHeart  = `<path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"/>`;
    const iconLeaf   = `<path d="M2 22 12 12"/><path d="M16.67 7.33C18.84 5.16 22 5 22 5s.16 3.16-2.01 5.33c-2.17 2.17-5.49 2.5-5.49 2.5s.33-3.32 2.17-5.5z"/>`;

    const renderPill = (text, bg, color) =>
        `<span style="display:inline-flex;align-items:center;gap:0.35rem;padding:0.3rem 0.75rem;background:${bg};color:${color};border-radius:9999px;font-size:0.8rem;font-weight:600;">${text}</span>`;

    const renderSection = (title, items, bgColor, borderColor, textColor, iconSvg) => {
        if (!items || !items.length) return "";
        return `
            <div style="padding:1rem;background:${bgColor};border-radius:var(--radius-md);border-left:4px solid ${borderColor};">
                <p style="font-weight:700;font-size:0.85rem;text-transform:uppercase;letter-spacing:0.06em;color:${borderColor};margin-bottom:0.6rem;">${title}</p>
                <ul style="margin:0;padding:0;list-style:none;display:flex;flex-direction:column;gap:0.4rem;">
                    ${items.map(item => `
                        <li style="display:flex;align-items:flex-start;gap:0.5rem;font-size:0.9rem;color:${textColor};line-height:1.5;">
                            ${icon(borderColor, iconSvg)}
                            <span>${item}</span>
                        </li>`).join("")}
                </ul>
            </div>`;
    };

    const renderResult = (payload) => {
        const analysis = payload.analysis || {};
        const nutrients = analysis.nutrients || {};

        statusText.textContent = payload.status === "detected"
            ? `✅ Analysis complete for ${payload.detected_name}`
            : "⚠️ Bottle not detected";

        const status = analysis.status || "unknown";
        const statusMeta = {
            safer:   { label: "SAFER",   bg: "rgba(16,185,129,0.15)",  border: "#10b981", color: "#10b981" },
            caution: { label: "CAUTION", bg: "rgba(245,158,11,0.15)",  border: "#f59e0b", color: "#f59e0b" },
            avoid:   { label: "AVOID",   bg: "rgba(244,63,94,0.15)",   border: "#f43f5e", color: "#f43f5e" },
            unknown: { label: "UNKNOWN", bg: "rgba(148,163,184,0.15)", border: "#94a3b8", color: "#94a3b8" },
        }[status] || { label: "UNKNOWN", bg: "rgba(148,163,184,0.15)", border: "#94a3b8", color: "#94a3b8" };

        // Score ring color
        const scoreColor = status === "safer" ? "#10b981" : status === "caution" ? "#f59e0b" : "#f43f5e";

        resultBody.className = "";
        resultBody.innerHTML = `
        <div style="display:flex;flex-direction:column;gap:1.5rem;">

            <!-- TOP: Image + Title + Score -->
            <div style="display:flex;gap:1.5rem;flex-wrap:wrap;align-items:flex-start;">
                ${payload.annotated_url ? `
                <div style="flex:0 0 180px;">
                    <img src="${payload.annotated_url}" alt="Detected bottle"
                        style="width:100%;height:180px;border-radius:var(--radius-md);object-fit:cover;border:2px solid ${statusMeta.border};">
                </div>` : ""}

                <div style="flex:1;min-width:260px;display:flex;flex-direction:column;gap:0.75rem;">
                    <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:0.75rem;">
                        <div>
                            <h3 style="margin:0;font-size:1.6rem;font-weight:800;">${analysis.beverage_name || payload.detected_name || "Unknown"}</h3>
                            <p class="muted" style="margin:0.25rem 0 0;font-size:0.9rem;">
                                Confidence: <strong style="color:var(--text-primary);">${payload.confidence || 0}%</strong>
                                &nbsp;•&nbsp; Frequency: <strong style="color:var(--text-primary);">${analysis.frequency_limit || "n/a"}</strong>
                            </p>
                        </div>
                        <div style="display:flex;flex-direction:column;align-items:center;justify-content:center;
                            width:80px;height:80px;border-radius:50%;border:3px solid ${scoreColor};
                            background:rgba(0,0,0,0.2);">
                            <strong style="font-size:1.4rem;color:${scoreColor};">${analysis.score || 0}</strong>
                            <span style="font-size:0.65rem;color:var(--text-secondary);text-transform:uppercase;">/ 100</span>
                        </div>
                    </div>

                    <!-- Status badge + health flags -->
                    <div style="display:flex;flex-wrap:wrap;gap:0.5rem;align-items:center;">
                        <span style="padding:0.35rem 1rem;background:${statusMeta.bg};color:${statusMeta.color};
                            border:1px solid ${statusMeta.border};border-radius:9999px;font-weight:700;font-size:0.85rem;">
                            ${statusMeta.label}
                        </span>
                        ${(analysis.health_flags || []).map(f => renderPill(f, "rgba(255,255,255,0.06)", "var(--text-secondary)")).join("")}
                    </div>

                    <!-- Nutrient pills -->
                    <div style="display:flex;gap:0.75rem;flex-wrap:wrap;">
                        ${[
                            ["🍬 Sugar",    (nutrients.sugar_g    || 0) + " g",   "#f59e0b"],
                            ["🧂 Sodium",   (nutrients.sodium_mg  || 0) + " mg",  "#3b82f6"],
                            ["☕ Caffeine", (nutrients.caffeine_mg|| 0) + " mg",  "#8b5cf6"],
                            ["🔥 Calories", (nutrients.calories   || 0) + " kcal","#ec4899"],
                        ].map(([label, val, col]) => `
                            <div style="flex:1;min-width:80px;background:rgba(255,255,255,0.04);
                                border:1px solid rgba(255,255,255,0.08);border-radius:var(--radius-md);
                                padding:0.6rem 0.8rem;text-align:center;">
                                <span style="display:block;font-size:0.75rem;color:var(--text-secondary);">${label}</span>
                                <strong style="font-size:1.1rem;color:${col};">${val}</strong>
                            </div>`).join("")}
                    </div>

                    ${analysis.portion_guidance ? `
                    <p style="font-size:0.9rem;background:rgba(16,185,129,0.08);border:1px solid rgba(16,185,129,0.2);
                        border-radius:var(--radius-md);padding:0.75rem 1rem;margin:0;">
                        ${icon("#10b981", iconDroplet)}
                        <strong style="color:#10b981;">Serving Advice:</strong>
                        <span style="color:var(--text-secondary);margin-left:0.25rem;">${analysis.portion_guidance}</span>
                    </p>` : ""}
                </div>
            </div>

            <!-- HEALTH CONDITION ANALYSIS SECTION -->
            ${(analysis.allergy_alerts && analysis.allergy_alerts.length) || (analysis.avoid_reasons && analysis.avoid_reasons.length) || (analysis.caution_reasons && analysis.caution_reasons.length) ? `
            <div style="background:rgba(255,255,255,0.02);border:1px solid rgba(255,255,255,0.07);
                border-radius:var(--radius-md);padding:1.25rem;">
                <p style="font-weight:700;font-size:0.9rem;text-transform:uppercase;letter-spacing:0.1em;
                    color:var(--text-secondary);margin-bottom:1rem;">
                    ${icon("#94a3b8", iconHeart)} &nbsp;Health Profile Analysis
                </p>
                <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:1rem;">
                    ${renderSection("🚨 Allergy & Sensitivity Alerts", analysis.allergy_alerts,
                        "rgba(244,63,94,0.08)", "#f43f5e", "#fca5a5", iconBan)}
                    ${renderSection("🚫 Avoid Reasons", analysis.avoid_reasons,
                        "rgba(244,63,94,0.06)", "#f43f5e", "#fca5a5", iconBan)}
                    ${renderSection("⚠️ Caution Reasons", analysis.caution_reasons,
                        "rgba(245,158,11,0.08)", "#f59e0b", "#fcd34d", iconWarn)}
                </div>
            </div>` : ""}

            <!-- POSITIVES + SUGGESTIONS -->
            <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:1rem;">
                ${renderSection("✅ Strengths", analysis.strengths,
                    "rgba(16,185,129,0.08)", "#10b981", "#6ee7b7", iconCheck)}
                ${renderSection("💡 Suggestions", analysis.suggestions,
                    "rgba(59,130,246,0.08)", "#3b82f6", "#93c5fd", iconStar)}
            </div>

            <!-- WHO CAN / WHO SHOULD AVOID -->
            <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:1rem;">
                ${renderSection("✅ Who Can Consume", analysis.can_consume,
                    "rgba(16,185,129,0.06)", "#10b981", "#6ee7b7", iconCheck)}
                ${renderSection("🚫 Who Should Avoid", analysis.should_avoid,
                    "rgba(244,63,94,0.06)", "#f43f5e", "#fca5a5", iconBan)}
            </div>

            <!-- BETTER ALTERNATIVES + COMPENSATION PLAN -->
            <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:1rem;">
                ${renderSection("🌿 Better Alternatives", analysis.better_alternatives,
                    "rgba(16,185,129,0.06)", "#10b981", "#6ee7b7", iconLeaf)}
                ${renderSection("📋 Recovery Plan", analysis.compensation_plan,
                    "rgba(139,92,246,0.08)", "#8b5cf6", "#c4b5fd", iconHeart)}
            </div>

            ${(analysis.ingredients && analysis.ingredients.length) ? `
            <div style="background:rgba(255,255,255,0.02);border:1px solid rgba(255,255,255,0.07);
                border-radius:var(--radius-md);padding:1rem;">
                <p style="font-size:0.8rem;text-transform:uppercase;letter-spacing:0.08em;color:var(--text-secondary);margin-bottom:0.5rem;">Ingredients</p>
                <p style="font-size:0.9rem;line-height:1.7;">${analysis.ingredients.join(", ")}</p>
            </div>` : ""}
        </div>`;
    };

    const scanRequest = async (options) => {
        statusText.textContent = "🔍 Analysing bottle...";
        resultBody.className = "empty-state";
        resultBody.innerHTML = `
            <div style="text-align:center;padding:2rem;">
                <div style="width:48px;height:48px;border:3px solid rgba(16,185,129,0.3);
                    border-top-color:#10b981;border-radius:50%;animation:spin 1s linear infinite;margin:0 auto 1rem;"></div>
                <p>Running YOLO detection and health analysis…</p>
            </div>
            <style>@keyframes spin{to{transform:rotate(360deg)}}</style>`;
        const response = await fetch("/api/scan", options);
        const payload = await response.json();
        if (!response.ok || !payload.ok) {
            statusText.textContent = "❌ Scan failed";
            resultBody.innerHTML = `<p style="color:var(--accent-rose);">${payload.message || "Unable to analyse the image."}</p>`;
            return;
        }
        renderResult(payload);
        // Scroll result into view
        document.getElementById("scanResultCard")?.scrollIntoView({ behavior: "smooth", block: "start" });
    };

    uploadForm?.addEventListener("submit", async (event) => {
        event.preventDefault();
        const formData = new FormData(uploadForm);
        await scanRequest({ method: "POST", body: formData });
    });

    startCameraBtn?.addEventListener("click", async () => {
        try {
            stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
            webcamFeed.srcObject = stream;
            statusText.textContent = "📷 Camera started. Capture when the bottle label is clear.";
        } catch (error) {
            statusText.textContent = "Camera access failed.";
            resultBody.innerHTML = `<p style="color:var(--accent-rose);">Unable to access webcam: ${error}</p>`;
        }
    });

    captureBtn?.addEventListener("click", async () => {
        if (!webcamFeed.videoWidth) {
            statusText.textContent = "Start the camera first.";
            return;
        }
        captureCanvas.width = webcamFeed.videoWidth;
        captureCanvas.height = webcamFeed.videoHeight;
        const ctx = captureCanvas.getContext("2d");
        ctx.drawImage(webcamFeed, 0, 0, captureCanvas.width, captureCanvas.height);
        const image = captureCanvas.toDataURL("image/jpeg", 0.92);
        await scanRequest({
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ image }),
        });
    });
})();
