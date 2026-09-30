"""Маршруты для отзывов и комментариев."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from reviews.views import CommentViewSet, ReviewViewSet

review_router = DefaultRouter()
review_router.register(
    r'titles/(?P<title_id>\d+)/reviews',
    ReviewViewSet,
    basename='review'
)
review_router.register(
    r'titles/(?P<title_id>\d+)/reviews/(?P<review_id>\d+)/comments',
    CommentViewSet,
    basename='comment'
)

urlpatterns = [
    path('', include(review_router.urls)),
]
