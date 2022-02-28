from dateutil.parser import parse
import re

from django.core.exceptions import ValidationError

from .parsers import MetadataParser


class MetadataValidator(MetadataParser):
    _registry = []

    def validate(self, input_data):
        try:
            self.execute(input_data)
        except Exception as exception:
            raise ValidationError(exception)


class DateAndTimeValidator(MetadataValidator):
    def execute(self, input_data):
        return parse(input_data).isoformat()


class DateValidator(MetadataValidator):
    def execute(self, input_data):
        return parse(input_data).date().isoformat()


# class TimeValidator(MetadataValidator):
#     def execute(self, input_data):
#         return parse(input_data).time().isoformat()

# this is => PhoneNumbervalidator class
class TimeValidator(MetadataValidator):
    def execute(self, input_data):
        rule = re.compile(r'(^[+]{1})*([0-9]{12,14}$)')
        if not rule.search(input_data):
            raise ValidationError("Phone Number must start with '+' and have atleast 13 characters.")
        return input_data


MetadataValidator.register(parser=DateAndTimeValidator)
MetadataValidator.register(parser=DateValidator)
MetadataValidator.register(parser=TimeValidator)
# MetadataValidator.register(parser=PhoneNumbervalidator)
