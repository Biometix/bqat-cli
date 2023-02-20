import csv
import datetime
import json
import os
from pathlib import Path

import pandas as pd
from pandas_profiling import ProfileReport
from PyInquirer import prompt

from bqat import __version__ as version


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
    else:
        out = json.loads(pd.json_normalize(out).to_json(orient="index"))["0"]

        if header:
            write_header = True
            if os.path.exists(path):
                append = True
                with open(path) as f:
                    data = f.read()
                    f.seek(0, os.SEEK_SET)
                    headline = f.readline()
                    if headline.count("file"):
                        write_header = False
            else:
                append = False
            if write_header:
                with open(path, "w") as f:
                    writer = csv.DictWriter(f, fieldnames=list(out.keys()))
                    writer.writeheader()
                if append:
                    with open(path, "a") as f:
                        f.write(data)

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


def filter_output(filepath, attributes, query, sort, cwd) -> dict:
    p = Path(filepath)
    if not (attributes or query or sort):
        return False
    if not p.is_file() or p.suffix != ".csv":
        print(f">>> Output [{str(p)}] not valid, please specify a CSV file. exit.")
        return False
    print("\n> Outlier:")
    dt = datetime.datetime.today()
    timestamp = f"{dt.day}-{dt.month}-{dt.year}_{dt.hour}-{dt.minute}-{dt.second}"
    table_dir = p.parent / f"outlier_table_{timestamp}.html"
    report_dir = p.parent / f"outlier_report_{timestamp}.html"
    pd.set_option('mode.chained_assignment', None)

    if p.exists() and p.suffix in (".csv", ".CSV"):
        data = pd.read_csv(p)
        pd.set_option("display.max_colwidth", None)
        if attributes and not data.empty:
            cols = attributes.split(",")
            cols.insert(0, "file") if "file" not in cols else None
            data = data[cols]
        if query and not data.empty:
            data = data.query(query)
        if sort and not data.empty:
            data = data.sort_values(sort.split(","))
        
        if not data.empty:
            ProfileReport(
                data,
                title=f"Outlier Report (BQAT v{version})",
                explorative=True,
                correlations={"cramers": {"calculate": False}},
                html={"navbar_show": True, "style": {"theme": "united"}},
            ).to_file(report_dir)
        
            with open(table_dir, "w") as f:
                f.write(
                    """<!doctype html><html lang=en>           
                    <head>
                    <script
                        src="https://code.jquery.com/jquery-2.2.4.min.js"
                        integrity="sha256-BbhdlvQf/xTY9gja0Dq3HiwQF8LaCRTXxZKRutelT44="
                        crossorigin="anonymous">
                    </script>
                    <script src="https://cdn.datatables.net/1.13.1/js/jquery.dataTables.min.js"></script>
                    <link href="https://cdn.datatables.net/1.13.1/css/jquery.dataTables.min.css" rel="stylesheet">
                    <link href="https://cdn.datatables.net/1.10.16/css/jquery.dataTables.min.css" rel="stylesheet">
                    </head>
                    <body>
                    <script>
                        $(document)
                    .ready(function () {
                        $('table')
                        .DataTable( {
                    fixedColumns: {
                            left: 2
                        }
                    }
                        );
                    });
                    </script>
                    """
                )
                data["file"] = data["file"].map(lambda x: f"file://{cwd}/{x}")

                def make_clickable(val):
                    # target _blank to open new window
                    return '<a target="_blank" href="{}">{}</a>'.format(val, val)

                f.write(
                    data.style.format({"file": make_clickable})
                    .background_gradient(axis=0)
                    .to_html()
                    # .to_html(render_links=True)
                )
        else:
            return False

        return {"output": str(table_dir), "report": str(report_dir)}

    else:
        raise RuntimeError("output csv not fount.")
