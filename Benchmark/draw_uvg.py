import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import os
import imageio
import cv2
import numpy as np

prefix = 'UVGresults'

font = {'family': 'serif', 'weight': 'normal', 'size': 12}
matplotlib.rc('font', **font)
LineWidth = 2


# bpp = [0.054142857142857145, 0.07154285714285714, 0.10525714285714284, 0.14809999999999998]
# psnr = [35.08253188344889, 35.72518803688726, 36.887165873124644, 37.737663494538516]
# msssim = [0.9568914285714286, 0.9618171428571429, 0.9699657142857142, 0.9762942857142859]
# MLVC, = plt.plot(bpp, psnr, "m-o", color='darkorange', linewidth=LineWidth, label='M-LVC')

bpp, psnr = [0.150682, 0.089331, 0.061964, 0.04496], [38.029177, 37.062886, 36.041041, 34.854808]
FVC, = plt.plot(bpp, psnr, "c-o", color="dimgrey", linewidth=LineWidth, label='FVC')


bpp, psnr = [0.040222, 0.059522, 0.090525, 0.155768], [34.36477, 35.594595, 36.651909, 37.74166]
rafc, = plt.plot(bpp, psnr, 'c-*', color="blueviolet", linewidth=LineWidth, label='HU_ECCV20')

bpp, psnr = [0.055, 0.07727, 0.114, 0.189], [34.655, 35.941, 37.066, 38.061]
LU, = plt.plot(bpp, psnr, "c-o", color="royalblue", linewidth=LineWidth, label='LU_ECCV20')

bpp, psnr =  [0.047607, 0.067984, 0.114375, 0.222292], [34.412507, 35.861409, 36.950722, 38.393440]
EA, = plt.plot(bpp, psnr, "g-o", color="orange", linewidth=LineWidth, label='EA_CVPR20')

bpp, msssim = [0.0524, 0.0781, 0.1278, 0.2303], [34.5390, 35.8618, 37.1899, 38.4590]
RY, = plt.plot(bpp, msssim, "c-o", color="darkred", linewidth=LineWidth, label='RY_CVPR20')

bpp, psnr = [0.1744, 0.0865, 0.0572, 0.0406], [38.1853, 37.0549, 35.9941, 34.702]
Liu, = plt.plot(bpp, psnr, "c-o", color="green", linewidth=LineWidth, label='Liu et al.')

bpp = [0.12377, 0.16239, 0.1983, 0.229, 0.2699, 0.3113]
psnr = [36.0736, 36.663, 36.9157, 37.1818, 37.5149, 37.6513]
eccv, = plt.plot(bpp, psnr, "b-*", linewidth=LineWidth, label='CW_ECCV18')

bpp, psnr = [0.052080695, 0.060782631, 0.073709049, 0.094923348, 0.132789571, 0.211082522, 0.539064405], [35.01218307, 35.69302652, 36.48478603, 37.28231639, 38.21140795, 39.28474608, 41.47109755]
bpp = [0.052080695, 0.060782631, 0.073709049, 0.094923348 , 0.132789571, 0.211082522]
psnr = [35.01218307, 35.69302652, 36.48478603, 37.28231639, 38.21140795, 39.28474608]
iccv, = plt.plot(bpp, psnr, "c-*", linewidth=LineWidth, label='AD_ICCV19')

bpp, psnr, msssim = [0.185334726, 0.108594607, 0.076628071, 0.06013501], [37.69306179, 36.68785979, 35.52100014, 34.54747739], [0.971436012, 0.96574275, 0.957191524, 0.949676821]
DVC, = plt.plot(bpp, psnr, "y-o", linewidth=LineWidth, label='DVC')

bpp, psnr, msssim = [0.1580652024, 0.09510494048, 0.06334845238, 0.05001147619], [37.83633036, 36.77129217, 35.7142323, 35.03949596], [0.971793119, 0.9658603452, 0.9588654881, 0.9534102738]
DVCp, = plt.plot(bpp, psnr, "y-o", color="peru", linewidth=LineWidth, label='DVC++')

# Ours default
bpp, psnr, msssim = [0.360398059, 0.148765645, 0.076027148, 0.044918456], [38.17135327, 36.64284159, 35.23609537, 33.81775541], [0.978673172, 0.967889817, 0.95755343, 0.945528742]
h264, = plt.plot(bpp, psnr, "m--s", linewidth=LineWidth, label='H.264')

bpp, psnr, msssim = [0.28976166, 0.123933107, 0.058072298, 0.032210368], [38.23271652, 36.77568687, 35.3981028, 33.96352277], [0.976551152, 0.966845419, 0.956987797, 0.945751638]
h265, = plt.plot(bpp, psnr, "r--v", linewidth=LineWidth, label='H.265')

savepathpsnr = prefix + '/UVG_psnr'
print(prefix)
if not os.path.exists(prefix):
    os.makedirs(prefix)
plt.legend(handles=[h264, h265, DVC, DVCp, eccv, iccv, EA, RY, Liu, LU, rafc, FVC], loc=4)
plt.grid()
plt.xlabel('Bpp')
plt.ylabel('PSNR')
plt.title('UVG dataset')
# plt.savefig(savepathpsnr + '.eps', format='eps', dpi=300, bbox_inches='tight')
plt.savefig(savepathpsnr + '.png')
plt.clf()

# ----------------------------------------MSSSIM-------------------------------------------------

