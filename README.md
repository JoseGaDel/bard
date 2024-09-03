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

This module has been designed considering the server-side would implement an execute endpoint where users can pass functions that will perform the API calls. The directory [server](server) contains a minimal Flask application to give a rough idea of how this could be implemented. This is by no means a production-ready application, but it allows us to test the module in a server environment. To run the server, simply clone the repository and deploy using Docker:

```bash
docker-compose up --build
```

During development we used a SSH to connect to the server and we needed to use a specific port to connect to the server. You will need to adjust this in the configuration, as well as the `APIParser.server_ip` variable in the module, which defaults to `127.0.0.1` (localhost).