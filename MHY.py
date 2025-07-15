import requests
from requests.exceptions import HTTPError, Timeout, RequestException
from tqdm import tqdm

import json, re, os, sys
import hashlib
import argparse


class GameNotFound(Exception):
    pass


class VersionNotFound(Exception):
    pass


class OSManager:
    @staticmethod
    def exit(exit_code: int = 0):
        os._exit(exit_code)


class InputTools:
    @staticmethod
    def simple_select(
        data_type, prompt: str, loop: bool = True, response: str = None
    ) -> str:
        while True:
            try:
                return data_type(input(prompt))
            except ValueError:
                print(response)
                if not loop:
                    break
            except KeyboardInterrupt:
                print("\nUser canceled.")
                OSManager.exit(0)
        return

    @staticmethod
    def simple_yn(
        prompt: str,
        choices: list[tuple[str, ...], tuple[str, ...]] = [
            ("no", "n", "false", "0"),
            ("yes", "y", "true", "1"),
        ],
        case_sensitive: bool = False,
        default_choice: bool = None,
    ):
        try:
            user_choice: str = (
                input(prompt) if case_sensitive else input(prompt).lower()
            )
        except KeyboardInterrupt:
            print("\nUser canceled.")
            OSManager.exit(0)

        if user_choice in choices[0]:  # False
            return False
        elif user_choice in choices[1]:  # True
            return True
        return default_choice


class ApiHandler:
    def __init__(self):
        self.api: str = "https://sg-hyp-api.hoyoverse.com/hyp/hyp-connect/api/getGamePackages?launcher_id=VYTpXlbWo8"

    def send_request(self, attempt: int = 3):
        while attempt > 0:
            try:
                response: requests.models.Response = requests.get(self.api, timeout=10)

                response.raise_for_status()

                return response.json()

            except HTTPError as http_err:
                print(f"HTTP error occurred: {http_err}")
            except Timeout as timeout_err:
                print(f"Timeout error occurred: {timeout_err}")
            except RequestException as req_err:
                print(f"Error occurred during the request: {req_err}")
            except Exception as err:
                print(f"An unexpected error occurred: {err}")

        print("Max retries reached. Exiting.")
        OSManager.exit(1)


class GameListMaker:
    def __init__(self):
        response: requests.models.Response = ApiHandler().send_request()
        self.game_ids: list[str] = [
            (item["game"]["id"], item["game"]["biz"])
            for item in response["data"]["game_packages"]
        ]
        self.urls: list[str] = [
            item["main"]["major"]["game_pkgs"][0]["url"]
            for item in response["data"]["game_packages"]
        ]

    def save_gamelist(self, game_dict: dict):
        try:
            with open("gamelist.json", "w", encoding="utf-8") as file:
                json.dump(game_dict, file, indent=4)
        except IOError:
            print("Unable to write file.")

    def main(self):
        game_dict: dict[str:str] = {}

        print(
            "Each game is identified by an ID. Use this tool to name the corresponding game ID."
        )

        try:
            for (ids, biz), url in zip(self.game_ids, self.urls):
                print(f"\nFile name: {url.split('/')[-1]}\nURL: {url}")
                name: str = input(f"BIZ: {biz}\nID: {ids} -> ")
                game_dict[ids] = name.strip()
        except KeyboardInterrupt:
            print("\nUser canceled.")
            OSManager.exit(0)

        if not InputTools.simple_yn(
            prompt="\nConfirm completion and save changes (y/N) ", default_choice=False
        ):
            self.main()

        self.save_gamelist(game_dict)


