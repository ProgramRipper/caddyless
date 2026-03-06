from shutil import copyfileobj
from urllib.request import urlopen


def pdm_build_initialize(_):
    with (
        open("caddyless/tlds-alpha-by-domain.txt", "wb") as file,
        urlopen("https://data.iana.org/TLD/tlds-alpha-by-domain.txt") as resp,
    ):
        copyfileobj(resp, file)
