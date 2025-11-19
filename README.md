# 🍽️ ZeCo Restaurant Management System

A modern, full-stack restaurant management solution featuring a dynamic React frontend and a robust FastAPI backend.

## 🚀 Quick Start

The easiest way to run the entire application is using Docker Compose.

```bash
# Clone the repository
git clone <repository-url>
cd ZeCo

# Start the application
docker-compose up -d --build
```

Once running:
- **Frontend:** [http://localhost:5173](http://localhost:5173)
- **Backend API:** [http://localhost:8000/docs](http://localhost:8000/docs)

## 🏗️ Project Structure

```
ZeCo/
├── 📂 frontend/          # React + Vite application
│   ├── theme.json       # Centralized theme configuration
│   ├── src/             # Source code
│   └── Dockerfile       # Frontend container config
│
├── 📂 backend/           # FastAPI application
│   ├── api/             # API routes and endpoints
│   ├── database/        # Database models and session
│   ├── services/        # Business logic
│   ├── DATABASE.db      # SQLite database (persisted via volume)
│   └── Dockerfile       # Backend container config
│
├── 📂 assets/            # Generated branding assets (logos, icons)
└── 📄 docker-compose.yml # Orchestration for both services
```

## 🌟 Key Features

- **🎨 Automated Theming System:** Change the entire look of the app by editing a single `theme.json` file.
- **📱 Responsive Design:** Fully optimized for mobile, tablet, and desktop.
- **🔐 Secure Authentication:** JWT-based auth with role management (Admin, Client, Staff).
- **🛒 Shopping Cart:** Real-time cart management.
- **📦 Inventory Management:** Track stock, ingredients, and menu items.

## 🛠️ Tech Stack

### Frontend
- **Framework:** React 18
- **Build Tool:** Vite
- **Styling:** CSS Variables (Auto-generated)
- **State Management:** React Context API

### Backend
- **Framework:** FastAPI (Python)
- **Database:** SQLite (with SQLAlchemy ORM)
- **Authentication:** OAuth2 with Password Flow (JWT)

## 🐳 Docker Configuration

The project uses `docker-compose` to orchestrate the services:

- **Frontend Service:**
  - Maps port `5173` to host.
  - Mounts `./frontend` for live development updates.
  - Automatically regenerates theme on startup.

- **Backend Service:**
  - Maps port `8000` to host.
  - Mounts `./backend` to persist the `DATABASE.db` file.
  - Hot-reloads on code changes.

## 📝 License

This project is licensed under the MIT License.
