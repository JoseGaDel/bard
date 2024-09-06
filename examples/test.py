from bard import *


# ____ Consult the API documentation ____

api_parser = APIParser()

# Get a list of all the API calls
api_calls = api_parser.api_calls()

# Consult the documentation of a specific API call. This will print a table on the console
api_parser.usecase('messages')

# You can also get the table itself
table = api_parser.usecase('messages', return_table=True)


## ____ Open API documentation ____

api_parser.open_api_docs()
# This will open the API documentation main page

api_parser.open_api_docs("get identifications id")
# This will directly open: /v1/docs/#!/Identifications/get_identifications_id

api_parser.open_api_docs("delete identifications id")
# This will directly open: /v1/docs/#!/Identifications/delete_identifications_id

api_parser.open_api_docs("identifications/{id}")
# As we didn't specify the method, it will ask us to choose between:
# 1. GET /identifications/{id}
# 2. PUT /identifications/{id}
# 3. DELETE /identifications/{id}


api_parser.open_api_docs("identifications/id")
api_parser.open_api_docs("identifications id")
# This two should give the same result as the previous one


api_parser.open_api_docs("observations")
# This will match with lots of endpoints


## ____ Example of using the APIParser, corrections, etc ____

coordinates = launch_map(save_polygon=True)
bounding_boxes = coordinates.get_grid(square_area=4, show_result=True)

# Get the parameters dictionary for the API call
api_parser = APIParser()
parameters = api_parser.get_parameters('mesages') # this call has default parameters. Note that they get automatically added to the dictionary

parameters["threatenede"] = True # this is a typo. The SafeDict class will catch it and ask for a correction
parameters["incorrect_key"] = "value" # this key is not in the list of parameters and will suggest changes


for key, value in parameters.items():
    if value:
        print(f"{key}: {value}")

del parameters

parameters = api_parser.get_parameters('observations')
parameters['per_page'] = 200


variables = (bounding_boxes, parameters)
result = api_parser.make_request(user_function=density, variables=variables)


import json
# save result to a file
with open("result.json", "w") as file:
    file.write(json.dumps(result, indent=4))



# ____ Example of pagination ____

api_parser = APIParser()
# This is an API call that requires pagination
parameters = api_parser.get_parameters('observations')
parameters['year'] = 2023
# we can uncomment the following lines to test that the program stops retrieving when the
# server has sent all the data, because with that there's 240 results
# parameters.update({
#     "day": 10,
#     "month": 3,
# })

# Test with max_results
res_limited = api_parser.make_request(parameters, max_results=1000)
print(f"Limited results retrieved: {len(res_limited['results'])}")

'''
without pagination, we would have needed to manually change the page number in the parameters dictionary
and make a new request. The APIParser class takes care of this for us. It would have looked like this:
    
    parameters['page'] = 2
    res_page2 = api_parser.make_request(parameters)
    parameters['page'] = 3
    res_page3 = api_parser.make_request(parameters)
    etc.
'''


# This is an API call that do not require pagination
del parameters
parameters = api_parser.get_parameters('observations id')
parameters['id'] = 123

# test fetching
res_unpaged = api_parser.make_request(parameters)
print(f"Unpaged results retrieved: {len(res_unpaged['results'])}")





# ____ Example of using periodic report ____

api_parser = APIParser(verbosity=1)
param_dict = api_parser.get_parameters("identifications similar species")


# Test with date
param_dict['d1'] = "2023-01-01"
param_dict['d2'] = "2023-01-31"

# Imagine we want a time window of 1 week, 3 days, 2h30m15s. We can use periodic_report like this:
periodic_report(param_dict, weeks=1, days=3, hours=2, minutes=30, seconds=15)
# Or this, which is the equivalent in weeks to the previous one
periodic_report(param_dict, weeks=1.44347718254)
# If we want to divide the period in 10 equal parts, we can use the following:
periodic_report(param_dict, period=10)

# The function will take care of leap years, months with different number of days, etc. 
# let's see the results for a period of 7 days. If we don't set no_overlap to True, the periods will overlap
result_with_overlap = periodic_report(param_dict, days=7)
result_with_overlap = [ {k: v for k, v in d.items() if v} for d in result_with_overlap ]
print("With overlap:")
print(json.dumps(result_with_overlap, indent=2))

# now we set no_overlap to True, so the periods will not overlap.
result_without_overlap = periodic_report(param_dict, days=7, no_overlap=True)
result_without_overlap = [ {k: v for k, v in d.items() if v} for d in result_without_overlap ]
print("\nWithout overlap:")
print(json.dumps(result_without_overlap, indent=2))

