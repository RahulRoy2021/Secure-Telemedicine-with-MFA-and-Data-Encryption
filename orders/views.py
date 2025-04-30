# orders/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import MedicineOrderForm # Form import is correct
from .models import MedicineOrder
# --- Imports for PDF generation ---
from django.http import HttpResponse
from django.template.loader import get_template
from xhtml2pdf import pisa # From the installed library
from io import BytesIO # To handle PDF in memory
# --------------------------------
@login_required
def create_medicine_order(request):
    if not request.user.is_doctor:
         messages.error(request, "You do not have permission to create medicine orders.")
         return redirect('home')

    if request.method == 'POST':
        # --- Pass the doctor user to the form ---
        form = MedicineOrderForm(request.POST, user=request.user)
        # --------------------------------------
        if form.is_valid():
            order = form.save(commit=False)
            order.doctor = request.user # Still assign doctor explicitly before final save
            order.save()
            messages.success(request, f"Medicine order created successfully for patient {order.patient.username}.")
            return redirect('home') # TODO: Redirect appropriately
        else:
             messages.error(request, "Please correct the errors below.")
    else:
        # --- Pass the doctor user to the form ---
        form = MedicineOrderForm(user=request.user)
        # --------------------------------------

    context = {'form': form}
    return render(request, 'orders/create_order.html', context)
@login_required
def view_medicine_orders(request):
    """
    Displays a list of medicine orders received by the logged-in patient.
    """
    # Ensure only patients can access this view
    if not request.user.is_patient:
         messages.error(request, "Only patients can view medicine orders.")
         return redirect('home')

    # Fetch orders where the logged-in user is the patient
    orders = MedicineOrder.objects.filter(patient=request.user).order_by('-created_at') # Show newest first

    context = {
        'orders': orders
    }
    # Create this template next
    return render(request, 'orders/order_list.html', context)
@login_required
def download_order_pdf(request, order_id):
    """
    Generates and serves a PDF version of a specific MedicineOrder
    for the logged-in patient.
    """
    # 1. Get the order, ensuring it belongs to the logged-in patient
    order = get_object_or_404(MedicineOrder, pk=order_id, patient=request.user)

    # 2. Load the HTML template for the PDF
    template_path = 'orders/order_pdf_template.html'
    template = get_template(template_path)

    # 3. Define context data for the template
    context = {'order': order}

    # 4. Render HTML to String
    html_string = template.render(context)

    # 5. Create PDF in memory
    result_buffer = BytesIO() # In-memory binary buffer

    # Use pisa to convert HTML to PDF, writing to the buffer
    # Ensure encoding is UTF-8 for pisa
    pdf_status = pisa.CreatePDF(
        html_string.encode('utf-8'), # Source HTML string encoded
        dest=result_buffer,
        encoding='utf-8'
    )

    # Check for errors during PDF creation
    if pdf_status.err:
        messages.error(request, f"Error generating PDF: {pdf_status.err}")
        return HttpResponse("Error generating PDF", status=500)

    # 6. Create the HTTP response with PDF content
    response = HttpResponse(result_buffer.getvalue(), content_type='application/pdf')
    # Suggest a filename for the download
    filename = f"Medicine_Order_{order.pk}_{order.patient.username}_{order.created_at.strftime('%Y%m%d')}.pdf"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    return response
@login_required
def view_issued_orders(request):
    """
    Displays a list of medicine orders created by the logged-in doctor.
    """
    # Ensure only doctors can access this view
    if not request.user.is_doctor:
         messages.error(request, "Only doctors can view issued medicine orders.")
         return redirect('home')

    # Fetch orders where the logged-in user is the doctor
    # Also fetch related patient info to display username efficiently
    issued_orders = MedicineOrder.objects.filter(
        doctor=request.user
    ).select_related('patient').order_by('-created_at') # Show newest first

    context = {
        'issued_orders': issued_orders
    }
    # Create this template next
    return render(request, 'orders/doctor_order_list.html', context)
