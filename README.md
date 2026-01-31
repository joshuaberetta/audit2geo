# Audit CSV to GeoJSON/KML Converter

Converts audit.csv data to GeoJSON or KML format for mapping paths with proper timestamp conversion.

## Features

- **Web Application**: Interactive web interface for easy file processing
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
   - Drag and drop your `audit.csv` file or click to browse
   - Choose output format (GeoJSON or KML)
   - Optionally enable outlier detection and set threshold
   - Optionally enable outlier removal
   - Click "Process File" to see results on the map
   - Download the processed file

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
