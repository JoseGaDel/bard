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

The core components of this module are the `APIParser` class and the parameters dictionary. The `APIParser` class is the main class of the module, and it is responsible for handling the API calls, authentication, and response parsing. The `APIParser.get_parameters` method give us a dictionary with the parameters needed for the API call. This way, we do not need to worry about constructing API calls and just to set what parameters we want to use. The rest of the module will use this parameters dictionary to understand what we want to get from the API.

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