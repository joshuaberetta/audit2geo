#!/usr/bin/env python3
"""
Convert audit.csv data to GeoJSON for mapping paths.
Converts epoch timestamps (milliseconds) to human-readable format.
"""

import csv
import json
import math
from datetime import datetime, timezone

try:
    import simplekml
    KML_AVAILABLE = True
except ImportError:
    KML_AVAILABLE = False


def epoch_ms_to_datetime(epoch_ms_str):
    """
    Convert epoch timestamp in milliseconds to ISO 8601 datetime string.
    
    Args:
        epoch_ms_str: String representation of epoch time in milliseconds
                     (may use scientific notation like "1,76978E+12")
    
    Returns:
        ISO 8601 formatted datetime string in UTC, or None if invalid
    """
    if not epoch_ms_str or epoch_ms_str.strip() == "":
        return None
    
    try:
        # Handle European number format (comma as decimal separator, period as thousands)
        # Replace commas with periods and remove periods used as thousands separators
        normalized = epoch_ms_str.replace(".", "").replace(",", ".")
        
        # Convert from scientific notation if needed
        epoch_ms = float(normalized)
        
        # Convert milliseconds to seconds
        epoch_seconds = epoch_ms / 1000
        
        # Create datetime object
        dt = datetime.fromtimestamp(epoch_seconds, tz=timezone.utc)
        
        # Return ISO 8601 format
        return dt.isoformat()
    except (ValueError, OSError) as e:
        print(f"Warning: Could not convert timestamp '{epoch_ms_str}': {e}")
        return None


