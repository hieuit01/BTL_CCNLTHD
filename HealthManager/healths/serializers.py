from rest_framework import serializers
from rest_framework.serializers import ModelSerializer
from healths.models import (User, UserRole, TrackingMode, Expert, ExpertType, RegularUser, HealthProfile, HealthTracking,
                           Workout, WorkoutPlan, WorkoutSession, Gender,
                           Meal, MealPlan, MealPlanMeal,
                           HealthJournal, Reminder, ChatMessage, Review)


# ------ItemSerializer------
class ItemSerializer(serializers.ModelSerializer):
    def to_representation(self, instance):
        data = super().to_representation(instance)

        data['image'] = instance.image.url

        return data

# ------UserSerializer------
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            'id', 'username', 'password',
            'first_name', 'last_name', 'email', 'phone',
            'gender', 'avatar', 'role'
        ]
        extra_kwargs = {
            'password': {'write_only': True},
            'avatar': {'required': False, 'allow_null': True},
            'role': {'read_only': True},  # Vai trò mặc định là USER, không cho phép client set role
        }

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['avatar'] = instance.avatar.url if instance.avatar else None
        return data

    def create(self, validated_data):
        password = validated_data.pop('password')
        validated_data.pop('old_password', None)

        role = validated_data.get('role', UserRole.USER)
        user = User(**validated_data)
        user.set_password(password)
        user.save()

        # Tạo profile phù hợp
        if role == UserRole.USER:
            RegularUser.objects.create(user=user)
        elif role == UserRole.EXPERT:
            pass  # Expert sẽ được tạo bên ngoài (ExpertSerializer)

        return user

    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        old_password = validated_data.pop('old_password', None)

        if password:
            if not instance.check_password(old_password or ''):
                raise serializers.ValidationError({'old_password': 'Mật khẩu cũ không đúng'})
            instance.set_password(password)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()
        return instance

# ------ExpertSerializer------
class ExpertSerializer(serializers.ModelSerializer):
    user = UserSerializer()
    avg_rating = serializers.FloatField(read_only=True, allow_null=True)

    class Meta:
        model = Expert
        fields = [
            'id', 'user',
            'expert_type', 'specialization',
            'experience_years', 'bio', 'avg_rating'
        ]

    def create(self, validated_data):
        user_data = validated_data.pop('user')
        user_data['role'] = UserRole.EXPERT

        user_serializer = UserSerializer(data=user_data)
        user_serializer.is_valid(raise_exception=True)
        user = user_serializer.save()

        return Expert.objects.create(user=user, **validated_data)

    def update(self, instance, validated_data):
        user_data = validated_data.pop('user', None)

        # Cập nhật user nếu có
        if user_data:
            user_serializer = UserSerializer(instance=instance.user, data=user_data, partial=True)
            user_serializer.is_valid(raise_exception=True)
            user_serializer.save()

        # Cập nhật các trường Expert
        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()
        return instance

# ------UserConnectedSerializer------
class UserConnectedSerializer(serializers.ModelSerializer):
    connected_trainer = ExpertSerializer(read_only=True)
    connected_nutritionist = ExpertSerializer(read_only=True)

    class Meta:
        model = RegularUser
        fields = [
            'id',
            'tracking_mode',
            'connected_trainer',
            'connected_nutritionist',
        ]

    def validate(self, data):
        # Lấy giá trị mới cập nhật hoặc giữ nguyên instance cũ
        mode = data.get('tracking_mode', getattr(self.instance, 'tracking_mode', TrackingMode.PERSONAL))
        trainer = data.get('connected_trainer', getattr(self.instance, 'connected_trainer', None))
        nutritionist = data.get('connected_nutritionist', getattr(self.instance, 'connected_nutritionist', None))

        # Nếu chế độ là cá nhân thì không được chọn chuyên gia
        if mode == TrackingMode.PERSONAL and (trainer or nutritionist):
            raise serializers.ValidationError("Chế độ 'Theo dõi cá nhân' không được chọn chuyên gia.")

        # Nếu chế độ là kết nối chuyên gia thì phải chọn ít nhất 1 chuyên gia
        if mode == TrackingMode.CONNECTED and not (trainer or nutritionist):
            raise serializers.ValidationError("Khi chọn chế độ kết nối chuyên gia phải chọn ít nhất một chuyên gia.")

        return data

    def update(self, instance, validated_data):
        # Cập nhật các trường trong instance
        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        # Nếu chế độ chuyển thành cá nhân, xóa các kết nối chuyên gia để đảm bảo dữ liệu sạch
        if validated_data.get('tracking_mode') == TrackingMode.PERSONAL:
            instance.connected_trainer = None
            instance.connected_nutritionist = None

        instance.save()
        return instance

# ------HealthProfileSerializer------
class HealthProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = HealthProfile
        fields = ['id', 'user', 'height', 'weight', 'age', 'goal', 'created_date']
        read_only_fields = ['id', 'user', 'created_date']

    def create(self, validated_data):
        # Gán user hiện tại khi tạo
        validated_data['user'] = self.context['request'].user.regular_profile
        return super().create(validated_data)

