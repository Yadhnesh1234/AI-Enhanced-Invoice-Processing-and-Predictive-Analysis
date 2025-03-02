import pandas as pd
from typing import Optional
import pandas as pd
import numpy as np
from sklearn.preprocessing import MinMaxScaler
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import TruncatedSVD

def combine_csv_files(file1_path: str, file2_path: str, output_path: Optional[str] = None) -> pd.DataFrame:
    df1 = pd.read_csv(file1_path)
    df2 = pd.read_csv(file2_path)
    combined_df = pd.concat([df1, df2], ignore_index=True)
    combined_df = combined_df[combined_df['StockCode'].str.isnumeric()]
    if output_path:
        combined_df.to_csv(output_path, index=False)

    return combined_df

def perform_kmeans_clustering(ds: pd.DataFrame) -> dict:
    ds = ds.dropna()
    ds['InvoiceDate'] = pd.to_datetime(ds['InvoiceDate'], errors='coerce')
    max_date = ds['InvoiceDate'].max()

    recency_df = ds.groupby('StockCode')['InvoiceDate'].max().reset_index()
    recency_df['Recency'] = (max_date - recency_df['InvoiceDate']).dt.days
    recency_df.drop(columns=['InvoiceDate'], inplace=True)

    frequency_df = ds.groupby('StockCode')['Invoice'].nunique().reset_index()
    frequency_df.columns = ['StockCode', 'Frequency']

    ds['TotalSales'] = ds['Quantity'] * ds['Price']
    monetary_df = ds.groupby('StockCode')['TotalSales'].sum().reset_index()
    monetary_df.columns = ['StockCode', 'Monetary']

    rfm_df = recency_df.merge(frequency_df, on='StockCode').merge(monetary_df, on='StockCode')

    for col in ['Recency', 'Frequency', 'Monetary']:
        Q1 = rfm_df[col].quantile(0.05)
        Q3 = rfm_df[col].quantile(0.95)
        IQR = Q3 - Q1
        rfm_df = rfm_df[(rfm_df[col] >= Q1 - 1.5 * IQR) & (rfm_df[col] <= Q3 + 1.5 * IQR)]

    scaler = MinMaxScaler()
    rfm_scaled = scaler.fit_transform(rfm_df[['Recency', 'Frequency', 'Monetary']])
 
    optimal_k = 3  
    kmeans = KMeans(n_clusters=optimal_k, max_iter=50, random_state=42)
    rfm_df['Cluster'] = kmeans.fit_predict(rfm_scaled)

    vectorizer = TfidfVectorizer(stop_words='english', max_features=1000)
    description_vectors = vectorizer.fit_transform(ds.groupby('StockCode')['Description'].first().fillna(""))

    svd = TruncatedSVD(n_components=5, random_state=42)
    reduced_vectors = svd.fit_transform(description_vectors)

    kmeans_desc = KMeans(n_clusters=5, random_state=42)
    category_labels = kmeans_desc.fit_predict(reduced_vectors)

    product_categories = pd.DataFrame({
        'StockCode': ds['StockCode'].unique(),
        'ProductCategory': category_labels
    })

    rfm_df = rfm_df.merge(product_categories, on='StockCode', how='left')

    cluster_summary = rfm_df.groupby('Cluster').agg({
        'Recency': 'mean',
        'Frequency': 'mean',
        'Monetary': 'mean'
    }).reset_index()

    highest_recency_cluster = cluster_summary.loc[cluster_summary['Recency'].idxmax(), 'Cluster']
    highest_frequency_cluster = cluster_summary.loc[cluster_summary['Frequency'].idxmax(), 'Cluster']
    highest_amount_cluster = cluster_summary.loc[cluster_summary['Monetary'].idxmax(), 'Cluster']

    highest_recency_stockcodes = rfm_df[rfm_df['Cluster'] == highest_recency_cluster]['StockCode'].tolist()
    highest_frequency_stockcodes = rfm_df[rfm_df['Cluster'] == highest_frequency_cluster]['StockCode'].tolist()
    highest_amount_stockcodes = rfm_df[rfm_df['Cluster'] == highest_amount_cluster]['StockCode'].tolist()

    return rfm_df

def get_high_recency_prod(ds: pd.DataFrame, rfm_df: pd.DataFrame) -> list:
    rfm_df = rfm_df.replace([np.inf, -np.inf], np.nan).dropna()
    cluster_summary = rfm_df.groupby('Cluster').agg({'Recency': 'mean'}).reset_index()
    if cluster_summary['Recency'].isnull().all():
        return [] 
    highest_recency_cluster = int(cluster_summary.loc[cluster_summary['Recency'].idxmax(), 'Cluster'])
    max_recency_stockcodes = rfm_df[rfm_df['Cluster'] == highest_recency_cluster]['StockCode'].astype(str).tolist()
    product_names = ds[['StockCode', 'Description']].drop_duplicates()
    max_recency_products = product_names[product_names['StockCode'].astype(str).isin(max_recency_stockcodes)]
    return max_recency_products.fillna("").to_dict(orient="records")

import numpy as np

def get_high_amount_high_frequency_prod(ds: pd.DataFrame, rfm_df: pd.DataFrame) -> list:
    rfm_df = rfm_df.replace([np.inf, -np.inf], np.nan).dropna()
    cluster_summary = rfm_df.groupby('Cluster').agg({
        'Frequency': 'mean',
        'Monetary': 'mean'
    }).reset_index()
    if cluster_summary[['Frequency', 'Monetary']].isnull().all().any():
        return [] 
    highest_frequency_cluster = int(cluster_summary.loc[cluster_summary['Frequency'].idxmax(), 'Cluster'])
    highest_amount_cluster = int(cluster_summary.loc[cluster_summary['Monetary'].idxmax(), 'Cluster'])
    high_freq_stockcodes = rfm_df[rfm_df['Cluster'] == highest_frequency_cluster]['StockCode'].astype(str).tolist()
    high_amount_stockcodes = rfm_df[rfm_df['Cluster'] == highest_amount_cluster]['StockCode'].astype(str).tolist()
    high_value_stockcodes = list(set(high_freq_stockcodes + high_amount_stockcodes))
    product_names = ds[['StockCode', 'Description']].drop_duplicates()
    high_value_products = product_names[product_names['StockCode'].astype(str).isin(high_value_stockcodes)]
    return high_value_products.fillna("").to_dict(orient="records")
