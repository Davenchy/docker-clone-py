import argparse
from os import getcwd

from app.docker_image import DockerImage, DockerImageDownloader
from app.utils import format_size, format_time

parser = argparse.ArgumentParser()
subparser = parser.add_subparsers()

pull_parser = subparser.add_parser(
    'pull',
    help="pull docker image from docker hub",
)

pull_parser.add_argument(
    'image_name', type=str,
    help="""image name to pull.\n
    Examples:
        library/ubuntu:latest OR library/ubuntu OR ubuntu OR ubuntu:latest""",
)

pull_parser.add_argument(
    "path", type=str, help="path to save downloaded image",
)

create_parser = subparser.add_parser(
    'create',
    help="create container from downloaded docker image"
)

create_parser.add_argument(
    'image', type=str, help="path to downloaded image",
)

create_parser.add_argument(
    'container_path', type=str, help='path to container filesystem/root',
)

exec_parser = subparser.add_parser(
    'exec',
    help="run container and execute command",
)

exec_parser.add_argument(
    "container_path", type=str,
    help="path to created container filesystem/root",
)

exec_parser.add_argument(
    "command", type=str, help="command to execute in container",
)

args = parser.parse_args()


def on_download_started(downloader: DockerImageDownloader):
    print('download started:', downloader.filename)


def on_download_completed(downloader: DockerImageDownloader):
    print('download completed:', downloader.filename)


def on_download_updated(downloader: DockerImageDownloader):
    msg = '({:.2f}%), Size: {}, Downloaded: {}, Speed: {}/s, \
    Estimated Time: {}'
    print(msg.format(
        downloader.progress * 100,
        format_size(downloader.total_size),
        format_size(downloader.downloaded),
        format_size(downloader.speed),
        format_time(downloader.estimated_time_remaining),
    ))


if __name__ == '__main__':
    dockerImage = DockerImage.from_image_name('library/ubuntu:latest')
    download_profile = dockerImage.create_download_profile('arm64')
    downloader = download_profile.create_downloader(getcwd())

    downloader.started.connect(on_download_started)
    downloader.updated.connect(on_download_updated)
    downloader.completed.connect(on_download_completed)

    downloader.start()

    print(f'Name: {downloader.filepath}')
    print(f'Size: {download_profile.size_human_readable}')
