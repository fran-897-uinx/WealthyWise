# 💰 WealthyWise

WealthyWise is a modern **personal finance management web app** built with **Django**.  
It helps users **track income, expenses, savings, and spending patterns** with clean dashboards, charts, and insights.

---

## 🚀 Features

- **User Authentication**
  - Signup, login, and password reset (via Gmail or SendGrid).
  - Two-factor authentication (optional).

- **Transactions**
  - Add, edit, and delete income/expense transactions.
  - Categorize expenses (Food, Transport, Rent, Healthcare, etc.).
  - Track balances per account.

- **Analytics & Charts**
  - Weekly, monthly, and yearly breakdowns.
  - Income vs Expense visualization using **Chart.js**.
  - Quick stats (savings rate, emergency fund coverage).
  - Top spending categories.

- **Responsive UI**
  - Sidebar navigation with mobile-friendly design.
  - Light, minimal dashboard optimized for all devices.

- **Notifications**
  - Email confirmation and password resets via **Gmail SMTP** or **SendGrid**.

---

## 🛠️ Tech Stack

- **Backend**: Django (Python 3.13)
- **Database**: PostgreSQL (Render)
- **Frontend**: HTML, CSS, JavaScript, TailwindCSS (with Chart.js for graphs)
- **Deployment**: Render
- **Other Tools**:
  - Django-Allauth (auth management)
  - Django-Two-Factor-Auth (optional 2FA)
  - Whitenoise (static file handling)

---

## ⚙️ Installation & Setup

### 1. Clone Repository
```bash
git clone https://github.com/your-username/wealthywise.git
cd wealthywise

python -m venv env
source env/bin/activate   # On Windows: env\Scripts\activate

pip install -r requirements.txt

Pro tip: If you only want direct dependencies (not every single sub-package), you can use pip-tools:

pip install pip-tools
pip-compile
