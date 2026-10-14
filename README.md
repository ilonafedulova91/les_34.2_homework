## Running the Project with Docker Compose

This project is a Django REST Framework Learning Management System (LMS).

Docker Compose runs five services:

- **web** — Django REST API
- **db** — PostgreSQL database
- **redis** — Redis message broker
- **celery_worker** — Celery background task worker
- **celery_beat** — Celery periodic task scheduler

### Prerequisites

Install Docker Desktop with Docker Compose support.

### Environment Configuration

Create a `.env` file using the provided template.

On Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

Edit `.env` and configure `SECRET_KEY`, `POSTGRES_PASSWORD`, and `STRIPE_API_KEY`.

Do not commit `.env` to Git.

### Start the Application

Build and start all services:

```powershell
docker compose up -d --build
```

Docker Compose starts PostgreSQL and Redis, runs Django database migrations, and launches Django, Celery Worker, and Celery Beat.

### Access the Application

- Django API: http://localhost:8000/
- Django Admin: http://localhost:8000/admin/

Create a superuser if needed:

```powershell
docker compose exec web python manage.py createsuperuser
```

### Useful Commands

Check running containers:

```powershell
docker compose ps
```

View logs:

```powershell
docker compose logs -f
```

View Celery Worker logs:

```powershell
docker compose logs -f celery_worker
```

View Celery Beat logs:

```powershell
docker compose logs -f celery_beat
```

Run migrations manually:

```powershell
docker compose exec web python manage.py migrate
```

Run Django tests:

```powershell
docker compose exec web python manage.py test
```

Stop the application:

```powershell
docker compose down
```

### Data Persistence

PostgreSQL and Redis use Docker named volumes to preserve data between container restarts.

Running `docker compose down` does not delete these volumes.

**Warning:** Running `docker compose down -v` removes the volumes and deletes the stored database and Redis data.

### Notes

The Docker configuration is intended for local development. Django uses its development server and should not be deployed to production without additional configuration.