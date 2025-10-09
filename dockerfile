# Use a Debian-based Python image to leverage manylinux wheels
FROM python:3.11-slim
ARG BUILDKIT_INLINE_CACHE=1

# Set env for clearer logs
ENV PYTHONUNBUFFERED=1

# Set the working directory
WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copy the Flask app
COPY . .

# Add a user called "appuser"
RUN adduser -D appuser

# Use that user instead of root
USER appuser

# Expose the port Flask runs on
EXPOSE 8080

# Run the Flask app
CMD ["python", "app.py"]
