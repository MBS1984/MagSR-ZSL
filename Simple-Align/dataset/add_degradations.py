import os.path
import io
import zipfile
from PIL import Image
import torchvision.transforms as transforms
import numpy as np
import random
import cv2
from io import BytesIO

import cv2
import numpy as np
import os.path as osp
import os
def pdf2(sigma_matrix, grid):
    """Calculate PDF of the bivariate Gaussian distribution.

    Args:
        sigma_matrix (ndarray): with the shape (2, 2)
        grid (ndarray): generated by :func:`mesh_grid`,
            with the shape (K, K, 2), K is the kernel size.

    Returns:
        kernel (ndarrray): un-normalized kernel.
    """
    inverse_sigma = np.linalg.inv(sigma_matrix)
    kernel = np.exp(-0.5 * np.sum(np.dot(grid, inverse_sigma) * grid, 2))
    return kernel

def mesh_grid(kernel_size):
    """Generate the mesh grid, centering at zero.

    Args:
        kernel_size (int):

    Returns:
        xy (ndarray): with the shape (kernel_size, kernel_size, 2)
        xx (ndarray): with the shape (kernel_size, kernel_size)
        yy (ndarray): with the shape (kernel_size, kernel_size)
    """
    ax = np.arange(-kernel_size // 2 + 1., kernel_size // 2 + 1.)
    xx, yy = np.meshgrid(ax, ax)
    xy = np.hstack((xx.reshape((kernel_size * kernel_size, 1)), yy.reshape(kernel_size * kernel_size,
                                                                           1))).reshape(kernel_size, kernel_size, 2)
    return xy, xx, yy

def bivariate_Gaussian(kernel_size, sig_x, grid=None, isotropic=True):
    """Generate a bivariate isotropic or anisotropic Gaussian kernel.

    In the isotropic mode, only `sig_x` is used. `sig_y` and `theta` is ignored.

    Args:
        kernel_size (int):
        sig_x (float):
        sig_y (float):
        theta (float): Radian measurement.
        grid (ndarray, optional): generated by :func:`mesh_grid`,
            with the shape (K, K, 2), K is the kernel size. Default: None
        isotropic (bool):

    Returns:
        kernel (ndarray): normalized kernel.
    """
    if grid is None:
        grid, _, _ = mesh_grid(kernel_size)
    if isotropic:
        sigma_matrix = np.array([[sig_x**2, 0], [0, sig_x**2]])
    else:
        sigma_matrix = sigma_matrix2(sig_x, sig_y, theta)
    kernel = pdf2(sigma_matrix, grid)
    kernel = kernel / np.sum(kernel)
    return kernel

def pil_to_np(img_PIL):
    '''Converts image in PIL format to np.array.
    From W x H x C [0...255] to C x W x H [0..1]
    '''
    ar = np.array(img_PIL)

    if len(ar.shape) == 3:
        ar = ar.transpose(2, 0, 1)
    else:
        ar = ar[None, ...]

    return ar.astype(np.float32) / 255.

def np_to_pil(img_np):
    '''Converts image in np.array format to PIL image.
    From C x W x H [0..1] to  W x H x C [0...255]
    '''
    ar = np.clip(img_np * 255, 0, 255).astype(np.uint8)

    if img_np.shape[0] == 1:
        ar = ar[0]
    else:
        ar = ar.transpose(1, 2, 0)

    return Image.fromarray(ar)

def synthesize_salt_pepper(image,amount,salt_vs_pepper):

    ## Give PIL, return the noisy PIL

    img_pil=pil_to_np(image)

    out = img_pil.copy()
    p = amount
    q = salt_vs_pepper
    flipped = np.random.choice([True, False], size=img_pil.shape,
                               p=[p, 1 - p])
    salted = np.random.choice([True, False], size=img_pil.shape,
                              p=[q, 1 - q])
    peppered = ~salted
    out[flipped & salted] = 1
    out[flipped & peppered] = 0.
    noisy = np.clip(out, 0, 1).astype(np.float32)


    return np_to_pil(noisy)

def synthesize_gaussian(image,std_l,std_r):

    ## Give PIL, return the noisy PIL

    img_pil=pil_to_np(image)

    mean=0
    std=random.uniform(std_l/255.,std_r/255.)
    gauss=np.random.normal(loc=mean,scale=std,size=img_pil.shape)
    noisy=img_pil+gauss
    noisy=np.clip(noisy,0,1).astype(np.float32)

    return np_to_pil(noisy)

def synthesize_speckle(image,std_l,std_r):

    ## Give PIL, return the noisy PIL

    img_pil=pil_to_np(image)

    mean=0
    std=random.uniform(std_l/255.,std_r/255.)
    gauss=np.random.normal(loc=mean,scale=std,size=img_pil.shape)
    noisy=img_pil+gauss*img_pil
    noisy=np.clip(noisy,0,1).astype(np.float32)

    return np_to_pil(noisy)

def synthesize_low_resolution(img):
    w,h=img.size

    new_w=random.randint(int(w/2),w)
    new_h=random.randint(int(h/2),h)

    img=img.resize((new_w,new_h),Image.BICUBIC)

    if random.uniform(0,1)<0.5:
        img=img.resize((w,h),Image.NEAREST)
    else:
        img = img.resize((w, h), Image.BILINEAR)

    return img

def blur_image_v2(img,num):

    x=np.array(img)
    blur=cv2.GaussianBlur(x,(21,21),num)

    return Image.fromarray(blur.astype(np.uint8))

def irregular_hole_synthesize(img,mask):

    img_np=np.array(img).astype('uint8')
    mask_np=np.array(mask).astype('uint8')
    mask_np=mask_np/255
    img_new=img_np*(1-mask_np)+mask_np*255


    hole_img=Image.fromarray(img_new.astype('uint8')).convert("RGB")

    return hole_img,mask.convert("L")

def add_blur(img_GT):
    x = np.array(img_GT)
    blur = cv2.GaussianBlur(x, (21, 21), 2)
    return Image.fromarray(blur.astype(np.uint8))

def add_noise(min,max,img_GT):

    img_GT_noise = synthesize_gaussian(img_GT, min, max)
    
    return img_GT_noise

def donw_sample_bicubic(img):

    w, h = img.size

    new_w = int(w / 4)
    new_h = int(h / 4)

    img = img.resize((new_w, new_h), Image.BICUBIC)

    return img

def donw_sample_nearest(img):

    w, h = img.size

    new_w = int(w / 4)
    new_h = int(h / 4)

    img = img.resize((new_w, new_h), Image.NEAREST)

    return img

def donw_sample_bilinear(img):

    w, h = img.size

    new_w = int(w / 4)
    new_h = int(h / 4)

    img = img.resize((new_w, new_h), Image.BILINEAR)

    return img

def convertToJpeg(im,quality):
    with BytesIO() as f:
        im.save(f, format='JPEG',quality=quality)
        f.seek(0)
        return Image.open(f).convert('RGB')

def convertToJpeg2000(im,quality):
    with BytesIO() as f:
        im.save(f, format='JPEG2000',quality=quality)
        f.seek(0)
        return Image.open(f).convert('RGB')

def check_dir(dir):
    if os.path.exists(dir):
        pass
    else:
        os.makedirs(dir)



if __name__ == '__main__':
    
    for i in ['Set5','Set14','B100','Manga109','Urban100']:

        GT_folder = os.path.join('C:\\Users\\mbava\\Downloads\\Simple-Align-main\\dataset\\benchmark', i, 'HR', 'GTmod12')
        save_LR_folder = os.path.join('C:\\Users\\mbava\\Downloads\\Simple-Align-main\\dataset\\benchmark', i, 'LR_degra')

        img_GT_list = sorted(os.listdir(GT_folder))

        for path_GT in img_GT_list:
            print(path_GT)

            img_GT = Image.open(os.path.join(GT_folder,path_GT))

            # only bicubic
            img_copy = img_GT.copy()
            img_LR=donw_sample_bicubic(img_copy)
            save_dir=os.path.join(save_LR_folder,'bicubic')
            check_dir(save_dir)
            img_LR.save(os.path.join(save_dir,os.path.basename(path_GT)))

            #blur2+bicubic
            # blur
            img_copy = img_GT.copy()
            img_blured = blur_image_v2(img_copy,2)
            # only downsample
            img_LR = donw_sample_bicubic(img_blured)
            save_dir = os.path.join(save_LR_folder, 'blur2_bicubic')
            check_dir(save_dir)
            img_LR.save(os.path.join(save_dir,os.path.basename(path_GT)))

            # bicubic+noise20
            #down
            img_copy = img_GT.copy()
            img_LR = donw_sample_bicubic(img_copy)
            #noise
            img_noise=add_noise(20,20,img_LR)
            save_dir = os.path.join(save_LR_folder, 'bicubic_noise20')
            check_dir(save_dir)
            img_noise.save(os.path.join(save_dir,os.path.basename(path_GT)))

            # bicubic+jepg50
            #down
            img_copy = img_GT.copy()
            img_LR = donw_sample_bicubic(img_copy)
            # JEPG50
            img_jepg=convertToJpeg(img_LR,50)
            save_dir = os.path.join(save_LR_folder, 'bicubic_jepg50')
            check_dir(save_dir)
            img_jepg.save(os.path.join(save_dir,os.path.basename(path_GT)))


            # blur2+bicubic+noise20
            # blur
            img_copy = img_GT.copy()
            img_blured = blur_image_v2(img_copy, 2)
            # downsample
            img_LR = donw_sample_bicubic(img_blured)
            # noise20
            img_noise = add_noise(20, 20, img_LR)
            save_dir = os.path.join(save_LR_folder, 'blur2_bicubic_noise20')
            check_dir(save_dir)
            img_noise.save(os.path.join(save_dir, os.path.basename(path_GT)))

            # blur2+bicubic+jepg50
            # blur
            img_copy = img_GT.copy()
            img_blured = blur_image_v2(img_copy, 2)
            # downsample
            img_LR = donw_sample_bicubic(img_blured)
            # JEPG50
            img_jepg = convertToJpeg(img_LR, 50)
            save_dir = os.path.join(save_LR_folder, 'blur2_bicubic_jepg50')
            check_dir(save_dir)
            img_jepg.save(os.path.join(save_dir, os.path.basename(path_GT)))


            # bicubic+noise20+jepg50
            # down
            img_copy = img_GT.copy()
            img_LR = donw_sample_bicubic(img_copy)
            # noise
            img_noise = add_noise(20, 20, img_LR)
            # JEPG50
            img_jepg = convertToJpeg(img_noise, 50)
            save_dir = os.path.join(save_LR_folder, 'bicubic_noise20_jepg50')
            check_dir(save_dir)
            img_jepg.save(os.path.join(save_dir, os.path.basename(path_GT)))

            # blur2+bicubic+noise20+jepg50
            # blur
            img_copy = img_GT.copy()
            img_blured = blur_image_v2(img_copy, 2)
            # downsample
            img_LR = donw_sample_bicubic(img_blured)
            # noise20
            img_noise = add_noise(20, 20, img_LR)
            # JEPG50
            img_jepg = convertToJpeg(img_noise, 50)
            save_dir = os.path.join(save_LR_folder, 'blur2_bicubic_noise20_jepg50')
            check_dir(save_dir)
            img_jepg.save(os.path.join(save_dir, os.path.basename(path_GT)))
