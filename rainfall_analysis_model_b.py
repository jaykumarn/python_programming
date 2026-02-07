"""
Satellite Image Rainfall Prediction Analysis
Analyzes INSAT-3DS thermal infrared imagery to identify potential rainfall regions.
"""

import numpy as np
from PIL import Image
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

def load_and_preprocess(image_path):
    """Load satellite image and convert to grayscale."""
    img = Image.open(image_path)
    img_array = np.array(img)
    
    if len(img_array.shape) == 3:
        gray = np.mean(img_array, axis=2)
    else:
        gray = img_array
    
    return img, img_array, gray

def define_geographic_bounds(img_shape):
    """
    Define geographic bounds based on the image.
    Image covers approximately: 50°E to 105°E longitude, -5°S to 45°N latitude
    """
    header_height = 80
    height, width = img_shape[0] - header_height, img_shape[1]
    
    lon_min, lon_max = 50, 105
    lat_min, lat_max = -5, 45
    
    return {
        'header_height': header_height,
        'lon_range': (lon_min, lon_max),
        'lat_range': (lat_min, lat_max),
        'pixels_per_degree_lon': width / (lon_max - lon_min),
        'pixels_per_degree_lat': height / (lat_max - lat_min)
    }

def pixel_to_coords(x, y, bounds):
    """Convert pixel coordinates to geographic coordinates."""
    lon = bounds['lon_range'][0] + x / bounds['pixels_per_degree_lon']
    lat = bounds['lat_range'][1] - (y - bounds['header_height']) / bounds['pixels_per_degree_lat']
    return lat, lon

def coords_to_pixel(lat, lon, bounds):
    """Convert geographic coordinates to pixel coordinates."""
    x = (lon - bounds['lon_range'][0]) * bounds['pixels_per_degree_lon']
    y = bounds['header_height'] + (bounds['lat_range'][1] - lat) * bounds['pixels_per_degree_lat']
    return int(x), int(y)

def analyze_cloud_cover(gray, bounds, threshold_high=180, threshold_medium=140):
    """
    Analyze cloud cover from grayscale image.
    In thermal IR, bright (white) = cold cloud tops = deep convective clouds = rain potential
    """
    data_region = gray[bounds['header_height']:, :]
    
    high_cloud_mask = data_region > threshold_high
    medium_cloud_mask = (data_region > threshold_medium) & (data_region <= threshold_high)
    
    stats = {
        'high_cloud_percent': np.sum(high_cloud_mask) / data_region.size * 100,
        'medium_cloud_percent': np.sum(medium_cloud_mask) / data_region.size * 100,
        'mean_brightness': np.mean(data_region),
        'high_cloud_mask': high_cloud_mask,
        'medium_cloud_mask': medium_cloud_mask
    }
    
    return stats

def identify_rain_regions(gray, bounds):
    """Identify specific geographic regions with potential rainfall."""
    
    regions = {
        'Northern India (Western Disturbance)': {
            'lat_range': (28, 40),
            'lon_range': (70, 95),
            'description': 'J&K, Himachal, Uttarakhand, Punjab'
        },
        'Arabian Sea (Southwest)': {
            'lat_range': (5, 15),
            'lon_range': (55, 72),
            'description': 'Kerala coast, Lakshadweep'
        },
        'Bay of Bengal (East)': {
            'lat_range': (10, 22),
            'lon_range': (85, 100),
            'description': 'Andaman Islands, Coastal Odisha/Andhra'
        },
        'Southern Indian Ocean': {
            'lat_range': (-5, 5),
            'lon_range': (70, 95),
            'description': 'Sri Lanka, Southern Tamil Nadu'
        },
        'Central India': {
            'lat_range': (18, 26),
            'lon_range': (74, 84),
            'description': 'Maharashtra, MP, Chhattisgarh'
        },
        'Western Rajasthan': {
            'lat_range': (24, 30),
            'lon_range': (68, 76),
            'description': 'Rajasthan desert region'
        }
    }
    
    results = []
    
    for region_name, region_data in regions.items():
        lat_min, lat_max = region_data['lat_range']
        lon_min, lon_max = region_data['lon_range']
        
        x1, y1 = coords_to_pixel(lat_max, lon_min, bounds)
        x2, y2 = coords_to_pixel(lat_min, lon_max, bounds)
        
        x1, x2 = max(0, x1), min(gray.shape[1], x2)
        y1, y2 = max(bounds['header_height'], y1), min(gray.shape[0], y2)
        
        if x2 > x1 and y2 > y1:
            region_pixels = gray[y1:y2, x1:x2]
            
            high_cloud_pct = np.sum(region_pixels > 180) / region_pixels.size * 100
            medium_cloud_pct = np.sum((region_pixels > 140) & (region_pixels <= 180)) / region_pixels.size * 100
            mean_brightness = np.mean(region_pixels)
            
            if high_cloud_pct > 30:
                rain_likelihood = 'HIGH'
            elif high_cloud_pct > 15 or (high_cloud_pct + medium_cloud_pct) > 40:
                rain_likelihood = 'MODERATE'
            elif high_cloud_pct > 5 or medium_cloud_pct > 20:
                rain_likelihood = 'LOW'
            else:
                rain_likelihood = 'UNLIKELY'
            
            results.append({
                'region': region_name,
                'description': region_data['description'],
                'high_cloud_pct': high_cloud_pct,
                'medium_cloud_pct': medium_cloud_pct,
                'mean_brightness': mean_brightness,
                'rain_likelihood': rain_likelihood,
                'bounds': (x1, y1, x2, y2)
            })
    
    return results

