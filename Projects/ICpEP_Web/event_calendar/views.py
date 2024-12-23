from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import Event, Participation
from accounts.models import CustomUser
from .forms import EventForm
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
from django.utils import timezone
from accounts.decorators import role_required
from django.contrib.auth.decorators import login_required
from .forms import EventForm, AttendanceSpanForm

# Admin Dashboard for Event Management
from datetime import datetime

@login_required
@role_required('admin')
def admin_calendar(request):
    events = Event.objects.all()
    now = datetime.now()
    
    event_data = []
    for event in events:
        attendance_span = AttendanceSpan.objects.filter(event=event).first()
        qr_button_state = "disabled"
        qr_message = "Attendance start time is not yet started."
        
        if attendance_span:
            start = datetime.combine(attendance_span.start_date, attendance_span.start_time)
            end = datetime.combine(attendance_span.end_date, attendance_span.end_time)
            
            if start <= now <= end:
                qr_button_state = "enabled"
                qr_message = ""
            elif now > end:
                qr_button_state = "disabled"
                qr_message = "Attendance has already ended."
        
        event_data.append({
            'event': event,
            'qr_button_state': qr_button_state,
            'qr_message': qr_message,
        })
    
    return render(request, 'event_calendar/admin/admin_calendar.html', {
        'events': event_data,
    })

# Create a new event
@login_required
@role_required('admin')
def create_event(request):
    if request.method == 'POST':
        event_form = EventForm(request.POST)
        attendance_form = AttendanceSpanForm(request.POST)

        needs_attendance = 'needs_attendance' in request.POST and request.POST['needs_attendance'] == 'on'

        # Validate forms
        event_valid = event_form.is_valid()
        attendance_valid = attendance_form.is_valid() if needs_attendance else True

        if event_valid and attendance_valid:
            # Save the event
            event = event_form.save()

            # Save attendance span if needed
            if needs_attendance:
                attendance_span = attendance_form.save(commit=False)
                attendance_span.event = event
                attendance_span.save()

            messages.success(request, 'Event created successfully!')
            return redirect('event_calendar:admin_calendar')

        # Debugging errors (optional)
        print(event_form.errors)
        if needs_attendance:
            print(attendance_form.errors)

    else:
        event_form = EventForm()
        attendance_form = AttendanceSpanForm()

    return render(request, 'event_calendar/admin/event_form.html', {
        'event_form': event_form,
        'attendance_form': attendance_form
    })





# Edit an existing event
@login_required
@role_required('admin')
def edit_event(request, event_id):
    event = get_object_or_404(Event, event_id=event_id)
    attendance_span = AttendanceSpan.objects.filter(event=event).first()

    if request.method == 'POST':
        event_form = EventForm(request.POST, instance=event)
        attendance_form = AttendanceSpanForm(request.POST, instance=attendance_span)

        needs_attendance = 'needs_attendance' in request.POST and request.POST['needs_attendance'] == 'on'

        event_valid = event_form.is_valid()
        attendance_valid = attendance_form.is_valid() if needs_attendance else True

        if event_valid and attendance_valid:
            event = event_form.save()

            if needs_attendance:
                attendance_span = attendance_form.save(commit=False)
                attendance_span.event = event
                attendance_span.save()
            elif attendance_span:
                attendance_span.delete()

            messages.success(request, 'Event updated successfully!')
            return redirect('event_calendar:admin_calendar')

    else:
        event_form = EventForm(instance=event)
        attendance_form = AttendanceSpanForm(instance=attendance_span) if attendance_span else AttendanceSpanForm()

    return render(request, 'event_calendar/admin/event_form.html', {
        'event_form': event_form,
        'attendance_form': attendance_form,
        'event': event,
    })


# Delete an event
@login_required
@role_required('admin')
def delete_event(request, event_id):
    event = get_object_or_404(Event, event_id=event_id)
    event.delete()
    messages.success(request, 'Event deleted successfully!')
    return redirect('event_calendar:admin_calendar')

# View participants of a specific event
@login_required
@role_required('admin')
def view_participants(request, event_id):
    event = get_object_or_404(Event, event_id=event_id)
    participants = Participation.objects.filter(event_id=event)
    return render(request, 'event_calendar/admin/view_participants.html', {'event': event, 'participants': participants})


