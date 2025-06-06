from django.db import models
from django.contrib.auth.models import AbstractUser
from ckeditor.fields import RichTextField
from cloudinary.models import CloudinaryField
from django.core.exceptions import ValidationError


# Base Model
class BaseModel(models.Model):
    active = models.BooleanField(default=True)
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


# Enum Choices
class UserRole(models.TextChoices):
    USER = 'user', 'Người dùng'
    EXPERT = 'expert', 'Chuyên gia'
    ADMIN = 'Admin', 'admin'


class Gender(models.TextChoices):
    MALE = 'male', 'Nam'
    FEMALE = 'female', 'Nữ'


class ExpertType(models.TextChoices):
    TRAINER = 'trainer', 'Huấn luyện viên'
    NUTRITIONIST = 'nutritionist', 'Chuyên gia dinh dưỡng'


class TrackingMode(models.TextChoices):
    PERSONAL = 'personal', 'Theo dõi cá nhân'
    CONNECTED = 'connected', 'Kết nối với chuyên gia'


class HealthGoal(models.TextChoices):
    GAIN_MUSCLE = 'gain_muscle', 'Tăng cơ'
    LOSE_WEIGHT = 'lose_weight', 'Giảm cân'
    MAINTAIN = 'maintain', 'Duy trì sức khỏe'


class PlanStatus(models.TextChoices):
    PENDING = 'pending', 'Chưa hoàn thành'
    COMPLETED = 'completed', 'Hoàn thành'


class SessionStatus(models.TextChoices):
    PENDING = 'pending', 'Chưa thực hiện'
    COMPLETED = 'completed', 'Hoàn thành'


class MealTime(models.TextChoices):
    BREAKFAST = 'breakfast', 'Sáng'
    LUNCH = 'lunch', 'Trưa'
    DINNER = 'dinner', 'Tối'
    SNACK = 'snack', 'Ăn nhẹ'


class MoodType(models.TextChoices):
    HAPPY = 'happy', 'Vui'
    NORMAL = 'normal', 'Bình thường'
    TIRED = 'tired', 'Mệt'
    STRESSED = 'stressed', 'Căng thẳng'


class ReminderType(models.TextChoices):
    WATER = 'water', 'Uống nước'
    WORKOUT = 'workout', 'Tập luyện'
    REST = 'rest', 'Nghỉ ngơi'


# User Model
class User(AbstractUser):
    role = models.CharField(max_length=20, choices=UserRole.choices, default=UserRole.USER)
    avatar = CloudinaryField(null=True, blank=True)
    gender = models.CharField(max_length=10, choices=Gender.choices, default=Gender.MALE)
    phone = models.CharField(max_length=20, blank=True, null=True, unique=True)

    def __str__(self):
        return self.username


# Expert Model
class Expert(BaseModel):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="expert_profile")
    expert_type = models.CharField(max_length=20, choices=ExpertType.choices)
    specialization = models.CharField(max_length=255)
    experience_years = models.PositiveIntegerField()
    bio = RichTextField()

    def __str__(self):
        return f"{self.user.username} - {self.get_expert_type_display()}"


# Regular User Model
class RegularUser(BaseModel):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="regular_profile")
    tracking_mode = models.CharField(max_length=20, choices=TrackingMode.choices, default=TrackingMode.PERSONAL)

    connected_trainer = models.ForeignKey(
        Expert, on_delete=models.SET_NULL,
        limit_choices_to={'expert_type': ExpertType.TRAINER},
        null=True, blank=True, related_name='trainer_clients'
    )
    connected_nutritionist = models.ForeignKey(
        Expert, on_delete=models.SET_NULL,
        limit_choices_to={'expert_type': ExpertType.NUTRITIONIST},
        null=True, blank=True, related_name='nutritionist_clients'
    )

    def clean(self):
        super().clean()
        if self.tracking_mode == TrackingMode.PERSONAL and (self.connected_trainer or self.connected_nutritionist):
            raise ValidationError("Chế độ cá nhân không được liên kết chuyên gia.")
        elif self.tracking_mode == TrackingMode.CONNECTED and not (self.connected_trainer or self.connected_nutritionist):
            raise ValidationError("Phải chọn ít nhất một chuyên gia khi ở chế độ kết nối.")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.user.username


# Health Profile
class HealthProfile(BaseModel):
    user = models.ForeignKey(RegularUser, on_delete=models.CASCADE, related_name='health_profiles')
    height = models.FloatField(help_text="Chiều cao (cm)")
    weight = models.FloatField(help_text="Cân nặng (kg)")
    age = models.PositiveIntegerField()
    goal = models.CharField(max_length=20, choices=HealthGoal.choices)

    class Meta:
        get_latest_by = 'created_date'

    def calculate_bmi(self):
        return self.weight / ((self.height / 100) ** 2)

    def __str__(self):
        return f"Hồ sơ của {self.user}"


# Health Tracking
class HealthTracking(BaseModel):
    user = models.ForeignKey(RegularUser, on_delete=models.CASCADE, related_name='health_tracking')
    date = models.DateField()
    bmi = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True)
    steps = models.PositiveIntegerField(default=0)
    heart_rate = models.PositiveIntegerField(null=True, blank=True)
    water_intake = models.FloatField(default=0.0)

    class Meta:
        unique_together = ['user', 'date']

    def save(self, *args, **kwargs):
        if not self.bmi and self.user.health_profiles.exists():
            latest = self.user.health_profiles.latest('created_date')
            self.bmi = latest.calculate_bmi()
        super().save(*args, **kwargs)


