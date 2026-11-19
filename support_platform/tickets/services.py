from django.core.exceptions import ValidationError
from django.utils import timezone
from accounts.models import User
from .models import Ticket, Comment

def create_ticket(user: User, data: dict) -> Ticket:
    """Сервіс створення заявки з перевіркою ліміту (не більше 5 відкритих)."""
    active_statuses = [Ticket.Status.NEW, Ticket.Status.IN_PROGRESS, Ticket.Status.WAITING_CLIENT]
    active_count = Ticket.objects.filter(author=user, status__in=active_statuses).count()
    
    if active_count >= 5:
        raise ValidationError("Ви не можете мати більше 5 відкритих заявок одночасно.")

    ticket = Ticket.objects.create(
        title=data.get('title'),
        description=data.get('description'),
        category=data.get('category'),
        priority=data.get('priority', Ticket.Priority.MEDIUM),
        author=user
    )
    return ticket

def take_ticket_in_work(ticket: Ticket, agent: User) -> None:
    """Агент бере заявку в роботу."""
    if ticket.is_final:
        raise ValidationError("Заявка вже закрита.")
    if ticket.author == agent:
        raise ValidationError("Агент не може взяти в роботу власну заявку.")
    if ticket.assignee is not None and ticket.assignee != agent:
        raise ValidationError("Ця заявка вже призначена іншому агенту.")

    ticket.assignee = agent
    if ticket.status == Ticket.Status.NEW:
        ticket.status = Ticket.Status.IN_PROGRESS
    ticket.save()

def change_ticket_status(ticket: Ticket, new_status: str, user: User) -> None:
    """Зміна статусу заявки через держмашину переходів."""
    if ticket.is_final:
        raise ValidationError("Закриту або відхилену заявку не можна змінювати.")

    if user.is_agent() and ticket.author == user:
        raise ValidationError("Агент не може обробляти власну заявку.")

    if user.is_agent() and ticket.assignee and ticket.assignee != user:
        raise ValidationError("Заявка призначена іншому агенту.")

    allowed = ticket.get_available_transitions(user)
    if new_status not in allowed:
        raise ValidationError("Недопустимий перехід статусу або вичерпано термін повторного відкриття (3 дні).")

    ticket.status = new_status
    if new_status == Ticket.Status.RESOLVED:
        ticket.resolved_at = timezone.now()
    ticket.save()

def add_comment_to_ticket(ticket: Ticket, user: User, text: str, is_internal: bool = False) -> Comment:
    """Додавання коментаря до заявки."""
    if ticket.is_final:
        raise ValidationError("Не можна коментувати закриту або відхилену заявку.")
    
    if user.is_client():
        is_internal = False  

    return Comment.objects.create(
        ticket=ticket,
        author=user,
        text=text,
        is_internal=is_internal
    )