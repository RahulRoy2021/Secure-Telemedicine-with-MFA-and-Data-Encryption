# medical_records/forms.py
from django import forms
from .models import MedicalRecord

class MedicalRecordForm(forms.ModelForm):
    class Meta:
        model = MedicalRecord
        # Include all fields the user should edit/see in the form
        # Make sure 'record_date' is here if it should be editable/visible
        fields = ['diagnosis', 'prescription', 'test_results', 'attached_file', 'description', 'record_date']
        labels = {
            'diagnosis': 'Diagnosis',
            'prescription': 'Prescription',
            'test_results': 'Test Results',
            'description': 'Description',
            'record_date': 'Record Date' # Added label
        }
        # Optional: Use a date picker widget for the date field
        widgets = {
            'record_date': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        # Pop the instance before it's passed to the parent __init__
        # We'll use it but won't let super automatically map its encrypted fields initially
        instance = kwargs.get('instance', None)
        initial_data = {} # Prepare a dictionary for initial values

        if instance:
            # If we are editing an existing record, decrypt its data
            decrypted_data = instance.get_decrypted_data()
            initial_data['diagnosis'] = decrypted_data.get('diagnosis')
            initial_data['prescription'] = decrypted_data.get('prescription')
            initial_data['test_results'] = decrypted_data.get('test_results')

            # You might want to pre-fill non-encrypted fields too, although
            # passing the instance to super later often handles this.
            # But being explicit can sometimes help.
            initial_data['description'] = instance.description
            initial_data['record_date'] = instance.record_date
            # NOTE: Don't put file fields like 'attached_file' in 'initial'

        # Update the 'initial' dictionary in kwargs *before* calling super()
        # This merges any initial data passed to the form with our decrypted data.
        # Use update to preserve any initial data passed in kwargs.
        current_initial = kwargs.get('initial', {})
        current_initial.update(initial_data)
        kwargs['initial'] = current_initial

        # Now, call the parent __init__ method.
        # We still pass the instance so the form knows it's updating an existing object upon save.
        super().__init__(*args, **kwargs)

        # Ensure record_date is required if necessary (ModelForm might make it optional otherwise)
        # Do this *after* super().__init__
        if 'record_date' in self.fields:
             self.fields['record_date'].required = True