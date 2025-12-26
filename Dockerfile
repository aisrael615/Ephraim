# =========================================
# Dockerfile
# =========================================

# Use official Python 3.13 slim image
FROM python:3.13-slim

# -----------------------------------------
# Environment settings
# -----------------------------------------
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# -----------------------------------------
# Set working directory inside container
# -----------------------------------------
WORKDIR /app/agent

# -----------------------------------------
# Install dependencies
# -----------------------------------------
# Copy only requirements first for caching
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r /app/requirements.txt

# -----------------------------------------
# Copy the agent folder contents into WORKDIR
# -----------------------------------------
COPY agent/ ./

# -----------------------------------------
# Default command to run your agent
# -----------------------------------------
CMD ["python", "ephraim.py"]
