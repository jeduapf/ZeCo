# ---------- Stage 1: Test Stage ----------
FROM python:3.11-slim AS test-stage

WORKDIR /backend

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install dependencies
COPY dev-requirements.txt .
RUN pip install --no-cache-dir -r dev-requirements.txt

# Copy entire project (includes tests/)
COPY . .

# Run your tests (pytest will automatically use tests/conftest.py)
RUN pytest --disable-warnings --maxfail=1


# ---------- Stage 2: Production Stage ----------
FROM python:3.11-slim AS final

WORKDIR /backend

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install only production dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy only the backend code, NOT the tests
COPY . .


EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
