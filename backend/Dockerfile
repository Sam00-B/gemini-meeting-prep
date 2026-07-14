# 1. Base Image: Use the official lightweight Python image
FROM python:3.12-slim

# 2. Environment Variables: Optimize Python for containerization
# Prevents Python from writing .pyc files to disk
ENV PYTHONDONTWRITEBYTECODE=1
# Prevents Python from buffering stdout/stderr (ensures logs appear instantly)
ENV PYTHONUNBUFFERED=1

# 3. Work Directory: Set the context for all subsequent commands
WORKDIR /app

# 4. Dependency Caching: Copy ONLY the requirements file first
# This is a crucial caching strategy. If your code changes but your dependencies 
# don't, Docker skips this heavy installation step on the next build.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 5. Application Code: Copy the rest of your FastAPI app
COPY . .

# 6. Port Exposure: Document the port the container will listen on
EXPOSE 8000

# 7. Execution: The command to spin up the ASGI server
# We bind to 0.0.0.0 so Uvicorn accepts traffic from outside the container network
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]