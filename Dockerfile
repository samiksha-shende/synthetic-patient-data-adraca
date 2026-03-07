FROM python:3.12-slim

# Set environment variables for security and performance
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Create a non-root user
RUN useradd -m -r adraca_user

# Set working directory
WORKDIR /app

# Copy dependency files
COPY requirements.txt /app/
COPY wheels/ /app/wheels/

# Install dependencies strictly offline from local wheels
RUN pip install --no-cache-dir --no-index --find-links=/app/wheels -r requirements.txt

# Copy source code
COPY src/ /app/src/

# Create necessary directories for runtime
RUN mkdir -p /app/data/input /app/data/output /app/reports /app/models

# Clean up wheels to save space and speed up chown
RUN rm -rf /app/wheels

# Change ownership of the runtime necessary directories
RUN chown -R adraca_user:adraca_user /app

# Switch to the non-root user for execution
USER adraca_user

# Expose Streamlit port
EXPOSE 8501

# Run the Streamlit frontend
CMD ["streamlit", "run", "src/app.py", "--server.port=8501", "--server.address=0.0.0.0"]
