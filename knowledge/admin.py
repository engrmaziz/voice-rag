from django.contrib import admin
from .models import Document

@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ('title', 'uploaded_at', 'ingested')
    actions = ['run_ingestion']

    @admin.action(description='Run ingestion for selected documents')
    def run_ingestion(self, request, queryset):
        for doc in queryset:
            print(f"Ingesting {doc.title}...")
        queryset.update(ingested=True)
