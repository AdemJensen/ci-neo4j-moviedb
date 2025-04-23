from email.policy import default
from pathlib import Path
import requests
import os
from tqdm import tqdm

def download_from_url(url, destination):
    """
    Downloads a file from url with a progress bar
    """
    response = requests.get(url, stream=True)
    total_size = int(response.headers.get('content-length', 0))
    block_size = 1024  # 1 Kilobyte

    if response.status_code == 200:
        with open(destination, 'wb') as f, tqdm(
            desc=f"Downloading model files",
            total=total_size,
            unit='iB',
            unit_scale=True,
            unit_divisor=1024,
        ) as bar:
            for chunk in response.iter_content(chunk_size=block_size):
                if chunk:
                    f.write(chunk)
                    bar.update(len(chunk))
        print(f"✅ Downloaded model files to {destination}")
    else:
        print(f"❌ Failed to download {destination}. Status code: {response.status_code}")


def setup_model_data(file_url):
    model_dir = Path(__file__).parent
    model_check_dir = Path(__file__).parent / "TheMoviesDataset"
    if not model_check_dir.exists():
        print("Model files not found, will download and unzip automatically...")
        # model_dir.mkdir(exist_ok=True)
        zip_path = model_dir / "model.zip"
        download_from_url(file_url, zip_path)
        print("Unzipping model files...")
        unzip_file(zip_path, model_dir)
        os.remove(zip_path)
        print("✅ Model files setup successfully.")
    else:
        print("Model files already exist.")

def unzip_file(zip_path, extract_to):
    import zipfile
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(extract_to)

def calculate_list_embeddings():
    from .filter_embedding import encode_and_save_embeddings_from_csv
    from .filter_embedding import GENRES_PT_FILE, KEYWORDS_PT_FILE, GENRES_CSV_FILE, KEYWORDS_CSV_FILE
    # Encode and save the embeddings
    encode_and_save_embeddings_from_csv(GENRES_CSV_FILE, GENRES_PT_FILE)
    encode_and_save_embeddings_from_csv(KEYWORDS_CSV_FILE, KEYWORDS_PT_FILE)

def setup_model_data_auto():
    setup_model_data("https://www.dropbox.com/scl/fi/6g0psqd25dy1ihuzo6pwi/model.zip?rlkey=jfkyihw9c3xchvd8isvlb2pho&st=qvxxs8w0&dl=1")


setup_model_data_auto()

# export necessary functions
from .utils import recommend_by_tmdb_movies, recommend_by_genres