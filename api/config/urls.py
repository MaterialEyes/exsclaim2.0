from django.conf import settings
from django.urls import path, re_path, include, reverse_lazy
from django.conf.urls.static import static
from django.contrib import admin
from django.views.generic.base import RedirectView
from rest_framework.routers import DefaultRouter
from rest_framework.authtoken import views
from apps.exsclaim.views import (
    ArticleViewSet,
    FigureViewSet,
    SubfigureViewSet,
    ScaleBarViewSet,
    ScaleBarLabelViewSet,
    SubfigureLabelViewSet,
    QueryViewSet
)

router = DefaultRouter()
router.register(r'articles', ArticleViewSet)
router.register(r'figures', FigureViewSet)
router.register(r'subfigures',SubfigureViewSet)
router.register(r'scalebars', ScaleBarViewSet)
router.register(r'scalebarlabels', ScaleBarLabelViewSet)
router.register(r'subfigurelabels', SubfigureLabelViewSet)
router.register(r'query', QueryViewSet)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/', include(router.urls)),

    # the 'api-root' from django rest-frameworks default router
    # http://www.django-rest-framework.org/api-guide/routers/#defaultrouter
    re_path(r'^$', RedirectView.as_view(url=reverse_lazy('api-root'), permanent=False)),

] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
