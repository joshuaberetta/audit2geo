#!/usr/bin/env python3
"""
Create duplicate audit CSV files with random noise for testing multi-trace overlay
"""

import csv
import random

# Read original file
with open('audit.csv', 'r') as f:
    reader = csv.DictReader(f)
    rows = list(reader)

# Create 8 variations with random noise
for i in range(1, 9):
    output_file = f'audit_{i}.csv'
    
    with open(output_file, 'w', newline='') as f:
        fieldnames = ['event', 'node', 'start', 'end', 'latitude', 'longitude', 'accuracy']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        
        for row in rows:
            new_row = row.copy()
            # Add random noise to latitude and longitude if they exist
            if row['latitude'] and row['latitude'].strip():
                try:
                    lat = float(row['latitude'])
                    # Add noise: ~0.001 to 0.005 degrees (roughly 100-500 meters)
                    noise = random.uniform(-0.005, 0.005)
                    new_row['latitude'] = str(lat + noise)
                except ValueError:
                    pass
            
            if row['longitude'] and row['longitude'].strip():
                try:
                    lon = float(row['longitude'])
                    # Add noise: ~0.001 to 0.005 degrees
                    noise = random.uniform(-0.005, 0.005)
                    new_row['longitude'] = str(lon + noise)
                except ValueError:
                    pass
            
            writer.writerow(new_row)
    
    print(f'Created {output_file}')

print('\nAll files created successfully!')
print('You can now upload these files to test the multi-trace overlay feature.')
