from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    class Role(models.TextChoices):
        CLIENT = 'client', 'Клієнт'
        AGENT = 'agent', 'Агент підтримки'
        MANAGER = 'manager', 'Менеджер'

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.CLIENT,
        verbose_name='Роль'
    )
    phone = models.CharField(max_length=20, blank=True, verbose_name='Телефон')

    def save(self, *args, **kwargs):
        if self.role == self.Role.MANAGER:
            self.is_staff = True
        super().save(*args, **kwargs)

    def is_client(self):
        return self.role == self.Role.CLIENT

    def is_agent(self):
        return self.role == self.Role.AGENT

    def is_manager(self):
        return self.role == self.Role.MANAGER