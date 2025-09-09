// =========================
// Transactions
// =========================
function addTransaction(event) {
    event.preventDefault();
    const form = event.target;
    const formData = new FormData(form);
    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;

    const submitBtn = form.querySelector('.btn-add');
    submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Adding...';
    submitBtn.disabled = true;

    fetch("/add-transaction/", {   // ✅ use Django URL mapping
        method: "POST",
        headers: {
            "X-CSRFToken": csrfToken,
            "Content-Type": "application/json",
        },
        body: JSON.stringify({
            account_id: formData.get('account'),
            amount: parseFloat(formData.get('amount')),
            type: formData.get('type'),
            description: formData.get('description'),
            category: formData.get('category')
        })
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            closeModal();
            updateDashboardAfterTransaction(data.transaction);
            showNotification(data.message, 'success');
            form.reset();
        } else {
            showNotification('Error: ' + data.message, 'error');
            submitBtn.innerHTML = 'Add Transaction';
            submitBtn.disabled = false;
        }
    })
    .catch(() => {
        showNotification('Error adding transaction', 'error');
        submitBtn.innerHTML = 'Add Transaction';
        submitBtn.disabled = false;
    });
}

function exportData(event) {
    const btn = event.target;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Exporting...';
    btn.disabled = true;
    window.location.href = "/export-csv/";
    setTimeout(() => {
        btn.innerHTML = '<i class="fas fa-download"></i> Export';
        btn.disabled = false;
    }, 2000);
}

// =========================
// Chat
// =========================
function toggleChat() {
    const chatWindow = document.getElementById("chatWindow");
    chatWindow.style.display = (chatWindow.style.display === "none") ? "flex" : "none";
}

async function handleChatInput(event) {
    if (event.key === "Enter") {
        const input = document.getElementById("chatInput");
        const message = input.value.trim();
        if (!message) return;

        const chatMessages = document.getElementById("chatMessages");
        chatMessages.innerHTML += `<div class="user message">${message}</div>`;
        chatMessages.scrollTop = chatMessages.scrollHeight;
        input.value = "";

        const loading = document.createElement("div");
        loading.textContent = "please wait....";
        chatMessages.appendChild(loading);

        try {
            const response = await fetch("/api/", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ text: message })
            });

            const data = await response.json();
            loading.remove();

            if (data.reply) {
                chatMessages.innerHTML += `<div class="message ai">${data.reply}</div>`;
            } else {
                chatMessages.innerHTML += `<div class="message ai" style="color:red;">Error: ${data.error}</div>`;
            }
        } catch (error) {
            loading.remove();
            chatMessages.innerHTML += `<div class="message ai" style="color:red;">Error: ${error}</div>`;
        }
    }
}

function clearChat() {
    const chatMessages = document.getElementById("chatMessages");
    chatMessages.innerHTML = `<div class="chat-message ai">
        Hi! I'm your AI financial assistant. I can help you analyze spending, set budgets, and answer questions about your finances. What would you like to know?
    </div>`;
}

// =========================
// Transactions filter
// =========================
function filterTransactions() {
    const searchTerm = document.getElementById('searchBox').value.toLowerCase();
    document.querySelectorAll('.transaction-item').forEach(tx => {
        tx.style.display = tx.textContent.toLowerCase().includes(searchTerm) ? 'flex' : 'none';
    });
}

// =========================
// Charts
// =========================
const chartData = window.chartData;
let mainChart = null;

function setupChartTabs() {
    const tabButtons = document.querySelectorAll('.chart-tabs .tab-btn');
    tabButtons.forEach(button => {
        button.addEventListener('click', function() {
            tabButtons.forEach(btn => btn.classList.remove('active'));
            this.classList.add('active');
            switchChart(this.dataset.period);
        });
    });
}

function initializeChart() {
    const ctx = document.getElementById('mainChart').getContext('2d');
    const initialData = chartData.week;

    mainChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: initialData.labels,
            datasets: [
                { label: 'Income', data: initialData.income, backgroundColor: '#10b981' },
                { label: 'Expenses', data: initialData.expenses, backgroundColor: '#ef4444' }
            ]
        },
        options: {
            responsive: true,
            plugins: {
                legend: { position: 'top' },
                tooltip: {
                    callbacks: {
                        label: ctx => ctx.dataset.label + ': ₦' + ctx.raw.toLocaleString('en-NG')
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        callback: val => '₦' + val.toLocaleString('en-NG')
                    }
                }
            }
        }
    });
}

function switchChart(period) {
    if (!chartData[period]) return console.error("No data:", period);
    const data = chartData[period];
    mainChart.data.labels = data.labels;
    mainChart.data.datasets[0].data = data.income;
    mainChart.data.datasets[1].data = data.expenses;
    mainChart.config.type = (period === 'year') ? 'line' : 'bar';
    mainChart.update();
}

// =========================
// Quick stats
// =========================
function updateQuickStats() {
    const cat = window.topCategoryData;
    document.querySelector('[data-stat="top-category"]').textContent =
        `${cat.category}: ₦${cat.amount.toLocaleString('en-NG', {minimumFractionDigits: 2})}`;
    document.querySelector('[data-stat="total-balance"]').textContent =
        `₦${window.totalBalance.toLocaleString('en-NG', {minimumFractionDigits: 2})}`;
    document.querySelector('[data-stat="cash-flow"]').textContent =
        `₦${window.netCashFlow.toLocaleString('en-NG', {minimumFractionDigits: 2})}`;
    document.querySelector('[data-stat="emergency-fund"]').textContent =
        `${window.emergencyFundMonths} months`;
    document.querySelector('[data-stat="savings-rate"]').textContent =
        `${window.savingsRate}%`;
}

// =========================
// Utilities
// =========================
function showNotification(message, type = 'success') {
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.innerHTML = `
        <i class="fas fa-${type === 'success' ? 'check-circle' : 'exclamation-circle'}"></i>
        <span>${message}</span>
    `;
    document.body.appendChild(notification);
    setTimeout(() => notification.remove(), 3000);
}

function closeModal() {
    document.getElementById('transactionModal').style.display = 'none';
}

function updateDashboardAfterTransaction(tx) {
    console.log('Transaction added:', tx);
    window.location.reload(); // quick way to refresh
}

// =========================
// Init
// =========================
document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('transactionForm');
    if (form) form.addEventListener('submit', addTransaction);

    if (document.getElementById('mainChart')) {
        initializeChart();
        setupChartTabs();
    }

    const searchBox = document.getElementById('searchBox');
    if (searchBox) searchBox.addEventListener('input', filterTransactions);

    updateQuickStats();

    document.querySelectorAll('.stat-card').forEach(card => {
        card.addEventListener('mouseenter', () => card.style.transform = 'translateY(-5px)');
        card.addEventListener('mouseleave', () => card.style.transform = 'translateY(0)');
    });

    window.addEventListener('load', () => document.body.classList.add('loaded'));
});
