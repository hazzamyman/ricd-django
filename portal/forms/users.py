from django import forms
from django.contrib.auth.models import User, Group
from ricd.models import Officer, UserProfile, Project


class UserCreationForm(forms.ModelForm):
    """Form for creating new users with group assignment"""

    password1 = forms.CharField(
        label='Password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter password'
        })
    )
    password2 = forms.CharField(
        label='Password confirmation',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Repeat password'
        })
    )
    groups = forms.ModelMultipleChoiceField(
        queryset=Group.objects.all(),
        required=False,
        widget=forms.SelectMultiple(attrs={
            'class': 'form-select'
        })
    )

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'is_active', 'is_staff']
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Username'
            }),
            'first_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'First name'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Last name'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'Email address'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'is_staff': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }

    def clean_password2(self):
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("Passwords don't match")
        return password2

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
            if self.cleaned_data.get('groups'):
                user.groups.set(self.cleaned_data['groups'])
        return user


class OfficerForm(forms.ModelForm):
    """Form for creating and editing Officers"""

    create_user = forms.BooleanField(
        required=False,
        label="Create new user account",
        initial=True,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        })
    )

    class Meta:
        model = Officer
        fields = ['user', 'position', 'is_principal', 'is_senior', 'is_active']
        widgets = {
            'user': forms.Select(attrs={
                'class': 'form-select'
            }),
            'position': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Official position title'
            }),
            'is_principal': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'is_senior': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }


class OfficerAssignmentForm(forms.Form):
    """Form for assigning officers to projects"""

    principal_officer = forms.ModelChoiceField(
        queryset=Officer.objects.filter(is_principal=True),
        widget=forms.Select(attrs={
            'class': 'form-select'
        }),
        required=False
    )
    senior_officer = forms.ModelChoiceField(
        queryset=Officer.objects.filter(is_senior=True),
        widget=forms.Select(attrs={
            'class': 'form-select'
        }),
        required=False
    )


