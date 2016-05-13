# -*- coding: utf-8 -*-
"""
Created on Mon May 09 10:11:46 2016

@author: darellvdv
"""

import numpy as np
import os
import math
from osgeo import gdal
from matplotlib import pyplot as plt
import cv2

from skimage.segmentation import clear_border
from skimage.measure import label
from skimage.measure import regionprops
from skimage.color import label2rgb

import scipy.ndimage
from scipy.stats import itemfreq

# Set working directory
path = os.chdir('D:/Sugarcane_Project/201601_Sugar_Bacolod_sugarcanfields_zone_1/orthomosaics/output')

# READ RASTER (needs to be an NDVI image)
image = cv2.imread('ndvi_ren.tif',0)

# apply adaptive opencv threshold
th3 = cv2.adaptiveThreshold(image,255,cv2.ADAPTIVE_THRESH_MEAN_C,\
            cv2.THRESH_BINARY,95,2)

# Plot NDVI and adaptive thresholding            
plt.subplot(1,2,1),plt.imshow(image,cmap='nipy_spectral')
plt.title('NDVI Image'), plt.xticks([]), plt.yticks([])
plt.subplot(1,2,2),plt.imshow(th3,cmap = 'gray')
plt.title('Adaptive thresholding'), plt.xticks([]), plt.yticks([])

# Remove noise bij opening
kernel = np.ones((3,3),np.uint8)
opening = cv2.morphologyEx(th3, cv2.MORPH_OPEN, kernel)

# close image using scikit
#bw = closing(th3 > opening, square(14))

# remove artifacts connected to image border
cleared = opening.copy()
clear_border(cleared)

# Plot before and after cleaning
plt.subplot(1,2,1),plt.imshow(th3,cmap='gray')
plt.title('Before cleaning'), plt.xticks([]), plt.yticks([])
plt.subplot(1,2,2),plt.imshow(cleared,cmap = 'gray')
plt.title('After cleaning'), plt.xticks([]), plt.yticks([])

# label image regions
crop_regions = label(cleared)
image_label_overlay = label2rgb(crop_regions, image=image)

# Remove noise by area
region_size = np.bincount(crop_regions.ravel())
region_mask = region_size > 200
region_mask[0] = 0
regions_cleaned = region_mask[crop_regions]

# Re-label cleaned areas
crop_regions_relab = label(regions_cleaned)
regions = regionprops(crop_regions_relab)
region_size_new = np.bincount(crop_regions_relab.ravel())

# Plot before and after labeling and cleaning on area
plt.subplot(1,2,1),plt.imshow(cleared,cmap='gray')
plt.title('Before labeling'), plt.xticks([]), plt.yticks([])
plt.subplot(1,2,2),plt.imshow(crop_regions_relab,cmap = 'nipy_spectral')
plt.title('After labeling'), plt.xticks([]), plt.yticks([])

row_centers = ndimage.measurements.center_of_mass(regions_cleaned,crop_regions_relab,itemfreq(crop_regions_relab)[1:,0])
np.savetxt('centroidscord.txt', row_centers)

#-----------------------------------------
# Calulcate lines from skikit regions cleaned

from skimage import img_as_ubyte

cv_image = img_as_ubyte(regions_cleaned)

lines = cv2.HoughLinesP(cv_image,rho=0.9,theta=np.pi/180,threshold=500,lines=np.array([]),
                        minLineLength=100,maxLineGap=25)
for line in lines:
   x1,y1,x2,y2 = line[0]
   cv2.line(cv_image,(x1,y1),(x2,y2),(50,255,10),2)
   
# Extract only the coordinates from NP array
coordinates = lines[0:,0,]
np.save('coordinates.npy', coordinates)
np.savetxt('coordinates.txt', coordinates)


def anglecalc(hough_lines):
    '''
    hough_lines = output of OpenCV hough lines transformation
    
    Calculates angle based on middle percentile of hough lines
    '''
    
    # Calculate angle
    dx = hough_lines[0:,2] - coordinates[0:,0]
    dy = hough_lines[0:,3] - hough_lines[0:,1]
    
    rads = np.arctan2(dy,dx)
    
    # Select rads based on quantile (80% of data) and avarage
    q1, q2 = np.percentile(rads, 10), np.percentile(rads, 90)

    radssubq1, radssubq2 = np.mean((rads[rads[0:,] <= q1])), np.mean((rads[rads[0:,] >= q2]))
    radm = (radssubq1 + radssubq2) / 2
    
    # Convert rads 
    radconv = np.pi - (-radm)
    radconv = np.pi - radconv
    
    angle = (radconv * 180) / (np.pi)
    
    radangle = (radconv, angle)
    
    return radangle


# CREATE GRID ##

