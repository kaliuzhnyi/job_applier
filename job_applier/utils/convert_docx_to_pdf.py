import os
import platform
import subprocess


def find_libreoffice():
    """
    Finds the path to LibreOffice based on the operating system.
    Returns the path to `soffice` or None if LibreOffice is not found.
    """
    system = platform.system()

    if system == "Windows":
        # Standard installation paths for LibreOffice on Windows
        potential_paths = [
            r"C:\Program Files\LibreOffice\program\soffice.exe",
            r"C:\Program Files (x86)\LibreOffice\program\soffice.exe"
        ]
    elif system == "Linux":
        # Standard installation paths for LibreOffice on Linux
        potential_paths = ["/usr/bin/libreoffice", "/usr/bin/soffice"]
    elif system == "Darwin":  # macOS
        # Standard installation path for LibreOffice on macOS
        potential_paths = ["/Applications/LibreOffice.app/Contents/MacOS/soffice"]
    else:
        raise EnvironmentError(f"Unknown operating system: {system}")

    # Check if any of the potential paths exist
    for path in potential_paths:
        if os.path.exists(path):
            return path

    # Return None if no path is found
    return None


def libreoffice_available() -> bool:
    return find_libreoffice() is not None


def convert_to_pdf_with_libreoffice(input_path, output_path):
    """
    Converts a .docx file to .pdf using LibreOffice.

    :param input_path: Path to the input .docx file.
    :param output_path: Path to save the converted .pdf file.
    """
    # Find the path to LibreOffice
    libreoffice_path = find_libreoffice()
    if not libreoffice_path:
        raise FileNotFoundError("LibreOffice was not found. Please ensure it is installed.")

    # Get the directory of the output file
    output_dir = os.path.dirname(output_path)

    # Run LibreOffice in headless mode to perform the conversion
    subprocess.run([
        libreoffice_path, "--headless", "--convert-to", "pdf", "--outdir", output_dir, input_path
    ], check=True)
