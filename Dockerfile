# 1. Base Image Selection
# We use the official Python 3.11 slim image. "slim" is preferred for production
# because it contains the minimal packages needed to run Python, keeping the image size small.
FROM python:3.11-slim

# 2. Working Directory Setup
# This sets the "base camp" inside the container. All following commands (COPY, RUN, etc.)
# will be executed relative to this folder.
WORKDIR /app

# 3. Environment Variables
# PYTHONUNBUFFERED=1: Forces Python to flush its output to the terminal immediately.
# This is crucial for seeing logs in real-time when running in Docker.
# PYTHONDONTWRITEBYTECODE=1: Prevents Python from creating .pyc files, which aren't needed in a container.
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# 4. System Dependency Installation
# Our project uses 'librosa' and 'transformers', which often require underlying C libraries.
# - build-essential: Provides compilers for C-based Python extensions.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# 5. Dependency Management (Optimization)
COPY requirements.txt .

# 6. Cleaning and Installing Requirements
# Since this project was developed on Windows, the requirements.txt contains windows-specific packages like 'pywin32' which will fail on a Linux container.
# Use 'sed' to remove those lines and then install the rest.
RUN sed -i '/pywin32/d; /pypiwin32/d; /comtypes/d; s/+cu[0-9]*//g' requirements.txt && \
    pip install --no-cache-dir -r requirements.txt

# 7. Copy Application Code
COPY . .

# 8. Directory Preparation
# The application logs data to a './logs/' folder. We ensure it exists here.
RUN mkdir -p logs

# 9. Port Exposure
EXPOSE 8000

# 10. Default Command
CMD ["uvicorn", "api.app:app", "--host", "0.0.0.0", "--port", "8000"]