imgun = cv2.imread('ndvi_ren.tif',cv2.IMREAD_UNCHANGED)
img = cv2.imread('ndvi_ren.tif',cv2.IMREAD_GRAYSCALE)

cv2.imshow('ndvi',img)
cv2.waitKey(0)
cv2.destroyAllWindows()

pixels = img[57, 23:87]

line_amount = 20
line_length = 2000
angle = anglecalc(coordinates)[0]
spacing = 20 # change this to automaticcaly detect cell size

def gridcreate(line_amount, line_length, angle, spacing):
    '''
    line_amount = amount of lines to be created
    line_length = total length from starting point for each line
    angle = angle as determined by hough transform
    spacing = spacing between lines (pixel size of raster)
    
    Creates grid without spatial reference
    '''
    
    # Initialize array of 2 by 3
    w, h = 2, line_amount
    begin_coord = [[0 for x in range(w)] for y in range(h)]
    
    begin_coord_array = np.zeros((h, w))
    end_coord_array = np.zeros((h, w))
    # Set x and y min
    xmin = 0 # set this to automaticcaly detect xmin
    ymax = 1910 # set this to automaticcaly detect ymax
    
    # Generate start coordinates and fill array 
    if anglecalc(coordinates)[1] <= 210 and anglecalc(coordinates)[1] >= 150:
        for i in range(line_amount):
            begin_coord_array[i][0] = xmin
            
        for i in range(line_amount):
            begin_coord_array[i][1] = (ymax + (i * spacing))
    
    else:
        for i in range(line_amount):
            begin_coord_array[i][0] = (xmin + (i * spacing))
            
        for i in range(line_amount):
            begin_coord_array[i][1] = ymax
       
    # Calulcate end points based on length and angle 
    end_coord = [[0 for x in range(w)] for y in range(h)]
    
    for i in range(line_amount):
        end_coord_array[i][0] = begin_coord_array[i][0] + line_length * math.cos(angle)
        
    for i in range(line_amount):
        end_coord_array[i][1] = begin_coord_array[i][1] - line_length * math.sin(angle)
        
    return begin_coord_array, end_coord_array
        


grid = gridcreate(line_amount, line_length, angle, spacing)
grid = np.array(grid)

# Plot the grid
plt.imshow(image)
plt.plot([grid[0,:,0], grid[1,:,0]], [grid[0,:,1], grid[1,:,1]], 'ro-')

plt.show()



def extractvalues(line_grid, raster):
    '''
    line_grid = grid of lines as created with the gridcreate tool
    raster = raster image of which values need to be extracted
    
    extracts values based on coordinates as created with the gridcreate tool
    Samples at each pixel using nearest neighbour and line length
    '''
    
    # Extract all coordinates for later plotting
    x0, y0 = line_grid[0,:,0], line_grid[0,:,1]
    x1, y1 = line_grid[1,:,0], line_grid[1,:,1]
    
    length = np.hypot(x1[1]-x0[1], y1[1]-y0[1])
    
    # Check if line length is correct
    if int(np.hypot(x1[1]-x0[1], y1[1]-y0[1])) != line_length:
        print 'Error: line length not in same range'
        return
        
    else:
        w, h = line_length, line_amount
        xvalues_array = np.zeros((h, w))
        for i in range(line_amount):
            xvalues_array[i] = np.linspace(line_grid[0][i][0], line_grid[1][i][0], length)
    
        yvalues_array = np.zeros((h, w))
        for i in range(line_amount):
            yvalues_array[i] = np.linspace(line_grid[0][i][1], line_grid[1][i][1], length)
            
        # Extract the values along the line
        imaget = np.transpose(raster)
        zi = imaget[xvalues_array.astype(np.int), yvalues_array.astype(np.int)]

        zitrans = zi.T
    
    return zitrans
    
values = extractvalues(grid, image)

# Extract line from coordinates
x0, y0 = grid[0,:,0], grid[0,:,1]
x1, y1 = grid[1,:,0], grid[1,:,1]

#-- Plot grid and value lines
fig, axes = plt.subplots(nrows=2)
axes[0].imshow(image)
axes[0].plot([x0, x1], [y0, y1], 'ro-')
axes[0].axis('image')

axes[1].plot(values)

plt.show()


# Calculate lines with highest values
valuestotal = np.zeros((line_amount, 1))
for i in range(line_amount):
    valuestotal[i] = np.sum(values[:,i])

valuestotal_max = valuestotal > np.percentile(valuestotal, 50)



