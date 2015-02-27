from django.contrib.auth import get_user_model
from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers

from user_management.utils.validators import validate_password_strength


User = get_user_model()


class ValidateEmailMixin(object):
    def validate_email(self, value):
        email = value.lower()

        try:
            User.objects.get_by_natural_key(email)
        except User.DoesNotExist:
            return email
        else:
            msg = _('That email address has already been registered.')
            raise serializers.ValidationError(msg)


class EmailSerializerBase(serializers.Serializer):
    """Serializer defining a read-only `email` field."""
    email = serializers.EmailField(max_length=511, label=_('Email address'))

    class Meta:
        fields = ['email']


class RegistrationSerializer(ValidateEmailMixin, serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True,
        min_length=8,
        label=_('Password'),
        validators=[validate_password_strength],
    )
    password2 = serializers.CharField(
        write_only=True,
        min_length=8,
        label=_('Repeat password'),
    )

    class Meta:
        fields = ['name', 'email', 'password', 'password2']
        model = User

    def validate(self, attrs):
        password2 = attrs.pop('password2')
        if password2 != attrs.get('password'):
            msg = _('Your passwords do not match.')
            raise serializers.ValidationError({'password2': msg})
        return attrs

    def create(self, validated_data):
        return User.objects.create(**validated_data)


class PasswordChangeSerializer(serializers.ModelSerializer):
    old_password = serializers.CharField(
        write_only=True,
        label=_('Old password'),
    )
    new_password = serializers.CharField(
        write_only=True,
        min_length=8,
        label=_('New password'),
        validators=[validate_password_strength],
    )
    new_password2 = serializers.CharField(
        write_only=True,
        min_length=8,
        label=_('Repeat new password'),
    )

    class Meta:
        model = User
        fields = ('old_password', 'new_password', 'new_password2')

    def update(self, instance, validated_data):
        """Check the old password is valid and set the new password."""
        if not instance.check_password(validated_data['old_password']):
            msg = _('Invalid password.')
            raise serializers.ValidationError({'old_password': msg})

        instance.set_password(validated_data['new_password'])
        return instance

    def validate(self, attrs):
        if attrs.get('new_password') != attrs['new_password2']:
            msg = _('Your new passwords do not match.')
            raise serializers.ValidationError({'new_password2': msg})
        return attrs


class PasswordResetSerializer(serializers.ModelSerializer):
    new_password = serializers.CharField(
        write_only=True,
        min_length=8,
        label=_('New password'),
        validators=[validate_password_strength],
    )
    new_password2 = serializers.CharField(
        write_only=True,
        min_length=8,
        label=_('Repeat new password'),
    )

    class Meta:
        model = User
        fields = ('new_password', 'new_password2')

    def update(self, instance, validated_data):
        """Set the new password for the user."""
        instance.set_password(validated_data['new_password'])
        return instance

    def validate(self, attrs):
        if attrs.get('new_password') != attrs['new_password2']:
            msg = _('Your new passwords do not match.')
            raise serializers.ValidationError({'new_password2': msg})
        return attrs


class PasswordResetEmailSerializer(EmailSerializerBase):
    """Serializer defining an `email` field to reset password."""


class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('name', 'email', 'date_joined')
        read_only_fields = ('email', 'date_joined')


class ResendConfirmationEmailSerializer(EmailSerializerBase):
    """Serializer defining an `email` field to resend a confirmation email."""
    def validate_email(self, email):
        """
        Validate if email exists and requires a verification.

        `validate_email` will set a `user` attribute on the instance allowing
        the view to send an email confirmation.
        """
        try:
            self.user = User.objects.get_by_natural_key(email)
        except User.DoesNotExist:
            msg = _('A user with this email address does not exist.')
            raise serializers.ValidationError(msg)

        if not self.user.email_verification_required:
            msg = _('User email address is already verified.')
            raise serializers.ValidationError(msg)
        return email


class UserSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = User
        fields = ('url', 'name', 'email', 'date_joined')
        read_only_fields = ('email', 'date_joined')
        view_name = 'user_management_api:user_detail'


class UserSerializerCreate(ValidateEmailMixin, UserSerializer):
    class Meta(UserSerializer.Meta):
        read_only_fields = ('date_joined',)
