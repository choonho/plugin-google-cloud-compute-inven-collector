from schematics import Model
from schematics.types import StringType, DictType


class Region(Model):
    region_code = StringType()
    provider = StringType(default="google_cloud")
    name = StringType(default='')
    tags = DictType(StringType, serialize_when_none=False)
