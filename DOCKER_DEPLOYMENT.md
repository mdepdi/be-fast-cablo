# Fast LastMile API - Docker Deployment Guide

## Prerequisites

1. Docker and Docker Compose installed
2. External PostgreSQL database accessible
3. OpenRouteService (ORS) instance running (optional, can use external)

## Quick Start

### 1. Environment Configuration

Copy the production environment template:
```bash
cp env.production.example .env
```

Edit `.env` file with your configuration:
```env
# Database Configuration - IMPORTANT
DATABASE_URL=postgresql://username:password@host:port/database

# API Security
API_KEY=your-secure-api-key-here

# External Services
ORS_BASE_URL=http://your-ors-host:port
```

### 2. Deploy with Docker Compose

Using the deployment script:
```bash
# Make the script executable
chmod +x deploy.sh

# Start services in detached mode
./deploy.sh up -d

# Check status
./deploy.sh status
```

Or using Docker Compose directly:
```bash
# Build and start services
docker-compose up -d --build

# Check logs
docker-compose logs -f
```

## Configuration Details

### Database Configuration

The application expects an external PostgreSQL database. Configure the connection using the `DATABASE_URL` environment variable:

```env
# For external database on host machine (Windows/Mac)
DATABASE_URL=postgresql://user:password@host.docker.internal:5432/dbname

# For external database on Linux host
DATABASE_URL=postgresql://user:password@172.17.0.1:5432/dbname

# For remote database
DATABASE_URL=postgresql://user:password@remote-host.com:5432/dbname
```

### ORS Configuration

Similarly, configure the OpenRouteService connection:

```env
# For ORS on host machine (Windows/Mac)
ORS_BASE_URL=http://host.docker.internal:6080

# For ORS on Linux host
ORS_BASE_URL=http://172.17.0.1:6080

# For remote ORS
ORS_BASE_URL=https://ors.example.com
```

### Volume Mounts

The following directories are mounted as volumes:
- `./uploads`: Upload directory for input files
- `./outputs`: Output directory for processed files
- `./data`: Data directory for default files
- `./logs`: Application logs

## Database Migrations

The application automatically runs Alembic migrations on startup. To run migrations manually:

```bash
# Using deployment script
./deploy.sh migrate

# Using docker-compose
docker-compose exec fast-lastmile-api alembic upgrade head
```

To create a new migration:
```bash
docker-compose exec fast-lastmile-api alembic revision -m "description"
```

## Deployment Commands

### Using deploy.sh Script

```bash
# Start services
./deploy.sh up -d

# Stop services
./deploy.sh down

# Restart services
./deploy.sh restart -d

# View logs
./deploy.sh logs

# Run migrations
./deploy.sh migrate

# Open shell in container
./deploy.sh shell

# Check status
./deploy.sh status
```

### Using Docker Compose

```bash
# Start services
docker-compose up -d

# Stop services
docker-compose down

# Restart services
docker-compose restart

# View logs
docker-compose logs -f fast-lastmile-api

# Run command in container
docker-compose exec fast-lastmile-api <command>
```

## Health Checks

The API includes health check endpoints:
- Main health: `http://localhost:8000/health`
- API docs: `http://localhost:8000/docs`

## Troubleshooting

### Database Connection Issues

1. Check if external database is accessible:
```bash
# Test connection from host
psql -h localhost -p 5433 -U postgres -d db-cablo

# Test from container
docker-compose exec fast-lastmile-api pg_isready -h host.docker.internal -p 5433
```

2. Verify DATABASE_URL format:
```
postgresql://username:password@host:port/database
```

3. For Windows/Mac, ensure `host.docker.internal` is used for host services

### Migration Issues

If migrations fail:
1. Check database connectivity
2. Verify database permissions
3. Check migration history:
```bash
docker-compose exec fast-lastmile-api alembic history
```

### Container Access Issues

For Linux hosts accessing host services:
- Use `172.17.0.1` instead of `host.docker.internal`
- Or use the host's actual IP address

## Production Considerations

1. **Security**:
   - Use strong API_KEY
   - Use secure database credentials
   - Consider using Docker secrets for sensitive data

2. **Performance**:
   - Adjust MAX_FILE_SIZE_MB based on needs
   - Monitor disk space for uploads/outputs
   - Consider using external volume for large datasets

3. **Monitoring**:
   - Set up log aggregation
   - Monitor health endpoints
   - Set up alerts for failures

4. **Backup**:
   - Regular database backups
   - Backup uploaded/processed files if needed

## Environment Variables Reference

| Variable | Description | Default |
|----------|-------------|---------|
| DATABASE_URL | PostgreSQL connection string | Required |
| API_KEY | API authentication key | Required |
| API_PORT | API port mapping | 8000 |
| ORS_BASE_URL | OpenRouteService URL | http://host.docker.internal:6080 |
| MAX_FILE_SIZE_MB | Maximum upload file size | 100 |
| DEFAULT_PULAU | Default island parameter | Sulawesi |
| ALLOWED_ORIGINS | CORS allowed origins | ["http://localhost:3000"] |
| DEBUG | Debug mode | false |

## Support

For issues or questions:
1. Check application logs: `./deploy.sh logs`
2. Verify environment configuration
3. Check database and ORS connectivity
4. Review error messages in health endpoint