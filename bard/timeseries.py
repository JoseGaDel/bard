from typing import List, Dict, Any, Callable
import folium
from folium.plugins import HeatMap
from branca.colormap import LinearColormap
import statistics
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from PIL import Image
import time
import os
import concurrent.futures

class BiodiversityConfig:
    """
    Configuration class for biodiversity data processing and visualization.
    
    Attributes:
        filter_field (str): Field used for filtering observations.
        filter_value (Any): Value to match in the filter field.
        heatmap_field (str): Field used for heatmap intensity.
        popup_field (str): Field used for popup information.
        heatmap_label (str): Label for the heatmap legend.
        popup_label (str): Label for the popup information.
    """
    def __init__(self, 
                 filter_field: str,
                 filter_value: Any,
                 heatmap_field: str,
                 popup_field: str,
                 heatmap_label: str,
                 popup_label: str):
        self.filter_field = filter_field
        self.filter_value = filter_value
        self.heatmap_field = heatmap_field
        self.popup_field = popup_field
        self.heatmap_label = heatmap_label
        self.popup_label = popup_label


def process_observations(density_results: List[List[Dict]], 
                         bounding_boxes: List[List[float]], 
                         config: BiodiversityConfig) -> List[List[Dict]]:
    """
    Process observation data for each time period and bounding box.
    
    Args:
        - density_results (List[List[Dict]]): Nested list of observation data for each time period and box.
        - bounding_boxes (List[List[float]]): List of bounding box coordinates.
        - config (BiodiversityConfig): Configuration for data processing.
    
    Returns:
        - List[List[Dict]]: Processed data for each time period.
    """
    processed_data = []

    for time_period, period_boxes in enumerate(density_results):
        period_data = []
        for box_index, box_data in enumerate(period_boxes):
            filtered_data = filter_and_extract(box_data, config)
            if filtered_data['heatmap_value'] > 0:
                period_data.append({
                    'box_index': box_index,
                    'heatmap_value': filtered_data['heatmap_value'],
                    'popup_value': filtered_data['popup_value'],
                    'bounding_box': bounding_boxes[box_index]
                })
        processed_data.append(period_data)

    return processed_data

def filter_and_extract(data: Dict, config: BiodiversityConfig) -> Dict[str, int]:
    """
    Filter and extract relevant data from observations.
    
    Args:
        - data (Dict): Raw observation data.
        - config (BiodiversityConfig): Configuration for filtering and extraction.
    
    Returns:
        - Dict[str, int]: Extracted heatmap and popup values.
    """
    filtered_data = [
        obs for obs in data.get('results', [])
        if get_nested_value(obs, config.filter_field) == config.filter_value
    ]
    
    heatmap_value = sum(get_nested_value(obs, config.heatmap_field, 1) for obs in filtered_data)
    popup_value = len(set(get_nested_value(obs, config.popup_field) for obs in filtered_data if get_nested_value(obs, config.popup_field) is not None))
    
    return {
        'heatmap_value': heatmap_value,
        'popup_value': popup_value
    }

def get_nested_value(obj: Dict, path: str, default: Any = None) -> Any:
    """
    Retrieve a nested value from a dictionary using a dot-separated path.
    
    Args:
        - obj (Dict): The dictionary to search.
        - path (str): Dot-separated path to the desired value.
        - default (Any): Default value if the path is not found.
    
    Returns:
        - Any: The value at the specified path or the default value.
    """
    keys = path.split('.')
    for key in keys:
        if isinstance(obj, dict):
            obj = obj.get(key, {})
        else:
            return default
    return obj if obj != {} else default



def analyze_biodiversity(data: Dict, config: BiodiversityConfig) -> Dict:
    """
    Analyze biodiversity data based on the provided configuration.
    
    Args:
        - data (Dict): Raw biodiversity data.
        - config (BiodiversityConfig): Configuration for analysis.
    
    Returns:
        - Dict: Extracted and analyzed data.
    """
    filtered_data = [obs for obs in data.get('results', []) if config.filter_function(obs)]
    extracted_data = config.extract_function(filtered_data)
    return extracted_data


