#!/bin/bash
# Odoo Security Monitor
# Checks for security events and sends email alerts with HTML tables

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_FILE="$SCRIPT_DIR/monitor.conf"
STATE_DIR="$SCRIPT_DIR/state"
LOG_FILE="$SCRIPT_DIR/monitor.log"
COMPOSE_DIR="/home/as/ws/odoo"

# Load configuration
if [[ -f "$CONFIG_FILE" ]]; then
    source "$CONFIG_FILE"
else
    echo "ERROR: Config file not found: $CONFIG_FILE"
    exit 1
fi

# Create state directory
mkdir -p "$STATE_DIR"

# Logging function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Send HTML email alert
send_alert() {
    local subject="$1"
    local alert_type="$2"
    local alert_color="$3"
    local alert_details="$4"

    if [[ "$EMAIL_ENABLED" != "true" ]]; then
        log "Email disabled, would send: $subject"
        return
    fi

    # Collect system data
    local CURRENT_USER=$(whoami)
    local HOSTNAME_FULL=$(hostname -f 2>/dev/null || hostname)
    local PUBLIC_IP=$(curl -s --max-time 5 ifconfig.me 2>/dev/null || echo "Unable to fetch")
    local PRIVATE_IP=$(hostname -I 2>/dev/null | awk '{print $1}' || echo "Unknown")
    local UPTIME=$(uptime -p 2>/dev/null || uptime | awk -F'up ' '{print $2}' | awk -F',' '{print $1}')
    local LOAD_AVG=$(uptime | awk -F'load average:' '{print $2}' | xargs)
    local MEM_USED=$(free -h 2>/dev/null | awk '/^Mem:/ {print $3}')
    local MEM_TOTAL=$(free -h 2>/dev/null | awk '/^Mem:/ {print $2}')
    local MEM_AVAIL=$(free -h 2>/dev/null | awk '/^Mem:/ {print $7}')
    local DISK_USED=$(df -h / 2>/dev/null | awk 'NR==2 {print $3}')
    local DISK_TOTAL=$(df -h / 2>/dev/null | awk 'NR==2 {print $2}')
    local DISK_PERC=$(df -h / 2>/dev/null | awk 'NR==2 {print $5}')
    local KERNEL=$(uname -r)
    local OS=$(cat /etc/os-release 2>/dev/null | grep "^PRETTY_NAME" | cut -d'"' -f2 || uname -s)
    local DOCKER_VERSION=$(docker --version 2>/dev/null | awk '{print $3}' | tr -d ',' || echo "Unknown")
    local TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S %Z')

    # Get container data as JSON-like format for Python
    local CONTAINER_DATA=$(cd "$COMPOSE_DIR" && docker compose ps --format "{{.Name}}|{{.Status}}|{{.Ports}}" 2>/dev/null | head -10)
    local CONTAINER_STATS=$(docker stats --no-stream --format "{{.Name}}|{{.CPUPerc}}|{{.MemUsage}}|{{.NetIO}}" 2>/dev/null | head -10)
    local DISK_DATA=$(df -h 2>/dev/null | tail -n +2 | head -10)
    local DOCKER_DISK=$(docker system df 2>/dev/null | tail -n +2 | head -5)

    # Use Python to send HTML email
    python3 << PYEOF
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Data from bash
alert_type = """$alert_type"""
alert_color = """$alert_color"""
alert_details = """$alert_details"""
subject = """$subject"""

system_data = {
    "timestamp": """$TIMESTAMP""",
    "hostname": """$HOSTNAME_FULL""",
    "user": """$CURRENT_USER""",
    "os": """$OS""",
    "kernel": """$KERNEL""",
    "docker": """$DOCKER_VERSION""",
    "public_ip": """$PUBLIC_IP""",
    "private_ip": """$PRIVATE_IP""",
    "uptime": """$UPTIME""",
    "load": """$LOAD_AVG""",
    "mem_used": """$MEM_USED""",
    "mem_total": """$MEM_TOTAL""",
    "mem_avail": """$MEM_AVAIL""",
    "disk_used": """$DISK_USED""",
    "disk_total": """$DISK_TOTAL""",
    "disk_perc": """$DISK_PERC""",
}

container_data = """$CONTAINER_DATA"""
container_stats = """$CONTAINER_STATS"""
disk_data = """$DISK_DATA"""
docker_disk = """$DOCKER_DISK"""

# Build container tables
container_rows = ""
for line in container_data.strip().split('\n'):
    if line:
        parts = line.split('|')
        if len(parts) >= 3:
            name, status, ports = parts[0], parts[1], parts[2] if len(parts) > 2 else ""
            status_color = "#28a745" if "Up" in status and "healthy" in status else "#ffc107" if "Up" in status else "#dc3545"
            container_rows += f'''<tr>
                <td style="padding: 8px; border: 1px solid #ddd;">{name}</td>
                <td style="padding: 8px; border: 1px solid #ddd; color: {status_color}; font-weight: bold;">{status}</td>
                <td style="padding: 8px; border: 1px solid #ddd; font-size: 11px;">{ports[:50]}...</td>
            </tr>'''

stats_rows = ""
for line in container_stats.strip().split('\n'):
    if line:
        parts = line.split('|')
        if len(parts) >= 4:
            name, cpu, mem, net = parts[0], parts[1], parts[2], parts[3]
            cpu_val = float(cpu.replace('%', '')) if cpu.replace('%', '').replace('.', '').isdigit() else 0
            cpu_color = "#dc3545" if cpu_val > 100 else "#ffc107" if cpu_val > 50 else "#28a745"
            stats_rows += f'''<tr>
                <td style="padding: 8px; border: 1px solid #ddd;">{name}</td>
                <td style="padding: 8px; border: 1px solid #ddd; color: {cpu_color}; font-weight: bold;">{cpu}</td>
                <td style="padding: 8px; border: 1px solid #ddd;">{mem}</td>
                <td style="padding: 8px; border: 1px solid #ddd;">{net}</td>
            </tr>'''

disk_rows = ""
for line in disk_data.strip().split('\n'):
    if line:
        parts = line.split()
        if len(parts) >= 6:
            fs, size, used, avail, perc, mount = parts[0], parts[1], parts[2], parts[3], parts[4], parts[5]
            perc_val = int(perc.replace('%', '')) if perc.replace('%', '').isdigit() else 0
            perc_color = "#dc3545" if perc_val > 85 else "#ffc107" if perc_val > 70 else "#28a745"
            disk_rows += f'''<tr>
                <td style="padding: 8px; border: 1px solid #ddd;">{mount}</td>
                <td style="padding: 8px; border: 1px solid #ddd;">{fs[:20]}</td>
                <td style="padding: 8px; border: 1px solid #ddd;">{size}</td>
                <td style="padding: 8px; border: 1px solid #ddd;">{used}</td>
                <td style="padding: 8px; border: 1px solid #ddd;">{avail}</td>
                <td style="padding: 8px; border: 1px solid #ddd; color: {perc_color}; font-weight: bold;">{perc}</td>
            </tr>'''

# Format alert details for HTML
alert_details_html = alert_details.replace('\n', '<br>').replace(' ', '&nbsp;') if alert_details else ""

html = f'''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="font-family: 'Segoe UI', Arial, sans-serif; margin: 0; padding: 20px; background-color: #f5f5f5;">
    <div style="max-width: 800px; margin: 0 auto; background-color: #ffffff; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">

        <!-- Header -->
        <div style="background-color: {alert_color}; color: white; padding: 20px; text-align: center;">
            <h1 style="margin: 0; font-size: 24px;">{alert_type} ALERT</h1>
            <p style="margin: 10px 0 0 0; opacity: 0.9;">{system_data['hostname']}</p>
        </div>

        <!-- Alert Details -->
        <div style="padding: 20px; background-color: #fff3cd; border-left: 4px solid {alert_color};">
            <h3 style="margin: 0 0 10px 0; color: #856404;">Alert Details</h3>
            <div style="font-family: monospace; font-size: 12px; white-space: pre-wrap; color: #333;">{alert_details_html}</div>
        </div>

        <!-- System Information -->
        <div style="padding: 20px;">
            <h2 style="color: #333; border-bottom: 2px solid {alert_color}; padding-bottom: 10px; margin-top: 0;">
                System Information
            </h2>
            <table style="width: 100%; border-collapse: collapse; margin-bottom: 20px;">
                <tr style="background-color: #f8f9fa;">
                    <td style="padding: 12px; border: 1px solid #ddd; font-weight: bold; width: 30%;">Timestamp</td>
                    <td style="padding: 12px; border: 1px solid #ddd;">{system_data['timestamp']}</td>
                </tr>
                <tr>
                    <td style="padding: 12px; border: 1px solid #ddd; font-weight: bold;">Hostname</td>
                    <td style="padding: 12px; border: 1px solid #ddd;">{system_data['hostname']}</td>
                </tr>
                <tr style="background-color: #f8f9fa;">
                    <td style="padding: 12px; border: 1px solid #ddd; font-weight: bold;">User</td>
                    <td style="padding: 12px; border: 1px solid #ddd;">{system_data['user']}</td>
                </tr>
                <tr>
                    <td style="padding: 12px; border: 1px solid #ddd; font-weight: bold;">Operating System</td>
                    <td style="padding: 12px; border: 1px solid #ddd;">{system_data['os']}</td>
                </tr>
                <tr style="background-color: #f8f9fa;">
                    <td style="padding: 12px; border: 1px solid #ddd; font-weight: bold;">Kernel</td>
                    <td style="padding: 12px; border: 1px solid #ddd;">{system_data['kernel']}</td>
                </tr>
                <tr>
                    <td style="padding: 12px; border: 1px solid #ddd; font-weight: bold;">Docker Version</td>
                    <td style="padding: 12px; border: 1px solid #ddd;">{system_data['docker']}</td>
                </tr>
            </table>

            <!-- Network Information -->
            <h2 style="color: #333; border-bottom: 2px solid {alert_color}; padding-bottom: 10px;">
                Network Information
            </h2>
            <table style="width: 100%; border-collapse: collapse; margin-bottom: 20px;">
                <tr style="background-color: #f8f9fa;">
                    <td style="padding: 12px; border: 1px solid #ddd; font-weight: bold; width: 30%;">Public IP</td>
                    <td style="padding: 12px; border: 1px solid #ddd; font-family: monospace;">{system_data['public_ip']}</td>
                </tr>
                <tr>
                    <td style="padding: 12px; border: 1px solid #ddd; font-weight: bold;">Private IP</td>
                    <td style="padding: 12px; border: 1px solid #ddd; font-family: monospace;">{system_data['private_ip']}</td>
                </tr>
            </table>

            <!-- Resource Usage -->
            <h2 style="color: #333; border-bottom: 2px solid {alert_color}; padding-bottom: 10px;">
                Resource Usage
            </h2>
            <table style="width: 100%; border-collapse: collapse; margin-bottom: 20px;">
                <tr style="background-color: #f8f9fa;">
                    <td style="padding: 12px; border: 1px solid #ddd; font-weight: bold; width: 30%;">Uptime</td>
                    <td style="padding: 12px; border: 1px solid #ddd;">{system_data['uptime']}</td>
                </tr>
                <tr>
                    <td style="padding: 12px; border: 1px solid #ddd; font-weight: bold;">Load Average</td>
                    <td style="padding: 12px; border: 1px solid #ddd;">{system_data['load']}</td>
                </tr>
                <tr style="background-color: #f8f9fa;">
                    <td style="padding: 12px; border: 1px solid #ddd; font-weight: bold;">Memory</td>
                    <td style="padding: 12px; border: 1px solid #ddd;">
                        Used: <strong>{system_data['mem_used']}</strong> /
                        Total: {system_data['mem_total']}
                        (Available: {system_data['mem_avail']})
                    </td>
                </tr>
                <tr>
                    <td style="padding: 12px; border: 1px solid #ddd; font-weight: bold;">Root Disk (/)</td>
                    <td style="padding: 12px; border: 1px solid #ddd;">
                        Used: <strong>{system_data['disk_used']}</strong> /
                        Total: {system_data['disk_total']}
                        (<strong>{system_data['disk_perc']}</strong>)
                    </td>
                </tr>
            </table>

            <!-- Container Status -->
            <h2 style="color: #333; border-bottom: 2px solid {alert_color}; padding-bottom: 10px;">
                Container Status
            </h2>
            <table style="width: 100%; border-collapse: collapse; margin-bottom: 20px;">
                <thead>
                    <tr style="background-color: #343a40; color: white;">
                        <th style="padding: 12px; border: 1px solid #ddd; text-align: left;">Container</th>
                        <th style="padding: 12px; border: 1px solid #ddd; text-align: left;">Status</th>
                        <th style="padding: 12px; border: 1px solid #ddd; text-align: left;">Ports</th>
                    </tr>
                </thead>
                <tbody>
                    {container_rows if container_rows else '<tr><td colspan="3" style="padding: 12px; text-align: center;">No containers found</td></tr>'}
                </tbody>
            </table>

            <!-- Container Resources -->
            <h2 style="color: #333; border-bottom: 2px solid {alert_color}; padding-bottom: 10px;">
                Container Resources
            </h2>
            <table style="width: 100%; border-collapse: collapse; margin-bottom: 20px;">
                <thead>
                    <tr style="background-color: #343a40; color: white;">
                        <th style="padding: 12px; border: 1px solid #ddd; text-align: left;">Container</th>
                        <th style="padding: 12px; border: 1px solid #ddd; text-align: left;">CPU %</th>
                        <th style="padding: 12px; border: 1px solid #ddd; text-align: left;">Memory</th>
                        <th style="padding: 12px; border: 1px solid #ddd; text-align: left;">Network I/O</th>
                    </tr>
                </thead>
                <tbody>
                    {stats_rows if stats_rows else '<tr><td colspan="4" style="padding: 12px; text-align: center;">No stats available</td></tr>'}
                </tbody>
            </table>

            <!-- Filesystem -->
            <h2 style="color: #333; border-bottom: 2px solid {alert_color}; padding-bottom: 10px;">
                Filesystem
            </h2>
            <table style="width: 100%; border-collapse: collapse; margin-bottom: 20px;">
                <thead>
                    <tr style="background-color: #343a40; color: white;">
                        <th style="padding: 12px; border: 1px solid #ddd; text-align: left;">Mount</th>
                        <th style="padding: 12px; border: 1px solid #ddd; text-align: left;">Filesystem</th>
                        <th style="padding: 12px; border: 1px solid #ddd; text-align: left;">Size</th>
                        <th style="padding: 12px; border: 1px solid #ddd; text-align: left;">Used</th>
                        <th style="padding: 12px; border: 1px solid #ddd; text-align: left;">Avail</th>
                        <th style="padding: 12px; border: 1px solid #ddd; text-align: left;">Use%</th>
                    </tr>
                </thead>
                <tbody>
                    {disk_rows if disk_rows else '<tr><td colspan="6" style="padding: 12px; text-align: center;">No disk info available</td></tr>'}
                </tbody>
            </table>

            <!-- Quick Actions -->
            <h2 style="color: #333; border-bottom: 2px solid {alert_color}; padding-bottom: 10px;">
                Quick Actions
            </h2>
            <table style="width: 100%; border-collapse: collapse; margin-bottom: 20px;">
                <tr style="background-color: #e9ecef;">
                    <td style="padding: 12px; border: 1px solid #ddd; font-weight: bold;">SSH Command</td>
                    <td style="padding: 12px; border: 1px solid #ddd; font-family: monospace; background-color: #1e1e1e; color: #4ec9b0;">
                        ssh {system_data['user']}@{system_data['public_ip']}
                    </td>
                </tr>
                <tr>
                    <td style="padding: 12px; border: 1px solid #ddd; font-weight: bold;">View Logs</td>
                    <td style="padding: 12px; border: 1px solid #ddd; font-family: monospace; background-color: #1e1e1e; color: #4ec9b0;">
                        cd /home/as/ws/odoo && docker compose logs --tail=100
                    </td>
                </tr>
                <tr style="background-color: #e9ecef;">
                    <td style="padding: 12px; border: 1px solid #ddd; font-weight: bold;">Monitor</td>
                    <td style="padding: 12px; border: 1px solid #ddd; font-family: monospace; background-color: #1e1e1e; color: #4ec9b0;">
                        docker stats
                    </td>
                </tr>
            </table>
        </div>

        <!-- Footer -->
        <div style="background-color: #343a40; color: #adb5bd; padding: 15px; text-align: center; font-size: 12px;">
            <p style="margin: 0;">Generated by <strong>Odoo Security Monitor</strong></p>
            <p style="margin: 5px 0 0 0;">Config: /home/as/ws/odoo/ops/monitoring/monitor.conf</p>
        </div>
    </div>
</body>
</html>
'''

msg = MIMEMultipart('alternative')
msg['Subject'] = subject
msg['From'] = "$EMAIL_FROM"
msg['To'] = "$EMAIL_TO"

# Attach HTML
html_part = MIMEText(html, 'html', 'utf-8')
msg.attach(html_part)

try:
    server = smtplib.SMTP("$SMTP_SERVER", $SMTP_PORT, timeout=30)
    server.starttls()
    server.login("$SMTP_USER", "$SMTP_PASS")
    server.sendmail("$EMAIL_FROM", "$EMAIL_TO", msg.as_string())
    server.quit()
    print("Email sent successfully")
except Exception as e:
    print(f"Failed to send email: {e}")
PYEOF

    log "Alert sent: $subject"
}

