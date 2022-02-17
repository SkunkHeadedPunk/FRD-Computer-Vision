from picamera.array import PiRGBArray
from picamera import PiCamera
import picamera
import cv2 as cv
import numpy as np
import math

# Image capture dimensions
WIDTH, HEIGHT = 1920, 1088
width, height = str(WIDTH), str(HEIGHT)

# Display image scaling
scale = 0.5
width_d = int(WIDTH * scale)
height_d = int(HEIGHT * scale)
dim = (width_d, height_d)

# Marker length / scaling
##MARKER_LENGTH_IN = 4.5 / 25.4 # "5mm Marker"
MARKER_LENGTH_IN = 0.3 # BS Value
print("MARKER_LENGTH_IN = ", MARKER_LENGTH_IN)

# Import Aruco marker dictionary
arucoDict = cv.aruco.getPredefinedDictionary(cv.aruco.DICT_4X4_100)

# Import camera calibration data
KD = np.load('CV_CameraCalibrationData.npz')
K = KD['k']
DIST = KD['dist']

# Calculate 3D distance between markers
def get_dist(img, ids, corners, newCamMtx):
    
    # Get rotation and translation vectors with respect to marker
    rvecs, tvecs, _ = cv.aruco.estimatePoseSingleMarkers(
        corners,
        markerLength=MARKER_LENGTH_IN,
        cameraMatrix=newCamMtx,
        distCoeffs=0
        )

    # Extract translation vectors for each marker
    tvec0 = tvecs[0][0]
    tvec1 = tvecs[1][0]

    # Calculate distance between markers
    distance = math.sqrt((tvec0[0] - tvec1[0]) ** 2 +
                         (tvec0[1] - tvec1[1]) ** 2 + 
                         (tvec0[2] - tvec1[2]) ** 2
                         )

    # Draw marker borders & axes on display image
    cv.aruco.drawDetectedMarkers(image=img,
                                 corners=corners,
                                 ids=ids,
                                 borderColor=(0, 0, 255)
                                 )

    # Resize display image
    disp_img = cv.resize(img, dim, interpolation=cv.INTER_AREA)

    # Return calculated distance and marked display image
    return distance, disp_img


if __name__ == '__main__':
    # Initialize Camera
    camera = PiCamera()
    camera.resolution = (WIDTH, HEIGHT)
    camera.exposure_mode = 'sports'
    rawCapture = PiRGBArray(camera, size=(WIDTH, HEIGHT))

    # Initialize stage statuses
    gotMin = False
    gotMax = False

    # For each frame...
    for frame in camera.capture_continuous(rawCapture,
                                           format="bgr",
                                           use_video_port=True
                                           ):
        # Get image and clear stream
        img = frame.array
        rawCapture.truncate(0)

        # Get optimal camera matrix
        newCamMtx, roi = cv.getOptimalNewCameraMatrix(cameraMatrix=K,
                                                      distCoeffs=DIST,
                                                      imageSize=(WIDTH, HEIGHT),
                                                      alpha=1,
                                                      newImgSize=(WIDTH, HEIGHT)
                                                      )
        # Correct image using optimal camera matrix
        corr_img = cv.undistort(img,
                                K,
                                DIST,
                                None,
                                newCamMtx
                                )

        # Detect Aruco marker ids and corners
        corners, ids, _ = cv.aruco.detectMarkers(image=img,
                                                 dictionary=arucoDict,
                                                 cameraMatrix=K,
                                                 distCoeff=DIST
                                                 )

        # Initialize detected marker count
        count = 0

        # Get maximum control distance (Stage 2)
        if gotMin == True:
            if gotMax == False:
                if ids is not None:
                    for tag in ids:
                        count = count + 1
                        print(count, " tag detected (max)")
                        
                # When two markers are detected, get distance and show image                        
                if count >= 2:
                    maxDist, maxImg = get_dist(img, ids, corners, newCamMtx)
                    print("Maximum Distance: ", maxDist)
                    gotMax = True

                    cv.imshow("Max. Control Img", maxImg)
                    cv.waitKey(0)
                    
                    # Print calibration distance range and difference
                    print("Control Distance Range: ",
                          round(minDist, 4), " - ",
                          round(maxDist, 4), " inches")
                    print("Control Distance Difference : ",
                          round(maxDist - minDist, 4), " inches")

        # Get minimum control distance (Stage 1)
        if gotMin == False:
            if ids is not None:
                for tag in ids:
                    count = count + 1
                    print(count, " tag detected (min)")
                    
            # When two markers are detected, get distance and show image        
            if count >= 2:
                minDist, minImg = get_dist(img, ids, corners, newCamMtx)
                print("Minimum Distance: ", minDist)
                gotMin = True

                cv.imshow("Min. Control Img", minImg)
                cv.waitKey(0)
                    

        # Resize and show live stream feed
        resized = cv.resize(img, dim, interpolation = cv.INTER_AREA)
            
        cv.imshow("Stream", resized)
        cv.waitKey(1)
        
        rawCapture.truncate(0)
