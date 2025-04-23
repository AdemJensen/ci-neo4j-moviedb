from pathlib import Path
import pandas as pd
import torch
from sentence_transformers import SentenceTransformer, util


# 加载 BERT 语义向量模型
model = SentenceTransformer('all-MiniLM-L6-v2')  # 推荐用于小规模项目，快速又精确

GENRES_PT_FILE = Path(__file__).parent / "filter_options" / "genres.pt"
KEYWORDS_PT_FILE = Path(__file__).parent / "filter_options" / "keywords.pt"
GENRES_CSV_FILE = Path(__file__).parent / "filter_options" / "genres.csv"
KEYWORDS_CSV_FILE = Path(__file__).parent / "filter_options" / "keywords.csv"

def read_single_column_csv(filepath):
    df = pd.read_csv(filepath)
    col_name = df.columns[0]  # 获取第一列名称
    entries = df[col_name].dropna().astype(str).tolist()
    return entries

def encode_and_save_embeddings_from_csv(csv_path, output_path):
    entries = read_single_column_csv(csv_path)
    embeddings = model.encode(entries, convert_to_tensor=True)
    torch.save({"entries": entries, "embeddings": embeddings}, output_path)

def load_embeddings(file_path):
    data = torch.load(file_path)
    return data["entries"], data["embeddings"]

def find_top_k_similar_from_cache(query, entries, embeddings, k=5):
    query_emb = model.encode(query, convert_to_tensor=True)
    cosine_scores = util.pytorch_cos_sim(query_emb, embeddings)[0]
    top_k = min(k, len(entries))
    top_results = torch.topk(cosine_scores, k=top_k)
    return [(entries[idx], float(cosine_scores[idx])) for idx in top_results.indices]

def get_names_with_score_gt(lst, score):
    return [item[0] for item in lst if item[1] >= score]
