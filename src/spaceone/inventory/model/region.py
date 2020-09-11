from schematics import Model
from schematics.types import StringType, DictType


class Region(Model):
    region_code = StringType()
    region_type = StringType(default='GOOGLE_CLOUD')
    name = StringType(default='')
    tags = DictType(StringType, serialize_when_none=False)
