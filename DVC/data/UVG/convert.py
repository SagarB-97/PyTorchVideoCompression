import os

num = 1
video_name = ['HoneyBee_1920x1024_120fps_420_8bit_YUV.yuv']
short = ['HoneyBee']

for i in range(num):
    saveroot = 'images/' + short[i]
    savepath = 'images/' + short[i] + '/im%03d.png'
    if not os.path.exists(saveroot):
        os.makedirs(saveroot)
    print('ffmpeg -y -pix_fmt yuv420p -s 1920x1024 -i ' + 'videos_crop/' + video_name[i] +  ' ' + savepath)
    os.system('ffmpeg -y -pix_fmt yuv420p -s 1920x1024 -i ' + 'videos_crop/' + video_name[i] +  ' ' + savepath)
