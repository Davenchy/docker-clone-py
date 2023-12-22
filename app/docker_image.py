"""This module contains the DockerImage class that fetches the image manifest
files, the DockerImageDownloadProfile which contains information about the
chosen architecture and the layers of the image
and finally the DockerImageDownloader class that downloads the image layers
into single tar/tar.gz file

VIP: The DockerImageDownloader contains signal objects to listen for
download state changes, check signal.py for more information"""

from __future__ import annotations
from typing import IO, List, Dict, Tuple, Any
from functools import reduce
from time import time
import requests
import json
import os

from app.docker_hub_constants import BASE_ENDPOINT, TOKEN_ENDPOINT
from app.image_layer import ImageLayer
from app.signal import Signal
from app.utils import format_size, load_and_cache


class DockerImageError(Exception):
    pass


class DockerImage:
    def __init__(self, repo: str, name: str, tag: str):
        self.__repo = repo
        self.__name = name
        self.__tag = tag

    @ property
    def repo(self) -> str:
        return self.__repo

    @ property
    def name(self) -> str:
        return self.__name

    @ property
    def tag(self) -> str:
        return self.__tag

    @ property
    def image_scope(self) -> str:
        """<repo>/<image>"""
        return f"{self.repo}/{self.name}"

    @ property
    def image_name(self) -> str:
        """<repo>/<image>:<tag>"""
        return f"{self.image_scope}:{self.tag}"

    @ property
    def token(self) -> str:
        def generator():
            return DockerImage.request_access_token(self.image_scope)
        return load_and_cache(self, '_DockerImage__token', generator)

    @ property
    def image_manifests(self) -> Dict[str, Any]:
        def generator():
            return self.request_image_manifests(
                self.image_scope, self.tag, self.token)
        return load_and_cache(self, '_DockerImage__images_manifest', generator)

    @ property
    def manifests_list(self) -> List[Dict[str, Any]]:
        """{
      "digest": "sha256:3a6c58f84a3ca8af9a5bcd...",
      "mediaType": "application/vnd.docker.distribution.manifest.v2+json",
      "platform": {
        "architecture": "amd64",
        "os": "linux"
      },
      "size": 528
    }
        """
        return self.image_manifests["manifests"]

    @ property
    def platforms(self) -> List[Dict[str, Any]]:
        return [mani['platform'] for mani in self.manifests_list]

    @ property
    def get_arches(self) -> List[str]:
        return [platform["architecture"] for platform in self.platforms]

    def get_image_by_arch(self, arch: str) -> Dict[str, Any]:
        for mini in self.manifests_list:
            if mini['platform']["architecture"] == arch:
                return mini
        raise DockerImageError("No image for arch: {}".format(arch))

    def get_arch_image_digest(self, arch: str) -> str:
        return self.get_image_by_arch(arch)["digest"]

    def get_image_manifest(self, arch: str) -> Dict[str, Any]:
        def generator():
            digest = self.get_arch_image_digest(arch)
            url = f"{BASE_ENDPOINT}/{self.image_scope}/manifests/{digest}"
            res = requests.get(url, headers={
                "Authorization": f"Bearer {self.token}",
                "Accept": "application/vnd.oci.image.manifest.v1+json",
            })

            if res.ok:
                return res.json()
            raise DockerImageError(
                f"Failed to get manifest: {res.status_code}: {res.text}")
        return load_and_cache(
            self, '_DockerImage__image_manifest_{}'.format(arch), generator)

    def get_layers(self, arch: str) -> List[ImageLayer]:
        """returns list of layers for an arch image

        Format:
            {
              "mediaType": "application/...",
              "size": 29547485,
              "digest": "sha256:a486411936734b0d1d...",
              "url": "https://..."
            }"""
        return [
            ImageLayer.from_json(self.image_scope, layer)
            for layer in self.get_image_manifest(arch)['layers']
        ]

    @ staticmethod
    def parse_image_name(image_name: str) -> Tuple[str, str, str]:
        """parse passed image name into <repo>, <name> and <tag>

        Examples:
            >>> parse_image_name("library/ubuntu:latest")
            library, ubuntu, latest

            >>> parse_image_name("ubuntu:14.04")
            library, ubuntu, 14.04

            >>> parse_image_name("ubuntu")
            library, ubuntu, latest"""
        repo, name, tag = 'library', None, 'latest'

        if '/' in image_name:
            repo, image_name = image_name.split('/')

        if ':' in image_name:
            name, tag = image_name.split(':')

        name = name if name is not None else image_name
        return (repo, name, tag)

    @ staticmethod
    def from_image_name(image_name: str) -> "DockerImage":
        """create DockerImage from <repo>/<image>:<tag>

        All the next image names are the same:
            library/ubuntu:latest
            ubuntu:latest
            ubuntu"""
        repo, name, tag = DockerImage.parse_image_name(image_name)
        return DockerImage(repo, name, tag)

    @ staticmethod
    def request_access_token(image_name: str) -> str:
        response = requests.get(TOKEN_ENDPOINT.format(image_name))
        if response.ok:
            return response.json()["token"]
        raise DockerImageError(
            f"Failed to get token: {response.status_code}: {response.text}")

    @ staticmethod
    def request_image_manifests(
            image_name: str, tag: str, token: str) -> Dict[str, Any]:
        repository_url = f"{BASE_ENDPOINT}/{image_name}/manifests/{tag}"
        response = requests.get(repository_url, headers={
            "Authorization": f"Bearer {token}",
            "Accept": ", ".join([
                "application/vnd.docker.distribution.manifest.v2+json",
                "application/vnd.docker.distribution.manifest.list.v2+json",
            ]),
        })

        if response.ok:
            return response.json()
        if response.status_code == 401:
            raise DockerImageError(
                "Failed to get manifests: Required Token: {}".format(
                    response.headers['Www-Authenticate']
                )
            )
        raise DockerImageError(
            f"Failed to get manifests: {response.status_code}: {response.text}"
        )

    def print_image_manifests(self, indent: int = 2):
        print(json.dumps(self.image_manifests, indent=indent))

    def print_image_manifest(self, arch: str, indent: int = 2):
        print(json.dumps(self.get_image_manifest(arch), indent=indent))

    def print_layers(self, arch: str, indent: int = 2):
        print(json.dumps(self.get_layers(arch), indent=indent))

    def create_download_profile(self, arch: str) -> DockerImageDownloadProfile:
        return DockerImageDownloadProfile(self, arch)