class ApiParser:
    def __init__(self):
        self.json_response: dict = ApiHandler().send_request()
        self.json_response = self.json_response["data"]["game_packages"]

    def _convert_bytes(self, byte_size: int) -> str:
        units = ["B", "KB", "MB", "GB"]

        if not byte_size:
            return "0 B"

        i = 0
        while byte_size >= 1024 and i < len(units) - 1:
            byte_size /= 1024.0
            i += 1

        return f"{byte_size:.2f} {units[i]}"

    def _get_gamelist(self) -> dict:
        with open("gamelist.json", "r", encoding="utf-8") as file:
            return json.load(file)

    def select_game(self) -> str:
        gamelist: dict = self._get_gamelist()
        list_of_id_games: list[str] = list(gamelist)

        print("Games available:")
        for index in range(len(list_of_id_games)):
            print(f"({index + 1}) {gamelist[list_of_id_games[index]]}")

        selected_game: int = (
            InputTools.simple_select(
                data_type=int,
                prompt="Select game: ",
                loop=True,
                response="Invalid input! Please enter a valid number.",
            )
            - 1
        )

        return list_of_id_games[selected_game]

    def find_game(self, game_id: str) -> int:
        for game_index in range(len(self.json_response)):
            if self.json_response[game_index]["game"]["id"] == game_id:
                return game_index
        raise GameNotFound("The requested game ID was not found.")

    def is_pre_download(self, game_index: int) -> bool:
        game_item: dict = self.json_response[game_index]
        if (
            "pre_download" in list(game_item)
            and game_item["pre_download"]["major"] != None
        ):
            return True
        return False

    def get_game_main(
        self, game_index: int, parse_game_version: callable
    ) -> dict:  # main or pre_download
        if self.is_pre_download(game_index) and InputTools.simple_yn(
            prompt="Pre-download available. Pre-download? (Y/n) ", default_choice=True
        ):
            game_main: dict = self.json_response[game_index]["pre_download"]

            if parse_game_version == self.get_game_major:
                print(
                    "\nNOTICE: To select patches for a specific update version, add the -p/--patches argument. Currently working with the full game."
                )
        else:
            game_main: dict = self.json_response[game_index]["main"]

        return game_main

    def get_game_major(self, game_main: dict) -> dict:
        game_major: dict = game_main["major"]
        print(f"\nVersion: {game_major['version']}\n")
        return game_major

    def get_game_patches(self, game_main: dict) -> dict:
        game_patches: dict = game_main["patches"]

        version_list: list = [
            f"({index + 1}) {game_patches[index]['version']}"
            for index in range(len(game_patches))
        ]
        version_print: str = "\n=> ".join(version_list)

        while True:
            print(f"Available Versions:\n=> {version_print}")

            previous_ver: int = InputTools.simple_select(
                data_type=int,
                prompt="Select current version: ",
                loop=True,
                response="Invalid input! Please enter a valid number.",
            )

            if 0 > previous_ver or previous_ver > len(game_patches):
                print(VersionNotFound("Requested version not found."))
            else:
                break

        print(f"Selected: {version_list[previous_ver - 1]}\n")
        return game_patches[previous_ver - 1]

    def _print_pkg_info(
        self,
        total_size,
        total_decompressed_size,
        languages,
        audio_total_size,
        audio_total_decompressed_size,
    ):
        print("Total size (game_pkgs):")
        print(f"=> Compressed: {self._convert_bytes(total_size)}")
        print(f"=> Decompressed: {self._convert_bytes(total_decompressed_size)}")

        print(f"\nTotal size (audio_pkgs={languages}):")
        print(f"=> Compressed: {self._convert_bytes(audio_total_size)}")
        print(
            f"=> Decompressed: {self._convert_bytes(audio_total_decompressed_size)}\n"
        )

    def get_game_pkgs(
        self,
        game_major: dict,
        types: list = ["game_pkgs", "audio_pkgs"],
        languages: list[str, ...] = ["en-us"],
        print_info: bool = False,
    ) -> list[tuple[str, int, str], ...]:
        pkgs: list[dict] = [game_major.get(t) for t in set(types) if game_major.get(t)]
        languages = set(languages)

        total_size = total_decompressed_size = 0
        audio_total_size = audio_total_decompressed_size = 0
        lst_of_pkgs: list[tuple[str, int, str], ...] = []
        for pkg in pkgs:
            for pkg_info in pkg:
                if print_info:
                    for key, value in pkg_info.items():
                        print(f"{key}: {value}")
                    print()

                # The code below checks whether pkg_info should be added to lst_of_pkgs (download queue) or not
                if (
                    "language" in pkg_info
                ):  # Check if pkg_info is information about an audio file. Determined by the existence of the 'language' key
                    if (
                        pkg_info["language"] in languages
                    ):  # If it is the audio file information of the requested language, add it to the download queue.
                        audio_total_size += int(pkg_info["size"])
                        audio_total_decompressed_size += int(
                            pkg_info["decompressed_size"]
                        )
                    else:  # If it is audio file information but not the requested language, do not add it to the download queue.
                        continue
                else:  # If it's not an audio file info but a game file, add it to the download queue by default.
                    total_size += int(pkg_info["size"])
                    total_decompressed_size += int(pkg_info["decompressed_size"])

                lst_of_pkgs.append(
                    (pkg_info["url"], int(pkg_info["size"]), pkg_info["md5"])
                )

        self._print_pkg_info(
            total_size,
            total_decompressed_size,
            languages,
            audio_total_size,
            audio_total_decompressed_size,
        )
        return lst_of_pkgs

    def main(
        self,
        version: str = "major",
        types: list = ["game_pkgs", "audio_pkgs"],
        languages: list[str, ...] = ["en-us"],
        print_info: bool = False,
    ) -> list[tuple[str, int, str], ...]:
        parse_game_version = (
            self.get_game_major if version == "major" else self.get_game_patches
        )

        game_id: str = self.select_game()
        game_index: int = self.find_game(game_id)
        game_main: dict = self.get_game_main(game_index, parse_game_version)

        game_major: dict = parse_game_version(game_main)

        return self.get_game_pkgs(
            game_major, types=types, languages=languages, print_info=print_info
        )


