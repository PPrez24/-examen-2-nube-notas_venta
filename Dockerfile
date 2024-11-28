# Base image
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Copy project files
COPY . .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Add build arguments for environment variables
ARG DB_HOST
ARG DB_USER
ARG DB_PASSWORD
ARG DB_NAME
ARG S3_BUCKET
ARG AWS_REGION

# Set environment variables
ENV DB_HOST=$DB_HOST
ENV DB_USER=$DB_USER
ENV DB_PASSWORD=$DB_PASSWORD
ENV DB_NAME=$DB_NAME
ENV S3_BUCKET=$S3_BUCKET
ENV AWS_REGION=$AWS_REGION

# Expose the port
EXPOSE 5001

# Start the application
CMD ["python", "app.py"]
