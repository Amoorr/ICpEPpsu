"""

views.py is responsible for handling the user requests and displaying the corresponding outputs. 

"""

from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from .forms import CustomUserCreationForm, AdminEditAccountForm, LoginForm
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from .decorators import role_required
from .models import CustomUser
from django.db.models import Q
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import update_session_auth_hash
from .forms import CustomUserCreationForm
from django.contrib import messages
from django.shortcuts import render
from event_calendar.models import Event
from news.models import NewsArticle
from accounts.models import CustomUser
from marketplace.models import *
from news.models import *
from event_calendar.models import *
from datetime import datetime
from django.shortcuts import render
from django.utils import timezone
from datetime import timedelta
from accounts.models import CustomUser
from marketplace.models import Product, Cart
from event_calendar.models import Event, Participation
from news.models import NewsArticle




# Student login view (default)
def student_login(request):
    """
    Login view for students. It is the default login page.
    Admins will be prevented from logging in here.
    """
    if request.user.is_authenticated:  # Check if the user is already logged in
        # Redirect to respective dashboard based on the user's role
        if request.user.role == 'admin':
            return redirect('admin_dashboard')
        elif request.user.role == 'superuser':
            return redirect('superuser_dashboard')
        else:
            return redirect('student_dashboard')

    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['username']
            password = form.cleaned_data['password']
            user = authenticate(request, username=email, password=password)
            if user is not None:
                if user.role == 'admin':
                    form.add_error(None, 'Admins should log in using the Admin login page.')
                    return render(request, 'accounts/student_login.html', {'form': form})
                login(request, user)
                return redirect('student_dashboard')  # Redirect student to their dashboard
            else:
                form.add_error(None, 'Invalid credentials')

    else:
        form = LoginForm()

    return render(request, 'accounts/student_login.html', {'form': form})


# Admin login view
def admin_login(request):
    """
    Login view for admins. Only admins can access this page.
    """
    if request.user.is_authenticated:  # Check if the user is already logged in
        # Redirect to respective dashboard based on the user's role
        if request.user.role == 'admin':
            return redirect('admin_dashboard')
        elif request.user.role == 'superuser':
            return redirect('superuser_dashboard')
        else:
            return redirect('student_dashboard')

    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['username']
            password = form.cleaned_data['password']
            user = authenticate(request, username=email, password=password)
            if user is not None and user.role == 'admin':  # Ensure only admin can log in here
                login(request, user)
                return redirect('admin_dashboard')
            else:
                form.add_error(None, 'Invalid credentials or not an admin account')

    else:
        form = LoginForm()

    return render(request, 'accounts/admin_login.html', {'form': form})


@login_required
@role_required(['admin', 'superuser'])
def register(request):
    """
    Function responsible for registering an account and adding it to the database.
    """

    popup_message = None  # Default: no message
    account_created = False  # Track if an account was created

    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            form.save()  # Save the new user to the database
            popup_message = 'Account created successfully!'
            form = CustomUserCreationForm()  # Clear the form for the next entry
        else:
            # Aggregate errors into a single message for the pop-up
            error_list = []
            for field, errors in form.errors.items():
                for error in errors:
                    error_list.append(f"{field.capitalize()}: {error}")
            popup_message = " ".join(error_list)  # Combine errors into one message
    else:
        form = CustomUserCreationForm()  # Display an empty form for GET requests

    return render(request, 'accounts/admin/register.html', {
        'form': form,
        'popup_message': popup_message,
    })


@login_required # Decorator where it is only accessed to logged-in users
def logout_view(request):
    """
    Responsible for logging out. Applicable to admins and students
    """
    logout(request)  # Logs out the user
    return redirect('student_login')  # Redirects to the login page


from event_calendar.models import Event  # Import the Event model
from datetime import date

from django.shortcuts import render
from event_calendar.models import Event
from news.models import NewsArticle
from datetime import date
from django.contrib.auth.decorators import login_required

@login_required
@role_required('student')  # Ensure only students can access this view
def student_dashboard(request):
    """
    Renders the student dashboard with the latest news articles and events
    """
    # Fetch the latest news articles (e.g., last 4 articles)
    latest_news = NewsArticle.objects.order_by('-publication_date')[:4]

    # Fetch the next 4 upcoming events (ordered by date and time)
    upcoming_events = Event.objects.filter(event_date__gte=date.today()).order_by('event_date', 'event_time')[:4]

    # Check if there are no upcoming events
    no_upcoming_events = not upcoming_events.exists()

    context = {
        'latest_news': latest_news,
        'upcoming_events': upcoming_events,
        'no_upcoming_events': no_upcoming_events,  # Pass the flag to the template
    }

    return render(request, 'accounts/student/student_dashboard.html', context)


@login_required
@role_required('admin')
def admin_dashboard(request):


    return render(request, 'accounts/admin/admin_dashboard.html') 



