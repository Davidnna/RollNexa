from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import UserProfile


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def ensure_user_profile(sender, instance, created, **kwargs):
    if created:
        role = UserProfile.ROLE_ADMIN if instance.is_superuser else UserProfile.ROLE_STUDENT
        UserProfile.objects.get_or_create(user=instance, defaults={"role": role})
        return

    profile, _ = UserProfile.objects.get_or_create(
        user=instance,
        defaults={
            "role": UserProfile.ROLE_ADMIN if instance.is_superuser else UserProfile.ROLE_STUDENT
        },
    )
    if instance.is_superuser and profile.role != UserProfile.ROLE_ADMIN:
        profile.role = UserProfile.ROLE_ADMIN
        profile.save(update_fields=["role", "updated_at"])
