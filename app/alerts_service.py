#!/usr/bin/env python3
"""
User Alerts Service
Handles price alerts, volume alerts, score alerts, and event notifications
"""

from typing import Dict, List, Optional
from datetime import datetime, timedelta
from database import DatabaseManager
from sqlalchemy import text
from logging_config import get_logger
import json

logger = get_logger(__name__)

class AlertsService:
    """Service for managing user alerts and notifications"""
    
    def __init__(self):
        self.db_manager = DatabaseManager()
    
    def create_alert(self, user_id: int, symbol: str, alert_type: str, 
                    condition_type: str, target_value: float = None,
                    upper_threshold: float = None, lower_threshold: float = None) -> Optional[int]:
        """
        Create a new alert for a user
        
        Args:
            user_id: User ID
            symbol: Stock symbol
            alert_type: 'price', 'volume', 'score', 'event'
            condition_type: 'above', 'below', 'range', 'change_percent'
            target_value: Target value for above/below conditions
            upper_threshold: Upper bound for range conditions
            lower_threshold: Lower bound for range conditions
            
        Returns:
            Alert ID if successful, None otherwise
        """
        try:
            with self.db_manager.engine.connect() as conn:
                result = conn.execute(text("""
                    INSERT INTO user_alerts 
                    (user_id, symbol, alert_type, condition_type, target_value, 
                     upper_threshold, lower_threshold)
                    VALUES (:user_id, :symbol, :alert_type, :condition_type, 
                           :target_value, :upper_threshold, :lower_threshold)
                    RETURNING id
                """), {
                    'user_id': user_id,
                    'symbol': symbol.upper(),
                    'alert_type': alert_type,
                    'condition_type': condition_type,
                    'target_value': target_value,
                    'upper_threshold': upper_threshold,
                    'lower_threshold': lower_threshold
                })
                
                alert_id = result.fetchone()[0]
                conn.commit()
                
                logger.info(f"Created alert {alert_id} for user {user_id}: {symbol} {alert_type} {condition_type}")
                return alert_id
                
        except Exception as e:
            logger.error(f"Error creating alert: {e}")
            return None
    
    def get_user_alerts(self, user_id: int, active_only: bool = True) -> List[Dict]:
        """
        Get all alerts for a user
        
        Args:
            user_id: User ID
            active_only: Only return active alerts
            
        Returns:
            List of alert dictionaries
        """
        try:
            with self.db_manager.engine.connect() as conn:
                where_clause = "WHERE user_id = :user_id"
                if active_only:
                    where_clause += " AND is_active = TRUE"
                
                result = conn.execute(text(f"""
                    SELECT id, symbol, alert_type, condition_type, target_value,
                           upper_threshold, lower_threshold, is_active, created_at,
                           last_triggered_at, trigger_count
                    FROM user_alerts
                    {where_clause}
                    ORDER BY created_at DESC
                """), {'user_id': user_id})
                
                alerts = []
                for row in result.fetchall():
                    alerts.append({
                        'id': row.id,
                        'symbol': row.symbol,
                        'alert_type': row.alert_type,
                        'condition_type': row.condition_type,
                        'target_value': row.target_value,
                        'upper_threshold': row.upper_threshold,
                        'lower_threshold': row.lower_threshold,
                        'is_active': row.is_active,
                        'created_at': row.created_at.isoformat() if row.created_at else None,
                        'last_triggered_at': row.last_triggered_at.isoformat() if row.last_triggered_at else None,
                        'trigger_count': row.trigger_count
                    })
                
                return alerts
                
        except Exception as e:
            logger.error(f"Error getting user alerts: {e}")
            return []
    
    def delete_alert(self, alert_id: int, user_id: int) -> bool:
        """
        Delete an alert (only if it belongs to the user)
        
        Args:
            alert_id: Alert ID
            user_id: User ID for verification
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with self.db_manager.engine.connect() as conn:
                result = conn.execute(text("""
                    DELETE FROM user_alerts 
                    WHERE id = :alert_id AND user_id = :user_id
                """), {'alert_id': alert_id, 'user_id': user_id})
                
                deleted = result.rowcount > 0
                conn.commit()
                
                if deleted:
                    logger.info(f"Deleted alert {alert_id} for user {user_id}")
                
                return deleted
                
        except Exception as e:
            logger.error(f"Error deleting alert: {e}")
            return False
    
    def toggle_alert(self, alert_id: int, user_id: int) -> bool:
        """
        Toggle alert active status
        
        Args:
            alert_id: Alert ID
            user_id: User ID for verification
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with self.db_manager.engine.connect() as conn:
                result = conn.execute(text("""
                    UPDATE user_alerts 
                    SET is_active = NOT is_active, updated_at = CURRENT_TIMESTAMP
                    WHERE id = :alert_id AND user_id = :user_id
                """), {'alert_id': alert_id, 'user_id': user_id})
                
                updated = result.rowcount > 0
                conn.commit()
                
                if updated:
                    logger.info(f"Toggled alert {alert_id} for user {user_id}")
                
                return updated
                
        except Exception as e:
            logger.error(f"Error toggling alert: {e}")
            return False
    
    def check_price_alerts(self, symbol: str, current_price: float) -> List[Dict]:
        """
        Check if any price alerts should be triggered
        
        Args:
            symbol: Stock symbol
            current_price: Current stock price
            
        Returns:
            List of triggered alerts
        """
        try:
            with self.db_manager.engine.connect() as conn:
                # Get all active price alerts for this symbol
                result = conn.execute(text("""
                    SELECT id, user_id, condition_type, target_value, 
                           upper_threshold, lower_threshold, last_triggered_at
                    FROM user_alerts
                    WHERE symbol = :symbol AND alert_type = 'price' AND is_active = TRUE
                """), {'symbol': symbol.upper()})
                
                triggered_alerts = []
                
                for row in result.fetchall():
                    should_trigger = False
                    
                    # Check cooldown period (don't trigger same alert within 1 hour)
                    if row.last_triggered_at:
                        cooldown_period = datetime.now() - row.last_triggered_at
                        if cooldown_period < timedelta(hours=1):
                            continue
                    
                    # Check trigger conditions
                    if row.condition_type == 'above' and current_price > row.target_value:
                        should_trigger = True
                    elif row.condition_type == 'below' and current_price < row.target_value:
                        should_trigger = True
                    elif row.condition_type == 'range':
                        if (row.lower_threshold and current_price < row.lower_threshold) or \
                           (row.upper_threshold and current_price > row.upper_threshold):
                            should_trigger = True
                    
                    if should_trigger:
                        triggered_alerts.append({
                            'alert_id': row.id,
                            'user_id': row.user_id,
                            'symbol': symbol,
                            'condition_type': row.condition_type,
                            'target_value': row.target_value,
                            'current_value': current_price
                        })
                
                return triggered_alerts
                
        except Exception as e:
            logger.error(f"Error checking price alerts: {e}")
            return []
    
    def check_score_alerts(self, symbol: str, current_score: float) -> List[Dict]:
        """
        Check if any undervaluation score alerts should be triggered
        
        Args:
            symbol: Stock symbol
            current_score: Current undervaluation score
            
        Returns:
            List of triggered alerts
        """
        try:
            with self.db_manager.engine.connect() as conn:
                # Get all active score alerts for this symbol
                result = conn.execute(text("""
                    SELECT id, user_id, condition_type, target_value, 
                           upper_threshold, lower_threshold, last_triggered_at
                    FROM user_alerts
                    WHERE symbol = :symbol AND alert_type = 'score' AND is_active = TRUE
                """), {'symbol': symbol.upper()})
                
                triggered_alerts = []
                
                for row in result.fetchall():
                    should_trigger = False
                    
                    # Check cooldown period (don't trigger same alert within 4 hours)
                    if row.last_triggered_at:
                        cooldown_period = datetime.now() - row.last_triggered_at
                        if cooldown_period < timedelta(hours=4):
                            continue
                    
                    # Check trigger conditions
                    if row.condition_type == 'above' and current_score > row.target_value:
                        should_trigger = True
                    elif row.condition_type == 'below' and current_score < row.target_value:
                        should_trigger = True
                    elif row.condition_type == 'range':
                        if (row.lower_threshold and current_score < row.lower_threshold) or \
                           (row.upper_threshold and current_score > row.upper_threshold):
                            should_trigger = True
                    
                    if should_trigger:
                        triggered_alerts.append({
                            'alert_id': row.id,
                            'user_id': row.user_id,
                            'symbol': symbol,
                            'condition_type': row.condition_type,
                            'target_value': row.target_value,
                            'current_value': current_score
                        })
                
                return triggered_alerts
                
        except Exception as e:
            logger.error(f"Error checking score alerts: {e}")
            return []
    
    def trigger_alert(self, alert_id: int, user_id: int, symbol: str, 
                     alert_type: str, current_value: float, target_value: float) -> bool:
        """
        Trigger an alert and create a notification
        
        Args:
            alert_id: Alert ID
            user_id: User ID
            symbol: Stock symbol
            alert_type: Type of alert
            current_value: Current value that triggered the alert
            target_value: Target value from alert condition
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with self.db_manager.engine.connect() as conn:
                # Update alert trigger info
                conn.execute(text("""
                    UPDATE user_alerts 
                    SET last_triggered_at = CURRENT_TIMESTAMP, trigger_count = trigger_count + 1
                    WHERE id = :alert_id
                """), {'alert_id': alert_id})
                
                # Create notification message
                if alert_type == 'price':
                    message = f"{symbol} price alert: ${current_value:.2f} (target: ${target_value:.2f})"
                elif alert_type == 'score':
                    message = f"{symbol} undervaluation score alert: {current_value:.1f} (target: {target_value:.1f})"
                else:
                    message = f"{symbol} {alert_type} alert triggered"
                
                # Create notification
                conn.execute(text("""
                    INSERT INTO alert_notifications 
                    (alert_id, user_id, symbol, alert_type, message, current_value, target_value)
                    VALUES (:alert_id, :user_id, :symbol, :alert_type, :message, :current_value, :target_value)
                """), {
                    'alert_id': alert_id,
                    'user_id': user_id,
                    'symbol': symbol,
                    'alert_type': alert_type,
                    'message': message,
                    'current_value': current_value,
                    'target_value': target_value
                })
                
                conn.commit()
                logger.info(f"Triggered alert {alert_id} for user {user_id}: {message}")
                return True
                
        except Exception as e:
            logger.error(f"Error triggering alert: {e}")
            return False
    
    def get_user_notifications(self, user_id: int, unread_only: bool = False, limit: int = 50) -> List[Dict]:
        """
        Get notifications for a user
        
        Args:
            user_id: User ID
            unread_only: Only return unread notifications
            limit: Maximum number of notifications to return
            
        Returns:
            List of notification dictionaries
        """
        try:
            with self.db_manager.engine.connect() as conn:
                where_clause = "WHERE user_id = :user_id"
                if unread_only:
                    where_clause += " AND is_read = FALSE"
                
                result = conn.execute(text(f"""
                    SELECT id, alert_id, symbol, alert_type, message, current_value,
                           target_value, triggered_at, is_read
                    FROM alert_notifications
                    {where_clause}
                    ORDER BY triggered_at DESC
                    LIMIT :limit
                """), {'user_id': user_id, 'limit': limit})
                
                notifications = []
                for row in result.fetchall():
                    notifications.append({
                        'id': row.id,
                        'alert_id': row.alert_id,
                        'symbol': row.symbol,
                        'alert_type': row.alert_type,
                        'message': row.message,
                        'current_value': row.current_value,
                        'target_value': row.target_value,
                        'triggered_at': row.triggered_at.isoformat() if row.triggered_at else None,
                        'is_read': row.is_read
                    })
                
                return notifications
                
        except Exception as e:
            logger.error(f"Error getting user notifications: {e}")
            return []
    
    def mark_notification_read(self, notification_id: int, user_id: int) -> bool:
        """
        Mark a notification as read
        
        Args:
            notification_id: Notification ID
            user_id: User ID for verification
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with self.db_manager.engine.connect() as conn:
                result = conn.execute(text("""
                    UPDATE alert_notifications 
                    SET is_read = TRUE
                    WHERE id = :notification_id AND user_id = :user_id
                """), {'notification_id': notification_id, 'user_id': user_id})
                
                updated = result.rowcount > 0
                conn.commit()
                
                return updated
                
        except Exception as e:
            logger.error(f"Error marking notification as read: {e}")
            return False
    
    def mark_all_notifications_read(self, user_id: int) -> bool:
        """
        Mark all notifications as read for a user
        
        Args:
            user_id: User ID
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with self.db_manager.engine.connect() as conn:
                result = conn.execute(text("""
                    UPDATE alert_notifications 
                    SET is_read = TRUE
                    WHERE user_id = :user_id AND is_read = FALSE
                """), {'user_id': user_id})
                
                updated_count = result.rowcount
                conn.commit()
                
                logger.info(f"Marked {updated_count} notifications as read for user {user_id}")
                return True
                
        except Exception as e:
            logger.error(f"Error marking all notifications as read: {e}")
            return False
    
    def get_unread_count(self, user_id: int) -> int:
        """
        Get count of unread notifications for a user
        
        Args:
            user_id: User ID
            
        Returns:
            Number of unread notifications
        """
        try:
            with self.db_manager.engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT COUNT(*) 
                    FROM alert_notifications 
                    WHERE user_id = :user_id AND is_read = FALSE
                """), {'user_id': user_id})
                
                return result.fetchone()[0]
                
        except Exception as e:
            logger.error(f"Error getting unread count: {e}")
            return 0
    
    def cleanup_old_notifications(self, days_old: int = 30) -> int:
        """
        Clean up old notifications
        
        Args:
            days_old: Delete notifications older than this many days
            
        Returns:
            Number of deleted notifications
        """
        try:
            with self.db_manager.engine.connect() as conn:
                result = conn.execute(text("""
                    DELETE FROM alert_notifications 
                    WHERE triggered_at < CURRENT_TIMESTAMP - INTERVAL '%s days'
                """ % days_old))
                
                deleted_count = result.rowcount
                conn.commit()
                
                logger.info(f"Cleaned up {deleted_count} old notifications")
                return deleted_count
                
        except Exception as e:
            logger.error(f"Error cleaning up old notifications: {e}")
            return 0