# Check 1: PostgreSQL failed login attempts
check_pg_failed_logins() {
    log "Checking PostgreSQL failed logins..."

    local state_file="$STATE_DIR/pg_failed_logins_count"
    local last_count=0
    [[ -f "$state_file" ]] && last_count=$(cat "$state_file")

    local failed_count
    failed_count=$(cd "$COMPOSE_DIR" && docker compose logs psql --since=10m 2>&1 | grep -c "password authentication failed" 2>/dev/null || true)
    failed_count=${failed_count:-0}
    failed_count=$(echo "$failed_count" | tr -d '[:space:]')

    if [[ "$failed_count" -ge "$PG_FAILED_LOGIN_THRESHOLD" ]]; then
        local attackers=$(cd "$COMPOSE_DIR" && docker compose logs psql --since=10m 2>&1 | grep "password authentication failed" | grep -oP 'user "\K[^"]+' | sort | uniq -c | sort -rn | head -10)
        local recent_logs=$(cd "$COMPOSE_DIR" && docker compose logs psql --since=10m 2>&1 | grep -E "(FATAL|ERROR)" | tail -10)
        local port_check=$(docker compose ps 2>/dev/null | grep psql | grep -q "0.0.0.0:5432" && echo "YES - DANGEROUS!" || echo "No (internal only)")

        local alert_details="BRUTE-FORCE ATTACK DETECTED

Failed Login Attempts (last 10 min): $failed_count
Alert Threshold: $PG_FAILED_LOGIN_THRESHOLD
PostgreSQL Port Exposed: $port_check

TOP TARGETED USERNAMES:
$attackers

RECENT ERRORS:
$recent_logs"

        send_alert "[CRITICAL] PostgreSQL Brute-Force Attack - $(hostname)" \
                   "SECURITY" \
                   "#dc3545" \
                   "$alert_details"

        log "ALERT: $failed_count failed PostgreSQL logins detected"
    fi

    echo "$failed_count" > "$state_file"
}