def rotate_lines(line_grid_max, degrees):
    '''
    line_grid_max = grid of max value lines as created with the gridcreate tool and subsetted
    degrees = list of degrees to rotate lines with
    
    Rotate lines the given angle about their centers. 
    '''
    # Convert angle from degrees to radians
    theta = math.radians(degrees)
    cosang, sinang = math.cos(theta), math.sin(theta)
    
    # Find logical center (avg x and avg y) of entire line 
    cxcy = np.zeros((line_amount, 2))
    for i in range(line_amount):
        cxcy[i,0] = (grid[0][i][0] + grid[1][i][0]) / 2
        cxcy[i,1] = (grid[0][i][1] + grid[1][i][1]) / 2
        
        # Rotate each around whole polyline's center point
        tx1, ty1 = np.zeros(line_amount), np.zeros(line_amount)
        tx1[i], ty1[i] = (grid[0][i][0] - cxcy[i,0]), (grid[1][i][0] - cxcy[i,1])
        
        p1x, p2y = np.zeros(line_amount), np.zeros(line_amount)
        p1x[i] = ( tx1[i] * cosang + ty1[i] * sinang) + cxcy[i,0]
        p2y[i] = (-tx1[i] * sinang + ty1[i] * cosang) + cxcy[i,1] 
        
    
    orgcord = np.zeros((line_amount, 4))
    for i in range(line_amount):
        orgcord[i,0], orgcord[i,1] = grid[0][i][0], grid[1][i][0]
        orgcord[i,2], orgcord[i,3] = grid[0][i][1], grid[1][i][1]
    
    tx1, ty1 = np.zeros(line_amount), np.zeros(line_amount)
    p1x, p1y, p2x, p2y = np.zeros(line_amount), np.zeros(line_amount), np.zeros(line_amount), np.zeros(line_amount)    
    for i in cxcy:
        for j in orgcord:
            for a in range(line_amount):
                tx1[a] = j[0] - i[0]
                ty1[a] = j[1] - i[1]                
                
                p1x = ( tx1[i] * cosang + ty1[i] * sinang) + cxcy[i,0]
                p1y = (-tx1[i] * sinang + ty1[i] * cosang) + cxcy[i,1] 
                
    
                
    for i in cxcy:
        print i[1]
        
        tx1, ty1 = np.zeros(line_amount), np.zeros(line_amount)
        tx1[i], ty1[i] = (grid[0][i][0] - cxcy[i,0]), (grid[1][i][0] - cxcy[i,1])
        p1x = ( tx1[i] * cosang + ty1[i] * sinang) + cxcy[i,0]
        p2y = (-tx1[i] * sinang + ty1[i] * cosang) + cxcy[i,1]        
        
        
        tx1, ty1 = x0 - cx, y0 - cy
        p1x = ( tx1 * cosang + ty1 * sinang) + cx
        p1y = (-tx1 * sinang + ty1 * cosang) + cy
        tx2, ty2 = x2 - cx, y2 - cy
        p2x = ( tx2 * cosang + ty2 * sinang) + cx
        p2y = (-tx2 * sinang + ty2 * cosang) + cy
        

    for pl in self:
        # Find logical center (avg x and avg y) of entire polyline
        n = len(pl.lines)*2  # Total number of points in polyline
        cx = sum(sum(line.get_xdata()) for line in pl.lines) / n
        cy = sum(sum(line.get_ydata()) for line in pl.lines) / n

        for line in pl.lines:
            # Retrieve vertices of the line
            x1, x2 = line.get_xdata()
            y1, y2 = line.get_ydata()

            # Rotate each around whole polyline's center point
            tx1, ty1 = x1-cx, y1-cy
            p1x = ( tx1*cosang + ty1*sinang) + cx
            p1y = (-tx1*sinang + ty1*cosang) + cy
            tx2, ty2 = x2-cx, y2-cy
            p2x = ( tx2*cosang + ty2*sinang) + cx
            p2y = (-tx2*sinang + ty2*cosang) + cy

            # Replace vertices with updated values
            pl.set_line(line, [p1x, p2x], [p1y, p2y])

rotated = rotate_lines(grid)


# ROTATE LINES
theta = math.radians(0.5)  # Convert angle from degrees to radians
cosang, sinang = math.cos(theta), math.sin(theta)

cx = (grid[0][0][0] + grid[1][0][0]) / 2
cy = (grid[0][0][1] + grid[1][0][1]) / 2

x0, x1 = grid[0][0][0], grid[1][0][0]
y0, y1 = grid[0][0][1], grid[1][0][1]

tx1, ty1 = x0 - cx, y0 - cy
p1x = ( tx1 * cosang + ty1 * sinang) + cx
p1y = (-tx1 * sinang + ty1 * cosang) + cy
tx2, ty2 = x2 - cx, y2 - cy
p2x = ( tx2 * cosang + ty2 * sinang) + cx
p2y = (-tx2 * sinang + ty2 * cosang) + cy






plt.imshow(img, cmap = 'gray', interpolation = 'bicubic')
plt.xticks([]), plt.yticks([])  # to hide tick values on X and Y axis
plt.plot([x1, y1],[x2, y2],'c', linewidth=5)
plt.show()