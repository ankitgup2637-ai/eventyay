import pytest
from decimal import Decimal
from django.core.exceptions import ValidationError
from rest_framework.exceptions import ValidationError as DRFValidationError
from django.core.validators import MinValueValidator, MaxValueValidator

from eventyay.control.forms.global_settings import GlobalSettingsForm
from eventyay.control.forms.event import EventWizardBasicsForm
from eventyay.control.forms.orders import EventCancelForm
from eventyay.base.configurations.default_setting import DEFAULT_SETTINGS
from eventyay.base.models import Voucher
from eventyay.api.serializers.order import OrderFeeCreateSerializer
from eventyay.api.serializers.voucher import VoucherSerializer

def validate_all(validators, value):
    errors = []
    for v in validators:
        try:
            v(value)
        except ValidationError as e:
            errors.append(e)
    if errors:
        raise ValidationError(errors)



def test_event_tax_rate_validators():
    field = EventWizardBasicsForm.base_fields['tax_rate']
    
    validate_all(field.validators, Decimal('0'))
    validate_all(field.validators, Decimal('100'))
    
    with pytest.raises(ValidationError):
        validate_all(field.validators, Decimal('-1'))
        
    with pytest.raises(ValidationError):
        validate_all(field.validators, Decimal('101'))

def test_event_cancel_keep_fee_percentage_validators():
    field = EventCancelForm.base_fields['keep_fee_percentage']
    
    validate_all(field.validators, Decimal('0'))
    validate_all(field.validators, Decimal('100'))
    
    with pytest.raises(ValidationError):
        validate_all(field.validators, Decimal('-1'))
        
    with pytest.raises(ValidationError):
        validate_all(field.validators, Decimal('101'))

def test_cancel_allow_user_paid_keep_percentage_validators():
    setting = DEFAULT_SETTINGS['cancel_allow_user_paid_keep_percentage']
    validators = setting['form_kwargs']['validators']
    
    validate_all(validators, Decimal('0'))
    validate_all(validators, Decimal('100'))
    
    with pytest.raises(ValidationError):
        validate_all(validators, Decimal('-1'))
        
    with pytest.raises(ValidationError):
        validate_all(validators, Decimal('101'))

def test_voucher_percentage_validation():
    from eventyay.base.models import Event
    mock_event = Event()
    # price_mode == 'percent'
    v = Voucher(code="TEST1", price_mode='percent', value=Decimal('0'))
    v.event = mock_event
    v.clean()  # should not raise
    
    v = Voucher(code="TEST2", price_mode='percent', value=Decimal('100'))
    v.event = mock_event
    v.clean()  # should not raise
    
    v = Voucher(code="TEST3", price_mode='percent', value=Decimal('-1'))
    v.event = mock_event
    with pytest.raises(ValidationError):
        v.clean()
        
    v = Voucher(code="TEST4", price_mode='percent', value=Decimal('101'))
    v.event = mock_event
    with pytest.raises(ValidationError):
        v.clean()
        
    # price_mode == 'set' (monetary)
    v = Voucher(code="TEST5", price_mode='set', value=Decimal('-1'))
    v.event = mock_event
    v.clean()
    v = Voucher(code="TEST6", price_mode='set', value=Decimal('101'))
    v.event = mock_event
    v.clean()
    
    # price_mode == 'subtract' (monetary)
    v = Voucher(code="TEST7", price_mode='subtract', value=Decimal('-1'))
    v.event = mock_event
    v.clean()
    v = Voucher(code="TEST8", price_mode='subtract', value=Decimal('101'))
    v.event = mock_event
    v.clean()

def test_order_fee_serializer_percentage_validation():
    serializer = OrderFeeCreateSerializer()
    
    # _treat_value_as_percentage == True
    serializer.validate({'_treat_value_as_percentage': True, 'value': Decimal('0')})
    serializer.validate({'_treat_value_as_percentage': True, 'value': Decimal('100')})
    
    with pytest.raises(DRFValidationError):
        serializer.validate({'_treat_value_as_percentage': True, 'value': Decimal('-1')})
        
    with pytest.raises(DRFValidationError):
        serializer.validate({'_treat_value_as_percentage': True, 'value': Decimal('101')})
        
    # _treat_value_as_percentage == False
    serializer.validate({'_treat_value_as_percentage': False, 'value': Decimal('-1')})
    serializer.validate({'_treat_value_as_percentage': False, 'value': Decimal('101')})

def test_voucher_serializer_percentage_validation():
    from unittest.mock import MagicMock
    serializer = VoucherSerializer()
    serializer.context['event'] = MagicMock(has_subevents=False)
    
    # Valid percentages
    serializer.validate({'price_mode': 'percent', 'value': Decimal('0')})
    serializer.validate({'price_mode': 'percent', 'value': Decimal('100')})
    
    with pytest.raises(DRFValidationError):
        serializer.validate({'price_mode': 'percent', 'value': Decimal('-1')})
        
    with pytest.raises(DRFValidationError):
        serializer.validate({'price_mode': 'percent', 'value': Decimal('101')})
        
    # Valid non-percentages
    serializer.validate({'price_mode': 'set', 'value': Decimal('-1')})
    serializer.validate({'price_mode': 'set', 'value': Decimal('101')})
