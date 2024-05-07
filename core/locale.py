import tomllib
import os

localization = dict()

for file in os.listdir("localization"):
    if file.endswith(".toml"):
        with open(f"localization/{file}", "rb") as data:
            localization[file.split(".")[0]] = tomllib.load(data)

def localize(guild_id: int, category: str, index: str) -> str:
    try:
        return localization[guild_id][category][index]
    except KeyError:
        return localization["en-US"][category][index]
