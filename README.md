# 📊 Device KPI Dashboard

A Dockerized **Streamlit + FastAPI** dashboard for monitoring electronic measurement devices in a DevOps / Build Engineering environment.

The dashboard provides interactive KPI visualizations, identifies problematic devices, and offers a modern web interface for analyzing test and pipeline data.

---

## 🚀 Features

- 📈 KPI overview for device status and health
- ✅ Test pass rate analysis
- 🔄 Pipeline success monitoring
- ⏱️ Test duration statistics
- 🚨 Detection of problematic devices
- 🔍 Interactive filtering and search
- 📊 Interactive Plotly visualizations
- 🌐 REST API powered by FastAPI
- 🐳 Dockerized frontend and backend
- ⚙️ Automated CI pipeline using GitHub Actions

---

## 🛠️ Tech Stack

### Backend
- Python
- FastAPI
- Pandas

### Frontend
- Streamlit
- Plotly

### DevOps
- Docker
- Docker Compose
- GitHub Actions
- Ruff
- Pytest
- Trivy Security Scanner

---

## 📁 Project Structure

```text
KPI-Dashboards/
│
├── backend/
│   └── api.py
│
├── frontend/
│   └── app.py
│
├── data/
│
├── tests/
│   └── test_smoke.py
│
├── .github/
│   └── workflows/
│       └── ci.yml
│
├── Dockerfile.backend
├── Dockerfile.frontend
├── docker-compose.yml
├── requirements.txt
├── README.md
└── .gitignore
```

---

# ⚡ Getting Started

## Clone the repository

```bash
git clone https://github.com/OmarrHegab/KPI-Dashboards.git
cd KPI-Dashboards
```

---

## Run with Docker (Recommended)

Build and start both frontend and backend:

```bash
docker compose up --build
```

Open the dashboard:

```
http://localhost:8501
```

Backend API:

```
http://localhost:8000
```

---

## Run without Docker

Install the dependencies:

```bash
pip install -r requirements.txt
```

Start the backend:

```bash
python backend/api.py
```

Start the frontend:

```bash
streamlit run frontend/app.py
```

---

# 🐳 Docker

The project is fully containerized.

Docker Compose automatically starts:

- FastAPI backend
- Streamlit frontend
- Docker network

No manual dependency installation is required.

---

# ⚙️ Continuous Integration

Every push to the repository automatically triggers a GitHub Actions pipeline.

The pipeline performs:

- ✅ Ruff linting
- ✅ Ruff formatting checks
- ✅ Pytest execution
- ✅ Docker image build
- ✅ Trivy security scan

This ensures that every commit builds successfully and follows code quality standards.

---

# 📊 Dashboard Overview

The dashboard enables engineers to:

- Monitor device KPIs
- Analyze test results
- Detect failing devices
- Track pipeline success
- Filter devices interactively
- Visualize trends over time

---

# 🔒 Security

The project includes automated vulnerability scanning using **Trivy** during every CI pipeline execution.

---

# 📌 Future Improvements

- User authentication
- Database integration
- PDF and Excel export
- Real-time KPI updates
- Historical trend analysis
- Cloud deployment
- Role-based access control

---

# 👨‍💻 Author

**Omar Hegab**

Computer Science Student  
University of Freiburg

GitHub:
https://github.com/OmarrHegab

---

## 📄 License

This project is intended for educational and portfolio purposes.