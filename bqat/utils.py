import csv
import datetime
import json
import os
from pathlib import Path

# import numpy as np
import pandas as pd

# from PyInquirer import prompt
from ydata_profiling import ProfileReport

from bqat import __version__ as version

from .core.bqat_core.utils import extend


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
    df = pd.read_csv(
        output_dir,
        # dtype=np.float32, # force parsing scientific notation string as number type
    )
    df = df.drop(columns="file")
    ProfileReport(
        df,
        title=title,
        samples=None,
        correlations=None,
        html={
            "navbar_show": True,
            "style": {
                "full_width": True,
                "theme": "simplex",
                "logo": "https://www.biometix.com/wp-content/uploads/2020/10/logo.png",
            },
        },
    ).to_file(report_dir)


def write_csv(path, out="", seam=False):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.parent / "header.temp"

    if seam:
        with open(temp) as f:
            header = f.read().rstrip().split(",")
        with open(path) as f:
            data = f.read()
        with open(path, "w") as f:
            writer = csv.DictWriter(f, fieldnames=header)
            writer.writeheader()
        with open(path, "a") as f:
            f.write(data)
        temp.unlink()
    else:
        out = json.loads(pd.json_normalize(out).to_json(orient="index"))["0"]
        if os.path.exists(temp):
            with open(temp) as f:
                header_len = len(f.readline().split(","))
        else:
            header_len = 0
        if header_len < len(list(out.keys())):
            with open(temp, "w") as f:
                writer = csv.DictWriter(f, fieldnames=list(out.keys()))
                writer.writeheader()

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


# def menu() -> dict:
#     questions_entry = [
#         {
#             "type": "list",
#             "name": "mode",
#             "message": "Select biometric modality",
#             "choices": ["Fingerprint", "Face", "Iris"],
#         },
#         {
#             "type": "list",
#             "name": "job",
#             "message": "Select job type",
#             "choices": ["Scan biometric samples", "Benchmark the system"],
#         },
#     ]

#     folders = [item for item in os.listdir("./data") if os.path.isdir(f"./data/{item}")]

#     questions_input = [
#         {
#             "type": "list",
#             "name": "input",
#             "message": "Select input folder",
#             "choices": folders + ["[User Input]"],
#         }
#     ]

#     questions_enter_input = [
#         {"type": "input", "name": "input", "message": "Enter input path"}
#     ]

#     questions_start = [
#         {
#             "type": "list",
#             "message": "Do you want to start the job or Proceed to Additional configurations",
#             "name": "start",
#             "choices": ["Start now", "Additional configurations"],
#         },
#     ]

#     questions_advance = [
#         {
#             "type": "input",
#             "name": "output",
#             "message": "Enter output folder path",
#             "default": "data/output/",
#         },
#         {
#             "type": "input",
#             "name": "filename",
#             "message": "Filename pattern to search (IRIS*, *Left*)",
#             "default": "*",
#         },
#         {
#             "type": "input",
#             "name": "search",
#             "message": "Specify file formats to search within the input folder. (Default: wsq, jpg, jpeg, png, bmp, jp2)",
#             "default": "",
#         },
#         {
#             "type": "input",
#             "name": "convert",
#             "message": "Specify file formats to convert before processing. (Default: jpg, jpeg, bmp, jp2, wsq) [Fingerprint only]",
#             "default": "",
#         },
#         {
#             "type": "input",
#             "name": "target",
#             "message": "Specify target format to convert to. (Default: png)",
#             "default": "",
#         },
#         {
#             "type": "input",
#             "name": "limit",
#             "message": "Enter scan limit number",
#             "default": "NA",
#         },
#         {
#             "type": "confirm",
#             "message": "Do you want to run in compatible mode? (For ARM64 platform)",
#             "name": "arm",
#             "default": False,
#         },
#     ]

#     ans = prompt(questions_entry)

