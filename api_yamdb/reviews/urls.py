"""Маршруты для отзывов и комментариев."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from reviews.views import (
    CategoryViewSet,
    CommentViewSet,
    GenreViewSet,
    ReviewViewSet,
    TitleViewSet,
)

review_router = DefaultRouter()
review_router.register('categories', CategoryViewSet)
review_router.register('genres', GenreViewSet)
review_router.register('titles', TitleViewSet)
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
