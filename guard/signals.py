from django.dispatch import receiver
from django.db.models.signals import post_save
from cities_light.signals import city_items_pre_import
import logging

logger = logging.getLogger(__name__)

ALLOWED_CITIES = {
    'TN': [ # Tunisia
        'Sousse', 'Sfax', 'Tunis', 'Kairouan', 'Monastir', 'Mahdia'
    ],
    'MA': [ # Morocco
        'Fez', 'Marrakesh', 'Essaouira', 'Tétouan', 'Rabat', 'Meknes'
    ],
    'DZ': [ # Algeria
        'Algiers', 'Ghardaïa'
    ],
    'LY': [ # Libya
        'Tripoli'
    ],
    'EG': [ # Egypt
        'Cairo'
    ],
    'LB': [ # Lebanon
        'Tripoli', 'Sidon'
    ],
    'YE': [ # Yemen
        "Sana'a"
    ],
    'SY': [ # Syria
        'Damascus', 'Aleppo'
    ]
}

@receiver(city_items_pre_import)
def filter_cities(sender, items, **kwargs):
    country_code = items[0] 
    
    name = items[1]
    country = items[8]
    
    if country in ALLOWED_CITIES:
        allowed_list = ALLOWED_CITIES[country]
        asciiname = items[2]
        
        if name in allowed_list or asciiname in allowed_list:
            return # Keep it
        
        if country == 'YE' and "Sana'a" in allowed_list:
             if name in ["Sana'a", "Sanaa", "Sana"]:
                 return

        if country == 'LB' and 'Sidon' in allowed_list:
            if name in ['Sidon', 'Saida']:
                return
                
        from cities_light.exceptions import InvalidItems
        raise InvalidItems()
    else:
        from cities_light.exceptions import InvalidItems
        raise InvalidItems()


# ============================================
# NOTIFICATION & DASHBOARD SIGNALS
# ============================================

def register_notification_signals():
    """
    Enregistre les signaux pour envoyer les push notifications
    ET mettre à jour le dashboard en temps réel
    """
    from guard.models import Location, Event, Hiking
    from guard.notifications import NotificationService
    from guard.statistics_service import StatisticsService

    @receiver(post_save, sender=Location)
    def location_created(sender, instance, created, **kwargs):
        """
        Déclenché quand une Location est créée:
        1. Log l'activité
        2. Envoie notification push
        3. Met à jour les statistiques
        4. Notifie les clients WebSocket
        """
        if created:
            try:
                logger.info(f"📍 New location created: {instance.id} - {instance.name}")
                
                # Envoie notification push
                try:
                    NotificationService.send_new_location_notification(instance)
                    logger.info(f"✅ Notification sent for location {instance.id}")
                except Exception as e:
                    logger.error(f"❌ Error sending notification: {e}")
                
                # Met à jour les statistiques du dashboard
                StatisticsService.update_all_statistics()
                
                # Notifie les clients WebSocket connectés
                notify_dashboard_clients('location', instance)
                
            except Exception as e:
                logger.error(f"❌ Error in location_created signal: {e}", exc_info=True)

    @receiver(post_save, sender=Event)
    def event_created(sender, instance, created, **kwargs):
        """
        Déclenché quand un Event est créé:
        1. Log l'activité
        2. Envoie notification push
        3. Met à jour les statistiques
        4. Notifie les clients WebSocket
        """
        if created:
            try:
                logger.info(f"🎉 New event created: {instance.id} - {instance.name}")
                
                # Envoie notification push
                try:
                    NotificationService.send_new_event_notification(instance)
                    logger.info(f"✅ Notification sent for event {instance.id}")
                except Exception as e:
                    logger.error(f"❌ Error sending notification: {e}")
                
                # Met à jour les statistiques du dashboard
                StatisticsService.update_all_statistics()
                
                # Notifie les clients WebSocket connectés
                notify_dashboard_clients('event', instance)
                
            except Exception as e:
                logger.error(f"❌ Error in event_created signal: {e}", exc_info=True)

    @receiver(post_save, sender=Hiking)
    def hiking_created(sender, instance, created, **kwargs):
        """
        Déclenché quand une Hiking est créée:
        1. Log l'activité
        2. Envoie notification push
        3. Met à jour les statistiques
        4. Notifie les clients WebSocket
        """
        if created:
            try:
                logger.info(f"🥾 New hiking created: {instance.id} - {instance.name}")
                
                # Envoie notification push
                try:
                    NotificationService.send_new_hiking_notification(instance)
                    logger.info(f"✅ Notification sent for hiking {instance.id}")
                except Exception as e:
                    logger.error(f"❌ Error sending notification: {e}")
                
                # Met à jour les statistiques du dashboard
                StatisticsService.update_all_statistics()
                
                # Notifie les clients WebSocket connectés
                notify_dashboard_clients('hiking', instance)
                
            except Exception as e:
                logger.error(f"❌ Error in hiking_created signal: {e}", exc_info=True)


def notify_dashboard_clients(entity_type, instance):
    """
    Envoie une notification WebSocket à tous les clients du dashboard
    pour les informer d'une nouvelle entité créée
    """
    try:
        from channels.layers import get_channel_layer
        from asgiref.sync import async_to_sync
        import json
        from django.utils import timezone
        
        channel_layer = get_channel_layer()
        
        # Prépare le message à envoyer
        message_data = {
            'type': 'dashboard_update',
            'entity_type': entity_type,
            'entity_id': instance.id,
            'entity_name': getattr(instance, 'name', str(instance)),
            'timestamp': timezone.now().isoformat(),
        }
        
        # Envoie le message à tous les clients du groupe 'dashboard'
        async_to_sync(channel_layer.group_send)(
            'dashboard',
            message_data
        )
        
        logger.debug(f"✅ WebSocket notification sent for {entity_type} {instance.id}")
        
    except Exception as e:
        logger.debug(f"⚠️ WebSocket notification failed (normal si WebSocket désactivé): {e}")


# Enregistre les signaux au démarrage
register_notification_signals()