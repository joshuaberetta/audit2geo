#!/usr/bin/env python3
"""
Audit2Geo Web Application
A web interface for converting audit CSV files to GeoJSON/KML with outlier detection and visualization.
"""

from flask import Flask, render_template, request, jsonify, send_file
import io
import csv
import json
import math
from datetime import datetime, timezone

try:
    import simplekml
    KML_AVAILABLE = True
except ImportError:
    KML_AVAILABLE = False

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size


def epoch_ms_to_datetime(epoch_ms_str):
    """
    Convert epoch timestamp in milliseconds to ISO 8601 datetime string.
    
    Args:
        epoch_ms_str: String representation of epoch time in milliseconds
    
    Returns:
        ISO 8601 formatted datetime string in UTC, or None if invalid
    """
    if not epoch_ms_str or epoch_ms_str.strip() == "":
        return None
    
    try:
        # Try standard format first
        try:
            epoch_ms = float(epoch_ms_str)
        except ValueError:
            # Fall back to European format (comma as decimal separator)
            normalized = epoch_ms_str.replace(".", "").replace(",", ".")
            epoch_ms = float(normalized)
        
        epoch_seconds = epoch_ms / 1000
        dt = datetime.fromtimestamp(epoch_seconds, tz=timezone.utc)
        return dt.isoformat()
    except (ValueError, OSError) as e:
        return None


def parse_coordinate(coord_str):
    """
    Parse coordinate string handling both European and standard number formats.
    
    Args:
        coord_str: String representation of coordinate
    
    Returns:
        Float value of coordinate, or None if invalid
    """
    if not coord_str or coord_str.strip() == "":
        return None
    
    try:
        # First try standard format (period as decimal)
        try:
            return float(coord_str)
        except ValueError:
            # Fall back to European format (period as thousands separator, comma as decimal)
            normalized = coord_str.replace(".", "").replace(",", ".")
            return float(normalized)
    except ValueError:
        return None


