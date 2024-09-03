'''
implementation of class Mapper. This class is used to draw a polygon on a map and then divide it into smaller squares of a given size.
The user can draw a polygon on the map and then the class will divide it into smaller squares of a given size (default 1 km2).
The class uses the folium library to draw the map and the shapely library to process the polygon.

The general use is as follows:
1. Create an instance of the Mapper class.
2. Draw a polygon on the map. This wil block the execution until the user closes the map.
3. Call the get_grid method to get the bounding boxes of the squares that cover the polygon.

Example:
app = QApplication(sys.argv)
okno = Mapper()
app.exec_()
bounding_boxes = okno.get_grid(square_area=1, area_units="km2")

The method will return a list of bounding boxes of the squares that cover the polygon. Each bounding box is a tuple of 
4 values: (minx, miny, maxx, maxy). The idea is to use this with the API helper.
'''

import io
import sys
import json
import os
import json
from shapely.geometry import Polygon, box
import geopandas as gpd
from math import isclose

import folium
from folium.plugins.draw import Draw
from branca.colormap import LinearColormap

from PyQt5.QtWidgets import QApplication, QVBoxLayout, QWidget
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtCore import QUrl, QDir



class Mapper(QWidget):
    def __init__(self, filename="poly_coordinates.geojson", save_polygon=False, parent=None):
        super().__init__(parent)
        self.filename = filename
        self.save_polygon = save_polygon
        self.bounding_boxes = None
        self.square_area = 1
        self.area_units = "km2"
        self.interfejs()

    def interfejs(self):
        vbox = QVBoxLayout(self)
        self.webEngineView = QWebEngineView()
        self.webEngineView.page().profile().downloadRequested.connect(
            self.handle_downloadRequested
        )
        self.loadPage()
        vbox.addWidget(self.webEngineView)
        self.setLayout(vbox)
        self.setGeometry(300, 300, 1050, 2050)
        self.setWindowTitle("Mapper")
        self.show()

    def loadPage(self):
        m = folium.Map(location=[41.3851, 2.1734], zoom_start=10)
        Draw(
            export=True,
            filename=self.filename,
            position="topleft",
            draw_options={
                "polyline": False,
                "rectangle": False,
                "circle": False,
                "circlemarker": False,
            },
            edit_options={"poly": {"allowIntersection": False}},
        ).add_to(m)
        data = io.BytesIO()
        m.save(data, close_file=False)
        self.webEngineView.setHtml(data.getvalue().decode())

    def handle_downloadRequested(self, item):
        path = QDir.currentPath() + "/" + self.filename
        item.setPath(path)
        item.finished.connect(self.process_downloaded_file)
        item.accept()

    def process_downloaded_file(self):
        print(f"Polygon saved as: {QDir.currentPath()}/{self.filename}")

    def get_grid(self, square_area=None, area_units=None, show_result=True, tolerance=0):
        '''
        """
        Generate a grid of squares covering the drawn polygon.

        Args:
            - square_area (float): The area of each square in the grid. Default is None.
            - area_units (str): The units of the square area. Default is None.
            - show_result (bool): Whether to display the result map. Default is True.
            - tolerance (float): The minimum fraction of a square's area that must intersect with the polygon. Default is 0.

        Returns:
            - list: A list of bounding boxes (squares) that cover the polygon.
        '''
        if square_area:
            self.square_area = square_area
            if area_units:
                self.area_units = area_units
        try:
            with open(self.filename, 'r') as f:
                data = json.load(f)
            
            # remove the file after loading it, unless the user wants to save it
            if not self.save_polygon:
                os.remove(self.filename)

            # Extract coordinates from the GeoJSON
            if 'features' in data and len(data['features']) > 0:
                geometry = data['features'][0]['geometry']
                if geometry['type'] == 'Polygon':
                    coordinates = geometry['coordinates'][0]
                    res, map = self.process_polygon(coordinates, show_result, tolerance)
                    return res, map
                else:
                    print("The drawn shape is not a polygon")
            else:
                print("No features found in the GeoJSON file")
        except Exception as e:
            print(f"Error loading GeoJSON file: {e}")

    def process_polygon(self, coordinates, show_result=True, tolerance=0):
        '''
        Process the polygon coordinates and generate a grid of squares.

        Args:
            - coordinates (list): List of coordinate pairs defining the polygon.
            - show_result (bool): Whether to display the result map. Default is True.
            - tolerance (float): The minimum fraction of a square's area that must intersect with the polygon. Default is 0.

        Returns:
            - list: A list of bounding boxes (squares) that cover the polygon.
        
        setting tolerance=0.5 means that a square must have at least 50% of its area inside the polygon to be included in the result.
        A tolerance of 0 (the default) will include any square that intersects the polygon at all, and a tolerance of 1 would only
        includes squares that are completely inside the polygon.
        '''
        polygon = Polygon(coordinates)
        # Divide the polygon into squares of the selected size, but first convert the area to square meters
        conversion_factors = {
            "km2": 1000000,
            "ha": 10000,
            "hm2": 10000,
            "dam2": 100,
            "m2": 1,
            "acres": 4046.86,
            "sqf": 0.092903,
            "sqy": 0.836127,
            "sqm": 2589988,
        }
        try:
            square_area = self.square_area * conversion_factors[self.area_units]
        except KeyError:
            print(f"Unknown area unit: {self.area_units}")
            print(f"Supported units:\n  km2 (default)\n  ha, hm2 (hectares)\n  dam2 (decare)\n  m2 (square meters)\n  acres\n  sqf (square feet)\n  sqy (square yards)\n  sqm (square miles)")
            return
        from math import cos, radians, sqrt
        # Convert square_area to square degrees. We will calculate the length of 1 degree
        # of latitude and longitude at this location. This approximation assumes the polygon
        # is not big enough to span multiple degrees of latitude or longitude.
        # Calculate the center of the polygon
        center_lat = polygon.centroid.y
        center_lon = polygon.centroid.x
        lat_degree_length = 111132.92 - 559.82 * cos(2 * radians(center_lat)) + 1.175 * cos(4 * radians(center_lat))
        lon_degree_length = 111412.84 * cos(radians(center_lat)) - 93.5 * cos(3 * radians(center_lat))

        # Calculate square side lengths in degrees
        lat_square_side = sqrt(square_area) / lat_degree_length
        lon_square_side = sqrt(square_area) / lon_degree_length
        
        # Get the bounds of the polygon
        minx, miny, maxx, maxy = polygon.bounds
        
        # Create a grid of squares that cover the polygon. We will check each square to see if it intersects
        # the polygon. If it does, we will keep it in the list of squares.
        squares = []
        y = miny
        while y < maxy:
            x = minx
            while x < maxx:
                square = box(x, y, x + lon_square_side, y + lat_square_side)
                if polygon.intersects(square):
                    intersection = polygon.intersection(square)
                    # we will add the square if at least `tolerance` of the square is inside the polygon. By default, tolerance is 0
                    # so all the squares that intersect the polygon will be added, even if most of them is outside the polygon.
                    if isclose(intersection.area / square.area, 1, rel_tol=1e-9, abs_tol=1e-9) or intersection.area / square.area > tolerance:
                        squares.append(square)
                x += lon_square_side
            y += lat_square_side

        # Before returning the grid, we will create a map to visualize the polygon and the grid
        # so the user can verify that the grid is correct.
        # Create GeoDataFrames with CRS
        polygon_gdf = gpd.GeoDataFrame(geometry=[polygon], crs="EPSG:4326")
        squares_gdf = gpd.GeoDataFrame(geometry=squares, crs="EPSG:4326")

        # Create a Folium map centered on the polygon
        center_lat = (maxy + miny) / 2
        center_lon = (maxx + minx) / 2
        m = folium.Map(location=[center_lat, center_lon], zoom_start=12)

        # Add the polygon to the map
        folium.GeoJson(
            polygon_gdf,
            style_function=lambda x: {'fillColor': 'none', 'color': 'red', 'weight': 2}
        ).add_to(m)

        # Add the squares to the map
        folium.GeoJson(
            squares_gdf,
            style_function=lambda x: {'fillColor': 'blue', 'color': 'blue', 'weight': 1, 'fillOpacity': 0.1}
        ).add_to(m)

        # Save the map
        m.save("polygon_map.html")

        # Open the map in the default web browser.
        if show_result:
            import webbrowser
            webbrowser.open('file://' + os.path.realpath("polygon_map.html"))

        return [square.bounds for square in squares], m
    