def create_time_series_maps(processed_data: List[List[Dict]], 
                            bounding_boxes: List[List[float]], 
                            time_periods: List[str], 
                            config: BiodiversityConfig) -> List[folium.Map]:
    """
    Create a series of folium maps for each time period.
    
    Args:
        - processed_data (List[List[Dict]]): Processed biodiversity data for each time period.
        - bounding_boxes (List[List[float]]): List of bounding box coordinates.
        - time_periods (List[str]): List of time period labels.
        - config (BiodiversityConfig): Configuration for map creation.
    
    Returns:
        - List[folium.Map]: List of folium maps for each time period.
    """
    maps = []
    
    # Calculate map boundaries
    all_lats = [coord for box in bounding_boxes for coord in [box[1], box[3]]]
    all_lons = [coord for box in bounding_boxes for coord in [box[0], box[2]]]
    min_lat, max_lat = min(all_lats), max(all_lats)
    min_lon, max_lon = min(all_lons), max(all_lons)
    
    # Determine the maximum heatmap value for the colormap
    max_heatmap_value = max(max(point['heatmap_value'] for point in period) if period else 0 for period in processed_data)

    for time_period, period_data in enumerate(processed_data):
        # base map
        m = folium.Map(location=[(min_lat + max_lat) / 2, (min_lon + max_lon) / 2], 
                       zoom_start=10, zoom_control=False)

        heat_data = []
        # Add heatmap data points
        for box in bounding_boxes:
            point = next((p for p in period_data if p['bounding_box'] == box), None)
            weight = point['heatmap_value'] if point else 0
            heat_data.extend([
                [box[1], box[0], weight], [box[1], box[2], weight],
                [box[3], box[0], weight], [box[3], box[2], weight],
                [(box[1] + box[3]) / 2, (box[0] + box[2]) / 2, weight]
            ])
        # Add heatmap layer
        HeatMap(heat_data, max_val=max_heatmap_value, radius=25, blur=20, min_opacity=0.2).add_to(m)

        # Add bounding boxes with popup information
        for box in bounding_boxes:
            point = next((p for p in period_data if p['bounding_box'] == box), None)
            popup_value = point['popup_value'] if point else 0
            folium.Rectangle(
                bounds=[[box[1], box[0]], [box[3], box[2]]],
                color="black",
                weight=1,
                fill=False,
                opacity=0.3,
                popup=f"{config.popup_label}: {popup_value}"
            ).add_to(m)

        # Add colormap legend
        colormap = LinearColormap(colors=['blue', 'yellow', 'red'], vmin=0, vmax=max_heatmap_value)
        colormap.add_to(m)
        colormap.caption = config.heatmap_label

        # Add time period label
        folium.map.Marker(
            [min_lat, min_lon],
            icon=folium.DivIcon(
                html=f'<div style="font-size: 24pt">{time_periods[time_period]}</div>'
            )
        ).add_to(m)

        # Fit map to bounds
        m.fit_bounds([[min_lat, min_lon], [max_lat, max_lon]])

        maps.append(m)

    return maps


def capture_screenshot(args: tuple) -> int:
    """
    Capture a screenshot of a folium map using Selenium.
    
    Args:
        - args (tuple): Tuple containing the index and HTML content of the map.
    
    Returns:
        - int: Index of the captured screenshot.
    """
    i, map_html = args
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    driver = webdriver.Chrome(options=chrome_options)
    
    # Save the map as an HTML file
    with open(f'temp_map_{i}.html', 'w') as f:
        f.write(map_html)
    
    # Open the HTML file with Selenium
    driver.get(f'file://{os.path.abspath(f"temp_map_{i}.html")}')
    
    # Wait for the map to load
    time.sleep(1.5)
    
    # Take a screenshot
    driver.save_screenshot(f'temp_screenshot_{i}.png')
    
    # Close the WebDriver
    driver.quit()
    
    # Remove temporary HTML file
    os.remove(f'temp_map_{i}.html')
    
    return i

def create_gif_from_maps(maps: List[folium.Map], output_filename: str = 'biodiversity_evolution.gif') -> None:
    """
    Create an animated GIF from a series of folium maps.
    
    Args:
        - maps (List[folium.Map]): List of folium maps to animate.
        - output_filename (str): Name of the output GIF file.
    """
    # Capture screenshots concurrently
    with concurrent.futures.ThreadPoolExecutor(max_workers=os.cpu_count()) as executor:
        futures = [executor.submit(capture_screenshot, (i, m.get_root().render())) for i, m in enumerate(maps)]
        concurrent.futures.wait(futures)
    
    # Create GIF from screenshots
    images = []
    for i in range(len(maps)):
        images.append(Image.open(f'temp_screenshot_{i}.png'))
    
    # Create and save the GIF
    images[0].save(
        output_filename,
        save_all=True,
        append_images=images[1:],
        duration=1000,  # Duration for each frame in milliseconds
        loop=0  # we put 0 here so it loops indefinitely
    )
    
    # Remove temporary screenshot files
    for i in range(len(maps)):
        os.remove(f'temp_screenshot_{i}.png')
    
    print(f"Animation saved as {output_filename}")