# Check 2: Container CPU usage
check_cpu_usage() {
    log "Checking container CPU usage..."

    local stats=$(docker stats --no-stream --format "{{.Name}},{{.CPUPerc}},{{.MemUsage}}" 2>/dev/null)

    while IFS=',' read -r name cpu mem; do
        cpu_num=$(echo "$cpu" | tr -d '%' | cut -d'.' -f1)

        if [[ "$cpu_num" -ge "$CPU_THRESHOLD" ]]; then
            local processes=$(docker exec "$name" ps aux --sort=-%cpu 2>/dev/null | head -15 || echo "Could not get processes")

            local alert_details="HIGH CPU USAGE DETECTED

Container: $name
Current CPU: $cpu
Memory: $mem
Threshold: ${CPU_THRESHOLD}%

TOP PROCESSES:
$processes

POSSIBLE CAUSES:
- Cryptominer malware
- Runaway process
- Heavy workload"

            send_alert "[ALERT] High CPU: $name at $cpu - $(hostname)" \
                       "PERFORMANCE" \
                       "#fd7e14" \
                       "$alert_details"

            log "ALERT: $name using $cpu CPU"
        fi
    done <<< "$stats"
}

# Check 3: Suspicious processes
check_suspicious_processes() {
    log "Checking for suspicious processes..."

    local pg_container=$(cd "$COMPOSE_DIR" && docker compose ps -q psql 2>/dev/null)

    if [[ -n "$pg_container" ]]; then
        local suspicious_patterns="pawns|earnfm|packet_sdk|cryptominer|xmrig|minerd|cgminer|bfgminer|cpuminer|kswapd0|kdevtmpfsi"

        local processes=$(docker exec "$pg_container" ps aux 2>/dev/null || echo "")
        local suspicious=$(echo "$processes" | grep -iE "$suspicious_patterns" || true)

        if [[ -n "$suspicious" ]]; then
            local alert_details="!!! MALWARE DETECTED !!!

SUSPICIOUS PROCESSES:
$suspicious

ALL PROCESSES:
$processes

IMMEDIATE ACTIONS:
1. docker compose stop psql
2. docker compose rm -f psql
3. docker compose up -d psql
4. Change all passwords!"

            send_alert "[CRITICAL] MALWARE DETECTED - $(hostname)" \
                       "SECURITY BREACH" \
                       "#dc3545" \
                       "$alert_details"

            log "CRITICAL: Suspicious processes detected"
        fi

        local proc_count=$(echo "$processes" | wc -l)
        if [[ "$proc_count" -gt "$MAX_PG_PROCESSES" ]]; then
            local alert_details="HIGH PROCESS COUNT

Process Count: $proc_count
Threshold: $MAX_PG_PROCESSES

PROCESSES:
$processes"

            send_alert "[WARNING] High Process Count - $(hostname)" \
                       "ANOMALY" \
                       "#ffc107" \
                       "$alert_details"

            log "WARNING: High process count ($proc_count)"
        fi
    fi
}