def launch_map(**kwargs) -> Mapper:
    # wrapper function to launch the app
    app = QApplication(sys.argv)
    okno = Mapper(**kwargs)
    app.exec_()  # This will block until the window is closed
    return okno



def density(bounding_boxes, base_parameters, **kwargs):
    '''
    Uses the make_request function from APIParser to perform an API call in squares of certain 
    area of each square in parallel. Given that each element of bounding_boxes is a tuple with 
    the following format: (Southwest longitude, Southwest latitude, Northeast longitude, Northeast latitude),
    which is the format expected by GeoJSON on the server. Each concurrent call to the API just
    need to take a copy of the parameters dict and update the bounding box coordinates. The 
    function returns the result of the API call for each square, joined in the same order. The
    function also accepts additional keyword arguments to handle time periods, so it can also
    incorporate time evolution in the analysis.
    
    Args:
        - bounding_boxes: list of tuples, each tuple is (swlng, swlat, nelng, nelat)
        - base_parameters: SafeDict or dict, the base parameters for the API call
        - **kwargs: Additional keyword arguments, including:
            - time_parameters: list of dicts, each dict contains time-related parameters
            (e.g., 'd1', 'd2', 'created_d1', 'created_d2', etc.)
    
    Returns a nested list of API call results, where the outer list corresponds to time periods
    (if provided) and the inner list to bounding boxes.
    '''
    import concurrent.futures
    from core import APIParser

    time_parameters = kwargs.get('time_parameters', [{}])  # Default to a list with an empty dict

    def process_square_and_time(args):
        bounding_box, time_params = args
        minx, miny, maxx, maxy = bounding_box
        params = base_parameters.copy()
        if time_params:
            params.update(time_params)
        params.update({
            'swlng': minx,  # Southwest longitude
            'swlat': miny,  # Southwest latitude
            'nelng': maxx,  # Northeast longitude
            'nelat': maxy   # Northeast latitude
        })
        
        api_parser = APIParser(verbosity=0)
        return api_parser.make_request(parameters=params)

    # Create a list of all combinations of bounding boxes and time parameters
    tasks = [(box, time_param) for time_param in time_parameters for box in bounding_boxes]

    with concurrent.futures.ThreadPoolExecutor() as executor:
        results = list(executor.map(process_square_and_time, tasks))
    
    # Reshape the results into a nested list: [time_periods][bounding_boxes]
    num_periods = len(time_parameters)
    num_boxes = len(bounding_boxes)
    reshaped_results = [results[i:i+num_boxes] for i in range(0, len(results), num_boxes)]
    
    return reshaped_results



