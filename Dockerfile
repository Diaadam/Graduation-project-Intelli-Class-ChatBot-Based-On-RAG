# Use a slim Python base image
FROM graduationproject.azurecr.io/chatbot-app:v3.0
# Set environment variables for Python

# Set work directory inside the container
WORKDIR /app
COPY src ./src
