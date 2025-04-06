FROM python:3.11-slim AS builder

# Install Rust and development dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Install Rust
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
ENV PATH="/root/.cargo/bin:${PATH}"

# Create app directory
WORKDIR /app

# Copy Rust and Python code
COPY src/rust /app/src/rust
COPY src/python /app/src/python
COPY pyproject.toml /app/
COPY README.md /app/

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir maturin

# Build the Rust extension
RUN cd /app && maturin build --release

# Install the wheel
RUN pip install --no-cache-dir /app/target/wheels/*.whl

# Now create a smaller runtime image
FROM python:3.11-slim

WORKDIR /app

# Copy Python code
COPY src/python /app/src/python
COPY pyproject.toml /app/
COPY README.md /app/

# Copy the built wheel from the builder stage
COPY --from=builder /app/target/wheels/*.whl /app/

# Install Python dependencies and the wheel
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir \
    fastapi>=0.104.0 \
    uvicorn[standard]>=0.23.2 \
    pydantic>=2.4.2 \
    numpy>=1.24.0 \
    pandas>=2.1.0 \
    matplotlib>=3.7.0 \
    plotly>=5.17.0 && \
    pip install --no-cache-dir /app/*.whl

# Add application to Python path
ENV PYTHONPATH=/app

# Expose API port
EXPOSE 8000

# Default command: run the API server
CMD ["python", "-m", "src.python.cli", "api", "--host", "0.0.0.0", "--port", "8000"] 