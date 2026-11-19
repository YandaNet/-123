from datetime import timedelta
from django.test import TestCase
from django.utils import timezone
from django.core.exceptions import ValidationError
from accounts.models import User
from .models import Ticket, Category

class TicketBusinessLogicTests(TestCase):
    def setUp(self):
        self.client_user = User.objects.create_user(username='client1', password='123', role='client')
        self.agent1 = User.objects.create_user(username='agent1', password='123', role='agent')
        self.agent2 = User.objects.create_user(username='agent2', password='123', role='agent')
        self.category = Category.objects.create(name='Технічна підтримка')

    def test_valid_and_invalid_status_transitions(self):
        ticket = Ticket.objects.create(title='Test', description='Desc', category=self.category, author=self.client_user)
        # З "Нова" не можна одразу в "Закрита"
        with self.assertRaises(ValidationError):
            ticket.change_status(Ticket.Status.CLOSED, self.agent1)

        # З "Нова" -> "В роботі" дозволено
        ticket.change_status(Ticket.Status.IN_PROGRESS, self.agent1)
        self.assertEqual(ticket.status, Ticket.Status.IN_PROGRESS)

    def test_reopen_within_3_days_rule(self):
        ticket = Ticket.objects.create(
            title='Resolved ticket',
            description='Desc',
            category=self.category,
            author=self.client_user,
            status=Ticket.Status.RESOLVED,
            resolved_at=timezone.now() - timedelta(days=4)
        )
        with self.assertRaises(ValidationError):
            ticket.change_status(Ticket.Status.IN_PROGRESS, self.client_user)

        ticket.change_status(Ticket.Status.CLOSED, self.client_user)
        self.assertEqual(ticket.status, Ticket.Status.CLOSED)

    def test_agent_cannot_process_own_ticket(self):
        ticket = Ticket.objects.create(title='Agent own', description='Desc', category=self.category, author=self.agent1)
        with self.assertRaises(ValidationError):
            ticket.change_status(Ticket.Status.IN_PROGRESS, self.agent1)