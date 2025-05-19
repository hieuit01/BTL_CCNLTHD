from django.db import models
from django.db.models import Avg
from cloudinary.models import CloudinaryField
from django.contrib.auth.models import AbstractUser
from ckeditor.fields import RichTextField

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
    NUTRITIONIST = 'nutritionist', 'Chuyên gia dinh dưỡng'
    TRAINER = 'trainer', 'Huấn luyện viên'
    ADMIN = 'admin', 'Admin'


# Giới tính
class Gender(models.TextChoices):
    MALE = 'Male', 'Nam'
    FEMALE = 'Female', 'Nữ'


# User model
class User(AbstractUser):
    avatar = CloudinaryField(null=True)
    gender = models.CharField(max_length=10, choices=Gender.choices, default=Gender.MALE)
    phone = models.CharField(max_length=20, blank=True, null=True)
    role = models.CharField(max_length=20, choices=UserRole.choices, default=UserRole.USER)
    active = models.BooleanField(default=True)
    created_date = models.DateField(auto_now_add=True, null=True)
    updated_date = models.DateField(auto_now=True, null=True)

    def __str__(self):
        return self.username

class ExpertType(models.TextChoices):
    TRAINER = 'trainer', 'Huấn luyện viên'
    NUTRITIONIST = 'nutritionist', 'Chuyên gia dinh dưỡng'

class Expert(User):
    expert_type = models.CharField(max_length=20, choices=ExpertType.choices)
    specialization = models.CharField(max_length=255)
    experience_years = models.PositiveIntegerField()
    bio = RichTextField()

    def __str__(self):
        return self.username


class TrackingMode(models.TextChoices):
    PERSONAL = 'personal', 'Theo dõi cá nhân'
    CONNECTED = 'connected', 'Kết nối với chuyên gia'


class RegularUser(User):
    tracking_mode = models.CharField(max_length=20, choices=TrackingMode.choices, default=TrackingMode.PERSONAL)
    connected_trainer = models.ForeignKey(
        Expert,
        limit_choices_to={'expert_type': ExpertType.TRAINER},
        blank=True,
        null=True,
        on_delete= models.CASCADE,
        related_name='connected_trainer'
    )
    connected_nutritionist = models.ForeignKey(
        Expert,
        limit_choices_to={'expert_type': ExpertType.NUTRITIONIST},
        blank=True,
        null=True,
        on_delete=models.CASCADE,
        related_name='connected_nutritionist'
    )

    def __str__(self):
        return f"Người dùng: {self.username}"

class Review(models.Model):
    expert = models.ForeignKey(Expert, on_delete=models.CASCADE, related_name='reviews')
    reviewer = models.ForeignKey(RegularUser, on_delete=models.CASCADE, related_name='reviews')
    rating = models.PositiveSmallIntegerField()  # 1-5 chẳng hạn
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('expert', 'reviewer')  # mỗi user chỉ đánh giá 1 expert 1 lần

    def __str__(self):
        return f"{self.reviewer} đánh giá {self.expert} - {self.rating} sao"

# Health profile
class HealthGoal(models.TextChoices):
    GAIN_MUSCLE = 'gain_muscle', 'Tăng cơ'
    LOSE_WEIGHT = 'lose_weight', 'Giảm cân'
    MAINTAIN = 'maintain', 'Duy trì sức khỏe'


class HealthProfile(BaseModel):
    user_profile = models.ForeignKey(RegularUser, on_delete=models.CASCADE, related_name='health_profiles')
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
    user_profile = models.ForeignKey(RegularUser, on_delete=models.CASCADE, related_name='health_tracking')
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
    description = RichTextField()
    image = CloudinaryField()
    duration = models.PositiveIntegerField(help_text="Thời gian (phút)")
    calories_burned = models.PositiveIntegerField()
    goal = models.CharField(max_length=20, choices=HealthGoal.choices, null=True, blank=True)

    def __str__(self):
        return self.name


class PlanStatus(models.TextChoices):
    PENDING = 'pending', 'Chưa hoàn thành'
    COMPLETED = 'completed', 'Hoàn thành'


class WorkoutPlan(BaseModel):
    user_profile = models.ForeignKey(RegularUser, on_delete=models.CASCADE, related_name='workout_plans')
    start_date = models.DateField()
    end_date = models.DateField()
    plan_name = models.CharField(max_length=255, help_text="Tên kế hoạch tập luyện", null=True) #them truong plan_name
    status = models.CharField(max_length=20, choices=PlanStatus.choices, default=PlanStatus.PENDING)
    workout = models.ManyToManyField(Workout, through='WorkoutSession')


class SessionStatus(models.TextChoices):
    PENDING = 'pending', 'Chưa thực hiện'
    COMPLETED = 'completed', 'Hoàn thành'

class WorkoutSession(BaseModel):
    workout_plan = models.ForeignKey(WorkoutPlan, on_delete=models.CASCADE, related_name="sessions")
    workout = models.ForeignKey(Workout, on_delete=models.CASCADE, related_name="sessions")
    date = models.DateField() # Ngày tập
    status = models.CharField(max_length=20, choices=SessionStatus.choices, default=SessionStatus.PENDING) # Trạng thái của ba tập

    class Meta:
        ordering = ['-date']

    def __str__(self):
        return f"{self.workout.name} - {self.date} - {self.get_status_display()}"


# Meal Plan & Meal
class Meal(BaseModel):
    name = models.CharField(max_length=255)
    description = RichTextField()
    image = CloudinaryField()
    calories = models.PositiveIntegerField()
    protein = models.FloatField()
    carbs = models.FloatField()
    fat = models.FloatField()
    goal = models.CharField(max_length=20, choices=HealthGoal.choices)

    def __str__(self):
        return self.name


class MealPlan(BaseModel):
    user_profile = models.ForeignKey(RegularUser, on_delete=models.CASCADE, related_name="meal_plans")
    plan_name = models.CharField(max_length=255)
    description = RichTextField()
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
    meal_plan = models.ForeignKey(MealPlan, on_delete=models.CASCADE, related_name='mealplan_meal')
    meal = models.ForeignKey(Meal, on_delete=models.CASCADE, related_name='mealplan_meal')
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
    user_profile = models.ForeignKey(RegularUser, on_delete=models.CASCADE, related_name="health_journals")
    date = models.DateTimeField(auto_now_add=True)
    note = RichTextField()
    mood = models.CharField(max_length=20, choices=MoodType.choices)

    class Meta:
        ordering = ['-date']

    def __str__(self):
        return f"{self.user_profile.user.username} - {self.date}"


# Reminder
class ReminderType(models.TextChoices):
    WATER = 'water', 'Uống nước'
    WORKOUT = 'workout', 'Tập luyện'
    REST = 'rest', 'Nghỉ ngơi'


class Reminder(BaseModel):
    user_profile = models.ForeignKey(RegularUser, on_delete=models.CASCADE, related_name="reminders")
    reminder_type = models.CharField(max_length=20, choices=ReminderType.choices)
    message = RichTextField()
    send_at = models.DateTimeField(null=False)

    def __str__(self):
        return f"{self.user_profile.user.username} - {self.get_reminder_type_display()}"


# Chat message
class ChatMessage(BaseModel):
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name="sent_messages")
    receiver = models.ForeignKey(User, on_delete=models.CASCADE, related_name="received_messages")
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    message_type = models.CharField(
        max_length=20,
        choices=[
            ('text', 'Text'),
            ('image', 'Image'),
            ('file', 'File')
        ],
        default='text'
    )

    def __str__(self):
        return f"{self.sender.username} -> {self.receiver.username}"



