from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import UserViewSet, TrainerViewSet, NutritionistViewSet

router = DefaultRouter()
router.register(r'users', UserViewSet, basename='user')
router.register(r'trainers', TrainerViewSet, basename='trainer')
router.register(r'nutritionists', NutritionistViewSet, basename='nutritionist')

urlpatterns = [
    path('api/', include(router.urls)),
]
