from django.contrib import admin
from .models import *


class BaseAdmin(admin.ModelAdmin):
    list_display = ("__str__", "created_at", "updated_at")
    readonly_fields = ("created_at", "updated_at")


# Register your models here.
admin.site.register(Company, BaseAdmin)
admin.site.register(Profile, BaseAdmin)
admin.site.register(Invoice, BaseAdmin)
admin.site.register(Pocket, BaseAdmin)
