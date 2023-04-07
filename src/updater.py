import argparse
import os
import shutil
import string
from pathlib import Path

import multivolumefile
from bs4 import BeautifulSoup
import requests
from py7zr import SevenZipFile

from src.config import Config
from src.rarch_config import RarchConfig
from src.skin_config import SkinConfig


def find_boot_partition(partitions):
    for p in partitions:
        found = next((f for f in p.iterdir() if f.is_file() and f.name == 'uImage'), None)
        if found:
            return p


def find_retroarch_drive(partitions):
    for p in partitions:
        found = next((f for f in p.iterdir() if f.is_dir() and f.name == 'CFW'), None)
        if found:
            return p


def fetch_garlic(url: str = "https://www.patreon.com/posts/76561333", link_names=None):
    if link_names is None:
        link_names = ["RG35XX-CopyPasteOnTopOfStock.7z.001", "RG35XX-CopyPasteOnTopOfStock.7z.002"]

    headers = {
        'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:78.0) Gecko/20100101 Firefox/78.0',
        'Accept-Language': 'en-US,en;q=0.5',
        'Referer': url
    }

    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        raise Exception(f"Unable to download garlic, got response code {response.status_code}")

    soup = BeautifulSoup(response.content, "html.parser")
    links = soup.find_all("a", string=link_names)

    garlic_fp = Path.cwd().parent / "out/garlic"
    garlic_fp.mkdir(exist_ok=True, parents=True)

    # Loop through the links and download each file
    files = []
    links.sort(key=lambda l: l.string)
    for i, link in enumerate(links):
        url = link.get("href")

        filename = f"../out/RG35XX-CopyPasteOnTopOfStock.7z.{i + 1:03d}"
        files.append(Path(filename))
        response = requests.get(url)
        with open(filename, "wb") as f:
            f.write(response.content)
            print(f"downloaded... {filename} successfully!")

    if len(files) <= 0:
        raise Exception("Unable to extract, no files were found")

    root_file = files[0].parent / files[0].stem
    with multivolumefile.open(root_file, mode='rb') as target_archive:
        with SevenZipFile(target_archive, 'r') as archive:
            archive.extractall(path=garlic_fp.absolute())
    print("unzipped garlic")

    return garlic_fp


def apply_garlic(conf, garlic_fp):
    print("Updating boot partition...")
    shutil.copytree(garlic_fp / "misc", conf.boot_partition, dirs_exist_ok=True)
    print("Updating rarch partition...")
    shutil.copytree(garlic_fp / "roms", conf.rarch_partition, dirs_exist_ok=True)


def apply_config_overrides(conf: Config):
    print(f"starting to apply rarch config overrides...")
    config_file = conf.rarch_partition / "CFW" / "retroarch" / ".retroarch" / "retroarch.cfg"
    if not config_file.is_file():
        print(f"Could not find rarch conf file at {config_file}")
        return
    conf_backup = conf.rarch_partition / "CFW" / "retroarch" / ".retroarch" / "old.retroarch.cfg"

    shutil.copy(config_file, conf_backup)
    print(f"created {conf_backup} file.")
    current_conf = RarchConfig(config_file)
    current_conf.update_entries(conf.conf_override_path)
    current_conf.write_entries()
    print(f"applied overrides to config file.")


def apply_skin_overrides(conf: Config):
    print(f"starting to apply skin config overrides...")
    skin_conf_file = conf.rarch_partition / "CFW" / "skin" / "settings.json"
    if not skin_conf_file.is_file():
        print(f"Could not find skin conf file at {skin_conf_file}")
        return

    skin_conf = SkinConfig(skin_conf_file)
    skin_conf.update_entries(conf.skin_conf_override_path)
    skin_conf.write_entries()

    print(f"finished updating json config.")


