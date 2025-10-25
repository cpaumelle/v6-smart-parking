# Stage 1: Build the React application
FROM node:18-alpine AS builder

WORKDIR /app

# Accept build arguments
ARG VITE_API_URL=https://api.verdegris.eu

# Copy package files
COPY package*.json ./

# Install ALL dependencies (including devDependencies for build)
RUN npm ci

# Copy source code
COPY . .

# Remove .env files to ensure ENV variables take precedence
RUN rm -f .env .env.local .env.production .env.production.local

# Set environment variables for Vite build
ENV VITE_API_URL=${VITE_API_URL}
ENV VITE_APP_NAME="Smart Parking V6"
ENV VITE_APP_VERSION="6.0.0"

# Build the application
RUN npm run build

# Stage 2: Serve with Nginx
FROM nginx:alpine

# Copy custom nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy built assets from builder stage
COPY --from=builder /app/dist /usr/share/nginx/html

# Add health check script
RUN echo -e '#!/bin/sh\nwget --no-verbose --tries=1 --spider http://localhost/ || exit 1' > /healthcheck.sh && \
    chmod +x /healthcheck.sh

# Expose port 80
EXPOSE 80

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD ["/healthcheck.sh"]

# Start nginx
CMD ["nginx", "-g", "daemon off;"]
