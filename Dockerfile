# Use the official Azure Functions Python image as the base image  
FROM mcr.microsoft.com/azure-functions/python:4-python3.11

# Set the working directory for the function app  
WORKDIR /home/site/wwwroot  
  
# Copy requirements.txt to the container  
COPY requirements.txt .  
  
# Install system-level dependencies (including ffmpeg) and Python packages  
RUN apt-get update && \  
    # apt-get install -y --no-install-recommends ffmpeg && \  
    apt-get clean && \  
    rm -rf /var/lib/apt/lists/* && \  
    pip install --no-cache-dir -r requirements.txt  
  
# Copy all the function app code to the container  
COPY . .  
  
# Set the entry point for the Azure Functions runtime  
ENV AzureWebJobsScriptRoot=/home/site/wwwroot \  
    AzureFunctionsJobHost__Logging__Console__IsEnabled=true  
  
# CMD ["python", "-m", "azure_functions_worker"]  