def create_visualization(img_array, gray, bounds, region_results, output_path):
    """Create visualization with rainfall regions marked."""
    
    fig, axes = plt.subplots(1, 2, figsize=(16, 10))
    
    # Original image
    axes[0].imshow(img_array)
    axes[0].set_title('Original Satellite Image\nINSAT-3DS Thermal IR @ 10.83 μm', fontsize=12)
    axes[0].axis('off')
    
    # Analyzed image with regions
    axes[1].imshow(img_array)
    
    colors = {
        'HIGH': 'red',
        'MODERATE': 'orange', 
        'LOW': 'yellow',
        'UNLIKELY': 'green'
    }
    
    for result in region_results:
        x1, y1, x2, y2 = result['bounds']
        color = colors[result['rain_likelihood']]
        
        rect = mpatches.Rectangle(
            (x1, y1), x2-x1, y2-y1,
            linewidth=2, edgecolor=color, facecolor='none',
            linestyle='--'
        )
        axes[1].add_patch(rect)
        
        label = f"{result['region'].split('(')[0].strip()}\n{result['rain_likelihood']}"
        axes[1].text(
            x1 + 5, y1 + 30, label,
            color='white', fontsize=7, fontweight='bold',
            bbox=dict(boxstyle='round', facecolor=color, alpha=0.7)
        )
    
    legend_patches = [
        mpatches.Patch(color='red', label='HIGH rainfall probability'),
        mpatches.Patch(color='orange', label='MODERATE rainfall probability'),
        mpatches.Patch(color='yellow', label='LOW rainfall probability'),
        mpatches.Patch(color='green', label='UNLIKELY to rain')
    ]
    axes[1].legend(handles=legend_patches, loc='lower right', fontsize=9)
    axes[1].set_title('Rainfall Probability Analysis', fontsize=12)
    axes[1].axis('off')
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()
    
    print(f"Visualization saved to: {output_path}")

def print_report(region_results, cloud_stats):
    """Print analysis report."""
    
    print("=" * 70)
    print("SATELLITE IMAGE RAINFALL ANALYSIS REPORT")
    print("INSAT-3DS Thermal Infrared @ 10.83 μm")
    print("=" * 70)
    
    print(f"\nOVERALL CLOUD STATISTICS:")
    print(f"  Dense cloud cover (>180 brightness): {cloud_stats['high_cloud_percent']:.1f}%")
    print(f"  Medium cloud cover (140-180):        {cloud_stats['medium_cloud_percent']:.1f}%")
    print(f"  Mean brightness:                     {cloud_stats['mean_brightness']:.1f}")
    
    print("\n" + "-" * 70)
    print("REGIONAL RAINFALL ANALYSIS:")
    print("-" * 70)
    
    sorted_results = sorted(region_results, 
                           key=lambda x: {'HIGH': 0, 'MODERATE': 1, 'LOW': 2, 'UNLIKELY': 3}[x['rain_likelihood']])
    
    for result in sorted_results:
        print(f"\n{result['region']}")
        print(f"  Areas: {result['description']}")
        print(f"  Dense clouds: {result['high_cloud_pct']:.1f}% | Medium clouds: {result['medium_cloud_pct']:.1f}%")
        print(f"  >>> RAINFALL LIKELIHOOD: {result['rain_likelihood']}")
    
    print("\n" + "=" * 70)
    print("SUMMARY:")
    print("=" * 70)
    
    high_rain = [r['region'] for r in sorted_results if r['rain_likelihood'] == 'HIGH']
    moderate_rain = [r['region'] for r in sorted_results if r['rain_likelihood'] == 'MODERATE']
    
    if high_rain:
        print(f"\nHIGH probability of rain in:")
        for r in high_rain:
            print(f"  - {r}")
    
    if moderate_rain:
        print(f"\nMODERATE probability of rain in:")
        for r in moderate_rain:
            print(f"  - {r}")
    
    dry_regions = [r['region'] for r in sorted_results if r['rain_likelihood'] == 'UNLIKELY']
    if dry_regions:
        print(f"\nLikely to remain DRY:")
        for r in dry_regions:
            print(f"  - {r}")

def main(image_path, output_path='rainfall_analysis_output.png'):
    """Main analysis function."""
    
    print(f"Loading image: {image_path}")
    img, img_array, gray = load_and_preprocess(image_path)
    
    bounds = define_geographic_bounds(gray.shape)
    
    cloud_stats = analyze_cloud_cover(gray, bounds)
    
    region_results = identify_rain_regions(gray, bounds)
    
    print_report(region_results, cloud_stats)
    
    create_visualization(img_array, gray, bounds, region_results, output_path)
    
    return region_results, cloud_stats

if __name__ == "__main__":
    results, stats = main(
        image_path="3Dasiasec_ir1.jpg",
        output_path="rainfall_analysis_output.png"
    )
