from rest_framework.pagination import PageNumberPagination


class HealthPagination(PageNumberPagination):
    page_size = 3