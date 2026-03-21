from django.db import models

class Designation(models.Model):
    title = models.CharField(max_length=100)
    
    def __str__(self):
        return self.title

class SkillBenchmark(models.Model):
    designation = models.ForeignKey(Designation, on_delete=models.CASCADE)
    skill_name = models.CharField(max_length=100)
    required_level = models.IntegerField(help_text="Scale of 1 to 5")

    def __str__(self):
        return f"{self.designation} - {self.skill_name}"

class Employee(models.Model):
    name = models.CharField(max_length=100)
    designation = models.ForeignKey(Designation, on_delete=models.SET_NULL, null=True)

    def __str__(self):
        return self.name

class EmployeeSkill(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    skill_name = models.CharField(max_length=100)
    actual_level = models.IntegerField(help_text="Scale of 1 to 5")

    def __str__(self):
        return f"{self.employee} - {self.skill_name}"