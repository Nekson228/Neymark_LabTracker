import os
import pandas as pd
import random
import numpy as np
from PIL import Image, ImageDraw
import torchvision.transforms as transforms
import cv2

def create_augmentations():
    augmentations = [
        {
            'name': 'RandomRotation',
            'transform': transforms.RandomRotation(degrees=(-10, 10)),
        },
        {
            'name': 'GaussianBlur',
            'transform': lambda img: apply_random_gaussian_blur(img),
        },
        {
            'name': 'ImageDilation',
            'transform': lambda img: apply_dilation(img),
        },
        {
            'name': 'Downscaling',
            'transform': lambda img: apply_downscaling(img),
        },
        {
            'name': 'RandomPerspective',
            'transform': lambda img: apply_random_perspective(img),
        },
        {
            'name': 'ColorJitter',
            'transform': lambda img: apply_color_jitter(img),
        }
    ]
    return augmentations

def apply_random_gaussian_blur(image):
    """Применяет GaussianBlur с kernel_size 3-11 и sigma до 10.0"""
    kernel_size = random.choice([3, 5, 7, 9, 11])
    sigma = random.uniform(1, 5)

    blur_transform = transforms.GaussianBlur(kernel_size=kernel_size, sigma=sigma)
    return blur_transform(image)

def apply_dilation(image):
    """Применяет дилатацию к изображению"""
    # Конвертируем PIL в numpy array для OpenCV
    img_array = np.array(image)

    # Создаем случайное ядро для дилатации
    kernel_size = random.randint(2, 3)
    kernel = np.ones((kernel_size, kernel_size), np.uint8)

    # Применяем дилатацию
    if len(img_array.shape) == 3:  # Color image
        dilated = cv2.dilate(img_array, kernel, iterations=1)
    else:  # Grayscale
        dilated = cv2.dilate(img_array, kernel, iterations=1)

    return Image.fromarray(dilated)

def apply_downscaling(image):
    """Применяет уменьшение разрешения с последующим увеличением"""
    width, height = image.size

    # Случайный коэффициент уменьшения (от 0.3 до 0.5 от исходного размера)
    scale_factor = random.uniform(0.3, 0.5)
    new_width = int(width * scale_factor)
    new_height = int(height * scale_factor)

    # Уменьшаем изображение
    downscaled = image.resize((new_width, new_height), Image.LANCZOS)

    # Увеличиваем обратно до исходного размера
    upscaled = downscaled.resize((width, height), Image.LANCZOS)

    return upscaled

def apply_random_perspective(image):
    """Применяет случайные перспективные искажения"""
    # Случайный уровень искажения (от слабого до среднего)
    distortion_scale = random.uniform(0.2, 0.6)

    perspective_transform = transforms.RandomPerspective(
        distortion_scale=distortion_scale,
        p=1.0,  # Всегда применяем
        interpolation=transforms.InterpolationMode.BILINEAR
    )

    return perspective_transform(image)

def apply_color_jitter(image):
    """Применяет случайные изменения цветовых характеристик"""
    # Случайные параметры для ColorJitter
    brightness = random.uniform(0.7, 1.3)  # Изменение яркости
    contrast = random.uniform(0.7, 1.3)    # Изменение контраста
    saturation = random.uniform(0.7, 1.3)  # Изменение насыщенности
    hue = random.uniform(-0.3, 0.3)        # Изменение оттенка

    color_jitter_transform = transforms.ColorJitter(
        brightness=(brightness, brightness),
        contrast=(contrast, contrast),
        saturation=(saturation, saturation),
        hue=(hue, hue)
    )

    return color_jitter_transform(image)
