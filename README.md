# BARD (Biodiversity API Retrieval & Data-processing)

BARD is a comprehensive Python framework designed to simplify and enhance interactions with biodiversity databases, specifically tailored for the MINKA platform but adaptable to other similar APIs. This tool bridges the gap between complex API structures and end-users, enabling efficient data retrieval and processing for biodiversity research and citizen science initiatives. Developed with the collaboration of the [MINKA project](https://minka-sdg.org/) as part of a master's thesis in computational science and mathematics from URV & UOC.

## Key Features:

- **Automated API Interaction**: Seamlessly handles API calls, authentication, and response parsing.
- **Flexible Query Building**: Implements security mechanisms to ensure correct queries and allows for lousy input so the user does not have to adhere to a strict format.
- **Spatial Data Processing**: Includes tools for geographical data analysis and visualization.
- **Temporal Data Handling**: Facilitates time-based data retrieval and analysis.
- **Data Transformation**: Offers some JSON data manipulation and filtering capabilities.
- **Extensible Architecture**: Designed with modularity in mind for easy expansion and customization.

BARD aims to democratize access to biodiversity data, empowering researchers, citizen scientists, and conservationists to contribute more effectively to global biodiversity monitoring and research efforts.


## Getting Started

### The user

To run this module locally as a user, clone this repository and install the required dependencies:

```bash
pip install -e .
```

You can head to the [examples](examples) folder to see some basic usage of the module.

### The server

This module has been designed considering the server-side would implement an execute endpoint where users can pass functions that will perform the API calls. The directory [server](server) contains a minimal Flask application to give a rough idea of how this could be implemented. This is by no means a production-ready application, but it allows us to test the module in a server environment. For the moment, the only feature that will not work if the server is not running is when we pass a function to `APIParser.make_request()`, but we can always run that function locally, or run the server on your local host for testing. To run the server, simply clone the repository and deploy using Docker:

```bash
docker-compose up --build
```

During development we used a SSH tunnel from local port 8000 to port 8001 on the remote server because we had certain port requirements. You may need to adjust this in the configuration, as well as the `APIParser.server_ip` variable in the module, which defaults to `127.0.0.1` (localhost) because it was being tested using the SSH tunnel. If you need to change the port on which the server runs, you'll need to update several components of the setup. First, update the port mapping in the [docker-compose.yml](docker-compose.yml) file:

```yaml
version: '3'
services:
  minka-server:
    build: .
    ports:
      - "<new-host-port>:<new-container-port>"
    volumes:
      - ./server:/app/server
```
Replace `<new-host-port>` with the port you want to expose on your host machine, and `<new-container-port>` with the port your Flask app will listen on inside the container. The [Dockerfile](Dockerfile) doesn't need to be changed unless you want to modify the `EXPOSE` instruction for documentation purposes. It does not have any operational effect on the behavior of the container, but it is best to make it match the actual configuration so it doesn't cause confusion. Update the port in your Flask application in [server/server.py](server/server.py):

```python
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=<new-container-port>)
```

and initialize with `APIParser(server_ip = "ip_or_domain", server_port = <port-listening-for-connections>)`. This way you can adjust ports and directions to your setup.


## Adjust the configuration to your specific needs

This project has been developed with the MINKA API in mind, but it can be easily adapted to other APIs. Here is a list of the main configuration options that can be adjusted to your specific needs:

### 1. API URL and Documentation URL
Set custom URLs during initialization to your desired API. You can even have two coexisting instances to switch between APIs easily.

```python
parser1 = APIParser(api_url="https://api.inaturalist.org/v1", instance="parser1")
parser2 = APIParser(api_url="https://api.minka-sdg.org/v1" , instance="parser2")
```

### 2. Verbosity Levels
Set the verbosity level (0-4) to control logging:

```python
parser.set_verbosity(2)

# Or set it during initialization
parser = APIParser(verbosity=2)
```

### 3. Caching
Control caching of API specifications and tokens:
```python
parser.cache_location = "custom_spec.json"
parser.token_lifetime = 7200  # Set token lifetime in seconds
```

### 4. Authentication

Set API token manually:
```python
parser.set_api_token("your_api_token", expires_in=3600)
```
Use browser-based authentication:
```python
parser.authenticate(username="user", password="pass")
```

Configure headless mode for browser authentication:
```python
parser.headless = True
```

### 5. Cookie Handling
Enable or disable cookie-based authentication:
```python
parser.use_cookies = True
parser.cookie_file = 'custom_cookies.pkl'
```

Cookies are intended to speed up the authentication process by storing the session cookies in a file. This is particularly useful when the API requires a browser-based login. When testing with MINKA, it looked like the server forces revalidation each time the browser is closed, so the cookies are not very useful in this case. This is why it is disable by default, but it can be enabled if your API supports it.

### 6. Strict Matching
Control how API calls are matched:
```python
parser = APIParser(strict_matching=False)
```
### 7. Server Configuration
Set the server IP and port:

```python
parser.server_ip = "ip_or_domain"
parser.server_port = 5000
server.executable_endpoint = "execute"
```
