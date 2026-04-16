from html import escape


def render_staging_home() -> str:
    return _page_shell(
        title="Room Cleanliness Staging",
        body="""
        <section class="hero">
          <div>
            <p class="eyebrow">Internal Staging</p>
            <h1>Room Cleanliness Tester</h1>
            <p class="lede">
              Upload a room image, inspect the model output, and review recent predictions
              through a lightweight internal interface.
            </p>
          </div>
          <div class="hero-actions">
            <a class="button" href="/staging/upload">Upload Test Image</a>
            <a class="button button-secondary" href="/staging/review-queue">Open Review Queue</a>
            <a class="button button-secondary" href="/staging/saved-reviews">Saved Reviews</a>
          </div>
        </section>
        <section class="cards">
          <article class="card">
            <h2>Upload Flow</h2>
            <p>Use a real image and send it through the same classify path the API already exposes.</p>
          </article>
          <article class="card">
            <h2>Prediction Review</h2>
            <p>Open any prediction, inspect the explanations, and submit an admin review.</p>
          </article>
          <article class="card">
            <h2>Summary Visibility</h2>
            <p>Track pending review count, classification mix, and estimated model spend during testing.</p>
          </article>
          <article class="card">
            <h2>Saved Reviews</h2>
            <p>Browse predictions that already have a reviewer decision and comment attached.</p>
          </article>
        </section>
        """,
    )


def render_upload_page() -> str:
    return _page_shell(
        title="Upload Test Image",
        body="""
        <section class="stack">
          <div class="page-header">
            <div>
              <p class="eyebrow">Staging Upload</p>
              <h1>Upload And Classify</h1>
            </div>
            <div class="hero-actions">
              <a class="button button-secondary" href="/staging/review-queue">Review Queue</a>
              <a class="button button-secondary" href="/staging/saved-reviews">Saved Reviews</a>
            </div>
          </div>
          <form id="upload-form" class="panel">
            <label>
              <span>Image file</span>
              <input id="image-file" type="file" accept="image/*,.heic,.heif" required />
            </label>
            <p class="muted">
              Common image types are supported for staging uploads. Files that are not already JPEG or PNG will be converted to JPEG in the browser before classification.
            </p>
            <label>
              <span>Room type</span>
              <input id="room-type" type="text" placeholder="bedroom" />
            </label>
            <label>
              <span>Source tag</span>
              <input id="source" type="text" placeholder="product-staging" value="staging-ui" />
            </label>
            <button class="button" type="submit">Classify Image</button>
          </form>
          <div id="upload-status" class="status" aria-live="polite"></div>
        </section>
        <script>
          const form = document.getElementById("upload-form");
          const status = document.getElementById("upload-status");

          form.addEventListener("submit", async (event) => {
            event.preventDefault();
            const fileInput = document.getElementById("image-file");
            const roomType = document.getElementById("room-type").value || null;
            const source = document.getElementById("source").value || null;
            const file = fileInput.files && fileInput.files[0];
            if (!file) {
              status.innerHTML = "<p class='error'>Choose an image before submitting.</p>";
              return;
            }

            status.innerHTML = "<p>Uploading image and running classification...</p>";
            let dataUrl;
            try {
              dataUrl = await normalizeImageForUpload(file);
            } catch (error) {
              status.innerHTML = "<p class='error'>That image type could not be processed in the browser. Try JPEG, PNG, or WebP.</p>";
              return;
            }
            const response = await fetch("/classify", {
              method: "POST",
              headers: {"Content-Type": "application/json"},
              body: JSON.stringify({
                image_base64: dataUrl,
                image_role: "after",
                room_type: roomType,
                source: source
              })
            });

            if (!response.ok) {
              status.innerHTML = "<p class='error'>Classification failed. Check the API response and try again.</p>";
              return;
            }

            const payload = await response.json();
            window.location.href = `/staging/predictions/${payload.prediction_id}`;
          });

          async function normalizeImageForUpload(file) {
            const type = (file.type || "").toLowerCase();
            if (type === "image/jpeg" || type === "image/png") {
              return readFileAsDataUrl(file);
            }
            return convertImageToJpeg(file);
          }

          function readFileAsDataUrl(file) {
            return new Promise((resolve, reject) => {
              const reader = new FileReader();
              reader.onload = () => resolve(reader.result);
              reader.onerror = reject;
              reader.readAsDataURL(file);
            });
          }

          async function convertImageToJpeg(file) {
            const objectUrl = URL.createObjectURL(file);
            try {
              const image = await loadImage(objectUrl);
              const canvas = document.createElement("canvas");
              canvas.width = image.naturalWidth || image.width;
              canvas.height = image.naturalHeight || image.height;
              const context = canvas.getContext("2d");
              if (!context) {
                throw new Error("2d canvas not available");
              }
              context.fillStyle = "#ffffff";
              context.fillRect(0, 0, canvas.width, canvas.height);
              context.drawImage(image, 0, 0);
              return canvas.toDataURL("image/jpeg", 0.92);
            } finally {
              URL.revokeObjectURL(objectUrl);
            }
          }

          function loadImage(src) {
            return new Promise((resolve, reject) => {
              const image = new Image();
              image.onload = () => resolve(image);
              image.onerror = reject;
              image.src = src;
            });
          }
        </script>
        """,
    )


