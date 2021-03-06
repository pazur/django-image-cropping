from django.db import models
from django import forms
from django.conf import settings
from django.utils.text import capfirst

from .widgets import ImageCropWidget, CropForeignKeyWidget, ImageMultipleRatioWidget


class ImageCropField(models.ImageField):
    def formfield(self, *args, **kwargs):
        kwargs['widget'] = ImageCropWidget
        return super(ImageCropField, self).formfield(*args, **kwargs)

    def south_field_triple(self):
        """
        Return a suitable description of this field for South.
        """
        # We'll just introspect ourselves, since we inherit.
        from south.modelsinspector import introspector
        field_class = "django.db.models.fields.files.ImageField"
        args, kwargs = introspector(self)
        return (field_class, args, kwargs)


class CropForeignKey(models.ForeignKey):
    '''
    A croppable image field contained in another model. Only works in admin
    for now, as it uses the raw_id widget.
    '''

    def __init__(self, model, field_name, *args, **kwargs):
        self.field_name = field_name
        super(CropForeignKey, self).__init__(model, *args, **kwargs)

    def formfield(self, *args, **kwargs):
        kwargs['widget'] = CropForeignKeyWidget(self.rel, field_name=self.field_name,
            using=kwargs.get('using'))
        return super(CropForeignKey, self).formfield(*args, **kwargs)

    def south_field_triple(self):
        """
        Return a suitable description of this field for South.
        """
        # We'll just introspect ourselves, since we inherit.
        from south.modelsinspector import introspector
        field_class = "django.db.models.fields.related.ForeignKey"
        args, kwargs = introspector(self)
        return (field_class, args, kwargs)


class ImageRatioField(models.CharField):
    def __init__(self, image_field, size, adapt_rotation=False, allow_fullsize=False, verbose_name=None,
                 size_warning=getattr(settings, 'IMAGE_CROPPING_SIZE_WARNING', False)):
        self.width, self.height = size.split('x')
        self.image_field = image_field
        self.adapt_rotation = adapt_rotation
        self.allow_fullsize = allow_fullsize
        self.size_warning = size_warning
        super(ImageRatioField, self).__init__(max_length=255, blank=True, verbose_name=verbose_name)

    def formfield(self, *args, **kwargs):
        kwargs['widget'] =  forms.TextInput(attrs={
            'data-width': int(self.width),
            'data-height': int(self.height),
            'data-image-field': self.image_field,
            'data-my-name': self.name,
            'data-adapt-rotation': str(self.adapt_rotation).lower(),
            'data-allow-fullsize': str(self.allow_fullsize).lower(),
            'data-size-warning': str(self.size_warning).lower(),
            'class': 'image-ratio',
        })
        return super(ImageRatioField, self).formfield(*args, **kwargs)

    def south_field_triple(self):
        """
        Return a suitable description of this field for South.
        """
        # We'll just introspect ourselves, since we inherit.
        from south.modelsinspector import introspector
        field_class = "django.db.models.fields.CharField"
        args, kwargs = introspector(self)
        return (field_class, args, kwargs)


class ImageMultipleRatioField(ImageRatioField):
    def __init__(self, image_field, sizes, *args, **kwargs):
        self.sizes = sizes
        super(ImageMultipleRatioField, self).__init__(image_field, '0x0', *args, **kwargs)

    def formfield(self, *args, **kwargs):
        text_input_attrs = {
            'data-image-field': self.image_field,
            'data-my-name': self.name,
            'data-adapt-rotation': str(self.adapt_rotation).lower(),
            'data-allow-fullsize': str(self.allow_fullsize).lower(),
            'data-size-warning': str(self.size_warning).lower(),
            'class': 'image-ratio multiple-ratio',
        }
        choices = zip(self.sizes, self.sizes)
        defaults = {'required': not self.blank,
            'label': capfirst(self.verbose_name),
            'help_text': self.help_text,
        }
        defaults.update(kwargs)
        return ImageMultipleRatioFormField(choices, text_input_attrs, *args, **defaults)

    def to_python(self, value):
        if(isinstance(value, Ratio)):
            return value
        if(len(value.split(',')) == 4):
            return Ratio('', value)
        return Ratio(*value.split(',', 1))

    def get_prep_value(self, value):
        return value.to_str()

    __metaclass__ = models.SubfieldBase


class Ratio(object):
    def __init__(self, ratio='', coordinates=''):
        self.ratio = ratio
        self.coordinates = coordinates

    def __str__(self):
        return self.coordinates

    def to_str(self):
        if not self.ratio:
            return self.coordinates
        return "%s,%s" % (self.ratio, self.coordinates)

    def __len__(self):
        return len(self.to_str())

    def __repr__(self):
        return str(self)
    
    def split(self, *args, **kwargs):
        return self.coordinates.split(*args, **kwargs)


class ImageMultipleRatioFormField(forms.MultiValueField):
    def __init__(self, ratio_choices, text_input_attrs, *args, **kwargs):
        fields = (
            forms.ChoiceField(ratio_choices),
            forms.CharField(),
        )
        kwargs['widget'] = ImageMultipleRatioWidget(ratio_choices, text_input_attrs)
        super(ImageMultipleRatioFormField, self).__init__(fields, *args, **kwargs)

    def compress(self, values):
        if not values:
            return Ratio()
        return Ratio(values[0], values[1])
