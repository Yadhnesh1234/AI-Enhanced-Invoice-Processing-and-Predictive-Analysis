from fastapi import APIRouter, File, UploadFile, HTTPException
from services.prediction_service import combine_csv_files,perform_kmeans_clustering,run_apriori_association
from mlxtend.frequent_patterns import apriori,association_rules
from mlxtend.preprocessing import TransactionEncoder
import pandas as pd
import re

router = APIRouter()

path1 = "./data/combine_dataset_2009_2011.csv"
# path2 = "./data/Year 2010-2011.csv"
ds=pd.read_csv(path1)
#ds=ds[ds['StockCode'].str.isnumeric()]

@router.get("/frequent-customer-behaviour/")
async def frequent_purchase_items():
    try:
       
       cluster_info = perform_kmeans_clustering(ds)
       
       return {
        "response": cluster_info
       }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing invoice: {str(e)}")
    
def safe_eval(value):
    try:
        match = re.match(r"frozenset\((\{.*\})\)", value)
        if match:
            return eval(match.group(1)) 
        return set()  
    except Exception:
        return set()


@router.get("/get-association-rule/")
async def get_association_rule():
    try:
        rules = pd.read_csv("./data/optimized_association_rules_new.csv")
        rules["antecedents"] = rules["antecedents"].apply(safe_eval)
        rules["consequents"] = rules["consequents"].apply(safe_eval)

        # Ensure rules with valid sets are selected
        rules = rules[(rules["antecedents"].apply(len) > 0) & (rules["consequents"].apply(len) > 0)]

        # Convert sets to lists for JSON serialization
        rules_json = rules.copy()
        rules_json["antecedents"] = rules_json["antecedents"].apply(list)
        rules_json["consequents"] = rules_json["consequents"].apply(list)

        return {"association_rules": rules_json[["antecedents", "consequents", "confidence", "lift"]].to_dict(orient="records")}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing invoice: {str(e)}")