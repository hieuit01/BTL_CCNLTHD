from django.utils import timezone
from rest_framework import viewsets, status, generics, permissions, parsers, serializers
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404

from .models import User, RegularUser, Expert, UserRole, TrackingMode, Review, ExpertType, HealthProfile, \
    HealthTracking, Workout, WorkoutPlan, WorkoutSession, Meal, MealPlan, ChatMessage, Reminder, HealthJournal, \
    MealPlanMeal
from .serializers import UserSerializer, RegularUserSerializer, ExpertSerializer, ReviewSerializer, \
    HealthProfileSerializer, HealthTrackingSerializer, WorkoutSerializer, WorkoutPlanSerializer, \
    WorkoutSessionSerializer, MealSerializer, MealPlanSerializer, ChatMessageCreateSerializer, ReminderSerializer, \
    HealthJournalSerializer, MealPlanMealSerializer
from .perm import IsRegularUserWithConnectedTrackingMode, CanReviewExpert
from django.db.models import Count, Avg, Value
from django.db.models.functions import Coalesce

# Đăng ký và chỉnh sửa thông tin cho user theo từng vai trò
class UserViewSet(viewsets.ViewSet, generics.CreateAPIView):
    queryset = User.objects.filter(is_active=True)
    parser_classes = [parsers.MultiPartParser]

    def get_permissions(self):
        if self.request.method == 'POST':
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]

    @action(methods=['get', 'patch'], detail=False, url_path='current-user')
    def current_user(self, request):
        user = request.user

        if request.method == 'PATCH':
            data = request.data

            for key, value in data.items():
                if key in ['first_name', 'last_name', 'phone', 'email', 'username']:
                    setattr(user, key, value)

                elif key == 'password':
                    user.set_password(value)

                elif key == 'avatar':
                    user.avatar = value

                elif key == 'tracking_mode' and hasattr(user, 'tracking_mode'):
                    if value in TrackingMode.values:
                        user.tracking_mode = value
                    else:
                        return Response({'error': 'Chế độ theo dõi không hợp lệ'}, status=status.HTTP_400_BAD_REQUEST)

                elif key == 'connected_trainer' and hasattr(user, 'tracking_mode'):
                    if value:
                        trainer = get_object_or_404(User, id=value, role=UserRole.TRAINER)
                        user.connected_trainer = trainer
                    else:
                        user.connected_trainer = None

                elif key == 'connected_nutritionist' and hasattr(user, 'tracking_mode'):
                    if value:
                        nutritionist = get_object_or_404(User, id=value, role=UserRole.NUTRITIONIST)
                        user.connected_nutritionist = nutritionist
                    else:
                        user.connected_nutritionist = None

                elif hasattr(user, 'expert_type') and key in ['specialization', 'experience_years', 'bio']:
                    setattr(user, key, value)

            user.save()

        # Chọn serializer phù hợp
        if hasattr(user, 'tracking_mode'):
            serializer_class = RegularUserSerializer
        elif hasattr(user, 'expert_type'):
            serializer_class = ExpertSerializer
        else:
            serializer_class = UserSerializer

        serializer = serializer_class(user)
        return Response(serializer.data)

    def get_serializer_class(self):
        if self.request.method == 'POST':
            role = self.request.data.get('role')
            if role == UserRole.USER:
                return RegularUserSerializer
            elif role in [UserRole.Admin, UserRole.EXPERT]:
                return ExpertSerializer
            return UserSerializer
        return UserSerializer

    def create(self, request, *args, **kwargs):
        role = request.data.get('role')
        if role not in [UserRole.USER, UserRole.Admin, UserRole.EXPERT]:
            return Response({'error': 'Vai trò không hợp lệ'}, status=status.HTTP_400_BAD_REQUEST)

        data = request.data.copy()
        if role in [ExpertType.TRAINER, ExpertType.NUTRITIONIST]:
            data['expert_type'] = role

        serializer_class = self.get_serializer_class()
        serializer = serializer_class(data=data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(serializer_class(user).data, status=status.HTTP_201_CREATED)

# Lấy danh sách(sắp xếp theo rating giảm dần) và xem chi tiết 1 Train cho người dùng có vai trò là user
class TrainerViewSet(viewsets.ViewSet):
    serializer_class = ExpertSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [IsRegularUserWithConnectedTrackingMode()]
        return super().get_permissions()

    def list(self, request):
        trainers = Expert.objects.filter(
            is_active=True,
            expert_type=UserRole.TRAINER
        ).annotate(
            average_rating=Coalesce(Avg('reviews__rating'), Value(0)),
            review_count=Count('reviews')
        ).order_by('-average_rating', '-review_count')

        serializer = self.serializer_class(trainers, many=True)
        return Response(serializer.data)

    def retrieve(self, request, pk=None):
        trainer = get_object_or_404(Expert, pk=pk, expert_type=UserRole.TRAINER)
        serializer = self.serializer_class(trainer)
        return Response(serializer.data)

# Lấy danh sách(Sắp xếp theo rating giẩm dần) và xem chi tiết 1 Nutritionist cho người dùng có vai trò là user
class NutritionistViewSet(viewsets.ViewSet):
    serializer_class = ExpertSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [IsRegularUserWithConnectedTrackingMode()]
        return super().get_permissions()

    def list(self, request):
        nutritionists = Expert.objects.filter(
            is_active=True,
            expert_type=UserRole.NUTRITIONIST
        ).annotate(
            average_rating=Coalesce(Avg('reviews__rating'), Value(0)),
            review_count=Count('reviews')
        ).order_by('-average_rating', '-review_count')

        serializer = self.serializer_class(nutritionists, many=True)
        return Response(serializer.data)

    def retrieve(self, request, pk=None):
        nutritionist = get_object_or_404(Expert, pk=pk, expert_type=UserRole.NUTRITIONIST)
        serializer = self.serializer_class(nutritionist)
        return Response(serializer.data)

# Người dùng tạo đánh giá cho expert mà họ đang kết nối
class ReviewCreateView(viewsets.ViewSet, generics.CreateAPIView):
    queryset = Review.objects.all()
    serializer_class = ReviewSerializer
    permission_classes = [permissions.IsAuthenticated, CanReviewExpert]

    def perform_create(self, serializer):
        expert = self.get_object()  # expert được lấy từ URL (pk)
        user = self.request.user

        # Kiểm tra xem người dùng có kết nối với chuyên gia này không
        if expert != user.connected_trainer and expert != user.connected_nutritionist:
            raise serializers.ValidationError("Bạn chưa kết nối với chuyên gia này.")

        # Nếu người dùng đã kết nối, lưu đánh giá
        serializer.save(reviewer=user, expert=expert)


# class ExpertProfileViewSet(viewsets.ViewSet):
#     serializer_class = serializers.ExpertProfileSerializer
#     permission_classes = [permissions.IsAuthenticated, IsExpertWithProfile]
#
#     @action(methods=['get', 'patch'], detail=False, url_path='me')
#     def get_current_expert(self, request):
#         expert = request.user.expert_profile
#
#         if request.method == 'PATCH':
#             serializer = self.serializer_class(expert, data=request.data, partial=True)
#             serializer.is_valid(raise_exception=True)
#             serializer.save()
#
#             return Response(serializer.data)
#
#         serializer = self.serializer_class(expert)
#         return Response(serializer.data)


class WorkoutViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = WorkoutSerializer

    def get_queryset(self):
        return Workout.objects.filter(active=True)

    def perform_create(self, serializer):
        serializer.save()

    def perform_update(self, serializer):
        serializer.save()

    def perform_destroy(self, instance):
        instance.delete()


class WorkoutPlanViewSet(viewsets.ModelViewSet):
    serializer_class = WorkoutPlanSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user

        if hasattr(user, 'regular_profile'):
            return WorkoutPlan.objects.filter(user=user.regular_profile)
        elif hasattr(user, 'expert_profile'):
            expert = user.expert_profile
            # Lọc các WorkoutPlan từ user đang kết nối với expert này
            return WorkoutPlan.objects.filter(
                user__connected_trainer=expert
            ) if expert.expert_type == 'trainer' else WorkoutPlan.objects.filter(
                user__connected_nutritionist=expert
            )
        else:
            return WorkoutPlan.objects.none()  # hoặc raise lỗi nếu cần

    def perform_create(self, serializer):
        user = self.request.user
        if hasattr(user, 'regular_profile'):
            serializer.save(user=user.regular_profile)
        else:
            raise serializers.ValidationError("Chỉ người dùng thường mới được phép tạo kế hoạch tập luyện.")

    def perform_update(self, serializer):
        serializer.save()

    def perform_destroy(self, instance):
        instance.delete()

    @action(detail=True, methods=['post'], url_path='add-workout')
    def add_workout(self, request, pk=None):
        plan = self.get_object()
        workout_id = request.data.get('workout_id')
        date = request.data.get('date')
        workout = get_object_or_404(Workout, pk=workout_id)
        session = WorkoutSession.objects.create(
            workout_plan=plan,
            workout=workout,
            date=date
        )
        return Response(WorkoutSessionSerializer(session).data, status=201)

    @action(detail=True, methods=['delete'], url_path='remove-workout')
    def remove_workout(self, request, pk=None):
        plan = self.get_object()
        session_id = request.query_params.get('session_id')
        session = get_object_or_404(WorkoutSession, pk=session_id, workout_plan=plan)
        session.delete()
        return Response(status=204)

    @action(detail=True, methods=['post'], url_path='mark-completed')
    def mark_completed(self, request, pk=None):
        plan = self.get_object()
        plan.status = 'completed'
        plan.save()
        return Response({'status': 'WorkoutPlan marked as completed'})

    @action(detail=True, methods=['post'], url_path='mark-pending')
    def mark_pending(self, request, pk=None):
        plan = self.get_object()
        plan.status = 'pending'
        plan.save()
        return Response({'status': 'WorkoutPlan marked as pending'})


class MealViewSet(viewsets.ModelViewSet):
    queryset = Meal.objects.all()
    serializer_class = MealSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Meal.objects.filter(active=True)

    def perform_create(self, serializer):
        serializer.save()

    def perform_update(self, serializer):
        serializer.save()

    def perform_destroy(self, instance):
        instance.delete()

class MealPlanViewSet(viewsets.ModelViewSet):
    serializer_class = MealPlanSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user

        # Người dùng thường: chỉ thấy kế hoạch của họ
        if hasattr(user, 'regular_profile'):
            return MealPlan.objects.filter(user=user.regular_profile)

        # Expert xem được kế hoạch của các user đã kết nối
        elif hasattr(user, 'expert_profile'):
            expert = user.expert_profile
            if expert.expert_type == 'trainer':
                return MealPlan.objects.filter(user__connected_trainer=expert)
            else:
                return MealPlan.objects.filter(user__connected_nutritionist=expert)

        # Admin: xem tất cả
        elif user.role == UserRole.Admin:
            return MealPlan.objects.all()

        return MealPlan.objects.none()

    def perform_create(self, serializer):
        serializer.save()

    def perform_update(self, serializer):
        serializer.save()

    def perform_destroy(self, instance):
        instance.delete()

    @action(detail=True, methods=['post'], url_path='add-meal')
    def add_meal(self, request, pk=None):
        plan = self.get_object()
        data = request.data.copy()
        data['meal_plan'] = plan.id
        serializer = MealPlanMealSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=201)
        return Response(serializer.errors, status=400)

    @action(detail=True, methods=['delete'], url_path='remove-meal')
    def remove_meal(self, request, pk=None):
        plan = self.get_object()
        meal_id = request.query_params.get('meal_id')
        date = request.query_params.get('date')
        meal_time = request.query_params.get('meal_time')

        instance = MealPlanMeal.objects.filter(
            meal_plan=plan,
            meal_id=meal_id,
            date=date,
            meal_time=meal_time
        ).first()

        if not instance:
            return Response({'error': 'Không tìm thấy meal'}, status=404)

        instance.delete()
        return Response(status=204)


