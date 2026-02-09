from django import forms
from .models import TimetableEntry

class TimetableEntryForm(forms.ModelForm):
    class Meta:
        model = TimetableEntry
        fields = [
            "day",
            "subject",
            "start_time",
            "end_time",
            "is_break",
        ]
        widgets = {
            "day": forms.Select(attrs={"class": "form-control"}),
            "subject": forms.TextInput(attrs={"class": "form-control"}),
            "start_time": forms.TimeInput(
                attrs={"type": "time", "class": "form-control"}
            ),
            "end_time": forms.TimeInput(
                attrs={"type": "time", "class": "form-control"}
            ),
            "is_break": forms.CheckboxInput(),
        }
