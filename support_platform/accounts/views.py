from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count
from .forms import CustomUserCreationForm, ProfileUpdateForm
from .models import User
from tickets.models import Ticket

def register_view(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()  
            login(request, user)
            return redirect('ticket_list')
    else:
        form = CustomUserCreationForm()
    return render(request, 'accounts/register.html', {'form': form})

@login_required
def profile_view(request):
    user = request.user
    
    if request.method == 'POST':
        form = ProfileUpdateForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Профіль успішно оновлено!')
            return redirect('profile')
    else:
        form = ProfileUpdateForm(instance=user)

    context = {'user': user, 'form': form}
    
    if user.is_client():
        context['tickets'] = user.created_tickets.all()
        context['stats'] = {
            'open': user.created_tickets.filter(status__in=['new', 'in_progress', 'waiting_client']).count(),
            'resolved': user.created_tickets.filter(status='resolved').count(),
            'closed': user.created_tickets.filter(status__in=['closed', 'rejected']).count(),
        }
    elif user.is_agent():
        context['assigned_tickets'] = user.assigned_tickets.all()
        context['resolved_count'] = user.assigned_tickets.filter(status__in=['resolved', 'closed']).count()
    elif user.is_manager():
        # Згрупована статистика за статусами
        status_labels = dict(Ticket.Status.choices)
        raw_stats = Ticket.objects.values('status').annotate(total=Count('id'))
        context['status_stats'] = [
            {'label': status_labels.get(item['status'], item['status']), 'total': item['total']}
            for item in raw_stats
        ]
        # Кількість заявок на кожного агента
        context['agents_stats'] = User.objects.filter(role=User.Role.AGENT).annotate(
            total_assigned=Count('assigned_tickets')
        )
        
    return render(request, 'accounts/profile.html', context)