class DockerImageDownloadProfile:
    def __init__(self, dockerImage: DockerImage, arch: str):
        self.__dockerImage = dockerImage
        self.__arch = arch

    @ property
    def layers(self) -> List[ImageLayer]:
        return self.__dockerImage.get_layers(self.__arch)

    @ property
    def size(self) -> int:
        return reduce(lambda sum, layer: sum + layer.size, self.layers, 0)

    @ property
    def name(self) -> str:
        repo = self.__dockerImage.repo
        image = self.__dockerImage.name
        tag = self.__dockerImage.tag
        return f'{repo}-{image}-{tag}-{self.__arch}'

    @ property
    def arch(self) -> str:
        return self.__arch

    @ property
    def size_human_readable(self) -> str:
        return format_size(self.size)

    @ property
    def file_extension(self) -> str:
        return self.layers[0].extension

    @ property
    def file_name(self) -> str:
        return f'{self.name}{self.file_extension}'

    def create_downloader(self, path: str) -> DockerImageDownloader:
        return DockerImageDownloader(self, path)


class DockerImageDownloader:
    chunk_size: int = 1024

    def __init__(self, downloadProfile: DockerImageDownloadProfile, path: str):
        self.__profile = downloadProfile
        self.__path = path
        self.__downloaded = 0
        self.__size = downloadProfile.size
        self.__is_downloading = False
        self.__bytes_per_sec: int = 0
        self.__signal_download_started = Signal('Download Started')
        self.__signal_download_updated = Signal('Download Updated')
        self.__signal_download_completed = Signal('Download Completed')

    @property
    def started(self) -> Signal:
        """Signal emits on downloader download started"""
        return self.__signal_download_started

    @property
    def updated(self) -> Signal:
        """Signal emits on downloader download progress updated"""
        return self.__signal_download_updated

    @property
    def completed(self) -> Signal:
        """Signal emits on downloader download completed"""
        return self.__signal_download_completed

    @ property
    def profile(self) -> DockerImageDownloadProfile:
        """The download profile for more information"""
        return self.__profile

    @ property
    def progress(self) -> float:
        """The download process progress between 0 and 1"""
        return self.__downloaded / self.__size

    @ property
    def downloaded(self) -> int:
        """The downloaded bytes count"""
        return self.__downloaded

    @ property
    def total_size(self) -> int:
        """The total size of the image as in the manifest file"""
        return self.__size

    @ property
    def current_size(self) -> int:
        """The actual written bytes count"""
        return os.path.getsize(self.filepath) if self.is_exists else 0

    @ property
    def filename(self) -> str:
        return self.__profile.file_name

    @ property
    def download_path(self) -> str:
        return self.__path

    @ property
    def filepath(self) -> str:
        """The full path to the downloaded image"""
        return os.path.join(self.__path, self.filename)

    @ property
    def estimated_time_remaining(self) -> int:
        """Estimated time remaining in seconds"""
        return round(self.current_size / self.total_size * self.speed)

    @ property
    def is_downloading(self) -> bool:
        return self.__is_downloading

    @ property
    def is_exists(self) -> bool:
        return os.path.exists(self.filepath)

    @property
    def speed(self) -> int:
        """Downloaded bytes per second"""
        return self.__bytes_per_sec

    def start(self, resume: bool = True):
        """Start downloading the image to the specified path"""
        # is already downloading??
        if self.__is_downloading:
            return

        self.__downloaded = 0  # reset downloaded bytes tracker for recheck

        # if not resume then reset downloaded data if any
        if not resume and self.is_exists:
            os.remove(self.filepath)

        # if any data is already downloaded then resume
        if self.is_exists:
            self.__downloaded = self.current_size

        is_resuming = self.__downloaded > 0
        self.__is_downloading = True
        self.__signal_download_started.emit(self)
        with open(self.filepath, 'ab' if is_resuming else 'wb') as file:
            while self.__downloaded < self.total_size:
                self._download_next_layer(file)
        self.__is_downloading = False
        self.__signal_download_completed.emit(self)

    def _get_next_layer(self) -> Tuple[ImageLayer, int] | None:
        """Returns the next layer to be downloaded and its already downloaded
        bytes"""
        sum = 0
        for layer in self.__profile.layers:
            sum += layer.size
            if sum > self.__downloaded:
                remaining = sum - self.__downloaded
                return layer, layer.size - remaining
        return None

    def _download_next_layer(self, file: IO):
        """Downloads the next layer"""
        # get next layer and its downloaded bytes
        next_layer_info = self._get_next_layer()
        # check if no more layers
        if next_layer_info is None:
            return

        layer, layer_downloaded = next_layer_info

        start_time = time()

        # start downloading after layer downloaded bytes
        res = requests.get(layer.url, stream=True, headers={
            'Range': f"bytes={layer_downloaded}-"
        })

        # write downloaded layer as chunks to disk
        for chunk in res.iter_content(chunk_size=self.chunk_size):
            if chunk:
                file.write(chunk)
                self.__downloaded += len(chunk)

        end_time = time()
        delta_time = end_time - start_time
        downloaded_bytes = layer.size - layer_downloaded
        self.__bytes_per_sec = round(downloaded_bytes / delta_time)
        self.__signal_download_updated.emit(self)