def apply_skin_system_overrides(conf: Config):
    print(f"starting to apply skin systems images overrides...")
    skin_systems_dir = conf.rarch_partition / "CFW" / "skin" / "system"
    if not skin_systems_dir.is_dir():
        print(f"Could not find skin system folders at {skin_systems_dir}")
        return
    shutil.copytree(conf.skin_systems_override_path, skin_systems_dir, dirs_exist_ok=True)
    print(f"finished updating systems images config.")


def apply_boot_logo_override(conf):
    shutil.copy(conf.boot_logo_path, conf.boot_partition / "boot_logo.bmp.gz")


def get_args():
    parser = argparse.ArgumentParser(prog='RG35xx Onion Updater',
                                     description='Fetches the newest onion os update, applies it and optionally allows overriding some content automatically',
                                     epilog='Please support Garlic development at https://www.patreon.com/posts/76561333')
    parser.add_argument('-bp', '--boot_partition', help="hardcode boot partition (uimage file)", required=False)
    parser.add_argument('-rp', '--rarch_partition', help="hardcode retroarch partition (CFW folder)", required=False)
    parser.add_argument('-co', '--conf_override', help="conf_overrides_path", required=False)
    parser.add_argument('-so', '--skin_override_path', help="specify the file containing skin overrides here. "
                                                            "This should be a json only containing options to override",
                        required=False)
    parser.add_argument('-si', '--skin_icons_dir', help="path to a folder containing system icons to override",
                        required=False)
    parser.add_argument('-bl', '--boot_logo', help="Replace custom bootlogo with the specified file", required=False)

    args = parser.parse_args()
    return Config(Path(args.conf_override),
                  Path(args.skin_override_path),
                  Path(args.skin_icons_dir),
                  Path(args.boot_partition),
                  Path(args.rarch_partition),
                  Path(args.boot_logo))


def query_partition_letter(message: str, detected_path: Path) -> Path:
    manual_rarch_partition_letter = input(message)
    if manual_rarch_partition_letter:
        rarch_manual_partition_path = Path(f"{manual_rarch_partition_letter}:")
        if rarch_manual_partition_path.exists():
            return rarch_manual_partition_path
        else:
            raise Exception(f"Unable to find partition for the given letter {manual_rarch_partition_letter}")
    return detected_path


def main():
    config = get_args()

    available_drives = [Path(f"{d}:") for d in string.ascii_uppercase if os.path.exists('%s:' % d)]
    boot_partition = None
    rarch_partition = None

    if not config.boot_partition or not config.boot_partition.exists():
        boot_partition = find_boot_partition(available_drives)
        boot_partition = query_partition_letter(
            f"Boot partition: {boot_partition} - press enter to continue, else enter the partition letter manually:\n",
            boot_partition)

    if not config.rarch_partition or not config.rarch_partition.exists():
        rarch_partition = find_retroarch_drive(available_drives)
        rarch_partition = query_partition_letter(
            f"Retroarch partition: {rarch_partition} - press enter to continue, else enter the partition letter manually:\n",
            rarch_partition)

    if not boot_partition or not rarch_partition:
        raise Exception(f"Unable to continue, partitions not specified. Please check boot and retroarch partitions:"
                        f"\n - boot: {boot_partition}\n - rarch: {rarch_partition}")

    config.boot_partition = Path(boot_partition)
    config.rarch_partition = Path(rarch_partition)

    print("=========================================================")
    print(f"boot: {config.boot_partition}")
    print(f"retroarch: {config.rarch_partition}")
    print(f"garlic retroarch conf path: {config.conf_override_path}")
    print(f"garlic skin path: {config.skin_conf_override_path}")
    print("=========================================================")

    garlic_fp = fetch_garlic()
    apply_garlic(config, garlic_fp)


    print("Applying overrides...")
    if config.conf_override_path:
        apply_config_overrides(config)
    if config.skin_conf_override_path:
        apply_skin_overrides(config)
    if config.skin_systems_override_path:
        apply_skin_system_overrides(config)
    if config.boot_logo_path:
        apply_boot_logo_override(config)


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(e)
