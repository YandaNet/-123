from django.db.models import QuerySet, Case, When, Value, IntegerField
from .models import Ticket
from accounts.models import User

def get_tickets_for_user(user: User) -> QuerySet[Ticket]:
    """Повертає базовий queryset заявок залежно від ролі користувача."""
    if user.is_client():
        return Ticket.objects.filter(author=user)
    elif user.is_agent():
        return (Ticket.objects.filter(assignee=user) | 
                Ticket.objects.filter(status=Ticket.Status.NEW, assignee__isnull=True)).exclude(author=user)
    elif user.is_manager():
        return Ticket.objects.all()
    return Ticket.objects.none()

def filter_and_sort_tickets(user: User, filters: dict) -> QuerySet[Ticket]:
    """Фільтрує, шукає та сортує заявки на основі переданих параметрів з GET-запиту."""
    tickets = get_tickets_for_user(user)

    # Пошук
    search_query = filters.get('q', '').strip()
    if search_query:
        tickets = tickets.filter(title__icontains=search_query)

    if status := filters.get('status'):
        tickets = tickets.filter(status=status)
    if priority := filters.get('priority'):
        tickets = filters.filter(priority=priority)
    if category_id := filters.get('category'):
        tickets = tickets.filter(category_id=category_id)
    if assignee_id := filters.get('assignee'):
        tickets = tickets.filter(assignee_id=assignee_id)
    if created_date := filters.get('created_date'):
        tickets = tickets.filter(created_at__date=created_date)

    sort_by = filters.get('sort', '-created_at')
    if sort_by in ['priority_desc', 'priority_asc']:
        direction = -1 if sort_by == 'priority_desc' else 1
        tickets = tickets.annotate(
            p_order=Case(
                When(priority='critical', then=Value(4)),
                When(priority='high', then=Value(3)),
                When(priority='medium', then=Value(2)),
                When(priority='low', then=Value(1)),
                output_field=IntegerField(),
            )
        ).order_by(f'{"-" if direction < int(0) else ""}p_order', '-created_at')
    elif sort_by in ['created_at', '-created_at']:
        tickets = tickets.order_by(sort_by)

    return tickets.distinct()