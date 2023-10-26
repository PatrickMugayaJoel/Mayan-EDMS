from django.conf import settings
from django.db import models
from django.utils.translation import ugettext_lazy as _

from .managers import UserOptionsManager


class UserOptions(models.Model):
    """
    This model stores administrative configurations for a user accounts.
    At the moment it stores a boolean flag to restrict a user's
    ability to change their password.
    """
    user = models.OneToOneField(
        on_delete=models.CASCADE, related_name='user_options',
        to=settings.AUTH_USER_MODEL, unique=True, verbose_name=_('User')
    )
    block_password_change = models.BooleanField(
        default=False,
        verbose_name=_('Forbid this user from changing their password.')
    )

    objects = UserOptionsManager()

    class Meta:
        verbose_name = _('User settings')
        verbose_name_plural = _('Users settings')

    def natural_key(self):
        return self.user.natural_key()
    natural_key.dependencies = [settings.AUTH_USER_MODEL]


class UserExtras(models.Model):
    """
    Model used to link a user to organizational information.
    """
    employee = models.CharField(
        primary_key=True,
        blank=True, db_index=True, help_text=_(
            'The employee.'
        ), max_length=255, verbose_name=_('employee')
    )
    company = models.CharField(
        blank=True, db_index=True, help_text=_(
            'The company.'
        ), max_length=255, null=True, verbose_name=_('company')
    )
    department = models.CharField(
        blank=True, db_index=True, help_text=_(
            'The department.'
        ), max_length=255, null=True, verbose_name=_('department')
    )
    supervisor = models.CharField(
        blank=True, db_index=True, help_text=_(
            'The supervisor.'
        ), max_length=255, null=True, verbose_name=_('supervisor')
    )

    class Meta:
        db_table = 'nic_employee'
        verbose_name = _('employee information')
        verbose_name_plural = _('employees information')

    def __str__(self):
        return force_text(s=self.employee)