# bpp = [0.054142857142857145, 0.07154285714285714, 0.10525714285714284, 0.14809999999999998]
# psnr = [35.08253188344889, 35.72518803688726, 36.887165873124644, 37.737663494538516]
# msssim = [0.9568914285714286, 0.9618171428571429, 0.9699657142857142, 0.9762942857142859]
# MLVC, = plt.plot(bpp, msssim, "m-o", color='darkorange', linewidth=LineWidth, label='M-LVC')

bpp, psnr = [0.363749, 0.227332, 0.134257, 0.085478], [0.986765, 0.982525, 0.976374, 0.969245]
FVC, = plt.plot(bpp, psnr, "c-o", color="dimgrey", linewidth=LineWidth, label='FVC')

bpp, psnr = [0.218918, 0.130343, 0.077172, 0.04779], [0.978714, 0.972417, 0.965527, 0.956974]
rafc, = plt.plot(bpp, psnr, 'c-*', color="blueviolet", linewidth=LineWidth, label='HU_ECCV20')
    
bpp, psnr = [0.258854285714286,  0.16422, 0.10424, 0.072], [0.979627142857143, 0.97517, 0.969065714285714, 0.96103]
LU, = plt.plot(bpp, psnr, "c-o", color="royalblue", linewidth=LineWidth, label='LU_ECCV20')

bpp, psnr =  [0.060844, 0.085622, 0.128203, 0.243156, 0.345827], [0.961259, 0.968878, 0.974102, 0.982171, 0.985049]
EA, = plt.plot(bpp, psnr, "g-o", color="orange", linewidth=LineWidth, label='EA_CVPR20')

bpp, msssim = [0.0764, 0.1133, 0.2125, 0.3839], [0.9640, 0.9693, 0.9779, 0.9832]
RY, = plt.plot(bpp, msssim, "c-o", color="darkred", linewidth=LineWidth, label='RY_CVPR20')

bpp, msssim = [0.5185, 0.3277, 0.1881, 0.1114], [0.9895, 0.98579, 0.98059, 0.97362]
Liu, = plt.plot(bpp, msssim, "c-o", color="green", linewidth=LineWidth, label='Liu et al.')

bpp = [0.12377, 0.16239, 0.1983, 0.229, 0.2699, 0.3113]
msssim = [0.96126, 0.96591, 0.96708, 0.96867, 0.97117, 0.97186]
eccv, = plt.plot(bpp, msssim, "b-*", linewidth=LineWidth, label='CW_ECCV18')

bpp = [0.052080695, 0.060782631, 0.073709049, 0.094923348, 0.132789571, 0.211082522]
msssim = [0.953062573, 0.958916648, 0.964496266, 0.969689354, 0.974711348, 0.979329442]
iccv, = plt.plot(bpp, msssim, "c-*", linewidth=LineWidth, label='AD_ICCV19')

bpp, psnr, msssim = [0.185334726, 0.108594607, 0.076628071, 0.06013501], [37.69306179, 36.68785979, 35.52100014, 34.54747739], [0.971436012, 0.96574275, 0.957191524, 0.949676821]
DVC, = plt.plot(bpp, msssim, "y-o", linewidth=LineWidth, label='DVC')

bpp, psnr, msssim = [0.1580652024, 0.09510494048, 0.06334845238, 0.05001147619], [37.83633036, 36.77129217, 35.7142323, 35.03949596], [0.971793119, 0.9658603452, 0.9588654881, 0.9534102738]
DVCp, = plt.plot(bpp, msssim, "y-o", color="peru", linewidth=LineWidth, label='DVC++')

bpp, msssim = [0.25601, 0.18540, 0.11757, 0.06162, 0.04352, 0.03561], [0.97627, 0.97311, 0.96770, 0.95592, 0.94839, 0.94459]
ha_iccv, = plt.plot(bpp, msssim, "g-o", color="lime", linewidth=LineWidth, label='AH_ICCV19')

bpp, psnr, msssim = [0.360398059, 0.148765645, 0.076027148, 0.044918456], [38.17135327, 36.64284159, 35.23609537, 33.81775541], [0.978673172, 0.967889817, 0.95755343, 0.945528742]
h264, = plt.plot(bpp, msssim, "m--s", linewidth=LineWidth, label='H.264')

bpp, psnr, msssim = [0.28976166, 0.123933107, 0.058072298, 0.032210368], [38.23271652, 36.77568687, 35.3981028, 33.96352277], [0.976551152, 0.966845419, 0.956987797, 0.945751638]
h265, = plt.plot(bpp, msssim, "r--v", linewidth=LineWidth, label='H.265')


savepathmsssim = prefix + '/' + 'UVG_msssim'# + '.eps'
plt.legend(handles=[h264, h265, DVC, DVCp, eccv, ha_iccv, iccv, EA, RY, Liu, LU, rafc, FVC], loc=4)
plt.grid()
plt.xlabel('Bpp')
plt.ylabel('MS-SSIM')
plt.title('UVG dataset')
# plt.savefig(savepathmsssim + '.eps', format='eps', dpi=300, bbox_inches='tight')
plt.savefig(savepathmsssim + '.png')
plt.clf()


savepath = prefix + '/' + 'UVG' + '.png'
img1 = cv2.imread(savepathpsnr + '.png')
img2 = cv2.imread(savepathmsssim + '.png')

image = np.concatenate((img1, img2), axis=1)
cv2.imwrite(savepath, image)