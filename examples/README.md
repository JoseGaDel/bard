# Table of Contents

1. [Core components](#core-components)
   1. [API information](#api-information)
   2. [Lousy Input](#lousy-input)
      - [Strict Matching](#strict-matching)
   3. [Safe Dictionary](#safe-dictionary)
   4. [Pagination](#pagination)
   5. [Authentication](#authentication)
   6. [Multiton Pattern](#multiton-pattern)
2. [Data Analysis](#data-analysis)
   1. [Time series](#time-series)
   2. [Geographic data](#geographic-data)
3. [JSON manipulation](#json-manipulation)
   1. [QueryInspector](#queryinspector)
   2. [path_finder](#path-finder)
4. [Data Visualization](#data-visualization)
   1. [Key Components](#key-components)
   2. [Custom Data Extraction](#custom-data-extraction)
      - [Customizing BiodiversityConfig](#customizing-biodiversityconfig)
      - [Usage](#usage)

# Core components
The simplest example to get you started with BARD, only requires the following:

```python
from bard import APIParser

# Initialize the API parser
api_parser = APIParser()

# Get parameters for an API call
parameters = api_parser.get_parameters('observations')

# Make a request
result = api_parser.make_request(parameters)

print(result)
```

The core components of this module are the `APIParser` class and the parameters dictionary. The `APIParser` class is the main class of the module, and it is responsible for handling the API calls, authentication, and response parsing. The `APIParser.get_parameters` method give us a dictionary with the parameters needed for the API call, which we will fill with the desired configuration and the class will take care of constructing a valid API call from it. The rest of the module will use this parameters dictionary to understand what we want to get from the API.

## API information

The `APIParser` has a couple of methods to get information from the API documentation. For instance, we can get a list of available API calls with

```python
available_calls = api_parser.api_calls()
```

We can also get a table with the description of a specific API call

```python
api_parser.usecase("messages")
```

This will give as the description and the table of the call like

API Call: GET /messages
Description: Show the user's inbox or sent box


| Parameter | Description | Parameter Type | Data Type |
|:---:|:---:|:---:|:---:|
| page | Pagination `page` number | query | string |
| box | Whether to view messages the user has received (default) or messages the user has sent | query | string |
| q | Search query for subject and body | query | string |
| user_id | User ID or username of correspondent to filter by | query | string |
| threads | Groups results by `thread_id`, only shows the latest message per thread, and includes a `thread_messages_count` attribute showing the total number of messages in that thread. Note that this will not work with the `q` param, and it probably should only be used with `box=any` because the `thread_messages_count` will be inaccurate when you restrict it to `inbox` or `sent`. | query | boolean |

This way, we have can consult the API documentation from the program, without the need to access the API documentation. If, however, we do want to access the API documentation, we can do so with the `open_api_docs` method. This method will open the API documentation in the browser, and will try to find the exact call we are looking for. We can use the method with the exact name of the call, or with a more natural language, and the program will try to resolve it. For example:

```python
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
```

## Lousy Input

The `APIParser` class also implements a lousy input mechanism that allows the user to use a more natural language to interact with the API. This way, the user does not need to adhere to a strict format when setting the parameters. The program will try to resolve the input and set the correct parameter. For example, if we want to take the API call `/identifications/similar_species`, we do not need to write the exact name. We can write `similar species` and the program will resolve it to the correct call. We can use any non-alphanumeric character to separate the words, and the program will still resolve it correctly. For example, `similar-species`, `similar_species`, `similar species`, `similar.species` `similar/species`, etc., will all resolve to the correct API call. If the input matches multiple calls, the program will ask the user to select the correct one.

```python
# Exact match. There is only one call that has "identifications" + "similar" : /identifications/similar
# The method will take it directly
test_call = "identifications similar"
param_dict = api_parser.get_parameters(test_call)

# Ambiguous match. Just this keyword is not enough to unequivocally identify the call, as there are 4 calls containing it.
#The user will be asked to choose between them
test_call = "heatmap"
param_dict = api_parser.get_parameters(test_call)
```

The first example will automatically select the correct call, while the second example will ask the user for disambiguation:

```
Multiple matches found for heatmap. Please choose one:
    1. /colored_heatmap/{zoom}/{x}/{y}.png
    2. /colored_heatmap/{zoom}/{x}/{y}.grid.json
    3. /heatmap/{zoom}/{x}/{y}.png
    4. /heatmap/{zoom}/{x}/{y}.grid.json
Enter the number of your choice:
```

The program also has a fuzzy lookup mechanism that will try to resolve typos in the input. If no matches are found, the program will search for calls that have some resemblance to the input and ask the user if that is the call they wanted to use. If the user confirms, the program will continue with the corrected call. If the user denies, the program will raise an error. For example:

```python
# No matches. Given there is a typo, no API call will match any of its tokens. The system will catch that this is very similar to "messages" and suggest the calls that match with it.
test_call = "mesages"
param_dict = api_parser.get_parameters(test_call)
```
```
No matches found for 'mesages'
Did you mean one of the following? (If not, type 'n')
1. /messages
2. /messages/{id}
3. /messages/unread
4. /users/{id}
5. /posts
```

### Strict Matching

Some API calls will inevitably have similar names, and they will always have multiple matches. There are base calls like `/observations`, that have multiple derived calls, like `/observations/deletedObservations`, `/observations/histogram`, `/observations/identifiers`, etc. Any of the derived calls can be unequivocally identified, but the base call cannot. In order to prevent the program from prompting every time a base call is used, the parser has a `strict_matching` attribute that can be set to `True` or `False`. By default, so if there are multiple matches but one of them fully covers the input, the program will take it directly. If `strict_matching` is set to `False`, the program will ask the user to choose between the multiple matches.

```python
# The default is strict matching. This will take the base call directly
print("getting parameters with strict matching")
parameters  = api_parser.get_parameters('observations')

# Change the matching to non-strict, so the parser will ask us to choose between the multiple matches
api_parser.strict_matching = False
print("getting parameters with non-strict matching")
parameters  = api_parser.get_parameters('observations')
```

```
getting parameters with strict matching
getting parameters with non-strict matching
Multiple matches found for observations. Please choose one:
    1. /observations/{id}
    2. /observations/{id}/subscriptions
    3. /observations/{id}/taxon_summary
    4. /observations
    5. /observations/deleted
    6. /observations/histogram
    7. /observations/identifiers
    8. /observations/observers
    9. /observations/popular_field_values
    10. /observations/species_counts
    11. /observations/updates
Enter the number of your choice: 
```

See how the first call is taken directly, while the second one asks for disambiguation.


## Safe Dictionary

The `APIParser` uses a safe dictionary that ensures that the parameters we are using are correct and valid. If we introduce a typo or a parameter that does not exist, the program will try to resolve it by performing fuzzy lookup in the same way as for the API calls. If it finds a match, it will ask the user if that is the parameter they wanted to use. If the user confirms, the program will continue with the corrected parameter. If the user denies, the program will ask for a new parameter. This way, program prevents the user from constructing an incorrect API call, we don't need to wait for the error response from the server to know that we made a mistake and instead we can correct it on the fly and continue with the program.

```python
# Initialize the APIParser
api_parser = APIParser()

# Get parameters for an API call
parameters = api_parser.get_parameters('observations')

# The SafeDict class will catch typos and suggest corrections
parameters["threatenede"] = True  # typo
parameters["incorrect_key"] = "value"  # non-existent key

# Make a request
result = api_parser.make_request(parameters)
```

This would output:

```
Parameter 'threatenede' not found. Did you mean 'threatened'?
Y/N:
```
If the user types `Y`, the program will continue with the corrected parameter. If the user types `N`, the program will give us some options to correct the parameter. If we type `L`, the program will list the valid keys for the API call. In this case, the output would be:

```
"threatenede" is not a valid parameter for the API call /observations.
Do you want to (I)gnore this parameter, (C)orrect it, (L)ist valid keys, or (R)aise an error? I/C/L/R: l
Valid keys are:
1. API_call
2. acc
3. acc_above
4. acc_below
5. apply_project_rules_for
6. captive
7. created_d1
8. created_d2
9. created_on
10. cs
...
```

The output is truncated as the list is very long. If we select a number, it will assign the parameter to the selected key. If we select `I`, the program will ignore the parameter. If we select `R`, the program will raise an error. If we select `C`, the program will ask for a new parameter. The line `parameters["incorrect_key"] = "value"` won't find any match and it will directly prompt the same message as above.


## Pagination

Some API calls will return a large amount of data, and the server will truncate the response. This means that, to obtain all the data, we need to make multiple requests changing the page parameter and then concatenate all chunks of data. The `APIParser` class handles pagination automatically, making it easy to retrieve large amounts of data without worrying about the underlying pagination mechanism. When you make a request using BARD, you don't need to manually manage page numbers or construct multiple requests. The `APIParser` takes care of this for you. Here's how it works:

1. BARD sends the initial request with the parameters you provide.
2. If the API response indicates that there are more pages of data available, BARD automatically sends subsequent requests to retrieve the additional pages.
3. BARD combines the results from all pages into a single response, which is then returned to you.

```python
# This is an API call that requires pagination
parameters = api_parser.get_parameters('observations')
parameters['year'] = 2023

# Test with max_results
res_limited = api_parser.make_request(parameters, max_results=1000)
print(f"Limited results retrieved: {len(res_limited['results'])}")
```

This API call can return hundreds of thousands (or millions) of results, but the MINKA API has a limit of 200 results per page. The `APIParser` will automatically perform calls handling pagination until all results are obtained or until it reaches `max_results`, which can be set by the user to limit the number of results retrieved. In this case, we set `max_results=1000`, so the program will stop after retrieving 1000 results.

## Authentication

Some API calls require user authentication. The `APIParser` class has a method to set the authentication token. If we have a token at hand, we can manually set it using the `set_token` method. The token can be set as a string or as a dictionary. If the token is a dictionary, the program will try to resolve the token key. If the token is a string, the program will use it directly. If we do not have the token, BARD has an automatic mechanism to perform authentication automatically. The program will try to find an authentication endpoint in the API specification and will try to authenticate using the user credentials. If this endpoint is not present, it will try to find it in the description and if this fails, we will have the chance of passing this link to the program both in the program using `set_auth_endpoint`, or in the CLI if all the previous methods fail. 

```python
username = "my_username"
password = "my_password"
api_token = "my_api_token"

# Get the parameters dictionary for the API call
api_parser = APIParser(api_url="https://api.minka-sdg.org/v1", verbosity=3)

# If the parser fails to find the authentication endpoint, we can set it manually
api_parser.set_auth_endpoint("https://www.minka-sdg.org/users/api_token")
```

If the direction above is not an endpoint, it will ask us if we want to open the browser to automatically obtain the token. For example, iNaturalist and MINKA do not have an authorization endpoint, and instead you have to login in the link of the last line of the previous code and you will get a token. If we accept, the program will use Selenium to automatically access the login page, introduce the user credentials, log in and retrieve the token. If the IDs of the  username and password in the HTML are not the expected ones, we can manually log in. If you
are sure this will succeed, you can set the browser to headless mode setting `api_parser.headless = True`

```python
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
```

When we successfully authenticate, the program will set the token in the `APIParser` object and will use it for all the subsequent calls. It will also cache it so that we do not need to authenticate every time we run the program. If the token expires, the program will try to authenticate again to update the token and cache it again. If the program fails to authenticate, it will raise an error. This will output:

```
| ℹ️ INFO | API URL: https://api.minka-sdg.org/v1

| ℹ️ INFO | API Documentation URL: https://api.minka-sdg.org/v1/docs/

| ℹ️ INFO | Loading spec from cache.

| 🔍 DEBUG | No cached token found.

| 🔍 DEBUG | Found token URL in description: https://www.minka-sdg.org/users/api_token

| 🔍 DEBUG | Failed to authenticate using the API endpoint.
Do you want to authenticate using a browser? (y/n): y

| 🔍 DEBUG | Attempting to use Chrome...

| 🔍 DEBUG | Successfully logged in and reached the API token page.

| 🔍 DEBUG | Successfully obtained API token via browser authentication.

| 🔍 DEBUG | Token saved successfully to auth_token.json. Valid until: 2024-09-04T13:59:34.224864
Authentication successful
```

Now we should have a valid token in disk. Let's play with it to see how they work

```python
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
```

The first call will load the cached token, it will check it's expiration date and if it's still valid, it will use it. To show what happens when a token is expired, we manually change the expiration date of the token to two days before the current date. The program will find that the token is expired and will repeat the authentication process. This depends on the program knowing what is the lifetime of the token, because it checks the expiration date in the cached file which has an expiration date field that is set by the program. The framework uses a default lifetime of 24 hours, which is the value used by MINKA. For different APIs you may need to adjust this parameter in `APIParser(token_lifetime = time_in_seconds)` or `APIParser.token_lifetime = time_in_seconds`. The output will look something like this:

```
| ℹ INFO | 
*** Taking the exact match API call "/messages/unread" ***


| 🔍 DEBUG | Using cached token.
Result for call that requires authentication (messages/unread):
{'count': 0}

Now trying authentication using an expired cached API token.


| ℹ INFO | 
*** Taking the exact match API call "/messages/unread" ***


| ⚠ WARNING | Token loaded from auth_token.json is expired by 2 days, 0:00:00.000238.

| ⚠ WARNING | Cached token is expired.

| 🔍 DEBUG | Found token URL in description: https://www.minka-sdg.org/users/api_token

| 🔍 DEBUG | Failed to authenticate using the API endpoint.
Do you want to authenticate using a browser? (y/n): y

| 🔍 DEBUG | Attempting to use Chrome...

| 🔍 DEBUG | Successfully logged in and reached the API token page.

| 🔍 DEBUG | Successfully obtained API token via browser authentication.

| 🔍 DEBUG | Token saved successfully to auth_token.json. Valid until: 2024-09-04T14:38:04.125581
Result expired token (messages/unread):
{'count': 0}

```

We have not passed user credentials, so `make_request` will receive the error response form the server and will ask if we want to authenticate to update the token. If we choose yes, it will launch internally the authentication process, and then the request will be made again. If we didn't pass any password it will ask for it, because if the authentication is an endpoint, it will need the password to get the token. Note that previously we triggered this authentication process without password, so the program launched a browser if the authentication link was not an endpoint. If we press enter when we are asked for the password, the process will be similar to the previous one, because when the browser is launched it allows the user to log in manually. `make_request` has a kwarg input, so we can also set the password there:

```python
result = parser.make_request(parameters, password="my_password", username="my_username")
```

## Multiton Pattern
The APIParser is implemented following a Multiton pattern, which is an extension of the Singleton pattern. Without it, each invocation of the class, specially if no other instance was visible within that scope, will cause repeated initialization and excessive logging. For example, when used internally by functions because previous runs will destroy their context after completion and thus will create new instances each time they are called. With a Singleton pattern, the class is instantiated once and is accessed universally. The Multiton pattern allows to have multiple named instances, each of which acts as a Singleton. All the following declarations is equivalent:

```python
api_parser1 = APIParser()
api_parser2 = APIParser.get_instance()
api_parser3 = APIParser("default")
api_parser4 = APIParser.get_instance("default")
```

This four parsers are actually a reference to the same object and modifying one of them will modify all of them. Only when we assign them different identifications, does an independent key comes to existence. We can use this to have two coexisting parsers, each configured to access a different database:

```python
parser1 = APIParser(api_url="https://api.inaturalist.org/v1", verbosity=3, instance="parser1")
parser2 = APIParser(api_url="https://api.minka-sdg.org/v1" , verbosity=3, instance="parser2")
# Another alternative to initialize the new parser is:
parser2 = APIParser.get_instance("parser2", api_url="https://api.minka-sdg.org/v1", verbosity=3)
```

This will mean that a change to one parser will propagate to every other instance of that parser with the same identification (but not between parser with different identifications). If we want to apply temporal changes to the configuration of one parser, we can do so by using context manager:

```python
api_parser = APIParser(verbosity=1, strict_matching=True)

# This will use strict matching
result1 = api_parser.get_closest_api_call("observations")

# Temporarily disable strict matching
with api_parser.temporary_settings(strict_matching=False):
    # This will use non-strict matching
    result2 = api_parser.get_closest_api_call("observations")

# This will use strict matching again
result3 = api_parser.get_closest_api_call("observations")

# To change verbosity (or any other variable), we use the same function
def some_function():
    with api_parser.temporary_settings(verbosity=0):
        api_parser.usecase("some_endpoint")
```

In contrast, consider the alternative:

```python
api_parser = APIParser(verbosity=1, strict_matching=True)

api_parser.strict_matching = False

def some_function():
    other_parser = APIParser()
```

Here, maybe we would expect that `other_parser` would have different settings from `api_parser`, but it will actually have the same settings as `api_parser` because it is a reference to the same object. Therefore, even if we expect it to have the default `strict_matching=True` even being in the scope of the function, the change made with `api_parser.strict_matching = False` is universal and `other_parser` will reflect this change. The context manager allows us to change the settings temporarily and then revert them back to the original settings, as in the previous case.



# Data Analysis

## Time series

We can use the function `periodic_report` to retrieve to perform a series of API calls with a certain period. To use this, we need to set a parameter from an API call that works as a lower bound for observations and another that will set the upper bound. When we call the function, we can set what period we want to use and it will split the time range in periods of the specified length and will return a list with a parameters dictionary in each element with the correct date parameters to get the data for that period.

```python
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
```

The function will take care of leap years, months with different number of days, etc. Imagine we want to get a weekly report of the month of January 2023, which we have specified above with the parameters `d1` and `d2`. By default, the function will split the period in windows of one week such that the first window will be from `d1` to `d1 + 1 week`, the second window will be from `d1 + 1 week` to `d1 + 2 weeks`, and so on, in such a way that the last element of one period coincides with the first element of the next, i.e., there are overlap between period and thus no gaps. We can change this behavior by setting the parameter `no_overlap` to `True`, in which case the periods will be disjoint. we can use the following to test the different behaviors:

```python
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
```

The output will look like this:

```
With overlap:
[
  {
    "d1": "2023-01-01",
    "d2": "2023-01-08",
    "API_call": "/identifications/similar_species"
  },
  {
    "d1": "2023-01-08",
    "d2": "2023-01-15",
    "API_call": "/identifications/similar_species"
  },
  {
    "d1": "2023-01-15",
    "d2": "2023-01-22",
    "API_call": "/identifications/similar_species"
  },
  {
    "d1": "2023-01-22",
    "d2": "2023-01-29",
    "API_call": "/identifications/similar_species"
  },
  {
    "d1": "2023-01-29",
    "d2": "2023-01-31",
    "API_call": "/identifications/similar_species"
  }
]

Without overlap:
[
  {
    "d1": "2023-01-01",
    "d2": "2023-01-07",
    "API_call": "/identifications/similar_species"
  },
  {
    "d1": "2023-01-08",
    "d2": "2023-01-14",
    "API_call": "/identifications/similar_species"
  },
  {
    "d1": "2023-01-15",
    "d2": "2023-01-21",
    "API_call": "/identifications/similar_species"
  },
  {
    "d1": "2023-01-22",
    "d2": "2023-01-28",
    "API_call": "/identifications/similar_species"
  },
  {
    "d1": "2023-01-29",
    "d2": "2023-01-31",
    "API_call": "/identifications/similar_species"
  }
]
```

This function also supports parameters of type date-time:

```python
param_dict['created_d1'] = "2023-01-01T00:00:00"
param_dict['created_d2'] = "2023-01-31T23:59:59"

result_with_overlap_datetime = periodic_report(param_dict, days=7)
```

## Geographic data

Imagine we want to get a certain observation for unit of area in a specific area of interest. We would need to get the coordinates of each bounding box, insert them in the parameters, perform the API call, and repeat until we have covered the entire area. Instead of doing this manually, we can use following functions:

```python
parameters  = api_parser.get_parameters('observations')

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
result = density(bounding_boxes, parameters)


# Alternatively, we can use pass this function to make_request and it will forward it to the execution endpoint,
# where it will be executed, and we will get back the results.
variables = (bounding_boxes, parameters)
result = api_parser.make_request(user_function=density, variables=variables)
```

In the `get_grid` method, we can set the `square_area` parameter to the desired area of the bounding box in square kilometers. The `tolerance` parameter is used to set what is the minimum fraction a bounding box needs to intersect the polygon in order to be included. The default is 0, which is the most permissive, and will include all bounding boxes that intersect the polygon, no matter how minimal this intersection is. If we set a tolerance of 1, the program will not include any bounding box that is not fully contained within the polygon, so there will not be any area outside the polygon but will mean there are bigger uncovered gaps inside the polygon. You can play with this parameter and the `square_area` to get a finer grained division of the area. You can also choose a different area unit with the `area_units` parameter. COmpatible units are square kilometers (`km2`), hectares (`ha`, `hm2`), square decametre (`dam2`),  square meters (`m2`), acres (`acres`), square feet (`sqf`), square yards (`sqy`), and square miles (`sqm`). The default is `km2`.

![tolerances](https://github.com/user-attachments/assets/d73c52ee-d40a-4819-b3a9-a6d95020657b)


Once we have our bounding boxes, we can use the `density` function to get the data for each bounding box. This function will take care of the API calls, and will return a list with the results for each bounding box. We can also pass this function to `make_request` and it will be executed in the server side and return the results. We can also use the `density` function to combine both the bounding boxes and the periodic report. This way, we can get the data for each bounding box in each period to, for example, study the time evolution of an observation on a geographic area. We can use the following code to test this:

```python
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


# Prepare variables and kwargs for the density function
variables = (bounding_boxes, parameters)
kwargs = {'time_parameters': monthly_report}  # Pass the entire monthly_report

# We can run locally with
result = density(bounding_boxes, parameters, time_parameters=monthly_report)
# or with 
result = density(bounding_boxes, parameters, **kwargs)


# Remote execution
result = api_parser.make_request(user_function=density, variables=variables, **kwargs)
```


https://github.com/user-attachments/assets/f1518ed8-83d0-4342-8690-96138b00c315


# JSON manipulation

## QueryInspector

The `QueryInspector` class has methods to manipulate JSON data, offering a set of primitive functions that can be used to filter, transform, or aggregate data. The `QueryInspector` class is a wrapper around a JSON object that allows us to perform operations on it in a functional way. We can chain multiple operations together to build complex queries. The `QueryInspector` class has the following methods:

```python
from bard import QueryInspector, load_json

data = load_json('result.json')
query = QueryInspector(data)

result = (query
    .select('result')
    .map(lambda x: x.get('results', []))
    .flatten()
    .filter(lambda x: 'identifications' in x and x['identifications'])
    .map(lambda x: x['identifications'][0].get('taxon', {}).get('ancestors', []))
    .flatten()
    .sort('observations_count', reverse=True)
    .map(lambda x: x.get('name'))
    .get())
```

Key methods:

- `select(path)`: Selects a specific path in the JSON structure.
- `filter(condition)`: Filters the data based on a condition.
- `map(func)`: Applies a function to each item in the data.
- `flatten()`: Flattens nested lists into a single list.
- `sort(key, reverse=False)`: Sorts the data based on a key.
- `get()`: Returns the final result.

Here are some examples of how to use `QueryInspector`:

```python
from bard import QueryInspector, load_json

data = load_json('result.json')
query = QueryInspector(data)

# Example 1: Get all species names
species_names = (query
    .select('result')
    .map(lambda x: x.get('species', []))
    .flatten()
    .map(lambda x: x.get('name'))
    .get())

print("Species names:", species_names[:5])  # Print first 5 names

# Example 2: Get observation counts for families, sorted in descending order
family_observations = (query
    .select('result')
    .map(lambda x: x.get('families', []))
    .flatten()
    .filter(lambda x: x.get('observations_count', 0) > 100)
    .sort('observations_count', reverse=True)
    .map(lambda x: (x.get('name'), x.get('observations_count')))
    .get())

print("Family observations:", family_observations[:5])  # Print top 5

# Example 3: Get unique iconic taxon names
iconic_taxa = (query
    .select('result')
    .map(lambda x: x.get('iconic_taxa', []))
    .flatten()
    .map(lambda x: x.get('name'))
    .get())

print("Unique iconic taxa:", list(set(iconic_taxa)))

# Example 4: Get average observations per species
avg_observations = (query
    .select('result')
    .map(lambda x: x.get('species', []))
    .flatten()
    .map(lambda x: x.get('observations_count', 0))
    .get())

if avg_observations:
    print("Average observations per species:", sum(avg_observations) / len(avg_observations))
```

The `QueryInspector` class is a powerful tool for working with JSON data, but requires some knowledge of the JSON structure to be effective. An easier approach comes by the hand of the `path_finder` function.

## path_finder

The `path_finder` function is a powerful tool for searching and extracting specific elements from complex JSON structures. It allows you to use logical expressions to define search criteria, making it easy to find elements that match multiple conditions.

Key features:
- Supports complex logical expressions using AND (&&) and OR (||) operators
- Allows parentheses for grouping conditions
- Provides various comparison operators: ==, !=, <, <=, >, >=
- Supports string operations: contains, startswith, endswith
- Includes membership testing with 'in' operator
- Checks for existence of fields with 'exists' operator
- Allows negation with 'not' prefix

Basic syntax:
```python
path_finder(data, logic_str, start_point="", return_content=False, compare_results=False)
```

Parameters:

- `data`: The JSON data to search
- `logic_str`: A string representing the logical expression for searching
- `start_point`: The path from which to start the search (optional)
- `return_content`: If True, returns both paths and content of matching elements
- `compare_results`: If True, returns comparison information for multiple results

Some examples of their use:

```python
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
```

Sometimes this will return a lot of results, so we can use the `compare_results` parameter to get a summary of the results. This will allow us to use the function  `comparison_results` to get a detailed breakdown of shared and unique values across multiple results, helping you understand the similarities and differences in your data.

Key features:
- Accepts various input formats (packed results, unpacked results, paths and contents, or just comparison data)
- Displays unique combinations of values across results
- Shows shared values across all results
- Highlights unique values for individual paths
- Provides a clear, formatted output for easy analysis

Basic syntax:
```python
comparison_results(results, logic_str="", start_point="")
```

Parameters:

- `results`: The results to compare (can be in various formats)
- `logic_str`: The logic string used in the path_finder call (optional)
- `start_point`: The start point used in the path_finder call (optional)

Here are some examples demonstrating how to use comparison_results:

```python
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
```


# Data Visualization

This tool allows you to create animated heatmaps that visualize biodiversity data over time and space. This feature combines geographical analysis with time-based reporting to provide dynamic insights into species distribution and abundance.

## Key Components

1. `BiodiversityConfig`: A configuration class for specifying data processing and visualization parameters.
2. `process_observations`: Function to process observation data for each time period and bounding box.
3. `create_time_series_maps`: Function to create a series of folium maps for each time period.
4. `create_gif_from_maps`: Function to generate an animated GIF from the series of maps.

## Custom Data Extraction

The system now allows for custom data extraction, giving you the flexibility to analyze any aspect of the JSON data structure. Here's how you can use this feature:

### Customizing BiodiversityConfig

You can now pass custom functions to `BiodiversityConfig` to decide how to filter, extract heatmap data, and extract popup information from the JSON data. Here's an example of how to customize the configuration:

```python
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
```

### Usage

To see how to use these components to create an animated biodiversity heatmap head to [examples/time_evolution.py](time_evolution.py).
![biodiversity_evolution_mollusca](https://github.com/user-attachments/assets/bcbe7155-b3e6-4b30-be64-e6a1ad0a1232)

