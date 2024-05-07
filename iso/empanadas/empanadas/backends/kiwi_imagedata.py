from attrs import define, field
from typing import Dict

import json


@define(auto_attribs=True, kw_only=True)
class ImageInfo:
    compress: bool
    filename: str
    shasum: bool
    use_for_bundle: bool


@define(auto_attribs=True, kw_only=True)
class ImagesData:
    images: Dict[str, ImageInfo] = field(factory=dict)

    @staticmethod
    def from_json(data: str) -> 'ImagesData':
        json_data = json.loads(data)
        images = {key: ImageInfo(**value) for key, value in json_data.items()}

        return ImagesData(images=images)
