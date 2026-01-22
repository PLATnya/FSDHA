
## Implemented bonuses
- **Automatic Progress Updates** via WebSocket
- - don't work with docker and frontend production preview mode
don't know why. It's some websocket problem
have no time for test task left to deal with it)
- **Downloadable Error Report**

## Tech Stack

### Backend
- **FastAPI** - Modern Python web framework
- **SQLAlchemy** - ORM for database operations
- **MySQL** - Database (via aiomysql)
- **WebSockets** - Real-time job progress updates
- **Uvicorn** - ASGI server

### Frontend
- **React 19** - UI library
- **TypeScript** - Type-safe JavaScript
- **Material-UI (MUI)** - Component library
- **Vite** - Build tool and dev server
- **WebSockets** - Real-time updates

## Prerequisites

Before you begin, ensure you have the following installed:

- **Python 3.10+**
- **Node.js 18+** and npm
- **MySQL 8.0+**
- **Git**

## Project Structure

```
FSDHA/
├── backend/                 # FastAPI backend
│   ├── controllers/        # Request handlers
│   ├── routers/            # API route definitions
│   ├── services/          # Business logic
│   ├── middleware/         # CORS, error handling
│   ├── schemas/           # Validation schemas
│   ├── main.py            # Application entry point
│   ├── database.py        # Database models
│   └── requirements.txt   # Python dependencies
├── frontend/              # React frontend
│   ├── src/
│   │   ├── components/   # React components
│   │   ├── App.tsx       # Main app component
│   │   └── main.tsx       # Entry point
│   └── package.json       # Node dependencies
└── input_data/            # Sample CSV files
```

## Setup Guide

### 1. Database Setup

1. **Install MySQL** (if not already installed):
   ```bash
   # Ubuntu/Debian
   sudo apt-get update
   sudo apt-get install mysql-server
   sudo systemctl start mysql
   sudo systemctl enable mysql

2. **Create the database**:
   ```bash
   mysql -u root -p
   ```
   ```sql
   CREATE DATABASE fsdha_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
   EXIT;
   ```

3. **Note the database credentials** - you'll need them for the `.env` file.

### 2. Backend Setup

1. **Navigate to the backend directory**:
   ```bash
   cd backend
   ```

2. **Create a virtual environment** (recommended):
   ```bash
   # Using venv
   python3 -m venv venv
   
   # Activate virtual environment
   # On Linux/macOS:
   source venv/bin/activate
   # On Windows:
   venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Create a `.env` file** in the `backend/` directory:

   Add the following environment variables:
   ```env
   # Database Configuration
   MYSQL_USER=root
   MYSQL_PASSWORD=your_mysql_password
   MYSQL_HOST=localhost
   MYSQL_PORT=3306
   MYSQL_DATABASE=fsdha_db

   # Optional: Logging
   LOG_LEVEL=INFO

   # Optional: SQL Query Logging (set to "true" for debugging)
   SQL_ECHO=False

   # Optional: CORS (comma-separated list of allowed origins)
   CORS_ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173
   ```

5. **Run database migrations** (tables are created automatically on first run):
   ```bash
   python -m uvicorn main:app --reload
   ```
   The application will automatically create all necessary tables on startup.

### 3. Frontend Setup

1. **Navigate to the frontend directory**:
   ```bash
   cd frontend
   ```

2. **Install dependencies**:
   ```bash
   npm install
   ```

3. **Create a `.env` file** in the `frontend/` directory (optional):
   ```env
   # API Target (default: http://localhost:8000)
   VITE_API_TARGET=http://localhost:8000

   # WebSocket Target (optional, defaults to API target)
   VITE_WS_TARGET=ws://localhost:8000

   # Dev Server Configuration (optional)
   VITE_DEV_HOST=0.0.0.0
   VITE_DEV_PORT=3000
   ```

   **Note**: The frontend will work with defaults if no `.env` file is provided.

### 4. Running the Application

#### Start the Backend

1. **Activate your virtual environment** (if using one):
   ```bash
   cd backend
   source venv/bin/activate  # Linux/macOS
   ```

2. **Start the FastAPI server**:
   ```bash
   python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```

   The API will be available at: `http://localhost:8000`
   - API Documentation: `http://localhost:8000/docs`
   - Alternative docs: `http://localhost:8000/redoc`

#### Start the Frontend

1. **In a new terminal**, navigate to the frontend directory:
   ```bash
   cd frontend
   ```

2. **Start the development server**:
   ```bash
   npm run dev
   ```

   The frontend will be available at: `http://localhost:3000` (or the port specified in your config)

## Usage

1. **Open the application** in your browser at `http://localhost:3000`

2. **Upload a CSV file**:
   - Click "Choose CSV" and select a CSV file
   - The CSV should have columns: `name`, `email`, `phone`, `company`
   - Click "Upload" to start processing

3. **Monitor job progress**:
   - View real-time updates in the Jobs list
   - Expand a job row to see details and errors
   - Download error reports as CSV

## API Endpoints

### Jobs
- `GET /api/jobs` - List all jobs
- `GET /api/jobs/{job_id}` - Get job details
- `POST /api/jobs/upload` - Upload and process CSV file
- `DELETE /api/jobs/reset` - Delete all jobs and data
- `GET /api/jobs/{job_id}/error-report` - Download error report CSV