# Test with date-time
del param_dict
param_dict = api_parser.get_parameters("identifications_similar_species")
param_dict['created_d1'] = "2023-01-01T00:00:00"
param_dict['created_d2'] = "2023-01-31T23:59:59"

result_with_overlap_datetime = periodic_report(param_dict, days=7)
# for each element of the list, remove the empty elements of the dictionary
result_with_overlap_datetime = [ {k: v for k, v in d.items() if v} for d in result_with_overlap_datetime ]
print("\nWith overlap (datetime):")
print(json.dumps(result_with_overlap_datetime, indent=2))

result_without_overlap_datetime = periodic_report(param_dict, days=7, no_overlap=True)
# for each element of the list, remove the empty elements of the dictionary
result_without_overlap_datetime = [ {k: v for k, v in d.items() if v} for d in result_without_overlap_datetime ]
print("\nWithout overlap (datetime):")
print(json.dumps(result_without_overlap_datetime, indent=2))


# ____ Example of the strict matching ____


# Let's compare the difference between strict and non-strict matching. The default is strict matching,
# so the following example will find multiple matches for the 'observations' API call:

#     1. /observations/{id}
#     2. /observations/{id}/subscriptions
#     3. /observations/{id}/taxon_summary
#     4. /observations
#     5. /observations/deleted
#     6. /observations/histogram
#     7. /observations/identifiers
#     8. /observations/observers
#     9. /observations/popular_field_values
#     10. /observations/species_counts
#     11. /observations/updates

# The 4th entry covers completely the 'observations' string, so it will be the one selected. Therefore,
# the following should be taking directly, without any prompt:

print("getting parameters with strict matching")
parameters  = api_parser.get_parameters('observations')

# Now we will change the matching to non-strict, so the parser will ask us to choose between the multiple matches
# above
print("getting parameters with non-strict matching")

del parameters
api_parser.strict_matching = False

# Get the parameters dictionary for the API call
parameters  = api_parser.get_parameters('observations')

# ____ Example of using the density function ____
input("Press Enter to continue...")

parameters  = api_parser.get_parameters('observations')

# of abundance per area
# This will launch a map where we can select the area of interest and save the coordinates of the bounding boxes
coordinates = launch_map(save_polygon=True)

# The method will return a list where each element is a list of coordinates of the bounding box,
# and the resulting map. Remember to unpack them.
bounding_boxes, _ = coordinates.get_grid(square_area=1, show_result=True, tolerance=0.03)

parameters.update({
    "year": 2023,
    "day": 10,
    "month": 3,
})


# We can use the density function to take care of the API calls. This function calls make_request internally
# for each bounding box using concurrent.futures to speed up the process
print("Local request, using the density function")
result = density(bounding_boxes, parameters)


print("Complex request, forwarding function to be executed on the server")
variables = (bounding_boxes, parameters)
result = api_parser.make_request(user_function=density, variables=variables)


# We can also combine both the geographical data and the periodic_report to get the
# time evolution of the density of observations in a specific area
parameters = api_parser.get_parameters('observations')
parameters.update({
    "geo": True,
    "verifiable": True,
    "identified": True,
    "endemic": True,
})

# lets see the monthly evolution along one year

parameters['d1'] = "2023-01-01"
parameters['d2'] = "2023-12-31"

monthly_report = periodic_report(parameters, months=1, no_overlap=True)

# each element in the list is a dictionary with the parameters for the API call. For each of them, we will
# use the density function to get the observations in that area. This function will return a list whose elements
# are the observations in that area in each of the bounding boxes that span the area of interest.


# Prepare variables and kwargs for the density function
variables = (bounding_boxes, parameters)
kwargs = {'time_parameters': monthly_report}  # Pass the entire monthly_report

# Make the request
result = api_parser.make_request(user_function=density, variables=variables, **kwargs)





## ____ Example of filtering JSON using QueryInspector ____

data = load_json('result.json')
query = QueryInspector(data)

# Get the name of the item with the biggest observations_count for each API call
result = (query
    .select('result')                                                               # Select the 'result' path in the JSON structure
    .map(lambda x: x.get('results', []))                                            # Map each item to its 'results' list
    .flatten()                                                                      # Flatten the list of lists into a single list
    .filter(lambda x: 'identifications' in x and x['identifications'])              # Filter items that have 'identifications'
    .map(lambda x: x['identifications'][0].get('taxon', {}).get('ancestors', []))   # Map to the 'ancestors' list of the first 'identifications' item
    .flatten()                                                                      # Flatten the list of ancestors                            
    .sort('observations_count', reverse=True)                                       # Sort the ancestors by 'observations_count' in descending order
    .map(lambda x: x.get('name'))                                                   # Map to the 'name' of each ancestor                        
    .get())                                                                         # Get the final result

