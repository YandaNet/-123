from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.exceptions import ValidationError

from .models import Ticket, Category
from .forms import TicketForm, CommentForm
from .selectors import filter_and_sort_tickets
from .services import create_ticket, take_ticket_in_work, change_ticket_status, add_comment_to_ticket
from accounts.models import User

@login_required
def ticket_list_view(request):
    tickets = filter_and_sort_tickets(request.user, request.GET)

    context = {
        'tickets': tickets,
        'categories': Category.objects.all(),
        'agents': User.objects.filter(role=User.Role.AGENT),
        'statuses': Ticket.Status.choices,
        'priorities': Ticket.Priority.choices,
    }
    return render(request, 'tickets/ticket_list.html', context)

@login_required
def ticket_create_view(request):
    if request.method == 'POST':
        form = TicketForm(request.POST)
        if form.is_valid():
            try:
                ticket = create_ticket(request.user, form.cleaned_data)
                messages.success(request, "Заявку успішно створено!")
                return redirect('ticket_detail', pk=ticket.pk)
            except ValidationError as e:
                messages.error(request, e.message)
    else:
        form = TicketForm()
    return render(request, 'tickets/ticket_form.html', {'form': form})

@login_required
def ticket_detail_view(request, pk):
    ticket = get_object_or_404(Ticket, pk=pk)
    user = request.user
    
    if request.method == 'POST':
        action = request.POST.get('action')
        try:
            if action == 'take_ticket' and user.is_agent():
                take_ticket_in_work(ticket, user)
                messages.success(request, "Ви взяли заявку в роботу.")
            elif action == 'change_status':
                change_ticket_status(ticket, request.POST.get('status'), user)
                messages.success(request, "Статус змінено.")
            elif action == 'add_comment':
                comment_form = CommentForm(request.POST)
                if comment_form.is_valid():
                    add_comment_to_ticket(ticket, user, comment_form.cleaned_data['text'], comment_form.cleaned_data.get('is_internal', False))
                    messages.success(request, "Коментар додано.")
        except ValidationError as e:
            messages.error(request, e.message)
        return redirect('ticket_detail', pk=ticket.pk)

    comment_form = CommentForm()
    comments = ticket.comments.filter(is_internal=False) if user.is_client() else ticket.comments.all()
    available_statuses = [(code, dict(Ticket.Status.choices)[code]) for code in ticket.get_available_transitions(user)]

    return render(request, 'tickets/ticket_detail.html', {
        'ticket': ticket,
        'comments': comments,
        'comment_form': comment_form,
        'available_statuses': available_statuses,
        'agents': User.objects.filter(role=User.Role.AGENT).exclude(id=ticket.author.id),
    })