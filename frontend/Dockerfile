FROM node:20-bullseye-slim

WORKDIR /app

# Copy package files first (for caching)
COPY package.json package-lock.json* ./

# Remove any existing node_modules / lockfile and install dependencies
RUN rm -rf node_modules package-lock.json && npm install

# Copy the rest of your app (not strictly necessary for dev if using volumes)
COPY . .

EXPOSE 5173

# Run dev server, but install dependencies on container start if needed
CMD ["sh", "-c", "npm install && npm run dev -- --host 0.0.0.0"]
