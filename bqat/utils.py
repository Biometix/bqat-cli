import csv
import json
import os
import subprocess
from io import StringIO

import cv2 as cv
import numpy as np
import pandas as pd
import wsq
from mediapipe.python.solutions.face_detection import FaceDetection
from mediapipe.python.solutions.face_mesh import FaceMesh
from pandas_profiling import ProfileReport
from PIL import Image, ImageOps
from PyInquirer import prompt
from scipy.spatial.distance import euclidean

# from scipy.stats import normaltest


## Main process
def scan_fingerprint(
    img_path: str, ext: bool = False, convert=["jpg", "jpeg", "bmp"], target="png"
) -> tuple:
    """Send fingerprint image to processing functions and get assessment results.

    The format of single input will be check and converted if needed. Then the
    results will be collected by a dict and returned.
    """
    result = {}
    log = {}

    CONVERT = convert

    try:
        img = Image.open(img_path)
    except Exception as e:
        log.update({"error": str(e)})
        return result, log

    try:
        filetype = get_type(img_path)

        if img_path.rsplit(".")[-1] in to_upper(CONVERT):
            log.update({"conversion": f"input converted to {target.upper()}"})
            im = Image.open(img_path)
            # im = ImageOps.grayscale(im)
            im = im.convert("L")
            img_path = os.path.splitext(img_path)[0] + f".converted.{target}"
            im.save(img_path)
            converted = True
        else:
            converted = False

        ## Append results from each analysis function
        result.update(nfiq2(img_path))
        result.update(detect_fault(img))
        result.update(get_size(img))
        result.update(filetype)

        if ext:
            try:
                from data import extensions

                result.update(extensions.func(img))
            except Exception as e:
                log.update({"extensions": str(e)})

        if (error := result.get("OptionalError")) != "NA":
            log.update({"nfiq2_error": error})

        if converted:
            os.remove(img_path)
    except Exception as e:
        log.update({"error": str(e)})

    return result, log


def scan_face(img_path: str, ext: bool = False) -> tuple:
    """Send face image to processing functions and get assessment results.

    Args:
        img_path (str): Input image path.
        ext (bool, optional): Enable extension function. Defaults to False.

    Returns:
        tuple: (face attributes, process log)
    """
    result = {}
    log = {}

    try:
        img = cv.imread(img_path)
    except Exception as e:
        log.update({"error": str(e)})
        return result, log
    if img is None:
        log.update({"error": f"failed to read {img_path}"})
        return result, log
    h, w, _ = img.shape

    try:
        with FaceDetection(
            model_selection=1,  # full-range detection model
            min_detection_confidence=0.5,
        ) as face_detection:
            detections = face_detection.process(cv.cvtColor(img, cv.COLOR_BGR2RGB))
            if not getattr(detections, "detections"):
                # print(">> fallback to short-range model.")
                with FaceDetection(
                    model_selection=0,  # short-range detection model
                    min_detection_confidence=0.5,
                ) as face_detection:
                    detections = face_detection.process(
                        cv.cvtColor(img, cv.COLOR_BGR2RGB)
                    )
                if not getattr(detections, "detections"):
                    raise RuntimeError("no face found")

        with FaceMesh(
            static_image_mode=True,
            min_detection_confidence=0.5,
            max_num_faces=1,
            refine_landmarks=True,
        ) as model:
            mesh = model.process(cv.cvtColor(img, cv.COLOR_BGR2RGB))

        if mesh.multi_face_landmarks:
            mesh = mesh.multi_face_landmarks[0]
        else:
            raise RuntimeError("fail to get face mesh")
    except Exception as e:
        log.update({"error": str(e)})
        return result, log

    # ## For debug
    # import mediapipe as mp
    # mp_drawing = mp.solutions.drawing_utils
    # mp_drawing_styles = mp.solutions.drawing_styles
    # mp_face_mesh = mp.solutions.face_mesh
    # annotated_image = img.copy()

    # face_landmarks = mesh
    # mp_drawing.draw_landmarks(
    #       image=annotated_image,
    #       landmark_list=face_landmarks,
    #       connections=mp_face_mesh.FACEMESH_TESSELATION,
    #       landmark_drawing_spec=None,
    #       connection_drawing_spec=mp_drawing_styles
    #       .get_default_face_mesh_tesselation_style())
    # mp_drawing.draw_landmarks(
    #     image=annotated_image,
    #     landmark_list=face_landmarks,
    #     connections=mp_face_mesh.FACEMESH_CONTOURS,
    #     landmark_drawing_spec=None,
    #     connection_drawing_spec=mp_drawing_styles
    #     .get_default_face_mesh_contours_style())
    # mp_drawing.draw_landmarks(
    #     image=annotated_image,
    #     landmark_list=face_landmarks,
    #     connections=mp_face_mesh.FACEMESH_IRISES,
    #     landmark_drawing_spec=None,
    #     connection_drawing_spec=mp_drawing_styles
    #     .get_default_face_mesh_iris_connections_style())

    # detection = detections.detections[0]
    # mp_drawing.draw_detection(annotated_image, detection)

    # cv.imwrite(f'data/output/annotated_image_{w}_{h}.png', annotated_image)

    try:
        result.update({"file": img_path})
        result.update({"img_h": h, "img_w": w})
        result.update(is_smile(detections, img))
        result.update(is_eye_closed(mesh, h, w))
        result.update(get_ipd(mesh, h, w))
        result.update(get_orientation(mesh, h, w))
        result.update(get_confidence(detections))
        result.update(get_type(img_path))
    except Exception as e:
        log.update({"error": str(e)})

    if ext:
        try:
            from data import extensions

            result.update(extensions.func(img))
        except Exception as e:
            log.update({"error": str(e)})

    return result, log


