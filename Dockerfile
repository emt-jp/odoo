# Use Python 3.10 slim image as base
FROM python:3.10-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV ODOO_RC=/etc/odoo/odoo.conf

# Set work directory
WORKDIR /opt/odoo

# Install system dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        curl \
        git \
        libfreetype6-dev \
        libjpeg62-turbo-dev \
        liblcms2-dev \
        libopenjp2-7-dev \
        libtiff5-dev \
        libwebp-dev \
        libxml2-dev \
        libxslt1-dev \
        nodejs \
        npm \
        postgresql-client \
        libpq-dev \
        python3-dev \
        python3-pip \
        python3-venv \
        tzdata \
        wget \
        zlib1g-dev \
        libldap2-dev \
        libsasl2-dev \
        libssl-dev \
        fontconfig \
        libxrender1 \
        xfonts-75dpi \
        xfonts-base \
    && rm -rf /var/lib/apt/lists/*

# Install wkhtmltopdf (includes wkhtmltoimage)
RUN wget -q https://github.com/wkhtmltopdf/packaging/releases/download/0.12.6.1-3/wkhtmltox_0.12.6.1-3.bookworm_amd64.deb -O /tmp/wkhtmltox.deb \
    && apt-get update \
    && apt-get install -y --no-install-recommends /tmp/wkhtmltox.deb \
    && rm -rf /tmp/wkhtmltox.deb /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements/requirements-basic.txt /opt/odoo/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Install Odoo
COPY . /opt/odoo/

# Create odoo user
RUN adduser --system --home=/opt/odoo --group odoo

# Create necessary directories
RUN mkdir -p /opt/odoo/var/run \
    && mkdir -p /opt/odoo/var/log \
    && mkdir -p /opt/odoo/var/lib \
    && mkdir -p /opt/odoo/var/backups \
    && mkdir -p /etc/odoo

# Set ownership
RUN chown -R odoo:odoo /opt/odoo \
    && chown -R odoo:odoo /etc/odoo

# Switch to odoo user
USER odoo

# Expose port
EXPOSE 8069

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8069/web/health || exit 1

# Default command
CMD ["python3", "odoo-bin", "-c", "/etc/odoo/odoo.conf"]
