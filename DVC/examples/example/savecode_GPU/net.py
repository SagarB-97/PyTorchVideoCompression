import numpy as np
import os
import torch
import torchvision.models as models
from torch.autograd import Variable
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
from torch.utils.data import DataLoader
import sys
import math
import torch.nn.init as init
import logging
from torch.nn.parameter import Parameter
from subnet import *
import torchac

def save_model(model, iter):
    torch.save(model.state_dict(), "./snapshot/iter{}.model".format(iter))

def load_model(model, f):
    with open(f, 'rb') as f:
        pretrained_dict = torch.load(f)
        model_dict = model.state_dict()
        pretrained_dict = {k: v for k, v in pretrained_dict.items() if k in model_dict}
        model_dict.update(pretrained_dict)
        model.load_state_dict(model_dict)
    f = str(f)
    if f.find('iter') != -1 and f.find('.model') != -1:
        st = f.find('iter') + 4
        ed = f.find('.model', st)
        return int(f[st:ed])
    else:
        return 0



class VideoCompressor(nn.Module):
    def __init__(self):
        super(VideoCompressor, self).__init__()
        # self.imageCompressor = ImageCompressor()
        self.opticFlow = ME_Spynet()
        self.mvEncoder = Analysis_mv_net()
        self.Q = None
        self.mvDecoder = Synthesis_mv_net()
        self.warpnet = Warp_net()
        self.resEncoder = Analysis_net()
        self.resDecoder = Synthesis_net()
        self.respriorEncoder = Analysis_prior_net()
        self.respriorDecoder = Synthesis_prior_net()
        self.bitEstimator_z = BitEstimator(out_channel_N)
        self.bitEstimator_mv = BitEstimator(out_channel_mv)
        # self.flow_warp = Resample2d()
        # self.bitEstimator_feature = BitEstimator(out_channel_M)
        self.warp_weight = 0
        self.mxrange = 150
        self.calrealbits = True

    def forwardFirstFrame(self, x):
        output, bittrans = self.imageCompressor(x)
        cost = self.bitEstimator(bittrans)
        return output, cost

    def motioncompensation(self, ref, mv):
        warpframe = flow_warp(ref, mv)
        inputfeature = torch.cat((warpframe, ref), 1)
        prediction = self.warpnet(inputfeature) + warpframe
        return prediction, warpframe

    def encode_bytestreams(self, quant_mv, compressed_feature_renorm, recon_sigma, compressed_z):
        def iclr18_estrate_bits_mv_bytes(mv):

            def getrealbits(x):
                cdfs = []
                x = x + self.mxrange
                n,c,h,w = x.shape
                for i in range(-self.mxrange, self.mxrange):
                    cdfs.append(self.bitEstimator_mv(i - 0.5).view(1, c, 1, 1, 1).repeat(1, 1, h, w, 1))
                cdfs = torch.cat(cdfs, 4).cpu().detach()
                byte_stream = torchac.encode_float_cdf(cdfs, x.cpu().detach().to(torch.int16), check_input_bounds=True)
                return byte_stream

            byte_stream = getrealbits(mv)

            return byte_stream
        byte_stream_mv = iclr18_estrate_bits_mv_bytes(quant_mv)

        def feature_probs_based_sigma_bytes(feature, sigma):
            
            def getrealbitsg(x, gaussian):
                # print("NIPS18noc : mn : ", torch.min(x), " - mx : ", torch.max(x), " range : ", self.mxrange)
                cdfs = []
                x = x + self.mxrange
                n,c,h,w = x.shape
                for i in range(-self.mxrange, self.mxrange):
                    cdfs.append(gaussian.cdf(i - 0.5).view(n,c,h,w,1))
                cdfs = torch.cat(cdfs, 4).cpu().detach()
                
                byte_stream = torchac.encode_float_cdf(cdfs, x.cpu().detach().to(torch.int16), check_input_bounds=True)
                return byte_stream


            mu = torch.zeros_like(sigma)
            sigma = sigma.clamp(1e-5, 1e10)
            gaussian = torch.distributions.laplace.Laplace(mu, sigma)
            byte_stream = getrealbitsg(feature, gaussian)

            return byte_stream
        byte_stream_feature = feature_probs_based_sigma_bytes(compressed_feature_renorm, recon_sigma)

        def iclr18_estrate_bits_z_bytes(z):
            def getrealbits(x):
                cdfs = []
                x = x + self.mxrange
                n,c,h,w = x.shape
                for i in range(-self.mxrange, self.mxrange):
                    cdfs.append(self.bitEstimator_z(i - 0.5).view(1, c, 1, 1, 1).repeat(1, 1, h, w, 1))
                cdfs = torch.cat(cdfs, 4).cpu().detach()
                byte_stream = torchac.encode_float_cdf(cdfs, x.cpu().detach().to(torch.int16), check_input_bounds=True)
                return byte_stream
            byte_stream = getrealbits(z)

            return byte_stream
        byte_stream_z = iclr18_estrate_bits_z_bytes(compressed_z)

        return byte_stream_mv, byte_stream_feature, byte_stream_z

    def forward_encode(self, input_image, referframe):
        estmv = self.opticFlow(input_image, referframe)
        mvfeature = self.mvEncoder(estmv)
        quant_mv = torch.round(mvfeature) ## Motion vectors

        quant_mv_upsample = self.mvDecoder(quant_mv)
        prediction, warpframe = self.motioncompensation(referframe, quant_mv_upsample)
        input_residual = input_image - prediction
        feature = self.resEncoder(input_residual)
        compressed_feature_renorm = torch.round(feature) ## Residual

        z = self.respriorEncoder(feature)
        compressed_z = torch.round(z) ## Sigma

        recon_sigma = self.respriorDecoder(compressed_z) ## Reconstructed sigma

        byte_stream_mv, byte_stream_feature, byte_stream_z = self.encode_bytestreams(
            quant_mv, compressed_feature_renorm, recon_sigma, compressed_z)
        
        return byte_stream_mv, quant_mv.shape, \
            byte_stream_feature, compressed_feature_renorm.shape, \
            byte_stream_z, compressed_z.shape

    def forward_encode_v2(self, input_image, referframe):
        estmv = self.opticFlow(input_image, referframe)
        mvfeature = self.mvEncoder(estmv)
        quant_mv = torch.round(mvfeature) ## Motion vectors

        quant_mv_upsample = self.mvDecoder(quant_mv)
        prediction, warpframe = self.motioncompensation(referframe, quant_mv_upsample)
        input_residual = input_image - prediction
        feature = self.resEncoder(input_residual)
        compressed_feature_renorm = torch.round(feature) ## Residual

        quant_mv = torch.clamp(quant_mv, min=-31, max=31)
        compressed_feature_renorm = torch.clamp(compressed_feature_renorm, min=-31, max=31)
        
        return quant_mv, compressed_feature_renorm

    def decode_bytestreams(self, byte_stream_mv, shape_mv,
                            byte_stream_feature, shape_feature, 
                            byte_stream_z, shape_z):
        
        def iclr18_estrate_bits_z_decode(byte_stream_z, shape_z):
            def decode_from_bits(byte_stream, shape):
                cdfs = []
                n,c,h,w = shape
                for i in range(-self.mxrange, self.mxrange):
                    cdfs.append(self.bitEstimator_z(i - 0.5).view(1, c, 1, 1, 1).repeat(1, 1, h, w, 1))
                cdfs = torch.cat(cdfs, 4).cpu().detach()

                decoded = torchac.decode_float_cdf(cdfs, byte_stream)

                return decoded - self.mxrange
            decoded = decode_from_bits(byte_stream_z, shape_z)

            return decoded
        compressed_z =  iclr18_estrate_bits_z_decode(byte_stream_z, shape_z)
        compressed_z = compressed_z.to(torch.float32)
        recon_sigma = self.respriorDecoder(compressed_z)

        def feature_probs_based_sigma_decode(byte_stream_feature, shape_feature, sigma):
            def decode_from_bits(byte_stream, shape, gaussian):
                # print("NIPS18noc : mn : ", torch.min(x), " - mx : ", torch.max(x), " range : ", self.mxrange)
                cdfs = []
                n,c,h,w = shape
                for i in range(-self.mxrange, self.mxrange):
                    cdfs.append(gaussian.cdf(i - 0.5).view(n,c,h,w,1))
                cdfs = torch.cat(cdfs, 4).cpu().detach()
                decoded = torchac.decode_float_cdf(cdfs, byte_stream)
                return decoded - self.mxrange
            
            mu = torch.zeros_like(sigma)
            sigma = sigma.clamp(1e-5, 1e10)
            gaussian = torch.distributions.laplace.Laplace(mu, sigma)
            decoded = decode_from_bits(byte_stream_feature, shape_feature, gaussian)

            return decoded
        compressed_feature_renorm = feature_probs_based_sigma_decode(byte_stream_feature, 
                                shape_feature, recon_sigma)
        compressed_feature_renorm = compressed_feature_renorm.to(torch.float32)
        
        def iclr18_estrate_bits_mv_decode(byte_stream_mv, shape_mv):

            def decode_from_bits(byte_stream, shape):
                cdfs = []
                n,c,h,w = shape
                for i in range(-self.mxrange, self.mxrange):
                    cdfs.append(self.bitEstimator_mv(i - 0.5).view(1, c, 1, 1, 1).repeat(1, 1, h, w, 1))
                cdfs = torch.cat(cdfs, 4).cpu().detach()
                decoded = torchac.decode_float_cdf(cdfs, byte_stream)
                return decoded - self.mxrange
            decoded = decode_from_bits(byte_stream_mv, shape_mv)
            return decoded
        quant_mv = iclr18_estrate_bits_mv_decode(byte_stream_mv, shape_mv)
        quant_mv = quant_mv.to(torch.float32)

        return quant_mv, compressed_feature_renorm

    def forward_decode(self, referframe, 
                    byte_stream_mv, shape_mv,
                    byte_stream_feature, shape_feature,
                    byte_stream_z, shape_z):
        quant_mv, compressed_feature_renorm = self.decode_bytestreams(byte_stream_mv, shape_mv, 
                                                    byte_stream_feature, shape_feature,
                                                    byte_stream_z, shape_z)

        quant_mv_upsample = self.mvDecoder(quant_mv)
        prediction, warpframe = self.motioncompensation(referframe, quant_mv_upsample)
        recon_res = self.resDecoder(compressed_feature_renorm)
        recon_image = prediction + recon_res
        clipped_recon_image = recon_image.clamp(0., 1.)

        return clipped_recon_image, recon_image
    
    def forward_decode_v2(self, referframe, 
                    quant_mv, compressed_feature_renorm):

        quant_mv_upsample = self.mvDecoder(quant_mv)
        prediction, warpframe = self.motioncompensation(referframe, quant_mv_upsample)
        recon_res = self.resDecoder(compressed_feature_renorm)
        recon_image = prediction + recon_res
        clipped_recon_image = recon_image.clamp(0., 1.)

        return clipped_recon_image, recon_image

    def forward(self, input_image, referframe, quant_noise_feature=None, quant_noise_z=None, quant_noise_mv=None):
        estmv = self.opticFlow(input_image, referframe)
        mvfeature = self.mvEncoder(estmv)
        if self.training:
            quant_mv = mvfeature + quant_noise_mv
        else:
            quant_mv = torch.round(mvfeature)
        quant_mv_upsample = self.mvDecoder(quant_mv)

        prediction, warpframe = self.motioncompensation(referframe, quant_mv_upsample)

        input_residual = input_image - prediction

        feature = self.resEncoder(input_residual)
        batch_size = feature.size()[0]

        z = self.respriorEncoder(feature)

        if self.training:
            compressed_z = z + quant_noise_z
        else:
            compressed_z = torch.round(z)

        recon_sigma = self.respriorDecoder(compressed_z)

        feature_renorm = feature

        if self.training:
            compressed_feature_renorm = feature_renorm + quant_noise_feature
        else:
            compressed_feature_renorm = torch.round(feature_renorm)

        recon_res = self.resDecoder(compressed_feature_renorm)
        recon_image = prediction + recon_res

        clipped_recon_image = recon_image.clamp(0., 1.)


        # distortion
        mse_loss = torch.mean((recon_image - input_image).pow(2))

        # psnr = tf.cond(
        #     tf.equal(mse_loss, 0), lambda: tf.constant(100, dtype=tf.float32),
        #     lambda: 10 * (tf.log(1 * 1 / mse_loss) / np.log(10)))

        warploss = torch.mean((warpframe - input_image).pow(2))
        interloss = torch.mean((prediction - input_image).pow(2))
        

        # bit per pixel

        def feature_probs_based_sigma(feature, sigma):
            
            def getrealbitsg(x, gaussian):
                # print("NIPS18noc : mn : ", torch.min(x), " - mx : ", torch.max(x), " range : ", self.mxrange)
                cdfs = []
                x = x + self.mxrange
                n,c,h,w = x.shape
                for i in range(-self.mxrange, self.mxrange):
                    cdfs.append(gaussian.cdf(i - 0.5).view(n,c,h,w,1))
                cdfs = torch.cat(cdfs, 4).cpu().detach()
                
                byte_stream = torchac.encode_float_cdf(cdfs, x.cpu().detach().to(torch.int16), check_input_bounds=True)

                real_bits = torch.from_numpy(np.array([len(byte_stream) * 8])).float()#.cuda()

                sym_out = torchac.decode_float_cdf(cdfs, byte_stream)

                return sym_out - self.mxrange, real_bits


            mu = torch.zeros_like(sigma)
            sigma = sigma.clamp(1e-5, 1e10)
            gaussian = torch.distributions.laplace.Laplace(mu, sigma)
            probs = gaussian.cdf(feature + 0.5) - gaussian.cdf(feature - 0.5)
            total_bits = torch.sum(torch.clamp(-1.0 * torch.log(probs + 1e-5) / math.log(2.0), 0, 50))
            
            if self.calrealbits and not self.training:
                decodedx, real_bits = getrealbitsg(feature, gaussian)
                total_bits = real_bits

            return total_bits, probs

        def iclr18_estrate_bits_z(z):
            
            def getrealbits(x):
                cdfs = []
                x = x + self.mxrange
                n,c,h,w = x.shape
                for i in range(-self.mxrange, self.mxrange):
                    cdfs.append(self.bitEstimator_z(i - 0.5).view(1, c, 1, 1, 1).repeat(1, 1, h, w, 1))
                cdfs = torch.cat(cdfs, 4).cpu().detach()
                byte_stream = torchac.encode_float_cdf(cdfs, x.cpu().detach().to(torch.int16), check_input_bounds=True)

                real_bits = torch.sum(torch.from_numpy(np.array([len(byte_stream) * 8])).float())#.cuda())

                sym_out = torchac.decode_float_cdf(cdfs, byte_stream)

                return sym_out - self.mxrange, real_bits

            prob = self.bitEstimator_z(z + 0.5) - self.bitEstimator_z(z - 0.5)
            total_bits = torch.sum(torch.clamp(-1.0 * torch.log(prob + 1e-5) / math.log(2.0), 0, 50))


            if self.calrealbits and not self.training:
                decodedx, real_bits = getrealbits(z)
                total_bits = real_bits

            return total_bits, prob

        def iclr18_estrate_bits_mv(mv):

            def getrealbits(x):
                cdfs = []
                x = x + self.mxrange
                n,c,h,w = x.shape
                for i in range(-self.mxrange, self.mxrange):
                    cdfs.append(self.bitEstimator_mv(i - 0.5).view(1, c, 1, 1, 1).repeat(1, 1, h, w, 1))
                cdfs = torch.cat(cdfs, 4).cpu().detach()
                byte_stream = torchac.encode_float_cdf(cdfs, x.cpu().detach().to(torch.int16), check_input_bounds=True)

                real_bits = torch.sum(torch.from_numpy(np.array([len(byte_stream) * 8])).float())#.cuda())

                sym_out = torchac.decode_float_cdf(cdfs, byte_stream)
                return sym_out - self.mxrange, real_bits

            prob = self.bitEstimator_mv(mv + 0.5) - self.bitEstimator_mv(mv - 0.5)
            total_bits = torch.sum(torch.clamp(-1.0 * torch.log(prob + 1e-5) / math.log(2.0), 0, 50))


            if self.calrealbits and not self.training:
                decodedx, real_bits = getrealbits(mv)
                total_bits = real_bits

            return total_bits, prob

        total_bits_feature, _ = feature_probs_based_sigma(compressed_feature_renorm, recon_sigma)
        # entropy_context = entropy_context_from_sigma(compressed_feature_renorm, recon_sigma)
        total_bits_z, _ = iclr18_estrate_bits_z(compressed_z)
        total_bits_mv, _ = iclr18_estrate_bits_mv(quant_mv)

        im_shape = input_image.size()

        bpp_feature = total_bits_feature / (batch_size * im_shape[2] * im_shape[3])
        bpp_z = total_bits_z / (batch_size * im_shape[2] * im_shape[3])
        bpp_mv = total_bits_mv / (batch_size * im_shape[2] * im_shape[3])
        bpp = bpp_feature + bpp_z + bpp_mv
        
        return clipped_recon_image, mse_loss, warploss, interloss, bpp_feature, bpp_z, bpp_mv, bpp

    def forward_v2(self, input_image, referframe, quant_noise_feature=None, quant_noise_z=None, quant_noise_mv=None):
        estmv = self.opticFlow(input_image, referframe)
        mvfeature = self.mvEncoder(estmv)
        if self.training:
            quant_mv = mvfeature + quant_noise_mv
        else:
            quant_mv = torch.round(mvfeature)
        
        quant_mv = torch.clamp(quant_mv, min=-31, max=31)
        quant_mv = (2 ** 0.5) * torch.randn_like(quant_mv)

        quant_mv_upsample = self.mvDecoder(quant_mv)

        prediction, warpframe = self.motioncompensation(referframe, quant_mv_upsample)

        input_residual = input_image - prediction

        feature = self.resEncoder(input_residual)
        batch_size = feature.size()[0]

        z = self.respriorEncoder(feature)

        if self.training:
            compressed_z = z + quant_noise_z
        else:
            compressed_z = torch.round(z)

        recon_sigma = self.respriorDecoder(compressed_z)

        feature_renorm = feature

        if self.training:
            compressed_feature_renorm = feature_renorm + quant_noise_feature
        else:
            compressed_feature_renorm = torch.round(feature_renorm)
        
        compressed_feature_renorm = torch.clamp(compressed_feature_renorm, min=-31, max=31)
        compressed_feature_renorm = (2 ** 0.5) * torch.randn_like(compressed_feature_renorm)

        recon_res = self.resDecoder(compressed_feature_renorm)
        recon_image = prediction + recon_res

        clipped_recon_image = recon_image.clamp(0., 1.)


        # distortion
        mse_loss = torch.mean((recon_image - input_image).pow(2))

        # psnr = tf.cond(
        #     tf.equal(mse_loss, 0), lambda: tf.constant(100, dtype=tf.float32),
        #     lambda: 10 * (tf.log(1 * 1 / mse_loss) / np.log(10)))

        warploss = torch.mean((warpframe - input_image).pow(2))
        interloss = torch.mean((prediction - input_image).pow(2))
        

        # bit per pixel

        def feature_probs_based_sigma(feature, sigma):
            
            def getrealbitsg(x, gaussian):
                # print("NIPS18noc : mn : ", torch.min(x), " - mx : ", torch.max(x), " range : ", self.mxrange)
                cdfs = []
                x = x + self.mxrange
                n,c,h,w = x.shape
                for i in range(-self.mxrange, self.mxrange):
                    cdfs.append(gaussian.cdf(i - 0.5).view(n,c,h,w,1))
                cdfs = torch.cat(cdfs, 4).cpu().detach()
                
                byte_stream = torchac.encode_float_cdf(cdfs, x.cpu().detach().to(torch.int16), check_input_bounds=True)

                real_bits = torch.from_numpy(np.array([len(byte_stream) * 8])).float()#.cuda()

                sym_out = torchac.decode_float_cdf(cdfs, byte_stream)

                return sym_out - self.mxrange, real_bits


            mu = torch.zeros_like(sigma)
            sigma = sigma.clamp(1e-5, 1e10)
            gaussian = torch.distributions.laplace.Laplace(mu, sigma)
            probs = gaussian.cdf(feature + 0.5) - gaussian.cdf(feature - 0.5)
            total_bits = torch.sum(torch.clamp(-1.0 * torch.log(probs + 1e-5) / math.log(2.0), 0, 50))
            
            if self.calrealbits and not self.training:
                decodedx, real_bits = getrealbitsg(feature, gaussian)
                total_bits = real_bits

            return total_bits, probs

        def iclr18_estrate_bits_z(z):
            
            def getrealbits(x):
                cdfs = []
                x = x + self.mxrange
                n,c,h,w = x.shape
                for i in range(-self.mxrange, self.mxrange):
                    cdfs.append(self.bitEstimator_z(i - 0.5).view(1, c, 1, 1, 1).repeat(1, 1, h, w, 1))
                cdfs = torch.cat(cdfs, 4).cpu().detach()
                byte_stream = torchac.encode_float_cdf(cdfs, x.cpu().detach().to(torch.int16), check_input_bounds=True)

                real_bits = torch.sum(torch.from_numpy(np.array([len(byte_stream) * 8])).float())#.cuda())

                sym_out = torchac.decode_float_cdf(cdfs, byte_stream)

                return sym_out - self.mxrange, real_bits

            prob = self.bitEstimator_z(z + 0.5) - self.bitEstimator_z(z - 0.5)
            total_bits = torch.sum(torch.clamp(-1.0 * torch.log(prob + 1e-5) / math.log(2.0), 0, 50))


            if self.calrealbits and not self.training:
                decodedx, real_bits = getrealbits(z)
                total_bits = real_bits

            return total_bits, prob

        def iclr18_estrate_bits_mv(mv):

            def getrealbits(x):
                cdfs = []
                x = x + self.mxrange
                n,c,h,w = x.shape
                for i in range(-self.mxrange, self.mxrange):
                    cdfs.append(self.bitEstimator_mv(i - 0.5).view(1, c, 1, 1, 1).repeat(1, 1, h, w, 1))
                cdfs = torch.cat(cdfs, 4).cpu().detach()
                byte_stream = torchac.encode_float_cdf(cdfs, x.cpu().detach().to(torch.int16), check_input_bounds=True)

                real_bits = torch.sum(torch.from_numpy(np.array([len(byte_stream) * 8])).float())#.cuda())

                sym_out = torchac.decode_float_cdf(cdfs, byte_stream)
                return sym_out - self.mxrange, real_bits

            prob = self.bitEstimator_mv(mv + 0.5) - self.bitEstimator_mv(mv - 0.5)
            total_bits = torch.sum(torch.clamp(-1.0 * torch.log(prob + 1e-5) / math.log(2.0), 0, 50))


            if self.calrealbits and not self.training:
                decodedx, real_bits = getrealbits(mv)
                total_bits = real_bits

            return total_bits, prob

        total_bits_feature, _ = feature_probs_based_sigma(compressed_feature_renorm, recon_sigma)
        # entropy_context = entropy_context_from_sigma(compressed_feature_renorm, recon_sigma)
        total_bits_z, _ = iclr18_estrate_bits_z(compressed_z)
        total_bits_mv, _ = iclr18_estrate_bits_mv(quant_mv)

        im_shape = input_image.size()

        bpp_feature = total_bits_feature / (batch_size * im_shape[2] * im_shape[3])
        bpp_z = total_bits_z / (batch_size * im_shape[2] * im_shape[3])
        bpp_mv = total_bits_mv / (batch_size * im_shape[2] * im_shape[3])
        bpp = bpp_feature + bpp_z + bpp_mv
        
        return clipped_recon_image, mse_loss, warploss, interloss, bpp_feature, bpp_z, bpp_mv, bpp
    