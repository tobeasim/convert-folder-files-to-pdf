# usage  python foo.py </app_folder> </output folder> --font "/Library/Fonts/Arial Unicode.ttf" --fontname Arial --generate-structure --merge
# change the font path to the path of the font you want to use

import os
import sys
import argparse
from fpdf import FPDF
from pathlib import Path
from tqdm import tqdm
import logging

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
    print("fpdf2 not found. Installing...")
    install('fpdf2')
    from fpdf import FPDF

try:
    from tqdm import tqdm
except ImportError:
    print("tqdm not found. Installing...")
    install('tqdm')
    from tqdm import tqdm

try:
    from PyPDF2 import PdfReader, PdfWriter
except ImportError:
    print("PyPDF2 not found. Installing...")
    install('PyPDF2')
    from PyPDF2 import PdfReader, PdfWriter

# Configure logging
logging.basicConfig(
    filename='pdf_conversion.log',
    level=logging.INFO,
    format='%(asctime)s:%(levelname)s:%(message)s'
)

# Configuration
# Define skip lists
SKIP_FOLDERS = ['.git', '__pycache__', 'node_modules', 'local_tiktoken_cache']  # Add folders you want to skip
SKIP_FILES = ['.dockerignore', 'README.md', 'generic.pdf', 'with_cabin.pdf','template_EN.pdf','modified_template.pdf','CALIBRI.ttf','CALIBRIB.ttf']    # Add files you want to skip
MAX_FILE_SIZE = 2 * 1024 * 1024  # Maximum file size in bytes (e.g., 5MB)

class PDF(FPDF):
    def __init__(self, font_path, font_name='CustomFont'):
        super().__init__()
        self.set_auto_page_break(auto=True, margin=15)
        self.add_page()

        # Add TrueType font with Unicode support
        if not os.path.isfile(font_path):
            logging.error(f"Font file '{font_path}' not found.")
            print(f"Font file '{font_path}' not found. Please ensure the font path is correct.")
            sys.exit(1)

        self.add_font(font_name, '', font_path, uni=True)
        self.set_font(font_name, size=10)

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

def process_file(file_path, base_folder, output_folder, font_path, font_name='CustomFont'):
    """
    Processes a single file: reads its content and creates a PDF.
    """
    relative_path = os.path.relpath(file_path, base_folder)
    display_path = relative_path.replace(os.sep, ' > ')
    pdf = PDF(font_path, font_name)

    # Add the file location as the first line
    pdf.add_text(f"File Location: {base_folder} > {display_path}\n\n")

    # Determine if the file is binary
    if is_binary(file_path):
        pdf.add_text("**Binary File: Content not displayed**")
        logging.info(f"Skipped binary file: {file_path}")
        return
    # Determine if the file exceeds the maximum size
    if os.path.getsize(file_path) > MAX_FILE_SIZE:
        pdf.add_text(f"**File skipped: Exceeds maximum size of {MAX_FILE_SIZE / (1024 * 1024)} MB**")
        logging.info(f"Skipped large file: {file_path}")
        return

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
        logging.error(f"Error reading file {file_path}: {e}")

    # Define the output PDF path
    relative_pdf_path = Path(relative_path).with_suffix('.pdf')
    output_pdf_path = Path(output_folder) / relative_pdf_path

    # Ensure the output directory exists
    output_pdf_path.parent.mkdir(parents=True, exist_ok=True)

    # Save the PDF
    try:
        pdf.output(str(output_pdf_path))
        logging.info(f"Successfully created PDF for {file_path}")
    except Exception as e:
        logging.error(f"Failed to write PDF for {file_path}: {e}")
        print(f"Failed to write PDF for {file_path}: {e}")

def generate_folder_structure_pdf(input_folder, output_folder, font_path, font_name='CustomFont'):
    """
    Generates a PDF that outlines the folder structure of the input_folder.
    """
    structure_pdf = PDF(font_path, font_name)

    # Add title
    structure_pdf.set_font(font_name, 'B', size=14)
    structure_pdf.add_text("Application Folder Structure\n\n")
    structure_pdf.set_font(font_name, size=10)

    def add_directory_contents(pdf, directory, prefix=''):
        """
        Recursively adds directory contents to the PDF.
        """
        try:
            items = sorted(os.listdir(directory))
        except PermissionError:
            pdf.add_text(f"{prefix}└── [Permission Denied]\n")
            return

        for index, item in enumerate(items):
            item_path = os.path.join(directory, item)
            is_last = index == len(items) - 1
            connector = "└── " if is_last else "├── "
            pdf.add_text(f"{prefix}{connector}{item}")
            if os.path.isdir(item_path):
                extension = "    " if is_last else "│   "
                add_directory_contents(pdf, item_path, prefix + extension)

    add_directory_contents(structure_pdf, input_folder)

    # Define the output PDF path
    output_pdf_path = Path(output_folder) / "application_folder_structure.pdf"

    # Save the PDF
    try:
        structure_pdf.output(str(output_pdf_path))
        logging.info(f"Successfully created folder structure PDF at {output_pdf_path}")
        print(f"Folder structure PDF saved to '{output_pdf_path}'.")
    except Exception as e:
        logging.error(f"Failed to write folder structure PDF: {e}")
        print(f"Failed to write folder structure PDF: {e}")

