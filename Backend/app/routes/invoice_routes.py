from fastapi import APIRouter, File, UploadFile, HTTPException,Depends
from services.invoice_data_extract import gemini_output
# import aiofiles
# import os
from pymongo.collection import Collection
import json
import re
from datetime import datetime
from db.database import get_db
from bson import ObjectId

router = APIRouter()


async def generate_invoice_number(database = Depends(get_db)):
     collection: Collection = database["Invoice"]
     pipeline = [
        {
            "$project": {
                "year": {"$year": "$created_at"},  
                "month": {"$month": "$created_at"}
            }
        },
        {
            "$match": {
                "year": datetime.now().year,  
                "month": datetime.now().month  
            }
        }
      ]
     result = await collection.aggregate(pipeline).to_list(length=None)
     print(result)
     if not result:
        return 1
     last_counter = len(result)
    
     next_counter = last_counter + 1
    
     return  next_counter

async def get_cleaned_values(parsed_data,database = Depends(get_db)):
     invoice_number = parsed_data.get("invoice_number")
     if not invoice_number:
          now = datetime.now()
          current_year = now.year
          current_month = now.month
          counter_invoice=await generate_invoice_number(database)
          invoice_number = str(current_year)+str(current_month)+str(counter_invoice)
          
     invoice_date = parsed_data.get("invoice_date")
     if not invoice_date:
        invoice_date = datetime.now()
     else:
        invoice_date = parse_date(invoice_date) or datetime.now().strftime("%Y-%m-%d")
            
     total_amount = parsed_data.get("total_amount")
     if not total_amount:
            product_items = parsed_data.get("product_items", [])
            total_amount = sum(item.get("total_price", 0) for item in product_items)
            
     subtotal = parsed_data.get("subtotal")
     if not subtotal:
            subtotal = sum(item.get("total_price", 0) for item in product_items)
     seller_name = parsed_data.get("seller_name", "")
     seller_address = parsed_data.get("seller_address", "")
     invoice = {
            "invoice_number": invoice_number,
            "invoice_date": invoice_date,
            "due_date": parsed_data.get("due_date", None),
            "seller_name": seller_name,
            "seller_address": seller_address,
            "buyer_name": parsed_data.get("buyer_name", ""),
            "buyer_address": parsed_data.get("buyer_address", ""),
            "product_items": parsed_data.get("product_items", []),
            "subtotal": subtotal,
            "tax_amount": parsed_data.get("tax_amount", None),
            "shipping_cost": parsed_data.get("shipping_cost", None),
            "total_amount": total_amount,
            "payment_method": parsed_data.get("payment_method", None),
            "currency": parsed_data.get("currency", None),
            "order_status": parsed_data.get("order_status", None),
            "payment_status": parsed_data.get("payment_status", None),
            "payment_due_date": parsed_data.get("payment_due_date", None),
            "transaction_id": parsed_data.get("transaction_id", None),
            "invoice_terms": parsed_data.get("invoice_terms", None),
            "shipping_address": parsed_data.get("shipping_address", None),
            "billing_address": parsed_data.get("billing_address", None),
            "invoice_type": parsed_data.get("invoice_type", None),
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        }
     return invoice

DATE_FORMATS = [
    "%d/%m/%Y", 
    "%m/%d/%Y",  
    "%Y-%m-%d",  
    "%d-%m-%Y", 
    "%b %d, %Y", 
]

def parse_date(date_str: str) -> str:
    for date_format in DATE_FORMATS:
        try:
            parsed_date = datetime.strptime(date_str, date_format)
            return parsed_date.strftime("%Y-%m-%d")  
        except ValueError:
            continue  
    return None     
 
def serialize_objectid(obj):
    """Recursively convert ObjectId to string."""
    if isinstance(obj, ObjectId):
        return str(obj)
    elif isinstance(obj, dict):
        return {key: serialize_objectid(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [serialize_objectid(item) for item in obj]
    return obj
    
@router.get("/process-invoice/")
async def process_invoice(database = Depends(get_db)):
    try:
        collection: Collection = database["Invoice"]
        temp_file_path = f"./test_img/handwritten_img1.jpg"

        system_prompt = """
               You are a specialist in comprehending receipts.
               Input images in the form of receipts will be provided to you,
               and your task is to respond to questions based on the content of the input image.
               """
        #user_prompt = "Convert Invoice data into json format with appropriate json tags as required for the data in image "
        user_prompt = """
                Please extract the data from the invoice image and convert it into a JSON format. assign  proper values to  following fields that are included in the JSON structure, if some fields need calculation then make proper calculations and if any field is missing in the invoice, assign it as `null` or an empty string (`""`). The fields are:
                {
                    "invoice_number": null,
                    "invoice_date": null,
                    "due_date": null,
                    "seller_name": null,
                    "seller_address": null,
                    "buyer_name": null,
                    "buyer_address": null,
                    "product_items": [
                        {
                        "product_name": null,
                        "product_code": null,
                        "category": null,
                        "quantity": null,
                        "unit_price": null,
                        "total_price": null,
                        "tax": null,
                        "discount": null
                        }
                    ],
                    "subtotal": null,
                    "tax_amount": null,
                    "shipping_cost": null,
                    "total_amount": null,
                    "payment_method": null,
                    "currency": null,
                    "order_status": null,
                    "payment_status": null,
                    "payment_due_date": null,
                    "transaction_id": null,
                    "invoice_terms": null,
                    "shipping_address": null,
                    "billing_address": null,
                    "invoice_type": null,
                    "created_at": null,
                    "updated_at": null
                    }
                Make sure the values are extracted accurately from the invoice. If any of these fields are not present in the invoice, please assign `null` (or an empty string for strings) as the value for that field. Thank you!
                """
        invoice_data = gemini_output(temp_file_path, system_prompt, user_prompt)

        json_string = re.sub(r'```json\n(.*?)\n```', r'\1', invoice_data, flags=re.DOTALL)

        parsed_data = json.loads(json_string)
        
        # invoice_data = await get_cleaned_values(parsed_data,database)
        # result = await collection.insert_one(invoice_data)
        return {"invoice_data": parsed_data}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing invoice: {str(e)}")
