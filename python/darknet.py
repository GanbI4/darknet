from ctypes import *
import time
import math
import random
import argparse
import cv2

def sample(probs):
    s = sum(probs)
    probs = [a/s for a in probs]
    r = random.uniform(0, 1)
    for i in range(len(probs)):
        r = r - probs[i]
        if r <= 0:
            return i
    return len(probs)-1

def c_array(ctype, values):
    arr = (ctype*len(values))()
    arr[:] = values
    return arr

class BOX(Structure):
    _fields_ = [("x", c_float),
                ("y", c_float),
                ("w", c_float),
                ("h", c_float)]

class DETECTION(Structure):
    _fields_ = [("bbox", BOX),
                ("classes", c_int),
                ("prob", POINTER(c_float)),
                ("mask", POINTER(c_float)),
                ("objectness", c_float),
                ("sort_class", c_int)]


class IMAGE(Structure):
    _fields_ = [("w", c_int),
                ("h", c_int),
                ("c", c_int),
                ("data", POINTER(c_float))]

class METADATA(Structure):
    _fields_ = [("classes", c_int),
                ("names", POINTER(c_char_p))]

    

#lib = CDLL("/home/pjreddie/documents/darknet/libdarknet.so", RTLD_GLOBAL)
lib = CDLL("/home/anyvision/projects/face/azyolo/libdarknet_cpu.so", RTLD_GLOBAL)
#lib = CDLL("/root/azyolo/libdarknet.so", RTLD_GLOBAL)
lib.network_width.argtypes = [c_void_p]
lib.network_width.restype = c_int
lib.network_height.argtypes = [c_void_p]
lib.network_height.restype = c_int

predict = lib.network_predict
predict.argtypes = [c_void_p, POINTER(c_float)]
predict.restype = POINTER(c_float)

set_gpu = lib.cuda_set_device
set_gpu.argtypes = [c_int]

make_image = lib.make_image
make_image.argtypes = [c_int, c_int, c_int]
make_image.restype = IMAGE

get_network_boxes = lib.get_network_boxes
get_network_boxes.argtypes = [c_void_p, c_int, c_int, c_float, c_float, POINTER(c_int), c_int, POINTER(c_int)]
get_network_boxes.restype = POINTER(DETECTION)

make_network_boxes = lib.make_network_boxes
make_network_boxes.argtypes = [c_void_p]
make_network_boxes.restype = POINTER(DETECTION)

free_detections = lib.free_detections
free_detections.argtypes = [POINTER(DETECTION), c_int]

free_ptrs = lib.free_ptrs
free_ptrs.argtypes = [POINTER(c_void_p), c_int]

network_predict = lib.network_predict
network_predict.argtypes = [c_void_p, POINTER(c_float)]

reset_rnn = lib.reset_rnn
reset_rnn.argtypes = [c_void_p]

load_net = lib.load_network
load_net.argtypes = [c_char_p, c_char_p, c_int]
load_net.restype = c_void_p

do_nms_obj = lib.do_nms_obj
do_nms_obj.argtypes = [POINTER(DETECTION), c_int, c_int, c_float]

do_nms_sort = lib.do_nms_sort
do_nms_sort.argtypes = [POINTER(DETECTION), c_int, c_int, c_float]

free_image = lib.free_image
free_image.argtypes = [IMAGE]

letterbox_image = lib.letterbox_image
letterbox_image.argtypes = [IMAGE, c_int, c_int]
letterbox_image.restype = IMAGE

load_meta = lib.get_metadata
lib.get_metadata.argtypes = [c_char_p]
lib.get_metadata.restype = METADATA

load_image = lib.load_image_color
load_image.argtypes = [c_char_p, c_int, c_int]
load_image.restype = IMAGE

ndarray_image = lib.ndarray_to_image
ndarray_image.argtypes = [POINTER(c_ubyte), POINTER(c_long), POINTER(c_long)]
ndarray_image.restype = IMAGE

rgbgr_image = lib.rgbgr_image
rgbgr_image.argtypes = [IMAGE]

predict_image = lib.network_predict_image
predict_image.argtypes = [c_void_p, IMAGE]
predict_image.restype = POINTER(c_float)

def classify(net, meta, im):
    out = predict_image(net, im)
    res = []
    for i in range(meta.classes):
        res.append((meta.names[i], out[i]))
    res = sorted(res, key=lambda x: -x[1])
    return res


def nparray_to_image(img):
    data = img.ctypes.data_as(POINTER(c_ubyte))
    image = ndarray_image(data, img.ctypes.shape, img.ctypes.strides)

    return image

