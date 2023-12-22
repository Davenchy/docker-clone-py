from __future__ import annotations
from typing import Dict, Any
from app.docker_hub_constants import BASE_ENDPOINT, BLOB_ENDPOINT
from app.utils import format_size, load_and_cache


class ImageLayer:
    def __init__(
            self, image_name: str, mediaType: str, size: int, digest: str):
        self.__image_name = image_name
        self.__mediaType = mediaType
        self.__size = size
        self.__digest = digest

    @property
    def image_name(self) -> str:
        """<repo>/<image>"""
        return self.__image_name

    @property
    def mediaType(self) -> str:
        return self.__mediaType

    @property
    def size(self) -> int:
        return self.__size

    @property
    def digest(self) -> str:
        return self.__digest

    @property
    def url(self):
        """generate and cache layer url"""
        def generator():
            return '{}/{}'.format(
                BASE_ENDPOINT, BLOB_ENDPOINT.format(
                    self.image_name, self.digest))
        return load_and_cache(self, '_ImageLayer__url', generator)

    @ property
    def extension(self) -> str:
        """generate and cache file extension of this layer"""
        def generator():
            if 'gzip' in self.mediaType[-4:].lower():
                return '.tar.gz'
            return '.tar'
        return load_and_cache(self, '_ImageLayer__extension', generator)

    @staticmethod
    def from_json(image_name: str, layer: Dict[str, Any]) -> ImageLayer:
        return ImageLayer(
            image_name,
            layer['mediaType'],
            layer['size'],
            layer['digest'],
        )

    def __str__(self):
        return f"ImageLayer(image: {self.image_name}, \
        size: {format_size(self.size)}, type: {self.mediaType}, \
        digest: {self.digest})"
