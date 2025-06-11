#!/usr/bin/env python3
"""
MorphoSource CSV Processor
Processes CSV files to match specimens with MorphoSource data and verify voxel spacing.
"""

import pandas as pd
import requests
import json
import time
import os
import sys
from pathlib import Path


class MorphoSourceCSVProcessor:
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = "https://www.morphosource.org/catalog/media"
        self.headers = {
            'Accept': 'application/json',
            'Authorization': f'Bearer {api_key}'
        }
        self.debug_count = 0
        
    def construct_specimen_id(self, row):
        """Construct specimen ID from CSV columns D, E, F (institution:collection:catalog)"""
        try:
            institution = str(row.get('institution_code', '')).strip()
            collection = str(row.get('collection_code', '')).strip()
            catalog = str(row.get('catalog_number', '')).strip()
            
            if not all([institution, collection, catalog]) or any(x in ['nan', 'None'] for x in [institution, collection, catalog]):
                return None
                
            specimen_id = f"{institution}:{collection}:{catalog}"
            return specimen_id
            
        except Exception as e:
            print(f"Error constructing specimen ID: {e}")
            return None
    
    def search_morphosource(self, specimen_id, debug=False):
        """Search MorphoSource for a specimen ID"""
        params = {
            'locale': 'en',
            'per_page': 100,
            'q': specimen_id,
            'search_field': 'all_fields'
        }
        
        try:
            response = requests.get(self.base_url, params=params, headers=self.headers, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                
                # Debug: Save first few responses
                if debug and hasattr(self, 'debug_count') and self.debug_count < 3:
                    with open(f"debug_response_{specimen_id.replace(':', '_')}.json", "w") as f:
                        json.dump(data, f, indent=2)
                    print(f"  DEBUG: Saved response structure to debug_response_{specimen_id.replace(':', '_')}.json")
                    self.debug_count += 1
                
                # Extract media items
                media_items = []
                
                if 'response' in data and 'media' in data['response']:
                    media_items = data['response']['media']
                    if debug:
                        print(f"  DEBUG: Found {len(media_items)} media items in response.media")
                elif 'response' in data and isinstance(data['response'], list):
                    media_items = data['response']
                    if debug:
                        print(f"  DEBUG: Found {len(media_items)} media items in response list")
                else:
                    if debug:
                        print(f"  DEBUG: No media items found in expected locations")
                        print(f"  DEBUG: Available keys: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")
                    return []
                
                if media_items:
                    # Filter for exact matches
                    exact_matches = []
                    for item in media_items:
                        object_title = item.get('physical_object_title', '')
                        if isinstance(object_title, list):
                            object_title = object_title[0] if object_title else ''
                        
                        if object_title.strip().upper() == specimen_id.upper():
                            exact_matches.append(item)
                    
                    if debug and exact_matches:
                        print(f"  DEBUG: Found {len(exact_matches)} exact matches out of {len(media_items)} total items")
                    
                    return exact_matches
                else:
                    return []
                    
            else:
                print(f"Search failed for {specimen_id}: {response.status_code}")
                return []
                
        except Exception as e:
            print(f"Error searching for {specimen_id}: {e}")
            return []
    
    def extract_voxel_spacing(self, media_item):
        """Extract voxel spacing from a media item"""
        def get_first_value(field_data):
            if isinstance(field_data, list):
                return field_data[0] if field_data else None
            return field_data
        
        x_spacing = get_first_value(media_item.get('x_pixel_spacing'))
        y_spacing = get_first_value(media_item.get('y_pixel_spacing'))
        z_spacing = get_first_value(media_item.get('z_pixel_spacing'))
        
        try:
            if x_spacing: x_spacing = float(x_spacing)
            if y_spacing: y_spacing = float(y_spacing)
            if z_spacing: z_spacing = float(z_spacing)
        except:
            pass
            
        return x_spacing, y_spacing, z_spacing
    
    def compare_voxel_spacing(self, csv_x, csv_y, csv_z, api_x, api_y, api_z, tolerance=0.0001):
        """Compare voxel spacing values with tolerance"""
        try:
            csv_x_float = float(csv_x) if csv_x is not None and str(csv_x).strip() != '' else None
            csv_y_float = float(csv_y) if csv_y is not None and str(csv_y).strip() != '' else None
            csv_z_float = float(csv_z) if csv_z is not None and str(csv_z).strip() != '' else None
            
            if None in [csv_x_float, csv_y_float, csv_z_float, api_x, api_y, api_z]:
                return False
            
            x_match = abs(csv_x_float - api_x) <= tolerance
            y_match = abs(csv_y_float - api_y) <= tolerance
            z_match = abs(csv_z_float - api_z) <= tolerance
            
            return x_match and y_match and z_match
            
        except Exception as e:
            print(f"Error comparing voxel spacing: {e}")
            return False
    
    def process_csv(self, csv_filename):
        """Process the entire CSV file"""
        print(f"Processing CSV file: {csv_filename}")
        print("=" * 60)
        
        # Load CSV
        try:
            df = pd.read_csv(csv_filename)
            print(f"Loaded {len(df)} rows from CSV")
        except Exception as e:
            print(f"Error loading CSV: {e}")
            return None
        
        # Check required columns
        required_columns = ['institution_code', 'collection_code', 'catalog_number', 
                           'Voxel_x_spacing', 'Voxel_y_spacing', 'Voxel_z_spacing']
        
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            print(f"Missing required columns: {missing_columns}")
            print(f"Available columns: {list(df.columns)}")
            return None
        
        # Process each row
        results = []
        processed = 0
        matched = 0
        verified = 0
        
        for idx, row in df.iterrows():
            result_row = row.copy()
            debug = (processed < 5)
            
            # Construct specimen ID
            specimen_id = self.construct_specimen_id(row)
            result_row['constructed_specimen_id'] = specimen_id
            
            if not specimen_id:
                result_row['morphosource_status'] = 'No Specimen ID'
                result_row['matched_media_id'] = ''
                result_row['match_status'] = 'No'
                result_row['api_x_spacing'] = ''
                result_row['api_y_spacing'] = ''
                result_row['api_z_spacing'] = ''
                results.append(result_row)
                continue
            
            # Search MorphoSource
            print(f"Processing row {idx+1}: {specimen_id}")
            media_items = self.search_morphosource(specimen_id, debug=debug)
            processed += 1
            
            if not media_items:
                result_row['morphosource_status'] = 'Not Found'
                result_row['matched_media_id'] = ''
                result_row['match_status'] = 'No'
                result_row['api_x_spacing'] = ''
                result_row['api_y_spacing'] = ''
                result_row['api_z_spacing'] = ''
                print(f"  ❌ Not found in MorphoSource")
                results.append(result_row)
                continue
            
            # Found in MorphoSource
            matched += 1
            
            # Get CSV voxel spacing
            csv_x = row.get('Voxel_x_spacing')
            csv_y = row.get('Voxel_y_spacing')
            csv_z = row.get('Voxel_z_spacing')
            
            if debug:
                print(f"  CSV spacing for this row: ({csv_x}, {csv_y}, {csv_z})")
                print(f"  Found {len(media_items)} media items in MorphoSource")
            
            # Find best matching media item
            best_match = None
            best_match_info = None
            
            for media_item in media_items:
                media_id = media_item.get('id')
                if isinstance(media_id, list):
                    media_id = media_id[0] if media_id else None
                
                api_x, api_y, api_z = self.extract_voxel_spacing(media_item)
                
                if debug:
                    print(f"    Media {media_id}: API spacing ({api_x}, {api_y}, {api_z})")
                
                if all(val is not None for val in [api_x, api_y, api_z, csv_x, csv_y, csv_z]):
                    if self.compare_voxel_spacing(csv_x, csv_y, csv_z, api_x, api_y, api_z):
                        best_match = media_item
                        best_match_info = {
                            'media_id': str(media_id) if media_id else '',
                            'api_x': api_x,
                            'api_y': api_y,
                            'api_z': api_z,
                            'match_status': 'Verified'
                        }
                        print(f"  ✅ Found matching scan: Media {media_id}")
                        print(f"    CSV: ({csv_x}, {csv_y}, {csv_z})")
                        print(f"    API: ({api_x}, {api_y}, {api_z})")
                        break
            
            # If no exact match, find closest or available
            if not best_match:
                available_scans = []
                for media_item in media_items:
                    media_id = media_item.get('id')
                    if isinstance(media_id, list):
                        media_id = media_id[0] if media_id else None
                    
                    api_x, api_y, api_z = self.extract_voxel_spacing(media_item)
                    
                    if all(val is not None for val in [api_x, api_y, api_z]):
                        available_scans.append({
                            'media_id': str(media_id) if media_id else '',
                            'api_x': api_x,
                            'api_y': api_y,
                            'api_z': api_z
                        })
                    elif media_id:
                        available_scans.append({
                            'media_id': str(media_id),
                            'api_x': None,
                            'api_y': None,
                            'api_z': None
                        })
                
                if available_scans:
                    first_scan = available_scans[0]
                    best_match_info = {
                        'media_id': first_scan['media_id'],
                        'api_x': first_scan['api_x'],
                        'api_y': first_scan['api_y'],
                        'api_z': first_scan['api_z'],
                        'match_status': 'Available but no spacing match'
                    }
                    print(f"  ⚠️ No exact voxel spacing match found")
                    print(f"    CSV: ({csv_x}, {csv_y}, {csv_z})")
                    print(f"    Available scans: {len(available_scans)}")
                    for i, scan in enumerate(available_scans[:3]):
                        print(f"      {i+1}. Media {scan['media_id']}: ({scan['api_x']}, {scan['api_y']}, {scan['api_z']})")
                else:
                    best_match_info = {
                        'media_id': str(media_items[0].get('id', [''])[0]) if media_items else '',
                        'api_x': None,
                        'api_y': None,
                        'api_z': None,
                        'match_status': 'Found but no voxel data'
                    }
                    print(f"  ⚠️ Found {len(media_items)} media items but none have voxel spacing data")
            
            # Set result fields
            if best_match_info:
                result_row['morphosource_status'] = 'Found'
                result_row['matched_media_id'] = best_match_info['media_id']
                
                if best_match_info['match_status'] == 'Verified':
                    result_row['match_status'] = 'Yes'
                elif best_match_info['api_x'] is not None:
                    result_row['match_status'] = 'Mismatch'
                else:
                    result_row['match_status'] = 'Missing Data'
                
                result_row['api_x_spacing'] = str(best_match_info['api_x']) if best_match_info['api_x'] is not None else ''
                result_row['api_y_spacing'] = str(best_match_info['api_y']) if best_match_info['api_y'] is not None else ''
                result_row['api_z_spacing'] = str(best_match_info['api_z']) if best_match_info['api_z'] is not None else ''
                
                if best_match_info['match_status'] == 'Verified':
                    verified += 1
            else:
                result_row['morphosource_status'] = 'Found'
                result_row['matched_media_id'] = ''
                result_row['match_status'] = 'Missing Data'
                result_row['api_x_spacing'] = ''
                result_row['api_y_spacing'] = ''
                result_row['api_z_spacing'] = ''
            
            results.append(result_row)
            
            # Rate limiting
            time.sleep(0.5)
            
            # Progress update
            if processed % 10 == 0:
                print(f"Progress: {processed} searches completed...")
        
        # Create results DataFrame
        results_df = pd.DataFrame(results)
        
        # Generate output filename and ensure output directory exists
        input_name = Path(csv_filename).stem
        output_dir = Path("data/output")
        output_dir.mkdir(parents=True, exist_ok=True)
        output_filename = output_dir / f"matched-{input_name}.csv"
        
        # Save results
        results_df.to_csv(output_filename, index=False)
        
        # Print summary
        print(f"\n{'='*60}")
        print(f"PROCESSING COMPLETE")
        print(f"{'='*60}")
        print(f"Input file: {csv_filename}")
        print(f"Output file: {output_filename}")
        print(f"Total rows processed: {len(df)}")
        print(f"Specimens searched: {processed}")
        print(f"Found in MorphoSource: {matched}")
        print(f"Exact voxel spacing matches: {verified}")
        
        if processed > 0:
            print(f"Search success rate: {matched/processed*100:.1f}%")
        if matched > 0:
            print(f"Verification success rate: {verified/matched*100:.1f}%")
        
        # Show match status breakdown
        if 'match_status' in results_df.columns:
            match_status_counts = results_df['match_status'].value_counts()
            print(f"\nMatch Status Breakdown:")
            for status, count in match_status_counts.items():
                print(f"  {status}: {count}")
        
        return results_df


def main():
    """Main entry point for the script"""
    if len(sys.argv) != 2:
        print("Usage: python morphosource_processor.py <csv_filename>")
        sys.exit(1)
    
    csv_filename = sys.argv[1]
    
    # Check if file exists
    if not os.path.exists(csv_filename):
        print(f"Error: File '{csv_filename}' not found")
        sys.exit(1)
    
    # Get API key from environment
    api_key = os.environ.get('MORPHOSOURCE_API_KEY')
    if not api_key:
        print("Error: MORPHOSOURCE_API_KEY environment variable not set")
        print("Please set it in GitHub Secrets or as an environment variable")
        sys.exit(1)
    
    # Run the processor
    processor = MorphoSourceCSVProcessor(api_key)
    results = processor.process_csv(csv_filename)
    
    if results is not None:
        print(f"\n🎉 Processing complete! Check the 'matched-' CSV file for results.")
        sys.exit(0)
    else:
        print(f"\n❌ Processing failed. Please check the error messages above.")
        sys.exit(1)


if __name__ == "__main__":
    main()