# print(len(result))
#print(result)



## ____ Example of filtering by conditions: function path_finder ____

with open('result.json', 'r') as f:
    data = json.load(f)


# Simple condition - Find all families
results = path_finder(data, "rank == family")

# Multiple conditions with AND logic - Find extinct mollusks
results = path_finder(data, "extinct == true && iconic_taxon_name == Mollusca", return_content=True)
print("\nExtinct mollusks:")
for path, content in results:
    print(f"Path: {path}")
    print(f"Name: {content.get('name')}")
    print(f"Rank: {content.get('rank')}")

# Complex logical expression - Find either families with high observation count or classes with low observation count
complex_logic = "(rank == family && observations_count > 10000) || (rank == class && observations_count < 1000)"
results = path_finder(data, complex_logic, return_content=True)
print("\nFamilies with high observations or classes with low observations:")
for path, content in results:
    print(f"Path: {path}")
    print(f"Name: {content.get('name')}")
    print(f"Rank: {content.get('rank')}")
    print(f"Observations: {content.get('observations_count')}")

# Using 'exists' operator - Find all taxa with a Wikipedia URL
results = path_finder(data, "wikipedia_url exists && wikipedia_url != null")
print("\nTaxa with Wikipedia URLs:")
for path in results:
    print(path)

# Using 'contains' operator - Find taxa with '116' in their ancestry
results = path_finder(data, "ancestry contains 116", start_point="result[0]")
print("\nTaxa under ancestry 116 in the first result:")
for path in results:
    print(path)

# Using 'startswith' operator - Find taxa whose name starts with 'A'
results = path_finder(data, "name startswith A")
print("\nTaxa whose names start with 'A':")
for path in results:
    print(path)

# Using 'in' operator - Find taxa with specific licenses
logic_str = "license_code in ['cc-by-nc', 'cc-by', 'cc0']"
results = path_finder(data, logic_str)
for path in results[:5]:
    print(path)

# If more than one path is found, the user may only be interested in one, or a specific combination of paths
# The following examples showcase how to 

with open('result.json', 'r') as f:
    data = json.load(f)

logic_str = "extinct == false && rank == family && observations_count exists"
paths_and_contents, comparison = path_finder(data, logic_str, start_point="result[1]", return_content=True, compare_results=True)

print(f"Paths and contents found (logic: '{logic_str}', starting from 'result[1]') (found {len(paths_and_contents)}):")
for path, _ in paths_and_contents:
    print(f"Path: {path}")
print()

print("Comparison results:")
print("\nUnique combinations:")
for combo in comparison["unique_combinations"]:
    print(f"Paths: {combo['paths']}")
    print("Unique values:")
    for key, value in combo['values'].items():
        if comparison["shared_values"].get(key) == "MULTIPLE_VALUES":
            print(f"  {key}: {value}")
    print()

print("Shared values across all paths:")
for key, value in comparison["shared_values"].items():
    if value != "MULTIPLE_VALUES":
        print(f"{key}: {value}")

print("\nUnique values for individual paths:")
for path, unique_values in comparison["unique_values"].items():
    if unique_values:
        print(f"Path: {path}")
        for key, value in unique_values.items():
            print(f"  {key}: {value}")
        print()

# All this can be done in a single function call:
# 1. With packed results from path_finder
logic_str = "extinct == false && rank == family && observations_count exists"
results = path_finder(data, logic_str, start_point="result[1]", return_content=True, compare_results=True)
print('\n\n\nWith packed results from path_finder:')
comparison_results(results, logic_str, "result[1]")

# 2. With unpacked results
print('\nWith unpacked results:')
paths_and_contents, comparison = path_finder(data, logic_str, start_point="result[1]", return_content=True, compare_results=True)
comparison_results((paths_and_contents, comparison), logic_str, "result[1]")

# 3. With just paths_and_contents (comparison will be generated)
print('\nWith just paths_and_contents:')
paths_and_contents = path_finder(data, logic_str, start_point="result[1]", return_content=True)
comparison_results(paths_and_contents, logic_str, "result[1]")

# 4. With just comparison results
comparison_results(comparison)

# Note that it can handle different input formats, whether you pass the packed results from path_finder, 
# unpacked results, just the paths_and_contents, or just the comparison. If only paths_and_contents is provided, 
# it automatically generates the comparison using advanced_compare.

