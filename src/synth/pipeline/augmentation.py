import os
import pandas as pd
import random
import numpy as np
from PIL import Image, ImageDraw
import torchvision.transforms as transforms
import cv2

def create_augmentations():
    """Создаем список аугментаций согласно указаниям"""
    augmentations = [
        {
            'name': 'RandomRotation',
            'transform': transforms.RandomRotation(degrees=(-10, 10)),
            'description': 'Случайный поворот от -10 до 10 градусов'
        },
        {
            'name': 'GaussianBlur',
            'transform': lambda img: apply_random_gaussian_blur(img),
            'description': 'Случайное размытие по Гауссу с kernel_size 3-7 и sigma до 1.3'
        },
        {
            'name': 'ImageDilation',
            'transform': lambda img: apply_dilation(img),
            'description': 'Дилатация (расширение) изображения'
        },
        {
            'name': 'Downscaling',
            'transform': lambda img: apply_downscaling(img),
            'description': 'Уменьшение разрешения с последующим увеличением'
        },
        {
            'name': 'RandomPerspective',
            'transform': lambda img: apply_random_perspective(img),
            'description': 'Случайные перспективные искажения'
        },
        {
            'name': 'ColorJitter',
            'transform': lambda img: apply_color_jitter(img),
            'description': 'Случайные изменения цветовых характеристик'
        }
    ]
    return augmentations

def apply_random_gaussian_blur(image):
    """Применяет GaussianBlur с kernel_size 3-15 и sigma до 10.0"""
    kernel_size = random.choice([3, 5, 7, 9, 11, 13, 15])
    sigma = random.uniform(1, 10)

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
    distortion_scale = random.uniform(0.2, 0.5)

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
    hue = random.uniform(-0.1, 0.1)        # Изменение оттенка

    color_jitter_transform = transforms.ColorJitter(
        brightness=(brightness, brightness),
        contrast=(contrast, contrast),
        saturation=(saturation, saturation),
        hue=(hue, hue)
    )

    return color_jitter_transform(image)

def augment_medical_reports(source_folder: str='medical_reports', output_folder: str='augmented_medical_reports'):
    """Основная функция для аугментации медицинских отчетов
    source_folder - папка с картинками в формате .png для аугментации
    output_folder - папка с результатами аугментации
    """


    os.makedirs(output_folder, exist_ok=True)

    # Получаем список изображений
    image_files = [f for f in os.listdir(source_folder) if f.endswith('.png')]

    if not image_files:
        print("В папке medical_reports не найдено PNG файлов!")
        return

    # Создаем аугментации
    augmentations = create_augmentations()

    # Метаданные
    metadata = []

    print(f"Начинаем обработку {len(image_files)} изображений...")
    print(f"Доступно {len(augmentations)} типов аугментаций")

    for i, img_file in enumerate(image_files):
        print(f"Обработка {i+1}/{len(image_files)}: {img_file}")

        try:
            # Загружаем изображение
            img_path = os.path.join(source_folder, img_file)
            image = Image.open(img_path).convert('RGB')

            # Выбираем случайную аугментацию (равная вероятность для каждого)
            aug = random.choice(augmentations)

            # Применяем преобразование
            augmented_image = aug['transform'](image)

            # Генерируем имена файлов
            base_name = os.path.splitext(img_file)[0]

            # Сохраняем аугментированное изображение
            aug_filename = f"{base_name}_{aug['name']}.png"
            aug_path = os.path.join(output_folder, aug_filename)
            augmented_image.save(aug_path)

            # Сохраняем исходное изображение (копия)
            orig_filename = f"{base_name}_original.png"
            orig_path = os.path.join(output_folder, orig_filename)
            image.save(orig_path)

            # Добавляем метаданные
            metadata.append({
                'original_file': orig_filename,
                'augmented_file': aug_filename,
                'source_file': img_file,
                'augmentation_type': aug['name'],
                'augmentation_description': aug['description'],
                'folder': output_folder
            })

        except Exception as e:
            print(f"Ошибка при обработке {img_file}: {str(e)}")
            continue

    # Сохраняем метаданные
    if metadata:
        df = pd.DataFrame(metadata)
        metadata_path = os.path.join(output_folder, 'augmentation_metadata.csv')
        df.to_csv(metadata_path, index=False, encoding='utf-8')

        print(f"\nАугментация завершена успешно!")
        print(f"Обработано изображений: {len(metadata)}")
        print(f"Создано файлов: {len(metadata) * 2}")
        print(f"Метаданные сохранены в: {metadata_path}")
        print(f"Аугментированные изображения в папке: {output_folder}")

        # Показываем статистику по типам аугментаций
        print("\nСтатистика примененных аугментаций:")
        aug_stats = df['augmentation_type'].value_counts()
        for aug_type, count in aug_stats.items():
            probability = count / len(metadata) * 100
            print(f"  {aug_type}: {count} изображений ({probability:.1f}%)")
    else:
        print("Не удалось обработать ни одного изображения!")

# Дополнительная функция для создания примера всех аугментаций на одном изображении
def create_augmentation_preview(source_folder: str='medical_reports', output_folder: str='augmented_medical_reports'):
    """Создает превью со всеми типами аугментаций на одном изображении
    source_folder - папка с картинками в формате .png для аугментации
    output_folder - папка с результатами аугментации
    """

    os.makedirs(output_folder, exist_ok=True)

    # Находим первое изображение для демонстрации
    image_files = [f for f in os.listdir(source_folder) if f.endswith('.png')]
    if not image_files:
        print("Нет изображений для создания превью!")
        return

    sample_image_path = os.path.join(source_folder, image_files[0])
    original_image = Image.open(sample_image_path).convert('RGB')

    augmentations = create_augmentations()

    # Создаем коллаж со всеми аугментациями
    preview_images = [original_image]
    preview_labels = ['Original']

    for aug in augmentations:
        try:
            augmented = aug['transform'](original_image.copy())
            preview_images.append(augmented)
            preview_labels.append(aug['name'])
        except Exception as e:
            print(f"Ошибка при создании превью для {aug['name']}: {e}")

    # Сохраняем превью
    base_name = os.path.splitext(image_files[0])[0]
    for img, label in zip(preview_images, preview_labels):
        preview_path = os.path.join(output_folder, f"{base_name}_{label}.png")
        img.save(preview_path)

    print(f"Превью аугментаций сохранено в папке: {output_folder}")

if __name__ == "__main__":
    augment_medical_reports(source_folder = 'medical_reports', output_folder = 'augmented_medical_reports')

    # Создаем превью (опционально)
    create_augmentation_preview(source_folder = 'medical_reports', output_folder = 'augmented_medical_reports')