class CouncilUserCreationForm(forms.ModelForm):
    """Form for creating new council users with role restrictions"""

    password1 = forms.CharField(
        label='Password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter password'
        })
    )
    password2 = forms.CharField(
        label='Password confirmation',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Repeat password'
        })
    )

    # Council selection for RICD users
    council = forms.ModelChoiceField(
        queryset=None,  # Will be set in __init__ based on user permissions
        required=False,
        label="Council",
        widget=forms.Select(attrs={
            'class': 'form-select'
        }),
        help_text="Select the council this user belongs to"
    )

    # Role choices restricted based on current user
    ROLE_CHOICES = [
        ('council_user', 'Council User'),
        ('council_manager', 'Council Manager'),
    ]

    role = forms.ChoiceField(
        choices=ROLE_CHOICES,
        label="User Role",
        widget=forms.Select(attrs={
            'class': 'form-select'
        }),
        help_text="Select the role for this council user"
    )

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'is_active']
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Username'
            }),
            'first_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'First name'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Last name'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'Email address'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }

    def __init__(self, council=None, user=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.council = council

        # Set council field behavior based on user permissions
        if user and user.groups.filter(name__in=['RICD Staff', 'RICD Manager']).exists():
            # RICD users can select council
            from ricd.models import Council
            self.fields['council'].queryset = Council.objects.all().order_by('name')
            self.fields['council'].required = True
            if council:
                # If council was passed, pre-select it
                self.fields['council'].initial = council
        else:
            # Council managers can't select council - it's fixed to their own
            self.fields['council'].widget = forms.HiddenInput()
            self.fields['council'].queryset = Council.objects.none()
            if council:
                self.fields['council'].initial = council
            # For council managers, council is always provided, so make it not required for form validation
            self.fields['council'].required = False

        # Restrict role choices based on current user permissions
        if user:
            user_council = getattr(user, 'council', None)
            if user_council and not user.groups.filter(name__in=['RICD Staff', 'RICD Manager']).exists():
                # Council Manager can only create Council User
                self.fields['role'].choices = [('council_user', 'Council User')]
                self.fields['role'].help_text = "As a Council Manager, you can only create Council User accounts."
                # For council managers, role is restricted to council_user only
                self.fields['role'].initial = 'council_user'
                self.fields['role'].required = True  # Make sure role is required
            elif user.groups.filter(name__in=['RICD Staff', 'RICD Manager']).exists():
                # RICD users can create both roles
                self.fields['role'].choices = self.ROLE_CHOICES
                self.fields['role'].help_text = "Select the appropriate role for this council user."

    def clean_password2(self):
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("Passwords don't match")
        return password2

    def clean(self):
        cleaned_data = super().clean()
        council = cleaned_data.get('council') or self.council

        # Ensure council is provided
        if not council:
            raise forms.ValidationError("A council must be selected for the user.")

        # Ensure council is in the form data for hidden fields
        if not cleaned_data.get('council') and self.council:
            cleaned_data['council'] = self.council

        return cleaned_data

    def clean_role(self):
        """Ensure role selection is valid for current user's permissions"""
        role = self.cleaned_data.get('role')
        if role and self.fields['role'].choices:
            # Check if the selected role is in the allowed choices
            allowed_roles = [choice[0] for choice in self.fields['role'].choices]
            if role not in allowed_roles:
                raise forms.ValidationError("You don't have permission to create users with this role.")
        elif not self.fields['role'].choices:
            raise forms.ValidationError("You don't have permission to create users with roles.")
        return role

    def save(self, commit=True):
        import logging
        from django.db import transaction
        logger = logging.getLogger(__name__)

        logger.info("=== COUNCIL USER CREATION FORM SAVE STARTED ===")
        logger.info(f"Form data - Username: {self.cleaned_data.get('username')}, Email: {self.cleaned_data.get('email')}")
        logger.info(f"Form council: {self.cleaned_data.get('council')}, Instance council: {self.council}")
        logger.info(f"Role: {self.cleaned_data.get('role')}, Commit: {commit}")

        user = super().save(commit=False)
        logger.info(f"User object created (not yet saved) - Username: {user.username}")

        # Set password
        password1 = self.cleaned_data.get("password1")
        if password1:
            user.set_password(password1)
            logger.info("Password set successfully")
        else:
            logger.warning("No password provided in form data")

        # Set user profile council - use form data if available, otherwise fall back to passed parameter
        council = self.cleaned_data.get('council') or self.council
        logger.info(f"Final council determined: {council}")

        if commit:
            try:
                logger.info("Starting atomic transaction for user creation")

                # Use atomic transaction to ensure all operations succeed or fail together
                with transaction.atomic():
                    logger.info("Transaction started - Saving user object")
                    # Save the user first
                    user.save()
                    logger.info(f"✅ User saved successfully - ID: {user.pk}, Username: {user.username}")

                    logger.info("Creating/updating UserProfile")
                    # Ensure UserProfile exists and is linked to council
                    profile, created = UserProfile.objects.get_or_create(
                        user=user,
                        defaults={'council': council}
                    )

                    if not created and profile.council != council:
                        logger.info(f"Profile exists but council differs - Old: {profile.council}, New: {council}")
                        # Update existing profile with new council
                        profile.council = council
                        profile.save()
                        logger.info(f"✅ UserProfile updated - Council: {council}")
                    elif created:
                        logger.info(f"✅ UserProfile created - Council: {council}")
                    else:
                        logger.info(f"UserProfile already exists with correct council: {council}")

                    logger.info("Clearing existing groups to prevent duplicates")
                    # Clear existing groups to prevent duplicates
                    user.groups.clear()

                    logger.info("Assigning groups based on role")
                    # Assign groups based on role
                    role = self.cleaned_data.get('role')
                    if role == 'council_user':
                        group, group_created = Group.objects.get_or_create(name='Council User')
                        user.groups.add(group)
                        logger.info(f"✅ Added Council User group (created: {group_created})")
                    elif role == 'council_manager':
                        group, group_created = Group.objects.get_or_create(name='Council Manager')
                        user.groups.add(group)
                        logger.info(f"✅ Added Council Manager group (created: {group_created})")
                    else:
                        logger.warning(f"Unknown role: {role}")

                    # Force refresh user groups from database
                    user.groups.through.objects.filter(user=user).exists()
                    final_groups = [g.name for g in user.groups.all()]
                    logger.info(f"✅ User creation completed successfully - Final groups: {final_groups}")
                    logger.info("=== COUNCIL USER CREATION FORM SAVE COMPLETED ===")

            except Exception as e:
                logger.error(f"❌ ERROR during user creation: {str(e)}")
                logger.error(f"Exception type: {type(e).__name__}")
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")
                # Re-raise the exception to ensure transaction rollback
                raise

        return user


class CouncilUserUpdateForm(forms.ModelForm):
    """Form for updating existing council users"""

    # Role choices restricted based on current user
    ROLE_CHOICES = [
        ('council_user', 'Council User'),
        ('council_manager', 'Council Manager'),
    ]

    role = forms.ChoiceField(
        choices=ROLE_CHOICES,
        label="User Role",
        widget=forms.Select(attrs={
            'class': 'form-select'
        }),
        help_text="Select the role for this council user"
    )

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'is_active']
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Username'
            }),
            'first_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'First name'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Last name'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'Email address'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }

    def __init__(self, council=None, user=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.council = council
        self.current_user = user

        # Set current user's role for display
        if self.instance and self.instance.pk:
            # Determine current role from groups
            if self.instance.groups.filter(name='Council Manager').exists():
                self.fields['role'].initial = 'council_manager'
            elif self.instance.groups.filter(name='Council User').exists():
                self.fields['role'].initial = 'council_user'

        # Restrict role choices based on current user permissions
        if user:
            user_council = getattr(user, 'council', None)
            if user_council and not user.groups.filter(name__in=['RICD Staff', 'RICD Manager']).exists():
                # Council Manager can only assign Council User role
                self.fields['role'].choices = [('council_user', 'Council User')]
                self.fields['role'].help_text = "As a Council Manager, you can only assign Council User role."
            elif user.groups.filter(name__in=['RICD Staff', 'RICD Manager']).exists():
                # RICD users can assign both roles
                self.fields['role'].choices = self.ROLE_CHOICES
                self.fields['role'].help_text = "Select the appropriate role for this council user."

    def clean_role(self):
        """Ensure role selection is valid for current user's permissions"""
        role = self.cleaned_data.get('role')
        if role and self.current_user:
            user_council = getattr(self.current_user, 'council', None)
            if user_council and not self.current_user.groups.filter(name__in=['RICD Staff', 'RICD Manager']).exists():
                if role != 'council_user':
                    raise forms.ValidationError("You don't have permission to assign this role.")
        return role

    def save(self, commit=True):
        import logging
        from django.db import transaction
        logger = logging.getLogger(__name__)

        logger.info("=== COUNCIL USER UPDATE FORM SAVE STARTED ===")
        logger.info(f"Updating user: {self.instance.username}, Role: {self.cleaned_data.get('role')}")

        user = super().save(commit=False)

        if commit:
            try:
                with transaction.atomic():
                    logger.info("Saving user object")
                    user.save()

                    # Update groups based on role
                    logger.info("Updating user groups")
                    user.groups.clear()  # Clear existing groups

                    role = self.cleaned_data.get('role')
                    if role == 'council_user':
                        group, _ = Group.objects.get_or_create(name='Council User')
                        user.groups.add(group)
                        logger.info("✅ Added Council User group")
                    elif role == 'council_manager':
                        group, _ = Group.objects.get_or_create(name='Council Manager')
                        user.groups.add(group)
                        logger.info("✅ Added Council Manager group")

                    # Ensure UserProfile exists and is linked to council
                    profile, created = UserProfile.objects.get_or_create(
                        user=user,
                        defaults={'council': self.council}
                    )

                    if not created and (profile.council != self.council or profile.council is None):
                        profile.council = self.council
                        profile.save()
                        logger.info(f"✅ Updated UserProfile council to: {self.council}")

                    logger.info("=== COUNCIL USER UPDATE FORM SAVE COMPLETED ===")

            except Exception as e:
                logger.error(f"❌ Error during user update: {str(e)}")
                raise

        return user