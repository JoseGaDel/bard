"""
This script demonstrates how to generate a monthly report of observations using the APIParser class.

The script performs the following steps:
1. Launches a map and saves the polygon coordinates.
2. Generates a grid of bounding boxes based on the polygon coordinates.
3. Retrieves the parameters for the 'observations' API call using the APIParser class.
4. Updates the parameters to include additional filters for the observations.
5. Sets the date range for the monthly report to be from January 1, 2023, to December 31, 2023.
6. Calls the periodic_report function to generate the monthly report using the specified parameters.
7. The function returns a list of dictionaries, where each dictionary contains the parameters for an API call.
    Each API call retrieves the observations within a specific bounding box.
"""
from bard import *
import json
from typing import Dict, Any



parser = APIParser()
parameters = parser.get_parameters('observations')
parameters.update({
    "geo": True,
    "verifiable": True,
    "identified": True,
    #"endemic": True,
})

# lets see the monthly evolution along one year

parameters['d1'] = "2023-01-01"
parameters['d2'] = "2023-12-31"


coordinates = launch_map(save_polygon=True)
bounding_boxes, m = coordinates.get_grid(square_area=1, show_result=True, tolerance=0.03)

monthly_report = periodic_report(parameters, months=1, no_overlap=True)

# each element in the list is a dictionary with the parameters for the API call. For each of them, we will
# use the density function to get the observations in that area. This function will return a list whose elements
# are the observations in that area in each of the bounding boxes that span the area of interest.


# Prepare variables and kwargs for the density function
variables = (bounding_boxes, parameters)
kwargs = {'time_parameters': monthly_report}  # Pass the entire monthly_report


# Call the density function to get the observations
results = parser.make_request(user_function=density, variables=variables, **kwargs)['result']
print(f"Number of time periods: {len(results)}")
print(f"Number of bounding boxes in results: {len(results[0])}")
print(f"Number of bounding boxes extracted from map: {len(bounding_boxes)}")
print(f"Type of first time period data: {type(results[0])}")


def default_filter(obs: Dict[str, Any]) -> bool:
    return obs.get('taxon', {}).get('iconic_taxon_name') == 'Mollusca'

def default_heatmap_extraction(obs: Dict[str, Any]) -> int:
    return obs.get('observations_count', 1)

def default_popup_extraction(obs: Dict[str, Any]) -> str:
    return obs.get('taxon', {}).get('name')

config = BiodiversityConfig(
    filter_function=default_filter,
    heatmap_extraction=default_heatmap_extraction,
    popup_extraction=default_popup_extraction,
    heatmap_label='Total Mollusca Observations',
    popup_label='Unique Mollusca Species'
)

processed_data = process_observations(results, bounding_boxes, config)

time_periods = [f"Period {i+1}" for i in range(len(processed_data))]

time_series_maps = create_time_series_maps(processed_data, bounding_boxes, time_periods, config)

# Create the animated GIF
create_gif_from_maps(time_series_maps)
