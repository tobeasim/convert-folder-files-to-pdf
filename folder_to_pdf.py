import os
import sys
import argparse
from fpdf import FPDF
from pathlib import Path
from tqdm import tqdm

def install(package):
    """
    Helper function to install packages if they're missing.
    """
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", package])

# Ensure required packages are installed
try:
    from fpdf import FPDF
except ImportError:
    print("fpdf not found. Installing...")
    install('fpdf2')
    from fpdf import FPDF

try:
    from tqdm import tqdm
except ImportError:
    print("tqdm not found. Installing...")
    install('tqdm')
    from tqdm import tqdm

class PDF(FPDF):
    def __init__(self, font_path='DejaVu Sans Mono for Powerline.ttf'):
        super().__init__()
        self.set_auto_page_break(auto=True, margin=15)
        self.add_page()

        # Add the Unicode-capable TrueType font
        if not os.path.isfile(font_path):
            print(f"Font file '{font_path}' not found. Please ensure the font is in the script directory or provide the correct path.")
            sys.exit(1)

        self.add_font('DejaVu', '', font_path, uni=True)
        self.set_font('DejaVu', size=10)

    def add_text(self, text):
        """
        Adds multi-line text to the PDF.
        """
        # Split text into lines to handle wrapping
        for line in text.split('\n'):
            self.multi_cell(0, 5, line)
            self.ln()

def is_binary(file_path):
    """
    Check if a file is binary by looking for null bytes.
    """
    try:
        with open(file_path, 'rb') as f:
            chunk = f.read(1024)
            if b'\0' in chunk:
                return True
    except:
        pass
    return False

def process_file(file_path, base_folder, output_folder, font_path='DejaVu Sans Mono for Powerline.ttf'):
    """
    Processes a single file: reads its content and creates a PDF.
    """
    relative_path = os.path.relpath(file_path, base_folder)
    display_path = relative_path.replace(os.sep, ' > ')
    pdf = PDF(font_path)

    # Add the file location as the first line
    pdf.add_text(f"File Location: {base_folder} > {display_path}\n\n")

    # Determine if the file is binary
    if is_binary(file_path):
        pdf.add_text("**Binary File: Content not displayed**")
    else:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            pdf.add_text(content)
        except UnicodeDecodeError:
            # If UTF-8 fails, try with 'utf-8' with replacement characters
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
            pdf.add_text(content)
        except Exception as e:
            pdf.add_text(f"**Error reading file: {e}**")

    # Define the output PDF path
    relative_pdf_path = Path(relative_path).with_suffix('.pdf')
    output_pdf_path = Path(output_folder) / relative_pdf_path

    # Ensure the output directory exists
    output_pdf_path.parent.mkdir(parents=True, exist_ok=True)

    # Save the PDF
    try:
        pdf.output(str(output_pdf_path))
    except Exception as e:
        print(f"Failed to write PDF for {file_path}: {e}")

def main():
    parser = argparse.ArgumentParser(description="Convert files in a folder to PDFs with file paths.")
    parser.add_argument("input_folder", help="Path to the input folder (e.g., app_folder)")
    parser.add_argument("output_folder", help="Path to the output folder where PDFs will be saved")
    parser.add_argument("--font", help="Path to the TTF font file to use for PDFs", default='DejaVu Sans Mono for Powerline.ttf')
    args = parser.parse_args()

    input_folder = args.input_folder
    output_folder = args.output_folder
    font_path = args.font

    if not os.path.isdir(input_folder):
        print(f"Input folder '{input_folder}' does not exist or is not a directory.")
        sys.exit(1)

    if not os.path.isfile(font_path):
        print(f"Font file '{font_path}' not found. Please provide a valid TTF font file.")
        sys.exit(1)

    # Collect all files
    all_files = []
    for root, dirs, files in os.walk(input_folder):
        for file in files:
            all_files.append(os.path.join(root, file))

    print(f"Found {len(all_files)} files to process.")

    # Process files with a progress bar
    for file_path in tqdm(all_files, desc="Processing files"):
        process_file(file_path, input_folder, output_folder, font_path)

    print(f"PDFs have been saved to '{output_folder}'.")

if __name__ == "__main__":
    main()