class HealthProfileViewSet(viewsets.ModelViewSet):
    serializer_class = HealthProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user

        # Người dùng thường: chỉ thấy kế hoạch của họ
        if hasattr(user, 'regular_profile'):
            return HealthProfile.objects.filter(user=user.regular_profile)

        # Expert xem được kế hoạch của các user đã kết nối
        elif hasattr(user, 'expert_profile'):
            expert = user.expert_profile
            if expert.expert_type == 'trainer':
                return HealthProfile.objects.filter(user__connected_trainer=expert)
            else:
                return HealthProfile.objects.filter(user__connected_nutritionist=expert)

        # Admin: xem tất cả
        elif user.role == UserRole.Admin:
            return HealthProfile.objects.all()



class HealthTrackingViewSet(viewsets.ModelViewSet):
    serializer_class = HealthTrackingSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user

        # Người dùng thường: chỉ thấy kế hoạch của họ
        if hasattr(user, 'regular_profile'):
            return HealthTracking.objects.filter(user=user.regular_profile)

        # Expert xem được kế hoạch của các user đã kết nối
        elif hasattr(user, 'expert_profile'):
            expert = user.expert_profile
            if expert.expert_type == 'trainer':
                return HealthTracking.objects.filter(user__connected_trainer=expert)
            else:
                return HealthTracking.objects.filter(user__connected_nutritionist=expert)

        # Admin: xem tất cả
        elif user.role == UserRole.Admin:
            return HealthTracking.objects.all()

    def perform_create(self, serializer):
        serializer.save(user=self.request.user.regular_profile)


