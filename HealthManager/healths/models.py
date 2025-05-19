from django.db import models
from django.contrib.auth.models import AbstractUser
from ckeditor.fields import RichTextField
from cloudinary.models import CloudinaryField
from django.core.exceptions import ValidationError


# Base model dùng chung
class BaseModel(models.Model):
    active = models.BooleanField(default=True)
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


# Vai trò người dùng
class UserRole(models.TextChoices):
    USER = 'user', 'Người dùng'
    EXPERT = 'expert', 'Chuyên gia'
    Admin = 'admin', 'Admin'


# Giới tính
class Gender(models.TextChoices):
    MALE = 'male', 'Nam'
    FEMALE = 'female', 'Nữ'


# Kiểu chuyên gia
class ExpertType(models.TextChoices):
    TRAINER = 'trainer', 'Huấn luyện viên'
    NUTRITIONIST = 'nutritionist', 'Chuyên gia dinh dưỡng'


# Trạng thái theo dõi
class TrackingMode(models.TextChoices):
    PERSONAL = 'personal', 'Theo dõi cá nhân'
    CONNECTED = 'connected', 'Kết nối với chuyên gia'


# User chung
class User(AbstractUser):
    role = models.CharField(max_length=20, choices=UserRole.choices, default=UserRole.USER)
    avatar = CloudinaryField(null=True, blank=True)
    gender = models.CharField(max_length=10, choices=Gender.choices, default=Gender.MALE)
    phone = models.CharField(max_length=20, blank=True, null=True, unique=True)

    def __str__(self):
        return self.username


# Người dùng thường
class RegularUser(BaseModel):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="regular_profile")
    tracking_mode = models.CharField(max_length=20, choices=TrackingMode.choices, default=TrackingMode.PERSONAL)

    connected_trainer = models.ForeignKey(
        'Expert',
        on_delete=models.SET_NULL,
        limit_choices_to={'expert_type': ExpertType.TRAINER},
        null=True,
        blank=True,
        related_name='connected_trainers'
    )

    connected_nutritionist = models.ForeignKey(
        'Expert',
        on_delete=models.SET_NULL,
        limit_choices_to={'expert_type': ExpertType.NUTRITIONIST},
        null=True,
        blank=True,
        related_name='connected_nutritionists'
    )

    def clean(self):
        if self.tracking_mode == TrackingMode.PERSONAL and (self.connected_trainer or self.connected_nutritionist):
            raise ValidationError("Chế độ 'Theo dõi cá nhân' không được chọn chuyên gia.")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Người dùng: {self.user.username}"


# Chuyên gia (trainer hoặc nutritionist)
class Expert(BaseModel):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="expert_profile")
    expert_type = models.CharField(max_length=20, choices=ExpertType.choices)
    specialization = models.CharField(max_length=255)
    experience_years = models.PositiveIntegerField()
    bio = RichTextField()

    def __str__(self):
        return f"Chuyên gia: {self.user.username} ({self.get_expert_type_display()})"


class Review(models.Model):
    expert = models.ForeignKey(Expert, on_delete=models.CASCADE, related_name='reviews')
    reviewer = models.ForeignKey(RegularUser, on_delete=models.CASCADE)
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
    user = models.ForeignKey(RegularUser, on_delete=models.CASCADE, related_name='health_profiles')
    height = models.FloatField(help_text="Chiều cao (cm)")
    weight = models.FloatField(help_text="Cân nặng (kg)")
    age = models.PositiveIntegerField()
    goal = models.CharField(max_length=20, choices=HealthGoal.choices, default=HealthGoal.MAINTAIN)

    class Meta:
        get_latest_by = "created_date"

    def calculate_bmi(self):
        return self.weight / ((self.height / 100) ** 2)

    def __str__(self):
        return f"Hồ sơ của {self.user.user.username}"


# Health tracking
class HealthTracking(BaseModel):
    user = models.ForeignKey(RegularUser, on_delete=models.CASCADE, related_name='health_tracking')
    date = models.DateField()
    bmi = models.FloatField(null=True, blank=True)
    steps = models.PositiveIntegerField(default=0)
    heart_rate = models.PositiveIntegerField(null=True, blank=True)
    water_intake = models.FloatField(default=0.0)

    class Meta:
        unique_together = ['user', 'date']

    def save(self, *args, **kwargs):
        if not self.bmi and self.user.health_profiles.exists():
            latest_profile = self.user.health_profiles.latest('created_date')
            self.bmi = latest_profile.calculate_bmi()
        super().save(*args, **kwargs)

# Workout & WorkoutPlan
class Workout(BaseModel):
    name = models.CharField(max_length=255)
    description = models.TextField()
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
    user = models.ForeignKey(RegularUser, on_delete=models.CASCADE, related_name='workout_plans')
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(max_length=20, choices=PlanStatus.choices, default=PlanStatus.PENDING)
    workout = models.ManyToManyField(Workout, through='WorkoutSession')

    def __str__(self):
        return f"Kế hoạch tập luyện của {self.user.user.username} từ {self.start_date} đến {self.end_date}"


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
    description = models.TextField()
    image = CloudinaryField()
    calories = models.PositiveIntegerField()
    protein = models.FloatField()
    carbs = models.FloatField()
    fat = models.FloatField()
    goal = models.CharField(max_length=20, choices=HealthGoal.choices)

    def __str__(self):
        return self.name


class MealPlan(BaseModel):
    user = models.ForeignKey(RegularUser, on_delete=models.CASCADE, related_name="meal_plans")
    plan_name = models.CharField(max_length=255)
    description = models.TextField()
    start_date = models.DateField()
    end_date = models.DateField()
    goal = models.CharField(max_length=20, choices=HealthGoal.choices)
    meals = models.ManyToManyField(Meal, through='MealPlanMeal')

    def __str__(self):
        return f"Kế hoạch dinh dưỡng của {self.user.user.username} từ {self.start_date} đến {self.end_date}"


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
        unique_together = ['meal_plan', 'meal', 'meal_time', 'date']  # Mỗi món ăn chỉ có thể được gán một lần cho một bữa ăn trong thực đơn


# Health Journal
class MoodType(models.TextChoices):
    HAPPY = 'happy', 'Vui'
    NORMAL = 'normal', 'Bình thường'
    TIRED = 'tired', 'Mệt'
    STRESSED = 'stressed', 'Căng thẳng'


class HealthJournal(BaseModel):
    user = models.ForeignKey(RegularUser, on_delete=models.CASCADE, related_name="health_journals")
    date = models.DateTimeField(auto_now_add=True)
    note = models.TextField()
    mood = models.CharField(max_length=20, choices=MoodType.choices)

    class Meta:
        ordering = ['-date']

    def __str__(self):
        return f"{self.user.user.username} - ..."


# Reminder
class ReminderType(models.TextChoices):
    WATER = 'water', 'Uống nước'
    WORKOUT = 'workout', 'Tập luyện'
    REST = 'rest', 'Nghỉ ngơi'


class Reminder(BaseModel):
    user = models.ForeignKey(RegularUser, on_delete=models.CASCADE, related_name="reminders")
    reminder_type = models.CharField(max_length=20, choices=ReminderType.choices)
    message = models.CharField(max_length=255)
    send_at = models.DateTimeField(null=False)

    def __str__(self):
        return f"{self.user.user.username} - {self.get_reminder_type_display()}"


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



