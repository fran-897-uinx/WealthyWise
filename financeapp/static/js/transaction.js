// Wait for DOM to be fully loaded
document.addEventListener("DOMContentLoaded", function () {
  console.log("DOM loaded - initializing transaction functionality");

  // --- TRANSACTION FORM SETUP ---
  let ADD_TRANSACTION_URL = null;
  const form = document.getElementById("transactionForm");

  if (form && form.dataset.url) {
    ADD_TRANSACTION_URL = form.dataset.url;
    console.log("Found URL in data attribute:", ADD_TRANSACTION_URL);
  } else if (window.ADD_TRANSACTION_URL) {
    ADD_TRANSACTION_URL = window.ADD_TRANSACTION_URL;
    console.log("Found URL in global variable:", ADD_TRANSACTION_URL);
  } else {
    console.error("Transaction URL not found!");
    showToast && showToast("Configuration error: Transaction URL not set", "error");
    return;
  }

  // --- CHART INITIALIZATION ---
  initializeChart();

  // --- TRANSACTION FORM HANDLING ---
  if (form) {
    initializeTransactionForm(form, ADD_TRANSACTION_URL);
  }

  // --- OTHER INITIALIZATIONS ---
  initializeTypeCards();
  initializeAccountSelect();
  initializeRippleEffects();
  setDefaultDate();
  safeThemeInitialization();
});

// --- THEME TOGGLE ---
function safeThemeInitialization() {
  const themeToggles = document.querySelectorAll(".theme-toggle");
  themeToggles.forEach((toggle) => {
    toggle.addEventListener("click", function () {
      const current = document.documentElement.getAttribute("data-theme");
      const next = current === "dark" ? "light" : "dark"; // simple toggle
      document.documentElement.setAttribute("data-theme", next);
      console.log("Theme changed to:", next);
    });
  });
}

// --- CHART.JS SETUP ---
function initializeChart() {
  try {
    const chartElement = document.getElementById("balanceChart");
    if (!chartElement) {
      console.warn("Chart element not found, skipping chart initialization");
      return;
    }

    const chartDataElement = document.getElementById("chart-data");
    if (!chartDataElement) {
      console.warn("Chart data element not found, skipping chart initialization");
      return;
    }

    const chartData = JSON.parse(chartDataElement.textContent);
    console.log("Chart data loaded:", chartData);

    // Get theme colors dynamically
    const style = getComputedStyle(document.documentElement);
    const accent = style.getPropertyValue("--accent").trim() || "rgba(59,130,246,0.8)";
    const accent2 = style.getPropertyValue("--accent-2").trim() || "rgba(139,92,246,0.8)";
    const success = style.getPropertyValue("--success").trim() || "rgba(16,185,129,0.8)";

    const ctx = chartElement.getContext("2d");
    new Chart(ctx, {
      type: "line",
      data: {
        labels: chartData.labels,
        datasets: [
          {
            label: "Account Balances",
            data: chartData.data,
            backgroundColor: [accent, accent2, success],
            borderColor: [accent, accent2, success],
            borderWidth: 0,
            borderRadius: 8,
            borderSkipped: false,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: true },
          tooltip: {
            backgroundColor: "rgba(0,0,0,0.8)",
            titleColor: "#fff",
            bodyColor: "#fff",
            borderColor: "rgba(59,130,246,0.3)",
            borderWidth: 1,
            cornerRadius: 8,
            displayColors: false,
            callbacks: {
              label: function (context) {
                return "₦" + context.raw.toLocaleString();
              },
            },
          },
        },
        scales: {
          x: {
            grid: { display: false },
            ticks: {
              color: style.getPropertyValue("--muted").trim() || "#64748b",
              font: { size: 12, weight: "600" },
            },
          },
          y: {
            grid: { color: "rgba(148,163,184,0.1)" },
            ticks: {
              color: style.getPropertyValue("--muted").trim() || "#64748b",
              font: { size: 12, weight: "600" },
              callback: function (value) {
                return "₦" + value.toLocaleString();
              },
            },
          },
        },
        animation: { duration: 1000, easing: "easeInOutQuart" },
      },
    });

    console.log("Chart initialized successfully");
  } catch (error) {
    console.error("Error initializing chart:", error);
  }
}
