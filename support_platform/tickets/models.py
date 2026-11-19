from datetime import timedelta
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name="Назва категорії")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Категорія"
        verbose_name_plural = "Категорії"


class Ticket(models.Model):
    class Priority(models.TextChoices):
        LOW = 'low', 'Низький'
        MEDIUM = 'medium', 'Середній'
        HIGH = 'high', 'Високий'
        CRITICAL = 'critical', 'Критичний'

    class Status(models.TextChoices):
        NEW = 'new', 'Нова'
        IN_PROGRESS = 'in_progress', 'В роботі'
        WAITING_CLIENT = 'waiting_client', 'Очікує відповіді клієнта'
        RESOLVED = 'resolved', 'Вирішена'
        CLOSED = 'closed', 'Закрита'
        REJECTED = 'rejected', 'Відхилена'

    # Дозволені переходи статусів (State Machine)
    ALLOWED_TRANSITIONS = {
        Status.NEW: [Status.IN_PROGRESS, Status.REJECTED],
        Status.IN_PROGRESS: [Status.WAITING_CLIENT, Status.RESOLVED, Status.REJECTED],
        Status.WAITING_CLIENT: [Status.IN_PROGRESS, Status.RESOLVED, Status.REJECTED],
        Status.RESOLVED: [Status.CLOSED, Status.IN_PROGRESS],
        Status.CLOSED: [],
        Status.REJECTED: [],
    }

    title = models.CharField(max_length=200, verbose_name="Заголовок")
    description = models.TextField(verbose_name="Опис")
    category = models.ForeignKey(Category, on_delete=models.PROTECT, verbose_name="Категорія")
    priority = models.CharField(max_length=20, choices=Priority.choices, default=Priority.MEDIUM, verbose_name="Пріоритет")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.NEW, verbose_name="Статус")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='created_tickets', verbose_name="Автор")
    assignee = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_tickets', verbose_name="Виконавець")
    resolved_at = models.DateTimeField(null=True, blank=True, verbose_name="Час вирішення")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата створення")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата оновлення")

    @property
    def is_final(self):
        return self.status in [self.Status.CLOSED, self.Status.REJECTED]

    def get_available_transitions(self, user):
        if self.is_final:
            return []

        possible = self.ALLOWED_TRANSITIONS.get(self.status, [])

        if user.is_client():
            # Клієнт може діяти тільки якщо заявка в статусі "Вирішена"
            if self.status != self.Status.RESOLVED:
                return []
            # Перевірка правила 3 днів
            if self.resolved_at and timezone.now() - self.resolved_at > timedelta(days=3):
                return [self.Status.CLOSED]  # Після 3 днів можна тільки закрити
            return [self.Status.CLOSED, self.Status.IN_PROGRESS]

        # Для Агента та Менеджера доступні стандартні переходи
        return possible

    def change_status(self, new_status, user):
        if self.is_final:
            raise ValidationError("Закриту або відхилену заявку не можна змінювати.")

        if user.is_agent() and self.author == user:
            raise ValidationError("Агент не може обробляти власну заявку.")

        if user.is_agent() and self.assignee and self.assignee != user:
            raise ValidationError("Заявка призначена іншому агенту.")

        allowed = self.get_available_transitions(user)
        if new_status not in allowed:
            raise ValidationError("Недопустимий перехід статусу або вичерпано термін повторного відкриття (3 дні).")

        self.status = new_status
        if new_status == self.Status.RESOLVED:
            self.resolved_at = timezone.now()
        self.save()

    def __str__(self):
        return f"#{self.id} - {self.title}"

    class Meta:
        verbose_name = "Заявка"
        verbose_name_plural = "Заявки"
        ordering = ['-created_at']


class Comment(models.Model):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name='comments', verbose_name="Заявка")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name="Автор")
    text = models.TextField(verbose_name="Текст коментаря")
    is_internal = models.BooleanField(default=False, verbose_name="Внутрішній коментар")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата створення")

    class Meta:
        verbose_name = "Коментар"
        verbose_name_plural = "Коментарі"
        ordering = ['created_at']