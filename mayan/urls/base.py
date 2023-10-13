from django.conf.urls import include, url


__all__ = ('urlpatterns',)

urlpatterns = [url(r"^account/", include("account.urls"))]
