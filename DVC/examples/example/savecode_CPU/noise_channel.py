import numpy as np
import torch

def noise_channel(arr1, arr2, arr3, p1, p2, p3):
    def modify(a_inp, p):
        a = list(a_inp)
        for i in range(len(a)):
            rn = np.random.uniform(0, 1)
            if rn < p:
                a[i] = 0
        return bytes(a)
    return modify(arr1, p1), modify(arr2, p2), modify(arr3, p3)

def real_noise_channel(arr1, arr2, mean, variance):
    noise_1 = (variance ** 0.5) * torch.randn_like(arr1) + mean
    noise_2 = (variance ** 0.5) * torch.randn_like(arr2) + mean
    return arr1 + noise_1, arr2 + noise_2
