import json
import requests
import urllib.parse
import webbrowser
from difflib import get_close_matches
import re
from datetime import datetime, timedelta
import os
import logging
from functools import lru_cache
from contextlib import contextmanager
from typing import Any, Dict, List, Optional, Union, Callable, Tuple

from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver.safari.service import Service as SafariService
from selenium.webdriver.edge.service import Service as EdgeService
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.edge.options import Options as EdgeOptions
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.firefox import GeckoDriverManager
from webdriver_manager.microsoft import EdgeChromiumDriverManager
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import platform
import time
import pickle
from colorama import Fore, Style, init



class SafeDict(dict):
    '''
    This dictionary class only allows the keys that were present when the dictionary was created.
    It will be used by the APIParser class to ensure that only the parameters allowed by the API are used.
    It also allows removal of existing keys and provides options for correcting or ignoring invalid keys.
    '''
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._original_keys = set(self.keys())

    def __setitem__(self, key: str, value: Any) -> None:
        """
        Set the value for a key in the dictionary. If the key is not in the original
        set of keys, it prompts the user for action.

        Args:
            - key (str): The key to set.
            - value (Any): The value to set for the key.
        """
        if key in self._original_keys:
            super().__setitem__(key, value)
        else:
            closest_match = get_close_matches(key, self._original_keys, n=1, cutoff=0.6)
            if closest_match:
                print(f"Parameter '{key}' not found. Did you mean '{closest_match[0]}'?")
                user_choice = input("Y/N: ").lower()
                if user_choice == 'y':
                    super().__setitem__(closest_match[0], value)
                else:
                    self._handle_invalid_key(key, value)
            else:
                self._handle_invalid_key(key, value)

    def _handle_invalid_key(self, key: str, value: Any) -> None:
        """
        Handle the case when an invalid key is provided.

        This method prompts the user for action when an invalid key is encountered.

        Args:
            - key (str): The invalid key.
            - value (Any): The value associated with the invalid key.
        """
        while True:
            print(f'"{key}" is not a valid parameter for the API call {self.get("API_call", "")}.')
            user_choice = input("Do you want to (I)gnore this parameter, (C)orrect it, (L)ist valid keys, or (R)aise an error? I/C/L/R: ").lower()
            if user_choice == 'i':
                print(f"Ignoring parameter '{key}'")
                break
            elif user_choice == 'c':
                new_key = input("Enter the correct parameter name: ")
                if new_key in self._original_keys:
                    super().__setitem__(new_key, value)
                    print(f"Parameter corrected: '{new_key}' = {value}")
                    break
                else:
                    print(f"'{new_key}' is also not a valid parameter.")
                    continue
            elif user_choice == 'l':
                self._list_and_select_key(key, value)
                break
            elif user_choice == 'r':
                raise KeyError(f"Key '{key}' is not allowed in this dictionary")
            else:
                print("Invalid choice. Please try again.")

    def _list_and_select_key(self, original_key: str, value: Any) -> None:
        """
        List all valid keys and allow the user to select one.

        Args:
            - original_key (str): The original (invalid) key.
            - value (Any): The value associated with the original key.
        """
        sorted_keys = sorted(self._original_keys)
        while True:
            print("Valid keys are:")
            for i, valid_key in enumerate(sorted_keys, 1):
                print(f"{i}. {valid_key}")
            
            selection = input("Enter the number of the correct key, or '0' to go back: ")
            if selection == '0':
                return
            
            try:
                index = int(selection) - 1
                if 0 <= index < len(sorted_keys):
                    selected_key = sorted_keys[index]
                    super().__setitem__(selected_key, value)
                    print(f"Parameter corrected: '{selected_key}' = {value}")
                    return
                else:
                    print("Invalid number. Please try again.")
            except ValueError:
                print("Please enter a valid number.")

    def __delitem__(self, key: str) -> None:
        """
        Delete a key from the dictionary.

        Args:
            - key (str): The key to delete.

        Raises:
            - KeyError: If the key is not in the dictionary.
        """
        if key in self._original_keys:
            super().__delitem__(key)
            self._original_keys.remove(key)
        else:
            raise KeyError(f"Key '{key}' is not in this dictionary")

    def pop(self, key: str, *args: Any) -> Any:
        """
        Remove and return an element from the dictionary.

        Args:
            - key (str): The key of the item to remove and return.
            - *args: Default value if the key is not found.

        Returns:
            - Any: The value of the removed key.
        """
        result = super().pop(key, *args)
        if key in self._original_keys:
            self._original_keys.remove(key)
        return result

    def clear(self) -> None:
        """Get a clean state by removing all items from the dictionary and the set of original keys."""
        super().clear()
        self._original_keys.clear()

    def update(self, *args: Union[Dict[str, Any], List[tuple]], **kwargs: Any) -> None:
        """
        Update the dictionary with the key/value pairs from other, overwriting existing keys.

        This method implements the same logic as __setitem__ for each key-value pair.

        Args:
            - *args: Either another dictionary object or an iterable of key/value pairs.
            - **kwargs: Keyword arguments to be added to the dictionary.

        Raises:
            - TypeError: If more than one positional argument is provided.
        """
        # Implements the same logic as __setitem__ for each key-value pair
        if args:
            if len(args) > 1:
                raise TypeError("update expected at most 1 arguments, got {}".format(len(args)))
            other = dict(args[0])
            for key in other:
                self[key] = other[key]
        for key in kwargs:
            self[key] = kwargs[key]