def render_prediction_page(prediction_id: str) -> str:
    escaped_id = escape(prediction_id)
    return _page_shell(
        title=f"Prediction {escaped_id}",
        body=f"""
        <section class="stack">
          <div class="page-header">
            <div>
              <p class="eyebrow">Prediction Detail</p>
              <h1>Prediction {escaped_id}</h1>
            </div>
            <div class="hero-actions">
              <a class="button button-secondary" href="/staging/upload">Upload Another</a>
              <a class="button button-secondary" href="/staging/review-queue">Review Queue</a>
              <a class="button button-secondary" href="/staging/saved-reviews">Saved Reviews</a>
            </div>
          </div>
          <div id="prediction-status" class="status" aria-live="polite"></div>
          <div class="metric-grid">
            <article class="metric-card">
              <p class="metric-label">Classification</p>
              <p id="classification-badge" class="metric-value">Loading...</p>
            </article>
            <article class="metric-card">
              <p class="metric-label">Confidence</p>
              <p id="confidence-value" class="metric-value">--</p>
            </article>
            <article class="metric-card">
              <p class="metric-label">Recommended Action</p>
              <p id="action-value" class="metric-value">--</p>
            </article>
            <article class="metric-card">
              <p class="metric-label">Estimated Cost</p>
              <p id="cost-value" class="metric-value">--</p>
            </article>
          </div>
          <div class="detail-grid">
            <div class="panel">
              <h2>Submitted Image</h2>
              <div class="preview-shell">
                <img id="prediction-image" class="prediction-image" alt="Submitted room image preview" hidden />
                <p id="prediction-image-fallback" class="muted">Loading image preview...</p>
              </div>
            </div>
            <div class="panel">
              <h2>Model Output</h2>
              <div class="stack compact">
                <div>
                  <h3>Visible Reasons</h3>
                  <ul id="visible-reasons" class="reason-list">
                    <li class="muted">Loading reasons...</li>
                  </ul>
                </div>
                <div>
                  <h3>Image Quality</h3>
                  <p id="image-quality-reason" class="muted">Loading image-quality details...</p>
                  <p id="image-quality-guidance" class="muted"></p>
                </div>
                <div>
                  <h3>Model Metadata</h3>
                  <p id="model-version" class="muted">Loading model version...</p>
                  <p id="prediction-meta" class="muted"></p>
                </div>
              </div>
            </div>
            <div class="panel">
              <h2>Submit Admin Review</h2>
              <form id="review-form" class="stack compact">
                <label>
                  <span>Final classification</span>
                  <select id="final-classification">
                    <option value="clean">clean</option>
                    <option value="borderline">borderline</option>
                    <option value="dirty">dirty</option>
                  </select>
                </label>
                <label>
                  <span>Reviewer</span>
                  <input id="reviewer" type="text" placeholder="product-reviewer" required />
                </label>
                <label>
                  <span>Admin comment</span>
                  <textarea id="admin-comment" rows="4" placeholder="What looked right or wrong?"></textarea>
                </label>
                <button class="button" type="submit">Save Review</button>
              </form>
            </div>
            <div class="panel">
              <h2>Saved Review</h2>
              <div id="saved-review" class="stack compact">
                <p class="muted">No review saved yet.</p>
              </div>
            </div>
          </div>
          <details class="panel">
            <summary><strong>Raw Prediction JSON</strong></summary>
            <pre id="prediction-json">Loading prediction...</pre>
          </details>
          <details class="panel">
            <summary><strong>How To Use This Result</strong></summary>
            <p class="muted">
              Review the image, confirm whether the classification makes product sense, and save a final admin review if the output should be overridden or documented.
            </p>
          </div>
        </section>
        <script>
          const predictionId = {escaped_id!r};
          const predictionJson = document.getElementById("prediction-json");
          const status = document.getElementById("prediction-status");
          const reviewForm = document.getElementById("review-form");
          const finalClassification = document.getElementById("final-classification");
          const reviewer = document.getElementById("reviewer");
          const adminComment = document.getElementById("admin-comment");
          const predictionImage = document.getElementById("prediction-image");
          const predictionImageFallback = document.getElementById("prediction-image-fallback");
          const classificationBadge = document.getElementById("classification-badge");
          const confidenceValue = document.getElementById("confidence-value");
          const actionValue = document.getElementById("action-value");
          const costValue = document.getElementById("cost-value");
          const visibleReasons = document.getElementById("visible-reasons");
          const imageQualityReason = document.getElementById("image-quality-reason");
          const imageQualityGuidance = document.getElementById("image-quality-guidance");
          const modelVersion = document.getElementById("model-version");
          const predictionMeta = document.getElementById("prediction-meta");
          const savedReview = document.getElementById("saved-review");

          loadPrediction();

          reviewForm.addEventListener("submit", async (event) => {{
            event.preventDefault();
            status.innerHTML = "<p>Saving review...</p>";
            const response = await fetch(`/predictions/${{predictionId}}/review`, {{
              method: "POST",
              headers: {{"Content-Type": "application/json"}},
              body: JSON.stringify({{
                final_classification: finalClassification.value,
                admin_comment: adminComment.value || "Reviewed in staging UI.",
                reviewer: reviewer.value || "staging-reviewer"
              }})
            }});

            if (!response.ok) {{
              status.innerHTML = "<p class='error'>Could not save review.</p>";
              return;
            }}

            status.innerHTML = "<p>Review saved.</p>";
            await loadPrediction();
          }});

          async function loadPrediction() {{
            const response = await fetch(`/predictions/${{predictionId}}`);
            if (!response.ok) {{
              predictionJson.textContent = "Prediction not found.";
              return;
            }}
            const payload = await response.json();
            predictionJson.textContent = JSON.stringify(payload, null, 2);
            finalClassification.value = payload.response.classification;
            classificationBadge.textContent = payload.response.classification;
            classificationBadge.className = "metric-value badge badge-" + payload.response.classification;
            confidenceValue.textContent = Math.round((payload.response.confidence || 0) * 100) + "%";
            actionValue.textContent = payload.response.recommended_action;
            costValue.textContent = "$" + (payload.response.model_usage.estimated_cost_usd || 0).toFixed(6);
            visibleReasons.innerHTML = renderReasonList(payload.response.visible_reasons || []);
            imageQualityReason.textContent = payload.response.image_quality.reason;
            imageQualityGuidance.textContent = "Guidance: " + payload.response.image_quality.retake_guidance;
            modelVersion.textContent = "Model: " + payload.response.model_version;
            predictionMeta.textContent = "Needs review: " + (payload.response.needs_review ? "yes" : "no") + " · Prediction ID: " + payload.prediction_id;
            savedReview.innerHTML = renderSavedReview(payload.admin_review);
            predictionImage.src = `/predictions/${{predictionId}}/image`;
            predictionImage.hidden = false;
            predictionImageFallback.textContent = "If the preview does not load, the image is not available through the current storage path.";
          }}

          predictionImage.addEventListener("load", () => {{
            predictionImageFallback.hidden = true;
          }});

          predictionImage.addEventListener("error", () => {{
            predictionImage.hidden = true;
            predictionImageFallback.hidden = false;
            predictionImageFallback.textContent = "Image preview is not available for this prediction.";
          }});

          function renderReasonList(reasons) {{
            if (!reasons.length) {{
              return "<li class='muted'>No visible reasons were provided.</li>";
            }}
            return reasons.map((reason) => "<li>" + escapeHtml(reason) + "</li>").join("");
          }}

          function renderSavedReview(review) {{
            if (!review) {{
              return "<p class='muted'>No review saved yet.</p>";
            }}
            return "<div class='review-summary'>"
              + "<p><strong>Final classification:</strong> " + escapeHtml(review.final_classification) + "</p>"
              + "<p><strong>Reviewer:</strong> " + escapeHtml(review.reviewer) + "</p>"
              + "<p><strong>Comment:</strong> " + escapeHtml(review.admin_comment) + "</p>"
              + "</div>";
          }}

          function escapeHtml(value) {{
            const div = document.createElement("div");
            div.textContent = value ?? "";
            return div.innerHTML;
          }}
        </script>
        """,
    )


