# Odoo 17 Docker Image for Google Cloud Run
FROM python:3.10-slim

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV ODOO_RC=/etc/odoo/odoo.conf

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
        node-less \
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
        fonts-noto-cjk \
    && rm -rf /var/lib/apt/lists/*

# Install rtlcss for CSS processing
RUN npm install -g rtlcss

# Install wkhtmltopdf
RUN wget -q https://github.com/wkhtmltopdf/packaging/releases/download/0.12.6.1-3/wkhtmltox_0.12.6.1-3.bookworm_amd64.deb -O /tmp/wkhtmltox.deb \
    && apt-get update \
    && apt-get install -y --no-install-recommends /tmp/wkhtmltox.deb \
    && rm -rf /tmp/wkhtmltox.deb /var/lib/apt/lists/*

# Copy requirements and install Python packages
COPY requirements/requirements-cloudrun.txt /opt/odoo/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy Odoo source code
COPY . /opt/odoo/

# Create odoo user and directories
RUN adduser --system --home=/opt/odoo --group odoo
RUN mkdir -p /opt/odoo/var/run \
    && mkdir -p /opt/odoo/var/log \
    && mkdir -p /opt/odoo/var/lib \
    && mkdir -p /opt/odoo/var/backups \
    && mkdir -p /etc/odoo \
    && mkdir -p /var/lib/odoo

# Copy entrypoint script
COPY entrypoint.sh /opt/odoo/entrypoint.sh
RUN chmod +x /opt/odoo/entrypoint.sh

# Set permissions
RUN chown -R odoo:odoo /opt/odoo \
    && chown -R odoo:odoo /etc/odoo \
    && chown -R odoo:odoo /var/lib/odoo

USER odoo

EXPOSE 8069

HEALTHCHECK --interval=30s --timeout=10s --start-period=300s --retries=5 \
    CMD curl -f http://localhost:8069/web/health || exit 1

ENTRYPOINT ["/opt/odoo/entrypoint.sh"]
CMD []
