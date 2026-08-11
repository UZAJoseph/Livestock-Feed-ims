from django import forms
from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from .models import UserProfile, FeedType, Review
import re




class ReviewForm(forms.Form):
    comment = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Share your experience...'})
    )

    def save(self, user):
        return Review.objects.create(
            user=user,
            comment=self.cleaned_data['comment'],
        )



class RegisterForm(forms.Form):
    first_name = forms.CharField(
        max_length=150, required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'First name'})
    )
    last_name = forms.CharField(
        max_length=150, required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Last name'})
    )
    username = forms.CharField(
        max_length=150, required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Username'})
    )
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email'})
    )
    password1 = forms.CharField(
        min_length=8,
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Password'})
    )
    password2 = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Confirm password'})
    )
    telephone = forms.CharField(
        max_length=20, required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Telephone'})
    )
    district = forms.CharField(
        max_length=100, required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'District'})
    )
    sector = forms.CharField(
        max_length=100, required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Sector'})
    )
    cell = forms.CharField(
        max_length=100, required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Cell'})
    )
    village = forms.CharField(
        max_length=100, required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Village'})
    )
    terms = forms.BooleanField(
        required=True,
        error_messages={'required': 'You must agree to the Terms & Conditions.'},
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )

    def clean_username(self):
        username = self.cleaned_data['username'].strip()
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError("This username is already taken.")
        return username

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email

    def clean_telephone(self):
        raw = self.cleaned_data['telephone'].strip()
        # strip spaces, dashes, parentheses
        cleaned = re.sub(r'[\s\-()]', '', raw)

        # Accept 07XXXXXXXX (10 digits) or +2507XXXXXXXX / 2507XXXXXXXX
        local_pattern = r'^07[2-9]\d{7}$'
        intl_pattern = r'^(\+?250)7[2-9]\d{7}$'

        if re.match(local_pattern, cleaned):
            normalized = '+250' + cleaned[1:]  # 0788123456 -> +250788123456
        elif re.match(intl_pattern, cleaned):
            digits = cleaned.lstrip('+')
            normalized = '+' + digits
        else:
            raise forms.ValidationError(
                "Enter a valid Rwandan phone number, e.g. 0788123456 or +250788123456."
            )

        if UserProfile.objects.filter(telephone=normalized).exists():
            raise forms.ValidationError("An account with this telephone number already exists.")

        return normalized

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get('password1')
        password2 = cleaned_data.get('password2')
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("Passwords do not match.")
        return cleaned_data

    def save(self):
        data = self.cleaned_data
        user = User.objects.create_user(
            username=data['username'],
            email=data['email'],
            first_name=data['first_name'],
            last_name=data.get('last_name', ''),
            password=data['password1'],
        )
        UserProfile.objects.create(
            user=user,
            telephone=data['telephone'],
            district=data['district'],
            sector=data['sector'],
            cell=data['cell'],
            village=data['village'],
        )
        return user


class LoginForm(forms.Form):
    identifier = forms.CharField(
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Email or Telephone'})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Enter your password'})
    )

    @staticmethod
    def _normalize_phone(value):
        """Returns normalized +250 phone string if value looks like a phone number, else None."""
        cleaned = re.sub(r'[\s\-()]', '', value)
        if re.match(r'^07[2-9]\d{7}$', cleaned):
            return '+250' + cleaned[1:]
        if re.match(r'^2507[2-9]\d{7}$', cleaned):
            return '+' + cleaned
        if re.match(r'^\+2507[2-9]\d{7}$', cleaned):
            return cleaned
        return None

    def clean(self):
        cleaned_data = super().clean()
        identifier = cleaned_data.get('identifier', '').strip()
        password = cleaned_data.get('password')

        if identifier and password:
            try:
                if '@' in identifier:
                    user_obj = User.objects.get(email__iexact=identifier)
                else:
                    normalized_phone = self._normalize_phone(identifier)
                    if normalized_phone is None:
                        raise forms.ValidationError("Invalid email/telephone or password.")
                    user_obj = User.objects.get(profile__telephone=normalized_phone)
            except User.DoesNotExist:
                raise forms.ValidationError("Invalid email/telephone or password.")
            except User.MultipleObjectsReturned:
                raise forms.ValidationError("Multiple accounts share this identifier. Contact support.")

            user = authenticate(username=user_obj.username, password=password)
            if user is None:
                raise forms.ValidationError("Invalid email/telephone or password.")
            cleaned_data['user'] = user

        return cleaned_data