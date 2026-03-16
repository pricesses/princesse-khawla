# guard/consumers.py

import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone
from datetime import timedelta
from .models import DashboardStatistics, ActivityLog
from .statistics_service import StatisticsService
import logging

logger = logging.getLogger(__name__)


class DashboardConsumer(AsyncWebsocketConsumer):
    """
    WebSocket Consumer pour le dashboard admin
    Gère les connexions et envoie les updates en temps réel
    """

    async def connect(self):
        await self.channel_layer.group_add('dashboard', self.channel_name)
        # Groupe séparé pour les clics temps réel
        await self.channel_layer.group_add('dashboard_realtime', self.channel_name)
        await self.accept()
        logger.info(f"Dashboard WebSocket connected: {self.channel_name}")

        # Stats initiales
        stats = await self.get_current_statistics()
        await self.send(text_data=json.dumps({
            'type': 'initial_stats',
            'data': stats,
        }))

        # Clics initiaux
        click_stats = await self.get_click_stats()
        await self.send(text_data=json.dumps({
            'type': 'init',
            **click_stats,
        }))

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard('dashboard', self.channel_name)
        await self.channel_layer.group_discard('dashboard_realtime', self.channel_name)
        logger.info(f"Dashboard WebSocket disconnected: {self.channel_name}")

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            message_type = data.get('type')

            if message_type == 'request_stats':
                stats = await self.get_current_statistics()
                await self.send(text_data=json.dumps({
                    'type': 'stats_update',
                    'data': stats,
                }))

            elif message_type == 'request_activities':
                activities = await self.get_recent_activities(
                    limit=data.get('limit', 20)
                )
                await self.send(text_data=json.dumps({
                    'type': 'activities_update',
                    'data': activities,
                }))

            elif message_type == 'request_chart_data':
                chart_type = data.get('chart_type')
                chart_data = await self.get_chart_data(chart_type)
                await self.send(text_data=json.dumps({
                    'type': 'chart_update',
                    'chart_type': chart_type,
                    'data': chart_data,
                }))

        except json.JSONDecodeError:
            logger.error(f"Invalid JSON received: {text_data}")
        except Exception as e:
            logger.error(f"Error processing WebSocket message: {e}")

    # ============================================
    # MESSAGE HANDLERS — Reçus du groupe
    # ============================================

    async def dashboard_update(self, event):
        """Updates généraux du dashboard"""
        await self.send(text_data=json.dumps({
            'type':          'dashboard_update',
            'entity_type':   event.get('entity_type'),
            'activity_type': event.get('activity_type'),
            'data':          event.get('data'),
            'timestamp':     event.get('timestamp'),
        }))

    async def click_update(self, event):
        """Reçoit un clic temps réel et le forward au client"""
        await self.send(text_data=json.dumps({
            'type':          'click_update',
            'content_type':  event.get('content_type'),
            'total_ads':     event.get('total_ads'),
            'total_events':  event.get('total_events'),
            'ads_series':    event.get('ads_series'),
            'events_series': event.get('events_series'),
        }))

    # ============================================
    # DATABASE METHODS
    # ============================================

    @database_sync_to_async
    def get_current_statistics(self):
        StatisticsService.update_all_statistics()
        stats = DashboardStatistics.get_or_create_current()
        return {
            'total_locations':        stats.total_locations,
            'locations_this_month':   stats.locations_this_month,
            'total_events':           stats.total_events,
            'upcoming_events':        stats.upcoming_events,
            'events_this_month':      stats.events_this_month,
            'total_hikings':          stats.total_hikings,
            'hikings_this_month':     stats.hikings_this_month,
            'total_ads':              stats.total_ads,
            'active_ads':             stats.active_ads,
            'total_fcm_devices':      stats.total_fcm_devices,
            'ios_devices':            stats.ios_devices,
            'android_devices':        stats.android_devices,
            'active_users_30d':       stats.active_users_30d,
            'notifications_sent_24h': stats.notifications_sent_24h,
            'notifications_failed_24h': stats.notifications_failed_24h,
            'error_count_24h':        stats.error_count_24h,
            'last_error_message':     stats.last_error_message,
            'updated_at':             stats.updated_at.isoformat(),
        }

    @database_sync_to_async
    def get_recent_activities(self, limit=20):
        return StatisticsService.get_recent_activities(limit)

    @database_sync_to_async
    def get_chart_data(self, chart_type):
        if chart_type == 'activity_timeline':
            return StatisticsService.get_activity_timeline(days=7)
        elif chart_type == 'device_distribution':
            data = StatisticsService.get_device_distribution()
            return [
                {'name': 'iOS',     'value': data['ios']},
                {'name': 'Android', 'value': data['android']},
            ]
        elif chart_type == 'notifications_timeline':
            return StatisticsService.get_notifications_timeline(hours=24)
        elif chart_type == 'locations_by_category':
            queryset = StatisticsService.get_locations_by_category()
            return [{'name': item['category__name'], 'count': item['count']} for item in queryset]
        elif chart_type == 'events_by_status':
            data = StatisticsService.get_events_by_status()
            return [
                {'name': 'À venir', 'value': data['upcoming']},
                {'name': 'En cours', 'value': data['ongoing']},
                {'name': 'Passés',   'value': data['past']},
            ]
        elif chart_type == 'hikings_by_difficulty':
            queryset = StatisticsService.get_hikings_by_difficulty()
            return [{'name': item['difficulty'], 'count': item['count']} for item in queryset]
        else:
            return []

    @database_sync_to_async
    def get_click_stats(self):
        """Retourne les séries de clics des 7 derniers jours"""
        try:
            from .models import ClickLog
            from django.db.models import Count
            from django.db.models.functions import TruncDate

            now   = timezone.now()
            start = now - timedelta(days=6)

            def series(content_type):
                counts = {
                    str(r['day']): r['n']
                    for r in ClickLog.objects
                        .filter(content_type=content_type, clicked_at__gte=start)
                        .annotate(day=TruncDate('clicked_at'))
                        .values('day')
                        .annotate(n=Count('id'))
                }
                result = []
                for i in range(6, -1, -1):
                    d = (now - timedelta(days=i)).date()
                    result.append(counts.get(str(d), 0))
                return result

            return {
                'total_ads':     ClickLog.objects.filter(content_type='ad').count(),
                'total_events':  ClickLog.objects.filter(content_type='event').count(),
                'ads_series':    series('ad'),
                'events_series': series('event'),
            }
        except Exception:
            # ClickLog pas encore migré — retourne des zéros
            return {
                'total_ads': 0, 'total_events': 0,
                'ads_series': [0,0,0,0,0,0,0],
                'events_series': [0,0,0,0,0,0,0],
            }