def render_review_queue_page() -> str:
    return _page_shell(
        title="Review Queue",
        body="""
        <section class="stack">
          <div class="page-header">
            <div>
              <p class="eyebrow">Review Queue</p>
              <h1>Pending Predictions</h1>
            </div>
            <div class="hero-actions">
              <a class="button" href="/staging/upload">Upload Test Image</a>
              <a class="button button-secondary" href="/staging">Home</a>
              <a class="button button-secondary" href="/staging/saved-reviews">Saved Reviews</a>
            </div>
          </div>
          <div class="detail-grid">
            <div class="panel">
              <h2>Pending Review</h2>
              <div id="queue-list">Loading queue...</div>
            </div>
            <div class="panel">
              <h2>Summary</h2>
              <pre id="summary-json">Loading summary...</pre>
            </div>
          </div>
        </section>
        <script>
          loadQueue();
          loadSummary();

          async function loadQueue() {
            const response = await fetch("/predictions?pending_only=true&limit=25");
            if (!response.ok) {
              document.getElementById("queue-list").innerHTML = "<p class='error'>Could not load predictions.</p>";
              return;
            }
            const payload = await response.json();
            if (!payload.predictions.length) {
              document.getElementById("queue-list").innerHTML = "<p>No pending predictions right now.</p>";
              return;
            }

            const rows = payload.predictions.map((prediction) => `
              <article class="queue-item">
                <div>
                  <strong>${prediction.prediction_id}</strong>
                  <p>${prediction.response.classification} · ${prediction.response.recommended_action}</p>
                  <p class="muted">${prediction.source || "unknown source"} · ${prediction.room_type || "unknown room type"}</p>
                </div>
                <a class="button button-secondary" href="/staging/predictions/${prediction.prediction_id}">Open</a>
              </article>
            `).join("");
            document.getElementById("queue-list").innerHTML = rows;
          }

          async function loadSummary() {
            const response = await fetch("/reports/summary");
            if (!response.ok) {
              document.getElementById("summary-json").textContent = "Could not load summary.";
              return;
            }
            const payload = await response.json();
            document.getElementById("summary-json").textContent = JSON.stringify(payload, null, 2);
          }
        </script>
        """,
    )