@login_required
@role_required('student')
def about_us(request):
    return render(request, 'accounts/student/about_us.html')

@login_required
@role_required('student')
def gallery(request):
     return render(request, 'accounts/student/gallery.html')



@login_required
@role_required(['admin', 'superuser'])
def admin_accounts(request):
    return render(request, 'accounts/admin/admin_accounts.html')

from django.contrib.auth import get_user_model
from django.contrib import messages

@login_required 
@role_required(['admin', 'superuser'])
def admin_list(request):
    users = CustomUser.objects.exclude(role='superuser')
    
    # Search
    search_term = request.GET.get('search', '')
    if search_term:
        users = users.filter(
            Q(given_name__icontains=search_term) |
            Q(last_name__icontains=search_term) |
            Q(student_id__icontains=search_term)
        )
    
    # Filter by role
    role_filter = request.GET.get('role', '')
    if role_filter:
        users = users.filter(role=role_filter)
    
    # Filter by academic year (ensure it's numeric before applying)
    acad_year_filter = request.GET.get('acad_year', '').strip()
    if acad_year_filter.isdigit():
        users = users.filter(acad_year=int(acad_year_filter))
    
    # Filter by academic block
    acad_block_filter = request.GET.get('acad_block', '').strip()
    if acad_block_filter:
        users = users.filter(acad_block=acad_block_filter)

    # Choices for filtering
    acad_year_choices = CustomUser.objects.values_list('acad_year', flat=True).distinct().order_by('acad_year')
    acad_block_choices = CustomUser.objects.values_list('acad_block', flat=True).distinct().order_by('acad_block')
    roles = CustomUser.objects.values_list('role', flat=True).distinct()

    return render(request, 'accounts/admin/admin_list.html', {
        'users': users,
        'acad_year_choices': acad_year_choices,
        'acad_block_choices': acad_block_choices,
        'roles': roles,  # Corrected variable name for clarity
    })


# Admin view to reset password
@login_required
@role_required(['admin', 'superuser'])
def reset_password(request, user_id):
    user = get_user_model().objects.get(id=user_id)
    user.set_password(user.membership_id)  # Set password to the user's membership ID
    user.save()
    messages.success(request, f'Password for {user.given_name} {user.last_name} has been reset to default.')
    return redirect('admin_list')  # Redirect back to the admin accounts list

@login_required
def change_password(request):
    """
    Handle the password change process for students and admins.
    """
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            form.save()
            update_session_auth_hash(request, form.user)  # Keep the user logged in after password change
            messages.success(request, 'Your password was successfully updated!')
            return redirect('admin_list')  # Redirect to the admin list after successful change
        else:
            messages.error(request, 'Please correct the error below.')
    else:
        form = PasswordChangeForm(request.user)

    return render(request, 'accounts/change_password.html', {'form': form})


@login_required
@role_required(['admin', 'superuser'])
def admin_delete_account(request, user_id):
    user = get_object_or_404(CustomUser, id=user_id)
    
    # Prevent deleting yourself or admins if needed
    if user == request.user:
        messages.error(request, "You cannot delete your own account or admin accounts.")
        return redirect('admin_list')  # Redirect back to the account list
    
    if user.role == 'superuser' and request.user.role != 'superuser':
        messages.error(request, "You do not have permission to edit the superuser account.")
        return redirect('admin_list')

    if user.role == 'superuser':
        messages.error(request, "The main superuser account cannot be deleted.")
        return redirect('admin_list')


    user.delete()
    messages.success(request, f"Account for {user.given_name} {user.last_name} has been deleted.")
    return redirect('admin_list')


from django.shortcuts import render, redirect
from django.contrib import messages

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from .forms import AdminEditAccountForm
from .models import CustomUser

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from .forms import AdminEditAccountForm
from .models import CustomUser

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from .forms import AdminEditAccountForm
from .models import CustomUser

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from .forms import AdminEditAccountForm
from .models import CustomUser

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from .forms import AdminEditAccountForm
from .models import CustomUser

from django.http import HttpResponseRedirect

def admin_edit_account(request, user_id):
    user = get_object_or_404(CustomUser, id=user_id)

    if request.method == "POST":
        form = AdminEditAccountForm(request.POST, instance=user)
        if form.is_valid():
            form.save()

            # Redirect with a success message in the query string
            return HttpResponseRedirect(f"{request.path}?success=true")
    else:
        form = AdminEditAccountForm(instance=user)

    # Check for a success query parameter
    popup_message = "Changes applied successfully!" if request.GET.get('success') else None

    return render(request, 'accounts/admin/admin_edit_account.html', {
        'form': form,
        'user': user,
        'popup_message': popup_message,
    })


@login_required
@role_required('superuser')
def superuser_dashboard(request):
    return render(request, 'accounts/superuser/superuser_dashboard.html')