# With those results, we can apply an additional filter on the initial results instead of the entire file
refined_logic_1 = "ancestor_ids contains 211"
refined_results_1 = filter_results(paths_and_contents, refined_logic_1)

print(f"Results after first refinement: {len(refined_results_1)}")

# We can refine further if needed
refined_logic_2 = "observations_count > 500"
final_results = filter_results(refined_results_1, refined_logic_2)

print(f"Final results: {len(final_results)}")

# Print the final results
for path, content in final_results:
    print(f"Path: {path}")
    print(f"Name: {content.get('name')}")
    print(f"Ancestry: {content.get('ancestry')}")
    print(f"Observations: {content.get('observations_count')}")
    print()




## ____ Example of how authentication works ____


username = "my_username"
password = "my_password"
api_token = "my_api_token"

# Get the parameters dictionary for the API call
api_parser = APIParser(api_url="https://api.minka-sdg.org/v1", verbosity=3)

# If the parser fails to find the authentication endpoint, we can set it manually
# api_parser.set_auth_endpoint("https://www.minka-sdg.org/users/api_token")


# Try to authenticate. If the direction above is not an endpoint, it will ask us if
# we want to open the browser to automatically obtain the token. If the IDs of the 
# username and password are not the expected ones, we can manually log in. If you
# are sure this will succeed, you can set the browser to headless mode:
# api_parser.headless = True


# Try to authenticate
try:
    api_parser.authenticate(username, password)
    print("Authentication successful")
except Exception as e:
    print(f"Failed to authenticate: {str(e)}")

# Make an API call that requires authentication
try:
    result = api_parser.make_request(api_parser.get_parameters("messages/unread"))
    print(f'Result for call that requires authentication (messages/unread):\n{result}')
except ValueError as e:
    print(f"Error making API call: {str(e)}")

# When we authenticate, the token is saved in a file called `auth_token.json`. If we now make another
# request, the parser will use the cached token, so the following will make the request automatically
print(f'\nNow trying authentication using the cached API token.\n')
result = api_parser.make_request(api_parser.get_parameters("messages/unread"))
print(f'Result cached token (messages/unread):\n{result}')




print(f'\nNow trying authentication using an expired cached API token.\n')
# the cached token is in `auth_token.json`. It looks like `{"token": "...", "expiry": "2024-08-13T16:31:46.647766"}`
# so lets load the file, subtract two days from the expiry date and save it again
import json
from datetime import datetime, timedelta

# Read the JSON file
with open("auth_token.json", "r") as file:
    token_data = json.load(file)

# Parse the expiry date, subtract 2 days, and format it back to string
expiry_date = datetime.fromisoformat(token_data["expiry"])
token_data["expiry"] = (expiry_date - timedelta(days=2)).isoformat()

# Write the updated data back to the file
with open("auth_token.json", "w") as file:
    json.dump(token_data, file)

# Try to authenticate again
api_parser.auth_token = None
api_parser.auth_expiry = None
result = api_parser.make_request(api_parser.get_parameters("messages/unread"))
print(f'Result expired token (messages/unread):\n{result}')



# Here we can see the multiton pattern at play. We create a new instance of the APIParser
# which will be a separate object with its own attributes. You can try changing the verbosity
# or the url and check that the other instance is not affected.
parser2 = APIParser(api_url="https://api.minka-sdg.org/v1" , verbosity=3, instance="parser2")
# Another alternative to initialize the new parser is:
parser2 = APIParser.get_instance("parser2", api_url="https://api.minka-sdg.org/v1", verbosity=3)
# These two are equivalent.


# Now let's see what happens when the user manually sets a token that is outdated or invalid
parser2.set_api_token(api_token)
parameters = parser2.get_parameters("messages/unread")
print('f\nPerforming request with outdated token\n')
result = parser2.make_request(parameters)
print(f'\nResult messages/unread:\n{result}')

# We have not passed user credentials, so `make_request` will receive the error response form the server
# and will ask if we want to authenticate to update the token. If we choose yes, it will launch internally
# the authentication process, and then the request will be made again. If we didn't pass any password it will
# ask for it, because if the authentication is an endpoint, it will need the password to get the token.
# Note that previously we triggered this authentication process without password, so the program launched
# a browser if the authentication link was not an endpoint. If we press enter when we are asked for the password,
# the process will be similar to the previous one, because when the browser is launched it allows the user to
# log in manually. make_request has a kwarg input, so we can also set the password there:

result = parser2.make_request(parameters, password="my_password", username="my_username")