def scan_iris(img_path: str, ext: bool = False, target="png") -> tuple:
    """Send iris image to processing functions and get assessment results.

    Args:
        img_path (str): Input image path.
        ext (bool, optional): Enable extension function. Defaults to False.

    Returns:
        tuple: (face attributes, process log)
    """
    result = {}
    log = {}
    processed = False

    target_size = (640, 480)

    try:
        img = Image.open(img_path)
        w, h = img.size
        if w > target_size[0] or h > target_size[1]:
            img = ImageOps.fit(img, target_size)
            img = ImageOps.grayscale(img)
            log.update({"resize": f"input resized to {target_size} as {target.upper()}"})
            processed = True
        if processed:
            img_path = os.path.splitext(img_path)[0] + f".processed.{target}"
            img.save(img_path)
    except Exception as e:
        log.update({"error": str(e)})
        return result, log
    if img is None:
        log.update({"error": f"failed to read {img_path}"})
        return result, log

    try:
        result.update({"file": img_path})
        result.update(get_iris_attr(img_path))
        result.update(get_type(img_path))
    except Exception as e:
        log.update({"error": str(e)})

    if ext:
        try:
            from data import extensions

            result.update(extensions.func(img))
        except Exception as e:
            log.update({"error": str(e)})

    if processed:
        os.remove(img_path)
    return result, log


## Fingerprint sample assessment
def nfiq2(img_path: str) -> dict:
    # raw = subprocess.check_output(['nfiq2', '-F', '-a', '-v', 'q', 'd', '-i', img_path])
    raw = subprocess.check_output(["nfiq2", "-F", "-a", "-i", img_path])
    # raw = subprocess.check_output(['nfiq2', '-v', '-a', img_path])
    content = StringIO(raw.decode())
    nfiq2_dict = next(csv.DictReader(content))
    nfiq2_dict = {
        "NFIQ2" if k == "QualityScore" else k: v for k, v in nfiq2_dict.items()
    }
    # quality_score = {"NFIQ2": nfiq2_dict.get("NFIQ2")}
    # nfiq2_dict.pop("NFIQ2")
    # quality_score.update(nfiq2_dict)
    # nfiq2_dict = quality_score
    nfiq2_dict.pop("FingerCode")
    return nfiq2_dict


def detect_fault(img: object) -> dict:
    """
    Checks to see if there is an issue with the image by taking a strip one pixel wide
    From the edges of the fingerprint image. If the finger print is corrupt this will have high varience
    """
    im = ImageOps.grayscale(img)
    size = im.size
    lres = np.array(im.copy().crop((0, 0, 1, size[1])))
    rres = np.array(im.copy().crop((size[0] - 1, 0, size[0], size[1])))
    left_std = np.std(lres)
    right_std = np.std(rres)
    # lstat, p = normaltest(rres)
    # rstat, p = normaltest(rres)
    # return {"edge_skew": lstat[0] + rstat[0] }
    detect_dict = {"EdgeStd": (left_std + right_std) / 2.0}
    return detect_dict


