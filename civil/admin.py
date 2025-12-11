from django.contrib import admin
from civil.models import *

# Register your models here.
class CompetenciaAdmin(admin.ModelAdmin):
    search_fields = ['nombre']
    # show all fields
    list_display = [field.name for field in Competencia._meta.fields]
    # show 100 records per page
    list_per_page = 20
    # show just last 1000 records
    list_max_show_all = 10000
    # change title
    admin.site.site_header = 'Administración de Causas Civiles'
    # change color header pager
    admin.site.index_title = 'Causas Civiles'
    # search like filter
    list_filter = ('nombre',)
    # set order
    ordering = ('id',)

class CorteAdmin(admin.ModelAdmin):
    search_fields = ['nombre']
    # show all fields
    list_display = [field.name for field in Corte._meta.fields]
    # show 100 records per page
    list_per_page = 20
    # show just last 1000 records
    list_max_show_all = 10000
    # change title
    admin.site.site_header = 'Administración de Causas Civiles'
    # change color header pager
    admin.site.index_title = 'Causas Civiles'
    # search like filter
    list_filter = ('nombre',)
    # set order
    ordering = ('id',)

class TribunalAdmin(admin.ModelAdmin):
    search_fields = ['nombre']
    # show all fields
    list_display = [field.name for field in Tribunal._meta.fields]
    # show 100 records per page
    list_per_page = 20
    # show just last 1000 records
    list_max_show_all = 10000
    # change title
    admin.site.site_header = 'Administración de Causas Civiles'
    # change color header pager
    admin.site.index_title = 'Causas Civiles'
    # search like filter
    list_filter = ('nombre',)
    # set order
    ordering = ('id',)

class LibroTipoAdmin(admin.ModelAdmin):
    search_fields = ['nombre']
    # show all fields
    list_display = [field.name for field in LibroTipo._meta.fields]
    # show 100 records per page
    list_per_page = 20
    # show just last 1000 records
    list_max_show_all = 10000
    # change title
    admin.site.site_header = 'Administración de Causas Civiles'
    # change color header pager
    admin.site.index_title = 'Causas Civiles'
    # search like filter
    list_filter = ('nombre',)
    # set order
    ordering = ('id',)

class CausaAdmin(admin.ModelAdmin):
    search_fields = ['rol', 'anio']
    # show all fields
    list_display = [field.name for field in Causa._meta.fields]
    # show 100 records per page
    list_per_page = 20
    # show just last 1000 records
    list_max_show_all = 10000
    # change title
    admin.site.site_header = 'Administración de Causas Civiles'
    # change color header pager
    admin.site.index_title = 'Causas Civiles'
    # search like filter
    list_filter = ('rol', 'anio')
    # set order
    ordering = ('id',)

admin.site.register(Competencia, CompetenciaAdmin)
admin.site.register(Corte, CorteAdmin)
admin.site.register(Tribunal, TribunalAdmin)
admin.site.register(LibroTipo, LibroTipoAdmin)
admin.site.register(Causa, CausaAdmin)