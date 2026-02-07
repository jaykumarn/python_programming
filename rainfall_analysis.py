import numpy as np
from PIL import Image
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

def analyze_satellite_image(image_path):
    """Analyze satellite image to identify potential rainfall regions."""
    
    img = Image.open(image_path)
    img_array = np.array(img)
    
    # Convert to grayscale if needed
    if len(img_array.shape) == 3:
        gray = np.mean(img_array, axis=2)
    else:
        gray = img_array
    
    # Image bounds (from the image metadata)
    # Approximate geographic bounds based on grid lines visible
    lat_min, lat_max = -5, 45  # Equator to ~45N
    lon_min, lon_max = 50, 105  # ~50E to ~105E
    
    header_height = 80
    data_region = gray[header_height:, :]
    
    height, width = data_region.shape
    
    # Cloud classification thresholds (IR imagery: brighter = colder = higher clouds)
    DENSE_CLOUD = 200  # Very bright - deep convective clouds, high rain probability
    MEDIUM_CLOUD = 160  # Medium brightness - moderate clouds
    LIGHT_CLOUD = 120  # Light clouds - low probability
    
    # Create classification map
    cloud_class = np.zeros_like(data_region)
    cloud_class[data_region >= DENSE_CLOUD] = 3  # High rain probability
    cloud_class[(data_region >= MEDIUM_CLOUD) & (data_region < DENSE_CLOUD)] = 2  # Medium
    cloud_class[(data_region >= LIGHT_CLOUD) & (data_region < MEDIUM_CLOUD)] = 1  # Low
    
    # Define regions of interest
    regions = {
        'North India (J&K, HP, Uttarakhand)': {'lat': (30, 40), 'lon': (70, 82)},
        'Northwest India (Punjab, Haryana, Rajasthan)': {'lat': (25, 32), 'lon': (70, 78)},
        'Northeast India': {'lat': (22, 30), 'lon': (88, 98)},
        'Central India (MP, Chhattisgarh)': {'lat': (18, 26), 'lon': (76, 85)},
        'Western India (Gujarat, Maharashtra)': {'lat': (15, 25), 'lon': (68, 76)},
        'South India (Karnataka, TN, Kerala)': {'lat': (8, 18), 'lon': (74, 82)},
        'Eastern India (Odisha, WB)': {'lat': (18, 25), 'lon': (82, 90)},
        'Arabian Sea': {'lat': (5, 20), 'lon': (55, 72)},
        'Bay of Bengal': {'lat': (5, 20), 'lon': (80, 95)},
        'Pakistan/Afghanistan': {'lat': (25, 38), 'lon': (60, 72)},
    }
    
    def latlon_to_pixel(lat, lon):
        """Convert lat/lon to pixel coordinates."""
        x = int((lon - lon_min) / (lon_max - lon_min) * width)
        y = int((lat_max - lat) / (lat_max - lat_min) * height)
        return max(0, min(x, width-1)), max(0, min(y, height-1))
    
    def analyze_region(lat_range, lon_range):
        """Analyze cloud cover in a specific region."""
        x1, y1 = latlon_to_pixel(lat_range[1], lon_range[0])
        x2, y2 = latlon_to_pixel(lat_range[0], lon_range[1])
        
        region_data = data_region[y1:y2, x1:x2]
        if region_data.size == 0:
            return 0, 0, 0
        
        total = region_data.size
        high_prob = np.sum(region_data >= DENSE_CLOUD) / total * 100
        medium_prob = np.sum((region_data >= MEDIUM_CLOUD) & (region_data < DENSE_CLOUD)) / total * 100
        low_prob = np.sum((region_data >= LIGHT_CLOUD) & (region_data < MEDIUM_CLOUD)) / total * 100
        
        return high_prob, medium_prob, low_prob
    
    # Analyze each region
    print("=" * 70)
    print("RAINFALL PROBABILITY ANALYSIS - INSAT-3DS Thermal IR Image")
    print("Date: 07-02-2026, Time: 19:30-19:57 IST")
    print("=" * 70)
    print()
    
    results = []
    for region_name, bounds in regions.items():
        high, medium, low = analyze_region(bounds['lat'], bounds['lon'])
        total_cloud = high + medium + low
        
        # Determine rainfall likelihood
        if high > 30:
            likelihood = "HIGH"
        elif high > 15 or (high + medium) > 40:
            likelihood = "MODERATE"
        elif total_cloud > 30:
            likelihood = "LOW"
        else:
            likelihood = "UNLIKELY"
        
        results.append({
            'region': region_name,
            'high': high,
            'medium': medium,
            'low': low,
            'likelihood': likelihood
        })
    
    # Sort by rainfall likelihood
    likelihood_order = {'HIGH': 0, 'MODERATE': 1, 'LOW': 2, 'UNLIKELY': 3}
    results.sort(key=lambda x: (likelihood_order[x['likelihood']], -x['high']))
    
    print(f"{'Region':<45} {'Dense%':>8} {'Medium%':>8} {'Likelihood':>12}")
    print("-" * 70)
    
    for r in results:
        print(f"{r['region']:<45} {r['high']:>7.1f}% {r['medium']:>7.1f}% {r['likelihood']:>12}")
    
    print()
    print("=" * 70)
    print("SUMMARY - Areas with Rainfall Potential:")
    print("=" * 70)
    
    high_rain = [r for r in results if r['likelihood'] == 'HIGH']
    moderate_rain = [r for r in results if r['likelihood'] == 'MODERATE']
    
    if high_rain:
        print("\nHIGH PROBABILITY:")
        for r in high_rain:
            print(f"  - {r['region']}")
    
    if moderate_rain:
        print("\nMODERATE PROBABILITY:")
        for r in moderate_rain:
            print(f"  - {r['region']}")
    
    # Create visualization
    fig, axes = plt.subplots(1, 2, figsize=(14, 8))
    
    # Original image
    axes[0].imshow(img_array)
    axes[0].set_title('Original Satellite Image (Thermal IR 10.83 μm)', fontsize=11)
    axes[0].axis('off')
    
    # Cloud classification overlay
    color_map = np.zeros((*data_region.shape, 3), dtype=np.uint8)
    color_map[cloud_class == 3] = [255, 0, 0]    # Red - high rain probability
    color_map[cloud_class == 2] = [255, 165, 0]  # Orange - medium
    color_map[cloud_class == 1] = [255, 255, 0]  # Yellow - low
    color_map[cloud_class == 0] = [0, 100, 0]    # Dark green - clear
    
    axes[1].imshow(color_map)
    axes[1].set_title('Cloud Classification & Rainfall Probability', fontsize=11)
    axes[1].axis('off')
    
    legend_elements = [
        Patch(facecolor='red', label='High Rain Probability (Dense Clouds)'),
        Patch(facecolor='orange', label='Moderate Probability'),
        Patch(facecolor='yellow', label='Low Probability'),
        Patch(facecolor='darkgreen', label='Clear / No Rain')
    ]
    axes[1].legend(handles=legend_elements, loc='lower right', fontsize=9)
    
    plt.tight_layout()
    plt.savefig('rainfall_analysis_output.png', dpi=150, bbox_inches='tight')
    plt.close()
    
    print(f"\nVisualization saved to: rainfall_analysis_output.png")
    
    return results

if __name__ == "__main__":
    results = analyze_satellite_image("3Dasiasec_ir1.jpg")