from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

def periodic_report(parameters: dict, no_overlap: bool = False, period: int = None, **time_units) -> list[dict]:
    '''
    This function will make requests to the API based on specified time periods.
    
    Parameters:
    - parameters: dict, the parameters to make the API call.
    - no_overlap: bool, if True, ensures that the time windows do not overlap
    - period: int, if provided, divides the time window into this many equal parts
    - **time_units: Keyword arguments for time units (years, months, weeks, days, hours, minutes, seconds)
                    Can be integers or floats.

    Output:
    - list of dictionaries, each representing an independent API call with the time window set to the corresponding period.

    Usage examples:
    periodic_report(parameters, weeks=1, days=3, hours=2, minutes=30, seconds=15)
    periodic_report(parameters, weeks=1.44347718254)
    periodic_report(parameters, period=10)
    '''
    from core import APIParser

    if not parameters:
        raise ValueError("No parameters provided for the API call.")

    API_call = parameters["API_call"]
    api_parser = APIParser()

    # Get parameter types and descriptions
    param_types = api_parser.get_parameter_types(API_call)
    usecase_table = api_parser.usecase(API_call, return_table=True)
    param_descriptions = {row[0]: row[1] for row in usecase_table}

    # Find date/datetime parameters with 'before' or 'after' in the description
    date_params = [param for param, info in param_types.items() 
                   if info['data_type'] in ['date', 'date-time'] 
                   and ('before' in param_descriptions.get(param, '').lower() 
                        or 'after' in param_descriptions.get(param, '').lower())
                   and parameters.get(param)]

    if not date_params:
        raise ValueError("No suitable date parameters found for splitting the request.")

    # Determine the time range from the parameters
    start_time, end_time = None, None
    for param in date_params:
        param_value = parameters[param]
        parsed_time = datetime.fromisoformat(param_value.replace('Z', '+00:00'))
        
        if 'after' in param_descriptions[param].lower():
            start_time = parsed_time
        elif 'before' in param_descriptions[param].lower():
            end_time = parsed_time

    if start_time is None or end_time is None:
        raise ValueError("Both start and end times must be provided in the parameters.")

    # Calculate the time delta
    if period is not None:
        # Divide the time range into equal parts
        total_duration = end_time - start_time
        time_delta = total_duration / period
    elif time_units:
        # Calculate time delta from provided units
        relativedelta_units = {k: v for k, v in time_units.items() if k in ['years', 'months', 'weeks']}
        timedelta_units = {k: v for k, v in time_units.items() if k in ['days', 'hours', 'minutes', 'seconds']}
        
        time_delta = relativedelta(**relativedelta_units) + timedelta(**timedelta_units)
    else:
        raise ValueError("Either 'period' or time units must be provided.")

    # Create a list of time windows
    time_windows = []
    current_time = start_time
    while current_time < end_time:
        next_time = min(current_time + time_delta, end_time)
        if no_overlap and next_time < end_time:
            next_time -= timedelta(microseconds=1)
        time_windows.append((current_time, next_time))
        
        if no_overlap:
            current_time = next_time + timedelta(microseconds=1)
        else:
            current_time = next_time

    # Make a list of parameters for the API call of each time fraction
    results = []
    for start, end in time_windows:
        window_params = parameters.copy()
        for param in date_params:
            param_type = param_types[param]['data_type']
            if 'after' in param_descriptions[param].lower():
                window_params[param] = start.date().isoformat() if param_type == 'date' else start.isoformat()
            elif 'before' in param_descriptions[param].lower():
                window_params[param] = end.date().isoformat() if param_type == 'date' else end.isoformat()
        
        results.append(window_params)

    return results