FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash app \
    && chown -R app:app /app
USER app

# Copy requirements first for better caching
COPY --chown=app:app requirements.txt .

# Install Python dependencies
RUN pip install --user --no-cache-dir -r requirements.txt

# Add user's local bin to PATH
ENV PATH="/home/app/.local/bin:${PATH}"

# Copy application code
COPY --chown=app:app . .

# Expose port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:5000/health || exit 1

# Set environment variables for production
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Run the application with uvicorn directly for production
CMD ["uvicorn", "strand_agent_api:app", "--host", "0.0.0.0", "--port", "5000", "--workers", "1"]