from django.shortcuts import render, get_object_or_404
from django.utils.timezone import now
from .models import Event, AttendanceSpan, Participation
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse

# List all events
from django.db.models import Q

@login_required
@role_required('student')
def student_calendar(request):
    query = request.GET.get('q')  # Retrieve the search query from the GET parameters
    if query:
        # Filter events based on the search query (case-insensitive)
        events = Event.objects.filter(
            Q(event_name__icontains=query) |
            Q(event_subhead__icontains=query) |
            Q(event_tag__icontains=query)
        )
    else:
        events = Event.objects.all()  # Return all events if no search query
    
    return render(request, 'event_calendar/student/student_calendar.html', {
        'events': events,
        'query': query,  # Pass the query back to the template for displaying in the search bar
    })


# View event details
@login_required
@role_required('student')
def event_details(request, event_id):
    event = get_object_or_404(Event, event_id=event_id)

    # Fetch Attendance Span for the event
    attendance_span = AttendanceSpan.objects.filter(event=event).first()

    # Check if the current time falls within the attendance span
    current_time = localtime(now())  # Ensure timezone-aware comparison
    attendance_open = False  # Default to false
    if attendance_span:
        attendance_open = (
            attendance_span.start_date <= current_time.date() <= attendance_span.end_date and
            (
                (current_time.date() == attendance_span.start_date and current_time.time() >= attendance_span.start_time) or
                (current_time.date() == attendance_span.end_date and current_time.time() <= attendance_span.end_time) or
                (attendance_span.start_date < current_time.date() < attendance_span.end_date)
            )
        )

    # Determine participation status
    participated = Participation.objects.filter(user=request.user, event=event, event_state='Present').exists()

    # Retrieve needs_attendance from the Event model
    need_attendance = event.needs_attendance

    context = {
        'event': event,
        'attendance_span': attendance_span,
        'attendance_open': attendance_open,
        'participated': participated,
        'need_attendance': need_attendance,
    }
    return render(request, 'event_calendar/student/event_details.html', context)




from .models import ScanData
from django.http import JsonResponse
from django.shortcuts import render
from django.http import JsonResponse
from django.shortcuts import render
from accounts.models import CustomUser
from .models import ScanData  # Assuming ScanData is your model for storing scans


from django.shortcuts import render
from django.http import JsonResponse
from .models import CustomUser
from .models import Event, Participation


import json
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from .models import Event, CustomUser, Participation
from django.utils import timezone

from django.utils.timezone import localtime, now

@login_required
@csrf_exempt
def qr_scanner(request, event_id):
    event = get_object_or_404(Event, event_id=event_id)

    if request.method == "POST":
        try:
            scanned_text = request.POST.get('scanned_text')
            user = CustomUser.objects.filter(membership_id=scanned_text).first()

            if user:
                participation = Participation.objects.filter(user=user, event=event).first()
                current_time = localtime(now())  # Get time in local timezone

                if not participation:
                    participation = Participation.objects.create(
                        user=user,
                        event=event,
                        admin=request.user,
                        event_state='Present',
                        time_in=current_time,  # Save current time for time_in
                    )
                    message = "Time-in recorded successfully!"
                else:
                    if participation.time_out is None:
                        participation.time_out = current_time  # Save current time for time_out
                        participation.save()
                        message = "Time-out recorded successfully!"
                    else:
                        message = "Attendance already completed!"

                return JsonResponse({
                    'found': True,
                    'name': f"{user.given_name} {user.last_name}",
                    'event_name': event.event_name,
                    'message': message,
                    'time_in': participation.time_in.strftime('%I:%M %p'),  # Format for display
                    'time_out': participation.time_out.strftime('%I:%M %p') if participation.time_out else "Not yet recorded",
                })

            return JsonResponse({'found': False, 'message': 'Student ID not found in the database.'})

        except Exception as e:
            return JsonResponse({"success": False, "message": f"An error occurred: {str(e)}"})

    return render(request, 'event_calendar/admin/scan_qr_code.html', {'event': event})