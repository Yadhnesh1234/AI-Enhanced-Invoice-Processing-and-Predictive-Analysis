import pandas as pd
from typing import Optional
import pandas as pd
from sklearn.preprocessing import MinMaxScaler
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from mlxtend.frequent_patterns import apriori, association_rules
from mlxtend.preprocessing import TransactionEncoder

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
    ds['Amount'] = ds['Quantity'] * ds['Price']
    
    # Group by StockCode instead of Customer ID
    rfm_ds_m = ds.groupby('StockCode')['Amount'].sum().reset_index()
    rfm_ds_m.columns = ['StockCode', 'Amount']
    
    # Calculate Recency (Days since last purchase)
    ds['InvoiceDate'] = pd.to_datetime(ds['InvoiceDate'], errors='coerce')
    max_date = max(ds['InvoiceDate'])
    ds['Diff'] = max_date - ds['InvoiceDate']
    rfm_ds_p = ds.groupby('StockCode')['Diff'].min().reset_index()
    rfm_ds_p.columns = ['StockCode', 'Diff']
    rfm_ds_p['Diff'] = rfm_ds_p['Diff'].dt.days
    
    # Calculate Frequency (Number of purchases per StockCode)
    rfm_ds_f = ds.groupby('StockCode')['Invoice'].count().reset_index()
    rfm_ds_f.columns = ['StockCode', 'Frequency']
    
    # Merge RFM metrics
    rfm_ds_final = pd.merge(rfm_ds_m, rfm_ds_f, on='StockCode', how='inner')
    rfm_ds_final = pd.merge(rfm_ds_final, rfm_ds_p, on='StockCode', how='inner')
    rfm_ds_final.columns = ['StockCode', 'Amount', 'Frequency', 'Recency']

    # Remove outliers
    for column in ['Amount', 'Frequency', 'Recency']:
        Q1 = rfm_ds_final[column].quantile(0.05)
        Q3 = rfm_ds_final[column].quantile(0.95)
        IQR = Q3 - Q1
        rfm_ds_final = rfm_ds_final[(rfm_ds_final[column] >= Q1 - 1.5 * IQR) & (rfm_ds_final[column] <= Q3 + 1.5 * IQR)]

    # Scale data
    X = rfm_ds_final[['Amount', 'Frequency', 'Recency']]
    scaler = MinMaxScaler()
    rfm_ds_scaled = scaler.fit_transform(X)
    rfm_ds_scaled = pd.DataFrame(rfm_ds_scaled, columns=['Amount', 'Frequency', 'Recency'])

    # KMeans Clustering
    kmeans = KMeans(n_clusters=3, max_iter=50, random_state=42)
    kmeans.fit(rfm_ds_scaled)
    rfm_ds_final['Cluster'] = kmeans.labels_

    # Identify clusters with highest Recency, Frequency, and Amount
    cluster_summary = rfm_ds_final.groupby('Cluster').agg({
        'Amount': 'mean',
        'Frequency': 'mean',
        'Recency': 'mean'
    }).reset_index()

    # Find clusters with highest values for each metric
    highest_recency_cluster = cluster_summary.loc[cluster_summary['Recency'].idxmax(), 'Cluster']
    highest_frequency_cluster = cluster_summary.loc[cluster_summary['Frequency'].idxmax(), 'Cluster']
    highest_amount_cluster = cluster_summary.loc[cluster_summary['Amount'].idxmax(), 'Cluster']

    # Extract StockCodes for each of these clusters
    highest_recency_stockcodes = rfm_ds_final[rfm_ds_final['Cluster'] == highest_recency_cluster]['StockCode'].tolist()
    highest_frequency_stockcodes = rfm_ds_final[rfm_ds_final['Cluster'] == highest_frequency_cluster]['StockCode'].tolist()
    highest_amount_stockcodes = rfm_ds_final[rfm_ds_final['Cluster'] == highest_amount_cluster]['StockCode'].tolist()

    # Return the clustered data and cluster information
    return {
        "highest_recency_cluster": {
            "cluster": int(highest_recency_cluster),
            "stockcodes": highest_recency_stockcodes
        },
        "highest_frequency_cluster": {
            "cluster": int(highest_frequency_cluster),
            "stockcodes": highest_frequency_stockcodes
        },
        "highest_amount_cluster": {
            "cluster": int(highest_amount_cluster),
            "stockcodes": highest_amount_stockcodes
        },
        "cluster_summary": cluster_summary.to_dict(orient='records')
    }
    
def filter_last_n_months(ds: pd.DataFrame, months: int = 2) -> pd.DataFrame:
    ds['InvoiceDate'] = pd.to_datetime(ds['InvoiceDate'])
    last_date = ds['InvoiceDate'].max()
    cutoff_date = last_date - pd.DateOffset(months=months)
    return ds[ds['InvoiceDate'] >= cutoff_date]

def prepare_transaction_data(ds: pd.DataFrame, min_items=2, min_freq=5) -> list:
    product_counts = ds['StockCode'].value_counts()
    frequent_products = product_counts[product_counts >= min_freq].index
    ds_filtered = ds[ds['StockCode'].isin(frequent_products)]
    
    transactions = ds_filtered.groupby('Invoice')['StockCode'].apply(list).tolist()
    return [t for t in transactions if len(t) >= min_items]

def encode_transactions(transactions: list) -> pd.DataFrame:
    te = TransactionEncoder()
    te_ary = te.fit(transactions).transform(transactions, sparse=True)  
    return pd.DataFrame.sparse.from_spmatrix(te_ary, columns=te.columns_)

def find_product_associations_apriori(df: pd.DataFrame, min_support: float = 0.005) -> pd.DataFrame:
    frequent_itemsets = apriori(df, min_support=min_support, use_colnames=True)
    
    if frequent_itemsets.empty:
        print("⚠️ No frequent itemsets found! Try reducing min_support.")
    
    return frequent_itemsets

def generate_association_rules(frequent_itemsets: pd.DataFrame, min_lift: float = 0.5) -> pd.DataFrame:
    if frequent_itemsets.empty:
        return pd.DataFrame()
    
    rules = association_rules(frequent_itemsets, metric="lift", min_threshold=min_lift)
    
    if rules.empty:
        print("⚠️ No association rules found! Try reducing min_lift.")
    
    return rules

def hot_encode(x): 
    if(x<= 0): 
        return 0
    if(x>= 1): 
        return 1
def run_apriori_association(data):
       data['Description'] = data['Description'].str.strip()  
       data.dropna(axis = 0, subset =['Invoice'], inplace = True) 
       data['Invoice'] = data['Invoice'].astype('str')  
       data = data[~data['Invoice'].str.contains('C')] 
       basket=data.groupby(['Invoice', 'Description'])['Quantity'] .sum().unstack().reset_index().fillna(0).set_index('Invoice') 
       basket_encoded = basket.applymap(hot_encode) 
       basket= basket_encoded 
       frq_items = apriori(basket, min_support=0.02, use_colnames=True)
       rules = association_rules(frq_items, metric="lift", min_threshold=1, support_only=False,num_itemsets=len(frq_items))
       rules = rules.sort_values(['confidence', 'lift'], ascending=[False, False])
       return rules.head()