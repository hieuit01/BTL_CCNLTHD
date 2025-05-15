from rest_framework import viewsets, status, generics, permissions, parsers, serializers
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404

from .models import User, RegularUser, Expert, UserRole, TrackingMode, Review
from .serializers import UserSerializer, RegularUserSerializer, ExpertSerializer, ReviewSerializer
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
            elif role in [UserRole.TRAINER, UserRole.NUTRITIONIST]:
                return ExpertSerializer
            return UserSerializer
        return UserSerializer

    def create(self, request, *args, **kwargs):
        role = request.data.get('role')
        if role not in [UserRole.USER, UserRole.TRAINER, UserRole.NUTRITIONIST]:
            return Response({'error': 'Vai trò không hợp lệ'}, status=status.HTTP_400_BAD_REQUEST)

        data = request.data.copy()
        if role in [UserRole.TRAINER, UserRole.NUTRITIONIST]:
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