#     if ans.get("job") == "Benchmark the system":
#         ans.pop("job")
#         ans.update({"benchmark": True})
#         return ans
#     else:
#         ans_input = prompt(questions_input)
#         if ans_input.get("input") == "[User Input]":
#             ans.update(prompt(questions_enter_input))
#         else:
#             ans.update({"input": "data/" + ans_input.get("input")})

#     if prompt(questions_start).get("start") == "Start now":
#         return ans
#     else:
#         ans.update(prompt(questions_advance))
#         if ans["limit"] == "NA":
#             ans["limit"] = 0

#     return ans


def filter_output(filepath, attributes, query, sort, cwd) -> dict:
    p = Path(filepath)
    if not (attributes or query or sort):
        return False
    if not p.is_file() or p.suffix != ".csv":
        print(f">>> Output [{str(p)}] not valid, please specify a CSV file. exit.")
        return False
    print("\n> Filtering:")
    dt = datetime.datetime.today()
    timestamp = f"{dt.day}-{dt.month}-{dt.year}_{dt.hour}-{dt.minute}-{dt.second}"
    table_dir = p.parent / f"filtered_table_{timestamp}.html"
    report_dir = p.parent / f"filtered_report_{timestamp}.html"
    output_dir = p.parent / f"filtered_output_{timestamp}.csv"
    pd.set_option("mode.chained_assignment", None)

    if p.exists() and p.suffix in (".csv", ".CSV"):
        data = pd.read_csv(
            p,
            # dtype=np.float32,
        )
        pd.set_option("display.max_colwidth", None)
        if attributes and not data.empty:
            cols = attributes.split(",")
            cols.insert(0, "file") if "file" not in cols else None
            data = data[cols]
        if query and not data.empty:
            data = data.query(query)
        if sort and not data.empty:
            data = data.sort_values(sort.split(","))
        
        data.to_csv(output_dir, index=False)

        if not data.empty:
            ProfileReport(
                data,
                title=f"EDA (Filtered) Report (BQAT v{version})",
                explorative=True,
                samples=None,
                # correlations={"cramers": {"calculate": False}},
                correlations=None,
                html={
                    "navbar_show": True,
                    "style": {
                        "full_width": True,
                        "theme": "simplex",
                        "logo": "https://www.biometix.com/wp-content/uploads/2020/10/logo.png",
                    },
                },
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
        
        return {
            "table": str(table_dir),
            "report": str(report_dir),
            "output": str(output_dir)
        }

    else:
        raise RuntimeError("output csv not fount.")


def glob_path(path: str, ext: list, recursive: bool = True) -> list:
    if recursive:
        return [i for e in extend(ext) for i in list(Path(path).rglob(f"*.{e}"))]
    else:
        return [i for e in extend(ext) for i in list(Path(path).glob(f"*.{e}"))]


def generate_report(filepath, cwd='') -> dict:
    p = Path(filepath)
    if not p.is_file() or p.suffix != ".csv":
        print(f">>> Input [{str(p)}] not valid, please specify a CSV file. exit.")
        return False
    print("\n> Reporting:")
    dt = datetime.datetime.today()
    timestamp = f"{dt.day}-{dt.month}-{dt.year}_{dt.hour}-{dt.minute}-{dt.second}"
    table_dir = p.parent / f"eda_table_{timestamp}.html"
    report_dir = p.parent / f"eda_report_{timestamp}.html"
    pd.set_option("mode.chained_assignment", None)

    if p.exists() and p.suffix in (".csv", ".CSV"):
        data = pd.read_csv(
            p,
            # dtype=np.float32,
        )
        pd.set_option("display.max_colwidth", None)

        if not data.empty:
            ProfileReport(
                data,
                title=f"EDA Report (BQAT v{version})",
                explorative=True,
                samples=None,
                # correlations={"cramers": {"calculate": False}},
                correlations=None,
                html={
                    "navbar_show": True,
                    "style": {
                        "full_width": True,
                        "theme": "simplex",
                        "logo": "https://www.biometix.com/wp-content/uploads/2020/10/logo.png",
                    },
                },
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

        return {"table": str(table_dir), "report": str(report_dir)}

    else:
        raise RuntimeError("input csv not fount.")