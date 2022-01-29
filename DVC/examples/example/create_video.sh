cd performance/images_gauss_error_0_2
# ffmpeg -framerate 6 -i %d_orig.png -c:v copy orig.mkv
ffmpeg -framerate 6 -i %d_recon.png -c:v copy recon.mkv