class Downloader:
    def __init__(self, path: str = ""):
        self.path: str = path

    def download_file(self, url: str, filename: str, filesize: int, md5: str):
        tmp_filename = filename + ".tmp"
        tmp_filepath = os.path.join(self.path, tmp_filename)
        final_filepath = os.path.join(self.path, filename)

        if os.path.exists(final_filepath):
            print(f'File "{filename}" already exists. Checking CRC...')
            if CheckHash.check_md5(final_filepath, md5):
                print(f"Skip download: {filename} is valid.")
                return
            else:
                print(f"CRC failed! Re-downloading: {filename}")
                os.remove(final_filepath)

        downloaded = 0
        if os.path.exists(tmp_filepath):
            downloaded = os.path.getsize(tmp_filepath)

        headers = {}
        if downloaded > 0:
            headers["Range"] = f"bytes={downloaded}-"
            print(f"Resuming {filename} from byte {downloaded} ({downloaded/1073741824:.2f}GB)")

        try:
            with requests.get(
                url, stream=True, headers=headers, timeout=10
            ) as response:
                if response.status_code in (200, 206):
                    mode = "ab" if downloaded > 0 else "wb"
                    with (
                        open(tmp_filepath, mode) as f,
                        tqdm(
                            total=filesize,
                            initial=downloaded,
                            unit="B",
                            unit_scale=True,
                            desc=filename,
                        ) as progress_bar,
                    ):
                        for chunk in response.iter_content(chunk_size=65536):
                            if chunk:
                                f.write(chunk)
                                progress_bar.update(len(chunk))
                else:
                    print(
                        f"Failed to download {filename}, status code: {response.status_code}"
                    )
                    return

            os.rename(tmp_filepath, final_filepath)
            print(f"Download completed: {filename}")

        except KeyboardInterrupt:
            if not InputTools.simple_yn(
                "\nSkip current download or all? (C=Current, A=All, default=Current) ",
                choices=[("all", "a"), ("current", "c", "d", "default")],
                case_sensitive=False,
                default_choice=True,
            ):
                print("Download interrupted by user.")
                OSManager.exit(0)

            print(f"Skip download: {filename}")

        except IOError:
            print(f"Unable to write: {filename}")
        except RequestException as req_err:
            print(f"Error occurred during the request: {req_err}")
        except Exception as err:
            print(f"Error downloading {filename}: {err}")

    def download_files(
        self, items: list[tuple[str, int, str], ...]
    ) -> list[tuple[str, str], ...]:
        file_hash: list[tuple[str, str], ...] = []
        for url, filesize, md5 in items:
            filename: str = url.split("/")[-1]
            self.download_file(url=url, filename=filename, filesize=filesize, md5=md5)
            file_hash.append((os.path.join(self.path, filename), md5))
            print()  # Separate multiple downloads for easy viewing
        return file_hash


