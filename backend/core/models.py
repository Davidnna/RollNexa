from django.conf import settings
from django.db import models


class AuditEvent(models.Model):
    """Append-only record of security- and operations-relevant changes."""

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="rollnexa_audit_events",
    )
    actor_username = models.CharField(max_length=150, blank=True)
    event_type = models.CharField(max_length=80, db_index=True)
    object_type = models.CharField(max_length=80, db_index=True)
    object_id = models.CharField(max_length=64, blank=True)
    summary = models.CharField(max_length=255)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at", "-pk"]
        indexes = [
            models.Index(fields=["event_type", "created_at"], name="audit_event_type_time_idx"),
            models.Index(fields=["object_type", "object_id"], name="audit_object_lookup_idx"),
        ]

    def save(self, *args, **kwargs):
        if self.pk is not None and not self._state.adding:
            raise ValueError("Audit events are append-only and cannot be modified.")
        if self.actor_id and not self.actor_username:
            self.actor_username = self.actor.get_username()
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValueError("Audit events are append-only and cannot be deleted through the application.")

    def __str__(self):
        return f"{self.event_type} — {self.object_type} {self.object_id}".strip()