# Workout & Plan
class Workout(BaseModel):
    name = models.CharField(max_length=255)
    description = models.TextField()
    image = CloudinaryField()
    calories_burned = models.PositiveIntegerField()
    goal = models.CharField(max_length=20, choices=HealthGoal.choices, null=True, blank=True)
    is_public = models.BooleanField(default=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    suggested_to = models.ForeignKey(
        RegularUser,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name='suggested_workouts',
        help_text='User cụ thể mà trainer gợi ý bài tập này'
    )

    def __str__(self):
        return self.name


class WorkoutPlan(BaseModel):
    user = models.ForeignKey(RegularUser, on_delete=models.CASCADE, related_name='workout_plans', null=True, blank=True)
    plan_name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    start_date = models.DateField()
    end_date = models.DateField()
    goal = models.CharField(max_length=20, choices=HealthGoal.choices, null=True, blank=True)
    workout = models.ManyToManyField(Workout, through='WorkoutSession')

    def clean(self):
        super().clean()
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValidationError("Ngày kết thúc phải lớn hơn hoặc bằng ngày bắt đầu.")

    def __str__(self):
        return self.plan_name


class WorkoutSession(BaseModel):
    workout_plan = models.ForeignKey(WorkoutPlan, on_delete=models.CASCADE, related_name="sessions")
    workout = models.ForeignKey(Workout, on_delete=models.PROTECT)
    date = models.DateField()
    duration = models.PositiveIntegerField(help_text="Thời gian (phút)")
    status = models.CharField(max_length=20, choices=SessionStatus.choices, default=SessionStatus.PENDING)

    class Meta:
        ordering = ['-date']


# Meal & Plan
class Meal(BaseModel):
    name = models.CharField(max_length=255)
    description = models.TextField()
    image = CloudinaryField()
    calories = models.PositiveIntegerField()
    protein = models.FloatField()
    carbs = models.FloatField()
    fat = models.FloatField()
    goal = models.CharField(max_length=20, choices=HealthGoal.choices, null=True, blank=True)
    is_public = models.BooleanField(default=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    suggested_to = models.ForeignKey(
        RegularUser,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name='suggested_meals',
        help_text='User cụ thể mà nutritionst gợi ý bài tập này'
    )

    def __str__(self):
        return self.name

class MealPlan(BaseModel):
    user = models.ForeignKey(RegularUser, on_delete=models.CASCADE, related_name="meal_plans", null=True, blank=True)
    plan_name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    start_date = models.DateField()
    end_date = models.DateField()
    goal = models.CharField(max_length=20, choices=HealthGoal.choices, null=True, blank=True)
    meals = models.ManyToManyField(Meal, through='MealPlanMeal')

    def clean(self):
        super().clean()
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValidationError("Ngày kết thúc phải lớn hơn hoặc bằng ngày bắt đầu.")

    def __str__(self):
        return self.plan_name


class MealPlanMeal(BaseModel):
    meal_plan = models.ForeignKey(MealPlan, on_delete=models.CASCADE, related_name='mealplan_meals')
    meal = models.ForeignKey(Meal, on_delete=models.CASCADE)
    date = models.DateField(null=True, blank=True)
    meal_time = models.CharField(max_length=20, choices=MealTime.choices)

    class Meta:
        unique_together = ['meal_plan', 'meal', 'meal_time', 'date']


# Health Journal
class HealthJournal(BaseModel):
    user = models.ForeignKey(RegularUser, on_delete=models.CASCADE, related_name="health_journals")
    date = models.DateTimeField(auto_now_add=True)
    note = models.TextField()
    mood = models.CharField(max_length=20, choices=MoodType.choices)

    class Meta:
        ordering = ['-date']


# Reminder
class Reminder(BaseModel):
    user = models.ForeignKey(RegularUser, on_delete=models.CASCADE, related_name="reminders")
    reminder_type = models.CharField(max_length=20, choices=ReminderType.choices)
    message = models.CharField(max_length=255)
    remind_time = models.TimeField()
    repeat_days = models.CharField(
        max_length=50,  # ví dụ: "mon,wed,fri"
        default="",
        blank=True,
        help_text="CSV các ngày lặp lại: mon,tue,wed,..."
    )

    def get_repeat_day_list(self):
        return self.repeat_days.split(',') if self.repeat_days else []

    def __str__(self):
        return f"{self.user} - {self.reminder_type}"


# Review
class Review(models.Model):
    expert = models.ForeignKey(Expert, on_delete=models.CASCADE, related_name='reviews')
    reviewer = models.ForeignKey(RegularUser, on_delete=models.CASCADE)
    rating = models.PositiveSmallIntegerField()
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('expert', 'reviewer')


# Chat
class ChatMessage(BaseModel):
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name="sent_messages")
    receiver = models.ForeignKey(User, on_delete=models.CASCADE, related_name="received_messages")
    message = models.TextField(blank=True)  # text message
    image = CloudinaryField(null=True, blank=True)  # ảnh gửi qua Cloudinary
    is_read = models.BooleanField(default=False)
    is_revoked = models.BooleanField(default=False)
    message_type = models.CharField(
        max_length=20,
        choices=[('text', 'Text'), ('image', 'Image')],
        default='text'
    )

    def save(self, *args, **kwargs):
        if self.image and not self.message:
            self.message_type = 'image'
        else:
            self.message_type = 'text'
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.sender} -> {self.receiver}"