class CheckHash:
    @staticmethod
    def calculate_md5(filepath: str) -> str:
        hash_md5: _hashlib.HASH = hashlib.md5()
        file_size = os.path.getsize(filepath)

        with open(filepath, "rb") as file:
            with tqdm(
                total=file_size, unit="B", unit_scale=True, desc="MD5", position=0
            ) as progress_bar:
                for chunk in iter(lambda: file.read(4096), b""):
                    hash_md5.update(chunk)
                    progress_bar.update(len(chunk))
        return hash_md5.hexdigest()

    @staticmethod
    def check_md5(filepath: str, expected_md5: str) -> bool:
        print(f"\nRunning CRC: {filepath}.", end="\n")

        try:
            file_hash: str = CheckHash.calculate_md5(filepath)
        except KeyboardInterrupt:
            print("CRC canceled.")
            OSManager.exit(0)
        except FileNotFoundError:
            tmp_path = filepath + ".tmp"
            if os.path.exists(tmp_path):
                print(f'Skip "{tmp_path}": file not finished downloading')
                return False

            print(f'Skip "{filepath}": file not found.')
            return FileNotFoundError(f"{filepath}")

        if file_hash.lower() == expected_md5.lower():
            print("CRC OK!")
            return True
        print(f"CRC Failed! Expected {expected_md5}, got {file_hash}")
        return False


class ArgsHandler:
    def __init__(self):
        self.parser: argparse.ArgumentParser = argparse.ArgumentParser()
        self.parser.add_argument(
            "-p",
            "--patches",
            action="store_const",
            const="patches",
            dest="version",
            default="major",
            help="select patch to update instead of full game",
            required=False,
        )
        self.parser.add_argument(
            "-t",
            "--types",
            type=str,
            choices=["game_pkgs", "audio_pkgs", "all"],
            default="all",
            help="download options for the respective data types",
            required=False,
        )
        self.parser.add_argument(
            "-l",
            "--languages",
            nargs="+",
            type=str,
            default=["en-us"],
            help="specify audio download language",
            required=False,
        )
        self.parser.add_argument(
            "-i",
            "--info",
            action="store_true",
            help="print out information instead of downloading",
            required=False,
        )
        self.parser.add_argument(
            "-o", "--path", type=str, help="download folder path", required=False
        )
        self.parser.add_argument(
            "--game-list",
            action="store_true",
            help="go to gamelist.json initialization interface",
            required=False,
        )

        self.args: argparse.Namespace = self.parser.parse_args()

    def listener(self):
        if len(sys.argv) == 1:
            self.parser.print_help()
            sys.exit(1)

        # GameList
        if self.args.game_list:
            GameListMaker().main()
            return

        # Fetch
        lst_of_pkgs: list[tuple[str, int, str], ...] = ApiParser().main(
            version=self.args.version,
            types=["game_pkgs", "audio_pkgs"]
            if self.args.types == "all"
            else [self.args.types],
            languages=self.args.languages,
            print_info=self.args.info,
        )

        # Verify args
        if self.args.info:
            return

        self.args.path = os.path.normpath(self.args.path) if self.args.path else ""

        # Donwload
        downloader: Downloader = Downloader(path=self.args.path)
        file_hash: list[tuple[str, str]] = downloader.download_files(items=lst_of_pkgs)

        # CRC check
        print("\033[F", end="")  # Move the cursor up one line
        for filepath, md5 in file_hash:
            CheckHash.check_md5(filepath=filepath, expected_md5=md5)


def main():
    ArgsHandler().listener()


if __name__ == "__main__":
    print(
        "\nNotice: This tool uses old download method and api. It will not be able to download the latest version of some games. New download method may be implemented in the future.\n"
    )
    main()
