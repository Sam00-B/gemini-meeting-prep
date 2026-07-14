# STAGE 1: Build and Test
FROM node:22 AS builder

WORKDIR /app

# Install dependencies first (leverages Docker cache)
COPY package.json ./
RUN npm install

# Copy the rest of the application
COPY . .

# Run the automated tests. If tests fail, the Docker build stops here!
RUN npm run test -- --run

# Compile the application for production
RUN npm run build

# STAGE 2: Production Server
FROM nginx:alpine

# Copy the compiled output from Stage 1 into the Nginx server directory
COPY --from=builder /app/dist /usr/share/nginx/html

# Expose port 80 for web traffic
EXPOSE 80

# Start Nginx
CMD ["nginx", "-g", "daemon off;"]