### Customers
- `GET /api/customers` - List all customers (with pagination)
- `GET /api/customers/{customer_id}` - Get customer details

### WebSocket
- `WS /ws/jobs/{job_id}` - Real-time job progress updates

## Environment Variables Reference

### Backend (.env in `backend/`)

| Variable | Description | Default |
|----------|-------------|---------|
| `MYSQL_USER` | MySQL username | `root` |
| `MYSQL_PASSWORD` | MySQL password | (empty) |
| `MYSQL_HOST` | MySQL host | `localhost` |
| `MYSQL_PORT` | MySQL port | `3306` |
| `MYSQL_DATABASE` | Database name | `fsdha_db` |
| `LOG_LEVEL` | Logging level (DEBUG, INFO, WARNING, ERROR) | `INFO` |
| `SQL_ECHO` | Log SQL queries (true/false) | `False` |
| `CORS_ALLOWED_ORIGINS` | Comma-separated list of allowed origins | (defaults included) |

### Frontend (.env in `frontend/`)

| Variable | Description | Default |
|----------|-------------|---------|
| `VITE_API_TARGET` | Backend API URL | `http://localhost:8000` |
| `VITE_WS_TARGET` | WebSocket URL | (derived from API target) |
| `VITE_DEV_HOST` | Dev server host | `0.0.0.0` |
| `VITE_DEV_PORT` | Dev server port | `3000` |
| `HOST` | Prod server host | `0.0.0.0` |
| `PORT` | Prod server port | `3000` |

## Development

### Backend Development

- The backend uses hot-reload with `--reload` flag
- Logs are written to `backend/logs/app.log` and `backend/logs/error.log`
- API documentation is auto-generated at `/docs`

### Frontend Development

- Hot module replacement is enabled
- TypeScript type checking: `npm run build`
- Linting: `npm run lint`

## Testing

### Backend Tests
```bash
cd backend
pytest
```

## Troubleshooting

### Database Connection Issues
- Verify MySQL is running: `sudo systemctl status mysql` (Linux) or `brew services list` (macOS)
- Check database credentials in `.env`
- Ensure database exists: `mysql -u root -p -e "SHOW DATABASES;"`

### Port Already in Use
- Backend: Change port with `--port 8001` or update `.env`
- Frontend: Change `VITE_DEV_PORT` in `.env` or use `npm run dev -- --port 3001`

### CORS Errors
- Add your frontend URL to `CORS_ALLOWED_ORIGINS` in backend `.env`
- Ensure backend and frontend URLs match your configuration

### WebSocket Connection Issues
- Verify WebSocket proxy is configured in `vite.config.ts`
- Check that `VITE_WS_TARGET` matches your backend WebSocket endpoint
- Ensure backend WebSocket route is accessible

## Docker Deployment

### Quick Start with Docker Compose

The easiest way to run the entire application is using Docker Compose:

1. **Create `.env` files** for backend and frontend with same variables as described above:


2. **Edit the `.env` files** with your configuration:

   **`backend/.env`**:
   ```env
   # Additional variable
   # MySQL Root Password (for MySQL container)
   MYSQL_ROOT_PASSWORD=your_root_password
   
   ```

2. **Build and start all services**:
   ```bash
   docker-compose up -d
   ```

3. **View logs**:
   ```bash
   docker-compose logs -f
   ```

4. **Stop all services**:
   ```bash
   docker-compose down
   ```

5. **Stop and remove volumes** (clears database):
   ```bash
   docker-compose down -v
   ```

### Individual Docker Builds

#### Backend Only
```bash
cd backend
# Edit .env with your configuration
docker build -t fsdha-backend .
docker run -p 8000:8000 --env-file .env fsdha-backend
```

#### Frontend Only
```bash
cd frontend

# Edit .env with your configuration
docker build -t fsdha-frontend .
docker run -p 3000:3000 --env-file .env fsdha-frontend
```

### Docker Compose Services

- **mysql**: MySQL 8.0 database (port 3306)
- **backend**: FastAPI application (port 8000)
- **frontend**: React application with Vite dev server (port 3000)

All services are connected via a Docker network. Each service reads environment variables from its own `.env` file:
- `backend/.env` - Backend and MySQL configuration
- `frontend/.env` - Frontend configuration

The frontend Vite dev server automatically proxies `/api` and `/ws` requests to the backend.

## Production Deployment

### Backend
1. Set `LOG_LEVEL=INFO` or `WARNING` in production
2. Use a production ASGI server like Gunicorn with Uvicorn workers
3. Configure proper CORS origins for your domain
4. Use environment-specific database credentials
5. Set up proper logging and monitoring

### Frontend
1. Build for production: `npm run build`
2. Serve the `dist/` directory with a web server (nginx, Apache, etc.)
3. Configure API proxy or set `VITE_API_TARGET` to production backend URL

### Docker Production
1. Use Docker Compose with production environment variables
2. Set up reverse proxy (nginx/traefik) in front of containers
3. Use Docker secrets for sensitive data
4. Configure volume mounts for persistent data
5. Set up health checks and restart policies