# ------HealthTrackingSerializer------
class HealthTrackingSerializer(serializers.ModelSerializer):
    class Meta:
        model = HealthTracking
        fields = ['id', 'user', 'date', 'bmi', 'steps', 'heart_rate', 'water_intake', 'created_date']
        read_only_fields = ['id', 'user', 'bmi', 'created_date']

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user.regular_profile
        return super().create(validated_data)

# ------WorkoutSerializer------
class WorkoutSerializer(ItemSerializer):
    class Meta:
        model = Workout
        fields = '__all__'
        read_only_fields = ['created_by', 'is_public', 'suggested_to']

    def create(self, validated_data):
        request = self.context['request']
        user = request.user

        # Gán created_by
        validated_data['created_by'] = user

        # Nếu user là người dùng hoặc chuyên gia (trainer), thì bài tập không công khai
        validated_data['is_public'] = False
        return super().create(validated_data)

# ------WorkoutSessionSerializer------
class WorkoutSessionSerializer(serializers.ModelSerializer):
    workout_name = serializers.CharField(source='workout.name', read_only=True)

    class Meta:
        model = WorkoutSession
        fields = ['id', 'workout_plan', 'workout', 'workout_name', 'date', 'duration', 'status']
        read_only_fields = ['workout_name', 'workout_plan']

    def validate(self, data):
        workout_plan = self.context.get('workout_plan') or self.instance.workout_plan
        session_date = data.get('date') or getattr(self.instance, 'date', None)

        if session_date and workout_plan:
            if session_date < workout_plan.start_date or session_date > workout_plan.end_date:
                raise serializers.ValidationError("Ngày buổi tập phải nằm trong khoảng thời gian của kế hoạch.")
        return data

# ------WorkoutPlanSerializer------
class WorkoutPlanSerializer(serializers.ModelSerializer):
    sessions = WorkoutSessionSerializer(many=True)

    class Meta:
        model = WorkoutPlan
        fields = ['id', 'user', 'plan_name', 'description', 'start_date', 'end_date', 'goal', 'workout', 'sessions']
        read_only_fields = ['user']

    def validate(self, data):
        start_date = data.get('start_date', getattr(self.instance, 'start_date', None))
        end_date = data.get('end_date', getattr(self.instance, 'end_date', None))
        if start_date and end_date and end_date < start_date:
            raise serializers.ValidationError("Ngày kết thúc phải lớn hơn hoặc bằng ngày bắt đầu.")
        return data

    def create(self, validated_data):
        sessions_data = validated_data.pop('sessions', [])
        user = self.context['request'].user
        validated_data['user'] = getattr(user, 'regular_profile', None)
        plan = WorkoutPlan.objects.create(**validated_data)

        for session_data in sessions_data:
            WorkoutSession.objects.create(workout_plan=plan, **session_data)
        return plan

    def update(self, instance, validated_data):
        sessions_data = validated_data.pop('sessions', None)
        validated_data.pop('user', None)

        # Update fields of WorkoutPlan
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if sessions_data is not None:
            existing_sessions = {s.id: s for s in instance.sessions.all()}
            incoming_ids = []

            for session_data in sessions_data:
                session_id = session_data.get('id', None)
                if session_id and session_id in existing_sessions:
                    session = existing_sessions[session_id]
                    for attr, value in session_data.items():
                        if attr != 'id':
                            setattr(session, attr, value)
                    session.save()
                    incoming_ids.append(session_id)
                else:
                    new_session = WorkoutSession.objects.create(workout_plan=instance, **session_data)
                    incoming_ids.append(new_session.id)

            # Optional: delete sessions not in incoming_ids
            for session_id, session in existing_sessions.items():
                if session_id not in incoming_ids:
                    session.delete()

        return instance

# ------MealSerializer------
class MealSerializer(ItemSerializer):
    class Meta:
        model = Meal
        fields = '__all__'
        read_only_fields = ['created_by', 'is_public', 'suggested_to']

    def create(self, validated_data):
        request = self.context['request']
        user = request.user

        validated_data['created_by'] = user
        validated_data['is_public'] = False
        return super().create(validated_data)

# ------MealPlanMealSerializer------
class MealPlanMealSerializer(serializers.ModelSerializer):
    meal_name = serializers.CharField(source='meal.name', read_only=True)

    class Meta:
        model = MealPlanMeal
        fields = ['id', 'meal_plan', 'meal', 'meal_name', 'date', 'meal_time']
        read_only_fields = ['meal_name', 'meal_plan']

    def validate(self, data):
        meal_plan = self.context.get('meal_plan') or self.instance.meal_plan
        meal_date = data.get('date') or getattr(self.instance, 'date', None)

        if meal_date and meal_plan:
            if meal_date < meal_plan.start_date or meal_date > meal_plan.end_date:
                raise serializers.ValidationError("Ngày bữa ăn phải nằm trong khoảng thời gian của kế hoạch.")
        return data

