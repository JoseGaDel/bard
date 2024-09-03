from flask import Flask, request, jsonify
import pickle
import base64
from bard import APIParser, SafeDict

app = Flask(__name__)

@app.route('/execute', methods=['POST'])
def execute_function():
    # Receive the data
    data = request.get_json()
    
    # Decode and deserialize the function
    function_code = base64.b64decode(data['function']).decode('utf-8')
    exec(function_code, globals())
    
    # Deserialize the variables
    variables = pickle.loads(base64.b64decode(data['variables']))
    
    # Deserialize the kwargs
    kwargs = pickle.loads(base64.b64decode(data['kwargs']))
    
    # Apply the function to the variables and kwargs
    result = user_function(*variables, **kwargs)
    
    return jsonify(result=result)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8001)


"""
Deploy with:

docker-compose up --build (-d to run in detached mode)

or with:

docker build -t minka-server . && docker run -p 8001:8001 minka-server
"""