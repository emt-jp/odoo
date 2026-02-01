# Odoo Docker Image for Cloud Run
FROM odoo:17.0

# Install additional dependencies
USER root
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

# Install Google Cloud Storage support
RUN pip3 install --no-cache-dir google-cloud-storage

# Copy custom addons
COPY --chown=odoo:odoo addons /mnt/extra-addons

# Copy configuration
COPY --chown=odoo:odoo config/odoo.conf /etc/odoo/odoo.conf

USER odoo

# Expose Odoo port
EXPOSE 8069

# Health check for Cloud Run
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8069/web/health || exit 1

# Start Odoo
CMD ["odoo", "-c", "/etc/odoo/odoo.conf"]
