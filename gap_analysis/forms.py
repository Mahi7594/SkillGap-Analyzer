from django import forms
from django.forms import formset_factory, BaseFormSet
from .models import RoleMatrix, SkillBenchmark, SkillMatrix, EmployeeSkill, Skill

class BootstrapFormMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs['class'] = 'form-check-input'
            elif isinstance(field.widget, forms.Select):
                field.widget.attrs['class'] = 'form-select'
            else:
                field.widget.attrs['class'] = 'form-control'

class SkillForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Skill
        fields = ['name', 'category', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'Enter skill name'}),
            'description': forms.Textarea(attrs={'rows': 2, 'placeholder': 'Optional description'}),
        }

class RoleMatrixForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = RoleMatrix
        fields = ['title', 'department', 'description']
        widgets = {
            'title': forms.TextInput(attrs={'placeholder': 'e.g., Software Engineer'}),
            'department': forms.TextInput(attrs={'placeholder': 'e.g., Engineering'}),
            'description': forms.Textarea(attrs={'rows': 2, 'placeholder': 'Optional description'}),
        }

class SkillBenchmarkForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = SkillBenchmark
        fields = ['role_matrix', 'skill', 'required_level', 'is_mandatory']
        widgets = {
            'required_level': forms.NumberInput(attrs={'min': 0, 'max': 5}),
        }

class RoleMatrixBenchmarkForm(BootstrapFormMixin, forms.ModelForm):
    skill_name = forms.CharField(
        label='Skill Name',
        required=True,
        widget=forms.TextInput(attrs={'placeholder': 'Enter or select skill name'})
    )
    skill_category = forms.ChoiceField(
        label='Category',
        required=False,
        choices=[('', 'Select Category')] + list(Skill.CATEGORY_CHOICES)
    )
    
    class Meta:
        model = SkillBenchmark
        fields = ['skill_name', 'skill_category', 'required_level']
        widgets = {
            'required_level': forms.NumberInput(attrs={'min': 0, 'max': 5, 'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['skill_name'].widget.attrs['list'] = 'skill-suggestions'
        # Set field order
        self.order_fields(['skill_name', 'skill_category', 'required_level'])
    
    def clean(self):
        cleaned_data = super().clean()
        skill_name = cleaned_data.get('skill_name', '').strip()
        skill_category = cleaned_data.get('skill_category', '')
        
        if skill_name:
            skill, created = Skill.objects.get_or_create(
                name__iexact=skill_name,
                defaults={'name': skill_name, 'category': skill_category if skill_category else None}
            )
            cleaned_data['skill'] = skill
        
        return cleaned_data

class SkillMatrixForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = SkillMatrix
        fields = ['name', 'email', 'role_matrix', 'status', 'join_date']
        labels = {
            'role_matrix': 'Designation',
        }
        widgets = {
            'join_date': forms.DateInput(attrs={'type': 'date'}),
            'email': forms.EmailInput(attrs={'placeholder': 'email@example.com'}),
        }

class EmployeeSkillForm(forms.ModelForm):
    class Meta:
        model = EmployeeSkill
        fields = ['actual_level', 'notes']
        widgets = {
            'actual_level': forms.NumberInput(attrs={'min': 0, 'max': 5, 'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'rows': 2, 'class': 'form-control', 'placeholder': 'Optional notes'}),
        }

class EmployeeSkillInlineForm(forms.ModelForm):
    skill_name = forms.CharField(widget=forms.HiddenInput())
    skill_id = forms.IntegerField(widget=forms.HiddenInput())
    benchmark_id = forms.IntegerField(widget=forms.HiddenInput(), required=False)
    required_level = forms.IntegerField(
        widget=forms.NumberInput(attrs={'min': 0, 'max': 5, 'class': 'form-control', 'readonly': 'readonly'})
    )
    
    class Meta:
        model = EmployeeSkill
        fields = ['actual_level', 'notes']
        widgets = {
            'actual_level': forms.NumberInput(attrs={'min': 0, 'max': 5, 'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'rows': 1, 'class': 'form-control', 'placeholder': 'Notes'}),
        }

class EmployeeSkillInlineFormSet(BaseFormSet):
    def __init__(self, *args, **kwargs):
        self.skill_matrix = kwargs.pop('skill_matrix', None)
        super().__init__(*args, **kwargs)
    
    def save(self, commit=True):
        instances = []
        for form in self.forms:
            if form.cleaned_data:
                skill_id = form.cleaned_data.get('skill_id')
                actual_level = form.cleaned_data.get('actual_level', 0)
                notes = form.cleaned_data.get('notes', '')
                
                if skill_id:
                    skill = Skill.objects.get(id=skill_id)
                    emp_skill, created = EmployeeSkill.objects.update_or_create(
                        skill_matrix=self.skill_matrix,
                        skill=skill,
                        defaults={'actual_level': actual_level, 'notes': notes}
                    )
                    instances.append(emp_skill)
        return instances

EmployeeSkillFormSet = formset_factory(
    EmployeeSkillForm,
    extra=0,
    can_delete=True
)

EmployeeSkillInlineFormSet = forms.formset_factory(
    EmployeeSkillForm,
    extra=0,
    can_delete=True
)
