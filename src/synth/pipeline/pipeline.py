import json
import random
import subprocess

from pathlib import Path

import fitz
from jinja2 import Template
from tqdm.auto import tqdm
from PIL import Image

from src.synth.generator import generate_report
from src.synth.pipeline.augmentation import create_augmentations

N = 100  # Number of samples to generate

LATEX_PATH = Path("src/synth/latex")
TEMPLATE_PATH = LATEX_PATH / "template.tex"
RESULT_PATH = LATEX_PATH / "filled_template.tex"
PDF_PATH = LATEX_PATH / "filled_template.pdf"

DATASET_PATH = Path("src/synth/data")
IMAGES_PATH = DATASET_PATH / "images"


def generate_pdf(template_path: Path, result_path: Path) -> tuple[dict, str]:
    with open(template_path, "r") as template_file:
        template = Template(template_file.read())

    report = generate_report()

    with open(result_path, "w") as result_file:
        result_file.write(template.render(**report.to_dict()))

    subprocess.run(["xelatex", f"--output-directory={LATEX_PATH}", result_path], check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                   )

    with fitz.open(PDF_PATH) as doc:
        if len(doc) > 1:
            raise ValueError("Generated PDF has more than one page.")
        page = doc[0]
        text = str(page.get_text()).replace('\n', ' ')

    return report.get_metadata(), text

def pdf_to_image(source_pdf: Path, output_image: Path, zoom: int = 3) -> None:
    doc = fitz.open(source_pdf)
    page = doc[0]
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat)
    pix.save(output_image)


def create_augmentation(input_image_path: str, output_image_path: str) -> str:
    augmentations = create_augmentations()
    aug = random.choice(augmentations)
    input_image = Image.open(input_image_path).convert('RGB')
    augmented_image = aug['transform'](input_image)
    augmented_image.save(output_image_path)

    return aug['name']


def main():
    DATASET_PATH.mkdir(parents=True, exist_ok=True)
    IMAGES_PATH.mkdir(parents=True, exist_ok=True)

    all_data = []
    for i in tqdm(range(N)):
        try:
            metadata, text = generate_pdf(TEMPLATE_PATH, RESULT_PATH)
        except ValueError:
            print("Regenerating due to multi-page PDF...")
            metadata, text = generate_pdf(TEMPLATE_PATH, RESULT_PATH)
        sample_path = IMAGES_PATH / f"{i:05d}.png"
        aug_sample_path = IMAGES_PATH / f"{i:05d}_aug.png"
        pdf_to_image(PDF_PATH, sample_path)
        aug_name = create_augmentation(str(sample_path), str(aug_sample_path))

        all_data.append({**metadata, 
                         "text": text, "image_path": str(sample_path), 
                         "aug_image_path": str(aug_sample_path), "aug_name": aug_name})


    with open(DATASET_PATH / "data.json", "w") as json_file:
        json.dump(all_data, json_file, ensure_ascii=False, indent=4)


if __name__ == "__main__":
    main()