def parse_coordinate(coord_str):
    """
    Parse coordinate string handling European number format.
    
    Args:
        coord_str: String representation of coordinate (may use European format)
    
    Returns:
        Float value of coordinate, or None if invalid
    """
    if not coord_str or coord_str.strip() == "":
        return None
    
    try:
        # Handle European number format (period as thousands separator, comma as decimal)
        # Remove periods (thousands separator) and replace comma with period (decimal)
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
    
    # Earth's radius in meters
    R = 6371000
    
    # Convert to radians
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    
    # Haversine formula
    a = math.sin(delta_phi/2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    
    return R * c


def detect_outliers(coordinates, threshold_meters=100000):
    """
    Detect coordinate outliers based on distance from the median center.
    
    Args:
        coordinates: List of (lat, lon) tuples
        threshold_meters: Distance threshold in meters (default: 100km)
    
    Returns:
        Tuple of (set of outlier indices, dict of {index: distance})
    """
    if len(coordinates) < 3:
        return set(), {}
    
    # Calculate median center
    lats = [coord[0] for coord in coordinates]
    lons = [coord[1] for coord in coordinates]
    
    lats_sorted = sorted(lats)
    lons_sorted = sorted(lons)
    
    median_lat = lats_sorted[len(lats_sorted) // 2]
    median_lon = lons_sorted[len(lons_sorted) // 2]
    median_center = (median_lat, median_lon)
    
    # Find outliers
    outliers = set()
    distances = {}
    for i, coord in enumerate(coordinates):
        distance = calculate_distance(coord, median_center)
        distances[i] = distance
        if distance > threshold_meters:
            outliers.add(i)
    
    return outliers, distances


def audit_csv_to_geojson(csv_file, output_file=None, remove_outliers=False, outlier_threshold=100000):
    """
    Convert audit.csv to GeoJSON format with timestamp conversion.
    
    Args:
        csv_file: Path to input CSV file
        output_file: Path to output GeoJSON file (optional)
        remove_outliers: Whether to remove outlier coordinates (default: False)
        outlier_threshold: Distance threshold in meters for outlier detection (default: 100km)
    
    Returns:
        Dictionary containing GeoJSON FeatureCollection
    """
    features = []
    path_coordinates = []
    raw_data = []
    
    with open(csv_file, 'r', encoding='utf-8') as f:
        # CSV uses semicolon as delimiter
        reader = csv.DictReader(f, delimiter=';')
        
        for row in reader:
            # Parse coordinates
            lat = parse_coordinate(row.get('latitude', ''))
            lon = parse_coordinate(row.get('longitude', ''))
            
            # Skip rows without valid coordinates
            if lat is None or lon is None:
                continue
            
            # Normalize coordinates (they appear to be in unusual format)
            # Divide by 10,000,000 to get proper lat/lon values
            lat = lat / 10000000
            lon = lon / 10000000
            
            # Convert timestamps
            start_time = epoch_ms_to_datetime(row.get('start', ''))
            end_time = epoch_ms_to_datetime(row.get('end', ''))
            
            # Parse accuracy
            accuracy = parse_coordinate(row.get('accuracy', ''))
            
            # Store raw data for outlier detection
            raw_data.append({
                'lat': lat,
                'lon': lon,
                'event': row.get('event', ''),
                'node': row.get('node', ''),
                'start': start_time,
                'end': end_time,
                'accuracy': accuracy
            })
    
    # Detect outliers if requested
    outlier_indices = set()
    distances = {}
    if remove_outliers and len(raw_data) > 0:
        coordinates = [(item['lat'], item['lon']) for item in raw_data]
        outlier_indices, distances = detect_outliers(coordinates, outlier_threshold)
        
        if outlier_indices:
            print(f"\n⚠️  Found {len(outlier_indices)} outlier(s):")
            for idx in sorted(outlier_indices):
                item = raw_data[idx]
                dist_km = distances[idx] / 1000
                print(f"  - Point {idx+1}: ({item['lat']:.6f}, {item['lon']:.6f}) - {item['event']} [{dist_km:.1f}km from center]")
            print(f"  Removing outliers more than {outlier_threshold/1000:.1f}km from median center\n")
    
    # Create features from filtered data
    for i, item in enumerate(raw_data):
        # Skip outliers if removal is enabled
        if remove_outliers and i in outlier_indices:
            continue
        
        lat = item['lat']
        lon = item['lon']
        
        # Create point feature for each event
        feature = {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [lon, lat]  # GeoJSON uses [lon, lat] order
            },
            "properties": {
                "event": item['event'],
                "node": item['node'],
                "start": item['start'],
                "end": item['end'],
                "accuracy": item['accuracy']
            }
        }
        features.append(feature)
        
        # Add to path coordinates for LineString
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
    
    # Create GeoJSON FeatureCollection
    geojson = {
        "type": "FeatureCollection",
        "features": features
    }
    
    # Write to file if output path specified
    if output_file:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(geojson, f, indent=2, ensure_ascii=False)
        print(f"GeoJSON written to {output_file}")
        print(f"Total features: {len(features)}")
        print(f"Points: {len(features) - 1}")
        print(f"Path segments: {len(path_coordinates) - 1}")
    
    return geojson


def geojson_to_kml(geojson, output_file):
    """
    Convert GeoJSON FeatureCollection to KML format.
    
    Args:
        geojson: Dictionary containing GeoJSON FeatureCollection
        output_file: Path to output KML file
    """
    if not KML_AVAILABLE:
        print("Error: simplekml library is not installed.")
        print("Install it with: pip install simplekml")
        return False
    
    kml = simplekml.Kml()
    
    # Track if we've added the path
    path_added = False
    
    for feature in geojson['features']:
        geometry_type = feature['geometry']['type']
        properties = feature.get('properties', {})
        
        if geometry_type == 'Point':
            coords = feature['geometry']['coordinates']
            # GeoJSON is [lon, lat], KML wants (lon, lat)
            lon, lat = coords[0], coords[1]
            
            # Create point
            pnt = kml.newpoint()
            pnt.coords = [(lon, lat)]
            
            # Set name and description
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
            # Convert to KML format (lon, lat)
            kml_coords = [(lon, lat) for lon, lat in coords]
            
            # Create linestring
            linestring = kml.newlinestring()
            linestring.coords = kml_coords
            linestring.name = properties.get('name', 'Audit Path')
            linestring.description = properties.get('description', '')
            
            # Style the line
            linestring.style.linestyle.color = simplekml.Color.blue
            linestring.style.linestyle.width = 3
            
            path_added = True
    
    # Save KML file
    kml.save(output_file)
    print(f"KML written to {output_file}")
    return True


if __name__ == "__main__":
    import sys
    import argparse
    
    # Set up argument parser
    parser = argparse.ArgumentParser(
        description='Convert audit.csv to GeoJSON with timestamp conversion',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python audit2geojson.py                              # Basic conversion
  python audit2geojson.py --kml                        # Output as KML instead of GeoJSON
  python audit2geojson.py --remove-outliers            # Remove outliers (100km threshold)
  python audit2geojson.py -r -t 200000                 # Remove outliers with 200km threshold
  python audit2geojson.py -r -t 10000                  # Remove outliers with 10km threshold
  python audit2geojson.py input.csv output.geojson     # Specify files
        """
    )
    
    parser.add_argument('input', nargs='?', default='audit.csv',
                        help='Input CSV file (default: audit.csv)')
    parser.add_argument('output', nargs='?', default=None,
                        help='Output file (default: audit.geojson or audit.kml)')
    parser.add_argument('--kml', action='store_true',
                        help='Output as KML format instead of GeoJSON')
    parser.add_argument('--remove-outliers', '-r', action='store_true',
                        help='Remove coordinate outliers from output')
    parser.add_argument('--threshold', '-t', type=float, default=100000,
                        help='Outlier distance threshold in meters (default: 100000 = 100km)')
    parser.add_argument('--check-only', '-c', action='store_true',
                        help='Only check for outliers without creating output file')
    
    args = parser.parse_args()
    
    # Determine output file based on format
    if args.output is None:
        if args.kml:
            args.output = 'audit.kml'
        else:
            args.output = 'audit.geojson'
    
    print(f"Converting {args.input} to {args.output}...")
    if args.remove_outliers:
        print(f"Outlier removal enabled (threshold: {args.threshold/1000:.1f}km)")
    print()
    
    # Check for outliers only if requested
    if args.check_only:
        print("Checking for outliers only (no output file will be created)...")
        geojson = audit_csv_to_geojson(args.input, None, True, args.threshold)
        sys.exit(0)
    
    # First create the GeoJSON data
    if args.kml:
        # Create GeoJSON in memory, then convert to KML
        geojson = audit_csv_to_geojson(args.input, None, args.remove_outliers, args.threshold)
        
        # Print stats
        print(f"Total features: {len(geojson['features'])}")
        points = sum(1 for f in geojson['features'] if f['geometry']['type'] == 'Point')
        print(f"Points: {points}")
        
        # Convert to KML
        if geojson_to_kml(geojson, args.output):
            # Print sample of first feature for verification
            if geojson['features']:
                print("\nSample feature:")
                print(json.dumps(geojson['features'][0], indent=2))
    else:
        # Output as GeoJSON
        geojson = audit_csv_to_geojson(args.input, args.output, args.remove_outliers, args.threshold)
        
        # Print sample of first feature for verification
        if geojson['features']:
            print("\nSample feature:")
            print(json.dumps(geojson['features'][0], indent=2))