class WorkoutSessionViewSet(viewsets.ModelViewSet):
    serializer_class = WorkoutSessionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return WorkoutSession.objects.filter(workout_plan__user=self.request.user.regular_profile)

    @action(detail=True, methods=['post'], url_path='mark-complete')
    def mark_complete(self, request, pk=None):
        session = self.get_object()
        session.status = 'completed'
        session.save()
        return Response({'status': 'WorkoutSession marked as completed'})

    @action(detail=True, methods=['post'], url_path='mark-pending')
    def mark_pending(self, request, pk=None):
        session = self.get_object()
        session.status = 'pending'
        session.save()
        return Response({'status': 'WorkoutSession marked as pending'})


class MealPlanMealViewSet(viewsets.ModelViewSet):
    serializer_class = MealPlanMealSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return MealPlanMeal.objects.filter(meal_plan__user=self.request.user.regular_profile)


class HealthJournalViewSet(viewsets.ModelViewSet):
    serializer_class = HealthJournalSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return HealthJournal.objects.filter(user=self.request.user.regular_profile)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user.regular_profile)


class ReminderViewSet(viewsets.ModelViewSet):
    serializer_class = ReminderSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Reminder.objects.filter(user=self.request.user.regular_profile)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user.regular_profile)


class ChatMessageViewSet(viewsets.ModelViewSet):
    serializer_class = ChatMessageCreateSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return ChatMessage.objects.filter(sender=user) | ChatMessage.objects.filter(receiver=user)

    def perform_create(self, serializer):
        serializer.save(sender=self.request.user)