def merge_pdfs(pdf_folder, output_filename):
    """
    Merges all PDFs in the specified folder into a single PDF.
    Each PDF starts on a new page.
    """
    writer = PdfWriter()

    # Collect all PDF files, excluding the merged PDF itself to prevent recursion
    all_pdfs = []
    for root, dirs, files in os.walk(pdf_folder):
        for file in sorted(files):
            if file.lower().endswith('.pdf') and file != output_filename:
                all_pdfs.append(os.path.join(root, file))

    logging.info(f"Found {len(all_pdfs)} PDFs to merge.")
    print(f"Found {len(all_pdfs)} PDFs to merge.")

    for pdf_path in tqdm(all_pdfs, desc="Merging PDFs"):
        try:
            reader = PdfReader(pdf_path)
            for page in reader.pages:
                writer.add_page(page)
        except Exception as e:
            logging.error(f"Failed to read '{pdf_path}': {e}")
            print(f"Failed to read '{pdf_path}': {e}")

    # Define the output PDF path
    output_pdf_path = Path(pdf_folder) / output_filename

    # Save the merged PDF
    try:
        with open(output_pdf_path, 'wb') as f_out:
            writer.write(f_out)
        logging.info(f"Merged PDF saved to '{output_pdf_path}'.")
        print(f"Merged PDF saved to '{output_pdf_path}'.")
    except Exception as e:
        logging.error(f"Failed to write merged PDF: {e}")
        print(f"Failed to write merged PDF: {e}")

def main():
    """
    Main function to convert files in a folder to PDFs, generate folder structure, and merge PDFs.

    This function parses command-line arguments to specify the input folder, output folder, font file,
    and optional actions such as generating a folder structure PDF and merging individual PDFs into a
    single PDF. It validates the input paths, creates necessary output directories, processes files
    in the input folder, and performs the requested actions.

    Command-line Arguments:
        input_folder (str): Path to the input folder (e.g., app_folder).
        output_folder (str): Path to the output folder where PDFs will be saved.
        --font (str): Path to the TTF font file to use for PDFs (required).
        --fontname (str): Name to assign to the custom font in the PDF (default: 'CustomFont').
        --generate-structure (bool): Generate a PDF outlining the folder structure (optional).
        --merge (bool): Merge all individual PDFs into a single app_source.pdf (optional).

    Raises:
        SystemExit: If the input folder does not exist or is not a directory.
        SystemExit: If the font file is not found.

    """
    parser = argparse.ArgumentParser(description="Convert files in a folder to PDFs with file paths, generate folder structure, and merge PDFs.")
    parser.add_argument("input_folder", help="Path to the input folder (e.g., app_folder)")
    parser.add_argument("output_folder", help="Path to the output folder where PDFs will be saved")
    parser.add_argument("--font", help="Path to the TTF font file to use for PDFs", required=True)
    parser.add_argument("--fontname", help="Name to assign to the custom font in the PDF", default='CustomFont')
    parser.add_argument("--generate-structure", action='store_true', help="Generate a PDF outlining the folder structure")
    parser.add_argument("--merge", action='store_true', help="Merge all individual PDFs into a single app_source.pdf")
    args = parser.parse_args()

    input_folder = args.input_folder
    output_folder = args.output_folder
    font_path = args.font
    font_name = args.fontname

    if not os.path.isdir(input_folder):
        print(f"Input folder '{input_folder}' does not exist or is not a directory.")
        sys.exit(1)

    if not os.path.isfile(font_path):
        print(f"Font file '{font_path}' not found. Please provide a valid TTF font file.")
        sys.exit(1)

    # Create output directories
    individual_pdfs_folder = Path(output_folder) / "individual_pdfs"
    individual_pdfs_folder.mkdir(parents=True, exist_ok=True)

    # Collect all files, excluding skipped folders
    all_files = []
    for root, dirs, files in os.walk(input_folder):
        # Modify dirs in-place to skip certain folders
        dirs[:] = [d for d in dirs if d not in SKIP_FOLDERS and not d.startswith('.')]
        for file in files:
            if file not in SKIP_FILES and not file.startswith('.'):
                all_files.append(os.path.join(root, file))

    print(f"Found {len(all_files)} files to process.")
    logging.info(f"Found {len(all_files)} files to process.")

    # Process files with a progress bar
    for file_path in tqdm(all_files, desc="Processing files"):
        process_file(file_path, input_folder, individual_pdfs_folder, font_path, font_name)

    print(f"Individual PDFs have been saved to '{individual_pdfs_folder}'.")
    logging.info(f"Individual PDFs have been saved to '{individual_pdfs_folder}'.")

    # Generate folder structure PDF if requested
    if args.generate_structure:
        print("Generating folder structure PDF...")
        logging.info("Generating folder structure PDF...")
        generate_folder_structure_pdf(input_folder, output_folder, font_path, font_name)

    # Merge PDFs into app_source.pdf if requested
    if args.merge:
        print("Merging individual PDFs into 'app_source.pdf'...")
        logging.info("Merging individual PDFs into 'app_source.pdf'...")
        merge_pdfs(individual_pdfs_folder, "app_source.pdf")
        print("Merged PDF 'app_source.pdf' has been created.")
        logging.info("Merged PDF 'app_source.pdf' has been created.")

if __name__ == "__main__":
    main()
