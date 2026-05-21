const analysisForm = document.getElementById("analysisForm");
const imageInput = document.getElementById("imageInput");
const analyzeBtn = document.getElementById("analyzeBtn");
const loadingArea = document.getElementById("loadingArea");
const resultsArea = document.getElementById("resultsArea");
const statusArea = document.getElementById("statusArea");
const statusAlert = document.getElementById("statusAlert");

const previewImage = document.getElementById("previewImage");
const summaryText = document.getElementById("summaryText");
const insightsList = document.getElementById("insightsList");
const brandTableBody = document.querySelector("#brandTable tbody");

let shareChart = null;
let countChart = null;

function showStatus(message, type = "warning") {
  statusAlert.className = `alert alert-${type} mb-0`;
  statusAlert.textContent = message;
  statusArea.classList.remove("d-none");
}

function hideStatus() {
  statusArea.classList.add("d-none");
  statusAlert.textContent = "";
}

function setLoading(isLoading) {
  if (isLoading) {
    loadingArea.classList.remove("d-none");
    analyzeBtn.disabled = true;
    analyzeBtn.textContent = "Analyzing...";
  } else {
    loadingArea.classList.add("d-none");
    analyzeBtn.disabled = false;
    analyzeBtn.textContent = "Analyze Shelf";
  }
}

function renderInsights(insights) {
  insightsList.innerHTML = "";

  if (!insights || !insights.length) {
    const li = document.createElement("li");
    li.textContent = "No additional insights returned by AI.";
    insightsList.appendChild(li);
    return;
  }

  insights.forEach((insight) => {
    const li = document.createElement("li");
    li.textContent = insight;
    insightsList.appendChild(li);
  });
}

function renderTable(brands) {
  brandTableBody.innerHTML = "";

  brands.forEach((brand) => {
    const row = document.createElement("tr");

    const brandCell = document.createElement("td");
    const badgeClass = brand.is_focus_brand ? "badge-focus" : "badge-competitor";
    const badgeText = brand.is_focus_brand ? "Focus" : "Competitor";
    brandCell.innerHTML = `${brand.name} <span class="badge ${badgeClass} ms-2">${badgeText}</span>`;

    const countCell = document.createElement("td");
    countCell.textContent = String(brand.count);

    const shareCell = document.createElement("td");
    shareCell.textContent = `${brand.share_percent}%`;

    row.appendChild(brandCell);
    row.appendChild(countCell);
    row.appendChild(shareCell);
    brandTableBody.appendChild(row);
  });
}

function destroyCharts() {
  if (shareChart) {
    shareChart.destroy();
    shareChart = null;
  }

  if (countChart) {
    countChart.destroy();
    countChart = null;
  }
}

function renderCharts(brands) {
  const labels = brands.map((b) => b.name);
  const counts = brands.map((b) => b.count);
  const shares = brands.map((b) => b.share_percent);

  const colorPalette = [
    "#f4b942",
    "#50c9a6",
    "#5bc0eb",
    "#f25f5c",
    "#ffe066",
    "#9bc53d",
    "#e55934",
    "#fa7921",
  ];

  destroyCharts();

  const shareCtx = document.getElementById("shareChart").getContext("2d");
  shareChart = new Chart(shareCtx, {
    type: "doughnut",
    data: {
      labels,
      datasets: [
        {
          data: shares,
          backgroundColor: colorPalette,
          borderWidth: 1,
          borderColor: "rgba(255,255,255,0.15)",
        },
      ],
    },
    options: {
      plugins: {
        legend: { labels: { color: "#f7fafc" } },
      },
    },
  });

  const countCtx = document.getElementById("countChart").getContext("2d");
  countChart = new Chart(countCtx, {
    type: "bar",
    data: {
      labels,
      datasets: [
        {
          label: "Estimated Product Count",
          data: counts,
          backgroundColor: colorPalette,
        },
      ],
    },
    options: {
      scales: {
        x: { ticks: { color: "#f7fafc" }, grid: { color: "rgba(255,255,255,0.1)" } },
        y: { ticks: { color: "#f7fafc" }, grid: { color: "rgba(255,255,255,0.1)" } },
      },
      plugins: {
        legend: { labels: { color: "#f7fafc" } },
      },
    },
  });
}

function renderResults(data) {
  const imageUrl = `data:${data.image_mime_type};base64,${data.image_preview_base64}`;
  previewImage.src = imageUrl;
  summaryText.textContent = data.summary || "No summary returned.";

  const brands = Array.isArray(data.brands) ? data.brands : [];
  renderTable(brands);
  renderInsights(data.insights || []);
  renderCharts(brands);

  if (data.warning) {
    showStatus(data.warning, "warning");
  } else if (data.used_mock_data) {
    showStatus("Showing mock fallback data for demo continuity.", "warning");
  } else {
    hideStatus();
  }

  resultsArea.classList.remove("d-none");
}

analysisForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  hideStatus();

  const file = imageInput.files[0];
  if (!file) {
    showStatus("Please select an image before analyzing.", "danger");
    return;
  }

  const formData = new FormData();
  formData.append("image", file);

  setLoading(true);

  try {
    const response = await fetch("/analyze", {
      method: "POST",
      body: formData,
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.error || "Failed to analyze image.");
    }

    renderResults(data);
  } catch (error) {
    showStatus(error.message || "Analysis failed. Please try again.", "danger");
  } finally {
    setLoading(false);
  }
});
