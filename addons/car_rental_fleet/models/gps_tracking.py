# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import logging
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import math

_logger = logging.getLogger(__name__)


class FleetGPSTracking(models.Model):
    _name = 'fleet.gps.tracking'
    _description = 'Fleet GPS Tracking'
    _order = 'timestamp desc'
    
    vehicle_id = fields.Many2one('fleet.vehicle', string='Vehicle', required=True)
    timestamp = fields.Datetime('Timestamp', required=True, default=fields.Datetime.now)
    
    # GPS Coordinates
    latitude = fields.Float('Latitude', digits=(10, 6), required=True)
    longitude = fields.Float('Longitude', digits=(10, 6), required=True)
    altitude = fields.Float('Altitude (meters)', digits=(10, 2))
    accuracy = fields.Float('Accuracy (meters)', digits=(10, 2))
    
    # Speed and Direction
    speed = fields.Float('Speed (km/h)', digits=(10, 2))
    direction = fields.Float('Direction (degrees)', digits=(10, 2))
    
    # Location Information
    location_name = fields.Char('Location Name')
    address = fields.Text('Address')
    city = fields.Char('City')
    state = fields.Char('State')
    country = fields.Char('Country')
    
    # Vehicle Status
    engine_status = fields.Selection([
        ('on', 'Engine On'),
        ('off', 'Engine Off'),
        ('idle', 'Idle'),
    ], string='Engine Status')
    
    fuel_level = fields.Float('Fuel Level (%)', digits=(5, 2))
    battery_level = fields.Float('Battery Level (%)', digits=(5, 2))
    
    # Alerts
    alert_type = fields.Selection([
        ('speed', 'Speed Alert'),
        ('geofence', 'Geofence Alert'),
        ('fuel', 'Fuel Alert'),
        ('battery', 'Battery Alert'),
        ('maintenance', 'Maintenance Alert'),
        ('accident', 'Accident Alert'),
        ('theft', 'Theft Alert'),
    ], string='Alert Type')
    
    alert_message = fields.Text('Alert Message')
    alert_severity = fields.Selection([
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ], string='Alert Severity')
    
    # Enterprise Features
    is_enterprise = fields.Boolean('Enterprise Feature', default=True)
    requires_license = fields.Boolean('Requires License', default=True)
    
    def _is_enterprise_available(self):
        """Check if enterprise features are available"""
        return self.env.context.get('is_enterprise', True)
    
    @api.model
    def create_tracking_record(self, vehicle_id, latitude, longitude, **kwargs):
        """Create GPS tracking record"""
        if not self._is_enterprise_available():
            raise UserError(_("GPS tracking requires the Enterprise edition."))
        
        # Calculate speed if previous record exists
        speed = 0.0
        direction = 0.0
        
        last_record = self.search([
            ('vehicle_id', '=', vehicle_id),
        ], order='timestamp desc', limit=1)
        
        if last_record:
            speed = self._calculate_speed(
                last_record.latitude, last_record.longitude, last_record.timestamp,
                latitude, longitude, fields.Datetime.now()
            )
            direction = self._calculate_direction(
                last_record.latitude, last_record.longitude,
                latitude, longitude
            )
        
        # Create tracking record
        tracking_data = {
            'vehicle_id': vehicle_id,
            'latitude': latitude,
            'longitude': longitude,
            'speed': speed,
            'direction': direction,
            'timestamp': fields.Datetime.now(),
        }
        
        # Add additional data
        tracking_data.update(kwargs)
        
        return self.create(tracking_data)
    
    def _calculate_speed(self, lat1, lon1, time1, lat2, lon2, time2):
        """Calculate speed between two GPS points"""
        # Calculate distance using Haversine formula
        distance = self._calculate_distance(lat1, lon1, lat2, lon2)
        
        # Calculate time difference in hours
        time_diff = (time2 - time1).total_seconds() / 3600
        
        if time_diff > 0:
            return distance / time_diff  # km/h
        return 0.0
    
    def _calculate_direction(self, lat1, lon1, lat2, lon2):
        """Calculate direction between two GPS points"""
        # Convert to radians
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lon = math.radians(lon2 - lon1)
        
        # Calculate bearing
        y = math.sin(delta_lon) * math.cos(lat2_rad)
        x = math.cos(lat1_rad) * math.sin(lat2_rad) - math.sin(lat1_rad) * math.cos(lat2_rad) * math.cos(delta_lon)
        
        bearing = math.atan2(y, x)
        bearing = math.degrees(bearing)
        bearing = (bearing + 360) % 360
        
        return bearing
    
    def _calculate_distance(self, lat1, lon1, lat2, lon2):
        """Calculate distance between two GPS points using Haversine formula"""
        # Earth's radius in kilometers
        R = 6371.0
        
        # Convert to radians
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lon = math.radians(lon2 - lon1)
        
        # Haversine formula
        a = (math.sin(delta_lat / 2) ** 2 + 
             math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        
        return R * c
    
    @api.model
    def get_vehicle_location(self, vehicle_id):
        """Get current vehicle location"""
        if not self._is_enterprise_available():
            raise UserError(_("Location tracking requires the Enterprise edition."))
        
        last_record = self.search([
            ('vehicle_id', '=', vehicle_id),
        ], order='timestamp desc', limit=1)
        
        if not last_record:
            return None
        
        return {
            'vehicle_id': vehicle_id,
            'latitude': last_record.latitude,
            'longitude': last_record.longitude,
            'timestamp': last_record.timestamp,
            'speed': last_record.speed,
            'direction': last_record.direction,
            'location_name': last_record.location_name,
            'address': last_record.address,
        }
    
    @api.model
    def get_vehicle_route(self, vehicle_id, start_date, end_date):
        """Get vehicle route for a specific period"""
        if not self._is_enterprise_available():
            raise UserError(_("Route tracking requires the Enterprise edition."))
        
        tracking_records = self.search([
            ('vehicle_id', '=', vehicle_id),
            ('timestamp', '>=', start_date),
            ('timestamp', '<=', end_date),
        ], order='timestamp asc')
        
        route = []
        for record in tracking_records:
            route.append({
                'latitude': record.latitude,
                'longitude': record.longitude,
                'timestamp': record.timestamp,
                'speed': record.speed,
                'direction': record.direction,
                'location_name': record.location_name,
            })
        
        return route
    
    @api.model
    def get_vehicle_speed_history(self, vehicle_id, start_date, end_date):
        """Get vehicle speed history"""
        if not self._is_enterprise_available():
            raise UserError(_("Speed tracking requires the Enterprise edition."))
        
        tracking_records = self.search([
            ('vehicle_id', '=', vehicle_id),
            ('timestamp', '>=', start_date),
            ('timestamp', '<=', end_date),
            ('speed', '>', 0),
        ], order='timestamp asc')
        
        speed_history = []
        for record in tracking_records:
            speed_history.append({
                'timestamp': record.timestamp,
                'speed': record.speed,
                'latitude': record.latitude,
                'longitude': record.longitude,
            })
        
        return speed_history
    
    @api.model
    def get_speed_violations(self, vehicle_id, speed_limit=80):
        """Get speed violations for vehicle"""
        if not self._is_enterprise_available():
            raise UserError(_("Speed monitoring requires the Enterprise edition."))
        
        violations = self.search([
            ('vehicle_id', '=', vehicle_id),
            ('speed', '>', speed_limit),
        ], order='timestamp desc')
        
        return [{
            'timestamp': violation.timestamp,
            'speed': violation.speed,
            'speed_limit': speed_limit,
            'excess_speed': violation.speed - speed_limit,
            'latitude': violation.latitude,
            'longitude': violation.longitude,
            'location_name': violation.location_name,
        } for violation in violations]
    
    @api.model
    def get_geofence_alerts(self, vehicle_id, geofence_id):
        """Get geofence alerts for vehicle"""
        if not self._is_enterprise_available():
            raise UserError(_("Geofence monitoring requires the Enterprise edition."))
        
        alerts = self.search([
            ('vehicle_id', '=', vehicle_id),
            ('alert_type', '=', 'geofence'),
        ], order='timestamp desc')
        
        return [{
            'timestamp': alert.timestamp,
            'latitude': alert.latitude,
            'longitude': alert.longitude,
            'alert_message': alert.alert_message,
            'alert_severity': alert.alert_severity,
        } for alert in alerts]
    
    @api.model
    def get_vehicle_analytics(self, vehicle_id, start_date, end_date):
        """Get vehicle analytics from GPS data"""
        if not self._is_enterprise_available():
            raise UserError(_("Vehicle analytics require the Enterprise edition."))
        
        tracking_records = self.search([
            ('vehicle_id', '=', vehicle_id),
            ('timestamp', '>=', start_date),
            ('timestamp', '<=', end_date),
        ])
        
        if not tracking_records:
            return {}
        
        # Calculate statistics
        total_distance = 0.0
        max_speed = 0.0
        avg_speed = 0.0
        idle_time = 0.0
        driving_time = 0.0
        
        speeds = []
        for i in range(len(tracking_records) - 1):
            record1 = tracking_records[i]
            record2 = tracking_records[i + 1]
            
            # Calculate distance
            distance = self._calculate_distance(
                record1.latitude, record1.longitude,
                record2.latitude, record2.longitude
            )
            total_distance += distance
            
            # Track speed
            if record2.speed > 0:
                speeds.append(record2.speed)
                max_speed = max(max_speed, record2.speed)
                
                # Calculate time difference
                time_diff = (record2.timestamp - record1.timestamp).total_seconds() / 3600
                if record2.speed > 5:  # Consider moving if speed > 5 km/h
                    driving_time += time_diff
                else:
                    idle_time += time_diff
        
        if speeds:
            avg_speed = sum(speeds) / len(speeds)
        
        return {
            'total_distance': total_distance,
            'max_speed': max_speed,
            'avg_speed': avg_speed,
            'driving_time': driving_time,
            'idle_time': idle_time,
            'total_time': driving_time + idle_time,
            'efficiency': (driving_time / (driving_time + idle_time) * 100) if (driving_time + idle_time) > 0 else 0,
        }
    
    @api.model
    def create_geofence_alert(self, vehicle_id, geofence_name, alert_type, message):
        """Create geofence alert"""
        if not self._is_enterprise_available():
            raise UserError(_("Geofence alerts require the Enterprise edition."))
        
        # Get current vehicle location
        location = self.get_vehicle_location(vehicle_id)
        if not location:
            return None
        
        return self.create({
            'vehicle_id': vehicle_id,
            'latitude': location['latitude'],
            'longitude': location['longitude'],
            'alert_type': 'geofence',
            'alert_message': f"{geofence_name}: {message}",
            'alert_severity': 'medium',
            'location_name': geofence_name,
        })
    
    @api.model
    def get_fleet_overview(self):
        """Get fleet overview from GPS data"""
        if not self._is_enterprise_available():
            return {}
        
        vehicles = self.env['fleet.vehicle'].search([
            ('is_rental_vehicle', '=', True),
        ])
        
        fleet_data = {
            'total_vehicles': len(vehicles),
            'online_vehicles': 0,
            'offline_vehicles': 0,
            'moving_vehicles': 0,
            'idle_vehicles': 0,
        }
        
        for vehicle in vehicles:
            # Get last tracking record
            last_record = self.search([
                ('vehicle_id', '=', vehicle.id),
            ], order='timestamp desc', limit=1)
            
            if last_record:
                # Check if online (last update within 5 minutes)
                time_diff = (fields.Datetime.now() - last_record.timestamp).total_seconds() / 60
                if time_diff <= 5:
                    fleet_data['online_vehicles'] += 1
                    
                    # Check if moving
                    if last_record.speed > 5:
                        fleet_data['moving_vehicles'] += 1
                    else:
                        fleet_data['idle_vehicles'] += 1
                else:
                    fleet_data['offline_vehicles'] += 1
            else:
                fleet_data['offline_vehicles'] += 1
        
        return fleet_data


class FleetGeofence(models.Model):
    _name = 'fleet.geofence'
    _description = 'Fleet Geofence Management'
    
    name = fields.Char('Geofence Name', required=True)
    description = fields.Text('Description')
    
    # Geofence Type
    geofence_type = fields.Selection([
        ('circle', 'Circle'),
        ('polygon', 'Polygon'),
        ('rectangle', 'Rectangle'),
    ], string='Geofence Type', required=True, default='circle')
    
    # Circle Geofence
    center_latitude = fields.Float('Center Latitude', digits=(10, 6))
    center_longitude = fields.Float('Center Longitude', digits=(10, 6))
    radius = fields.Float('Radius (meters)', digits=(10, 2))
    
    # Polygon Geofence
    polygon_coordinates = fields.Text('Polygon Coordinates', help='JSON array of lat/lng coordinates')
    
    # Rectangle Geofence
    north_latitude = fields.Float('North Latitude', digits=(10, 6))
    south_latitude = fields.Float('South Latitude', digits=(10, 6))
    east_longitude = fields.Float('East Longitude', digits=(10, 6))
    west_longitude = fields.Float('West Longitude', digits=(10, 6))
    
    # Alert Settings
    alert_on_entry = fields.Boolean('Alert on Entry', default=True)
    alert_on_exit = fields.Boolean('Alert on Exit', default=True)
    alert_message = fields.Text('Alert Message')
    
    # Status
    active = fields.Boolean('Active', default=True)
    
    # Enterprise Features
    is_enterprise = fields.Boolean('Enterprise Feature', default=True)
    requires_license = fields.Boolean('Requires License', default=True)
    
    def _is_enterprise_available(self):
        """Check if enterprise features are available"""
        return self.env.context.get('is_enterprise', True)
    
    @api.model
    def check_vehicle_in_geofence(self, vehicle_id, geofence_id):
        """Check if vehicle is in geofence"""
        if not self._is_enterprise_available():
            return False
        
        geofence = self.browse(geofence_id)
        if not geofence.exists() or not geofence.active:
            return False
        
        # Get current vehicle location
        location = self.env['fleet.gps.tracking'].get_vehicle_location(vehicle_id)
        if not location:
            return False
        
        latitude = location['latitude']
        longitude = location['longitude']
        
        if geofence.geofence_type == 'circle':
            return self._check_circle_geofence(geofence, latitude, longitude)
        elif geofence.geofence_type == 'polygon':
            return self._check_polygon_geofence(geofence, latitude, longitude)
        elif geofence.geofence_type == 'rectangle':
            return self._check_rectangle_geofence(geofence, latitude, longitude)
        
        return False
    
    def _check_circle_geofence(self, geofence, latitude, longitude):
        """Check if point is in circle geofence"""
        if not geofence.center_latitude or not geofence.center_longitude or not geofence.radius:
            return False
        
        # Calculate distance from center
        distance = self.env['fleet.gps.tracking']._calculate_distance(
            geofence.center_latitude, geofence.center_longitude,
            latitude, longitude
        ) * 1000  # Convert to meters
        
        return distance <= geofence.radius
    
    def _check_polygon_geofence(self, geofence, latitude, longitude):
        """Check if point is in polygon geofence"""
        if not geofence.polygon_coordinates:
            return False
        
        try:
            import json
            coordinates = json.loads(geofence.polygon_coordinates)
            return self._point_in_polygon(latitude, longitude, coordinates)
        except:
            return False
    
    def _check_rectangle_geofence(self, geofence, latitude, longitude):
        """Check if point is in rectangle geofence"""
        if not all([geofence.north_latitude, geofence.south_latitude, 
                   geofence.east_longitude, geofence.west_longitude]):
            return False
        
        return (geofence.south_latitude <= latitude <= geofence.north_latitude and
                geofence.west_longitude <= longitude <= geofence.east_longitude)
    
    def _point_in_polygon(self, lat, lon, polygon):
        """Check if point is inside polygon using ray casting algorithm"""
        n = len(polygon)
        inside = False
        
        p1x, p1y = polygon[0]
        for i in range(1, n + 1):
            p2x, p2y = polygon[i % n]
            if lat > min(p1y, p2y):
                if lat <= max(p1y, p2y):
                    if lon <= max(p1x, p2x):
                        if p1y != p2y:
                            xinters = (lat - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                        if p1x == p2x or lon <= xinters:
                            inside = not inside
            p1x, p1y = p2x, p2y
        
        return inside




