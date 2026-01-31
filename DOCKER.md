# Audit2Geo Docker Deployment

## Quick Start

1. Build and start the containers:
```bash
docker-compose up -d
```

2. Access the application:
- Local: http://localhost:8005
- Production: http://audit2geo.imtools.info

3. View logs:
```bash
docker-compose logs -f
```

4. Stop the containers:
```bash
docker-compose down
```

## Production Deployment

### SSL/HTTPS Setup

1. Install Certbot on your host machine:
```bash
apt-get update
apt-get install certbot python3-certbot-nginx
```

2. Generate SSL certificate:
```bash
certbot certonly --standalone -d audit2geo.imtools.info
```

3. Update nginx.conf:
   - Uncomment the HTTPS server block
   - Uncomment the HTTP to HTTPS redirect
   - Update SSL certificate paths if needed

4. Mount certificates in docker-compose.yml:
```yaml
  nginx:
    volumes:
      - ./nginx.conf:/etc/nginx/conf.d/default.conf:ro
      - /etc/letsencrypt:/etc/letsencrypt:ro
```

5. Restart the containers:
```bash
docker-compose down
docker-compose up -d
```

### Firewall Configuration

```bash
# Allow HTTP and HTTPS
ufw allow 8005/tcp
ufw allow 80/tcp
ufw allow 443/tcp
```

### Reverse Proxy Setup (if using external nginx)

If you have a main nginx on the host, add this to your sites-available:

```nginx
upstream audit2geo_backend {
    server localhost:8005;
}

server {
    listen 80;
    server_name audit2geo.imtools.info;
    
    location / {
        proxy_pass http://audit2geo_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## Maintenance

### Update the application:
```bash
git pull
docker-compose build
docker-compose up -d
```

### View container status:
```bash
docker-compose ps
```

### Access container shell:
```bash
docker-compose exec audit2geo /bin/bash
```

### Clean up old images:
```bash
docker system prune -a
```

## Environment Variables

You can create a `.env` file for custom configuration:

```env
FLASK_ENV=production
WORKERS=4
PORT=5000
```

## Monitoring

Check application health:
```bash
curl http://localhost:8005/
```

Monitor resource usage:
```bash
docker stats audit2geo audit2geo_nginx
```