def get_size(img: object) -> dict:
    size_dict = {
        "Width": img.size[0],
        "Height": img.size[1],
    }
    return size_dict


## Face image assessment
def get_ipd(face_mesh, img_h, img_w) -> dict:
    """Get inter-pupillary distance estimation."""
    right_iris = [469, 470, 471, 472]
    left_iris = [474, 475, 476, 477]

    r_x, r_y, l_x, l_y = [0] * 4
    r_x = np.mean([lm.x for i, lm in enumerate(face_mesh.landmark) if i in right_iris])
    r_y = np.mean([lm.y for i, lm in enumerate(face_mesh.landmark) if i in right_iris])

    l_x = np.mean([lm.x for i, lm in enumerate(face_mesh.landmark) if i in left_iris])
    l_y = np.mean([lm.y for i, lm in enumerate(face_mesh.landmark) if i in left_iris])

    r = (int(r_x * img_w), int(r_y * img_h))
    l = (int(l_x * img_w), int(l_y * img_h))
    dist = 0
    for u, v in zip(r, l):
        dist += (u - v) ** 2

    result = {
        # "pupil_r": r,
        # "pupil_l": l,
        "ipd": int(dist**0.5)
    }
    return result


def get_orientation(face_mesh, img_h, img_w) -> dict:
    """Get head pose estimation."""
    poi = [
        1,  # nose tip
        152,  # chin
        33,  # left corner of left eye
        263,  # right corner of right eye
        61,  # mouth left
        291,  # mouth right
        129,  # nose left
        358,  # nose right
    ]

    face_3d = []
    face_2d = []
    for i, lm in enumerate(face_mesh.landmark):
        if i in poi:
            x, y = int(lm.x * img_w), int(lm.y * img_h)
            face_2d.append((x, y))
            face_3d.append((x, y, lm.z))

    face_2d = np.array(face_2d, dtype=np.float64)
    face_3d = np.array(face_3d, dtype=np.float64)

    focal_length = img_w
    center = (img_w / 2, img_h / 2)
    camera_matrix = np.array(
        [
            [focal_length, 0, center[0]],
            [0, focal_length, center[1]],
            [0, 0, 1.0],
        ],
        dtype=np.float64,
    )
    distortion_coefficients = np.zeros((4, 1), dtype=np.float64)

    _, rotation_vec, _ = cv.solvePnP(
        face_3d,
        face_2d,
        camera_matrix,
        distortion_coefficients,
        flags=cv.SOLVEPNP_ITERATIVE,
    )

    rot_mat, _ = cv.Rodrigues(rotation_vec)
    try:
        angles, _, _, _, _, _ = cv.RQDecomp3x3(rot_mat)
        degree_yaw = -angles[1] * 360
        degree_pitch = angles[0] * 360
        degree_roll = angles[2] * 360
    except:
        raise RuntimeError("unable to get head pose angles.")

    if abs(degree_yaw) < 3:
        pose_yaw = "Forward"
    else:
        pose_yaw = "Left" if degree_yaw > 0 else "Right"
    if abs(degree_pitch) < 3:
        pose_pitch = "Level"
    else:
        pose_pitch = "Up" if degree_pitch > 0 else "Down"
    if abs(degree_roll) < 3:
        pose_roll = "Level"
    else:
        pose_roll = "Anti-clockwise" if degree_roll > 0 else "Clockwise"

    result = {
        "yaw_pose": pose_yaw,
        "yaw_degree": degree_yaw,
        "pitch_pose": pose_pitch,
        "pitch_degree": degree_pitch,
        "roll_pose": pose_roll,
        "roll_degree": degree_roll,
    }
    return result


def get_confidence(detections: object) -> dict:
    score = 0
    for detection in getattr(detections, "detections"):
        detection_score = detection.score[0]
        if detection_score > score:
            score = detection_score

    result = {"confidence_face": score}
    return result