def detect(net, meta, image, thresh=.5, hier_thresh=.5, nms=.45):
    im = load_image(image, 0, 0)
    num = c_int(0)
    pnum = pointer(num)
    predict_image(net, im)
    dets = get_network_boxes(net, im.w, im.h, thresh, hier_thresh, None, 0, pnum)
    num = pnum[0]
    if (nms): do_nms_obj(dets, num, meta.classes, nms);

    res = []
    for j in range(num):
        for i in range(meta.classes):
            if dets[j].prob[i] > 0:
                b = dets[j].bbox
                res.append((meta.names[i], dets[j].prob[i], (b.x, b.y, b.w, b.h)))
    res = sorted(res, key=lambda x: -x[1])
    free_image(im)
    free_detections(dets, num)
    return res

def detect_np(net, meta, np_img, thresh=.5, hier_thresh=.5, nms=.45):
    start_time = time.time()
    im = nparray_to_image(np_img)
    end_time = time.time()
    print "Elapsed cv2img Time: %f" % (end_time - start_time)

    num = c_int(0)
    pnum = pointer(num)

    start_time = time.time()
    predict_image(net, im)
    end_time = time.time()
    print "Elapsed predict Time: %f" % (end_time - start_time)

    start_time = time.time()
    dets = get_network_boxes(net, im.w, im.h, thresh, hier_thresh, None, 0, pnum)
    end_time = time.time()
    print "Elapsed get bxs Time: %f" % (end_time - start_time)

    num = pnum[0]

    start_time = time.time()
    if (nms): do_nms_obj(dets, num, meta.classes, nms);
    end_time = time.time()
    print "Elapsed nms Time: %f" % (end_time - start_time)

    start_time = time.time()
    res = []
    for j in range(num):
        for i in range(meta.classes):
            if dets[j].prob[i] > 0:
                b = dets[j].bbox
                res.append((meta.names[i], dets[j].prob[i], (b.x, b.y, b.w, b.h)))
    #res = sorted(res, key=lambda x: -x[1])
    end_time = time.time()
    print "Elapsed python stuff Time: %f" % (end_time - start_time)
    free_image(im)
    free_detections(dets, num)
    return res


if __name__ == "__main__":
    #net = load_net("cfg/densenet201.cfg", "/home/pjreddie/trained/densenet201.weights", 0)
    #im = load_image("data/wolf.jpg", 0, 0)
    #meta = load_meta("cfg/imagenet1k.data")
    #r = classify(net, meta, im)
    #print r[:10]

    parser = argparse.ArgumentParser(description='yolo video detecton with opencv')
    parser.add_argument("-c", type=str, dest="cfg", default="",
                        help="Path to net .cfg file")
    parser.add_argument("-w", type=str, dest="weights", default="",
                        help="Path to weights file")
    parser.add_argument("-d", type=str, dest="data", default='', help="path to .data file")
    parser.add_argument("-i", type=str, dest="input", default="0", help="webcam id or stream link")

    args = parser.parse_args()
    cfg = args.cfg
    weights = args.weights
    dataf = args.data
    source = args.input
    frame_count = 0

    try:
        int(source)
        source = int(source)
    except ValueError:
        pass

    cap = cv2.VideoCapture(source)
    ret, img = cap.read()
    # im=nparray_to_image(img)
    fps = cap.get(cv2.CAP_PROP_FPS)
    print("Frames per second using video.get(cv2.CAP_PROP_FPS) : {0}".format(fps))

    net = load_net(cfg, weights, 0)
    meta = load_meta(dataf)
    total_els = 0

    detect_each_frame = 6

    while (1):
        print "###############################################"
        ret, image = cap.read()
        src_img = image
        #image = cv2.resize(image, (1280,720))
        #image = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        start_time = time.time()
        scalor = 2
        ratio = 1.0 / scalor
        print ratio
        image = cv2.resize(src_img, (0,0), fx=ratio, fy=ratio)
        end_time = time.time()
        print "Elapsed cv resize Time: %f" % (end_time - start_time)
        
        start_time = time.time()
        if frame_count % detect_each_frame == 0:
            r = detect_np(net, meta, image)
            trackers = cv2.MultiTracker_create()
            print "USING DETECTOR"
        else:
            print "USING TRACKER"
            success, tr_boxes = trackers.update(image)

        end_time = time.time()
        elapsed = end_time - start_time
        total_els += elapsed
        print "Elapsed Total Time: %f" % (elapsed)

        print "###############################################"

        if frame_count % detect_each_frame == 0:
            for cat, score, bounds in r:
                x, y, w, h = bounds
                print score
                cv2.rectangle(src_img, (int(x-w/2) * scalor,int(y-h/2) * scalor),(int(x+w/2) * scalor,int(y+h/2) * scalor),(255,0,255), 5)
                box = (int(x-w/2),int(y-h/2),int(w),int(h))
                trackers.add(cv2.TrackerMOSSE_create(), image, box)
        else:
            for box in tr_boxes:
                (x, y, w, h) = [int(v) * scalor for v in box]
                cv2.rectangle(src_img, (x, y), (x + w, y + h), (0, 255, 0), 5)

        cv2.imshow("test", src_img)
        cv2.waitKey(1)
        frame_count += 1
        print "avg time to frame %f" % (total_els / frame_count)

