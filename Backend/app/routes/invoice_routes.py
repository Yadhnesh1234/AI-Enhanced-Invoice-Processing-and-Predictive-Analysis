from fastapi import APIRouter, HTTPException,Depends
from services.invoice_data_extract import gemini_output,serialize_objectid,parse_date,get_cleaned_values
# import aiofiles
# import os
from pymongo.collection import Collection
import json
import re
from db.database import database
import pandas as pd
from datetime import datetime

router = APIRouter()

    
@router.get("/process-invoice/")
async def process_invoice():
    try:
        collection: Collection = database["Invoice"]
        temp_file_path = f"./test_img/handwritten_img1.jpg"
        
        invoice_data = gemini_output(temp_file_path)

        json_string = re.sub(r'```json\n(.*?)\n```', r'\1', invoice_data, flags=re.DOTALL)

        parsed_data = json.loads(json_string)
        # invoice_data = await get_cleaned_values(parsed_data)
        # df = pd.read_csv('./data/combine_dataset_2009_2011.csv')
        # df = df[~df["Invoice"].astype(str).str.startswith("C")]
        # df['Customer ID']=df['Customer ID'].fillna("")
        # df["InvoiceDate"] = pd.to_datetime(df["InvoiceDate"], errors="coerce")
        # # print(len(df["Invoice"].unique()))
        # counter=0
        # for invoice, group in df.groupby("Invoice"):
        #     invoice_data = {
        #         "InvoiceNo": invoice,
        #         "InvoiceDate": group["InvoiceDate"].iloc[0].strftime("%Y-%m-%d %H:%M:%S"),
        #         "SellerName": "",
        #         "SellerAddress": "",
        #         "Customer ID": group["Customer ID"].iloc[0],
        #         "Customer Name": "",
        #         "ProductItems": [
        #             {
        #                 "Description": row["Description"],
        #                 "StockCode": row["StockCode"],
        #                 "Category": "",
        #                 "Quantity": row["Quantity"],
        #                 "UnitPrice": row["Price"],
        #                 "total_price": row["Quantity"] * row["Price"]
        #             }
        #             for _, row in group.iterrows()
        #         ],
        #         "SubTotal": group["Quantity"].mul(group["Price"]).sum(),
        #         "TotalAmount": group["Quantity"].mul(group["Price"]).sum(),  
        #         "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        #         "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        #     }
        #     await collection.insert_one(invoice_data)
        #     print("Data Inserted ",counter)
        #     counter=counter+1
        return {"Response": "Data Inserted","Invoice_Data":parsed_data}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing invoice: {str(e)}")
