import csv
import json
import os

import pandas as pd
from pandas_profiling import ProfileReport
from PyInquirer import prompt


## Helper functions
def convert_ram(bytes):
    factor = 1024
    for unit in ["", "K", "M", "G", "T", "P"]:
        if bytes < factor:
            return f"{bytes:.2f}{unit}B"
        bytes /= factor


def to_upper(ext_list):
    cap_list = []
    for ext in ext_list:
        cap_list.append(ext.upper())
    return ext_list + cap_list


def write_report(report_dir, output_dir, title="Biometric Quality Report (BQAT)"):
    print("\n> Report:")
    if not os.path.exists(report_dir.rsplit("/", 1)[0]):
        os.makedirs(report_dir.rsplit("/", 1)[0])
    df = pd.read_csv(output_dir)
    # df.set_index("uuid", inplace=True)
    ProfileReport(
        df,
        title=title,
        explorative=True,
        correlations={"cramers": {"calculate": False}},
        html={"navbar_show": True, "style": {"theme": "united"}},
    ).to_file(report_dir)


def write_csv(path, out="", header=False, init=False):
    if init:
        if not os.path.exists(path.rsplit("/", 1)[0]):
            os.makedirs(path.rsplit("/", 1)[0])
        with open(path, "w") as f:
            writer = csv.writer(f)
            writer.writerow("")
    else:
        out = json.loads(pd.json_normalize(out).to_json(orient="index"))["0"]
        if header:
            if os.path.exists(path):
                with open(path, "r") as f:
                    reader = csv.reader(f)
                    try:
                        line = next(reader)
                    except:
                        line = False
            if not line:
                with open(path, "w") as f:
                    writer = csv.DictWriter(f, fieldnames=list(out.keys()))
                    writer.writeheader()
            with open(path, "a") as f:
                writer = csv.DictWriter(f, fieldnames=list(out.keys()))
                writer.writerow(out)
        else:
            with open(path, "a") as f:
                writer = csv.DictWriter(f, fieldnames=list(out.keys()))
                writer.writerow(out)


def write_log(path, out=None, init=False, finish=False):
    if init:
        if not os.path.exists(path.rsplit("/", 1)[0]):
            os.makedirs(path.rsplit("/", 1)[0])
        with open(path, "w") as f:
            f.write("[")
    elif finish:
        with open(path, "rb+") as f:
            f.seek(-1, os.SEEK_END)
            if f.read1() == b"[":
                f.seek(-1, os.SEEK_CUR)
                f.write(bytes("[]", "utf-8"))
            else:
                f.seek(-1, os.SEEK_CUR)
                f.write(bytes("]", "utf-8"))
    else:
        with open(path, "a") as f:
            f.write(json.dumps(out) + ",")


def validate_path(path) -> str:
    if not path.endswith("/"):
        path = path + "/"
    return path


def manu() -> dict:
    questions_entry = [
        {
            "type": "list",
            "name": "mode",
            "message": "Select biometric modality",
            "choices": ["Fingerprint", "Face", "Iris"],
        },
        {
            "type": "list",
            "name": "job",
            "message": "Select job type",
            "choices": ["Scan biometric samples", "Benchmark the system"],
        },
    ]

    folders = [item for item in os.listdir("./data") if os.path.isdir(f"./data/{item}")]

    questions_input = [
        {
            "type": "list",
            "name": "input",
            "message": "Select input folder",
            "choices": folders + ["[User Input]"],
        }
    ]

    questions_enter_input = [
        {"type": "input", "name": "input", "message": "Enter input path"}
    ]

    questions_start = [
        {
            "type": "list",
            "message": "Do you want to start the job or Proceed to Additional configurations",
            "name": "start",
            "choices": ["Start now", "Additional configurations"],
        },
    ]

    questions_advance = [
        {
            "type": "input",
            "name": "output",
            "message": "Enter output folder path",
            "default": "data/output/",
        },
        {
            "type": "input",
            "name": "filename",
            "message": "Filename pattern to search (IRIS*, *Left*)",
            "default": "*",
        },
        {
            "type": "input",
            "name": "search",
            "message": "Specify file formats to search within the input folder. (Default: wsq, jpg, jpeg, png, bmp, jp2)",
            "default": "",
        },
        {
            "type": "input",
            "name": "convert",
            "message": "Specify file formats to convert before processing. (Default: jpg, jpeg, bmp, jp2, wsq) [Fingerprint only]",
            "default": "",
        },
        {
            "type": "input",
            "name": "target",
            "message": "Specify target format to convert to. (Default: png)",
            "default": "",
        },
        {
            "type": "input",
            "name": "limit",
            "message": "Enter scan limit number",
            "default": "NA",
        },
        {
            "type": "confirm",
            "message": "Do you want to run in compatible mode? (For ARM64 platform)",
            "name": "arm",
            "default": False,
        },
    ]

    ans = prompt(questions_entry)

    if ans.get("job") == "Benchmark the system":
        ans.pop("job")
        ans.update({"benchmark": True})
        return ans
    else:
        ans_input = prompt(questions_input)
        if ans_input.get("input") == "[User Input]":
            ans.update(prompt(questions_enter_input))
        else:
            ans.update({"input": "data/" + ans_input.get("input")})

    if prompt(questions_start).get("start") == "Start now":
        return ans
    else:
        ans.update(prompt(questions_advance))
        if ans["limit"] == "NA":
            ans["limit"] = 0

    return ans
