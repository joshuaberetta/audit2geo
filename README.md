# Audit CSV to GeoJSON/KML Converter

Converts audit.csv data to GeoJSON or KML format for mapping paths with proper timestamp conversion.

## Features

- **Web Application**: Interactive web interface for easy file processing
- **Multiple File Upload**: Import and overlay multiple audit files simultaneously
- **Color-Coded Traces**: Each file is assigned a unique color for easy identification
- **Interactive Legend**: Show/hide individual traces with checkboxes
- **Trace Filtering**: Search box to quickly find specific traces by filename
- **Optimized for Scale**: Efficiently handles 100+ overlaid traces
- **Drag & Drop Upload**: Easy file upload with drag-and-drop support
- **Live Map Visualization**: See your data on an interactive Leaflet map
- **Outlier Detection**: Configurable threshold for identifying outliers
- **Outlier Removal**: Option to remove outliers from the output
- **Multiple Export Formats**: Download as GeoJSON or KML
- Converts epoch timestamps (milliseconds) to ISO 8601 datetime format
- Handles European number format (comma as decimal separator, period as thousands)
- Creates individual Point features for each audit event
- Generates a LineString feature showing the complete path
- Includes all event metadata (event type, node, timestamps, accuracy)

## Timestamp Conversion

The script converts epoch timestamps from milliseconds to human-readable format:
- Input: `1488761807868` (epoch milliseconds)
- Conversion: Divide by 1000 to get seconds, then convert to datetime
- Output: `2017-03-06T00:56:47.868000+00:00` (ISO 8601 UTC)

## Quick Start - Web Application

1. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Run the Web Application**
   ```bash
   python app.py
   ```

3. **Open in Browser**
   
   Navigate to `http://localhost:5000`

4. **Use the Application**
   - Drag and drop your `audit.csv` file(s) or click to browse
   - **Multiple files**: Select multiple CSV files to overlay them on the map
   - Each trace will be assigned a unique color automatically
   - Use the legend to show/hide individual traces
   - Use the filter box to search for specific traces by filename
   - Choose output format (GeoJSON or KML)
   - Optionally enable outlier detection and set threshold
   - Optionally enable outlier removal
   - Click "Process File" to see results on the map
   - Download the processed file (combines all visible traces)

## Production Deployment

### Docker Deployment with Existing Nginx

This setup works with your existing nginx installation on the host machine:

1. **Build and Start Container**
   ```bash
   docker-compose up -d
   ```
   
   This exposes the Flask app on `127.0.0.1:8005` (localhost only, for security)

2. **Configure Your Host Nginx**
   
   Copy the provided nginx configuration:
   ```bash
   sudo cp nginx.conf /etc/nginx/sites-available/audit2geo
   sudo ln -s /etc/nginx/sites-available/audit2geo /etc/nginx/sites-enabled/
   sudo nginx -t
   sudo systemctl reload nginx
   ```

3. **Set Up SSL with Certbot**
   ```bash
   sudo certbot --nginx -d audit2geo.imtools.info
   ```
   
   Certbot will automatically:
   - Obtain an SSL certificate
   - Configure HTTPS in your nginx config
   - Set up HTTP to HTTPS redirect
   - Configure automatic certificate renewal

4. **Verify Deployment**
   ```bash
   # Check Docker container
   docker-compose ps
   docker-compose logs -f
   
   # Test the endpoint
   curl http://localhost:8005/
   curl http://audit2geo.imtools.info/
   curl https://audit2geo.imtools.info/
   ```

### Application Management

**View Logs:**
```bash
docker-compose logs -f
```

**Restart Application:**
```bash
docker-compose restart
```

**Update Application:**
```bash
git pull
docker-compose build
docker-compose up -d
```

**Stop Application:**
```bash
docker-compose down
```

### Nginx Configuration Details

The application runs on `127.0.0.1:8005` and nginx proxies requests to it:
- **Client Max Body Size:** 16MB for CSV uploads
- **Timeouts:** 120s for processing large files
- **Gzip Compression:** Enabled for better performance
- **Security Headers:** X-Frame-Options, X-Content-Type-Options, X-XSS-Protection
- **Keep-Alive:** Connection pooling for better performance

### SSL Certificate Renewal

Certbot sets up automatic renewal via systemd timer. Check renewal status:
```bash
sudo certbot renew --dry-run
sudo systemctl status certbot.timer
```

Certificates will auto-renew 30 days before expiration.

### Alternative: Full Docker Setup (Not Needed)

If you want nginx in Docker too, see [DOCKER.md](DOCKER.md) for the full containerized setup.

## Command Line Usage

The original command-line tool is still available in `audit2geo.py`:

```bash
# Basic usage (reads audit.csv, outputs audit.geojson)
python audit2geo.py

# Output as KML instead of GeoJSON
python audit2geo.py --kml

# Specify input file
python audit2geo.py input.csv

# Specify input and output files
python audit2geo.py input.csv output.geojson

# Create KML with custom output filename
python audit2geo.py input.csv output.kml --kml

# Remove outliers (points more than 100km from median center)
python audit2geo.py --remove-outliers

# Remove outliers with custom threshold (e.g., 10km)
python audit2geo.py -r -t 10000

# Combine KML output with outlier removal
python audit2geo.py --kml --remove-outliers
```

## Installation

### For Web Application
```bash
pip install -r requirements.txt
```

### For Command Line Tool Only

Install required dependencies:

```bash
# For basic GeoJSON export (no additional dependencies needed)
python audit2geo.py

# For KML export support
pip install simplekml
```

## Output Format

The script generates a GeoJSON FeatureCollection containing:

1. **Point Features**: One for each row with valid coordinates
   - Properties: event, node, start (datetime), end (datetime), accuracy

2. **LineString Feature**: A single path connecting all points in sequence
   - Properties: name, description

## Example

```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "geometry": {
        "type": "Point",
        "coordinates": [33.7492089, -24.8949632]
      },
      "properties": {
        "event": "group questions",
        "node": "/akmg7nPy964nXVvmRPkFvw/details",
        "start": "2026-01-24T10:30:00.000000+00:00",
        "end": "2026-01-24T10:30:00.000000+00:00",
        "accuracy": 5845899963378900
      }
    }
  ]
}
```

## Visualizing the Data

You can visualize the generated output using:

**GeoJSON Format:**
- [geojson.io](https://geojson.io) - Paste the contents
- QGIS - Import as vector layer
- Leaflet/Mapbox - Use in web mapping applications
- Any GIS software that supports GeoJSON

**KML Format:**
- Google Earth - Open directly
- Google Maps - Import the KML file
- ArcGIS Earth
- Any mapping application with KML support
