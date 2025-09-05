import csv
import datetime
import json
import os
import shutil
from pathlib import Path

import numpy as np
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

# Deprecated
# def write_report(report_dir, output_dir, title="Biometric Quality Report (BQAT)"):
#     print("\n> Report:")
#     if not os.path.exists(report_dir.rsplit("/", 1)[0]):
#         os.makedirs(report_dir.rsplit("/", 1)[0])
#     df = pd.read_csv(
#         output_dir,
#         # dtype=np.float32, # force parsing scientific notation string as number type
#     )
#     df = df.drop(columns="file")
#     ProfileReport(
#         df,
#         title=title,
#         samples=None,
#         correlations=None,
#         html={
#             "navbar_show": True,
#             "style": {
#                 "full_width": True,
#                 "theme": "simplex",
#                 "logo": "https://www.biometix.com/wp-content/uploads/2020/10/logo.png",
#             },
#         },
#     ).to_file(report_dir)


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
    table_dir = p.parent / f"data_table_filtered_{timestamp}.html"
    report_dir = p.parent / f"eda_report_filtered_{timestamp}.html"
    output_dir = p.parent / f"output_filtered_{timestamp}.csv"
    pd.set_option("mode.chained_assignment", None)

    if p.exists() and p.suffix in (".csv", ".CSV"):
        data = pd.read_csv(
            p,
            # dtype=np.float32,
        )
        df_raw = data.copy()
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
                title=f"EDA Report (BQAT v{version})",
                explorative=True,
                samples=None,
                # correlations=None,
                interactions=None,  # Makes the html 10x in size
                html={
                    "navbar_show": True,
                    "style": {
                        "full_width": True,
                        "theme": "simplex",
                        "logo": "https://www.biometix.com/wp-content/uploads/2020/10/logo.png",
                    },
                },
                type_schema={
                    "roll_pose": "categorical",
                    "pitch_pose": "categorical",
                    "yaw_pose": "categorical",
                },
            ).to_file(report_dir)

            with open(table_dir, "w") as f:
                f.write(
                    """<!doctype html><html lang=en>           
                    <head>
                    <meta charset="utf-8">
                    <title>Data Table</title>
                    <script
                        src="https://code.jquery.com/jquery-2.2.4.min.js"
                        integrity="sha256-BbhdlvQf/xTY9gja0Dq3HiwQF8LaCRTXxZKRutelT44="
                        crossorigin="anonymous">
                    </script>
                    <script src="https://cdn.datatables.net/1.13.1/js/jquery.dataTables.min.js"></script>
                    <script src="https://cdn.datatables.net/fixedcolumns/4.2.1/js/dataTables.fixedColumns.min.js"></script>
                    <link href="https://cdn.datatables.net/1.13.1/css/jquery.dataTables.min.css" rel="stylesheet">
                    <link href="https://cdn.datatables.net/fixedcolumns/4.2.1/css/fixedColumns.dataTables.min.css" rel="stylesheet">
                    <style>
                        .image-popup {
                            display: none;
                            position: fixed;
                            border: 1px solid #ccc;
                            background-color: white;
                            padding: 5px;
                            z-index: 1000;
                            box-shadow: 0 0 10px rgba(0,0,0,0.5);
                        }
                        .image-popup img { max-width: 400px; max-height: 400px; }
                    </style>
                    </head>
                    <body>
                    <script>
                        $(document)
                    .ready(function () {
                        $('table')
                        .DataTable( {
                    "pageLength": 50,
                    scrollX: true,
                    fixedColumns: {
                            left: 2
                        }
                    }
                        );

                        var popup = $('<div class="image-popup"><img src=""></div>').appendTo('body');

                        $('table').on('mouseenter', 'a.image-preview', function(e) {
                            var imageUrl = $(this).attr('href');
                            popup.find('img').attr('src', imageUrl);
                            popup.show();
                        }).on('mouseleave', 'a.image-preview', function(e) {
                            popup.hide();
                            popup.find('img').attr('src', ''); // Clear src to prevent showing old image
                        }).on('mousemove', 'a.image-preview', function(e) {
                            // Position popup near cursor
                            var x = e.clientX + 20;
                            var y = e.clientY + 20;
                            
                            // Adjust if popup goes off-screen
                            if (x + popup.outerWidth() > $(window).width()) {
                                x = e.clientX - popup.outerWidth() - 20;
                            }
                            if (y + popup.outerHeight() > $(window).height()) {
                                y = e.clientY - popup.outerHeight() - 20;
                            }
                            popup.css({ top: y, left: x });
                        });
                    });
                    </script>
                    """
                )
                df_raw["file"] = df_raw["file"].map(lambda x: f"file://{cwd}/{x}")

                def make_clickable(val):
                    return '<a target="_blank" href="{0}" class="image-preview">{0}</a>'.format(
                        val
                    )

                f.write(
                    df_raw.style.format({"file": make_clickable})
                    .background_gradient(axis=0)
                    .to_html(render_links=True)
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
    print("\n> Report:")
    dt = datetime.datetime.today()
    timestamp = f"{dt.day}-{dt.month}-{dt.year}_{dt.hour}-{dt.minute}-{dt.second}"
    table_dir = p.parent / f"data_table_{timestamp}.html"
    report_dir = p.parent / f"eda_report_{timestamp}.html"
    pd.set_option("mode.chained_assignment", None)

    if p.exists() and p.suffix in (".csv", ".CSV"):
        df = pd.read_csv(p)
        pd.set_option("display.max_colwidth", None)
        df = df.replace("nan", np.nan)
        tmp = df.apply(lambda col: pd.to_numeric(col, errors="coerce"))
        df = tmp.fillna(df)
        numeric_columns = df.select_dtypes(include="number").columns
        df[numeric_columns] = df[numeric_columns].apply(pd.to_numeric, downcast="float")
        df_raw = df.copy()
        excluded_columns = ["file", "tag", "log"]
        excluded_columns = [col for col in excluded_columns if col in df.columns]
        df = df.drop(columns=excluded_columns)
        pd.set_option("display.float_format", "{:.4f}".format)

        if not df.empty:
            ProfileReport(
                df,
                title=f"EDA Report (BQAT v{version})",
                explorative=True,
                # correlations=None,
                interactions=None,  # Makes the html 10x in size
                html={
                    "minify_html": True,
                    "style": {
                        "full_width": True,
                        "theme": "simplex",
                        "logo": "https://www.biometix.com/wp-content/uploads/2020/10/logo.png",
                    },
                },
                type_schema={
                    "roll_pose": "categorical",
                    "pitch_pose": "categorical",
                    "yaw_pose": "categorical",
                },
            ).to_file(report_dir)

            with open(table_dir, "w") as f:
                f.write(
                    """<!doctype html><html lang=en>           
                    <head>
                    <meta charset="utf-8">
                    <title>Data Table</title>
                    <script
                        src="https://code.jquery.com/jquery-2.2.4.min.js"
                        integrity="sha256-BbhdlvQf/xTY9gja0Dq3HiwQF8LaCRTXxZKRutelT44="
                        crossorigin="anonymous">
                    </script>
                    <script src="https://cdn.datatables.net/1.13.1/js/jquery.dataTables.min.js"></script>
                    <script src="https://cdn.datatables.net/fixedcolumns/4.2.1/js/dataTables.fixedColumns.min.js"></script>
                    <link href="https://cdn.datatables.net/1.13.1/css/jquery.dataTables.min.css" rel="stylesheet">
                    <link href="https://cdn.datatables.net/fixedcolumns/4.2.1/css/fixedColumns.dataTables.min.css" rel="stylesheet">
                    <style>
                        .image-popup {
                            display: none;
                            position: fixed;
                            border: 1px solid #ccc;
                            background-color: white;
                            padding: 5px;
                            z-index: 1000;
                            box-shadow: 0 0 10px rgba(0,0,0,0.5);
                        }
                        .image-popup img { max-width: 400px; max-height: 400px; }
                    </style>
                    </head>
                    <body>
                    <script>
                        $(document)
                    .ready(function () {
                        $('table')
                        .DataTable( {
                    "pageLength": 50,
                    scrollX: true,
                    fixedColumns: {
                            left: 2
                        }
                    }
                        );

                        var popup = $('<div class="image-popup"><img src=""></div>').appendTo('body');

                        $('table').on('mouseenter', 'a.image-preview', function(e) {
                            var imageUrl = $(this).attr('href');
                            popup.find('img').attr('src', imageUrl);
                            popup.show();
                        }).on('mouseleave', 'a.image-preview', function(e) {
                            popup.hide();
                            popup.find('img').attr('src', ''); // Clear src to prevent showing old image
                        }).on('mousemove', 'a.image-preview', function(e) {
                            // Position popup near cursor
                            var x = e.clientX + 20;
                            var y = e.clientY + 20;
                            
                            // Adjust if popup goes off-screen
                            if (x + popup.outerWidth() > $(window).width()) {
                                x = e.clientX - popup.outerWidth() - 20;
                            }
                            if (y + popup.outerHeight() > $(window).height()) {
                                y = e.clientY - popup.outerHeight() - 20;
                            }
                            popup.css({ top: y, left: x });
                        });
                    });
                    </script>
                    """
                )
                excluded_columns = ["log"]
                excluded_columns = [
                    col for col in excluded_columns if col in df_raw.columns
                ]
                df_raw = df_raw.drop(columns=excluded_columns)
                df_raw["file"] = df_raw["file"].map(lambda x: f"file://{cwd}/{x}")

                def make_clickable(val):
                    return '<a target="_blank" href="{0}" class="image-preview">{0}</a>'.format(
                        val
                    )

                f.write(
                    df_raw.style.format({"file": make_clickable})
                    .background_gradient(axis=0)
                    .to_html(render_links=True)
                )
        else:
            return False

        return {
            "table": str(table_dir),
            "report": str(report_dir),
        }

    else:
        raise RuntimeError("input csv not fount.")


def extended(ext_list):
    """Extends lower case file extensions list with UPPER and Capitalize ones."""
    full_list = []
    for ext in ext_list:
        full_list.extend([ext.upper(), ext.capitalize()])
    full_list.extend(ext_list)
    return full_list


def split_input_folder(
    temp_folder,
    input_folder="",
    input_files="",
    batch_size=30,
    exts=("jpg", "jpeg", "png", "bmp", "wsq", "jp2", "wav"),
    pattern="*",
) -> list:
    if not os.path.isdir(temp_folder):
        raise ValueError("Invalid temp folder path")
    if input_files:
        for f in input_files:
            if not os.path.exists(f):
                raise ValueError(f"Invalid input files: {f}")
        files = input_files
    else:
        if not os.path.isdir(input_folder):
            raise ValueError("Invalid input folder path")
        files = [
            file
            for ext in extended(exts)
            for file in Path(input_folder).rglob(f"{pattern}.{ext}")
        ]
    n_files = len(files)
    batch_size = batch_size if n_files > batch_size else n_files
    batches = (
        (n_files // batch_size) + 1
        if n_files % batch_size != 0
        else n_files // batch_size
    )
    subfolders = []
    for i in range(batches):
        subfolder = Path(temp_folder) / f"batch_{i + 1}"
        subfolder.mkdir(exist_ok=False)
        subfolders.append(subfolder.as_posix())
        start = i * batch_size
        end = start + batch_size
        [
            shutil.copyfile(
                file,
                subfolder
                / f"{Path(file).as_posix().encode('utf-8').hex()}{Path(file).suffix}",
            )
            for file in files[start:end]
        ]
    return subfolders


def fix_filepath(output_dict):
    hex_filename = Path(output_dict["file"]).stem
    output_dict["file"] = bytes.fromhex(hex_filename).decode("utf-8")
    if output_dict.get("log"):
        output_dict["log"] = output_dict.pop("log")
    return output_dict