class APIParser:
    """
    Class to parse an OpenAPI spec and provide functionality about the API calls. This class
    is intended to simplify the process of interacting with an API by constructing the API call.
    It also provides information about the API calls, such as the parameters they require, so the user
    doesn't need to refer to the API documentation every time they want to make a call. The class is
    implemented following a Multiton pattern to avoid fetching the API repeatedly every time a function uses a 
    method from this class. This allows us to create an instance of the class as a singleton, such that every
    time we invoke a method from this class, we use the same instance, and if we modify the settings of the class, 
    it will propagate to every place where we use the class. Note that this implies that by default, functions using this class 
    will use the same verbosity level. If you want to change the verbosity level locally,
    you can use the temporary_verbosity context manager.

    The verbosity levels are:
        0: ERROR
        1: WARNING
        2: INFO
        3: DEBUG
        4: TRACEBACK

    If the user wants to use a different instance of the class, they can use the get_instance method, which allows to have
    coexisting instances of the class with different settings:

    ```
    # This will always return the same instance
    default_parser = APIParser.get_instance()

    # This will return a different instance, but always the same one for this key
    another_parser = APIParser.get_instance("another")
    ```

    Equivalently, we can use direct constructor with different settings from the start, and they will be independent of each other:

    ```
    # These will be completely independent instances
    parser1 = APIParser(instance="parser1", verbosity=2)
    parser2 = APIParser(instance="parser2", verbosity=1)

    # That is equivalent to:
    parser1 = APIParser.get_instance("parser1", verbosity=2)
    parser2 = APIParser.get_instance("parser2", verbosity=1)
    ```
    """
    _instances = {}

    @classmethod
    def get_instance(cls, instance="default", **kwargs):
        if instance not in cls._instances:
            cls._instances[instance] = cls(instance=instance, **kwargs)
        return cls._instances[instance]

    def __new__(cls, instance="default", **kwargs):
        if instance not in cls._instances:
            cls._instances[instance] = super(APIParser, cls).__new__(cls)
        return cls._instances[instance]

    def __init__(self, instance="default", api_url=None, doc_url=None, verbosity=1, strict_matching=True, token_lifetime=86400, server_ip="127.0.0.1", server_port=8000, executable_endpoint='execute'):
        self.instance = instance
        self.verbosity = verbosity
        self.strict_matching = strict_matching
        self.api_url = "https://minka-tfm.quanta-labs.com:4000/v1" if api_url is None else api_url
        self.base_url, self.api_doc = self._parse_url(api_url)
        self.server_ip = server_ip    # Server where the endpoint /execute is hosted
        self.server_port = server_port # Port where the endpoint /execute is hosted
        self.executable_endpoint = executable_endpoint
        self.logger = self._setup_logger(verbosity)
        self._log_init_info()
        self.cache_location = "spec.json"
        self.spec = self._fetch_spec()
        self.auth_endpoint = None
        self.auth_token = None
        self.auth_expiry = None
        self.token_lifetime = token_lifetime  # Default is 86400 seconds (24 hours)
        self.headless = False
        self.use_cookies = False # Use saved cookies for authentication. I think the server forces revalidation each time the browser is closed
        self.cookie_file = 'minka_cookies.pkl'
        self.paths = self.spec.get('paths', {})
        self.initialized = True

    def _parse_url(self, url : str) -> Tuple[str, str]:
        # Remove trailing slash if present
        url = url.rstrip('/')

        # Check if the URL ends with '/docs'
        if url.endswith('/docs'):
            api_doc = url
            base_url = re.sub(r'/docs/?$', '', url)
        else:
            base_url = url
            api_doc = f"{url}/docs"

        # Ensure base_url doesn't end with a version number
        base_url = re.sub(r'/v\d+$', '', base_url)

        # Parse the URL to extract the scheme and netloc
        parsed_url = urllib.parse.urlparse(base_url)
        scheme_and_netloc = f"{parsed_url.scheme}://{parsed_url.netloc}"

        # If base_url is just the scheme and netloc, append '/v1'
        if base_url == scheme_and_netloc:
            base_url += '/v1'

        return base_url, api_doc

    def _setup_logger(self, verbosity: int) -> logging.Logger:
        logger = logging.getLogger(f"{self.__class__.__name__}_{self.instance}")
        if logger.hasHandlers():
            logger.handlers.clear()
        
        level_map = {
            0: logging.ERROR,
            1: logging.WARNING,
            2: logging.INFO,
            3: logging.DEBUG
        }

        logger.setLevel(level_map.get(verbosity, logging.DEBUG))  # Default to DEBUG if out of range
        handler = logging.StreamHandler()

        # Initialize colorama for cross-platform color support
        init()

        class ColoredFormatter(logging.Formatter):
            FORMATS = {
                logging.DEBUG: Fore.CYAN + "\n| 🔍 %(levelname)s | %(message)s" + Style.RESET_ALL,
                logging.INFO: Fore.GREEN + "\n| ℹ️ %(levelname)s | %(message)s" + Style.RESET_ALL,
                logging.WARNING: Fore.YELLOW + "\n| ⚠️ %(levelname)s | %(message)s" + Style.RESET_ALL,
                logging.ERROR: Fore.RED + "\n| ❌ %(levelname)s | %(message)s" + Style.RESET_ALL,
                logging.CRITICAL: Fore.MAGENTA + "\n| 🚨 %(levelname)s | %(message)s" + Style.RESET_ALL
            }
            # With timestamps:
            # FORMATS = {
            #     logging.DEBUG: Fore.CYAN + "🔍 %(asctime)s | %(name)s | %(levelname)-8s | %(message)s" + Style.RESET_ALL,
            #     logging.INFO: Fore.GREEN + "ℹ️  %(asctime)s | %(name)s | %(levelname)-8s | %(message)s" + Style.RESET_ALL,
            #     logging.WARNING: Fore.YELLOW + "⚠️  %(asctime)s | %(name)s | %(levelname)-8s | %(message)s" + Style.RESET_ALL,
            #     logging.ERROR: Fore.RED + "❌ %(asctime)s | %(name)s | %(levelname)-8s | %(message)s" + Style.RESET_ALL,
            #     logging.CRITICAL: Fore.MAGENTA + "🚨 %(asctime)s | %(name)s | %(levelname)-8s | %(message)s" + Style.RESET_ALL
            # }

            def format(self, record):
                log_fmt = self.FORMATS.get(record.levelno)
                formatter = logging.Formatter(log_fmt, datefmt='%Y-%m-%d %H:%M:%S')
                return formatter.format(record)

        handler.setFormatter(ColoredFormatter())
        logger.addHandler(handler)
        return logger

    def _log_init_info(self):
        self.logger.info(f"API URL: {self.base_url}")
        self.logger.info(f"API Documentation URL: {self.api_doc}")

    def set_verbosity(self, level):
        self.verbosity = level

    @contextmanager
    def temporary_settings(self, **kwargs):
        """
        Temporarily change any number of settings for a block of code.
        
        Example:
        ```
        api_parser = APIParser(verbosity=1, strict_matching=True)

        with api_parser.temporary_settings(verbosity=2, strict_matching=False):
            # APIParser will have verbosity 2 and strict_matching False only within this block
            api_parser.usecase("some_endpoint")

        # Outside the block, settings return to their original values
        ```
        """
        original_settings = {}
        for key, value in kwargs.items():
            if hasattr(self, key):
                original_settings[key] = getattr(self, key)
                setattr(self, key, value)
            else:
                print(f"Warning: {key} is not a valid setting for APIParser")

        try:
            yield
        finally:
            for key, value in original_settings.items():
                setattr(self, key, value)
    
    def _fetch_spec(self) -> Dict[str, Any]:
        """
        Fetch the OpenAPI specification, either from cache or from the server.

        Returns:
            - Dict[str, Any]: The OpenAPI specification as a dictionary.
        """
        # first check if there is a cached spec and it is not older than a week
        cached_spec = self._load_cached_spec()
        if cached_spec:
            return cached_spec

        # if not, fetch a new one
        return self._fetch_and_cache_new_spec()

    def _load_cached_spec(self) -> Optional[Dict[str, Any]]:
        """
        Attempt to load the OpenAPI specification from a local cache file.

        Returns:
            - Optional[Dict[str, Any]]: The cached specification if valid and recent, None otherwise.
        """
        try:
            with open(self.cache_location, 'r') as f:
                cached_data = json.load(f)
            
            if 'cached_date' not in cached_data:
                # If the cached spec does not have a cached_date, fetch a new one for good measure
                return None

            cached_date = datetime.fromisoformat(cached_data['cached_date'])
            if datetime.now() - cached_date <= timedelta(weeks=1):
                self.logger.info("Loading spec from cache.")
                return cached_data
            else:
                self.logger.warning("Cached spec is older than a week. Fetching new spec.")
                return None
        except FileNotFoundError:
            self.logger.warning("No cached spec found.")
            return None
        except json.JSONDecodeError:
            self.logger.warning("Cached spec is invalid. Fetching new spec.")
            return None

    def _fetch_and_cache_new_spec(self) -> Dict[str, Any]:
        """
        Fetch a new OpenAPI specification from the server and cache it locally.

        Returns:
            - Dict[str, Any]: The newly fetched OpenAPI specification.

        Raises:
            - Exception: If unable to fetch the spec from any of the possible paths.
        """
        possible_paths = [
            "/v1/swagger.json",
            "/swagger.json",
            "/openapi.json",
            "/api-docs.json",
            "/v1/api-docs.json"
        ]
        # Try multiple paths, some servers may have the spec in different locations
        for path in possible_paths:
            spec = self._fetch_openapi_spec(path)
            if spec:
                self.logger.debug(f"Successfully fetched spec from {path}\nCaching retrieved spec as {self.cache_location}")
                # Now we cache the spec
                spec['cached_date'] = datetime.now().isoformat()
                with open(self.cache_location, 'w') as f:
                    json.dump(spec, f)
                return spec
        self.logger.critical("Failed to fetch API spec from all possible paths.")
        raise Exception


    def _fetch_openapi_spec(self, spec_path: str) -> Optional[Dict[str, Any]]:
        """
        Attempt to fetch the OpenAPI specification from a specific path.

        Args:
            - spec_path (str): The path to append to the base API documentation URL.

        Returns:
            - Optional[Dict[str, Any]]: The OpenAPI specification if successfully fetched, None otherwise.
        """
        url = urllib.parse.urljoin(self.api_doc, spec_path)
        self.logger.debug(f"Attempting to fetch spec from: {url}")
        
        response = requests.get(url)
        self.logger.debug(f"Response status code: {response.status_code}")
        
        if response.status_code != 200:
            self.logger.error(f"Failed to fetch API spec. Status code: {response.status_code}")
            return None

        try:
            return response.json()
        except json.JSONDecodeError:
            self.logger.error(f"Failed to parse JSON. Response content: {response.text[:200]}...")
            return None

    def _resolve_parameter(self, param: Any) -> Optional[Dict[str, Any]]:
        """
        Resolve a parameter reference in the OpenAPI specification.

        Args:
            - param (Any): The parameter to resolve, which can be a dictionary or a string reference.

        Returns:
            - Optional[Dict[str, Any]]: The resolved parameter as a dictionary, or None if unable to resolve.
        """
        # If the parameter is a dictionary, it might be a direct parameter definition or a reference
        if isinstance(param, dict):
            # Check if it's a reference (indicated by the presence of '$ref' key)
            if '$ref' in param:
                # Split the reference string into a list of path components
                ref_path = param['$ref'].split('/')
                # Resolve the reference using the _resolve_ref method
                return self._resolve_ref(ref_path)
            # If it's not a reference, return the parameter as is
            return param
        # If the parameter is a string starting with '#/', it's a reference path
        elif isinstance(param, str) and param.startswith('#/'):
            # Split the reference string into a list of path components
            ref_path = param.split('/')
            # Resolve the reference using the _resolve_ref method
            return self._resolve_ref(ref_path)
        # If it's neither a dict nor a reference string, we can't resolve it
        return None

    def _resolve_ref(self, ref_path: list) -> Optional[Dict[str, Any]]:
        """
        Resolve a reference path in the OpenAPI specification.

        Args:
            - ref_path (list): A list of keys representing the path to the referenced object.

        Returns:
            - Optional[Dict[str, Any]]: The resolved object from the specification, or None if not found.
        """
        # Start at the root of the specification
        current = self.spec
        # Iterate through each part of the reference path
        for part in ref_path[1:]:  # Skip the first '#' element
            # If the current part exists in the current object, move to that part
            if part in current:
                current = current[part]
            else:
                # If at any point we can't find the next part, the reference is invalid
                return None
        # Return the final object we've navigated to
        return current
    
    # __ Authentication methods __
    def _check_auth_required(self, path, method='get'):
        """Check if the API call requires authentication."""
        if path in self.paths and method in self.paths[path]:
            return 'security' in self.paths[path][method]
        return False

    def _get_auth_info(self):
        """Retrieve authentication information from the spec."""
        if 'securityDefinitions' in self.spec:
            return self.spec['securityDefinitions']
        elif 'components' in self.spec and 'securitySchemes' in self.spec['components']:
            return self.spec['components']['securitySchemes']
        return None

    def _get_auth_endpoint(self) -> bool:
        """Get the authentication endpoint from the spec, description, or manual setting."""
        if self.auth_endpoint:
            return True
        
        auth_info = self._get_auth_info()
        # We try retrieving the tokenUrl from the securityDefinitions or components.securitySchemes
        if auth_info and auth_info['api_token'].get('tokenUrl'):
            self.auth_endpoint = auth_info['api_token'].get('tokenUrl')
            self.logger.debug(f"Found token URL in securityDefinitions: {self.auth_endpoint}")
            return True
        
        # If this fails, as a last resort we look for the token URL in the description
        if 'info' in self.spec and 'description' in self.spec['info']:
            description = self.spec['info']['description']
            match = re.search(r'(https?://\S+/users/api_token)', description)
            if match:
                self.logger.debug(f"Found token URL in description: {match.group(1)}")
                self.auth_endpoint = match.group(1)
                return True
            else:
                # if the previous pattern fail, try with the first link that can be found right
                # after the keyword `OAuth` in the description
                match = re.search(r'OAuth\s*(https?://\S+)', description)
                if match:
                    self.logger.debug(f"Found OAuth link in description: {match.group(1)}")
                    self.auth_endpoint = match.group(1)
                    return True
        
        return False

    def _obtain_jwt_token(self, username, password):
        """Obtain a JWT token using the provided credentials."""

        if not self._get_auth_endpoint():
            # If all _get_auth_endpoint methods fail, ask the user to visit the API documentation
            # and paste the authentication endpoint here, or interrupt the program and set it manually
            self.logger.warning("Authentication endpoint not found in the API specification.")
            self.auth_endpoint = input(f'Please visit the API documentation at {self.api_doc} and paste the authentication endpoint here. You can also press enter to interrupt the program and set the authentication endpoint manually with set_auth_endpoint. \n    answer:').strip()
            if not self.auth_endpoint:
                exit(1)

        auth_url = urllib.parse.urljoin(self.base_url, self.auth_endpoint)
        try:
            response = requests.post(auth_url, json={'username': username, 'password': password})
            response.raise_for_status()
            token_data = response.json()
            
            self.auth_token = token_data.get('token')
            # Assume the token expires in 24 hours if not specified
            expires_in = token_data.get('expires_in', 86400)
            self.auth_expiry = datetime.now() + timedelta(seconds=expires_in)
        except requests.exceptions.RequestException:
            self.logger.debug("Failed to authenticate using the API endpoint.")
            self._browser_authentication(username, password)

    def _browser_authentication(self, username, password):
        import traceback
        """Authenticate using browser automation."""
        user_input = input("Do you want to authenticate using a browser? (y/n): ").lower()
        if user_input.lower() not in ['y', 'yes']:
            raise ValueError("Authentication failed and browser authentication was declined.")

        # Try to authenticate using different browsers. We try with Chrome first and fallback to Firefox, Safari, and Edge
        browsers = [
            ('chrome', webdriver.Chrome, ChromeService, ChromeDriverManager, ChromeOptions),
            ('firefox', webdriver.Firefox, FirefoxService, GeckoDriverManager, FirefoxOptions),
            ('safari', webdriver.Safari, SafariService, None),
            ('edge', webdriver.Edge, EdgeService, EdgeChromiumDriverManager, EdgeOptions)
        ]

        for browser_name, browser_class, service_class, driver_manager, options_class in browsers:
            try:
                self.logger.debug(f"Attempting to use {browser_name.capitalize()}...")
                if browser_name == 'safari' and platform.system() != 'Darwin':
                    self.logger.debug("Safari is only available on macOS. Skipping...")
                    continue

                options = options_class() if options_class else None
                if browser_name in ['chrome', 'firefox', 'edge']:
                    options = getattr(webdriver, f"{browser_name.capitalize()}Options")()
                    # If you want to run the browser in headless mode, set the headless attribute to True
                    # but beware that some websites may not work properly in headless mode if the IDs 
                    # of the user and password don't match the expected ones.
                    if self.headless:
                        options.add_argument('--headless')

                if driver_manager:
                    service = service_class(driver_manager().install())
                    driver = browser_class(service=service, options=options)
                else:
                    driver = browser_class()

                return self._perform_browser_login(driver, username, password)
            except Exception as e:
                self.logger.debug(f"Failed to use {browser_name.capitalize()}: {str(e)}")
                self.logger.debug(f"Error type: {type(e)}")
                if self.verbosity >= 4:
                    self.logger.debug(f"Error traceback: {traceback.format_exc()}\n")
                continue
        self.logger.critical("Browser authentication failed with all available browsers.")
        raise ValueError

    def _perform_browser_login(self, driver, username, password):
        """Perform the actual login process using the provided WebDriver."""
        # Try to use saved cookies first
        if self.use_cookies:
            driver.get(self.auth_endpoint)
            if self._load_cookies(driver):
                #driver.get(auth_endpoint)
                if driver.current_url == self.auth_endpoint:
                    self.logger.debug("Successfully logged in using saved cookies.")
                else:
                    self.logger.debug("Saved cookies are invalid or expired. Proceeding with manual login.")
                    driver.delete_all_cookies()
        if not driver.current_url == self.auth_endpoint:
            driver.get(self.auth_endpoint)            
            try:
                # Wait for the username field to be visible and enter the username. Try ID user_email and if not found, try ID user_login
                try:
                    username_field = WebDriverWait(driver, 5).until(
                        EC.presence_of_element_located((By.ID, "user_email"))
                    )
                except TimeoutException:
                    username_field =  driver.find_element(By.ID, "user_login")
                if password and username:
                    username_field.send_keys(username)

                    password_field = driver.find_element(By.ID, "user_password")
                    password_field.send_keys(password)

                    submit_button = driver.find_element(By.NAME, "commit")
                    submit_button.click()
                    wait_indefinitely = False
                else:
                    wait_indefinitely = True

                # Wait for redirection. We check if we're already on the API token page to avoid waiting more than necessary
                start_time = time.time()
                while time.time() - start_time < 60 or wait_indefinitely:  # 60 seconds timeout so the user has time to log in
                    if driver.current_url == self.auth_endpoint:
                        self.logger.debug("Successfully logged in and reached the API token page.")
                        break
                    time.sleep(0.5)  # Check every 0.5 seconds
                else:
                    raise TimeoutException("Timed out waiting for redirection")
            except TimeoutException:
                # Check if we're already on the API token page
                if driver.current_url == self.auth_endpoint:
                    self.logger.debug("Already logged in and on the API token page.")
                else:
                    print("Automatic login failed or timed out. Please log in manually in the opened browser window.")
                    print(f"Please navigate to {self.auth_endpoint} after logging in.")
                    print("Press Enter once you're on the API token page...")
                    input()

                    if not driver.current_url == self.auth_endpoint:
                        self.logger.error("Failed to reach the API token page after manual login.")
                        raise ValueError
        
        if self.use_cookies:
            # Save cookies after successful login
            self._save_cookies(driver)

        # Extract the API token from the page
        try:
            if isinstance(driver, webdriver.Chrome) or isinstance(driver, webdriver.Edge):
                # Chrome-style (also works for Edge)
                api_token_element = WebDriverWait(driver, 3).until(
                    EC.presence_of_element_located((By.TAG_NAME, "pre"))
                )
                api_token_json = json.loads(api_token_element.text)
                self.auth_token = api_token_json.get('api_token')
            elif isinstance(driver, webdriver.Firefox) or isinstance(driver, webdriver.Safari):
                # Firefox-style (also works for Safari)
                api_token_element = WebDriverWait(driver, 3).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "span.objectBox.objectBox-string"))
                )
                token_match = re.search(r'"([^"]+)"', api_token_element.text)
                if token_match:
                    self.auth_token = token_match.group(1)
                else:
                    raise ValueError("Could not extract token from span element")
            else:
                raise ValueError("Unsupported browser type")

            if not self.auth_token:
                raise ValueError("Failed to extract API token from the page")

        except (TimeoutException, NoSuchElementException, json.JSONDecodeError, ValueError) as e:
            self.logger.error(f"Automatic token extraction failed: {str(e)}\n     Please copy the API token from the page.\n")
            self.auth_token = input("Paste the API token here: ").strip()

        finally:
            driver.quit()

        self.logger.debug("Successfully obtained API token via browser authentication.")
        # cache the token
        # Assume the token expires in 24 hours if not specified
        self._save_token(self.auth_token) 
        return True


    def authenticate(self, username=None, password=None) -> None:
        """
        Authenticate and obtain a JWT token.
        If username and password are not provided, it will use the manually set token.
        """
        # first check if there is a token in cache and it has not expired
        if self._load_token():
            if self._is_token_expired():
                self.auth_token = None
                self.auth_expiry = None
                self.logger.warning("Cached token is expired.")
                # try manual authentication
            else:
                self.logger.debug("Using cached token.")
                return
        else:
            self.logger.debug("No cached token found.")
        
        # if there was no cached token or it has expired, try to authenticate
        try:
            self._obtain_jwt_token(username, password)
        except ValueError as e:
            self.logger.error(str(e))
        if not self.auth_token:
            self.logger.critical("No authentication credentials provided and no API token set. Please provide credentials or set an API token.")
            raise ValueError
    
    def _save_cookies(self, driver):
        """Save the cookies for the current session."""
        if not os.path.exists('cookies'):
            os.makedirs('cookies')
        with open(os.path.join('cookies', self.cookie_file), 'wb') as file:
            pickle.dump(driver.get_cookies(), file)
        self.logger.debug(f"Cookies saved successfully at {self.cookie_file}")

    def _load_cookies(self, driver):
        """Load saved cookies into the current session."""
        try:
            with open(os.path.join('cookies', self.cookie_file), 'rb') as file:
                cookies = pickle.load(file)
                for cookie in cookies:
                    driver.add_cookie(cookie)
                    driver.refresh()
            self.logger.debug(f"Cookies loaded successfully from {self.cookie_file}")
            return True
        except FileNotFoundError:
            self.logger.debug("No cookies found.")
            return False

    def set_api_token(self, token, expires_in=None):
        """
        Manually set the API token.
        
        Args:
            - token (str): The API token.
            - expires_in (int, optional): The number of seconds until the token expires.
                                        If not provided, the token will use the default set in teh attribute.
        """
        self.auth_token = token
        if expires_in:
            self.auth_expiry = datetime.now() + timedelta(seconds=expires_in)
        else:
            # Tke the default expiration time from the class attribute
            self.auth_expiry = datetime.now() + timedelta(seconds=self.token_lifetime)

    def _check_auth_required(self, path, method='get'):
        """Check if the API call requires authentication."""
        if path in self.paths and method in self.paths[path]:
            return 'security' in self.paths[path][method]
        return False
    
    def _save_token(self, token):
        """Save the authentication token with its expiration time."""
        self.auth_token = token
        self.auth_expiry = datetime.now() + timedelta(seconds=self.token_lifetime)
        
        # Save token to file for persistence across sessions
        token_data = {
            'token': self.auth_token,
            'expiry': self.auth_expiry.isoformat()
        }
        with open('auth_token.json', 'w') as f:
            json.dump(token_data, f)
        self.logger.debug(f"Token saved successfully to auth_token.json. Valid until: {self.auth_expiry.isoformat()}")

    def _load_token(self) -> bool:
        """Load the authentication token and its expiration time from file."""
        # first make sure an up to date token is not already loaded
        if self.auth_token and self.auth_expiry and not self._is_token_expired():
            return True
        try:
            with open('auth_token.json', 'r') as f:
                token_data = json.load(f)
            self.auth_token = token_data['token']
            self.auth_expiry = datetime.fromisoformat(token_data['expiry'])
            valid_until = self.auth_expiry - datetime.now()
            if valid_until.total_seconds() < 0:
                self.logger.warning(f"Token loaded from auth_token.json is expired by {-valid_until}.")
            else:
                self.logger.debug(f"Token loaded successfully from auth_token.json. Valid until: {self.auth_expiry.isoformat()} ({self.auth_expiry - datetime.now()} remaining)")
            return True
        except (FileNotFoundError, json.JSONDecodeError, KeyError):
            self.auth_token = None
            self.auth_expiry = None
            return False

    def _is_token_expired(self):
        """Check if the current token has expired."""
        if not self.auth_token or not self.auth_expiry:
            return True
        return datetime.now() >= self.auth_expiry


    # __ Methods for interacting with the API __

    def api_calls(self) -> list[str]:
        """
        Function to get all the API calls available in the OpenAPI spec. Useful
        for the user to know which calls are available.
        Args:
            None
        Returns:
            - list[str]: A list of all the API calls available in the OpenAPI spec.
        """
        return [path for path, methods in self.paths.items() if 'get' in methods]

    def usecase(self, user_input : str, return_table : bool = False) -> list[str]:
        """
        Function to get information about a specific API call. It can also return the
        table with the API documentation in a list format if the return_table parameter
        is set to True. Some functions use this method to get information about parameters.
        Args:
            - user_input (str): The user input to match with an API call.
            - return_table (bool): Whether to return the table with the API documentation. Default is False.
        Returns:
            - list[str]: The table with the API documentation in a list format.
        """
        from tabulate import tabulate
        import textwrap

        path = self.get_closest_api_call(user_input)
        if not path:
            self.logger.error("No matching API call found.")
            return
        
        if path not in self.paths or 'get' not in self.paths[path]:
            self.logger.error(f"No GET method found for path: {path}")
            return

        method_info = self.paths[path]['get']
        description = method_info.get('description', 'No description available')
        parameters = method_info.get('parameters', [])

        table_data = []
        for param in parameters:
            resolved_param = self._resolve_parameter(param)
            if resolved_param:
                name = resolved_param.get('name', '')
                desc = resolved_param.get('description', '')
                param_type = resolved_param.get('in', '')
                data_type = resolved_param.get('type', '')
                if data_type == 'array':
                    data_type = f"Array[{resolved_param.get('items', {}).get('type', '')}]"
                if data_type == 'string' and resolved_param.get('format'):
                    data_type = resolved_param.get('format')
                table_data.append([name, desc, param_type, data_type])

        headers = ["Parameter", "Description", "Parameter Type", "Data Type"]
        
        # Wrap the description text so the description column is not too wide
        for row in table_data:
            row[1] = textwrap.fill(row[1], width=40)
        
        if return_table:
            return table_data

        # All internal calls to this method will have returned before this, so the following
        # prints will only be executed when the user calls this method directly without setting
        # the return_table parameter to True.
        print(f"API Call: GET {path}")
        print(f"Description: {textwrap.fill(description, width=80)}\n")
        print(tabulate(table_data, headers=headers, tablefmt="grid", colalign=("left", "left", "left", "left")))

    def open_api_docs(self, endpoint: Optional[str] = None) -> None:
        """
        Opens the API documentation in the default web browser.
        If an endpoint is specified, it tries to open the documentation for that specific endpoint or group.

        Args:
            - endpoint (Optional[str]): The specific API endpoint or group to open documentation for.

        Returns:
            - None
        """
        if not self.api_doc:
            self.logger.error("API documentation URL is not set.")
            return

        if endpoint:
            matches = self._find_matching_endpoints(endpoint)
            if len(matches) == 1:
                doc_link = self._construct_doc_link(*matches[0])
            elif len(matches) > 1:
                selected_match = self._prompt_user_for_selection(matches, endpoint)
                if selected_match:
                    doc_link = self._construct_doc_link(*selected_match)
                else:
                    self.logger.warning("No selection made. Opening general API documentation.")
                    webbrowser.open(self.api_doc)
                    return
            else:
                self.logger.warning(f"Couldn't find a matching endpoint for '{endpoint}'. Opening general API documentation.")
                webbrowser.open(self.api_doc)
                return

            specific_url = urllib.parse.urljoin(self.api_doc, doc_link)
            webbrowser.open(specific_url)
            self.logger.info(f"Opened API documentation for '{doc_link}' in browser: {specific_url}")
        else:
            webbrowser.open(self.api_doc)
            self.logger.info(f"Opened API documentation in browser: {self.api_doc}")

    def _find_matching_endpoints(self, endpoint: str) -> List[Tuple[str, str]]:
        """
        Find matching endpoints in the API specification. This method attempts to
        find endpoints that match the given input. It first tries to find endpoints that
        contain all the words in the input. If no such endpoints are found, it falls
        back to partial matching, sorting the results by the number of matching words.

        Args:
            - endpoint (str): The endpoint to search for.

        Returns:
            - List[Tuple[str, str]]: A list of tuples, where each tuple contains 
                (path, method) of matching endpoints.
        """

        endpoint_words = set(re.findall(r'\w+', endpoint.lower()))
        matches = []

        for path, methods in self.paths.items():
            path_words = set(re.findall(r'\w+', path.lower()))
            for method in methods.keys():
                method_words = set(re.findall(r'\w+', method.lower()))
                combined_words = path_words.union(method_words)
                
                # Check if all endpoint words are present in the combined words
                if endpoint_words.issubset(combined_words):
                    matches.append((path, method))

        # If we have matches with all words, return only those
        if matches:
            return matches

        # If no full matches, try partial matching
        partial_matches = []
        for path, methods in self.paths.items():
            path_words = set(re.findall(r'\w+', path.lower()))
            for method in methods.keys():
                method_words = set(re.findall(r'\w+', method.lower()))
                combined_words = path_words.union(method_words)
                
                # Check how many words match
                matching_words = endpoint_words.intersection(combined_words)
                if matching_words:
                    partial_matches.append((path, method, len(matching_words)))

        # Sort partial matches by number of matching words, descending
        partial_matches.sort(key=lambda x: x[2], reverse=True)

        # Return the paths and methods, without the count
        return [(path, method) for path, method, _ in partial_matches]

    def _prompt_user_for_selection(self, matches: List[Tuple[str, str]], endpoint : str) -> Optional[Tuple[str, str]]:
        """
        Prompt the user to select from multiple matching endpoints. Present the user 
        with a numbered list of matching endpoints and prompt them to select one.
        The user can also choose to cancel the selection.

        Args:
            - matches (List[Tuple[str, str]]): A list of tuples, where each tuple contains 
                (path, method) of matching endpoints.
            - endpoint (str): The original endpoint input, so that we can display it to the user.

        Returns:
            - Optional[Tuple[str, str]]: The selected (path, method) tuple if a selection 
                was made, or None if the selection was cancelled.
        """
        print(f"Multiple matches found for {endpoint}. Please select one:")
        for i, (path, method) in enumerate(matches, 1):
            print(f"{i}. {method.upper()} {path}")
        
        while True:
            try:
                choice = int(input("Enter the number of your choice (or 0 to cancel): "))
                if choice == 0:
                    return None
                if 1 <= choice <= len(matches):
                    return matches[choice - 1]
                print("Invalid choice. Please try again.")
            except ValueError:
                print("Invalid input. Please enter a number.")

    def _construct_doc_link(self, path: str, method: str) -> str:
        """
        Construct the documentation link for a given path and method. Creates a link
        fragment that can be appended to the base documentation URL to navigate
        directly to the specified endpoint.

        Args:
            - path (str): The API path.
            - method (str): The HTTP method.

        Returns:
            - str: The documentation link fragment.
        """
        # Extract the tag (usually the first part of the path)
        tag = path.split('/')[1].replace('_', ' ').title().replace(' ', '_')
        
        # Construct the operation ID
        operation_id = f"{method}_{path[1:].replace('/', '_').replace('{', '').replace('}', '')}"

        return f"#!/{tag}/{operation_id}"


    # @lru_cache(maxsize=None)
    def get_parameters(self, user_input: str) -> SafeDict:
        """
        Function to get the parameters for a specific API call. It returns a SafeDict object
        with the parameters for the API call as keys, so the user only needs to assign values
        to the parameters they want to use. This is the backbone of the implementation, 
        as every function that interacts with the API will use this to infer the desired call.
        Args:
            - user_input (str): The user input to match with an API call. It uses fuzzy lookup
                               so the user doesn't need to type the exact API call, just enough
                               to match it unambiguously.
        Returns:
            - SafeDict: A dictionary with the parameters for the API call. The keys are the parameter
                       names, and the values are empty strings. The user can then assign values to
                       the parameters they want to use. SafeDict won't allow the user to add parameters
                       that are not part of the API call.
        """
        path = self.get_closest_api_call(user_input)
        if not path:
            self.logger.error("No matching API call found.")
            return {}
        if path not in self.paths or 'get' not in self.paths[path]:
            return {}

        parameters = self.paths[path]['get'].get('parameters', [])
        param_dict = {}
        
        for param in parameters:
            resolved_param = self._resolve_parameter(param)
            if resolved_param:
                name = resolved_param.get('name', '')
                if name:
                    # Check for default value
                    default_value = resolved_param.get('default')
                    if default_value is None and 'schema' in resolved_param:
                        default_value = resolved_param['schema'].get('default')
                    
                    param_dict[name] = default_value if default_value is not None else ''

        # Add the API call to the parameter dictionary
        param_dict['API_call'] = path

        return SafeDict(param_dict)


    def get_parameter_types(self, path : str) -> dict:
        """
        Function to get the types of the parameters for a specific API call from the OpenAPI spec.
        Used mainly by internal methods.
        Args:
            - path (str): The API call to get the parameter types for.
        Returns:
            - dict: A dictionary with the parameter names as keys and the parameter types as values.
                   The parameter types are the location of the parameter (path, query, header, etc.)
                   and the data type of the parameter (string, integer, etc.).
        """
        if not path:
            self.logger.error("No matching API call found.")
            return {}
        if path not in self.paths or 'get' not in self.paths[path]:
            return {}

        parameters = self.paths[path]['get'].get('parameters', [])
        param_types = {}

        for param in parameters:
            resolved_param = self._resolve_parameter(param)
            if resolved_param:
                name = resolved_param.get('name', '')
                param_type = resolved_param.get('in', '')
                data_type = resolved_param.get('type', '')

                if data_type == 'array':
                    items = resolved_param.get('items', {})
                    item_type = items.get('type', '')
                    if items.get('format'):
                        item_type = items.get('format')
                    data_type = f"Array[{item_type}]"
                elif data_type == 'string' and resolved_param.get('format'):
                    data_type = resolved_param.get('format')

                param_types[name] = {
                    'parameter_type': param_type,
                    'data_type': data_type
                }

        return param_types
    
    def get_closest_api_call(self, user_input : str) -> str:
        """
        Function to get the most similar API call to the user input. It uses fuzzy lookup
        to find the closest match to the user input. If there are multiple matches, it will
        prompt the user to choose one. If there are no matches, it will try to guess the API
        call by searching for 'good enough' matches.
        Args:
            - user_input (str): The user input to match with an API call.
        Returns:
            - str: The closest API call to the user input.
        """
        # Get all API calls
        all_calls = self.api_calls()

        # Split the user input into tokens and search for matches. We split by non-alphabetic characters
        # so 'first name', 'first_name' 'first-name', 'first.name', etc will all be split into
        # ['first', 'name'] and will be equivalent.
        user_input_lower = user_input.lower()
        user_tokens = set(re.split('[^a-zA-Z]', user_input_lower))

        # Find all API calls that contain all the tokens in the user input. If the user is looking for
        # 'observations', we want to match 'observations', 'observations/{id}', 'observations/{id}/details', etc.
        matches = []
        for call in all_calls:
            call_lower = call.lower()
            call_tokens = set(re.split('[^a-zA-Z]', call_lower))
            
            # Check for exact match on the first non-empty element of the call tokens
            # This is to avoid matching empty strings at the beginning of the call
            call_tokens = {token for token in call_tokens if token}
            user_tokens = {token for token in user_tokens if token}

            # If multiple matches and one of them covers the whole user input, choose that one.
            # For example, if the user calls 'observations', and there are multiple matches like
            # 'observations', 'observations/{id}', 'observations/{id}/details', etc., we choose
            # 'observations' as it covers the whole user input. This can be disabled by setting
            # strict_matching to False.
            if call_tokens == user_tokens and self.strict_matching:
                self.logger.info(f'\n*** Taking the exact match API call "{call}" ***\n')
                return call
            
            # Check if all user tokens are in the call tokens
            if user_tokens.issubset(call_tokens):
                matches.append(call)

        
        if not matches:
            print(f"No matches found for '{user_input}'")
            # Try to guess the API call looking for the closest match
            return self.guess_api_call(user_input, all_calls) 
        
        
        if len(matches) == 1:
            self.logger.info(f'\n*** Taking the API call "{matches[0]}" ***\n')
            return matches[0]

        
        # If multiple matches, prompt the user to choose
        print(f'Multiple matches found for {user_input}. Please choose one:')
        for i, match in enumerate(matches, 1):
            print(f"    {i}. {match}")
        
        while True:
            try:
                choice = int(input("Enter the number of your choice: "))
                if 1 <= choice <= len(matches):
                    return matches[choice - 1]
                else:
                    print("Invalid choice. Please try again.")
            except ValueError:
                print("Invalid input. Please enter a number.")



    def guess_api_call(self, user_input : str, all_calls : list[str]) -> str:

        # Use get_close_matches to find similar API calls
        matches = get_close_matches(user_input, all_calls, n=5, cutoff=0.2)
        
        if not matches:
            return None
        
        if len(matches) == 1:
            input_str = input(f'Did you mean "{matches[0]}"? (Y/N): ')
            if input_str.lower() == 'y':
                return matches[0]
            else:
                return None
        
        # If multiple matches, prompt the user to choose
        print("Did you mean one of the following? (If not, type 'n')")
        for i, match in enumerate(matches, 1):
            print(f"{i}. {match}")
        while True:
            choice = input()
            if choice.lower() == 'n':
                return None
            try:
                choice = int(choice)
                if 1 <= choice <= len(matches):
                    return matches[choice - 1]
                else:
                    print("Invalid choice. Please try again.")
            except ValueError:
                print("Invalid input. Please enter a number.")

    def handle_API_call(self, query: SafeDict) -> str:
        '''
        Function that takes a dictionary with the parameters for an API call and produces the
        necessary API call.
        Args:
            - query (SafeDict): A dictionary with the parameters for the API call. The keys are the
                                parameter names, and the values are the values for the parameters.
        Returns:
            - str: The full URL for the API call.
        '''
        # the dictionary is a mutable object, so we need to make a copy of it to avoid modifying the original
        parameters = SafeDict({key: value for key, value in query.items() if value is not None})

        # extract the API call from the dictionary. This way it won't be included in the url
        API_call = parameters.pop('API_call', None)

        if API_call is None:
            self.logger.error("Error: No API call found")
            return None

        # get parameter types for the API call
        param_types = self.get_parameter_types(API_call)

        # check that all parameters of type 'path' have been provided in the dictionary
        for param, param_info in param_types.items():
            if param_info['parameter_type'] == 'path' and param not in parameters:
                self.logger.critical(f"Missing parameter '{param}' for API call '{API_call}'")
                raise ValueError()

        # if the API call has anything between curly braces, replace it with the corresponding value
        pattern = r'\{([^}]+)\}' # pattern to match anything between curly braces
        path = re.sub(pattern, lambda m: str(parameters.get(m.group(1), m.group(0))), API_call)


        # remove all parameters of type path from the dictionary and empty values
        parameters = {
            param: value for param, value in parameters.items() 
            if param_types[param]['parameter_type'] != 'path' and value
            }


        # If there are still query parameters, add them to the URL
        if parameters:
            # Add the rest of the parameters to the URL
            path += '?'
            for key, value in parameters.items():
                # Convert all the values to string. If the value is a list, we join the elements with `%2C` instead of a comma.
                # For example acc=true&endemic=false&id=123%2C456%2C789
                if isinstance(value, list):
                    value = '%2C'.join([str(v) for v in value])
                elif not isinstance(value, type('')):
                    if isinstance(value, bool):
                        #if value is a boolean, convert it to a string and lowercase it
                        value = str(value).lower()
                    else:
                        value = str(value)

                path += f'{key}={value}&'

            # Remove the last '&' from the URL
            path = path[:-1]

        return self.base_url + path



    def make_request(self, parameters: SafeDict = None, user_function: Callable = None, variables: tuple = None, max_results: int = None, **kwargs) -> dict:
        """
        Function that takes a dictionary with the parameters for an API call, produces the
        necessary API call and makes a request with it. The function `func` is a user defined
        function to be applied to the response of the API call. If no function is provided, the
        function will return the response as is. It automatically handles pagination and authentication.

        Args:
            - parameters (SafeDict): A dictionary with the parameters for the API call. The keys are the
                                     parameter names, and the values are the values for the parameters.
            - user_function (Callable): A user-defined function to apply to the response of the API call.
            - variables (tuple): A tuple with the variables to pass to the user function. It can be any number of variables.
            - max_results (int): The maximum number of results to return. If the API call returns more
                                 results than the maximum, it will trim the results to the maximum.
            - kwargs: Additional keyword arguments to pass to the function, or the credentials for authentication.

        Returns:
            - dict: The response of the API call.
        """
        import inspect
        import requests
        import pickle
        import base64
        import getpass

        # if parameters is provided, convert them to regular dict so it can be handled by the server backend
        parameters = dict(parameters) if parameters is not None else {}

        all_results = []
        total_results = None

        # if we have parameters, we can construct an API call.
        if parameters:
            # first check if the API call requires authentication
            API_call = parameters.get('API_call')
            if self._check_auth_required(API_call):
                # check if the user has passed credentials. We accept any of the following keys:
                username = next((kwargs[k] for k in ['username', 'user', 'email', 'mail'] if k in kwargs), None)
                password = next((kwargs[k] for k in ['password', 'pass', 'secret'] if k in kwargs), None)
                self.authenticate(username, password)

                if not self.auth_token:
                    self.logger.error("Authentication token is not set or has expired. Please authenticate or set a valid API token.")
                    raise ValueError
                headers = {'Authorization': f'Bearer {self.auth_token}', 'Accept': 'application/json'}
            else:
                headers = {'Accept': 'application/json'}
            
            # if the parameters has no page key, we don't need to handle pagination and can make the API call directly
            if any(key not in parameters for key in ['per_page', 'page']):
                url = self.handle_API_call(parameters)
                try:
                    response = requests.get(url, headers=headers)
                    response.raise_for_status()
                    return response.json()
                except requests.exceptions.RequestException as e:
                    self.logger.error(f"Error making API call: {str(e)}")
                    self.logger.debug(f"Response status code: {response.status_code}\nResponse text: {response.text}\nResponse headers: {response.headers}\n")
                    if "unauthorized" in str(e).lower():
                        self.auth_token = None
                        self.auth_expiry = None
                        self.logger.error("The used token is outdated or invalid. You can (P)aste a new token, (A)uthenticate again or (I)gnore the error, (Q)uit the program.")
                        user_input = input("(P/A/I/Q): ").lower()
                        if user_input == 'p':
                            new_token = input("Paste the new token here: ")
                            self.set_api_token(new_token)
                            return self.make_request(parameters, user_function, variables, max_results, **kwargs)
                        elif user_input == 'a':
                            if not username or not password:
                                print("Please provide your credentials to authenticate. Press enter to skip, but this will only work if you accept browser authentication")
                                username = input("    👤 username: ")
                                password = getpass.getpass("    🔑 password: ")
                            self.authenticate(username, password)
                            return self.make_request(parameters, user_function, variables, max_results, **kwargs)
                        elif user_input == 'i':
                            return None
                        elif user_input == 'q':
                            exit(1)

                    return None

            # Ensure per_page is set to 200 if not specified
            parameters['per_page'] = parameters.get('per_page') if parameters.get('per_page') else 200
            # If the user didn't specify a page, default to 1
            page = parameters.get('page') if parameters.get('page') else 1

            while True:
                parameters['page'] = page
                url = self.handle_API_call(parameters)
                
                # Make the API call
                try:
                    response = requests.get(url, headers=headers)
                    response.raise_for_status()  # Raises an HTTPError for bad responses
                    data = response.json()
                    
                    if total_results is None:
                        total_results = data.get('total_results')
                        self.logger.info(f"Total results available: {total_results}")

                    if 'results' in data:
                        all_results.extend(data['results'])
                        self.logger.info(f"Retrieved {len(all_results)} out of {total_results} results.")
                        
                        if len(data['results']) < parameters['per_page'] or \
                        (max_results and len(all_results) >= max_results):
                            break  # No more results to fetch or reached max_results
                    else:
                        # If 'results' is not in the response, assume it's the complete data
                        all_results = data
                        break

                    page += 1

                except requests.exceptions.RequestException as e:
                    self.logger.error(f"Error making API call: {str(e)}")
                    break

            # Trim results if we've exceeded max_results
            if max_results and len(all_results) > max_results:
                all_results = all_results[:max_results]

            return {
                'total_results': total_results,
                'results': all_results
            }
        # if user_function is provided, assume it will make the API calls on the server
        elif user_function:
            # If there is a SafeDict object in the variables, convert it to a regular dictionary
            variables = tuple(dict(var) if isinstance(var, SafeDict) else var for var in variables) if variables is not None else None

            function_code = inspect.getsource(user_function)

            #replace the function name for `user_function`
            function_code = function_code.replace(user_function.__name__, 'user_function')

            # Encode the function, variables, and kwargs
            encoded_function = base64.b64encode(function_code.encode('utf-8')).decode('utf-8')
            encoded_variables = base64.b64encode(pickle.dumps(variables)).decode('utf-8')
            encoded_kwargs = base64.b64encode(pickle.dumps(kwargs)).decode('utf-8')

            # Prepare the payload
            payload = {
                'function': encoded_function,
                'variables': encoded_variables,
                'kwargs': encoded_kwargs,
            }

            response = requests.post(f'http://{self.server_ip}:{self.port}/{self.executable_endpoint}', json=payload, verify=False)

            try:
                result = response.json()
                #print(f"The result is: {result['result']}")
            except requests.exceptions.JSONDecodeError:
                print(f"Error: {response.text}")

            return result
        else:
            return None
