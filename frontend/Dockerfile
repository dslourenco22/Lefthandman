# --- Build stage ---
FROM node:20-alpine AS build

WORKDIR /app

# Copy package.json and package-lock.json (if it exists)
# The wildcard (*) ensures the build won't fail if package-lock.json is missing
COPY package.json package-lock.json* ./

# If you have committed a package-lock.json to Git, change "npm install" to "npm ci" 
# for faster, 100% reproducible builds. Otherwise, npm install works fine.
RUN npm install

# Copy the rest of the frontend source code
COPY . .

# Build the static assets (creates the /app/dist folder)
RUN npm run build

# --- Serve stage ---
FROM nginx:1.27-alpine

# Copy the compiled static HTML/JS/CSS from the build stage
COPY --from=build /app/dist /usr/share/nginx/html

# Copy your custom Nginx configuration (handling SPA routing and /api proxying)
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]