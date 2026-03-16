# guard/statistics_service.py

from django.db.models import Count
from django.utils import timezone
from datetime import timedelta
from .models import DashboardStatistics, Location, Event, Hiking, Ad


class StatisticsService:
    """
    Service centralisé pour calculer toutes les statistiques du dashboard.
    Adapté aux champs réels des modèles.
    """

    @staticmethod
    def update_all_statistics():
        stats = DashboardStatistics.get_or_create_current()

        now = timezone.now()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        day_ago = now - timedelta(days=1)

        # === LOCATIONS ===
        stats.total_locations = Location.objects.count()
        stats.locations_this_month = Location.objects.filter(
            created_at__gte=month_start
        ).count()

        # === EVENTS ===
        stats.total_events = Event.objects.count()
        stats.upcoming_events = Event.objects.filter(startDate__gte=now.date()).count()
        stats.events_this_month = Event.objects.filter(
            created_at__gte=month_start
        ).count()

        # === HIKINGS ===
        stats.total_hikings = Hiking.objects.count()
        stats.hikings_this_month = Hiking.objects.filter(
            created_at__gte=month_start
        ).count()

        # === ADS ===
        stats.total_ads = Ad.objects.count()
        stats.active_ads = Ad.objects.filter(is_active=True).count()

        # === DEVICES ===
        try:
            from fcm_django.models import FCMDevice
            stats.total_fcm_devices = FCMDevice.objects.count()
            stats.ios_devices = FCMDevice.objects.filter(type='ios').count()
            stats.android_devices = FCMDevice.objects.filter(type='android').count()
            stats.active_users_30d = FCMDevice.objects.filter(
                date_created__gte=now - timedelta(days=30)
            ).values('user_id').distinct().count()
        except Exception:
            pass

        # === NOTIFICATIONS (24h) ===
        try:
            from .models import NotificationLog
            notifications_24h = NotificationLog.objects.filter(timestamp__gte=day_ago)
            stats.notifications_sent_24h = notifications_24h.filter(
                status__in=['sent', 'delivered']
            ).count()
            stats.notifications_failed_24h = notifications_24h.filter(
                status='failed'
            ).count()
        except Exception:
            pass

        # === ERREURS ===
        try:
            from .models import ActivityLog
            errors_24h = ActivityLog.objects.filter(
                timestamp__gte=day_ago, success=False
            )
            stats.error_count_24h = errors_24h.count()
            if errors_24h.exists():
                stats.last_error_message = errors_24h.first().error_message
        except Exception:
            pass

        stats.save()
        return stats

    @staticmethod
    def get_locations_by_category():
        return (
            Location.objects.values('category__name')
            .annotate(count=Count('id'))
            .order_by('-count')
        )

    @staticmethod
    def get_locations_by_city():
        return (
            Location.objects.values('city__name')
            .annotate(count=Count('id'))
            .order_by('-count')[:10]
        )

    @staticmethod
    def get_events_by_status():
        now = timezone.now().date()
        return {
            'upcoming': Event.objects.filter(startDate__gt=now).count(),
            'ongoing': Event.objects.filter(startDate__lte=now, endDate__gte=now).count(),
            'past': Event.objects.filter(endDate__lt=now).count(),
        }

    @staticmethod
    def get_activity_timeline(days=7):
        try:
            from .models import ActivityLog
            now = timezone.now()
            data = []
            for i in range(days, 0, -1):
                date = (now - timedelta(days=i)).date()
                date_start = timezone.make_aware(
                    timezone.datetime.combine(date, timezone.datetime.min.time())
                )
                date_end = date_start + timedelta(days=1)
                count = ActivityLog.objects.filter(
                    timestamp__gte=date_start,
                    timestamp__lt=date_end,
                    activity_type__in=['location_created', 'event_created', 'hiking_created'],
                ).count()
                data.append({'date': date.isoformat(), 'count': count})
            return data
        except Exception:
            return []

    @staticmethod
    def get_recent_activities(limit=20):
        try:
            from .models import ActivityLog
            activities = ActivityLog.objects.all()[:limit]
            return [
                {
                    'id': a.id,
                    'type': a.get_activity_type_display(),
                    'entity_type': a.entity_type,
                    'entity_name': a.entity_name,
                    'timestamp': a.timestamp.isoformat(),
                    'success': a.success,
                }
                for a in activities
            ]
        except Exception:
            return []

    @staticmethod
    def get_device_distribution():
        try:
            from fcm_django.models import FCMDevice
            return {
                'ios': FCMDevice.objects.filter(type='ios', active=True).count(),
                'android': FCMDevice.objects.filter(type='android', active=True).count(),
            }
        except Exception:
            return {'ios': 0, 'android': 0}

    @staticmethod
    def get_notifications_timeline(hours=24):
        try:
            from .models import NotificationLog
            now = timezone.now()
            data = []
            for i in range(hours, 0, -1):
                hour_start = now - timedelta(hours=i)
                hour_end = hour_start + timedelta(hours=1)
                sent = NotificationLog.objects.filter(
                    timestamp__gte=hour_start,
                    timestamp__lt=hour_end,
                    status__in=['sent', 'delivered'],
                ).count()
                failed = NotificationLog.objects.filter(
                    timestamp__gte=hour_start,
                    timestamp__lt=hour_end,
                    status='failed',
                ).count()
                data.append({'hour': hour_start.strftime('%H:%M'), 'sent': sent, 'failed': failed})
            return data
        except Exception:
            return []