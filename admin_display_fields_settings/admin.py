from django.contrib import admin
from django.core.exceptions import FieldDoesNotExist
from .forms import DisplayFieldsSettings
from .models import DisplaySettings
import json, types


class DisplayFieldsSettingsAdmin(admin.ModelAdmin):

    class Media:
        css = {
            "all": (
                "admin_display_fields_settings/admin/css/admin_display_fields_settings.css",
                "admin/css/forms.css",
            )
        }
        js = (
            "js/jquery.js",
            "admin_display_fields_settings/admin/js/jquery-ui.min.js",
            "admin_display_fields_settings/admin/js/admin_display_fields_settings.js",
        )

    def get_field(self, field_name):

        try:
            field = self.opts.get_field(field_name)
            return field.name
        except FieldDoesNotExist:
            if callable(field_name):
                attr = field_name
            elif hasattr(self, field_name):
                attr = getattr(self, field_name)
            else:
                attr = getattr(self.model, field_name)
            return getattr(attr, '__name__', None)

    def get_fields_names(self):
        response = []
        for field in self.list_display:

            name = None

            try:
                name = self.opts.get_field(field).verbose_name
            except FieldDoesNotExist:

                if isinstance(field, types.FunctionType):
                    if hasattr(field, 'short_description'):
                        name = getattr(field, 'short_description')
                    else:
                        field = field.__name__
                else:

                    if hasattr(self.model, field):
                        if field == '__str__' or field == '__unicode__':
                            name = self.model.__name__
                        else:
                            mth = getattr(self.model, field)
                            if hasattr(mth, 'short_description'):
                                name = getattr(mth, 'short_description')


            if name is None:
                name = field.replace('_', ' ')

            response.append([field, name.capitalize()])

        return response

    def get_display_settings(self, user):
        obj, created = DisplaySettings.objects\
            .get_or_create(user_id=user, app_label=self.opts.app_label,
                    model=self.model.__name__, view=self.__class__.__name__)

        settings = json.loads(obj.settings or '{}')
        settings['list_display'] = settings.get('list_display') or {}
        settings['list_display_sort'] = settings.get('list_display_sort') or {}

        return settings

    def get_list_display_settings_form(self, user, data=None):
        settings = self.get_display_settings(user)
        list_display = settings.get('list_display')
        list_display_sort = settings.get('list_display_sort')

        fields_names = self.get_fields_names()

        keyOrder = []
        if not list_display_sort:
            for field in fields_names:
                if isinstance(field[0], types.FunctionType):
                    if hasattr(field[0], 'short_description'):
                        name=getattr(field[0], 'short_description')
                        keyOrder.append(name)
                    else:
                        keyOrder.append(field[1])
                else:
                    keyOrder.append(field[0])
        else:
            if len(list_display_sort) > 0 \
                and isinstance(list_display_sort, list):
                    keyOrder = list_display_sort + \
                            [key for key in keyOrder
                             if key not in list_display_sort]

        fields = {}
        for field in fields_names:
            if isinstance(field[0], types.FunctionType):
                if hasattr(field[0], 'short_description'):
                    name=getattr(field[0], 'short_description')
                else:
                    name = field[1]
                fields[name] = {
                'label': name,
                'required': False,
                'class': 'forms.BooleanField'
                }
            else:
                fields[field[0]] = {
                'label': field[1],
                'required': False,
                'class': 'forms.BooleanField'
                }

        initial = {field: list_display.get(field, True) for field in fields.keys()}

        initial['sort_opts'] = ','.join(keyOrder)

        fields['sort_opts'] = {
            'required': True,
            'class': 'forms.CharField',
            'widget': 'forms.HiddenInput'
        }

        form = DisplayFieldsSettings(fields, initial=initial, data=data)

        keyOrder += ['sort_opts']
        form.fields.keyOrder = [field for field in keyOrder if field in fields]

        return form

    def get_list_display(self, request):
        """
        Return a sequence containing the fields to be displayed on the
        changelist.
        """

        response = []
        for field in list(self.list_display):
            if isinstance(field, types.FunctionType):
                if hasattr(field, 'short_description'):
                    name = getattr(field, 'short_description')
                    response.append(name)
                else:
                    field = field.__name__
                    name = field.replace('_', ' ')
                    response.append(name)
            else:
                response.append(field)

        settings = self.get_display_settings(request.user)
        list_display = settings.get('list_display')
        list_display_sort = settings.get('list_display_sort')

        if len(list_display) > 0:
            for field in tuple(response):
                if list_display.get(field) is False:
                    del response[response.index(field)]

        if len(list_display_sort) > 0 and len(response) > 1:
            for field in list(list_display_sort):
                if field not in response:
                    del list_display_sort[list_display_sort.index(field)]
                else:
                    del response[response.index(field)]

            response = list_display_sort + response
            new_response = []
            for f in list(self.list_display):
                name = f
                if isinstance(f, types.FunctionType):
                    name = getattr(f, 'short_description')
                if name in response:
                    new_response.append(f)
        else:
            new_response = list(self.list_display)

        self.list_editable = [field for field in self.list_editable if field in new_response]

        return new_response