def render_saved_reviews_page() -> str:
    return _page_shell(
        title="Saved Reviews",
        body="""
        <section class="stack">
          <div class="page-header">
            <div>
              <p class="eyebrow">Saved Reviews</p>
              <h1>Reviewed Predictions</h1>
            </div>
            <div class="hero-actions">
              <a class="button" href="/staging/upload">Upload Test Image</a>
              <a class="button button-secondary" href="/staging/review-queue">Review Queue</a>
              <a class="button button-secondary" href="/staging">Home</a>
            </div>
          </div>
          <div class="detail-grid">
            <div class="panel">
              <h2>Saved Review List</h2>
              <div id="reviewed-list">Loading saved reviews...</div>
            </div>
            <div class="panel">
              <h2>Summary</h2>
              <pre id="reviewed-summary-json">Loading summary...</pre>
            </div>
          </div>
        </section>
        <script>
          loadReviewed();
          loadSummary();

          async function loadReviewed() {
            const response = await fetch("/predictions?reviewed_only=true&limit=25");
            if (!response.ok) {
              document.getElementById("reviewed-list").innerHTML = "<p class='error'>Could not load saved reviews.</p>";
              return;
            }
            const payload = await response.json();
            if (!payload.predictions.length) {
              document.getElementById("reviewed-list").innerHTML = "<p>No saved reviews yet.</p>";
              return;
            }

            const rows = payload.predictions.map((prediction) => {
              const review = prediction.admin_review || {};
              return `
                <article class="queue-item">
                  <div>
                    <strong>${prediction.prediction_id}</strong>
                    <p>${prediction.response.classification} → ${review.final_classification || "unknown"}</p>
                    <p class="muted">${review.reviewer || "unknown reviewer"} · ${prediction.source || "unknown source"}</p>
                    <p class="muted">${review.admin_comment || "No comment saved."}</p>
                  </div>
                  <a class="button button-secondary" href="/staging/predictions/${prediction.prediction_id}">Open</a>
                </article>
              `;
            }).join("");
            document.getElementById("reviewed-list").innerHTML = rows;
          }

          async function loadSummary() {
            const response = await fetch("/reports/summary");
            if (!response.ok) {
              document.getElementById("reviewed-summary-json").textContent = "Could not load summary.";
              return;
            }
            const payload = await response.json();
            document.getElementById("reviewed-summary-json").textContent = JSON.stringify(payload, null, 2);
          }
        </script>
        """,
    )


