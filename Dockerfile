FROM python:3.12-slim

WORKDIR /app

COPY . /app

RUN pip install --upgrade pip

# Install the bard package
RUN pip install -e .

# Install server-specific requirements
RUN pip install --no-cache-dir -r server_requirements.txt

EXPOSE 8001

ENV FLASK_APP=server/server.py

CMD ["python", "server/server.py"]

