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
    parser = argparse.ArgumentParser()
    parser.add_argument("conf_overrides_path")
    parser.add_argument("skin_conf_override_path")
    parser.add_argument("skin_systems_override_path")
    parser.add_argument("boot_logo_path")
    args = parser.parse_args()
    return args.conf_overrides_path, args.skin_conf_override_path, args.skin_systems_override_path, args.boot_logo_path


def main():
    conf_overrides_path, skin_conf_override_path, skin_systems_override_path, boot_logo_path = get_args()

    available_drives = [Path(f"{d}:") for d in string.ascii_uppercase if os.path.exists('%s:' % d)]
    boot_partition = find_boot_partition(available_drives)
    rarch_partition = find_retroarch_drive(available_drives)

    conf = Config(Path(conf_overrides_path), skin_conf_override_path, skin_systems_override_path,
                  boot_partition, rarch_partition, boot_logo_path)

    print(f"boot: {conf.boot_partition}")
    print(f"retroarch: {conf.rarch_partition}")
    print(f"garlic retroarch conf path: {conf.conf_override_path}")
    print(f"garlic skin path: {conf.skin_conf_override_path}")

    garlic_fp = fetch_garlic()
    apply_garlic(conf, garlic_fp)
    apply_config_overrides(conf)
    apply_skin_overrides(conf)
    apply_skin_system_overrides(conf)
    apply_boot_logo_override(conf)


if __name__ == '__main__':
    main()
