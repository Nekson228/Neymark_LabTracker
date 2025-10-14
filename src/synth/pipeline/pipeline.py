import json
import random
import subprocess
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from uuid import uuid4

import fitz
from jinja2 import Template
from tqdm.auto import tqdm
from PIL import Image

from src.synth.generator import generate_report
from src.synth.pipeline.augmentation import create_augmentations

N = 10_000  # Number of samples to generate
MAX_WORKERS = 8

LATEX_PATH = Path("src/synth/latex")
TEMPLATE_PATH = LATEX_PATH / "template.tex"
DATASET_PATH = Path("src/synth/data")
IMAGES_PATH = DATASET_PATH / "images"


def generate_pdf_instance(template_str: str, idx: int) -> dict:
    """
    Generate a single PDF, render it as image, apply augmentation.
    Returns metadata + text + paths.
    """
    result_path = LATEX_PATH / f"filled_template_{idx}.tex"
    pdf_path = LATEX_PATH / f"filled_template_{idx}.pdf"

    template = Template(template_str)
    report = generate_report()

    with open(result_path, "w") as f:
        f.write(template.render(**report.to_dict()))

    # Run XeLaTeX
    subprocess.run(
        ["xelatex", f"--output-directory={LATEX_PATH}", result_path],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    # Extract text
    with fitz.open(pdf_path) as doc:
        if len(doc) > 1:
            raise ValueError("Generated PDF has more than one page.")
        page = doc[0]
        text = str(page.get_text()).replace("\n", " ")

        mat = fitz.Matrix(3, 3)
        pix = page.get_pixmap(matrix=mat)

    sample_path = IMAGES_PATH / f"{idx:05d}.png"
    pix.save(sample_path)

    # Augment image
    augmentations = create_augmentations()
    aug = random.choice(augmentations)
    input_image = Image.open(sample_path).convert("RGB")
    augmented_image = aug["transform"](input_image)

    aug_sample_path = IMAGES_PATH / f"{idx:05d}_aug.png"
    augmented_image.save(aug_sample_path)

    return {
        **report.get_metadata(),
        "text": text,
        "image_path": str(sample_path),
        "aug_image_path": str(aug_sample_path),
        "aug_name": aug["name"],
    }


def main():
    DATASET_PATH.mkdir(parents=True, exist_ok=True)
    IMAGES_PATH.mkdir(parents=True, exist_ok=True)

    with open(TEMPLATE_PATH, "r") as f:
        template_str = f.read()

    results = []

    with ProcessPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = [executor.submit(generate_pdf_instance, template_str, i) for i in range(N)]

        for future in tqdm(as_completed(futures), total=N, desc="Generating dataset"):
            try:
                results.append(future.result())
            except ValueError:
                continue  # Skip invalid PDFs
            except Exception as e:
                print(f"Error: {e}")

    with open(DATASET_PATH / "data.json", "w") as f:
        json.dump(results, f, ensure_ascii=False, indent=4)


if __name__ == "__main__":
    main()