# ------MealPlanSerializer------
class MealPlanSerializer(serializers.ModelSerializer):
    mealplan_meals = MealPlanMealSerializer(many=True)

    class Meta:
        model = MealPlan
        fields = ['id', 'user', 'plan_name', 'description', 'start_date', 'end_date', 'goal', 'meals', 'mealplan_meals']
        read_only_fields = ['user']

    def validate(self, data):
        start_date = data.get('start_date', getattr(self.instance, 'start_date', None))
        end_date = data.get('end_date', getattr(self.instance, 'end_date', None))
        if start_date and end_date and end_date < start_date:
            raise serializers.ValidationError("Ngày kết thúc phải lớn hơn hoặc bằng ngày bắt đầu.")
        return data

    def create(self, validated_data):
        meals_data = validated_data.pop('mealplan_meals', [])
        validated_data['user'] = self.context['request'].user.regular_profile
        plan = MealPlan.objects.create(**validated_data)

        for item in meals_data:
            MealPlanMeal.objects.create(meal_plan=plan, **item)

        return plan

    def update(self, instance, validated_data):
        meals_data = validated_data.pop('mealplan_meals', None)
        validated_data.pop('user', None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if meals_data is not None:
            existing = {m.id: m for m in instance.mealplan_meals.all()}
            incoming_ids = []

            for item in meals_data:
                meal_id = item.get('id')
                if meal_id and meal_id in existing:
                    meal = existing[meal_id]
                    for attr, value in item.items():
                        if attr != 'id':
                            setattr(meal, attr, value)
                    meal.save()
                    incoming_ids.append(meal_id)
                else:
                    new_meal = MealPlanMeal.objects.create(meal_plan=instance, **item)
                    incoming_ids.append(new_meal.id)

            for m_id, m in existing.items():
                if m_id not in incoming_ids:
                    m.delete()

        return instance

# ------HealthJournalSerializer------
class HealthJournalSerializer(serializers.ModelSerializer):
    class Meta:
        model = HealthJournal
        fields = ['id', 'user', 'date', 'note', 'mood']
        read_only_fields = ['id', 'user', 'date']

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user.regular_profile
        return super().create(validated_data)

# ------ReminderSerializer------
class ReminderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Reminder
        fields = ['id', 'user', 'reminder_type', 'message', 'send_at']
        read_only_fields = ['id', 'user']

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user.regular_profile
        return super().create(validated_data)

# ------ReviewerSerializer------
class ReviewerSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    avatar = serializers.ImageField(source='user.avatar', read_only=True)

    class Meta:
        model = RegularUser
        fields = ['id', 'username', 'avatar']

# ------ReviewSerializer------
class ReviewSerializer(serializers.ModelSerializer):
    reviewer = ReviewerSerializer(read_only=True)  # Hiển thị nested
    rating = serializers.IntegerField(min_value=1, max_value=5)
    comment = serializers.CharField(allow_blank=True)

    # expert và reviewer chỉ cần khi tạo, không cần hiển thị khi GET (hoặc hiển thị id nếu cần)
    expert = serializers.PrimaryKeyRelatedField(queryset=Expert.objects.all(), write_only=True, required=True)
    reviewer_id = serializers.PrimaryKeyRelatedField(source='reviewer', queryset=RegularUser.objects.all(),
                                                     write_only=True, required=True)

    class Meta:
        model = Review
        fields = ['id', 'expert', 'reviewer_id', 'reviewer', 'rating', 'comment', 'created_at']
        read_only_fields = ['id', 'reviewer', 'created_at']

# ------ChatMessageSerializer------
class ChatMessageSerializer(ItemSerializer):
    sender_name = serializers.SerializerMethodField()
    sender_avatar = serializers.SerializerMethodField()

    class Meta:
        model = ChatMessage
        fields = [
            'id', 'sender', 'sender_name', 'sender_avatar', 'receiver',
            'message', 'image', 'message_type', 'is_read', 'is_revoked', 'created_date'
        ]
        read_only_fields = ['id', 'sender', 'created_date', 'is_read', 'is_revoked', 'message_type']

    def validate(self, attrs):
        # Không kiểm tra message_type nữa mà kiểm tra trực tiếp dữ liệu
        if not attrs.get('message') and not attrs.get('image'):
            raise serializers.ValidationError("Tin nhắn phải có nội dung text hoặc hình ảnh.")
        return attrs

    def create(self, validated_data):
        validated_data['sender'] = self.context['request'].user
        return super().create(validated_data)

    def get_sender_name(self, obj):
        user = obj.sender
        if hasattr(user, 'expert_profile'):
            expert = user.expert_profile
            if expert.expert_type == ExpertType.TRAINER:
                return f"HLV {user.get_full_name() or user.username}"
            elif expert.expert_type == ExpertType.NUTRITIONIST:
                return f"Chuyên gia Dinh Dưỡng {user.get_full_name() or user.username}"
        return user.get_full_name() or user.username

    def get_sender_avatar(self, obj):
        user = obj.sender
        if user.avatar:
            try:
                return user.avatar.url
            except Exception:
                return None
        return None