def is_smile(detections: object, img: object) -> dict:
    h, w, _ = img.shape
    gray = cv.cvtColor(img, cv.COLOR_BGR2GRAY)

    # ## Extract detected face area
    # score = 0
    # index = 0
    # for detection in getattr(detections, "detections"):
    #     detection_score = detection.score[0]
    #     detection_label_id = detection.label_id[0]
    #     if detection_score > score:
    #         score = detection_score
    #         index = detection_label_id
    # detection = getattr(detections, "detections")[index]
    # x = int(detection.location_data.relative_bounding_box.xmin*w)
    # y = int(detection.location_data.relative_bounding_box.ymin*h)
    # w = int(detection.location_data.relative_bounding_box.width*w)
    # h = int(detection.location_data.relative_bounding_box.height*h)
    # gray = gray[y:y+h, x:x+w]

    smileCascade = cv.CascadeClassifier(
        "quality_assessor/classifiers/haarcascade_smile.xml"
    )
    smile = smileCascade.detectMultiScale(
        gray,
        scaleFactor=1.15,
        minNeighbors=20,
        minSize=(int(h / 6), int(w / 3)),
        maxSize=(int(h / 4), int(w / 2)),
        flags=cv.CASCADE_DO_CANNY_PRUNING,
    )
    smile = True if len(smile) >= 1 else False

    # ## Display detected smile
    # for (x2, y2, w2, h2) in smile:
    #     cv.rectangle(gray, (x2, y2), (x2+w2, y2+h2), (255, 0, 0), 2)
    # cv.imwrite(f'data/output/roi_gray_{h}_{w}.png', gray)

    result = {"smile": smile}
    return result


def is_eye_closed(face_mesh: object, img_h: int, img_w: int) -> dict:
    right_upper = [384, 385, 386, 387]
    right_lower = [381, 380, 374, 373]
    right_corner = [362, 263]
    left_upper = [160, 159, 158, 157]
    left_lower = [144, 145, 153, 154]
    left_corner = [33, 133]

    r_u, r_l, r_c, l_u, l_l, l_c = [], [], [], [], [], []
    for i, mark in enumerate(face_mesh.landmark):
        if i in right_upper:
            r_u.append((mark.x * img_w, mark.y * img_h))
        if i in right_lower:
            r_l.append((mark.x * img_w, mark.y * img_h))
        if i in right_corner:
            r_c.append((mark.x * img_w, mark.y * img_h))
        if i in left_lower:
            l_l.append((mark.x * img_w, mark.y * img_h))
        if i in left_upper:
            l_u.append((mark.x * img_w, mark.y * img_h))
        if i in left_corner:
            l_c.append((mark.x * img_w, mark.y * img_h))

    r_l.reverse()
    l_u.reverse()

    right_vertical = np.mean([euclidean(u, l) for u, l in zip(r_u, r_l)])
    right_horizontal = euclidean(r_c[0], r_c[1])
    left_vertical = np.mean([euclidean(u, l) for u, l in zip(l_u, l_l)])
    left_horizontal = euclidean(l_c[0], l_c[1])

    right_ratio = right_vertical / right_horizontal
    left_ratio = left_vertical / left_horizontal

    threshold = 0.15
    right = True if right_ratio < threshold else False
    left = True if left_ratio < threshold else False

    result = {
        "eye_l": left,
        "eye_r": right,
    }
    return result


def get_type(img_path: str) -> dict:
    _, ext = os.path.splitext(img_path)
    result = {"type": ext.strip(".")}
    return result


## Iris sample assessment
def get_iris_attr(img_path: str) -> dict:
    iris_dict = {}
    raw = subprocess.check_output(["biqt", "-m", "iris", img_path])
    content = StringIO(raw.decode())
    attributes = csv.DictReader(content)
    for attribute in attributes:
        iris_dict.update({attribute.get("Key"): attribute.get("Value")})
    quality_score = {"quality": iris_dict.get("quality")}
    iris_dict.pop("quality")
    iris_dict.pop("fast_quality")
    quality_score.update(iris_dict)
    iris_dict = quality_score
    return iris_dict


## Example assessment function
def new_func(img_path: str) -> dict:
    """Run analysis on input image.

    Processing function should take single input image path (or PIL image object)
    and return results as dict which will be converted columns in final csv output.

    Args:
        img_path: relative path to image path.

    Returns:
        A dict of result attributes. For example:

        {
            "image_width": 1920,
            "image_height": 1080
        }

    Raises:
        RuntimeError: An error occurred processing the input image.
    """
    pass


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
        out = json.loads(pd.json_normalize(out).to_json(orient='index'))["0"]
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
            f.write('[')
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
            f.write(json.dumps(out) + ',')


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
            "choices":[
                "Start now",
                "Additional configurations"
            ]
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
