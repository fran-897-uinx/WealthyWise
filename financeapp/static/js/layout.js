

// ===================== SIDEBAR TOGGLE ===================== //
function toggleSidebar() {
  const sidebar = document.getElementById("sidebar");
  const overlay = document.getElementById("mobileOverlay");

  if (sidebar && overlay) {
    sidebar.classList.toggle("open");
    overlay.classList.toggle("show");
  }
}

toggleSidebar();

// ===================== THEME SYSTEM ===================== //
document.addEventListener("DOMContentLoaded", () => {
  const darkModeToggle = document.getElementById("darkModeToggle");

  // Load saved theme
  const savedTheme = localStorage.getItem("theme") || "dark";
  document.documentElement.setAttribute("data-theme", savedTheme);
  if (savedTheme === "dark") darkModeToggle.classList.add("active");

  // Toggle click
  darkModeToggle.addEventListener("click", () => {
    darkModeToggle.classList.toggle("active");
    const newTheme = darkModeToggle.classList.contains("active") ? "dark" : "light";
    document.documentElement.setAttribute("data-theme", newTheme);
    localStorage.setItem("theme", newTheme);

    // Optional: save to backend
    saveSetting("theme", newTheme);
  });
});




// ===================== LOAD SETTINGS ON START ===================== //
document.addEventListener("DOMContentLoaded", function () {
  // Theme priority: backend attribute → localStorage → default
  const backendTheme = document.documentElement.getAttribute("data-theme");
  const savedTheme = localStorage.getItem("theme") || backendTheme || "dark";
  setTheme(savedTheme);

   const darkModeToggle = document.getElementById("darkModeToggle");
  if (darkModeToggle) {
    if (savedTheme === "dark") {
      darkModeToggle.classList.add("active");
    } else {
      darkModeToggle.classList.remove("active");
    }
  }
  // Currency
  const savedCurrency = localStorage.getItem("currency") || "NGN";
  if (document.getElementById("currencySelect")) {
    document.getElementById("currencySelect").value = savedCurrency;
  }

  // Language
  const savedLanguage = localStorage.getItem("language") || "en";
  if (document.getElementById("languageSelect")) {
    document.getElementById("languageSelect").value = savedLanguage;
  }

  // Notifications toggle
  const notificationsEnabled = localStorage.getItem("notifications") !== "false";
  if (document.getElementById("notificationsToggle")) {
    document
      .getElementById("notificationsToggle")
      .classList.toggle("active", notificationsEnabled);
  }

  // Auto categorize toggle
  const autoCategorizeEnabled = localStorage.getItem("autoCategorize") !== "false";
  if (document.getElementById("autoCategorizeToggle")) {
    document
      .getElementById("autoCategorizeToggle")
      .classList.toggle("active", autoCategorizeEnabled);
  }
});

// ===================== TOGGLE HANDLERS ===================== //
function toggleNotifications() {
  handleToggle("notificationsToggle", "notifications");
}

function toggleAutoCategorize() {
  handleToggle("autoCategorizeToggle", "autoCategorize");
}

function toggleTwoFactor() {
  handleToggle("twoFactorToggle", "twoFactor");
}

function toggleEmailAlerts() {
  handleToggle("emailAlertsToggle", "emailAlerts");
}

// Generic toggle function
function handleToggle(elementId, settingKey) {
  const toggle = document.getElementById(elementId);
  toggle.classList.toggle("active");

  const isEnabled = toggle.classList.contains("active");
  localStorage.setItem(settingKey, isEnabled);
  saveSetting(settingKey, isEnabled);
}

// ===================== SELECT HANDLERS ===================== //
if (document.getElementById("languageSelect")) {
  document.getElementById("languageSelect").addEventListener("change", (e) => {
    const selectedLang = e.target.value;
    localStorage.setItem("language", selectedLang);
    saveSetting("language", selectedLang);
  });
}

if (document.getElementById("currencySelect")) {
  document.getElementById("currencySelect").addEventListener("change", (e) => {
    const selectedCurrency = e.target.value;
    localStorage.setItem("currency", selectedCurrency);
    saveSetting("currency", selectedCurrency);
  });
}

// ===================== SAVE TO BACKEND ===================== //
function saveSetting(key, value) {
  fetch(SAVE_SETTING_URL, {   // ✅ now it works
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": getCSRFToken(),
    },
    body: JSON.stringify({ key, value }),
  })
  .then((res) => res.json())
  .then((data) => {
    if (data.success) {
      console.log("Setting saved:", data.message);
      showToast(data.message, "success");
    } else {
      console.error("Error saving setting:", data.message);
      showToast("Error saving: " + data.message, "error");
    }
  })
  .catch((err) => {
    console.error("Error saving setting:", err);
    showToast("Error saving setting", "error");
  });
}

// CSRF helper
function getCSRFToken() {
  const name = "csrftoken";
  const cookies = document.cookie.split("; ");
  for (let cookie of cookies) {
    if (cookie.startsWith(name + "=")) {
      return cookie.split("=")[1];
    }
  }
  return "";
}

// ===================== TOAST NOTIFICATIONS ===================== //
function showToast(message, type = "success") {
  let toastContainer = document.getElementById("toastContainer");
  if (!toastContainer) {
    toastContainer = document.createElement("div");
    toastContainer.id = "toastContainer";
    toastContainer.style.cssText = `
      position: fixed;
      top: 20px;
      right: 20px;
      z-index: 9999;
    `;
    document.body.appendChild(toastContainer);
  }

  const toast = document.createElement("div");
  toast.className = `toast toast-${type}`;
  toast.style.cssText = `
    background: white;
    color:#0a0a0f;
    border-radius: 8px;
    padding: 16px 20px;
    margin-bottom: 10px;
    box-shadow: 0 4px 20px rgba(0,0,0,0.15);
    display: flex;
    align-items: center;
    gap: 12px;
    transform: translateX(100%);
    transition: transform 0.3s ease;
    border-left: 4px solid ${type === "success" ? "#10b981" : "#ef4444"};
  `;

  const icon = type === "success" ? "✅" : "❌";
  toast.innerHTML = `
    <span class="toast-icon">${icon}</span>
    <span class="toast-message">${message}</span>
  `;

  toastContainer.appendChild(toast);

  setTimeout(() => (toast.style.transform = "translateX(0)"), 100);
  setTimeout(() => {
    toast.style.transform = "translateX(100%)";
    setTimeout(() => toast.remove(), 300);
  }, 3000);
}


// ===================== SETTINGS PANEL ===================== //
function initSettingsPanel() {
  const settingsBtn = document.getElementById("settingsBtn");
  const settingsPanel = document.getElementById("settingsPanel");
  const settingsClose = document.getElementById("settingsclose");

  if (settingsBtn && settingsPanel && settingsClose) {
    settingsBtn.addEventListener("click", (e) => {
      e.preventDefault(); // stop link refresh
      settingsPanel.classList.add("show");
      settingsPanel.classList.remove("hide");
    });

    settingsClose.addEventListener("click", (e) => {
      e.preventDefault();
      settingsPanel.classList.add("hide");
      settingsPanel.classList.remove("show");
    });
  }
}

// run when DOM is ready
document.addEventListener("DOMContentLoaded", initSettingsPanel);

