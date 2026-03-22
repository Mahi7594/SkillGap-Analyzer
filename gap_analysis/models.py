from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator

class Designation(models.Model):
    title = models.CharField(max_length=100)
    department = models.CharField(max_length=100, blank=True, null=True)
    
    def __str__(self):
        return self.title

class Skill(models.Model):
    name = models.CharField(max_length=100, unique=True)
    category = models.CharField(max_length=100, blank=True, null=True, help_text="e.g., Technical, Soft Skill, Leadership")

    def __str__(self):
        return self.name

class SkillBenchmark(models.Model):
    designation = models.ForeignKey(Designation, on_delete=models.CASCADE)
    skill = models.ForeignKey(Skill, on_delete=models.CASCADE, null=True)
    required_level = models.IntegerField(
        help_text="Scale of 1 to 5",
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )

    def __str__(self):
        return f"{self.designation} - {self.skill}"

    class Meta:
        unique_together = ('designation', 'skill')

class Employee(models.Model):
    name = models.CharField(max_length=100)
    designation = models.ForeignKey(Designation, on_delete=models.SET_NULL, null=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

class EmployeeSkill(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    skill = models.ForeignKey(Skill, on_delete=models.CASCADE, null=True)
    actual_level = models.IntegerField(
        help_text="Scale of 1 to 5",
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    last_evaluated = models.DateField(auto_now=True)

    def __str__(self):
        return f"{self.employee} - {self.skill}"

    class Meta:
        unique_together = ('employee', 'skill')