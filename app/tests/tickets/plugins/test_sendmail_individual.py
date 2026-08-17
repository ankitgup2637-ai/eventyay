import pytest
from django.core.exceptions import ValidationError
from django.test import RequestFactory
from django.utils.timezone import now
from django.contrib.sessions.backends.db import SessionStore
from django.contrib.messages.storage.fallback import FallbackStorage

from eventyay.base.models import Event, Organizer, User, Team, Product, Order, OrderPosition
from eventyay.plugins.sendmail.forms import MailForm
from eventyay.plugins.sendmail.models import EmailQueue, EmailQueueFilter, EmailQueueToUser, Recipients
from eventyay.plugins.sendmail.views import SenderView
from unittest.mock import patch


@pytest.fixture
def rf():
    return RequestFactory()


@pytest.fixture
def organizer():
    return Organizer.objects.create(name='Dummy', slug='dummy')


@pytest.fixture
def event(organizer):
    e = Event.objects.create(
        organizer=organizer, name='Dummy', slug='dummy',
        date_from=now(), plugins='eventyay.plugins.sendmail'
    )
    return e


@pytest.fixture
def user():
    return User.objects.create_superuser('dummy@dummy.dummy', 'dummy')


@pytest.fixture
def order(event):
    return Order.objects.create(
        code='DUMMY', event=event, email='dummy@dummy.test',
        status=Order.STATUS_PAID, datetime=now(), expires=now(),
        total=13
    )


@pytest.fixture
def product(event):
    return Product.objects.create(event=event, name='Test item', default_price=13)


@pytest.fixture
def pos(order, product):
    return OrderPosition.objects.create(order=order, product=product, price=13, attendee_email="attendee@dummy.test")


@pytest.mark.django_db
def test_sendmail_individual_validation(event, pos):
    """Test that attendee is required when individual recipient is selected."""
    form = MailForm(
        data={
            'sendto': 'na',
            'recipients': 'individual',
            'subject_0': 'Test',
            'message_0': 'Test message',
            'order_status': ['p'],
            'products': [pos.product.pk],
        },
        event=event
    )
    assert not form.is_valid()
    assert 'attendee' in form.errors

    form = MailForm(
        data={
            'sendto': 'na',
            'recipients': 'individual',
            'attendee': pos.pk,
            'subject_0': 'Test',
            'message_0': 'Test message',
            'order_status': ['p'],
            'products': [pos.product.pk],
        },
        event=event
    )
    assert form.is_valid(), form.errors


@pytest.mark.django_db
def test_sendmail_individual_recipient_isolation(event, user, order, pos, product):
    """Test that sending to individual attendee isolates the recipient correctly."""
    # Add a second position to the same order to ensure isolation
    pos2 = OrderPosition.objects.create(order=order, product=product, price=13, attendee_email="other@dummy.test")

    qm = EmailQueue.objects.create(
        event=event,
        user=user,
        subject='Test subject',
        message='Test message',
    )
    filters = EmailQueueFilter.objects.create(
        mail=qm,
        recipients='individual',
        positions=[pos.pk],
    )

    qm.populate_to_users()

    users = list(EmailQueueToUser.objects.filter(mail=qm))
    assert len(users) == 1
    assert users[0].email == 'attendee@dummy.test'
    assert pos.pk in users[0].positions
    assert pos2.pk not in users[0].positions


@pytest.mark.django_db
@patch('eventyay.base.services.mail.mail')
def test_sendmail_test_email_action(mock_mail, rf, event, user, product):
    """Test that 'test' action sends email and does NOT create EmailQueue."""
    order = Order.objects.create(
        event=event,
        status=Order.STATUS_PAID,
        expires=now(),
        total=0,
    )
    pos = OrderPosition.objects.create(
        order=order,
        product=product,
        price=0,
        attendee_email="attendee@example.com",
    )

    request = rf.post('/dummy', {
        'action': 'test',
        'test_email': 'test@example.com',
        'sendto': 'na',
        'recipients': 'orders',
        'subject_0': 'Test subject',
        'message_0': 'Test message',
        'order_status': ['p'],
        'products': [product.pk],
    })
    request.user = user
    t = Team.objects.create(organizer=event.organizer, can_view_orders=True, can_change_orders=True)
    t.members.add(user)
    t.limit_events.add(event)
    request.event = event
    request.organizer = event.organizer
    request.session = SessionStore()
    request.session.save()
    request._messages = FallbackStorage(request)

    view = SenderView.as_view()
    response = view(request, event=event.slug, organizer=event.organizer.slug)

    # Should redirect or return success (redirects back to GET typically or renders)
    assert response.status_code in [200, 302]

    if response.status_code == 200:
        pass

    messages = list(request._messages)
    assert len(messages) == 1
    assert "Test email sent successfully." in str(messages[0])

    # Ensure NO EmailQueue was created for this action
    assert EmailQueue.objects.count() == 0
