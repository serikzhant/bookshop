from django.contrib import admin
from django.urls import include, path, re_path
from rest_framework.routers import SimpleRouter

from store.views import BookViewSet, UserBookRelationView, auth


router = SimpleRouter()

router.register(r'book', BookViewSet)
router.register(r'book_relation', UserBookRelationView)

urlpatterns = [
    path('admin/', admin.site.urls),
    re_path('', include('social_django.urls', namespace='social')),
    path('auth/', auth),
]

urlpatterns += router.urls
