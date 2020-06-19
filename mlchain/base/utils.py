import urllib.request
import mimetypes
import numpy as np 
from werkzeug.datastructures import FileStorage
from PIL import Image, ImageSequence
import io 
from urllib.request import urlopen,Request
from io import BytesIO
from mlchain import logger
cv2 = None 

def import_cv2():
    global cv2
    if cv2 is None:
        import cv2 as cv
        cv2 = cv

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2228.0 Safari/537.3'}

def is_url_image(url):
    mimetype, encoding = mimetypes.guess_type(url)
    return (mimetype and mimetype.startswith('image'))


def check_url(url):
    """Returns True if the url returns a response code between 200-300,
       otherwise return False.
    """
    try:
        req = urllib.request.Request(url, headers=headers)
        response = urllib.request.urlopen(req)
        return response.code in range(200, 209)
    except Exception:
        return False

def is_image_url_and_ready(url):
    return is_url_image(url) and check_url(url)


def read_image_from_url_cv2(url):
    import_cv2()
    logger.info("Read cv2 image from: {0}".format(url))
    return cv2.imdecode(np.asarray(bytearray(urlopen(Request(url= url,headers= headers),timeout=100).read()), dtype="uint8"), cv2.IMREAD_UNCHANGED)

def read_image_from_url_pil(url):
    logger.info("Read pil image from: {0}".format(url))
    file = BytesIO(urlopen(Request(url=url,headers=headers),timeout=100).read())
    img = Image.open(file)
    return img

def url_to_image(url):
    return read_image_from_url_cv2(url)

def read_numpy_image_from_bytes(img_bytes):
    import_cv2()
    return cv2.imdecode(
        np.asarray(bytearray(img_bytes.read()), dtype="uint8"),
        cv2.IMREAD_COLOR)

def read_numpy_images_multi_page_from_bytes(img_bytes):
    output = []
    im = Image.open(io.BytesIO(img_bytes))

    for i, page in enumerate(ImageSequence.Iterator(im)):
        output.append(np.array(page))
    return np.array(output)

def read_ndarray_from_FileStorage(file_storage:FileStorage):
    file_ext = file_storage.filename.split(".")[-1].lower().strip('"')
    new_value = None

    if file_ext in ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'jpe', 'jp2', 'pbm', 'pgm', 'ppm', 'sr', 'ras']:
        # If input is an image 
        new_value = read_numpy_image_from_bytes(file_storage)
    elif file_ext in ['tif', 'tiff']:
        # If input is multipage image
        temp = read_numpy_images_multi_page_from_bytes(file_storage)

        if temp.shape[0] == 1:
            new_value = temp[0]
        else:
            new_value = temp
    else:
        raise AssertionError("Unsupported file type: {}".format(file_ext))

    return new_value

def read_ndarray_from_list_FileStorage(file_storage_list):
    new_value = []
    for file in file_storage_list:
        file_ext = file.filename.split(".")[-1].lower().strip('"')
        if file_ext in ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'jpe', 'jp2', 'pbm', 'pgm', 'ppm', 'sr', 'ras']:
            new_value.append(read_numpy_image_from_bytes(file))
        elif file_ext in ['tif', 'tiff']:
            # If input is multipage image
            temp = read_numpy_images_multi_page_from_bytes(file)
            if temp.shape[0] == 1:
                new_value.append(temp[0])
            else:
                raise AssertionError("There's a multipage tiff file, please check!")
        else:
            raise AssertionError("Unsupported file type: {}".format(file_ext))
    return new_value