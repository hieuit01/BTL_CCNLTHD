from rest_framework import serializers
from rest_framework.serializers import ModelSerializer
from .models import (User, UserRole, TrackingMode, Expert, RegularUser, HealthProfile, HealthTracking,
                           Workout, WorkoutPlan, WorkoutSession,
                           Meal, MealPlan, MealPlanMeal,
                           HealthJournal, Reminder, ChatMessage, Review)


class ItemSerializer(serializers.ModelSerializer):
    def to_representation(self, instance):
        data = super().to_representation(instance)

        data['image'] = instance.image.url

        return data


# UserSerializer dùng chung
class UserSerializer(serializers.ModelSerializer):
    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['avatar'] = instance.avatar.url if instance.avatar else None
        return data

    def create(self, validated_data):
        data = validated_data.copy()
        u = User(**data)
        u.set_password(u.password)
        u.save()

        return u

    class Meta:
        model = User
        fields = [
            'id', 'first_name', 'last_name', 'username',
            'password', 'avatar', 'role', 'phone', 'email', 'gender'
        ]
        extra_kwargs = {'password': {'write_only': True}}


class ExpertProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer()

    class Meta:
        model = Expert
        fields = ['id', 'user', 'expert_type', 'specialization', 'experience_years', 'bio']

    def update(self, instance, validated_data):
        user_data = validated_data.pop('user', None)

        # Cập nhật User
        if user_data:
            user = instance.user
            for attr, value in user_data.items():
                setattr(user, attr, value)
            user.save()

        # Cập nhật ExpertProfile
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        return instance

# Serializer cho RegularUser
class RegularUserSerializer(UserSerializer):
    connected_trainer_name = serializers.CharField(
        source='connected_trainer.username', read_only=True, allow_null=True
    )
    connected_nutritionist_name = serializers.CharField(
        source='connected_nutritionist.username', read_only=True, allow_null=True
    )

    def create(self, validated_data):
        password = validated_data.pop('password')
        regular_user = RegularUser(**validated_data)
        regular_user.set_password(password)
        regular_user.role = UserRole.USER
        regular_user.save()
        return regular_user

    class Meta(UserSerializer.Meta):
        model = RegularUser
        fields = UserSerializer.Meta.fields + [
            'tracking_mode',
            'connected_trainer',
            'connected_trainer_name',
            'connected_nutritionist',
            'connected_nutritionist_name',
        ]


# Serializer cho Expert (Trainer/Nutritionist)
class ExpertSerializer(UserSerializer):
    average_rating = serializers.FloatField(read_only=True, default=0.0)
    review_count = serializers.IntegerField(read_only=True, default=0)

    def create(self, validated_data):
        password = validated_data.pop('password')
        expert_type = validated_data.get('expert_type')

        if expert_type not in [UserRole.TRAINER, UserRole.NUTRITIONIST]:
            raise serializers.ValidationError({'expert_type': 'Loại chuyên gia không hợp lệ.'})

        expert = Expert(**validated_data)
        expert.set_password(password)
        expert.role = expert_type  # Đồng bộ role và expert_type
        expert.save()
        return expert

    class Meta(UserSerializer.Meta):
        model = Expert
        fields = UserSerializer.Meta.fields + [
            'expert_type', 'specialization', 'experience_years', 'bio', 'average_rating', 'review_count'
        ]

class ReviewSerializer(serializers.ModelSerializer):
    expert = serializers.PrimaryKeyRelatedField(queryset=Expert.objects.all())
    reviewer = serializers.PrimaryKeyRelatedField(queryset=RegularUser.objects.all())
    rating = serializers.IntegerField(min_value=1, max_value=5)
    comment = serializers.CharField(required=False, allow_blank=True)
    created_at = serializers.DateTimeField(read_only=True)

    class Meta:
        model = Review
        fields = ['id', 'expert', 'reviewer', 'rating', 'comment', 'created_at']
        read_only_fields = ['id', 'created_at']

    def validate(self, data):
        # Kiểm tra xem người dùng đã đánh giá chuyên gia này chưa
        if Review.objects.filter(expert=data['expert'], reviewer=data['reviewer']).exists():
            raise serializers.ValidationError("Bạn đã đánh giá chuyên gia này rồi.")
        return data

class HealthProfileSerializer(ModelSerializer):
    bmi = serializers.SerializerMethodField()

    def get_bmi(self, obj):
        return obj.calculate_bmi()

    class Meta:
        model = HealthProfile
        fields = ['id', 'user', 'height', 'weight', 'age', 'goal', 'bmi']


class HealthTrackingSerializer(ModelSerializer):
    class Meta:
        model = HealthTracking
        fields = ['id', 'user', 'date', 'bmi', 'steps', 'heart_rate', 'water_intake']


class WorkoutSerializer(ItemSerializer):
    class Meta:
        model = Workout
        fields = ['id', 'name', 'description', 'image', 'duration', 'calories_burned', 'goal']


class WorkoutSessionSerializer(ModelSerializer):
    class Meta:
        model = WorkoutSession
        fields = ['id', 'workout_plan', 'workout', 'date', 'status']


class WorkoutPlanSerializer(ModelSerializer):
    class Meta:
        model = WorkoutPlan
        fields = ['id', 'user', 'start_date', 'end_date', 'status', 'workout']


class MealSerializer(ItemSerializer):
    class Meta:
        model = Meal
        fields = ['id', 'name', 'description', 'image', 'calories', 'protein', 'carbs', 'fat', 'goal']


class MealPlanMealSerializer(ModelSerializer):
    class Meta:
        model = MealPlanMeal
        fields = ['id', 'meal_plan', 'meal', 'date', 'meal_time']


class MealPlanSerializer(ModelSerializer):
    class Meta:
        model = MealPlan
        fields = ['id', 'user', 'plan_name', 'description', 'start_date', 'end_date', 'goal', 'meals']


class HealthJournalSerializer(ModelSerializer):
    class Meta:
        model = HealthJournal
        fields = ['id', 'user', 'date', 'note', 'mood']


class ReminderSerializer(ModelSerializer):
    class Meta:
        model = Reminder
        fields = ['id', 'user', 'reminder_type', 'message', 'send_at']


class ChatMessageCreateSerializer(serializers.ModelSerializer):
    receiver_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = ChatMessage
        fields = ['receiver_id', 'message', 'message_type']
        read_only_fields = ['sender']

    def validate(self, data):
        sender = self.context['request'].user
        receiver_id = data.get('receiver_id')

        try:
            receiver = User.objects.get(id=receiver_id)
        except User.DoesNotExist:
            raise serializers.ValidationError("Người nhận không tồn tại.")

        # Kiểm tra quyền gửi tin nhắn
        if sender.role == UserRole.USER:
            if sender.user_profile.connected_trainer.user.id != receiver.id:
                raise serializers.ValidationError("Bạn chỉ được nhắn tin với huấn luyện viên của mình.")
        elif sender.role == UserRole.TRAINER:
            if not RegularUser.objects.filter(connected_trainer__user=sender, user=receiver).exists():
                raise serializers.ValidationError("Bạn chỉ được nhắn tin với người dùng của mình.")
        else:
            raise serializers.ValidationError("Vai trò của bạn không được phép gửi tin nhắn.")

        data['sender'] = sender
        data['receiver'] = receiver
        return data

    def create(self, validated_data):
        return ChatMessage.objects.create(**validated_data)