def _page_shell(*, title: str, body: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>{escape(title)}</title>
    <style>
      :root {{
        --bg: #f4f1ea;
        --panel: #fffdfa;
        --ink: #1f2a2e;
        --muted: #5b6a6f;
        --accent: #0b7a75;
        --accent-2: #d96c3f;
        --border: #d9d0c4;
      }}
      * {{ box-sizing: border-box; }}
      body {{
        margin: 0;
        font-family: Georgia, "Times New Roman", serif;
        background: linear-gradient(180deg, #f7f4ee 0%, #ece5d8 100%);
        color: var(--ink);
      }}
      main {{
        max-width: 1080px;
        margin: 0 auto;
        padding: 32px 20px 64px;
      }}
      h1, h2, p {{ margin-top: 0; }}
      .eyebrow {{
        text-transform: uppercase;
        letter-spacing: 0.08em;
        font-size: 0.8rem;
        color: var(--accent);
        font-weight: 700;
      }}
      .hero, .panel, .card {{
        background: var(--panel);
        border: 1px solid var(--border);
        border-radius: 18px;
        box-shadow: 0 16px 40px rgba(31, 42, 46, 0.08);
      }}
      .hero {{
        padding: 28px;
        display: grid;
        gap: 20px;
      }}
      .hero-actions, .page-header {{
        display: flex;
        gap: 12px;
        flex-wrap: wrap;
        justify-content: space-between;
        align-items: center;
      }}
      .cards, .detail-grid {{
        display: grid;
        gap: 18px;
        margin-top: 20px;
      }}
      .metric-grid {{
        display: grid;
        gap: 14px;
        margin-top: 18px;
        grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      }}
      .cards {{ grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); }}
      .detail-grid {{ grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); }}
      .card, .panel {{
        padding: 22px;
      }}
      .metric-card {{
        background: rgba(255, 253, 250, 0.88);
        border: 1px solid var(--border);
        border-radius: 16px;
        padding: 18px;
        box-shadow: 0 10px 24px rgba(31, 42, 46, 0.06);
      }}
      .metric-label {{
        color: var(--muted);
        font-size: 0.85rem;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        margin-bottom: 6px;
      }}
      .metric-value {{
        margin: 0;
        font-size: 1.2rem;
        font-weight: 700;
      }}
      .stack {{ display: grid; gap: 18px; }}
      .compact {{ gap: 12px; }}
      label {{ display: grid; gap: 8px; font-weight: 700; }}
      input, select, textarea {{
        width: 100%;
        padding: 12px 14px;
        border: 1px solid var(--border);
        border-radius: 12px;
        font: inherit;
        background: #fff;
      }}
      .button {{
        display: inline-flex;
        justify-content: center;
        align-items: center;
        padding: 12px 16px;
        border-radius: 999px;
        border: 0;
        background: var(--accent);
        color: white;
        text-decoration: none;
        font-weight: 700;
        cursor: pointer;
      }}
      .button-secondary {{
        background: #e9dfd1;
        color: var(--ink);
      }}
      .status, .muted {{
        color: var(--muted);
      }}
      .error {{
        color: #9e2b25;
        font-weight: 700;
      }}
      pre {{
        white-space: pre-wrap;
        word-break: break-word;
        background: #f8f4ec;
        padding: 14px;
        border-radius: 12px;
        border: 1px solid var(--border);
        overflow: auto;
      }}
      .queue-item {{
        display: flex;
        justify-content: space-between;
        gap: 12px;
        align-items: center;
        padding: 14px 0;
        border-bottom: 1px solid var(--border);
      }}
      .queue-item:last-child {{ border-bottom: none; }}
      .lede {{ font-size: 1.1rem; line-height: 1.5; max-width: 60ch; }}
      .reason-list {{
        margin: 0;
        padding-left: 20px;
      }}
      .badge {{
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: fit-content;
        min-width: 120px;
        padding: 8px 12px;
        border-radius: 999px;
      }}
      .badge-clean {{ background: #d7efe3; color: #14633f; }}
      .badge-borderline {{ background: #f4e4bd; color: #815f0d; }}
      .badge-dirty {{ background: #f2c8c1; color: #8d2d23; }}
      .review-summary {{
        display: grid;
        gap: 8px;
      }}
      .preview-shell {{
        display: grid;
        gap: 10px;
      }}
      .prediction-image {{
        width: 100%;
        max-height: 420px;
        object-fit: contain;
        border-radius: 14px;
        border: 1px solid var(--border);
        background: #f8f4ec;
      }}
      @media (max-width: 720px) {{
        main {{ padding: 20px 14px 48px; }}
        .hero, .panel, .card {{ border-radius: 14px; }}
      }}
    </style>
  </head>
  <body>
    <main>
      {body}
    </main>
  </body>
</html>"""
