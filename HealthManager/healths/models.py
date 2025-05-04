from django.db import models
from cloudinary.models import CloudinaryField
from django.core.validators import MinValueValidator, MaxValueValidator
from django.contrib.auth.models import AbstractUser


# Base model
class BaseModel(models.Model):
    active = models.BooleanField(default=True)
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


# User roles
class UserRole(models.TextChoices):
    USER = 'user', 'Người dùng'
    EXPERT = 'expert', 'Chuyên gia'

# Giới tính
class Gender(models.TextChoices):
    MALE = 'Male', 'Nam'
    FEMALE = 'Female', 'Nữ'

class User(AbstractUser):
    avatar = CloudinaryField(null=True)
    gender = models.CharField(max_length=10, choices=Gender, default=Gender.MALE)
    role = models.CharField(max_length=10, choices=UserRole.choices, default=UserRole.USER)
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)

    class Meta:
        abstract: True

    def __str__(self):
        return self.username


# Expert profile
class ExpertProfile(User):
    expert = models.OneToOneField(User, on_delete=models.CASCADE, related_name='expert_profile')
    specialization = models.CharField(max_length=255)
    experience_years = models.PositiveIntegerField()
    bio = models.TextField()

    def __str__(self):
        return self.expert.username


# User profile
class TrackingMode(models.TextChoices):
    PERSONAL = 'personal', 'Theo dõi cá nhân'
    CONNECTED = 'connected', 'Kết nối với chuyên gia'


class UserProfile(User):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    tracking_mode = models.CharField(max_length=20, choices=TrackingMode.choices)
    connected_expert = models.ForeignKey(ExpertProfile, on_delete=models.SET_NULL, null=True, blank=True)


# Health profile
class HealthGoal(models.TextChoices):
    GAIN_MUSCLE = 'gain_muscle', 'Tăng cơ'
    LOSE_WEIGHT = 'lose_weight', 'Giảm cân'
    MAINTAIN = 'maintain', 'Duy trì sức khỏe'


class HealthProfile(BaseModel):
    user_profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    height = models.FloatField(help_text="Chiều cao (cm)")
    weight = models.FloatField(help_text="Cân nặng (kg)")
    age = models.PositiveIntegerField()
    goal = models.CharField(max_length=20, choices=HealthGoal.choices, default=HealthGoal.MAINTAIN)

    def calculate_bmi(self):
        return self.weight / ((self.height / 100) ** 2)

    def __str__(self):
        return f"Hồ sơ của {self.user_profile.user.username}"


# Health tracking
class HealthTracking(BaseModel):
    user_profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    date = models.DateField()
    bmi = models.FloatField(null=True, blank=True)
    steps = models.PositiveIntegerField(default=0)
    heart_rate = models.PositiveIntegerField(null=True, blank=True)
    water_intake = models.FloatField(default=0.0)

    def save(self, *args, **kwargs):
        if not self.bmi and hasattr(self.user_profile, 'health_profile'):
            self.bmi = self.user_profile.health_profile.calculate_bmi()
        super().save(*args, **kwargs)


# Workout & WorkoutPlan
class Workout(BaseModel):
    name = models.CharField(max_length=255)
    description = models.TextField()
    duration = models.PositiveIntegerField(help_text="Thời gian (phút)")
    calories_burned = models.PositiveIntegerField()

    def __str__(self):
        return self.name


class PlanStatus(models.TextChoices):
    PENDING = 'pending', 'Chưa hoàn thành'
    COMPLETED = 'completed', 'Hoàn thành'


class WorkoutPlan(BaseModel):
    user_profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(max_length=20, choices=PlanStatus.choices, default=PlanStatus.PENDING)
    workout = models.ManyToManyField(Workout)


class SessionStatus(models.TextChoices):
    PENDING = 'pending', 'Chưa thực hiện'
    COMPLETED = 'completed', 'Hoàn thành'


class WorkoutSession(BaseModel):
    workout_plan = models.ForeignKey(WorkoutPlan, on_delete=models.CASCADE, related_name="sessions")
    workout = models.ForeignKey(Workout, on_delete=models.CASCADE)
    date = models.DateField() # Ngày tập
    status = models.CharField(max_length=20, choices=SessionStatus.choices, default=SessionStatus.PENDING) # Trạng thái của ba tập

    class Meta:
        ordering = ['-date']

    def __str__(self):
        return f"{self.workout.name} - {self.date} - {self.get_status_display()}"


# Meal Plan & Meal
class Meal(BaseModel):
    name = models.CharField(max_length=255)
    description = models.TextField()
    calories = models.PositiveIntegerField()
    protein = models.FloatField()
    carbs = models.FloatField()
    fat = models.FloatField()
    goal = models.CharField(max_length=20, choices=HealthGoal.choices)

    def __str__(self):
        return self.name


class MealPlan(BaseModel):
    user_profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    health_profile = models.ForeignKey(HealthProfile, on_delete=models.CASCADE)
    plan_name = models.CharField(max_length=255)
    description = models.TextField()
    start_date = models.DateField()
    end_date = models.DateField()
    goal = models.CharField(max_length=20, choices=HealthGoal.choices)
    meals = models.ManyToManyField(Meal, through='MealPlanMeal')


class MealTime(models.TextChoices):
    BREAKFAST = 'breakfast', 'Sáng'
    LUNCH = 'lunch', 'Trưa'
    DINNER = 'dinner', 'Tối'
    SNACK = 'snack', 'Ăn nhẹ'


class MealPlanMeal(BaseModel):
    meal_plan = models.ForeignKey(MealPlan, on_delete=models.CASCADE)
    meal = models.ForeignKey(Meal, on_delete=models.CASCADE)
    date = models.DateField()
    meal_time = models.CharField(max_length=20, choices=MealTime.choices)

    class Meta:
        unique_together = ['meal_plan', 'meal', 'meal_time'] # Mỗi món ăn chỉ có thể được gán một lần cho một bữa ăn trong thực đơn


# Health Journal
class MoodType(models.TextChoices):
    HAPPY = 'happy', 'Vui'
    NORMAL = 'normal', 'Bình thường'
    TIRED = 'tired', 'Mệt'
    STRESSED = 'stressed', 'Căng thẳng'


class HealthJournal(BaseModel):
    user_profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    date = models.DateTimeField(auto_now_add=True)
    note = models.TextField()
    mood = models.CharField(max_length=20, choices=MoodType.choices)

    def __str__(self):
        return f"{self.user_profile.user.username} - {self.date}"


# Reminder
class ReminderType(models.TextChoices):
    WATER = 'water', 'Uống nước'
    WORKOUT = 'workout', 'Tập luyện'
    REST = 'rest', 'Nghỉ ngơi'


class Reminder(BaseModel):
    user_profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    reminder_type = models.CharField(max_length=20, choices=ReminderType.choices)
    message = models.CharField(max_length=255)
    send_at = models.DateTimeField(null=False)

    def __str__(self):
        return f"{self.user_profile.user.username} - {self.get_reminder_type_display()}"


# Chat message
class ChatMessage(BaseModel):
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name="sent_messages")
    receiver = models.ForeignKey(User, on_delete=models.CASCADE, related_name="received_messages")
    message = models.TextField()

    def __str__(self):
        return f"{self.sender.username} -> {self.receiver.username}"