def calculate_distance(coord1, coord2):
    """
    Calculate distance between two coordinates in meters using Haversine formula.
    
    Args:
        coord1: Tuple of (lat, lon)
        coord2: Tuple of (lat, lon)
    
    Returns:
        Distance in meters
    """
    lat1, lon1 = coord1
    lat2, lon2 = coord2
    
    R = 6371000  # Earth's radius in meters
    
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    
    a = math.sin(delta_phi/2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    
    return R * c


def detect_outliers(coordinates, threshold_meters=100000):
    """
    Detect coordinate outliers based on distance from the median center.
    
    Args:
        coordinates: List of (lat, lon) tuples
        threshold_meters: Distance threshold in meters
    
    Returns:
        Tuple of (set of outlier indices, dict of {index: distance})
    """
    if len(coordinates) < 3:
        return set(), {}
    
    lats = [coord[0] for coord in coordinates]
    lons = [coord[1] for coord in coordinates]
    
    lats_sorted = sorted(lats)
    lons_sorted = sorted(lons)
    
    median_lat = lats_sorted[len(lats_sorted) // 2]
    median_lon = lons_sorted[len(lons_sorted) // 2]
    median_center = (median_lat, median_lon)
    
    outliers = set()
    distances = {}
    for i, coord in enumerate(coordinates):
        distance = calculate_distance(coord, median_center)
        distances[i] = distance
        if distance > threshold_meters:
            outliers.add(i)
    
    return outliers, distances


def process_csv_data(csv_content, remove_outliers=False, outlier_threshold=100000):
    """
    Process CSV content and return GeoJSON with outlier information.
    
    Args:
        csv_content: String content of the CSV file
        remove_outliers: Whether to remove outlier coordinates
        outlier_threshold: Distance threshold in meters for outlier detection
    
    Returns:
        Dictionary with GeoJSON data and outlier information
    """
    features = []
    path_coordinates = []
    raw_data = []
    
    csv_file = io.StringIO(csv_content)
    
    # Auto-detect delimiter (comma or semicolon)
    first_line = csv_content.split('\n')[0]
    delimiter = ',' if ',' in first_line else ';'
    
    reader = csv.DictReader(csv_file, delimiter=delimiter)
    
    for row in reader:
        lat = parse_coordinate(row.get('latitude', ''))
        lon = parse_coordinate(row.get('longitude', ''))
        
        if lat is None or lon is None:
            continue
        
        # Check if coordinates need normalization (values > 180 suggest they're in old format)
        if abs(lat) > 90 or abs(lon) > 180:
            # Normalize coordinates (divide by 10,000,000 for old format)
            lat = lat / 10000000
            lon = lon / 10000000
        
        start_time = epoch_ms_to_datetime(row.get('start', ''))
        end_time = epoch_ms_to_datetime(row.get('end', ''))
        accuracy = parse_coordinate(row.get('accuracy', ''))
        
        raw_data.append({
            'lat': lat,
            'lon': lon,
            'event': row.get('event', ''),
            'node': row.get('node', ''),
            'start': start_time,
            'end': end_time,
            'accuracy': accuracy
        })
    
    # Detect outliers
    outlier_indices = set()
    distances = {}
    outlier_info = []
    
    if len(raw_data) > 0:
        coordinates = [(item['lat'], item['lon']) for item in raw_data]
        outlier_indices, distances = detect_outliers(coordinates, outlier_threshold)
        
        if outlier_indices:
            for idx in sorted(outlier_indices):
                item = raw_data[idx]
                dist_km = distances[idx] / 1000
                outlier_info.append({
                    'index': idx,
                    'lat': item['lat'],
                    'lon': item['lon'],
                    'event': item['event'],
                    'distance_km': round(dist_km, 1)
                })
    
    # Create features from filtered data
    for i, item in enumerate(raw_data):
        if remove_outliers and i in outlier_indices:
            continue
        
        lat = item['lat']
        lon = item['lon']
        
        feature = {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [lon, lat]
            },
            "properties": {
                "event": item['event'],
                "node": item['node'],
                "start": item['start'],
                "end": item['end'],
                "accuracy": item['accuracy'],
                "is_outlier": i in outlier_indices
            }
        }
        features.append(feature)
        path_coordinates.append([lon, lat])
    
    # Create LineString feature for the path
    if len(path_coordinates) > 1:
        path_feature = {
            "type": "Feature",
            "geometry": {
                "type": "LineString",
                "coordinates": path_coordinates
            },
            "properties": {
                "name": "Audit Path",
                "description": f"Path with {len(path_coordinates)} points"
            }
        }
        features.append(path_feature)
    
    geojson = {
        "type": "FeatureCollection",
        "features": features
    }
    
    return {
        'geojson': geojson,
        'outliers': outlier_info,
        'total_points': len(raw_data),
        'processed_points': len(path_coordinates)
    }


def geojson_to_kml_string(geojson):
    """
    Convert GeoJSON FeatureCollection to KML string.
    
    Args:
        geojson: Dictionary containing GeoJSON FeatureCollection
    
    Returns:
        KML content as string
    """
    if not KML_AVAILABLE:
        return None
    
    kml = simplekml.Kml()
    path_added = False
    
    for feature in geojson['features']:
        geometry_type = feature['geometry']['type']
        properties = feature.get('properties', {})
        
        if geometry_type == 'Point':
            coords = feature['geometry']['coordinates']
            lon, lat = coords[0], coords[1]
            
            pnt = kml.newpoint()
            pnt.coords = [(lon, lat)]
            
            event = properties.get('event', 'Unknown')
            pnt.name = event
            
            description_parts = []
            if properties.get('node'):
                description_parts.append(f"Node: {properties['node']}")
            if properties.get('start'):
                description_parts.append(f"Start: {properties['start']}")
            if properties.get('end'):
                description_parts.append(f"End: {properties['end']}")
            if properties.get('accuracy'):
                description_parts.append(f"Accuracy: {properties['accuracy']}m")
            
            if description_parts:
                pnt.description = '\n'.join(description_parts)
        
        elif geometry_type == 'LineString' and not path_added:
            coords = feature['geometry']['coordinates']
            kml_coords = [(lon, lat) for lon, lat in coords]
            
            linestring = kml.newlinestring()
            linestring.coords = kml_coords
            linestring.name = properties.get('name', 'Audit Path')
            linestring.description = properties.get('description', '')
            
            linestring.style.linestyle.color = simplekml.Color.blue
            linestring.style.linestyle.width = 3
            
            path_added = True
    
    return kml.kml()


@app.route('/')
def index():
    """Render the main application page."""
    return render_template('index.html', kml_available=KML_AVAILABLE)


@app.route('/process', methods=['POST'])
def process():
    """Process uploaded CSV file(s) and return GeoJSON with outlier info."""
    # Check if multiple files were uploaded
    files = request.files.getlist('files')
    
    if not files or len(files) == 0:
        # Fallback to single file for backward compatibility
        if 'file' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400
        files = [request.files['file']]
    
    # Validate all files
    for file in files:
        if file.filename == '':
            return jsonify({'error': 'Empty filename detected'}), 400
        if not file.filename.endswith('.csv'):
            return jsonify({'error': f'File {file.filename} must be a CSV'}), 400
    
    try:
        remove_outliers = request.form.get('remove_outliers', 'false').lower() == 'true'
        threshold = float(request.form.get('threshold', 100000))
        
        results = []
        
        # Process each file
        for file in files:
            csv_content = file.read().decode('utf-8')
            result = process_csv_data(csv_content, remove_outliers, threshold)
            result['filename'] = file.filename
            results.append(result)
        
        # Return single result for backward compatibility if only one file
        if len(results) == 1:
            return jsonify(results[0])
        
        # Return multiple results
        return jsonify({
            'multiple': True,
            'traces': results
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/download/<format>', methods=['POST'])
def download(format):
    """Download the processed data in the requested format."""
    # Get data from POST body instead of query string
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    try:
        geojson = data
        
        if format == 'geojson':
            output = io.BytesIO()
            output.write(json.dumps(geojson, indent=2).encode('utf-8'))
            output.seek(0)
            
            return send_file(
                output,
                mimetype='application/geo+json',
                as_attachment=True,
                download_name='audit.geojson'
            )
        
        elif format == 'kml':
            if not KML_AVAILABLE:
                return jsonify({'error': 'KML export not available. Install simplekml.'}), 500
            
            kml_content = geojson_to_kml_string(geojson)
            output = io.BytesIO()
            output.write(kml_content.encode('utf-8'))
            output.seek(0)
            
            return send_file(
                output,
                mimetype='application/vnd.google-earth.kml+xml',
                as_attachment=True,
                download_name='audit.kml'
            )
        
        else:
            return jsonify({'error': 'Invalid format'}), 400
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True, port=5000)