# Check 4: Container health
check_container_health() {
    log "Checking container health..."

    local unhealthy=$(cd "$COMPOSE_DIR" && docker compose ps 2>/dev/null | grep -E "(unhealthy|Exit)" || true)

    if [[ -n "$unhealthy" ]]; then
        local all_status=$(cd "$COMPOSE_DIR" && docker compose ps 2>/dev/null)

        local alert_details="CONTAINER HEALTH ISSUE

UNHEALTHY CONTAINERS:
$unhealthy

ALL CONTAINERS:
$all_status

RECOVERY:
docker compose restart <container>
docker compose up -d --force-recreate <container>"

        send_alert "[WARNING] Container Health Issue - $(hostname)" \
                   "AVAILABILITY" \
                   "#ffc107" \
                   "$alert_details"

        log "WARNING: Unhealthy containers detected"
    fi
}

# Check 5: Disk space
check_disk_space() {
    log "Checking disk space..."

    local usage=$(df -h / | awk 'NR==2 {print $5}' | tr -d '%')

    if [[ "$usage" -ge "$DISK_THRESHOLD" ]]; then
        local docker_disk=$(docker system df 2>/dev/null)

        local alert_details="LOW DISK SPACE

Root Partition: ${usage}%
Threshold: ${DISK_THRESHOLD}%

DOCKER USAGE:
$docker_disk

CLEANUP:
docker system prune -af
docker volume prune -f"

        send_alert "[WARNING] Low Disk Space: ${usage}% - $(hostname)" \
                   "CAPACITY" \
                   "#ffc107" \
                   "$alert_details"

        log "WARNING: Disk usage at ${usage}%"
    fi
}

# Main
main() {
    log "=== Starting security monitor ==="

    check_pg_failed_logins
    check_cpu_usage
    check_suspicious_processes
    check_container_health
    check_disk_space

    log "=== Monitor completed ==="
}

main "$@"
