# PriceWatcher

## 📌 Overview
**PriceWatcher** is a Python-based tool that tracks product prices on e-commerce websites and notifies users of price changes. This helps consumers monitor deals, analyze price trends, and make informed purchasing decisions.

## 🚀 Features
- **Automated Price Monitoring** – Track prices from predefined stores.
- **Custom Alerts** – Get notified when a product reaches a target price.
- **Real-time Notifications** – Receive alerts via Telegram, WhatsApp, or email.
- **Historical Data Storage** – Keep track of past price changes.
- **REST API** – Access and manage data remotely.
- **Web Dashboard (Optional)** – Visualize price trends and statistics.

## 🛠️ Technologies Used
- **Python** – Core programming language.
- **Selenium / BeautifulSoup / Scrapy** – Web scraping.
- **FastAPI / Flask** – Backend API.
- **SQLite / PostgreSQL** – Database for storing price history.
- **Celery + Redis** – Asynchronous task processing.
- **Telegram API / Twilio** – Sending notifications.
- **Streamlit / Vue.js** – Optional web dashboard.

## 🔧 Installation
### 1️⃣ Clone the repository
```sh
git clone https://github.com/yourusername/pricewatcher.git
cd pricewatcher
```

### 2️⃣ Create a virtual environment and install dependencies
```sh
python -m venv venv
source venv/bin/activate  # On Windows use: venv\Scripts\activate
pip install -r requirements.txt
```

### 3️⃣ Run the application
```sh
python main.py
```

## 📬 Notifications Setup
To receive notifications via Telegram or WhatsApp, configure the API keys in the `.env` file.

## 📈 Future Improvements
- Support for more e-commerce websites.
- Improved scraping performance.
- Additional notification methods (Slack, Discord, etc.).

## 📜 License
This project is licensed under the MIT License.

---

🔥 **Contributions are welcome!** Feel free to submit issues or pull requests.

🚀 Happy tracking!

